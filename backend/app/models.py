"""Request and response shapes shared with the frontend. Keep in sync with frontend types."""

from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

from .lifecycle import Stage
from .market import NewsKind

Nickname = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20)]


class JoinRequest(BaseModel):
    nickname: Nickname


class JoinResponse(BaseModel):
    player_id: str


class TradeRequest(BaseModel):
    player_id: str
    asset_id: str
    side: Literal["buy", "sell"]
    qty: float = Field(gt=0)


class ForceStageRequest(BaseModel):
    asset_id: str


class Asset(BaseModel):
    id: str
    name: str
    kind: Literal["star"]
    stage: Stage
    spectral_type: str  # at birth; stays the same as the star evolves
    mass: float  # solar masses
    temperature: float  # kelvin
    L: float  # luminosity, solar units
    price: float
    shares_total: float
    shares_available: float


class AssetTick(BaseModel):
    id: str
    stage: Stage
    price: float
    L: float


class Portfolio(BaseModel):
    player_id: str
    nickname: str
    cash: float
    holdings: dict[str, float]  # asset_id -> qty
    net_worth: float


class LeaderboardRow(BaseModel):
    nickname: str
    net_worth: float


class PricePoint(BaseModel):
    t: int
    price: float


class NewsItem(BaseModel):
    id: str
    t: int  # tick the news is about
    kind: NewsKind
    headline: str
    body: str
    asset_ids: list[str]


class StateSnapshot(BaseModel):
    t: int
    assets: list[Asset]
    leaderboard: list[LeaderboardRow]
    news: list[NewsItem]  # the last 50 items, oldest first


class TickMessage(BaseModel):
    type: Literal["tick"] = "tick"
    t: int
    assets: list[AssetTick]


class LeaderboardMessage(BaseModel):
    type: Literal["leaderboard"] = "leaderboard"
    rows: list[LeaderboardRow]


class NewsMessage(BaseModel):
    type: Literal["news"] = "news"
    item: NewsItem
