import asyncio

from fastapi.testclient import TestClient

from app import main
from app.main import app
from app.market import Market

# Created without a `with` block, so the lifespan tick loop doesn't run and prices stay put.
client = TestClient(app)


def test_join_trade_and_portfolio():
    player_id = client.post("/join", json={"nickname": "  zaki  "}).json()["player_id"]

    response = client.post("/trade", json={"player_id": player_id, "asset_id": "sol-nova", "side": "buy", "qty": 1})
    assert response.status_code == 200
    portfolio = response.json()
    assert portfolio["nickname"] == "zaki"
    assert portfolio["holdings"] == {"sol-nova": 1}
    assert portfolio["net_worth"] == 10_000

    assert client.get(f"/portfolio/{player_id}").json() == portfolio


def test_state_lists_assets_and_leaderboard():
    body = client.get("/state").json()
    assert {asset["id"] for asset in body["assets"]} >= {"kestrel", "sol-nova", "ember"}
    assert {asset["stage"] for asset in body["assets"]} == {"main_sequence"}
    assert "leaderboard" in body


def test_rejected_trades():
    player_id = client.post("/join", json={"nickname": "broke"}).json()["player_id"]
    too_big = {"player_id": player_id, "asset_id": "kestrel", "side": "buy", "qty": 1_000}
    assert client.post("/trade", json=too_big).status_code == 400
    unknown = {"player_id": player_id, "asset_id": "nope", "side": "buy", "qty": 1}
    assert client.post("/trade", json=unknown).status_code == 404
    negative = {"player_id": player_id, "asset_id": "kestrel", "side": "buy", "qty": -1}
    assert client.post("/trade", json=negative).status_code == 422
    assert client.post("/join", json={"nickname": "   "}).status_code == 422


def test_history_and_websocket_tick():
    assert client.get("/assets/sol-nova/history").json()[0]["t"] == 0
    assert client.get("/assets/nope/history").status_code == 404
    with TestClient(app) as live_client, live_client.websocket_connect("/ws") as ws:
        message = ws.receive_json()
    assert message["type"] == "tick"
    assert {"id", "stage", "price", "L"} <= message["assets"][0].keys()


def test_director_force_stage(monkeypatch):
    monkeypatch.setattr(main, "market", Market(random_events=False))  # keep the shared market untouched
    response = client.post("/director/force_stage", json={"asset_id": "altra"})
    assert response.status_code == 200
    assert response.json()["stage"] == "blue_giant"
    stages = {asset["id"]: asset["stage"] for asset in client.get("/state").json()["assets"]}
    assert stages["altra"] == "blue_giant"
    for _ in range(2):
        client.post("/director/force_stage", json={"asset_id": "altra"})
    assert client.post("/director/force_stage", json={"asset_id": "altra"}).status_code == 400
    assert client.post("/director/force_stage", json={"asset_id": "nope"}).status_code == 404


def test_stage_change_news_reaches_state(monkeypatch, fake_gemma):
    monkeypatch.setattr(main, "market", Market(random_events=False))
    fake_gemma.reply = {"headline": "Altra swells", "body": "Up it goes."}
    client.post("/director/force_stage", json={"asset_id": "altra"})
    asyncio.run(main.worker.handle(main.worker.queue.get_nowait()))
    [news] = client.get("/state").json()["news"]
    assert news["kind"] == "lifecycle"
    assert news["asset_ids"] == ["altra"]
    assert (news["headline"], news["body"]) == ("Altra swells", "Up it goes.")
    assert "main-sequence star into a blue giant" in fake_gemma.prompts[0]


def test_websocket_sends_news(monkeypatch):
    monkeypatch.setattr(main, "market", Market(random_events=False))
    with TestClient(app) as live_client, live_client.websocket_connect("/ws") as ws:
        live_client.post("/director/force_stage", json={"asset_id": "kestrel"})
        messages = [ws.receive_json() for _ in range(3)]
        news = next(message for message in messages if message["type"] == "news")
    assert news["item"]["headline"] == "Fake headline"
    assert news["item"]["asset_ids"] == ["kestrel"]


def test_director_fire_event_publishes_news(monkeypatch, fake_gemma):
    monkeypatch.setattr(main, "market", Market(random_events=False))
    response = client.post("/director/fire_event", json={"type": "meteor_strike", "asset_id": "kora"})
    assert response.status_code == 200
    assert response.json()["id"] == "kora"
    asyncio.run(main.worker.handle(main.worker.queue.get_nowait()))
    [news] = client.get("/state").json()["news"]
    assert (news["kind"], news["asset_ids"]) == ("event", ["kora"])
    assert "meteor storm has hit Kora, a main-sequence star" in fake_gemma.prompts[0]

    flare_on_giant = {"type": "stellar_flare", "asset_id": "kora"}
    client.post("/director/force_stage", json={"asset_id": "kora"})
    assert client.post("/director/fire_event", json=flare_on_giant).status_code == 400
    assert client.post("/director/fire_event", json={"type": "meteor_strike", "asset_id": "nope"}).status_code == 404
    assert client.post("/director/fire_event", json={"type": "supernova", "asset_id": "kora"}).status_code == 422
