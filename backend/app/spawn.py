"""New stars, which appear as protostars (section 3 of docs/main_sequence_pricing_data.md).

A protostar's future is rolled when it spawns and kept on the server. Players see a forecast of its
main-sequence price, which wobbles and narrows as ignition nears but may still be badly wrong: at
ignition the price jumps to the true value.
"""

import random
import re
from dataclasses import dataclass

from .lifecycle import MAIN_SEQUENCE_L_BOUNDS, MAIN_SEQUENCE_MASS_BOUNDS, MAIN_SEQUENCE_TEMPERATURE_BOUNDS
from .pricing import price_from_luminosity

# Every spectral type is equally likely (real galaxies are mostly M stars, which makes a dull market).
SPAWN_TYPES = "OBAFGKM"

# How wrong a forecast is at ignition: usually close, sometimes way off in either direction.
FORECAST_CLOSE_CHANCE = 0.7
FORECAST_CLOSE_ERROR = 0.05  # within ±5% of the true price
FORECAST_WRONG_ERROR = (0.2, 0.4)  # otherwise 20–40% too high or too low
FORECAST_START_SPREAD = 0.15  # extra error at spawn, up to ±15%, which shrinks to nothing by ignition
FORECAST_JITTER = 0.01  # per-tick noise on the forecast

# Used when Gemma hasn't supplied names.
FALLBACK_NAMES = [
    "Vesper", "Halcyon", "Corvid", "Lumen", "Tarn", "Seraph", "Marrow", "Quill", "Ashgrove", "Pellucid",
    "Wren", "Cinder", "Obelus", "Fathom", "Ivory Gate", "Sable", "Kittiwake", "Morrow", "Brine", "Ostara",
    "Thistle", "Calder", "Nimbus", "Gloam", "Juniper", "Rook", "Solace", "Tamsin", "Umber", "Zephyr",
]


def name_key(name: str) -> str:
    """What two star names must not share: "Ivory Gate", "ivory-gate" and "IvoryGate" are the same name."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


@dataclass
class Forecast:
    """A protostar's hidden future, and the public forecast of it."""

    true_L: float  # the main-sequence L it will ignite with
    final_error: float  # how wrong the forecast still is at ignition, as a fraction of the true price
    start_offset: float  # extra error at spawn, gone by ignition
    start_tick: int
    end_tick: int
    first_price: float = 0.0  # the forecast at spawn, for "revised up/down" news

    @property
    def true_price(self) -> float:
        return price_from_luminosity(self.true_L)

    @property
    def midpoint_tick(self) -> int:
        return (self.start_tick + self.end_tick) // 2

    def predicted_price(self, tick: int, rng: random.Random) -> float:
        progress = min(max((tick - self.start_tick) / max(self.end_tick - self.start_tick, 1), 0.0), 1.0)
        error = self.final_error + self.start_offset * (1 - progress) + rng.gauss(0.0, FORECAST_JITTER)
        return max(self.true_price * (1 + error), 0.0)


def roll_forecast(true_L: float, start_tick: int, end_tick: int, rng: random.Random) -> Forecast:
    if rng.random() < FORECAST_CLOSE_CHANCE:
        final_error = rng.uniform(-FORECAST_CLOSE_ERROR, FORECAST_CLOSE_ERROR)
    else:
        final_error = rng.choice((-1, 1)) * rng.uniform(*FORECAST_WRONG_ERROR)
    start_offset = rng.uniform(-FORECAST_START_SPREAD, FORECAST_START_SPREAD)
    forecast = Forecast(true_L, final_error, start_offset, start_tick, end_tick)
    forecast.first_price = forecast.true_price * (1 + final_error + start_offset)
    return forecast


def projected_type(price: float) -> str:
    """The spectral type whose main-sequence price range is nearest to a forecast price."""

    def distance(spectral_type: str) -> float:
        low, high = (price_from_luminosity(L) for L in MAIN_SEQUENCE_L_BOUNDS[spectral_type])
        return max(low - price, 0.0, price - high)

    return min(SPAWN_TYPES, key=distance)


def projected_profile(price: float) -> tuple[str, float, float]:
    """The spectral type, mass and temperature a forecast price suggests: what players see of a protostar."""
    spectral_type = projected_type(price)
    mass = sum(MAIN_SEQUENCE_MASS_BOUNDS[spectral_type]) / 2
    temperature = sum(MAIN_SEQUENCE_TEMPERATURE_BOUNDS[spectral_type]) / 2
    return spectral_type, round(mass, 2), round(temperature, -2)


def ignition_note(forecast: Forecast) -> str:
    """How the forecast compared with the truth, for the news when a protostar ignites."""
    if abs(forecast.final_error) <= FORECAST_CLOSE_ERROR:
        return "Forecasters called it about right."
    if forecast.final_error > 0:
        return "It turned out far dimmer than forecast, so its price fell sharply."
    return "It turned out far brighter than forecast, so its price jumped."
