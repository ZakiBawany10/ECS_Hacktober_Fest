import math
import random
from dataclasses import dataclass

from . import config


def price_from_luminosity(L: float) -> float:
    """Share price from luminosity in solar units, rounded to 2 decimal places. No light, no value."""
    if L <= 0:
        return 0.0
    price = config.PRICE_SCALE * (math.log10(L) + config.LOG_LUMINOSITY_OFFSET)
    return round(max(price, 0.0), 2)


def luminosity_from_price(price: float) -> float:
    """The L/L☉ a luminosity price corresponds to: the inverse of price_from_luminosity."""
    return 10 ** (price / config.PRICE_SCALE - config.LOG_LUMINOSITY_OFFSET)


def market_price(L: float, impact: float) -> float:
    """Luminosity price adjusted by trading pressure, rounded to 2 decimal places."""
    return round(price_from_luminosity(L) * impact, 2)


def apply_impact(impact: float, side: str, value: float) -> float:
    """Return the price multiplier after a trade worth `value`, kept within 1 ± IMPACT_CAP."""
    nudge = config.IMPACT_PER_10K * value / 10_000
    impact += nudge if side == "buy" else -nudge
    return min(max(impact, 1 - config.IMPACT_CAP), 1 + config.IMPACT_CAP)


def decay_impact(impact: float) -> float:
    """Return the price multiplier after one tick of easing back towards 1."""
    return 1 + (impact - 1) * (1 - config.IMPACT_DECAY)


def twinkle(L: float, base_L: float, rng: random.Random) -> float:
    """Return L after one tick of mean-reverting noise around base_L."""
    log_L = math.log10(L)
    log_L += config.TWINKLE_REVERSION * (math.log10(base_L) - log_L)
    log_L += rng.gauss(0.0, config.TWINKLE_SIGMA)
    return 10**log_L


@dataclass
class PriceLeg:
    """A straight-line move in luminosity price from start_price at start_tick to end_price at end_tick."""

    start_tick: int
    start_price: float
    end_tick: int
    end_price: float


def path_price(path: list[PriceLeg], tick: int) -> float:
    """The luminosity price a scripted path gives at tick. It holds the final price once the path ends."""
    for leg in path:
        if tick <= leg.end_tick:
            progress = max(tick - leg.start_tick, 0) / (leg.end_tick - leg.start_tick)
            return leg.start_price + (leg.end_price - leg.start_price) * progress
    return path[-1].end_price
