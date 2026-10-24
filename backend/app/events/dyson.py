"""Section 5.1: aliens enclose a star in a Dyson sphere. Its light, and so its price, slides away.

The outcome is rolled at the start and kept on the server: 20% of builds complete and leave the star
at ~3% of its price, and 80% are abandoned partway, when the price rallies back. Builds can stall
either way, so a pause isn't a giveaway.
"""

import math
import random
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .. import config
from ..lifecycle import Stage
from ..newsroom import OUTLETS, OUTLETS_BY_NAME, percent, reported_progress
from .base import EasingEvent

if TYPE_CHECKING:
    from ..market import Market, Star

BUILD_SECONDS = 300.0
DYSON_DIMMING = 0.97  # a finished sphere hides 97% of the light: price ≈ 3% of baseline
DYSON_TAU = 3.0
ABANDON_TAU = 5.0  # the multiplier snaps back: a sharp rally within ~15 s
COMPLETE_CHANCE = 0.2
ABANDON_PROGRESS = (0.15, 0.85)  # where an abandoned build stops
STALLS = (0, 2)  # pauses per build
STALL_SECONDS = (15.0, 30.0)
UPDATE_SECONDS = (20.0, 30.0)  # between progress reports
HINT_SECONDS = 30.0  # Free Xeno Press may hint at trouble this long before an abandonment
HINT_CHANCE = 0.5
MAX_BUILDING = 2  # Dyson spheres under construction at once
DYSON_STAGES: set[Stage] = {"main_sequence", "red_giant", "blue_giant", "red_hypergiant", "blue_hypergiant"}
LEAKER = "Free Xeno Press"  # first to report stalls, and the only one to hint at abandonment


def build_progress(build_seconds: float) -> float:
    """Front-loaded: fast at first, slowing as more gets built."""
    return 1 - (1 - min(build_seconds / BUILD_SECONDS, 1.0)) ** 2


def seconds_to_reach(progress: float) -> float:
    return BUILD_SECONDS * (1 - math.sqrt(1 - progress))


@dataclass
class DysonSphere(EasingEvent):
    major = True

    completes: bool = False
    stop_progress: float = 1.0
    stalls: list[tuple[int, int]] = field(default_factory=list)  # (build tick it starts at, length in ticks)
    start_value: float = 1.0  # the multiplier's starting value, so a sphere growing out of a dimming doesn't jump
    phase: str = "building"  # building, complete, abandoned or destroyed
    build_ticks: int = 0
    stall_left: int = 0
    next_update_tick: int = 0
    last_progress: float = 0.0  # at the previous report, for outlets that lag
    start_stage: Stage = "main_sequence"
    origin: str = ""  # extra context for the start news

    @property
    def counts_towards_cap(self) -> bool:
        return self.phase == "building"

    @property
    def progress(self) -> float:
        return build_progress(self.build_ticks * config.TICK_SECONDS)

    def start(self, market: "Market") -> None:
        star = self.star(market)
        self.start_stage = star.stage
        self.set_target(market, 1.0, DYSON_TAU)
        self.multiplier(market).value = self.start_value
        self.next_update_tick = market.tick + self._update_gap(market.rng)
        self.report(market, "start", flash=True, origin=self.origin)

    def tick(self, market: "Market") -> bool:
        star = self.star(market)
        if self.phase in ("building", "complete") and star.stage != self.start_stage:
            # The star swelled or exploded, tearing the sphere apart: the light comes back.
            self.phase = "destroyed"
            self.set_target(market, 1.0, ABANDON_TAU)
            self.report(market, "destroyed", flash=True)
        if self.phase == "building":
            self._build(market)
        if self.phase in ("abandoned", "destroyed"):
            return self.released_once_settled(market)
        return False

    def _build(self, market: "Market") -> None:
        if self.stall_left > 0:
            self.stall_left -= 1
        elif self.stalls and self.stalls[0][0] <= self.build_ticks:
            self.stall_left = self.stalls.pop(0)[1] - 1  # this tick is the first of the stall
            # The leaker breaks it; the other outlets mention it in their next progress update.
            self.report(market, "stall", outlet=LEAKER)
        else:
            self.build_ticks += 1
        progress = self.progress
        if not self.completes and progress >= self.stop_progress:
            self.phase = "abandoned"
            self.set_target(market, 1.0, ABANDON_TAU)
            self.report(market, "abandoned", flash=True)
        elif progress >= 1.0:
            self.phase = "complete"
            self.set_target(market, 1 - DYSON_DIMMING, DYSON_TAU)
            self.report(market, "complete", flash=True)
        else:
            self.set_target(market, 1 - DYSON_DIMMING * progress, DYSON_TAU)
            if market.tick >= self.next_update_tick:
                self._report_progress(market)

    def _report_progress(self, market: "Market") -> None:
        rng = market.rng
        outlet = rng.choice(OUTLETS)
        hint = ""
        if not self.completes and self.stall_left == 0:
            seconds_left = seconds_to_reach(self.stop_progress) - self.build_ticks * config.TICK_SECONDS
            if seconds_left <= HINT_SECONDS and rng.random() < HINT_CHANCE:
                outlet = OUTLETS_BY_NAME[LEAKER]
                hint = "Sources whisper of funding disputes and workforce unrest on the construction crews."
        reported = reported_progress(outlet, self.progress, self.last_progress, rng)
        status = "Construction is paused." if self.stall_left else ""
        self.report(market, "update", outlet=outlet.name, progress=percent(reported), status=status, hint=hint)
        self.last_progress = self.progress
        self.next_update_tick = market.tick + self._update_gap(rng)

    @staticmethod
    def _update_gap(rng: random.Random) -> int:
        return max(round(rng.uniform(*UPDATE_SECONDS) / config.TICK_SECONDS), 1)


def dyson_eligible(star: "Star") -> bool:
    return star.stage in DYSON_STAGES


def create_dyson(star: "Star", tick: int, rng: random.Random, start_value: float = 1.0, origin: str = "") -> DysonSphere:
    completes = rng.random() < COMPLETE_CHANCE
    stalls = []
    for _ in range(rng.randint(*STALLS)):
        at = round(rng.uniform(0.1, 0.9) * BUILD_SECONDS / config.TICK_SECONDS)
        stalls.append((at, max(round(rng.uniform(*STALL_SECONDS) / config.TICK_SECONDS), 1)))
    return DysonSphere(
        id=uuid.uuid4().hex,
        type="dyson_sphere",
        asset_id=star.id,
        t=tick,
        completes=completes,
        stop_progress=1.0 if completes else rng.uniform(*ABANDON_PROGRESS),
        stalls=sorted(stalls),
        start_value=start_value,
        origin=origin,
    )
