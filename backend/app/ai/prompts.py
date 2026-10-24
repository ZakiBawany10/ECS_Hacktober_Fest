"""What Gemma is asked, the JSON it must reply with, and the templates used when it can't."""

import re
from typing import Annotated, Any, Literal

from pydantic import BaseModel, StringConstraints

from ..events import EventType
from ..lifecycle import STAGE_LABELS, Stage
from ..newsroom import OUTLETS, Outlet

SYSTEM = (
    "You write for Star Market, a live stock market game where the assets are stars and a star's share "
    "price follows its brightness. Reply with JSON only."
)


def outlet_system_prompt(outlet: Outlet) -> str:
    return (
        f"You are {outlet.name}, a{'n' if outlet.side == 'alien' else ''} {outlet.side} news outlet covering "
        "Star Market, a live stock market game where the assets are stars and a star's share price follows its "
        f"brightness. {outlet.voice} Write in that voice, but stick to the facts you are given: never change "
        "what happened or which way a price is moving. Never quote prices or share counts, and use no "
        "numbers except those in the facts. "
        "Reply with JSON only."
    )

# Ollama constrains Gemma's output to this schema.
HEADLINE_SCHEMA = {
    "type": "object",
    "properties": {
        "headline": {"type": "string", "maxLength": 90},
        "body": {"type": "string", "maxLength": 280},
    },
    "required": ["headline", "body"],
}


class Headline(BaseModel):
    """A validated headline. The limits are looser than the schema's so a slightly long reply still counts."""

    headline: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
    body: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=400)]


# What each new stage means for the price, so Gemma's headlines point players the right way.
_GIANT_NOTE = "It has swollen and brightened enormously, so its price is rallying."
STAGE_NOTES: dict[Stage, str] = {
    "main_sequence": "It has ignited and started fusing hydrogen, so its true value is finally known.",
    "red_giant": _GIANT_NOTE,
    "blue_giant": _GIANT_NOTE,
    "red_hypergiant": _GIANT_NOTE,
    "blue_hypergiant": _GIANT_NOTE,
    "supernova": (
        "It has exploded. Its price has spiked far above its old value and will fade slowly for about "
        "half a minute, then crash as the remnant forms. Smart traders sell before the crash."
    ),
    "white_dwarf": "Its outer layers have drifted away, leaving a dim core, so its price is sliding steadily.",
    "neutron_star": "The supernova has collapsed into a neutron star: the crash is over and the price has settled far lower.",
    "black_hole": "The supernova has collapsed into a black hole. No light means no value: its shares are worthless and can't be traded.",
}

_GIANT_FALLBACK = ("{name} swells into a {label}", "{name} has left the main sequence and its price is rallying.")
FALLBACKS: dict[Stage, tuple[str, str]] = {
    "main_sequence": ("{name} ignites", "{name} has joined the main sequence. {note}"),
    "red_giant": _GIANT_FALLBACK,
    "blue_giant": _GIANT_FALLBACK,
    "red_hypergiant": _GIANT_FALLBACK,
    "blue_hypergiant": _GIANT_FALLBACK,
    "supernova": ("{name} goes supernova", "{name} has exploded. The spike won't last: a crash follows within a minute."),
    "white_dwarf": ("{name} fades into a white dwarf", "{name} has shed its outer layers and its price is sliding."),
    "neutron_star": ("{name} collapses into a neutron star", "The supernova is over and {name} has settled far lower."),
    "black_hole": ("{name} becomes a black hole", "{name} has gone dark. Its shares are worthless and trading has stopped."),
}


# What happened at each moment of an event, filled in with its facts plus {name} and {stage}. Gemma
# writes from this. Notes never reveal a hidden outcome: facts like {hint} carry what code allows.
EVENT_NOTES: dict[tuple[EventType, str], str] = {
    ("meteor_strike", "start"): (
        "A {size} meteor storm has hit {name}, a {stage}. Its light has dipped, so its price has dropped, "
        "but it should recover within about half a minute."
    ),
    ("stellar_flare", "start"): (
        "{name}, a {stage}, has erupted in a {size} stellar flare. Its price has jumped, "
        "but the flare fades within about 20 seconds."
    ),
    ("coronal_collapse", "start"): (
        "{name}, a {stage}, is collapsing faster than forecast: it will become a {next_stage} much sooner "
        "than expected."
    ),
    ("mysterious_dimming", "start"): (
        "{name}, a {stage}, has started dimming in strange, irregular dips, and its price is wobbling. "
        "Nobody knows why: it could be dust or comets, or something being built. Don't say which."
    ),
    ("mysterious_dimming", "update"): (
        "{name} keeps dimming in odd dips. Speculate in your outlet's style (a tabloid might cry alien "
        "megastructure, a scientist might lean towards dust), but don't state the cause as fact."
    ),
    ("mysterious_dimming", "cleared"): (
        "The strange dimming of {name} has stopped: it was dust after all, and its light and price are "
        "returning to normal."
    ),
    ("dyson_sphere", "start"): (
        "Unidentified structures have been detected around {name}, a {stage}: someone appears to be "
        "building a Dyson sphere to capture its light. {origin} As the sphere grows, the star will look "
        "dimmer and its price will fall. Nobody knows yet whether it will be finished."
    ),
    ("dyson_sphere", "update"): (
        "Progress report on the Dyson sphere around {name}: it is about {progress} complete, and the star's "
        "price keeps falling as more light is blocked. {status} {hint}"
    ),
    ("dyson_sphere", "stall"): (
        "Construction crews around {name} have gone idle: work on its Dyson sphere has stopped, for now. "
        "It isn't clear whether it will restart."
    ),
    ("dyson_sphere", "abandoned"): (
        "The Dyson sphere around {name} has been abandoned half-built. The star's light is flooding back and "
        "its price is rallying sharply."
    ),
    ("dyson_sphere", "complete"): (
        "The Dyson sphere around {name} is complete. The star is enclosed, almost none of its light escapes, "
        "and its shares are near worthless. Only the star swelling or exploding could break the sphere."
    ),
    ("dyson_sphere", "destroyed"): (
        "{name} has become a {stage} and torn its Dyson sphere apart. Its light, and its price, are back."
    ),
    ("intelligent_life", "start"): (
        "Astronomers have detected {life} on planets around {name}, a {stage}. Markets value a living "
        "system, so its price is climbing. Nobody knows yet if it will grow into a civilisation."
    ),
    ("intelligent_life", "level_up"): (
        "The life around {name} has advanced: it is now {life}. Its price is climbing again."
    ),
    ("intelligent_life", "silent"): (
        "The signals from {life} around {name} have suddenly gone silent: it seems to have destroyed itself. "
        "Its price premium is collapsing. Make it eerie."
    ),
    ("intelligent_life", "sterilised"): (
        "A stellar flare from {name} has sterilised its planets, wiping out {life}. Its price premium is gone."
    ),
    ("intelligent_life", "migrated"): (
        "{name} has swollen into a {stage}, and {life} has fled its dying star for {new_home}. {new_home}'s "
        "price is climbing as the refugees arrive."
    ),
    ("intelligent_life", "extinct"): (
        "{name} has swollen into a {stage}, and {life} on its planets could not escape. It is extinct, "
        "and its price premium is gone."
    ),
    ("alien_signal", "start"): (
        "RUMOUR: an unexplained signal has been picked up from the direction of {name}, a {stage}. {flavour} "
        "It is unconfirmed: report it as a rumour. {secret}"
    ),
    ("alien_signal", "confirmed"): (
        "The signal from {name} has been confirmed as genuine. The price move it caused was real, and will "
        "fade as the excitement settles."
    ),
    ("alien_signal", "debunked"): (
        "The signal from {name} has been debunked: it was a hoax. Nothing about the star has changed, and "
        "anyone who traded on the rumour was fooled."
    ),
}

EVENT_FALLBACKS: dict[tuple[EventType, str], tuple[str, str]] = {
    ("meteor_strike", "start"): ("Meteor storm batters {name}", "{name} has dimmed after a meteor strike. A recovery is expected within the minute."),
    ("stellar_flare", "start"): ("{name} erupts in a stellar flare", "A flare has lit up {name}, but it should fade within half a minute."),
    ("coronal_collapse", "start"): ("{name}'s core is collapsing early", "{name} will become a {next_stage} sooner than expected."),
    ("mysterious_dimming", "start"): ("{name} dims mysteriously", "Strange dips in {name}'s light have traders guessing: dust, or something else?"),
    ("mysterious_dimming", "update"): ("{name} keeps flickering", "The dips in {name}'s light continue, and so does the speculation."),
    ("mysterious_dimming", "cleared"): ("{name}'s dimming was just dust", "The dips have cleared and {name}'s price is recovering."),
    ("dyson_sphere", "start"): ("Structures detected around {name}", "Someone is building a Dyson sphere around {name}, and its light is fading."),
    ("dyson_sphere", "update"): ("{name}'s Dyson sphere about {progress} built", "More of {name}'s light is blocked as construction continues."),
    ("dyson_sphere", "stall"): ("Work stalls on {name}'s Dyson sphere", "Construction crews around {name} have gone idle."),
    ("dyson_sphere", "abandoned"): ("{name}'s Dyson sphere abandoned", "The builders have walked away and {name}'s price is rallying."),
    ("dyson_sphere", "complete"): ("{name} fully enclosed", "The Dyson sphere around {name} is finished. Its shares are near worthless."),
    ("dyson_sphere", "destroyed"): ("{name} shatters its Dyson sphere", "{name} has become a {stage}, and its light is back."),
    ("intelligent_life", "start"): ("Life detected around {name}", "Astronomers have found {life} around {name}, and its price is climbing."),
    ("intelligent_life", "level_up"): ("{name}'s life evolves", "The life around {name} is now {life}."),
    ("intelligent_life", "silent"): ("{name} goes silent", "The signals from {life} around {name} have stopped."),
    ("intelligent_life", "sterilised"): ("Flare sterilises {name}", "A stellar flare has wiped out {life} around {name}."),
    ("intelligent_life", "migrated"): ("Life flees {name} for {new_home}", "As {name} swells, {life} has moved to {new_home}."),
    ("intelligent_life", "extinct"): ("Life dies out at {name}", "Nothing survived on {name}'s planets as it swelled."),
    ("alien_signal", "start"): ("Mystery signal from {name}?", "An unconfirmed signal has been picked up from {name}. {flavour}"),
    ("alien_signal", "confirmed"): ("{name} signal confirmed", "The signal from {name} is genuine."),
    ("alien_signal", "debunked"): ("{name} signal was a hoax", "The signal from {name} has been debunked. Nothing has changed."),
}

_HEADLINE_REQUEST = "Write a headline of at most 12 words and a body of one or two sentences."


def _fill(template: str, facts: dict[str, str]) -> str:
    """Fill a template, tidying the gaps left by empty facts."""
    return " ".join(template.format(**facts).split())


def event_prompt(event_type: EventType, moment: str, facts: dict[str, str]) -> str:
    return f"{_fill(EVENT_NOTES[event_type, moment], facts)} {_HEADLINE_REQUEST}"


def event_fallback(event_type: EventType, moment: str, facts: dict[str, str]) -> Headline:
    headline, body = EVENT_FALLBACKS[event_type, moment]
    return Headline(headline=_fill(headline, facts), body=_fill(body, facts))


def stage_change_prompt(name: str, spectral_type: str, old_stage: Stage, new_stage: Stage, note: str = "") -> str:
    extra = f" {note}" if note else ""
    return (
        f"{name}, a type {spectral_type} star, has just evolved from a {STAGE_LABELS[old_stage]} "
        f"into a {STAGE_LABELS[new_stage]}. {STAGE_NOTES[new_stage]}{extra} {_HEADLINE_REQUEST}"
    )


def stage_change_fallback(name: str, new_stage: Stage, note: str = "") -> Headline:
    headline, body = FALLBACKS[new_stage]
    facts = {"name": name, "label": STAGE_LABELS[new_stage], "note": note}
    return Headline(headline=headline.format(**facts), body=body.format(**facts).strip())


# News about a star outside its stage changes: from discovery as a protostar to delisting as a black hole.
StarNews = Literal["discovery", "forecast", "delisted"]

SPECTRAL_LOOKS = {
    "O": "a huge, hot blue type O star",
    "B": "a bright blue-white type B star",
    "A": "a white type A star",
    "F": "a yellow-white type F star",
    "G": "a yellow, Sun-like type G star",
    "K": "an orange type K star",
    "M": "a dim red type M dwarf",
}

STAR_NEWS_NOTES: dict[StarNews, str] = {
    "discovery": (
        "Astronomers have spotted {name}, a new protostar: a collapsing cloud of gas that hasn't started "
        "fusing yet. Forecasters project it will become {projection}. Forecasts this early can be badly wrong, "
        "and its true value is only revealed when it ignites. Traders can buy in now at the forecast price."
    ),
    "forecast": (
        "Forecasters have updated their projection for {name}, a protostar still gathering gas: they now "
        "expect {projection}, {revision}. It will ignite and reveal its true value soon."
    ),
    "delisted": (
        "{name}, a black hole, has been delisted from the exchange. Its shares were worthless and have been "
        "written off."
    ),
}

STAR_NEWS_FALLBACKS: dict[StarNews, tuple[str, str]] = {
    "discovery": ("New protostar {name} spotted", "Forecasters expect {name} to become {projection}."),
    "forecast": ("Forecast updated for {name}", "Forecasters now expect {projection}, {revision}."),
    "delisted": ("{name} delisted", "{name}'s worthless black hole shares have been written off."),
}


# Star names: Gemma invents a batch at a time, kept in Market.name_pool until a star spawns.
NAME_BATCH = 5
NAME_PATTERN = re.compile(r"[A-Z][A-Za-z' -]{1,15}")
NAMES_SCHEMA = {
    "type": "object",
    "properties": {
        "names": {"type": "array", "items": {"type": "string", "maxLength": 16}, "minItems": 1, "maxItems": NAME_BATCH}
    },
    "required": ["names"],
}


def names_prompt(avoid: list[str]) -> str:
    return (
        f"Invent {NAME_BATCH} names for newly discovered stars in a space trading game. Each should be one or "
        "two words and at most 16 letters: varied, memorable names that sound like places, people, birds, "
        "myths or old words. Avoid overused space words (Nova, Star, Stellar, Aether, Cosmic, Astro, Flare, "
        "Glimmer), real astronomical names, and names from games, films or brands. "
        f"Don't reuse any of these: {', '.join(avoid) or 'none'}."
    )


def valid_names(reply: dict[str, Any], avoid: list[str]) -> list[str]:
    """The new, well-formed names in Gemma's reply, in order, without repeats."""
    taken = {name.lower() for name in avoid}
    names = []
    for name in reply.get("names") or []:
        if not isinstance(name, str):
            continue
        name = " ".join(name.split())
        if NAME_PATTERN.fullmatch(name) and name.lower() not in taken:
            names.append(name)
            taken.add(name.lower())
    return names


def star_news_prompt(kind: StarNews, facts: dict[str, str]) -> str:
    return f"{STAR_NEWS_NOTES[kind].format(**facts)} {_HEADLINE_REQUEST}"


def star_news_fallback(kind: StarNews, facts: dict[str, str]) -> Headline:
    headline, body = STAR_NEWS_FALLBACKS[kind]
    return Headline(headline=headline.format(**facts), body=body.format(**facts))
