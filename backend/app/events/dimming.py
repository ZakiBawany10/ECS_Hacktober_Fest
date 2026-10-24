"""Section 5.6: a star dims in strange dips, like Tabby's star. Dust, or something being built?

The cause is rolled at the start and kept on the server. Dust (85%) dips at random and clears. An early
Dyson sphere (15%) dips deeper and more regularly each time, then turns into a full Dyson sphere.
"""

import random
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .. import config
from .base import EasingEvent

if TYPE_CHECKING:
    from ..market import Market, Star

DIMMING_SECONDS = (60.0, 120.0)
DIPS = (3, 5)
DIP_DEPTH = (0.06, 0.14)  # price −6% to −14%
DIP_SECONDS = (5.0, 15.0)
DYSON_DIP_SECONDS = 10.0  # an early Dyson sphere's dips are evenly spaced and the same length
DIP_TAU = 1.5
RECOVERY_TAU = 3.0  # back to baseline within ~15 s
EARLY_DYSON_CHANCE = 0.15
MAX_DIMMING = 1  # at once
SPECULATORS = ("StarWire", "Orbital Observatory Bulletin")  # one leans "aliens!", the other "likely dust"


@dataclass
class MysteriousDimming(EasingEvent):
    major = True

    early_dyson: bool = False
    dips: list[tuple[int, int, float]] = field(default_factory=list)  # (start tick, end tick, depth)
    end_tick: int = 0
    reported_midway: bool = False
    ended: bool = False

    def start(self, market: "Market") -> None:
        self.set_target(market, 1.0, RECOVERY_TAU)
        self.report(market, "start")

    def tick(self, market: "Market") -> bool:
        if self.ended:
            return self.released_once_settled(market)
        tick = market.tick
        dip = next((depth for start, end, depth in self.dips if start <= tick < end), None)
        if dip is None:
            self.set_target(market, 1.0, RECOVERY_TAU)
        else:
            self.set_target(market, 1 - dip, DIP_TAU)
        if not self.reported_midway and tick >= (self.t + self.end_tick) // 2:
            self.reported_midway = True
            self.report(market, "update", outlet=market.rng.choice(SPECULATORS))
        if tick < self.end_tick:
            return False
        self.ended = True
        if self.early_dyson and market.can_start_dyson():
            # The dimming was construction all along: hand over to a Dyson sphere at today's price.
            value = self.multiplier(market).value
            self.release(market)
            market.follow_up(self.asset_id, start_value=value)
            return True
        self.set_target(market, 1.0, RECOVERY_TAU)
        self.report(market, "cleared")
        return False


def dimming_eligible(star: "Star") -> bool:
    return star.stage == "main_sequence"


def create_dimming(star: "Star", tick: int, rng: random.Random, early_dyson_possible: bool) -> MysteriousDimming:
    early_dyson = early_dyson_possible and rng.random() < EARLY_DYSON_CHANCE
    length = round(rng.uniform(*DIMMING_SECONDS) / config.TICK_SECONDS)
    count = rng.randint(*DIPS)
    slot = length // count
    dips = []
    for i in range(count):
        if early_dyson:
            # Evenly spaced, each deeper than the last: a pattern sharp players can spot.
            dip_ticks = round(DYSON_DIP_SECONDS / config.TICK_SECONDS)
            start = tick + i * slot + (slot - dip_ticks) // 2
            depth = DIP_DEPTH[0] + (DIP_DEPTH[1] - DIP_DEPTH[0]) * i / max(count - 1, 1)
        else:
            dip_ticks = min(round(rng.uniform(*DIP_SECONDS) / config.TICK_SECONDS), slot)
            start = tick + i * slot + rng.randint(0, slot - dip_ticks)
            depth = rng.uniform(*DIP_DEPTH)
        dips.append((start, start + dip_ticks, depth))
    return MysteriousDimming(
        id=uuid.uuid4().hex,
        type="mysterious_dimming",
        asset_id=star.id,
        t=tick,
        early_dyson=early_dyson,
        dips=dips,
        end_tick=tick + length,
    )
