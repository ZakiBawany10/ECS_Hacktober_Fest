import math
import random

import pytest

from app import config
from app.lifecycle import MAIN_SEQUENCE_L_BOUNDS, STAGE_L_BOUNDS, generate_luminosity
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


def test_seeded_luminosity_is_within_spectral_bounds():
    market = make_market()
    for star in market.stars.values():
        low, high = MAIN_SEQUENCE_L_BOUNDS[star.spectral_type]
        assert low <= star.L <= high
        assert star.base_L == star.L
        assert star.stage == "main_sequence"


def test_generate_luminosity_stays_in_bounds():
    rng = random.Random(1)
    for bounds in [*MAIN_SEQUENCE_L_BOUNDS.values(), *STAGE_L_BOUNDS.values()]:
        for _ in range(200):
            assert bounds[0] <= generate_luminosity(bounds, rng) <= bounds[1] * (1 + 1e-12)


def walk_lifecycle(market: Market, star_id: str) -> list[str]:
    """Advance a star through every stage, skipping the waiting, and return the stages it visited."""
    star = market.stars[star_id]
    stages = [star.stage]
    while star.ticks_left is not None:
        star.ticks_left = 1
        market.advance()
        if star.stage != stages[-1]:
            stages.append(star.stage)
            low, high = STAGE_L_BOUNDS[star.stage]
            assert low <= star.base_L <= high * (1 + 1e-12)
        assert star.price == price_from_luminosity(star.L)
    return stages


def test_heavy_stars_go_supernova():
    market = make_market()
    assert walk_lifecycle(market, "kestrel") == [
        "main_sequence", "red_supergiant", "supernova", "black_hole",
    ]  # 40 M☉
    assert walk_lifecycle(market, "brightwater") == [
        "main_sequence", "red_supergiant", "supernova", "neutron_star",
    ]  # 8 M☉


def test_sun_like_star_becomes_white_dwarf():
    market = make_market()
    assert walk_lifecycle(market, "sol-nova") == [
        "main_sequence", "red_giant", "planetary_nebula", "white_dwarf",
    ]


def test_red_dwarf_never_evolves():
    market = make_market()
    star = market.stars["ember"]
    assert star.ticks_left is None
    for _ in range(50):
        market.advance()
    assert star.stage == "main_sequence"


def test_supernova_snaps_to_new_luminosity():
    market = make_market()
    star = market.stars["kestrel"]
    star.stage = "red_supergiant"
    star.ticks_left = 1
    market.advance()
    assert star.stage == "supernova"
    assert abs(math.log10(star.L) - math.log10(star.base_L)) < 0.05  # only one tick of twinkle


def test_seconds_left_starts_star_late_in_life():
    market = make_market()
    assert market.stars["kestrel"].ticks_left == round(40 / config.TICK_SECONDS)
