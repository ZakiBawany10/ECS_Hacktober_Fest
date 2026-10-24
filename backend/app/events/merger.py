"""Section 5.2: two main-sequence stars spiral together and merge into a bigger, brighter one.

Adapted to spectral types: the survivor (the heavier star) takes the combined mass, which can move it
up a spectral type, onto a shorter-lived path, with the doc's "blue straggler" boost to its light.
Holders of the absorbed star are cashed out at a premium, like shareholders in a takeover (the doc
converts their shares by mass, which loses them money under Rupert's log pricing). Without positions
on the server, the pair is picked at random. The outcome is rolled at the start: 85% merge.
"""

import random
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .. import config
from .base import Event, Multiplier

if TYPE_CHECKING:
    from ..market import Market, Star

MERGE_CHANCE = 0.85
HYPE = 1.05  # both stars, as they're drawn together
HYPE_TAU = 8.0
CONTACT_SECONDS = 25.0  # contact binary from here: volatile
MERGE_SECONDS = 50.0
CONTACT_JITTER = 0.01  # extra per-tick price noise while in contact
JITTER_TAU = 1.0
NEAR_MISS_DIP = 0.97  # a small give-back when the orbits stabilise
NEAR_MISS_TAU = 10.0
NEAR_MISS_RECOVERY_SECONDS = 20.0
STRAGGLER_BOOST = 1.5  # merged stars shine brighter than their mass suggests
CASH_OUT_PREMIUM = 1.2  # what holders of the absorbed star get, × its price
UPDATE_AT = (15.0, 35.0)  # seconds in: orbital decay update, then contact
MAX_MERGERS = 1


@dataclass
class StarMerger(Event):
    major = True

    partner_id: str = ""
    merges: bool = True
    phase: str = "spiral"  # spiral, contact, near_miss
    recovery_tick: int = 0
    updates_sent: int = 0

    @property
    def asset_ids(self) -> list[str]:
        return [self.asset_id, self.partner_id]

    def pair(self, market: "Market") -> list["Star"]:
        return [market.stars[asset_id] for asset_id in self.asset_ids]

    def _set(self, market: "Market", target: float, tau: float) -> None:
        for star in self.pair(market):
            multiplier = star.multipliers.setdefault(self.id, Multiplier(target=target, tau=tau))
            multiplier.target, multiplier.tau = target, tau

    def start(self, market: "Market") -> None:
        self._set(market, HYPE, HYPE_TAU)
        partner = market.stars[self.partner_id]
        self.report(market, "start", flash=True, also=[self.partner_id], partner=partner.name)

    def tick(self, market: "Market") -> bool:
        pair = self.pair(market)
        partner = market.stars[self.partner_id]
        if any(star.stage != "main_sequence" for star in pair):
            if self.phase != "near_miss":
                self.report(market, "called_off", also=[self.partner_id], partner=partner.name)
            self.cancel(market)  # one of them evolved: the dance is off
            return True
        seconds = (market.tick - self.t) * config.TICK_SECONDS
        if self.phase == "near_miss":
            if market.tick >= self.recovery_tick:
                self._set(market, 1.0, NEAR_MISS_TAU)
                if all(star.multipliers[self.id].settled for star in pair):
                    self.cancel(market)
                    return True
            return False
        if self.updates_sent < len(UPDATE_AT) and seconds >= UPDATE_AT[self.updates_sent]:
            self.updates_sent += 1
            closeness = "drawing closer" if seconds < CONTACT_SECONDS else "touching, sharing one swollen envelope"
            self.report(market, "update", also=[self.partner_id], partner=partner.name, closeness=closeness)
        if seconds >= CONTACT_SECONDS:
            self.phase = "contact"
            for star in pair:
                star.multipliers[self.id].target = HYPE * (1 + market.rng.gauss(0.0, CONTACT_JITTER))
                star.multipliers[self.id].tau = JITTER_TAU
        if seconds < MERGE_SECONDS:
            return False
        if not self.merges:
            self.phase = "near_miss"
            self.recovery_tick = market.tick + round(NEAR_MISS_RECOVERY_SECONDS / config.TICK_SECONDS)
            self._set(market, NEAR_MISS_DIP, NEAR_MISS_TAU)
            self.report(market, "near_miss", flash=True, also=[self.partner_id], partner=partner.name)
            return False
        survivor, absorbed = sorted(pair, key=lambda star: (star.mass, star.id), reverse=True)
        self.cancel(market)
        old_type = survivor.spectral_type
        market.retype(survivor, survivor.mass + absorbed.mass, boost=STRAGGLER_BOOST, fresh_life=True)
        survivor.L = survivor.base_L  # the flash of the merger
        self.asset_id = survivor.id  # report from the survivor's side
        new_type = f"a type {survivor.spectral_type} star"
        if survivor.spectral_type != old_type:
            new_type += f", up from type {old_type}, so it will burn out sooner"
        self.report(market, "merged", flash=True, also=[absorbed.id], partner=absorbed.name, new_type=new_type)
        market.absorb(survivor, absorbed, CASH_OUT_PREMIUM)
        return True


def merger_eligible(star: "Star") -> bool:
    return star.stage == "main_sequence"


def merger_partners(star: "Star", market: "Market") -> list["Star"]:
    return [
        other
        for other in market.stars.values()
        if other.id != star.id and other.listed and other.stage == "main_sequence" and not market.has_major_event(other)
    ]


def create_merger(star: "Star", partner: "Star", tick: int, rng: random.Random) -> StarMerger:
    return StarMerger(
        id=uuid.uuid4().hex,
        type="star_merger",
        asset_id=star.id,
        t=tick,
        partner_id=partner.id,
        merges=rng.random() < MERGE_CHANCE,
    )
