from fastapi.testclient import TestClient

from app.main import app

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
    assert {"id", "price", "L"} <= message["assets"][0].keys()
