import math
import random

from . import config


def price_from_luminosity(L: float) -> float:
    """Share price from luminosity in solar units, rounded to 2 decimal places."""
    price = config.PRICE_SCALE * (math.log10(L) + config.LOG_LUMINOSITY_OFFSET)
    return round(max(price, 0.0), 2)


def twinkle(L: float, base_L: float, rng: random.Random) -> float:
    """Return L after one tick of mean-reverting noise around base_L."""
    log_L = math.log10(L)
    log_L += config.TWINKLE_REVERSION * (math.log10(base_L) - log_L)
    log_L += rng.gauss(0.0, config.TWINKLE_SIGMA)
    return 10**log_L
