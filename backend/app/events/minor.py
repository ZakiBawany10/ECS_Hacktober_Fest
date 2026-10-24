"""Section 5.10 minor events: short price blips and a lifecycle nudge."""

import random
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .. import config
from ..lifecycle import STAGE_LABELS, next_stage
from .base import EasingEvent, Event, EventType

if TYPE_CHECKING:
    from ..market import Market, Star

# A pulse eases to its peak with PULSE_ATTACK_TAU, holds for PULSE_HOLD_SECONDS, then eases back to 1.
# Recovering "over ~30 s" means about three taus.
PULSE_ATTACK_TAU = 1.0
PULSE_HOLD_SECONDS = 3.0
METEOR_DROP = (0.03, 0.09)  # price −3% to −9%
METEOR_RECOVERY_TAU = 10.0
FLARE_RISE = (0.12, 0.28)  # price +12% to +28%
FLARE_DECAY_TAU = 6.0
CORONAL_COLLAPSE_CUT = (0.3, 0.6)  # fraction of the stage's remaining time removed
CORONAL_COLLAPSE_STAGES = {"red_giant", "red_hypergiant"}


@dataclass
class Pulse(EasingEvent):
    """A temporary price move: eases to peak, holds, then eases back to 1."""

    peak: float = 1.0
    release_tick: int = 0
    recovery_tau: float = 1.0
    size: str = ""

    def start(self, market: "Market") -> None:
        self.set_target(market, self.peak, PULSE_ATTACK_TAU)
        self.report(market, "start", size=self.size)

    def tick(self, market: "Market") -> bool:
        if market.tick >= self.release_tick and self.multiplier(market).target != 1.0:
            self.set_target(market, 1.0, self.recovery_tau)
        return self.released_once_settled(market)


@dataclass
class CoronalCollapse(Event):
    """Brings a red giant's next stage forward."""

    cut: float = 0.0

    def start(self, market: "Market") -> None:
        star = self.star(market)
        assert star.ticks_left is not None
        star.ticks_left = max(round(star.ticks_left * (1 - self.cut)), 1)
        following = next_stage(star.stage, star.spectral_type)
        self.report(market, "start", next_stage=STAGE_LABELS[following] if following else "remnant")


def minor_eligible(event_type: EventType, star: "Star") -> bool:
    if event_type == "stellar_flare":
        return star.stage == "main_sequence"
    if event_type == "coronal_collapse":
        return star.stage in CORONAL_COLLAPSE_STAGES and star.ticks_left is not None and star.ticks_left > 1
    return True


def create_minor(event_type: EventType, star: "Star", tick: int, rng: random.Random) -> Event:
    base = {"id": uuid.uuid4().hex, "type": event_type, "asset_id": star.id, "t": tick}
    release_tick = tick + round(PULSE_HOLD_SECONDS / config.TICK_SECONDS)
    if event_type == "meteor_strike":
        drop = rng.uniform(*METEOR_DROP)
        size = "heavy" if drop > sum(METEOR_DROP) / 2 else "light"
        return Pulse(**base, peak=1 - drop, release_tick=release_tick, recovery_tau=METEOR_RECOVERY_TAU, size=size)
    if event_type == "stellar_flare":
        rise = rng.uniform(*FLARE_RISE)
        size = "powerful" if rise > sum(FLARE_RISE) / 2 else "modest"
        return Pulse(**base, peak=1 + rise, release_tick=release_tick, recovery_tau=FLARE_DECAY_TAU, size=size)
    if event_type == "coronal_collapse":
        return CoronalCollapse(**base, cut=rng.uniform(*CORONAL_COLLAPSE_CUT))
    raise ValueError(f"Not a minor event: {event_type!r}")
