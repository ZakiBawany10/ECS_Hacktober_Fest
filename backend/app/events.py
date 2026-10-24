"""Price-moving events from section 5 of docs/main_sequence_pricing_data.md.

Code rolls every number when an event starts; Gemma only writes the news about it. Events move a
star's price through named multipliers (section 5.0.3) that ease towards a target, so the
luminosity price from Rupert's formula is left alone.
"""

import math
import random
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

from . import config
from .lifecycle import DARK_STAGES, STAGE_LABELS, next_stage

if TYPE_CHECKING:
    from .market import Star

EventType = Literal["meteor_strike", "stellar_flare", "coronal_collapse"]

# How likely each type is when the scheduler fires, among types with an eligible star (5.0.1).
# The doc gives no weight for coronal collapse.
EVENT_WEIGHTS: dict[EventType, float] = {
    "meteor_strike": 25,
    "stellar_flare": 20,
    "coronal_collapse": 10,
}

# Section 5.10 minor events. A pulse eases to its peak with PULSE_ATTACK_TAU, holds for
# PULSE_HOLD_SECONDS, then eases back to 1. Recovering "over ~30 s" means about three taus.
PULSE_ATTACK_TAU = 1.0
PULSE_HOLD_SECONDS = 3.0
METEOR_DROP = (0.03, 0.09)  # price −3% to −9%
METEOR_RECOVERY_TAU = 10.0
FLARE_RISE = (0.12, 0.28)  # price +12% to +28%
FLARE_DECAY_TAU = 6.0
CORONAL_COLLAPSE_CUT = (0.3, 0.6)  # fraction of the stage's remaining time removed
CORONAL_COLLAPSE_STAGES = {"red_giant", "red_hypergiant"}

# A multiplier this close to 1 has finished easing back and is removed.
SETTLED = 0.001


@dataclass
class Multiplier:
    """An event's effect on a star's price. Each tick, value eases towards target with time constant tau."""

    target: float
    tau: float  # seconds
    value: float = 1.0

    def ease(self) -> None:
        self.value += (self.target - self.value) * (1 - math.exp(-config.TICK_SECONDS / self.tau))


@dataclass
class Event:
    id: str
    type: EventType
    asset_id: str
    t: int  # tick it started
    facts: dict[str, str] = field(default_factory=dict)  # for the news text; never numbers

    def start(self, star: "Star") -> None:
        pass

    def tick(self, star: "Star", tick: int) -> bool:
        """Advance the event one tick. Return True once it has finished."""
        return True


@dataclass
class Pulse(Event):
    """A temporary price move: eases to peak, holds, then eases back to 1."""

    peak: float = 1.0
    release_tick: int = 0
    recovery_tau: float = 1.0

    def start(self, star: "Star") -> None:
        star.multipliers[self.id] = Multiplier(target=self.peak, tau=PULSE_ATTACK_TAU)

    def tick(self, star: "Star", tick: int) -> bool:
        multiplier = star.multipliers[self.id]
        if tick >= self.release_tick and multiplier.target != 1.0:
            multiplier.target, multiplier.tau = 1.0, self.recovery_tau
        if multiplier.target == 1.0 and abs(multiplier.value - 1.0) < SETTLED:
            del star.multipliers[self.id]
            return True
        return False


@dataclass
class CoronalCollapse(Event):
    """Brings a red giant's next stage forward."""

    cut: float = 0.0

    def start(self, star: "Star") -> None:
        assert star.ticks_left is not None
        star.ticks_left = max(round(star.ticks_left * (1 - self.cut)), 1)


def eligible(event_type: EventType, star: "Star") -> bool:
    if star.stage in DARK_STAGES:
        return False
    if event_type == "stellar_flare":
        return star.stage == "main_sequence"
    if event_type == "coronal_collapse":
        return star.stage in CORONAL_COLLAPSE_STAGES and star.ticks_left is not None and star.ticks_left > 1
    return True


def create_event(event_type: EventType, star: "Star", tick: int, rng: random.Random) -> Event:
    """Roll a new event's numbers. The caller checks eligibility and calls start()."""
    base = {"id": uuid.uuid4().hex, "type": event_type, "asset_id": star.id, "t": tick}
    release_tick = tick + round(PULSE_HOLD_SECONDS / config.TICK_SECONDS)
    if event_type == "meteor_strike":
        drop = rng.uniform(*METEOR_DROP)
        size = "heavy" if drop > sum(METEOR_DROP) / 2 else "light"
        return Pulse(
            **base, facts={"size": size}, peak=1 - drop, release_tick=release_tick, recovery_tau=METEOR_RECOVERY_TAU
        )
    if event_type == "stellar_flare":
        rise = rng.uniform(*FLARE_RISE)
        size = "powerful" if rise > sum(FLARE_RISE) / 2 else "modest"
        return Pulse(
            **base, facts={"size": size}, peak=1 + rise, release_tick=release_tick, recovery_tau=FLARE_DECAY_TAU
        )
    if event_type == "coronal_collapse":
        following = next_stage(star.stage, star.spectral_type)
        label = STAGE_LABELS[following] if following else "remnant"
        return CoronalCollapse(**base, facts={"next_stage": label}, cut=rng.uniform(*CORONAL_COLLAPSE_CUT))
    raise ValueError(f"Unknown event type {event_type!r}")
