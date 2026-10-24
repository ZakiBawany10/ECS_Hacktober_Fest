import math
import random
import re
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Literal

from . import config
from .events import EVENT_WEIGHTS, Event, EventType, Multiplier, create_event, eligible
from .lifecycle import (
    DARK_STAGES,
    DECLINE_SECONDS,
    DECLINE_STAGES,
    MAIN_SEQUENCE_L_BOUNDS,
    REMNANT_STAGES,
    STAGE_L_BOUNDS,
    SUPERNOVA_DROP_SECONDS,
    SUPERNOVA_FADE,
    SUPERNOVA_GLOW_SECONDS,
    SUPERNOVA_PEAK,
    Stage,
    generate_luminosity,
    next_stage,
    roll_duration_ticks,
    seconds_to_ticks,
)
from .pricing import (
    PriceLeg,
    apply_impact,
    decay_impact,
    luminosity_from_price,
    market_price,
    path_price,
    price_from_luminosity,
    twinkle,
)
from .seed import SEED_STARS
from .spawn import (
    FALLBACK_NAMES,
    MAIN_SEQUENCE_MASS_BOUNDS,
    MAIN_SEQUENCE_TEMPERATURE_BOUNDS,
    SPAWN_TYPES,
    Forecast,
    ignition_note,
    roll_forecast,
)

# Tolerance for float comparisons on cash and share quantities.
EPSILON = 1e-9

NewsKind = Literal["lifecycle", "event", "rumour", "system"]


class MarketError(Exception):
    """A request the market rejects, such as a trade the player can't afford."""


class NotFoundError(MarketError):
    pass


@dataclass
class Star:
    id: str
    name: str
    spectral_type: str
    mass: float
    temperature: float
    base_L: float  # server-only: the luminosity twinkle reverts towards
    L: float
    price: float
    impact: float = 1.0  # trading-pressure multiplier on the luminosity price; decays back to 1
    stage: Stage = "main_sequence"
    ticks_left: int | None = None  # ticks until the next stage; None means the star never evolves
    path: list[PriceLeg] = field(default_factory=list)  # server-only: scripted price legs; L follows them
    multipliers: dict[str, Multiplier] = field(default_factory=dict)  # event effects on price, keyed by event id
    forecast: Forecast | None = None  # server-only: set for stars that spawned as protostars
    listed: bool = True  # False once delisted: still shown on the map, but off the exchange
    shares_held: float = 0.0
    history: deque[tuple[int, float]] = field(default_factory=lambda: deque(maxlen=config.HISTORY_LENGTH))

    @property
    def shares_available(self) -> float:
        return config.SHARES_PER_STAR - self.shares_held

    @property
    def event_multiplier(self) -> float:
        return math.prod(multiplier.value for multiplier in self.multipliers.values())

    def priced_at(self, impact: float) -> float:
        """Share price with this trading-pressure multiplier and the current event multipliers."""
        return market_price(self.L, self.event_multiplier * impact)


@dataclass
class StageChange:
    asset_id: str
    old_stage: Stage
    new_stage: Stage
    t: int
    note: str = ""  # extra context for the news, such as how a protostar's forecast turned out


@dataclass
class TickReport:
    """What happened during a tick that the news should cover."""

    stage_changes: list[StageChange] = field(default_factory=list)
    events: list[Event] = field(default_factory=list)
    spawned: list[Star] = field(default_factory=list)
    forecast_updates: list[Star] = field(default_factory=list)  # protostars halfway to ignition
    delisted: list[Star] = field(default_factory=list)


@dataclass
class News:
    id: str
    t: int
    kind: NewsKind
    headline: str
    body: str
    asset_ids: list[str]
    source: str  # the outlet reporting it
    side: Literal["human", "alien"]


@dataclass
class Player:
    id: str
    nickname: str
    cash: float
    holdings: dict[str, float] = field(default_factory=dict)
    joined_at: float = field(default_factory=time.time)


@dataclass
class Trade:
    id: str
    player_id: str
    asset_id: str
    side: str
    qty: float
    price: float
    t: int


class Market:
    """In-memory, authoritative game state. Not thread-safe: call it from one event loop."""

    def __init__(self, rng: random.Random | None = None, random_events: bool = True) -> None:
        """random_events=False stops random events and spawns, for tests; start_event and spawn_star still work."""
        self.rng = rng or random.Random()
        self.tick = 0
        self.stars: dict[str, Star] = {}
        self.players: dict[str, Player] = {}
        self.trades: list[Trade] = []
        self.news: deque[News] = deque(maxlen=config.NEWS_LENGTH)
        self.events: dict[str, Event] = {}
        self.name_pool: deque[str] = deque()  # names for new stars, filled by Gemma; FALLBACK_NAMES otherwise
        for seed in SEED_STARS:
            L = generate_luminosity(MAIN_SEQUENCE_L_BOUNDS[seed["spectral_type"]], self.rng)
            star = Star(
                id=seed["id"],
                name=seed["name"],
                spectral_type=seed["spectral_type"],
                mass=seed["mass"],
                temperature=seed["temperature"],
                base_L=L,
                L=L,
                price=price_from_luminosity(L),
            )
            star.ticks_left = roll_duration_ticks(star.stage, star.spectral_type, self.rng)
            if star.ticks_left is not None and "seconds_left" in seed:
                star.ticks_left = seconds_to_ticks(seed["seconds_left"])
            star.history.append((self.tick, star.price))
            self.stars[star.id] = star
        self.next_event_tick = self._roll_next_event_tick() if random_events else None
        self.next_spawn_tick = self._roll_next_spawn_tick() if random_events else None

    def _enter_stage(self, star: Star, stage: Stage) -> None:
        # A star leaving mid-path, such as a supernova forced early, lands where its path was heading.
        landing_price = star.path[-1].end_price if star.path else None
        star.path = []
        star.stage = stage
        if stage == "supernova":
            self._start_supernova(star)
            return
        star.ticks_left = roll_duration_ticks(stage, star.spectral_type, self.rng)
        if stage in DARK_STAGES:
            star.base_L = star.L = 0.0
        elif stage == "main_sequence":
            assert star.forecast is not None, "only protostars enter the main sequence"
            star.base_L = star.L = star.forecast.true_L  # ignition: the true value is revealed
        elif landing_price is not None:
            star.base_L = star.L = luminosity_from_price(landing_price)
        else:
            # Twinkle's mean reversion eases L towards the new base_L over the next few ticks.
            star.base_L = generate_luminosity(STAGE_L_BOUNDS[stage], self.rng)
            if stage in DECLINE_STAGES:
                start_price = price_from_luminosity(star.L)
                self._start_path(star, start_price, [(DECLINE_SECONDS, price_from_luminosity(star.base_L))])

    def _start_supernova(self, star: Star) -> None:
        """Spike to SUPERNOVA_PEAK × the price, fade slowly, then drop to the remnant's price."""
        peak = SUPERNOVA_PEAK * price_from_luminosity(star.L)
        remnant = next_stage("supernova", star.spectral_type)
        if remnant in DARK_STAGES:
            remnant_price = 0.0
        else:
            remnant_price = price_from_luminosity(generate_luminosity(STAGE_L_BOUNDS[remnant], self.rng))
        glow_seconds = self.rng.uniform(*SUPERNOVA_GLOW_SECONDS)
        self._start_path(
            star, peak, [(glow_seconds, SUPERNOVA_FADE * peak), (SUPERNOVA_DROP_SECONDS, remnant_price)]
        )
        star.ticks_left = star.path[-1].end_tick - self.tick

    def _start_path(self, star: Star, start_price: float, legs: list[tuple[float, float]]) -> None:
        """Script the star's luminosity price as straight lines from now, each (seconds, end price)."""
        tick = self.tick
        star.path = []
        for seconds, end_price in legs:
            end_tick = tick + seconds_to_ticks(seconds)
            star.path.append(PriceLeg(tick, start_price, end_tick, end_price))
            tick, start_price = end_tick, end_price
        star.L = luminosity_from_price(path_price(star.path, self.tick))

    def _change_stage(self, star: Star, stage: Stage) -> StageChange:
        change = StageChange(star.id, star.stage, stage, self.tick)
        self._enter_stage(star, stage)
        if change.old_stage == "protostar" and star.forecast is not None:
            change.note = ignition_note(star.forecast)
        return change

    def force_next_stage(self, asset_id: str) -> StageChange:
        """Move a star to its next stage now, for testing and the demo."""
        star = self.get_star(asset_id)
        stage = next_stage(star.stage, star.spectral_type)
        if stage is None:
            raise MarketError(f"{star.name} is already in its final stage")
        change = self._change_stage(star, stage)
        star.price = star.priced_at(star.impact)
        return change

    def living_stars(self) -> list[Star]:
        return [star for star in self.stars.values() if star.stage not in REMNANT_STAGES]

    def spawn_star(self, spectral_type: str | None = None) -> Star:
        """List a new protostar. Its spectral type and true future are hidden until it ignites."""
        spectral_type = spectral_type or self.rng.choice(SPAWN_TYPES)
        name = self._new_name()
        ticks = roll_duration_ticks("protostar", spectral_type, self.rng)
        assert ticks is not None
        true_L = generate_luminosity(MAIN_SEQUENCE_L_BOUNDS[spectral_type], self.rng)
        forecast = roll_forecast(true_L, self.tick, self.tick + ticks, self.rng)
        L = luminosity_from_price(forecast.predicted_price(self.tick, self.rng))
        star = Star(
            id=self._new_id(name),
            name=name,
            spectral_type=spectral_type,
            mass=round(self.rng.uniform(*MAIN_SEQUENCE_MASS_BOUNDS[spectral_type]), 2),
            temperature=round(self.rng.uniform(*MAIN_SEQUENCE_TEMPERATURE_BOUNDS[spectral_type]), -2),
            base_L=L,
            L=L,
            price=price_from_luminosity(L),
            stage="protostar",
            ticks_left=ticks,
            forecast=forecast,
        )
        star.history.append((self.tick, star.price))
        self.stars[star.id] = star
        return star

    def _new_name(self) -> str:
        taken = {star.name.lower() for star in self.stars.values()}
        while self.name_pool:
            name = self.name_pool.popleft()
            if name.lower() not in taken:
                return name
        unused = [name for name in FALLBACK_NAMES if name.lower() not in taken]
        if unused:
            return self.rng.choice(unused)
        return f"Nova {self.tick}"

    def _new_id(self, name: str) -> str:
        base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "star"
        asset_id, n = base, 2
        while asset_id in self.stars:
            asset_id, n = f"{base}-{n}", n + 1
        return asset_id

    def _delist(self, star: Star) -> None:
        """Take a star off the exchange. It stays in self.stars for the map, but its shares are written
        off: they were worth nothing anyway."""
        star.listed = False
        star.ticks_left = None
        for event_id in [event.id for event in self.events.values() if event.asset_id == star.id]:
            del self.events[event_id]
        for player in self.players.values():
            player.holdings.pop(star.id, None)

    def start_event(self, event_type: EventType, asset_id: str) -> Event:
        """Start an event on a star now, or raise MarketError if it can't happen to that star."""
        star = self.get_star(asset_id)
        if not eligible(event_type, star):
            raise MarketError(f"A {event_type.replace('_', ' ')} can't happen to {star.name} as a {star.stage}")
        event = create_event(event_type, star, self.tick, self.rng)
        event.start(star)
        self.events[event.id] = event
        return event

    def _roll_next_event_tick(self) -> int:
        """Events arrive as a Poisson process: exponential gaps averaging EVENT_MEAN_GAP_SECONDS."""
        return self.tick + seconds_to_ticks(self.rng.expovariate(1 / config.EVENT_MEAN_GAP_SECONDS))

    def _roll_next_spawn_tick(self) -> int:
        return self.tick + seconds_to_ticks(self.rng.expovariate(1 / config.SPAWN_MEAN_GAP_SECONDS))

    def _start_random_event(self) -> Event | None:
        """Pick a type by weight among those with an eligible star, then one of those stars at random."""
        candidates = {
            event_type: [star for star in self.stars.values() if eligible(event_type, star)]
            for event_type in EVENT_WEIGHTS
        }
        types = [event_type for event_type, stars in candidates.items() if stars]
        if not types:
            return None
        event_type = self.rng.choices(types, weights=[EVENT_WEIGHTS[t] for t in types])[0]
        return self.start_event(event_type, self.rng.choice(candidates[event_type]).id)

    def advance(self) -> TickReport:
        """Move the market on one tick and report what happened that the news should cover."""
        self.tick += 1
        report = TickReport()
        if self.next_event_tick is not None and self.tick >= self.next_event_tick:
            event = self._start_random_event()
            if event is not None:
                report.events.append(event)
            self.next_event_tick = self._roll_next_event_tick()
        if self.next_spawn_tick is not None and self.tick >= self.next_spawn_tick:
            if len(self.living_stars()) < config.MAX_LIVING_STARS:
                report.spawned.append(self.spawn_star())
            self.next_spawn_tick = self._roll_next_spawn_tick()
        for event in list(self.events.values()):
            if event.tick(self.stars[event.asset_id], self.tick):
                del self.events[event.id]
        for star in list(self.stars.values()):
            if star.ticks_left is not None:
                star.ticks_left -= 1
                if star.ticks_left <= 0:
                    stage = next_stage(star.stage, star.spectral_type)
                    if stage is not None:
                        report.stage_changes.append(self._change_stage(star, stage))
                    elif star.stage in DARK_STAGES:
                        self._delist(star)
                        report.delisted.append(star)
                    else:
                        star.ticks_left = None
            if star.stage == "protostar" and star.forecast is not None:
                star.L = luminosity_from_price(star.forecast.predicted_price(self.tick, self.rng))
                if self.tick == star.forecast.midpoint_tick:
                    report.forecast_updates.append(star)
            elif star.path:
                star.L = luminosity_from_price(path_price(star.path, self.tick))
                if self.tick >= star.path[-1].end_tick:
                    star.base_L = star.L
                    star.path = []
            elif star.stage not in DARK_STAGES:
                star.L = twinkle(star.L, star.base_L, self.rng)
            for multiplier in star.multipliers.values():
                multiplier.ease()
            star.impact = decay_impact(star.impact)
            star.price = star.priced_at(star.impact)
            star.history.append((self.tick, star.price))
        return report

    def add_news(
        self,
        kind: NewsKind,
        headline: str,
        body: str,
        asset_ids: list[str],
        t: int | None = None,
        source: str = "Star Market Exchange",
        side: Literal["human", "alien"] = "human",
    ) -> News:
        """Publish a news item. t defaults to now; pass the tick an event happened if it was earlier."""
        news = News(
            id=uuid.uuid4().hex,
            t=self.tick if t is None else t,
            kind=kind,
            headline=headline,
            body=body,
            asset_ids=asset_ids,
            source=source,
            side=side,
        )
        self.news.append(news)
        return news

    def join(self, nickname: str) -> Player:
        player = Player(id=uuid.uuid4().hex, nickname=nickname, cash=config.STARTING_CASH)
        self.players[player.id] = player
        return player

    def get_player(self, player_id: str) -> Player:
        player = self.players.get(player_id)
        if player is None:
            raise NotFoundError(f"Unknown player {player_id!r}")
        return player

    def get_star(self, asset_id: str) -> Star:
        star = self.stars.get(asset_id)
        if star is None:
            raise NotFoundError(f"Unknown asset {asset_id!r}")
        return star

    def trade(self, player_id: str, asset_id: str, side: str, qty: float) -> Trade:
        """Fill a market order, or raise MarketError.

        The trade moves the price first and fills at the moved price, so the trader pays their own
        price impact. That makes an instant buy-then-sell lose money instead of printing it.
        """
        player = self.get_player(player_id)
        star = self.get_star(asset_id)
        if qty <= 0:
            raise MarketError("Quantity must be positive")
        if not star.listed:
            raise MarketError(f"{star.name} has been delisted and can't be traded")
        if star.stage in DARK_STAGES:
            raise MarketError(f"{star.name} is a black hole and can't be traded")
        if side not in ("buy", "sell"):
            raise MarketError("Side must be 'buy' or 'sell'")

        impact = apply_impact(star.impact, side, qty * star.price)
        fill_price = star.priced_at(impact)
        cost = qty * fill_price
        if side == "buy":
            if qty > star.shares_available + EPSILON:
                raise MarketError(f"Only {star.shares_available:g} shares of {star.name} are available")
            if cost > player.cash + EPSILON:
                raise MarketError(f"Not enough cash: {qty:g} shares of {star.name} cost {cost:,.2f} at {fill_price:,.2f} each")
            player.cash = max(player.cash - cost, 0.0)
            player.holdings[star.id] = player.holdings.get(star.id, 0.0) + qty
            star.shares_held += qty
        else:
            held = player.holdings.get(star.id, 0.0)
            if qty > held + EPSILON:
                raise MarketError(f"You only hold {held:g} shares of {star.name}")
            qty = min(qty, held)
            player.cash += qty * fill_price
            remaining = held - qty
            if remaining > EPSILON:
                player.holdings[star.id] = remaining
            else:
                del player.holdings[star.id]
            star.shares_held = max(star.shares_held - qty, 0.0)

        star.impact = impact
        star.price = fill_price
        trade = Trade(
            id=uuid.uuid4().hex,
            player_id=player.id,
            asset_id=star.id,
            side=side,
            qty=qty,
            price=star.price,
            t=self.tick,
        )
        self.trades.append(trade)
        return trade

    def net_worth(self, player: Player) -> float:
        return player.cash + sum(qty * self.stars[asset_id].price for asset_id, qty in player.holdings.items())

    def leaderboard(self) -> list[tuple[Player, float]]:
        rows = [(player, self.net_worth(player)) for player in self.players.values()]
        return sorted(rows, key=lambda row: row[1], reverse=True)
