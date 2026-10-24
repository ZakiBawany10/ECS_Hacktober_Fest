import random

import pytest

from app import config
from app.market import Market, MarketError, NotFoundError
from app.pricing import price_from_luminosity, twinkle


def test_price_follows_log_luminosity():
    assert price_from_luminosity(1.0) == 500.0  # the Sun: 100 × (0 + 5)
    assert price_from_luminosity(1_000.0) == 800.0
    assert price_from_luminosity(3e-4) == pytest.approx(147.71, abs=0.01)  # smallest M star


def test_twinkle_stays_near_base():
    rng = random.Random(0)
    L = 1.0
    for _ in range(1_000):
        L = twinkle(L, 1.0, rng)
    assert 0.8 < L < 1.25


def make_market() -> Market:
    return Market(rng=random.Random(0))


def test_join_gives_starting_cash():
    market = make_market()
    player = market.join("zaki")
    assert player.cash == config.STARTING_CASH
    assert market.net_worth(player) == config.STARTING_CASH


def test_buy_and_sell_round_trip():
    market = make_market()
    player = market.join("zaki")
    star = market.stars["sol-nova"]

    market.trade(player.id, star.id, "buy", 2.5)
    assert player.holdings == {star.id: 2.5}
    assert player.cash == pytest.approx(config.STARTING_CASH - 2.5 * star.price)
    assert star.shares_available == config.SHARES_PER_STAR - 2.5

    market.trade(player.id, star.id, "sell", 2.5)
    assert player.holdings == {}
    assert player.cash == pytest.approx(config.STARTING_CASH)
    assert star.shares_available == config.SHARES_PER_STAR


def test_cannot_overspend_or_oversell():
    market = make_market()
    player = market.join("zaki")
    star = market.stars["kestrel"]
    with pytest.raises(MarketError, match="cash"):
        market.trade(player.id, star.id, "buy", 1_000)
    with pytest.raises(MarketError, match="hold"):
        market.trade(player.id, star.id, "sell", 1)


def test_share_supply_is_capped():
    market = make_market()
    star = market.stars["ember"]
    star.shares_held = config.SHARES_PER_STAR - 5
    player = market.join("zaki")
    with pytest.raises(MarketError, match="available"):
        market.trade(player.id, star.id, "buy", 6)
    market.trade(player.id, star.id, "buy", 5)
    assert star.shares_available == 0


def test_unknown_ids_raise_not_found():
    market = make_market()
    player = market.join("zaki")
    with pytest.raises(NotFoundError):
        market.trade("nobody", "sol-nova", "buy", 1)
    with pytest.raises(NotFoundError):
        market.trade(player.id, "no-such-star", "buy", 1)


def test_leaderboard_sorted_by_net_worth():
    market = make_market()
    a = market.join("a")
    b = market.join("b")
    market.trade(b.id, "sol-nova", "buy", 1)
    market.stars["sol-nova"].price *= 2
    assert [p.nickname for p, _ in market.leaderboard()] == ["b", "a"]


def test_advance_records_history():
    market = make_market()
    market.advance()
    market.advance()
    star = market.stars["sol-nova"]
    assert [t for t, _ in star.history] == [0, 1, 2]
    assert star.price == price_from_luminosity(star.L)
