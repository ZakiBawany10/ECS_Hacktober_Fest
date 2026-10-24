"""Stellar lifecycle: luminosity bounds, stage durations and the path each star takes."""

import math
import random
from typing import Literal

from . import config

Stage = Literal[
    "main_sequence",
    "red_giant",
    "blue_giant",
    "red_hypergiant",
    "blue_hypergiant",
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


def _from_shifted_log(low: float, high: float) -> tuple[float, float]:
    """L/L☉ bounds from the doc's log10(L/L☉) + 5 values, which are price / 100."""
    offset = config.LOG_LUMINOSITY_OFFSET
    return (10 ** (low - offset), 10 ** (high - offset))


# L/L☉ bounds for each stage after the main sequence. Black holes have none: see DARK_STAGES.
STAGE_L_BOUNDS: dict[Stage, tuple[float, float]] = {
    # Table 4 of docs/main_sequence_pricing_data.md.
    "red_giant": _from_shifted_log(6.00, 9.00),
    "blue_giant": _from_shifted_log(7.00, 11.00),
    # Hypergiants start at or above the top of their main-sequence range, so becoming one is a rally.
    # Table 4's red hypergiant floor (1e5) is already above B's top (4.5e4); blue starts at O's top.
    "red_hypergiant": _from_shifted_log(10.00, 10.70),
    "blue_hypergiant": (MAIN_SEQUENCE_L_BOUNDS["O"][1], _from_shifted_log(10.30, 11.48)[1]),
    # PLACEHOLDER: replace with Rupert's values.
    "supernova": (1e9, 1e10),
    "planetary_nebula": (1e3, 1e4),
    "white_dwarf": (1e-3, 1e-2),
    "neutron_star": (1e-4, 1e-3),
}

# The stages each spectral type passes through, from section 2 of docs/main_sequence_pricing_data.md.
_ENDS_AS_WHITE_DWARF: list[Stage] = ["planetary_nebula", "white_dwarf"]
LIFECYCLE_PATHS: dict[str, list[Stage]] = {
    "O": ["main_sequence", "blue_hypergiant", "supernova", "black_hole"],
    "B": ["main_sequence", "red_hypergiant", "supernova", "neutron_star"],
    "A": ["main_sequence", "blue_giant", *_ENDS_AS_WHITE_DWARF],
    "F": ["main_sequence", "blue_giant", *_ENDS_AS_WHITE_DWARF],
    "G": ["main_sequence", "red_giant", *_ENDS_AS_WHITE_DWARF],
    "K": ["main_sequence", "red_giant", *_ENDS_AS_WHITE_DWARF],
    "M": ["main_sequence", "red_giant", *_ENDS_AS_WHITE_DWARF],
}

# Stage durations in real seconds, compressed for a ~20 minute session. Hotter types burn out sooner.
MAIN_SEQUENCE_SECONDS: dict[str, tuple[float, float]] = {
    "O": (180, 300),
    "B": (240, 360),
    "A": (480, 720),
    "F": (480, 720),
    "G": (600, 900),
    "K": (600, 900),
    "M": (600, 900),
}
# None means the stage is terminal.
STAGE_SECONDS: dict[Stage, tuple[float, float] | None] = {
    "red_giant": (120, 180),
    "blue_giant": (120, 180),
    "red_hypergiant": (60, 120),
    "blue_hypergiant": (60, 120),
    "supernova": (10, 15),
    "planetary_nebula": (45, 60),
    "white_dwarf": None,
    "neutron_star": None,
    "black_hole": None,
}

# Stages whose luminosity jumps straight to the new value instead of easing towards it.
SNAP_STAGES: set[Stage] = {"supernova"}

# Stages with no luminosity: L and price sit at 0 and don't twinkle.
DARK_STAGES: set[Stage] = {"black_hole"}


def generate_luminosity(bounds: tuple[float, float], rng: random.Random) -> float:
    """Pick an L within bounds, uniform in log10(L) so every order of magnitude is equally likely."""
    low, high = bounds
    return 10 ** rng.uniform(math.log10(low), math.log10(high))


def next_stage(stage: Stage, spectral_type: str) -> Stage | None:
    path = LIFECYCLE_PATHS[spectral_type]
    i = path.index(stage)
    return path[i + 1] if i + 1 < len(path) else None


def stage_seconds(stage: Stage, spectral_type: str) -> tuple[float, float] | None:
    if stage == "main_sequence":
        return MAIN_SEQUENCE_SECONDS[spectral_type]
    return STAGE_SECONDS[stage]


def seconds_to_ticks(seconds: float) -> int:
    return max(round(seconds / config.TICK_SECONDS), 1)


def roll_duration_ticks(stage: Stage, spectral_type: str, rng: random.Random) -> int | None:
    """Ticks until the star leaves this stage, or None if it never does."""
    seconds = stage_seconds(stage, spectral_type)
    if seconds is None:
        return None
    return seconds_to_ticks(rng.uniform(*seconds))
