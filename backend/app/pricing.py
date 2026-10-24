import math
import random

from . import config


def price_from_luminosity(L: float) -> float:
    """Share price from luminosity in solar units, rounded to 2 decimal places. No light, no value."""
    if L <= 0:
        return 0.0
    price = config.PRICE_SCALE * (math.log10(L) + config.LOG_LUMINOSITY_OFFSET)
    return round(max(price, 0.0), 2)


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
