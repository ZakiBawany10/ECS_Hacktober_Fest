"""Runs Gemma calls in their own asyncio task, so a slow model never holds up the tick loop."""

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from pydantic import ValidationError

from .. import config
from ..lifecycle import Stage
from .client import ChatClient, GemmaError
from .prompts import HEADLINE_SCHEMA, SYSTEM, Headline, stage_change_fallback, stage_change_prompt

log = logging.getLogger(__name__)

OnHeadline = Callable[[Headline], Awaitable[None]]


@dataclass
class HeadlineJob:
    user_prompt: str
    fallback: Headline
    deadline: float  # time.monotonic() after which the fallback is published instead
    on_ready: OnHeadline


class AIWorker:
    def __init__(self, client: ChatClient, deadline_seconds: float = config.HEADLINE_DEADLINE_SECONDS) -> None:
        self.client = client
        self.deadline_seconds = deadline_seconds
        self.queue: asyncio.Queue[HeadlineJob] = asyncio.Queue()

    def request_headline(self, user_prompt: str, fallback: Headline, on_ready: OnHeadline) -> None:
        """Queue a headline. on_ready gets Gemma's, or the fallback once the deadline passes."""
        self.queue.put_nowait(HeadlineJob(user_prompt, fallback, time.monotonic() + self.deadline_seconds, on_ready))

    def request_stage_headline(
        self, name: str, spectral_type: str, old_stage: Stage, new_stage: Stage, on_ready: OnHeadline
    ) -> None:
        self.request_headline(
            stage_change_prompt(name, spectral_type, old_stage, new_stage), stage_change_fallback(name, new_stage), on_ready
        )

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

    async def handle(self, job: HeadlineJob) -> None:
        headline = job.fallback
        remaining = job.deadline - time.monotonic()
        if remaining > 0:
            try:
                reply = await asyncio.wait_for(
                    self.client.chat_json(SYSTEM, job.user_prompt, HEADLINE_SCHEMA), remaining
                )
                headline = Headline.model_validate(reply)
            except (GemmaError, TimeoutError, ValidationError) as exc:
                log.warning("Using the template headline: %r", exc)
        await job.on_ready(headline)
