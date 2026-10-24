"""What Gemma is asked, the JSON it must reply with, and the templates used when it can't."""

from typing import Annotated, Literal

from pydantic import BaseModel, StringConstraints

from ..events import EventType
from ..lifecycle import STAGE_LABELS, Stage

SYSTEM = (
    "You write breaking-news items for Star Market, a live stock market game where the assets are stars "
    "and a star's share price follows its brightness. Tone: a punchy financial-news wire, lightly playful. "
    "You may say which way a price is heading, but never quote prices, percentages or share counts. "
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


# What happened, filled in with the event's facts plus {name} and {stage}. Gemma writes from this.
EVENT_NOTES: dict[EventType, str] = {
    "meteor_strike": (
        "A {size} meteor storm has hit {name}, a {stage}. Its light has dipped, so its price has dropped, "
        "but it should recover within about half a minute."
    ),
    "stellar_flare": (
        "{name}, a {stage}, has erupted in a {size} stellar flare. Its price has jumped, "
        "but the flare fades within about 20 seconds."
    ),
    "coronal_collapse": (
        "{name}, a {stage}, is collapsing faster than forecast: it will become a {next_stage} much sooner "
        "than expected."
    ),
}

EVENT_FALLBACKS: dict[EventType, tuple[str, str]] = {
    "meteor_strike": ("Meteor storm batters {name}", "{name} has dimmed after a meteor strike. A recovery is expected within the minute."),
    "stellar_flare": ("{name} erupts in a stellar flare", "A flare has lit up {name}, but it should fade within half a minute."),
    "coronal_collapse": ("{name}'s core is collapsing early", "{name} will become a {next_stage} sooner than expected."),
}

_HEADLINE_REQUEST = "Write a headline of at most 12 words and a body of one or two sentences."


def event_prompt(event_type: EventType, facts: dict[str, str]) -> str:
    return f"{EVENT_NOTES[event_type].format(**facts)} {_HEADLINE_REQUEST}"


def event_fallback(event_type: EventType, facts: dict[str, str]) -> Headline:
    headline, body = EVENT_FALLBACKS[event_type]
    return Headline(headline=headline.format(**facts), body=body.format(**facts))


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


def star_news_prompt(kind: StarNews, facts: dict[str, str]) -> str:
    return f"{STAR_NEWS_NOTES[kind].format(**facts)} {_HEADLINE_REQUEST}"


def star_news_fallback(kind: StarNews, facts: dict[str, str]) -> Headline:
    headline, body = STAR_NEWS_FALLBACKS[kind]
    return Headline(headline=headline.format(**facts), body=body.format(**facts))
