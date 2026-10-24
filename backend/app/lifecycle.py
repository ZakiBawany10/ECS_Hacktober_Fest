"""Stellar lifecycle: luminosity bounds, stage durations and the path each star takes."""

import math
import random
from typing import Literal

from . import config

Stage = Literal[
    "protostar",
    "main_sequence",
    "red_giant",
    "blue_giant",
    "red_hypergiant",
    "blue_hypergiant",
    "supernova",
    "white_dwarf",
    "neutron_star",
    "black_hole",
]

# How stages are written in news text.
STAGE_LABELS: dict[Stage, str] = {
    "protostar": "protostar",
    "main_sequence": "main-sequence star",
    "red_giant": "red giant",
    "blue_giant": "blue giant",
    "red_hypergiant": "red hypergiant",
    "blue_hypergiant": "blue hypergiant",
    "supernova": "supernova",
    "white_dwarf": "white dwarf",
    "neutron_star": "neutron star",
    "black_hole": "black hole",
}

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


# Main-sequence temperature (K) and mass (M☉) by spectral type, also from Table 1. Temperature is
# display only; mass decides what a merger or mass transfer turns a star into.
MAIN_SEQUENCE_TEMPERATURE_BOUNDS: dict[str, tuple[float, float]] = {
    "O": (32_000, 45_000),
    "B": (10_000, 31_000),
    "A": (7_400, 9_700),
    "F": (6_000, 7_200),
    "G": (5_400, 5_900),
    "K": (3_900, 5_300),
    "M": (2_400, 3_900),
}
MAIN_SEQUENCE_MASS_BOUNDS: dict[str, tuple[float, float]] = {
    "O": (19, 60),
    "B": (2.7, 18),
    "A": (1.75, 2.2),
    "F": (1.1, 1.6),
    "G": (0.90, 1.06),
    "K": (0.59, 0.88),
    "M": (0.08, 0.57),
}


def _from_shifted_log(low: float, high: float) -> tuple[float, float]:
    """L/L☉ bounds from the doc's log10(L/L☉) + 5 values, which are price / 100."""
    offset = config.LOG_LUMINOSITY_OFFSET
    return (10 ** (low - offset), 10 ** (high - offset))


# L/L☉ bounds for each stage after the main sequence. A supernova's price follows a scripted path
# instead (see SUPERNOVA_PEAK), and black holes have no light (see DARK_STAGES).
STAGE_L_BOUNDS: dict[Stage, tuple[float, float]] = {
    # Table 4 of docs/main_sequence_pricing_data.md.
    "red_giant": _from_shifted_log(6.00, 9.00),
    "blue_giant": _from_shifted_log(7.00, 11.00),
    # Hypergiants start at or above the top of their main-sequence range, so becoming one is a rally.
    # Table 4's red hypergiant floor (1e5) is already above B's top (4.5e4); blue starts at O's top.
    "red_hypergiant": _from_shifted_log(10.00, 10.70),
    "blue_hypergiant": (MAIN_SEQUENCE_L_BOUNDS["O"][1], _from_shifted_log(10.30, 11.48)[1]),
    # Table 5 of docs/main_sequence_pricing_data.md.
    "white_dwarf": _from_shifted_log(0.00, 7.00),
    "neutron_star": _from_shifted_log(0.00, 6.00),
}

# The stages each spectral type passes through, from sections 2 to 4 of
# docs/main_sequence_pricing_data.md. G, K and M skip the supernova and go straight to their remnant.
# Spawned stars start as protostars; the seeded ones start on the main sequence.
LIFECYCLE_PATHS: dict[str, list[Stage]] = {
    "O": ["protostar", "main_sequence", "blue_hypergiant", "supernova", "black_hole"],
    "B": ["protostar", "main_sequence", "red_hypergiant", "supernova", "black_hole"],
    "A": ["protostar", "main_sequence", "blue_giant", "supernova", "neutron_star"],
    "F": ["protostar", "main_sequence", "blue_giant", "supernova", "neutron_star"],
    "G": ["protostar", "main_sequence", "red_giant", "white_dwarf"],
    "K": ["protostar", "main_sequence", "red_giant", "white_dwarf"],
    "M": ["protostar", "main_sequence", "red_giant", "white_dwarf"],
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
# None means the stage is terminal. A supernova lasts as long as its price path: see SUPERNOVA_PEAK.
STAGE_SECONDS: dict[Stage, tuple[float, float] | None] = {
    "protostar": (60, 90),
    "red_giant": (120, 180),
    "blue_giant": (120, 180),
    "red_hypergiant": (60, 120),
    "blue_hypergiant": (60, 120),
    "white_dwarf": None,
    "neutron_star": None,
    "black_hole": (60, 60),  # then it's delisted
}

# Section 4 price paths, which are straight lines in luminosity price. A supernova jumps to
# SUPERNOVA_PEAK × the star's price, fades slowly to SUPERNOVA_FADE of that peak over
# SUPERNOVA_GLOW_SECONDS, then drops to its remnant's price over SUPERNOVA_DROP_SECONDS. It
# becomes the remnant when the drop ends, so players can still sell on the way down.
SUPERNOVA_PEAK = 3.0
SUPERNOVA_FADE = 0.9
SUPERNOVA_GLOW_SECONDS = (27.0, 33.0)
SUPERNOVA_DROP_SECONDS = 8.0
# Stages entered without a supernova decline from the giant's price to the remnant's price.
DECLINE_STAGES: set[Stage] = {"white_dwarf"}
DECLINE_SECONDS = 45.0

# Dead stars. They don't count towards the limit on stars in play (MAX_LIVING_STARS).
REMNANT_STAGES: set[Stage] = {"white_dwarf", "neutron_star", "black_hole"}

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


def type_for_mass(mass: float) -> str:
    """The spectral type whose main-sequence mass range holds this mass, or the nearest one."""

    def distance(spectral_type: str) -> float:
        low, high = MAIN_SEQUENCE_MASS_BOUNDS[spectral_type]
        return max(low - mass, 0.0, mass - high)

    return min(MAIN_SEQUENCE_MASS_BOUNDS, key=distance)


def luminosity_for_mass(spectral_type: str, mass: float) -> float:
    """Where a mass sits in its type's mass range, mapped to the same place in its L range (in log L)."""
    low_m, high_m = MAIN_SEQUENCE_MASS_BOUNDS[spectral_type]
    low_L, high_L = MAIN_SEQUENCE_L_BOUNDS[spectral_type]
    position = min(max((mass - low_m) / (high_m - low_m), 0.0), 1.0)
    return 10 ** (math.log10(low_L) + position * (math.log10(high_L) - math.log10(low_L)))
