"""What every event shares: price multipliers, news moments and the Event base class."""

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, ClassVar, Literal

from .. import config
from ..lifecycle import STAGE_LABELS
from ..newsroom import NewsKind

if TYPE_CHECKING:
    from ..market import Market, Star

EventType = Literal[
    "meteor_strike",
    "stellar_flare",
    "coronal_collapse",
    "mysterious_dimming",
    "dyson_sphere",
    "intelligent_life",
    "alien_signal",
]

# A multiplier this close to its target has finished easing.
SETTLED = 0.001


@dataclass
class Multiplier:
    """An event's effect on a star's price. Each tick, value eases towards target with time constant tau."""

    target: float
    tau: float  # seconds
    value: float = 1.0

    def ease(self) -> None:
        self.value += (self.target - self.value) * (1 - math.exp(-config.TICK_SECONDS / self.tau))

    @property
    def settled(self) -> bool:
        return abs(self.value - self.target) < SETTLED


@dataclass
class EventNews:
    """A moment in an event that the news should cover. Code supplies the facts; Gemma writes the words."""

    event_type: EventType
    moment: str  # such as "start", "update" or "abandoned"; see MOMENTS
    asset_ids: list[str]
    facts: dict[str, str]
    t: int
    flash: bool = False  # a key moment, shown as a pop-up banner
    outlet: str | None = None  # the outlet that reports it, or None for a random one
    kind: NewsKind = "event"


@dataclass
class Event:
    id: str
    type: EventType
    asset_id: str
    t: int  # tick it started

    # A major event blocks other major events on its star, and counts towards MAX_MAJOR_EVENTS.
    major: ClassVar[bool] = False
    news_kind: ClassVar[NewsKind] = "event"

    @property
    def counts_towards_cap(self) -> bool:
        return self.major

    def start(self, market: "Market") -> None:
        pass

    def tick(self, market: "Market") -> bool:
        """Advance the event one tick. Return True once it has finished."""
        return True

    def star(self, market: "Market") -> "Star":
        return market.stars[self.asset_id]

    def report(
        self,
        market: "Market",
        moment: str,
        flash: bool = False,
        outlet: str | None = None,
        also: list[str] | None = None,
        **facts: str,
    ) -> None:
        """Queue news about this event. The star's name and stage are always in the facts; `also` lists
        other stars the news is about."""
        star = self.star(market)
        facts = {"name": star.name, "stage": STAGE_LABELS[star.stage], **facts}
        asset_ids = [star.id, *(also or [])]
        news = EventNews(self.type, moment, asset_ids, facts, market.tick, flash, outlet, self.news_kind)
        market.event_news.append(news)


@dataclass
class EasingEvent(Event):
    """An event with one price multiplier, keyed by the event's id."""

    def multiplier(self, market: "Market") -> Multiplier:
        return self.star(market).multipliers[self.id]

    def set_target(self, market: "Market", target: float, tau: float) -> None:
        star = self.star(market)
        if self.id not in star.multipliers:
            star.multipliers[self.id] = Multiplier(target=target, tau=tau)
        multiplier = star.multipliers[self.id]
        multiplier.target, multiplier.tau = target, tau

    def release(self, market: "Market") -> None:
        del self.star(market).multipliers[self.id]

    def released_once_settled(self, market: "Market") -> bool:
        """True, after removing the multiplier, once it has eased back to 1."""
        multiplier = self.multiplier(market)
        if multiplier.target == 1.0 and multiplier.settled:
            self.release(market)
            return True
        return False
