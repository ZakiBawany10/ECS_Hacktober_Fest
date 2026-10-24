"""Section 5.4: life emerges around a star and grows into a civilisation, which markets price in.

It's a long-running state on the star rather than a one-off event, so it doesn't count towards the
major-event limits. It can level up, stall, wipe itself out, be sterilised by a flare, or, when its
star leaves the main sequence, migrate to another star or die out.
"""

import random
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .. import config
from .base import EasingEvent

if TYPE_CHECKING:
    from ..market import Market, Star

LEVELS = {
    1: ("microbial life", 1.05),
    2: ("intelligent life", 1.20),
    3: ("a spacefaring civilisation", 1.45),
}
ADVANCE_CHANCE = {1: 0.6, 2: 0.5}
ROLL_SECONDS = (60.0, 90.0)  # between level-up rolls
ROLLS_PER_LEVEL = 2  # a civilisation that stays gets one more roll, then stays for good
CIV_TAU = 4.0
CRASH_TAU = 2.0  # a sharp drop when life is wiped out
RISK_SECONDS = 60.0
SELF_DESTRUCT_CHANCE = 0.05  # per risk check, at levels 2 and 3
FLARE_STERILISE_CHANCE = 0.3  # a flare on a red dwarf with level 1–2 life
MIGRATE_CHANCE = 0.5  # when the host star leaves the main sequence
MAX_CIVILISATIONS = 3
LIFE_TYPES = {"G", "K", "M"}  # yellow and red dwarfs: blue stars live too briefly for life
SETTLED_SECONDS = 60.0  # a star must have been in its stage this long for life to emerge
ALIEN_OUTLETS = ("Zr'kth Construction Authority", "Free Xeno Press")  # cover alien life from both sides


@dataclass
class Civilisation(EasingEvent):
    level: int = 1
    next_roll_tick: int = 0
    rolls_left: int = ROLLS_PER_LEVEL
    next_risk_tick: int = 0
    ending: bool = False
    migrated: bool = False  # arrived from a dying star

    def start(self, market: "Market") -> None:
        self.set_target(market, LEVELS[self.level][1], CIV_TAU)
        self._schedule_roll(market)
        self.next_risk_tick = market.tick + _ticks(RISK_SECONDS)
        if not self.migrated:
            self.report(market, "start", flash=True, outlet=_outlet(market.rng), life=LEVELS[1][0])

    def tick(self, market: "Market") -> bool:
        if self.ending:
            return self.released_once_settled(market)
        star = self.star(market)
        if star.stage != "main_sequence":
            self._leave_host(market)
            return False
        if market.tick >= self.next_roll_tick and self.level in ADVANCE_CHANCE and self.rolls_left > 0:
            self._roll(market)
        if market.tick >= self.next_risk_tick:
            self.next_risk_tick = market.tick + _ticks(RISK_SECONDS)
            if self.level >= 2 and market.rng.random() < SELF_DESTRUCT_CHANCE:
                self.end(market, "silent")
        return False

    def end(self, market: "Market", moment: str) -> None:
        """Wipe the civilisation out and report it. Its price premium drains away."""
        self.ending = True
        self.set_target(market, 1.0, CRASH_TAU)
        self.report(market, moment, flash=True, outlet=_outlet(market.rng), life=LEVELS[self.level][0])

    def _roll(self, market: "Market") -> None:
        self.rolls_left -= 1
        if market.rng.random() < ADVANCE_CHANCE[self.level]:
            self.level += 1
            self.rolls_left = ROLLS_PER_LEVEL
            self.set_target(market, LEVELS[self.level][1], CIV_TAU)
            self.report(market, "level_up", flash=True, outlet=_outlet(market.rng), life=LEVELS[self.level][0])
        self._schedule_roll(market)

    def _leave_host(self, market: "Market") -> None:
        self.ending = True
        self.set_target(market, 1.0, CIV_TAU)
        life = LEVELS[self.level][0]
        refuges = [star for star in market.stars.values() if refuge(star, market)]
        if refuges and market.rng.random() < MIGRATE_CHANCE:
            new_home = market.rng.choice(refuges)
            settlers = Civilisation(
                id=uuid.uuid4().hex,
                type="intelligent_life",
                asset_id=new_home.id,
                t=market.tick,
                level=self.level,
                migrated=True,
            )
            market.add_event(settlers)
            self.report(market, "migrated", flash=True, also=[new_home.id], life=life, new_home=new_home.name)
        else:
            self.report(market, "extinct", flash=True, outlet=_outlet(market.rng), life=life)

    def _schedule_roll(self, market: "Market") -> None:
        self.next_roll_tick = market.tick + _ticks(market.rng.uniform(*ROLL_SECONDS))


def _ticks(seconds: float) -> int:
    return max(round(seconds / config.TICK_SECONDS), 1)


def _outlet(rng: random.Random) -> str | None:
    """Half the time an alien outlet, otherwise any."""
    return rng.choice(ALIEN_OUTLETS) if rng.random() < 0.5 else None


def civilisation_on(star: "Star", market: "Market") -> Civilisation | None:
    return next(
        (e for e in market.events.values() if isinstance(e, Civilisation) and e.asset_id == star.id and not e.ending),
        None,
    )


def refuge(star: "Star", market: "Market") -> bool:
    """A star life could live on: a listed yellow or red dwarf with no life of its own."""
    return (
        star.listed
        and star.stage == "main_sequence"
        and star.spectral_type in LIFE_TYPES
        and civilisation_on(star, market) is None
    )


def life_eligible(star: "Star", market: "Market") -> bool:
    settled = (market.tick - star.stage_tick) * config.TICK_SECONDS >= SETTLED_SECONDS
    civilisations = sum(isinstance(e, Civilisation) and not e.ending for e in market.events.values())
    return refuge(star, market) and settled and not market.has_major_event(star) and civilisations < MAX_CIVILISATIONS


def flare_strike(star: "Star", market: "Market") -> None:
    """A flare on a red dwarf may sterilise level 1–2 life."""
    civ = civilisation_on(star, market)
    if civ and star.spectral_type == "M" and civ.level <= 2 and market.rng.random() < FLARE_STERILISE_CHANCE:
        civ.end(market, "sterilised")


def create_civilisation(star: "Star", tick: int) -> Civilisation:
    return Civilisation(id=uuid.uuid4().hex, type="intelligent_life", asset_id=star.id, t=tick)
