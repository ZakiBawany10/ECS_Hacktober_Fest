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
    monkeypatch.setattr(main, "market", Market())  # keep the shared market untouched for other tests
    response = client.post("/director/force_stage", json={"asset_id": "altra"})
    assert response.status_code == 200
    assert response.json()["stage"] == "blue_giant"
    stages = {asset["id"]: asset["stage"] for asset in client.get("/state").json()["assets"]}
    assert stages["altra"] == "blue_giant"
    for _ in range(2):
        client.post("/director/force_stage", json={"asset_id": "altra"})
    assert client.post("/director/force_stage", json={"asset_id": "altra"}).status_code == 400
    assert client.post("/director/force_stage", json={"asset_id": "nope"}).status_code == 404
