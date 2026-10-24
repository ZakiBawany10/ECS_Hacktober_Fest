import math
import random

import pytest

from app import config
from app.lifecycle import DARK_STAGES, MAIN_SEQUENCE_L_BOUNDS, STAGE_L_BOUNDS, generate_luminosity
from app.market import Market, MarketError, NotFoundError
from app.pricing import price_from_luminosity, twinkle


def test_price_follows_log_luminosity():
    assert price_from_luminosity(1.0) == 500.0  # the Sun: 100 × (0 + 5)
    assert price_from_luminosity(1_000.0) == 800.0
    assert price_from_luminosity(3e-4) == pytest.approx(147.71, abs=0.01)  # smallest M star
    assert price_from_luminosity(0.0) == 0.0  # black hole


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
            if star.stage in DARK_STAGES:
                continue
            low, high = STAGE_L_BOUNDS[star.stage]
            assert low <= star.base_L <= high * (1 + 1e-12)
        assert star.price == price_from_luminosity(star.L)
    return stages


@pytest.mark.parametrize(
    ("star_id", "expected"),
    [
        ("kestrel", ["main_sequence", "blue_hypergiant", "supernova", "black_hole"]),  # O
        ("brightwater", ["main_sequence", "red_hypergiant", "supernova", "neutron_star"]),  # B
        ("altra", ["main_sequence", "blue_giant", "planetary_nebula", "white_dwarf"]),  # A
        ("fenwick", ["main_sequence", "blue_giant", "planetary_nebula", "white_dwarf"]),  # F
        ("sol-nova", ["main_sequence", "red_giant", "planetary_nebula", "white_dwarf"]),  # G
        ("kora", ["main_sequence", "red_giant", "planetary_nebula", "white_dwarf"]),  # K
        ("ember", ["main_sequence", "red_giant", "planetary_nebula", "white_dwarf"]),  # M
    ],
)
def test_spectral_type_decides_lifecycle(star_id, expected):
    assert walk_lifecycle(make_market(), star_id) == expected


@pytest.mark.parametrize(("spectral_type", "stage"), [("O", "blue_hypergiant"), ("B", "red_hypergiant")])
def test_hypergiant_starts_above_main_sequence(spectral_type, stage):
    assert STAGE_L_BOUNDS[stage][0] >= MAIN_SEQUENCE_L_BOUNDS[spectral_type][1]


def test_path_ignores_mass():
    market = make_market()
    market.stars["sol-nova"].mass = 50.0
    assert walk_lifecycle(market, "sol-nova")[1] == "red_giant"


def test_black_hole_price_sits_at_zero():
    market = make_market()
    walk_lifecycle(market, "kestrel")
    star = market.stars["kestrel"]
    for _ in range(20):
        market.advance()
    assert star.L == 0.0
    assert [price for _, price in list(star.history)[-20:]] == [0.0] * 20


def test_black_hole_cannot_be_traded():
    market = make_market()
    player = market.join("zaki")
    market.trade(player.id, "kestrel", "buy", 1)
    walk_lifecycle(market, "kestrel")
    for side in ("buy", "sell"):
        with pytest.raises(MarketError, match="black hole"):
            market.trade(player.id, "kestrel", side, 1)
    assert player.holdings == {"kestrel": 1}


def test_supernova_snaps_to_new_luminosity():
    market = make_market()
    star = market.stars["kestrel"]
    star.stage = "blue_hypergiant"
    star.ticks_left = 1
    market.advance()
    assert star.stage == "supernova"
    assert abs(math.log10(star.L) - math.log10(star.base_L)) < 0.05  # only one tick of twinkle


def test_seconds_left_starts_star_late_in_life():
    market = make_market()
    assert market.stars["kestrel"].ticks_left == round(40 / config.TICK_SECONDS)


def test_force_next_stage_walks_the_path():
    market = make_market()
    stages = [market.force_next_stage("kestrel").stage for _ in range(3)]
    assert stages == ["blue_hypergiant", "supernova", "black_hole"]
    assert market.stars["kestrel"].price == 0.0
    with pytest.raises(MarketError, match="final stage"):
        market.force_next_stage("kestrel")
    with pytest.raises(NotFoundError):
        market.force_next_stage("nope")
