"""Section 5.10's alien signal: a rumour that may be false.

Code rolls whether it's true and keeps that on the server. A true signal moves the price; a false one
moves nothing physical, so any price move comes from players trading on it. Either way a "confirmed"
or "debunked" item follows. Gemma is told the truth so it can write a convincing story either way.
"""

import random
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar

from .. import config
from ..newsroom import NewsKind
from .base import EasingEvent

if TYPE_CHECKING:
    from ..market import Market

TRUE_CHANCE = 0.7
EFFECT = (0.05, 0.10)  # a true signal moves the price ±5–10%
EFFECT_TAU = 5.0
FADE_TAU = 10.0  # after it's confirmed, the move fades
REVEAL_SECONDS = (45.0, 75.0)
FLAVOURS = {
    1: "Some say it's a message from a friendly civilisation, which would make the star far more valuable.",
    -1: "Some fear it's a warning beacon, a sign of danger around the star.",
}


@dataclass
class AlienSignal(EasingEvent):
    news_kind: ClassVar[NewsKind] = "rumour"

    is_true: bool = True  # server-only: never sent to clients
    direction: int = 1
    size: float = 0.0
    reveal_tick: int = 0
    revealed: bool = False

    def start(self, market: "Market") -> None:
        if self.is_true:
            self.set_target(market, 1 + self.direction * self.size, EFFECT_TAU)
        secret = (
            f"Secret, for you only: the signal is {'real' if self.is_true else 'a hoax'}. "
            "Write it so readers can't tell either way."
        )
        self.report(market, "start", flavour=FLAVOURS[self.direction], secret=secret)

    def tick(self, market: "Market") -> bool:
        if not self.revealed and market.tick >= self.reveal_tick:
            self.revealed = True
            self.report(market, "confirmed" if self.is_true else "debunked", flash=True)
            if not self.is_true:
                return True
            self.set_target(market, 1.0, FADE_TAU)
        return self.revealed and self.released_once_settled(market)


def create_signal(asset_id: str, tick: int, rng: random.Random) -> AlienSignal:
    reveal = round(rng.uniform(*REVEAL_SECONDS) / config.TICK_SECONDS)
    return AlienSignal(
        id=uuid.uuid4().hex,
        type="alien_signal",
        asset_id=asset_id,
        t=tick,
        is_true=rng.random() < TRUE_CHANCE,
        direction=rng.choice((1, -1)),
        size=rng.uniform(*EFFECT),
        reveal_tick=tick + reveal,
    )
