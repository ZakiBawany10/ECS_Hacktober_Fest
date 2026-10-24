"""Price-moving events from section 5 of docs/main_sequence_pricing_data.md.

Code rolls every number, and every hidden outcome, when an event starts; Gemma only writes the news.
Events move a star's price through named multipliers (section 5.0.3) that ease towards a target, so
the luminosity price from Rupert's formula is left alone.
"""

from typing import TYPE_CHECKING

from ..lifecycle import DARK_STAGES
from .base import EasingEvent, Event, EventNews, EventType, Multiplier
from .civ import civilisation_on, create_civilisation, life_eligible
from .dimming import MAX_DIMMING, create_dimming, dimming_eligible
from .dyson import create_dyson, dyson_eligible
from .mass_transfer import MAX_TRANSFERS, create_transfer, donor_eligible, gainers
from .merger import MAX_MERGERS, create_merger, merger_eligible, merger_partners
from .minor import create_minor, minor_eligible
from .rumour import create_signal

if TYPE_CHECKING:
    from ..market import Market, Star

__all__ = [
    "EVENT_WEIGHTS",
    "MAJOR_TYPES",
    "MAX_MAJOR_EVENTS",
    "MOMENTS",
    "EasingEvent",
    "Event",
    "EventNews",
    "EventType",
    "Multiplier",
    "create_dyson",
    "create_event",
    "eligible",
    "star_weight",
]

# How likely each type is when the scheduler fires, among types with an eligible star (5.0.1).
# The doc gives no weight for coronal collapse.
EVENT_WEIGHTS: dict[EventType, float] = {
    "meteor_strike": 25,
    "stellar_flare": 20,
    "coronal_collapse": 10,
    "mysterious_dimming": 10,
    "dyson_sphere": 4,
    "intelligent_life": 8,
    "alien_signal": 8,  # the doc gives no weight
    "star_merger": 8,
    "mass_transfer": 10,
}
DYSON_CIV_WEIGHT = 5  # a spacefaring civilisation's star is this much likelier to get a Dyson sphere

# Major events: at most MAX_MAJOR_EVENTS at once across the market, and one per star.
MAJOR_TYPES: set[EventType] = {"mysterious_dimming", "dyson_sphere", "star_merger", "mass_transfer"}
MAX_MAJOR_EVENTS = 4

# The news moments each event can report. Every one needs a note and a fallback in app/ai/prompts.py.
MOMENTS: dict[EventType, set[str]] = {
    "meteor_strike": {"start"},
    "stellar_flare": {"start"},
    "coronal_collapse": {"start"},
    "mysterious_dimming": {"start", "update", "cleared"},
    "dyson_sphere": {"start", "update", "stall", "abandoned", "complete", "destroyed"},
    "intelligent_life": {"start", "level_up", "silent", "sterilised", "migrated", "extinct"},
    "alien_signal": {"start", "confirmed", "debunked"},
    "star_merger": {"start", "update", "merged", "near_miss", "called_off"},
    "mass_transfer": {"start", "update", "retyped", "ended"},
}


def partners(event_type: EventType, star: "Star", market: "Market") -> list["Star"]:
    """The stars a two-star event could pair this one with."""
    if event_type == "star_merger":
        return merger_partners(star, market)
    if event_type == "mass_transfer":
        return gainers(star, market)
    return []


def eligible(
    event_type: EventType, star: "Star", market: "Market", director: bool = False, partner: "Star | None" = None
) -> bool:
    """Whether the event can start on this star now (with this partner, for two-star events). The
    director skips the market-wide limits."""
    if not star.listed or star.stage in DARK_STAGES or star.stage == "protostar":
        return False
    if event_type in MAJOR_TYPES:
        if market.has_major_event(star):
            return False
        if not director and market.major_event_count() >= MAX_MAJOR_EVENTS:
            return False
    if event_type == "dyson_sphere":
        return dyson_eligible(star) and (director or market.can_start_dyson())
    if event_type == "mysterious_dimming":
        return dimming_eligible(star) and (director or market.event_count("mysterious_dimming") < MAX_DIMMING)
    if event_type == "intelligent_life":
        return life_eligible(star, market)
    if event_type == "alien_signal":
        return not any(e.type == "alien_signal" and e.asset_id == star.id for e in market.events.values())
    if event_type in ("star_merger", "mass_transfer"):
        fits = merger_eligible(star) if event_type == "star_merger" else donor_eligible(star)
        limit = MAX_MERGERS if event_type == "star_merger" else MAX_TRANSFERS
        options = partners(event_type, star, market)
        paired = partner in options if partner else bool(options)
        return fits and paired and (director or market.event_count(event_type) < limit)
    return minor_eligible(event_type, star)


def star_weight(event_type: EventType, star: "Star", market: "Market") -> float:
    """How likely this star is to be picked, once the scheduler has chosen an event type."""
    if event_type == "dyson_sphere":
        civ = civilisation_on(star, market)
        return DYSON_CIV_WEIGHT if civ and civ.level == 3 else 1
    return 1


def create_event(event_type: EventType, star: "Star", market: "Market", partner: "Star | None" = None) -> Event:
    """Roll a new event's numbers and hidden outcome. The caller checks eligibility and calls start()."""
    if event_type in ("star_merger", "mass_transfer"):
        partner = partner or market.rng.choice(partners(event_type, star, market))
        create = create_merger if event_type == "star_merger" else create_transfer
        return create(star, partner, market.tick, market.rng)
    if event_type == "dyson_sphere":
        return create_dyson(star, market.tick, market.rng)
    if event_type == "mysterious_dimming":
        return create_dimming(star, market.tick, market.rng, early_dyson_possible=market.can_start_dyson())
    if event_type == "intelligent_life":
        return create_civilisation(star, market.tick)
    if event_type == "alien_signal":
        return create_signal(star.id, market.tick, market.rng)
    return create_minor(event_type, star, market.tick, market.rng)
