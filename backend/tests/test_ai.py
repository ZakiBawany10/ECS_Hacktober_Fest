import asyncio
import json
import random

import httpx
import pytest

from app.ai.client import GemmaClient, GemmaError
from app.ai.prompts import (
    EVENT_FALLBACKS,
    OUTLETS,
    EVENT_NOTES,
    FALLBACKS,
    STAGE_LABELS,
    STAGE_NOTES,
    Headline,
    event_fallback,
    event_prompt,
    stage_change_fallback,
)
from app.events import EVENT_WEIGHTS, MOMENTS
from app.newsroom import percent, reported_progress
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
    later_stages = set(STAGE_LABELS) - {"protostar"}
    assert set(STAGE_NOTES) == later_stages
    assert set(FALLBACKS) == later_stages
    for stage in later_stages:
        assert "Kestrel" in stage_change_fallback("Kestrel", stage).headline


def run_job(client, deadline_seconds=5.0) -> list[Headline]:
    published: list[Headline] = []

    async def on_ready(headline, outlet):
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


def test_every_event_moment_has_a_note_and_fallback():
    moments = {(event_type, moment) for event_type, names in MOMENTS.items() for moment in names}
    assert set(EVENT_NOTES) == set(EVENT_FALLBACKS) == moments
    assert set(MOMENTS) == set(EVENT_WEIGHTS)
    facts = {
        "name": "Kora", "stage": "red giant", "size": "heavy", "next_stage": "white dwarf",
        "origin": "", "progress": "40%", "status": "", "hint": "", "life": "microbial life", "new_home": "Ember", "flavour": "", "secret": "",
    }  # fmt: skip
    for event_type, moment in moments:
        assert "Kora" in event_fallback(event_type, moment, facts).body + event_fallback(event_type, moment, facts).headline
        assert "  " not in event_prompt(event_type, moment, facts)


def test_outlets_slant_progress_within_limits():
    rng = random.Random(0)
    for outlet in OUTLETS:
        for true in (0.0, 0.3, 0.9, 0.99):
            reported = reported_progress(outlet, true, previous=max(true - 0.1, 0), rng=rng)
            assert abs(reported - true) <= 0.15 + 1e-9 and 0 <= reported <= 0.95
    assert percent(0.437) == "45%"


def run_names_job(client, avoid):
    named: list[list[str]] = []

    async def go():
        worker = AIWorker(client)
        worker.request_names(avoid, named.append)
        worker.request_names(avoid, named.append)  # ignored: a batch is already on its way
        assert worker.queue.qsize() == 1
        await worker.handle(worker.queue.get_nowait())
        assert not worker.names_pending

    asyncio.run(go())
    return named


def test_worker_collects_valid_star_names():
    reply = {"names": ["Vireo", "  Ash   Wake ", "vireo", "Kora", "lowercase", "Way Too Long A Star Name", 7, "Q"]}
    assert run_names_job(FakeChatClient(reply), avoid=["Kora"]) == [["Vireo", "Ash Wake"]]


def test_worker_survives_gemma_failing_to_name_stars():
    assert run_names_job(FakeChatClient(GemmaError("down")), avoid=[]) == []


def test_each_headline_comes_from_an_outlet_in_its_voice():
    client = FakeChatClient()
    outlets = []

    async def on_ready(headline, outlet):
        outlets.append(outlet)

    async def go():
        worker = AIWorker(client)
        worker.request_headline("Write it.", stage_change_fallback("Altra", "supernova"), on_ready, OUTLETS[3])
        await worker.handle(worker.queue.get_nowait())

    asyncio.run(go())
    assert outlets == [OUTLETS[3]] and OUTLETS[3].side == "alien"
    assert "You are Zr'kth Construction Authority, an alien news outlet" in client.systems[0]
    assert {outlet.side for outlet in OUTLETS} == {"human", "alien"}
