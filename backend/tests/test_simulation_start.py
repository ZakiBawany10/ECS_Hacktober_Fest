import asyncio
import time

import pytest
from fastapi.testclient import TestClient

from app import main
from app.market import Market
from app.models import JoinRequest


def test_reads_saved_player_websocket_and_invalid_names_do_not_start_market(monkeypatch, fake_gemma):
    market = Market(random_events=False)
    saved_player = market.join("Returning player")
    monkeypatch.setattr(main, "market", market)
    monkeypatch.setattr(main.config, "TICK_SECONDS", 0.01)

    with TestClient(main.app) as client, client.websocket_connect("/ws"):
        initial = client.get("/state").json()
        assert client.get("/health").status_code == 200
        assert client.get(f"/portfolio/{saved_player.id}").status_code == 200
        assert client.get("/assets/sol-nova/history").status_code == 200
        for nickname in ("", "   ", "x" * 21):
            assert client.post("/join", json={"nickname": nickname}).status_code == 422

        # Several tick intervals pass while the menu is open, without evolving stars.
        time.sleep(0.04)
        assert client.get("/state").json() == initial
        assert not main.app.state.simulation_started.is_set()
        assert len(market.players) == 1
        assert len(fake_gemma.prompts) == 1  # Only the independent AI warm-up ran.


def test_first_join_starts_shared_clock_and_later_joins_keep_it_running(monkeypatch):
    market = Market(random_events=False)
    monkeypatch.setattr(main, "market", market)
    monkeypatch.setattr(main.config, "TICK_SECONDS", 0.005)

    def wait_for_later_tick(client, previous):
        deadline = time.monotonic() + 1
        while time.monotonic() < deadline:
            tick = client.get("/state").json()["t"]
            if tick > previous:
                return tick
            time.sleep(0.005)
        pytest.fail("The shared simulation did not advance after joining")

    with TestClient(main.app) as client:
        assert client.get("/state").json()["t"] == 0
        first_id = client.post("/join", json={"nickname": "First"}).json()["player_id"]
        started = main.app.state.simulation_started
        assert started.is_set()
        previous = wait_for_later_tick(client, 0)
        first_player = market.get_player(first_id)
        second_id = client.post("/join", json={"nickname": "Second"}).json()["player_id"]

        assert second_id != first_id
        assert market.get_player(first_id) is first_player
        assert main.app.state.simulation_started is started
        assert market.tick >= previous
        wait_for_later_tick(client, previous)
        assert len(market.players) == 2
        assert len(market.stars["sol-nova"].history) > 1


@pytest.mark.parametrize("start", [False, True])
def test_shutdown_cancels_waiting_and_running_tasks(monkeypatch, start):
    monkeypatch.setattr(main, "market", Market(random_events=False))
    monkeypatch.setattr(main.config, "TICK_SECONDS", 60)

    async def scenario():
        existing_tasks = asyncio.all_tasks()
        async with main.lifespan(main.app):
            await asyncio.sleep(0)
            if start:
                await main.join(JoinRequest(nickname="Start"))
                await asyncio.sleep(0)
            tasks = asyncio.all_tasks() - existing_tasks
            assert len(tasks) == 2  # The gated tick loop and the AI worker.
            assert main.market.tick == 0  # The full first interval is still pending.
        assert all(task.done() for task in tasks)
        assert not hasattr(main.app.state, "simulation_started")

    asyncio.run(scenario())
