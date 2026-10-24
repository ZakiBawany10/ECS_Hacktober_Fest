import random
import time
import uuid
from collections import deque
from dataclasses import dataclass, field

from . import config
from .lifecycle import (
    DARK_STAGES,
    DECLINE_SECONDS,
    DECLINE_STAGES,
    MAIN_SEQUENCE_L_BOUNDS,
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

# Tolerance for float comparisons on cash and share quantities.
EPSILON = 1e-9


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
    shares_held: float = 0.0
    history: deque[tuple[int, float]] = field(default_factory=lambda: deque(maxlen=config.HISTORY_LENGTH))

    @property
    def shares_available(self) -> float:
        return config.SHARES_PER_STAR - self.shares_held


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

    def __init__(self, rng: random.Random | None = None) -> None:
        self.rng = rng or random.Random()
        self.tick = 0
        self.stars: dict[str, Star] = {}
        self.players: dict[str, Player] = {}
        self.trades: list[Trade] = []
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

    def force_next_stage(self, asset_id: str) -> Star:
        """Move a star to its next stage now, for testing and the demo."""
        star = self.get_star(asset_id)
        stage = next_stage(star.stage, star.spectral_type)
        if stage is None:
            raise MarketError(f"{star.name} is already in its final stage")
        self._enter_stage(star, stage)
        star.price = market_price(star.L, star.impact)
        return star

    def advance(self) -> None:
        self.tick += 1
        for star in self.stars.values():
            if star.ticks_left is not None:
                star.ticks_left -= 1
                if star.ticks_left <= 0:
                    stage = next_stage(star.stage, star.spectral_type)
                    if stage is None:
                        star.ticks_left = None
                    else:
                        self._enter_stage(star, stage)
            if star.path:
                star.L = luminosity_from_price(path_price(star.path, self.tick))
                if self.tick >= star.path[-1].end_tick:
                    star.base_L = star.L
                    star.path = []
            elif star.stage not in DARK_STAGES:
                star.L = twinkle(star.L, star.base_L, self.rng)
            star.impact = decay_impact(star.impact)
            star.price = market_price(star.L, star.impact)
            star.history.append((self.tick, star.price))

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
        if star.stage in DARK_STAGES:
            raise MarketError(f"{star.name} is a black hole and can't be traded")
        if side not in ("buy", "sell"):
            raise MarketError("Side must be 'buy' or 'sell'")

        impact = apply_impact(star.impact, side, qty * star.price)
        fill_price = market_price(star.L, impact)
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
