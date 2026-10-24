"""Who reports the news, and how each source bends the numbers (section 5.0.5 of the pricing doc).

Code works out the facts, including the slanted figure each outlet reports; Gemma only writes the words.
"""

import random
from dataclasses import dataclass
from typing import Literal

NewsKind = Literal["lifecycle", "event", "rumour", "system"]
Side = Literal["human", "alien"]


@dataclass(frozen=True)
class Outlet:
    name: str
    side: Side
    voice: str  # how Gemma should write as this outlet
    progress_bias: tuple[float, float] = (0.0, 0.0)  # added to the true progress it reports
    lags: bool = False  # reports the previous update's progress


OUTLETS = [
    Outlet(
        "Galactic Financial Times",
        "human",
        "You are measured and market-focused, like a serious financial paper: calm, precise, about what it means for investors.",
        lags=True,
    ),
    Outlet(
        "StarWire",
        "human",
        "You are a fast, sensational tabloid: breathless, exaggerated, fond of exclamation marks and puns.",
        progress_bias=(0.05, 0.15),
    ),
    Outlet(
        "Orbital Observatory Bulletin",
        "human",
        "You are a cautious scientific bulletin: you explain the astrophysics plainly and hedge ('data suggests...').",
        progress_bias=(-0.03, 0.03),
    ),
    Outlet(
        "Zr'kth Construction Authority",
        "alien",
        "You are the official state feed of the Zr'kth, an alien empire of builders. Write like an imperial "
        "ministry: grandiose propaganda that presents every event as part of the Zr'kth's grand design, calls "
        "humans 'carbon traders', and praises 'the glorious Zr'kth'.",
        progress_bias=(0.05, 0.15),
    ),
    Outlet(
        "Free Xeno Press",
        "alien",
        "You are a dissident alien underground press: sceptical and sardonic. You call the Zr'kth 'the "
        "regime', distrust human markets too, and always point out what could go wrong.",
        progress_bias=(-0.10, -0.05),
    ),
]
OUTLETS_BY_NAME = {outlet.name: outlet for outlet in OUTLETS}

# Reported figures stay within this of the truth, and never claim an outcome that hasn't happened.
MAX_REPORTING_ERROR = 0.15
MAX_UNFINISHED_PROGRESS = 0.95


def reported_progress(outlet: Outlet, true: float, previous: float, rng: random.Random) -> float:
    """The progress (0–1) an outlet reports, slanted by its bias but within MAX_REPORTING_ERROR of the truth."""
    reported = previous if outlet.lags else true + rng.uniform(*outlet.progress_bias)
    reported = min(max(reported, true - MAX_REPORTING_ERROR), true + MAX_REPORTING_ERROR)
    return min(max(reported, 0.0), MAX_UNFINISHED_PROGRESS)


def percent(progress: float) -> str:
    """A progress figure for news text, rounded to the nearest 5%."""
    return f"{round(progress * 20) * 5}%"
