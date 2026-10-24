"""Request and response shapes shared with the frontend. Keep in sync with frontend types."""

from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

from .lifecycle import Stage

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


class StateSnapshot(BaseModel):
    t: int
    assets: list[Asset]
    leaderboard: list[LeaderboardRow]


class TickMessage(BaseModel):
    type: Literal["tick"] = "tick"
    t: int
    assets: list[AssetTick]


class LeaderboardMessage(BaseModel):
    type: Literal["leaderboard"] = "leaderboard"
    rows: list[LeaderboardRow]
