"""Stellar lifecycle: luminosity bounds, stage durations and the path each star takes."""

import math
import random
from typing import Literal

from . import config

Stage = Literal[
    "main_sequence",
    "red_giant",
    "red_supergiant",
    "supernova",
    "planetary_nebula",
    "white_dwarf",
    "neutron_star",
    "black_hole",
]

# Main-sequence L/L☉ bounds by spectral type, from Table 1 of docs/main_sequence_pricing_data.md.
MAIN_SEQUENCE_L_BOUNDS: dict[str, tuple[float, float]] = {
    "O": (5e4, 7e5),
    "B": (60.0, 4.5e4),
    "A": (8.0, 40.0),
    "F": (1.5, 7.2),
    "G": (0.55, 1.35),
    "K": (0.08, 0.46),
    "M": (3e-4, 0.07),
}

# PLACEHOLDER: replace with Rupert's values. L/L☉ bounds for each stage after the main sequence.
STAGE_L_BOUNDS: dict[Stage, tuple[float, float]] = {
    "red_giant": (1e2, 1e3),
    "red_supergiant": (1e5, 5e5),
    "supernova": (1e9, 1e10),
    "planetary_nebula": (1e3, 1e4),
    "white_dwarf": (1e-3, 1e-2),
    "neutron_star": (1e-4, 1e-3),
    "black_hole": (1e-5, 1e-5),
}

# Stage durations in real seconds, compressed for a ~20 minute session. None means the stage is terminal.
STAGE_SECONDS: dict[Stage, tuple[float, float] | None] = {
    "red_giant": (120, 180),
    "red_supergiant": (60, 120),
    "supernova": (10, 15),
    "planetary_nebula": (45, 60),
    "white_dwarf": None,
    "neutron_star": None,
    "black_hole": None,
}

# Stages whose luminosity jumps straight to the new value instead of easing towards it.
SNAP_STAGES: set[Stage] = {"supernova"}

MASSIVE_STAR_MASS = 8.0  # at or above this, a star ends in a supernova
BLACK_HOLE_MASS = 22.0  # at or above this, a supernova leaves a black hole
RED_DWARF_MASS = 0.5  # below this, a star stays on the main sequence for the whole session


def generate_luminosity(bounds: tuple[float, float], rng: random.Random) -> float:
    """Pick an L within bounds, uniform in log10(L) so every order of magnitude is equally likely."""
    low, high = bounds
    return 10 ** rng.uniform(math.log10(low), math.log10(high))


def next_stage(stage: Stage, mass: float) -> Stage | None:
    if stage == "main_sequence":
        if mass >= MASSIVE_STAR_MASS:
            return "red_supergiant"
        return "red_giant" if mass >= RED_DWARF_MASS else None
    if stage == "red_supergiant":
        return "supernova"
    if stage == "supernova":
        return "black_hole" if mass >= BLACK_HOLE_MASS else "neutron_star"
    if stage == "red_giant":
        return "planetary_nebula"
    if stage == "planetary_nebula":
        return "white_dwarf"
    return None


def stage_seconds(stage: Stage, mass: float) -> tuple[float, float] | None:
    if stage == "main_sequence":
        if mass >= MASSIVE_STAR_MASS:
            return (180, 300)
        return (600, 900) if mass >= RED_DWARF_MASS else None
    return STAGE_SECONDS[stage]


def seconds_to_ticks(seconds: float) -> int:
    return max(round(seconds / config.TICK_SECONDS), 1)


def roll_duration_ticks(stage: Stage, mass: float, rng: random.Random) -> int | None:
    """Ticks until the star leaves this stage, or None if it never does."""
    seconds = stage_seconds(stage, mass)
    if seconds is None:
        return None
    return seconds_to_ticks(rng.uniform(*seconds))
