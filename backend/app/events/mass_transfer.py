"""Section 5.8: a red giant spills gas onto a main-sequence neighbour. The donor shrinks and the gainer
grows, so their prices move in opposite directions: a pair trade.

Adapted to spectral types: the gainer's brightness follows its mass within its type's range, and if
it outgrows the type it moves up one, onto a shorter-lived path. The donor's loss is a price
multiplier that lasts until it next changes stage. Without positions on the server, the gainer is
picked at random. The amount and duration are rolled at the start.
"""

import random
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .. import config
from .base import Event, Multiplier

if TYPE_CHECKING:
    from ..market import Market, Star

DONOR_STAGES = {"red_giant", "red_hypergiant"}
TRANSFER_FRACTION = (0.10, 0.30)  # of the donor's mass
TRANSFER_SECONDS = (90.0, 150.0)
DONOR_PRICE_LOSS = 0.85  # price falls by this × the fraction of mass lost: 30% of its mass ≈ −25%
DONOR_TAU = 3.0
UPDATE_SECONDS = 30.0
MAX_TRANSFERS = 2  # at once; the doc gives no limit
PAIR_TRADER = "Galactic Financial Times"  # frames it as a pair trade


@dataclass
class MassTransfer(Event):
    major = True

    gainer_id: str = ""
    fraction: float = 0.0
    end_tick: int = 0
    donor_mass: float = 0.0  # at the start
    moved: float = 0.0  # mass moved so far
    next_update_tick: int = 0
    finished: bool = False  # the donor keeps its loss until its next stage change
    donor_stage: str = ""

    @property
    def counts_towards_cap(self) -> bool:
        return not self.finished

    @property
    def asset_ids(self) -> list[str]:
        return [self.asset_id] if self.finished else [self.asset_id, self.gainer_id]

    def start(self, market: "Market") -> None:
        donor, gainer = market.stars[self.asset_id], market.stars[self.gainer_id]
        self.donor_mass, self.donor_stage = donor.mass, donor.stage
        donor.multipliers[self.id] = Multiplier(target=1.0, tau=DONOR_TAU)
        self.next_update_tick = market.tick + round(UPDATE_SECONDS / config.TICK_SECONDS)
        self.report(market, "start", outlet=PAIR_TRADER, also=[gainer.id], gainer=gainer.name)

    def tick(self, market: "Market") -> bool:
        donor = market.stars[self.asset_id]
        if donor.stage != self.donor_stage:
            gainer = market.stars.get(self.gainer_id)
            if not self.finished and gainer is not None:
                self._finish(market, gainer)  # cut short: the donor has moved on
            self.cancel(market)  # a new stage brings a fresh brightness; the loss goes with the old one
            return True
        if self.finished:
            return False
        gainer = market.stars[self.gainer_id]
        if gainer.stage != "main_sequence":
            self._finish(market, gainer)
            return False
        total = self.fraction * self.donor_mass
        step = total / max(self.end_tick - self.t, 1)
        self.moved = min(self.moved + step, total)
        donor.mass = self.donor_mass - self.moved
        donor.multipliers[self.id].target = 1 - DONOR_PRICE_LOSS * self.moved / self.donor_mass
        old_type = gainer.spectral_type
        if market.retype(gainer, gainer.mass + step):
            facts = {"gainer": gainer.name, "old_type": old_type, "new_type": gainer.spectral_type}
            self.report(market, "retyped", flash=True, also=[gainer.id], **facts)
        if market.tick >= self.end_tick:
            self._finish(market, gainer)
        elif market.tick >= self.next_update_tick:
            self.next_update_tick = market.tick + round(UPDATE_SECONDS / config.TICK_SECONDS)
            self.report(market, "update", also=[gainer.id], gainer=gainer.name)
        return False

    def _finish(self, market: "Market", gainer: "Star") -> None:
        self.finished = True
        self.report(market, "ended", also=[gainer.id], gainer=gainer.name)


def donor_eligible(star: "Star") -> bool:
    return star.stage in DONOR_STAGES


def gainers(star: "Star", market: "Market") -> list["Star"]:
    return [
        other
        for other in market.stars.values()
        if other.id != star.id and other.listed and other.stage == "main_sequence" and not market.has_major_event(other)
    ]


def create_transfer(donor: "Star", gainer: "Star", tick: int, rng: random.Random) -> MassTransfer:
    duration = round(rng.uniform(*TRANSFER_SECONDS) / config.TICK_SECONDS)
    return MassTransfer(
        id=uuid.uuid4().hex,
        type="mass_transfer",
        asset_id=donor.id,
        t=tick,
        gainer_id=gainer.id,
        fraction=rng.uniform(*TRANSFER_FRACTION),
        end_tick=tick + duration,
    )
