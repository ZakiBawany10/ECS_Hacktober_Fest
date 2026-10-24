"""Request and response shapes shared with the frontend. Keep in sync with frontend types."""

from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

from .events import EventType
from .lifecycle import Stage
from .newsroom import NewsKind

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


class FireEventRequest(BaseModel):
    type: EventType
    asset_id: str


class SpawnStarRequest(BaseModel):
    spectral_type: Literal["O", "B", "A", "F", "G", "K", "M"] | None = None  # random if left out


class Asset(BaseModel):
    id: str
    name: str
    kind: Literal["star"]
    stage: Stage
    # Birth values that stay the same as the star evolves. For a protostar they're the forecast's
    # projection, which can change, and the true values appear when it ignites.
    spectral_type: str
    mass: float  # solar masses
    temperature: float  # kelvin
    L: float  # luminosity, solar units
    price: float
    shares_total: float
    shares_available: float
    listed: bool  # False once delisted: show it on the map, not the exchange


class AssetTick(BaseModel):
    id: str
    stage: Stage
    price: float
    L: float
    listed: bool


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
    source: str  # the outlet reporting it, such as "StarWire"
    side: Literal["human", "alien"]
    flash: bool  # a key moment: worth a pop-up banner


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


class ListedMessage(BaseModel):
    """A new star has spawned. It also appears in tick messages from now on."""

    type: Literal["listed"] = "listed"
    asset: Asset


class DelistedMessage(BaseModel):
    """A star has left the exchange. It stays in /state and tick messages with listed: false, for the
    map, and its holdings are gone."""

    type: Literal["delisted"] = "delisted"
    asset_id: str
