import asyncio
import json

import httpx
import pytest

from app.ai.client import GemmaClient, GemmaError
from app.ai.prompts import (
    EVENT_FALLBACKS,
    EVENT_NOTES,
    FALLBACKS,
    STAGE_LABELS,
    STAGE_NOTES,
    Headline,
    event_fallback,
    stage_change_fallback,
)
from app.events import EVENT_WEIGHTS
from app.ai.worker import AIWorker
from conftest import FakeChatClient


def gemma_with(handler) -> GemmaClient:
    return GemmaClient(http=httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://gemma"))


def ollama_reply(content: str) -> httpx.Response:
    return httpx.Response(200, json={"message": {"role": "assistant", "content": content}})


def test_client_sends_structured_request_and_parses_reply():
    requests = []

    def handler(request):
        requests.append(json.loads(request.content))
        return ollama_reply('{"headline": "Hi", "body": "There."}')

    reply = asyncio.run(gemma_with(handler).chat_json("sys", "user", {"type": "object"}))
    assert reply == {"headline": "Hi", "body": "There."}
    body = requests[0]
    assert body["think"] is False and body["stream"] is False
    assert body["format"] == {"type": "object"}
    assert [m["role"] for m in body["messages"]] == ["system", "user"]


def test_client_retries_once():
    responses = [httpx.Response(500), ollama_reply('{"ok": true}')]
    assert asyncio.run(gemma_with(lambda request: responses.pop(0)).chat_json("s", "u", {})) == {"ok": True}


@pytest.mark.parametrize(
    "response", [httpx.Response(500), ollama_reply("not json"), ollama_reply("[1, 2]"), httpx.Response(200, json={})]
)
def test_client_raises_after_two_failures(response):
    calls = []

    def handler(request):
        calls.append(request)
        return response

    with pytest.raises(GemmaError):
        asyncio.run(gemma_with(handler).chat_json("s", "u", {}))
    assert len(calls) == 2


def test_every_later_stage_has_a_note_and_fallback():
    later_stages = set(STAGE_LABELS) - {"main_sequence"}
    assert set(STAGE_NOTES) == later_stages
    assert set(FALLBACKS) == later_stages
    for stage in later_stages:
        assert "Kestrel" in stage_change_fallback("Kestrel", stage).headline


def run_job(client, deadline_seconds=5.0) -> list[Headline]:
    published: list[Headline] = []

    async def on_ready(headline):
        published.append(headline)

    async def go():
        worker = AIWorker(client, deadline_seconds=deadline_seconds)
        worker.request_stage_headline("Altra", "A", "blue_giant", "supernova", on_ready)
        await worker.handle(worker.queue.get_nowait())

    asyncio.run(go())
    return published


def test_worker_publishes_gemma_headline():
    client = FakeChatClient({"headline": "  Altra Blows!  ", "body": "Sell before the crash."})
    assert run_job(client) == [Headline(headline="Altra Blows!", body="Sell before the crash.")]
    assert "blue giant into a supernova" in client.prompts[0]


@pytest.mark.parametrize(
    "reply", [GemmaError("down"), {"headline": "", "body": "x"}, {"headline": "x"}, {"headline": "x" * 500, "body": "y"}]
)
def test_worker_falls_back_to_template(reply):
    assert run_job(FakeChatClient(reply)) == [stage_change_fallback("Altra", "supernova")]


def test_worker_falls_back_when_gemma_is_too_slow():
    class SlowClient:
        async def chat_json(self, system, user, schema):
            await asyncio.sleep(10)

    assert run_job(SlowClient(), deadline_seconds=0.05) == [stage_change_fallback("Altra", "supernova")]


def test_worker_skips_gemma_once_deadline_has_passed():
    client = FakeChatClient()
    assert run_job(client, deadline_seconds=0) == [stage_change_fallback("Altra", "supernova")]
    assert client.prompts == []


def test_every_event_type_has_a_note_and_fallback():
    assert set(EVENT_NOTES) == set(EVENT_FALLBACKS) == set(EVENT_WEIGHTS)
    facts = {"name": "Kora", "stage": "red giant", "size": "heavy", "next_stage": "white dwarf"}
    for event_type in EVENT_WEIGHTS:
        assert "Kora" in event_fallback(event_type, facts).headline
