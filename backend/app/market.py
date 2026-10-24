import random
import time
import uuid
from collections import deque
from dataclasses import dataclass, field

from . import config
from .lifecycle import (
    DARK_STAGES,
    MAIN_SEQUENCE_L_BOUNDS,
    SNAP_STAGES,
    STAGE_L_BOUNDS,
    Stage,
    generate_luminosity,
    next_stage,
    roll_duration_ticks,
    seconds_to_ticks,
)
from .pricing import price_from_luminosity, twinkle
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
    stage: Stage = "main_sequence"
    ticks_left: int | None = None  # ticks until the next stage; None means the star never evolves
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
        star.stage = stage
        star.ticks_left = roll_duration_ticks(stage, star.spectral_type, self.rng)
        if stage in DARK_STAGES:
            star.base_L = star.L = 0.0
            return
        # Twinkle's mean reversion eases L towards the new base_L over the next few ticks.
        star.base_L = generate_luminosity(STAGE_L_BOUNDS[stage], self.rng)
        if stage in SNAP_STAGES:
            star.L = star.base_L

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
            if star.stage not in DARK_STAGES:
                star.L = twinkle(star.L, star.base_L, self.rng)
            star.price = price_from_luminosity(star.L)
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
        """Fill a market order at the current price, or raise MarketError."""
        player = self.get_player(player_id)
        star = self.get_star(asset_id)
        if qty <= 0:
            raise MarketError("Quantity must be positive")

        cost = qty * star.price
        if side == "buy":
            if qty > star.shares_available + EPSILON:
                raise MarketError(f"Only {star.shares_available:g} shares of {star.name} are available")
            if cost > player.cash + EPSILON:
                raise MarketError("Not enough cash")
            player.cash = max(player.cash - cost, 0.0)
            player.holdings[star.id] = player.holdings.get(star.id, 0.0) + qty
            star.shares_held += qty
        elif side == "sell":
            held = player.holdings.get(star.id, 0.0)
            if qty > held + EPSILON:
                raise MarketError(f"You only hold {held:g} shares of {star.name}")
            qty = min(qty, held)
            player.cash += qty * star.price
            remaining = held - qty
            if remaining > EPSILON:
                player.holdings[star.id] = remaining
            else:
                del player.holdings[star.id]
            star.shares_held = max(star.shares_held - qty, 0.0)
        else:
            raise MarketError("Side must be 'buy' or 'sell'")

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
