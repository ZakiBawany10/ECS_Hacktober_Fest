import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from . import config
from .ai.client import GemmaClient
from .ai.prompts import Headline, event_fallback, event_prompt
from .ai.worker import AIWorker
from .events import Event
from .lifecycle import STAGE_LABELS
from .market import Market, MarketError, News, NewsKind, NotFoundError, Player, StageChange, Star
from .models import (
    Asset,
    AssetTick,
    FireEventRequest,
    ForceStageRequest,
    JoinRequest,
    JoinResponse,
    LeaderboardMessage,
    LeaderboardRow,
    NewsItem,
    NewsMessage,
    Portfolio,
    PricePoint,
    StateSnapshot,
    TickMessage,
    TradeRequest,
)

# Route handlers are async so they run on the same event loop as the tick loop,
# which keeps all access to the market single-threaded.
market = Market()
# Gemma calls run in the worker's own task, never on the tick loop.
gemma = GemmaClient()
worker = AIWorker(gemma)


class ConnectionManager:
    def __init__(self) -> None:
        self.connections: set[WebSocket] = set()

    async def broadcast(self, message: BaseModel) -> None:
        data = message.model_dump(mode="json")
        for websocket in list(self.connections):
            try:
                await websocket.send_json(data)
            except Exception:
                self.connections.discard(websocket)


connections = ConnectionManager()


def asset_out(star: Star) -> Asset:
    return Asset(
        id=star.id,
        name=star.name,
        kind="star",
        stage=star.stage,
        spectral_type=star.spectral_type,
        mass=star.mass,
        temperature=star.temperature,
        L=star.L,
        price=star.price,
        shares_total=config.SHARES_PER_STAR,
        shares_available=star.shares_available,
    )


def portfolio_out(player: Player) -> Portfolio:
    return Portfolio(
        player_id=player.id,
        nickname=player.nickname,
        cash=round(player.cash, 2),
        holdings=dict(player.holdings),
        net_worth=round(market.net_worth(player), 2),
    )


def leaderboard_out() -> list[LeaderboardRow]:
    return [LeaderboardRow(nickname=p.nickname, net_worth=round(worth, 2)) for p, worth in market.leaderboard()]


def news_out(news: News) -> NewsItem:
    return NewsItem(
        id=news.id,
        t=news.t,
        kind=news.kind,
        headline=news.headline,
        body=news.body,
        asset_ids=list(news.asset_ids),
    )


def publisher(kind: NewsKind, asset_ids: list[str], t: int):
    """Return a callback that publishes a finished headline to the feed and the WebSocket."""

    async def publish(headline: Headline) -> None:
        news = market.add_news(kind, headline.headline, headline.body, asset_ids, t=t)
        await connections.broadcast(NewsMessage(item=news_out(news)))

    return publish


def announce_stage_change(change: StageChange) -> None:
    star = market.get_star(change.asset_id)
    publish = publisher("lifecycle", [star.id], change.t)
    worker.request_stage_headline(star.name, star.spectral_type, change.old_stage, change.new_stage, publish)


def announce_event(event: Event) -> None:
    star = market.get_star(event.asset_id)
    facts = {"name": star.name, "stage": STAGE_LABELS[star.stage], **event.facts}
    publish = publisher("event", [star.id], event.t)
    worker.request_headline(event_prompt(event.type, facts), event_fallback(event.type, facts), publish)


async def tick_loop() -> None:
    while True:
        await asyncio.sleep(config.TICK_SECONDS)
        report = market.advance()
        for change in report.stage_changes:
            announce_stage_change(change)
        for event in report.events:
            announce_event(event)
        ticks = [AssetTick(id=s.id, stage=s.stage, price=s.price, L=s.L) for s in market.stars.values()]
        await connections.broadcast(TickMessage(t=market.tick, assets=ticks))
        if market.tick % config.LEADERBOARD_EVERY_TICKS == 0:
            await connections.broadcast(LeaderboardMessage(rows=leaderboard_out()))


@asynccontextmanager
async def lifespan(app: FastAPI):
    tasks = [asyncio.create_task(tick_loop()), asyncio.create_task(worker.run())]
    yield
    for task in tasks:
        task.cancel()
    for task in tasks:
        with suppress(asyncio.CancelledError):
            await task
    await gemma.aclose()


app = FastAPI(title="Star Market", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/join")
async def join(request: JoinRequest) -> JoinResponse:
    player = market.join(request.nickname)
    return JoinResponse(player_id=player.id)


@app.get("/state")
async def state() -> StateSnapshot:
    return StateSnapshot(
        t=market.tick,
        assets=[asset_out(star) for star in market.stars.values()],
        leaderboard=leaderboard_out(),
        news=[news_out(news) for news in market.news],
    )


@app.get("/assets/{asset_id}/history")
async def asset_history(asset_id: str) -> list[PricePoint]:
    try:
        star = market.get_star(asset_id)
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return [PricePoint(t=t, price=price) for t, price in star.history]


@app.get("/portfolio/{player_id}")
async def portfolio(player_id: str) -> Portfolio:
    try:
        player = market.get_player(player_id)
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return portfolio_out(player)


@app.post("/trade")
async def trade(request: TradeRequest) -> Portfolio:
    try:
        market.trade(request.player_id, request.asset_id, request.side, request.qty)
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except MarketError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return portfolio_out(market.get_player(request.player_id))


# Director endpoints drive the game by hand for testing and the demo. No auth, by design.
@app.post("/director/force_stage")
async def force_stage(request: ForceStageRequest) -> Asset:
    try:
        old_stage = market.get_star(request.asset_id).stage
        star = market.force_next_stage(request.asset_id)
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except MarketError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    announce_stage_change(StageChange(star.id, old_stage, star.stage, market.tick))
    return asset_out(star)


@app.post("/director/fire_event")
async def fire_event(request: FireEventRequest) -> Asset:
    try:
        event = market.start_event(request.type, request.asset_id)
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except MarketError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    announce_event(event)
    return asset_out(market.get_star(event.asset_id))


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    connections.connections.add(websocket)
    try:
        while True:
            await websocket.receive_text()  # clients don't send anything yet; this waits for disconnect
    except WebSocketDisconnect:
        pass
    finally:
        connections.connections.discard(websocket)
