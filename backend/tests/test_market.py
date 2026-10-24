import math
import random

import pytest

from app import config
from app.lifecycle import (
    DARK_STAGES,
    DECLINE_SECONDS,
    LIFECYCLE_PATHS,
    MAIN_SEQUENCE_L_BOUNDS,
    STAGE_L_BOUNDS,
    SUPERNOVA_DROP_SECONDS,
    SUPERNOVA_GLOW_SECONDS,
    generate_luminosity,
    seconds_to_ticks,
)
from app.market import Market, MarketError, NotFoundError
from app.pricing import apply_impact, luminosity_from_price, market_price, price_from_luminosity, twinkle


def test_price_follows_log_luminosity():
    assert price_from_luminosity(1.0) == 500.0  # the Sun: 100 × (0 + 5)
    assert price_from_luminosity(1_000.0) == 800.0
    assert price_from_luminosity(3e-4) == pytest.approx(147.71, abs=0.01)  # smallest M star
    assert price_from_luminosity(0.0) == 0.0  # black hole
    for price in (0.0, 147.71, 500.0, 3300.0):
        assert price_from_luminosity(luminosity_from_price(price)) == price


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

    price_before = star.price

    buy = market.trade(player.id, star.id, "buy", 2.5)
    assert player.holdings == {star.id: 2.5}
    assert player.cash == pytest.approx(config.STARTING_CASH - 2.5 * buy.price)
    assert star.shares_available == config.SHARES_PER_STAR - 2.5
    assert buy.price > price_before  # the buy pushed the price up and filled there

    sell = market.trade(player.id, star.id, "sell", 2.5)
    assert player.holdings == {}
    assert sell.price < buy.price
    assert player.cash < config.STARTING_CASH  # paying your own impact means a round trip costs a little
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
            if star.stage in DARK_STAGES or star.stage not in STAGE_L_BOUNDS:
                continue
            low, high = STAGE_L_BOUNDS[star.stage]
            assert low <= star.base_L <= high * (1 + 1e-12)
        assert star.price == market_price(star.L, star.impact)
    return stages


@pytest.mark.parametrize(
    ("star_id", "expected"),
    [
        ("kestrel", ["main_sequence", "blue_hypergiant", "supernova", "black_hole"]),  # O
        ("brightwater", ["main_sequence", "red_hypergiant", "supernova", "black_hole"]),  # B
        ("altra", ["main_sequence", "blue_giant", "supernova", "neutron_star"]),  # A
        ("fenwick", ["main_sequence", "blue_giant", "supernova", "neutron_star"]),  # F
        ("sol-nova", ["main_sequence", "red_giant", "white_dwarf"]),  # G
        ("kora", ["main_sequence", "red_giant", "white_dwarf"]),  # K
        ("ember", ["main_sequence", "red_giant", "white_dwarf"]),  # M
    ],
)
def test_spectral_type_decides_lifecycle(star_id, expected):
    assert walk_lifecycle(make_market(), star_id) == expected


@pytest.mark.parametrize(("spectral_type", "stage"), [("O", "blue_hypergiant"), ("B", "red_hypergiant")])
def test_hypergiant_starts_above_main_sequence(spectral_type, stage):
    assert STAGE_L_BOUNDS[stage][0] >= MAIN_SEQUENCE_L_BOUNDS[spectral_type][1]


@pytest.mark.parametrize(("stage", "top_price"), [("white_dwarf", 700.0), ("neutron_star", 600.0)])
def test_remnant_prices_match_table_5(stage, top_price):
    low, high = STAGE_L_BOUNDS[stage]
    assert price_from_luminosity(low) == 0.0
    assert price_from_luminosity(high) == top_price


def test_path_ignores_mass():
    market = make_market()
    market.stars["sol-nova"].mass = 50.0
    assert walk_lifecycle(market, "sol-nova")[1] == "red_giant"


@pytest.mark.parametrize("star_id", ["kestrel", "brightwater"])  # O and B
def test_black_hole_price_sits_at_zero(star_id):
    market = make_market()
    walk_lifecycle(market, star_id)
    star = market.stars[star_id]
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


def start_supernova(market: Market, star_id: str):
    """Put a star on the tick before its supernova and return it with its luminosity price."""
    star = market.stars[star_id]
    path = LIFECYCLE_PATHS[star.spectral_type]
    star.stage = path[path.index("supernova") - 1]
    star.ticks_left = 1
    pre_price = price_from_luminosity(star.L)
    market.advance()
    assert star.stage == "supernova"
    return star, pre_price


def test_supernova_spikes_fades_then_drops_to_neutron_star():
    market = make_market()
    star, pre_price = start_supernova(market, "altra")
    assert star.price == pytest.approx(3 * pre_price, abs=0.02)
    glow_ticks = star.path[0].end_tick - market.tick
    low, high = SUPERNOVA_GLOW_SECONDS
    assert seconds_to_ticks(low) <= glow_ticks <= seconds_to_ticks(high)

    glow = [star.price]
    for _ in range(glow_ticks):
        market.advance()
        glow.append(star.price)
    assert glow == sorted(glow, reverse=True)
    assert glow[-1] == pytest.approx(2.7 * pre_price, abs=0.02)

    drop = []
    while star.stage == "supernova":
        market.advance()
        drop.append(star.price)
    assert len(drop) == seconds_to_ticks(SUPERNOVA_DROP_SECONDS)
    assert drop == sorted(drop, reverse=True)
    assert star.stage == "neutron_star"
    assert 0.0 <= star.price <= 600.0
    assert star.path == []


def test_black_hole_supernova_can_be_sold_until_it_collapses():
    market = make_market()
    player = market.join("zaki")
    market.trade(player.id, "brightwater", "buy", 2)
    star, _ = start_supernova(market, "brightwater")
    while market.tick < star.path[-1].end_tick - 1:
        market.advance()
    assert star.stage == "supernova"
    assert 0.0 < star.price < 1000.0
    market.trade(player.id, "brightwater", "sell", 1)
    market.advance()
    assert star.stage == "black_hole"
    assert star.price == 0.0


def test_forced_supernova_lands_on_its_remnant():
    market = make_market()
    star = market.stars["altra"]
    market.force_next_stage("altra")
    market.force_next_stage("altra")
    remnant_price = star.path[-1].end_price
    assert market.force_next_stage("altra").stage == "neutron_star"
    assert star.price == pytest.approx(remnant_price, abs=0.01)


def test_white_dwarf_declines_linearly_from_giant():
    market = make_market()
    star = market.stars["sol-nova"]
    market.force_next_stage("sol-nova")
    giant_price = star.price
    market.force_next_stage("sol-nova")
    assert star.stage == "white_dwarf"
    assert star.price == pytest.approx(giant_price, abs=0.01)
    target = price_from_luminosity(star.base_L)

    prices = [star.price]
    for _ in range(seconds_to_ticks(DECLINE_SECONDS)):
        market.advance()
        prices.append(star.price)
    steps = [a - b for a, b in zip(prices, prices[1:])]
    assert max(steps) - min(steps) < 0.05  # a straight line, give or take rounding
    assert prices[-1] == pytest.approx(target, abs=0.01)
    assert star.path == []
    market.advance()  # twinkle takes over again
    assert star.price == pytest.approx(target, rel=0.02)


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


def test_trading_pressure_moves_price_and_decays():
    market = make_market()
    star = market.stars["sol-nova"]
    price_before = star.price
    for nickname in "abcdefghij":  # a herd of 10 players each buying about 9k
        player = market.join(nickname)
        market.trade(player.id, star.id, "buy", 9_000 / star.price)
    assert star.impact == pytest.approx(1.09, abs=0.001)  # 10 × 1% × 9k/10k
    assert star.price == pytest.approx(price_before * star.impact, rel=0.01)
    for _ in range(30):
        market.advance()
    assert abs(star.impact - 1) < 0.01


def test_impact_is_capped():
    assert apply_impact(1.0, "buy", 10_000_000) == pytest.approx(1 + config.IMPACT_CAP)
    assert apply_impact(1.0, "sell", 10_000_000) == pytest.approx(1 - config.IMPACT_CAP)


def test_repeated_round_trips_never_make_money():
    market = make_market()
    player = market.join("zaki")
    star = market.stars["kestrel"]
    qty = 5_000 / star.price
    for _ in range(20):
        market.trade(player.id, star.id, "buy", qty)
        market.trade(player.id, star.id, "sell", qty)
    assert player.cash < config.STARTING_CASH
