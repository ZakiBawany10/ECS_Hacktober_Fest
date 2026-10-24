"""Runs Gemma calls in their own asyncio task, so a slow model never holds up the tick loop."""

import asyncio
import logging
import random
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from pydantic import ValidationError

from .. import config
from ..lifecycle import Stage
from .client import ChatClient, GemmaError
from .prompts import (
    HEADLINE_SCHEMA,
    NAMES_SCHEMA,
    OUTLETS,
    SYSTEM,
    Headline,
    Outlet,
    names_prompt,
    outlet_system_prompt,
    stage_change_fallback,
    stage_change_prompt,
    valid_names,
)

log = logging.getLogger(__name__)

OnHeadline = Callable[[Headline, Outlet], Awaitable[None]]


@dataclass
class HeadlineJob:
    user_prompt: str
    fallback: Headline
    deadline: float  # time.monotonic() after which the fallback is published instead
    on_ready: OnHeadline
    outlet: Outlet  # who reports it; the fallback is credited to them too


@dataclass
class NamesJob:
    avoid: list[str]  # names already in use
    on_ready: Callable[[list[str]], None]  # gets the valid new names; not called if Gemma fails


class AIWorker:
    def __init__(self, client: ChatClient, deadline_seconds: float = config.HEADLINE_DEADLINE_SECONDS) -> None:
        self.client = client
        self.deadline_seconds = deadline_seconds
        self.queue: asyncio.Queue[HeadlineJob | NamesJob] = asyncio.Queue()
        self.names_pending = False
        self.rng = random.Random()

    def request_headline(
        self, user_prompt: str, fallback: Headline, on_ready: OnHeadline, outlet: Outlet | None = None
    ) -> None:
        """Queue a headline from an outlet (random by default). on_ready gets Gemma's, or the fallback once
        the deadline passes."""
        outlet = outlet or self.rng.choice(OUTLETS)
        deadline = time.monotonic() + self.deadline_seconds
        self.queue.put_nowait(HeadlineJob(user_prompt, fallback, deadline, on_ready, outlet))

    def request_stage_headline(
        self, name: str, spectral_type: str, old_stage: Stage, new_stage: Stage, on_ready: OnHeadline, note: str = ""
    ) -> None:
        self.request_headline(
            stage_change_prompt(name, spectral_type, old_stage, new_stage, note),
            stage_change_fallback(name, new_stage, note),
            on_ready,
        )

    def request_names(self, avoid: list[str], on_ready: Callable[[list[str]], None]) -> None:
        """Queue a batch of star names, unless one is already on its way."""
        if not self.names_pending:
            self.names_pending = True
            self.queue.put_nowait(NamesJob(avoid, on_ready))

    async def run(self) -> None:
        await self.warm_up()
        while True:
            job = await self.queue.get()
            try:
                await self.handle(job)
            except Exception:
                log.exception("News headline job failed")

    async def warm_up(self) -> None:
        """Load the model now, so the first real headline doesn't pay the ~5 s load time."""
        try:
            await self.client.chat_json(SYSTEM, "Write a headline announcing that the market is open.", HEADLINE_SCHEMA)
        except GemmaError as exc:
            log.warning("Gemma warm-up failed; headlines will use templates until it responds: %s", exc)

    async def handle(self, job: HeadlineJob | NamesJob) -> None:
        if isinstance(job, NamesJob):
            await self.handle_names(job)
        else:
            await self.handle_headline(job)

    async def handle_names(self, job: NamesJob) -> None:
        try:
            reply = await self.client.chat_json(SYSTEM, names_prompt(job.avoid), NAMES_SCHEMA)
            job.on_ready(valid_names(reply, job.avoid))
        except GemmaError as exc:
            log.warning("Gemma couldn't name stars; new stars will use fallback names: %r", exc)
        finally:
            self.names_pending = False
        self.rng = random.Random()

    async def handle_headline(self, job: HeadlineJob) -> None:
        headline = job.fallback
        remaining = job.deadline - time.monotonic()
        if remaining > 0:
            try:
                reply = await asyncio.wait_for(
                    self.client.chat_json(outlet_system_prompt(job.outlet), job.user_prompt, HEADLINE_SCHEMA),
                    remaining,
                )
                headline = Headline.model_validate(reply)
            except (GemmaError, TimeoutError, ValidationError) as exc:
                log.warning("Using the template headline: %r", exc)
        await job.on_ready(headline, job.outlet)
