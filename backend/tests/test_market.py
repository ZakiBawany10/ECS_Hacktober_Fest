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
    next_stage,
    seconds_to_ticks,
)
from app.events import MAJOR_TYPES, MOMENTS, eligible
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
    """A seeded market with no random events, so prices only move when a test says so."""
    return Market(rng=random.Random(0), random_events=False)


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
    while next_stage(star.stage, star.spectral_type) is not None:
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
    assert market.force_next_stage("altra").new_stage == "neutron_star"
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


def test_advance_reports_stage_changes():
    market = make_market()
    assert market.advance().stage_changes == []
    star = market.stars["kestrel"]
    star.ticks_left = 1
    [change] = market.advance().stage_changes
    assert (change.asset_id, change.old_stage, change.new_stage, change.t) == (
        "kestrel",
        "main_sequence",
        "blue_hypergiant",
        market.tick,
    )


def test_news_keeps_the_latest_items():
    market = make_market()
    for i in range(config.NEWS_LENGTH + 5):
        market.add_news("system", f"Item {i}", "Body.", [])
    assert len(market.news) == config.NEWS_LENGTH
    assert market.news[-1].headline == f"Item {config.NEWS_LENGTH + 4}"
    assert market.add_news("lifecycle", "Old", "Body.", ["kestrel"], t=-3).t == -3


def test_seconds_left_starts_star_late_in_life():
    market = make_market()
    assert market.stars["kestrel"].ticks_left == round(40 / config.TICK_SECONDS)


def test_force_next_stage_walks_the_path():
    market = make_market()
    stages = [market.force_next_stage("kestrel").new_stage for _ in range(3)]
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


def test_random_events_average_one_per_gap():
    market = Market(rng=random.Random(5))
    ticks = 2400
    started = sum(len(market.advance().events) for _ in range(ticks))
    expected = ticks * config.TICK_SECONDS / config.EVENT_MEAN_GAP_SECONDS
    assert 0.7 * expected < started < 1.3 * expected


def test_meteor_strike_dips_then_recovers():
    market = make_market()
    star = market.stars["sol-nova"]
    event = market.start_event("meteor_strike", "sol-nova")
    peak = star.multipliers[event.id].target
    assert 0.91 <= peak <= 0.97
    for _ in range(5):
        market.advance()
    assert star.price < 0.98 * market_price(star.L, star.impact)
    for _ in range(60):
        market.advance()
    assert star.multipliers == {} and market.events == {}
    assert star.price == market_price(star.L, star.impact)


def test_stellar_flare_lifts_price_and_trades_fill_at_it():
    market = make_market()
    star = market.stars["ember"]
    market.start_event("stellar_flare", "ember")
    for _ in range(4):
        market.advance()
    assert star.event_multiplier > 1.1
    player = market.join("zaki")
    trade = market.trade(player.id, "ember", "buy", 1)
    assert trade.price == star.priced_at(star.impact) > market_price(star.L, star.impact)


def test_events_need_an_eligible_star():
    market = make_market()
    market.force_next_stage("kestrel")
    with pytest.raises(MarketError, match="stellar flare"):
        market.start_event("stellar_flare", "kestrel")  # a hypergiant, not main sequence
    with pytest.raises(MarketError):
        market.start_event("coronal_collapse", "sol-nova")  # not a red giant yet
    walk_lifecycle(market, "kestrel")
    with pytest.raises(MarketError):
        market.start_event("meteor_strike", "kestrel")  # black hole
    with pytest.raises(NotFoundError):
        market.start_event("meteor_strike", "nope")


def test_coronal_collapse_brings_next_stage_forward():
    market = make_market()
    star = market.stars["sol-nova"]
    market.force_next_stage("sol-nova")
    star.ticks_left = 100
    market.start_event("coronal_collapse", "sol-nova")
    assert 40 <= star.ticks_left <= 70


def test_event_effect_survives_a_stage_change():
    market = make_market()
    star = market.stars["sol-nova"]
    event = market.start_event("meteor_strike", "sol-nova")
    market.force_next_stage("sol-nova")
    assert event.id in star.multipliers
    assert star.price == star.priced_at(star.impact)


def test_spawned_star_starts_as_protostar_and_ignites_at_true_value():
    market = make_market()
    star = market.spawn_star("F")
    assert star.stage == "protostar" and star.id in market.stars
    forecast = star.forecast
    while star.stage == "protostar":
        market.advance()
    assert star.stage == "main_sequence"
    assert star.base_L == forecast.true_L
    assert star.L == pytest.approx(forecast.true_L, rel=0.05)  # plus one tick of twinkle
    low, high = MAIN_SEQUENCE_L_BOUNDS["F"]
    assert low <= star.base_L <= high
    assert walk_lifecycle(market, star.id) == ["main_sequence", "blue_giant", "supernova", "neutron_star"]


def test_protostar_price_follows_its_forecast():
    market = make_market()
    star = market.spawn_star("G")
    forecast = star.forecast
    updates = 0
    while star.ticks_left > 1:
        updates += len(market.advance().forecast_updates)
        expected = forecast.true_price * (1 + forecast.final_error)
        assert star.price == pytest.approx(expected, rel=0.2)
    assert updates == 1  # one "forecast updated" item, halfway through
    assert star.price == pytest.approx(forecast.true_price * (1 + forecast.final_error), rel=0.05)


def test_ignition_reports_how_the_forecast_did():
    market = make_market()
    star = market.spawn_star("K")
    star.forecast.final_error = 0.3  # forecast far too high
    change = market.force_next_stage(star.id)
    assert (change.old_stage, change.new_stage) == ("protostar", "main_sequence")
    assert "dimmer than forecast" in change.note


def test_spawned_names_and_ids_are_unique():
    market = make_market()
    market.name_pool.extend(["Sol Nova", "Wisp", "wisp"])
    stars = [market.spawn_star() for _ in range(3)]
    names = [star.name for star in stars]
    assert names[0] == "Wisp"  # Sol Nova is taken, and so is wisp once Wisp is used
    assert len({name.lower() for name in names} | {"sol nova"}) == 4
    assert len({star.id for star in market.stars.values()}) == len(market.stars)


def test_spawning_stops_at_the_living_star_limit():
    market = Market(rng=random.Random(2))
    for _ in range(3000):
        market.advance()
        assert len(market.living_stars()) <= config.MAX_LIVING_STARS
    assert any(star.forecast is not None for star in market.stars.values())


def test_black_hole_is_delisted_after_a_minute():
    market = make_market()
    player = market.join("zaki")
    market.trade(player.id, "kestrel", "buy", 1)
    walk_lifecycle(market, "kestrel")
    market.events.clear()
    delisted = []
    for _ in range(seconds_to_ticks(60)):
        delisted += market.advance().delisted
    assert [star.id for star in delisted] == ["kestrel"]
    star = market.stars["kestrel"]  # kept for the map
    assert not star.listed and star.ticks_left is None
    assert player.holdings == {}
    assert market.net_worth(player) == player.cash
    with pytest.raises(MarketError, match="delisted"):
        market.trade(player.id, "kestrel", "buy", 1)
    assert market.advance().delisted == []  # only once
    assert star not in market.living_stars()


def test_protostars_dodge_events():
    market = make_market()
    star = market.spawn_star()
    for event_type in ("meteor_strike", "stellar_flare", "coronal_collapse"):
        with pytest.raises(MarketError):
            market.start_event(event_type, star.id)


def start_dyson(market: Market, star_id: str = "sol-nova", completes=True, stop=1.0, stalls=()):
    event = market.start_event("dyson_sphere", star_id, director=True)
    event.completes, event.stop_progress, event.stalls = completes, stop, list(stalls)
    return event


def news_moments(market: Market, ticks: int) -> list[tuple[str, str]]:
    moments = []
    for _ in range(ticks):
        moments += [(news.event_type, news.moment) for news in market.advance().event_news]
    return moments


def test_dyson_sphere_dims_along_the_build_curve_and_completes():
    market = make_market()
    star = market.stars["sol-nova"]
    event = start_dyson(market)
    assert [(n.moment, n.flash) for n in market.take_event_news()] == [("start", True)]
    for _ in range(seconds_to_ticks(60)):
        market.advance()
    assert star.event_multiplier == pytest.approx(1 - 0.97 * 0.36, abs=0.03)  # 5.1 table: 65% at 60 s
    moments = news_moments(market, seconds_to_ticks(250))
    assert ("dyson_sphere", "complete") in moments
    assert moments.count(("dyson_sphere", "update")) >= 6
    assert star.event_multiplier == pytest.approx(0.03, abs=0.005)
    assert event.id in market.events and not event.counts_towards_cap  # enclosed for good
    assert market.has_major_event(star)


def test_abandoned_dyson_sphere_rallies_back():
    market = make_market()
    star = market.stars["sol-nova"]
    event = start_dyson(market, completes=False, stop=0.5)
    moments = news_moments(market, seconds_to_ticks(140))
    assert ("dyson_sphere", "abandoned") in moments
    assert event.id not in market.events and star.multipliers == {}


def test_dyson_stall_pauses_progress():
    market = make_market()
    event = start_dyson(market, stalls=[(10, 20)])
    moments = news_moments(market, 40)
    assert ("dyson_sphere", "stall") in moments
    assert event.build_ticks == 20


def test_star_evolving_destroys_its_dyson_sphere():
    market = make_market()
    star = market.stars["sol-nova"]
    event = start_dyson(market)
    for _ in range(seconds_to_ticks(120)):
        market.advance()
    market.force_next_stage("sol-nova")
    moments = news_moments(market, seconds_to_ticks(40))
    assert ("dyson_sphere", "destroyed") in moments
    assert event.id not in market.events and star.multipliers == {}


def test_mysterious_dimming_dips_then_clears():
    market = make_market()
    star = market.stars["kora"]
    event = market.start_event("mysterious_dimming", "kora")
    event.early_dyson = False
    lowest = 1.0
    moments = []
    while event.id in market.events:
        moments += [(n.event_type, n.moment) for n in market.advance().event_news]
        lowest = min(lowest, star.event_multiplier)
    assert lowest < 0.95
    assert [m for _, m in moments] == ["start", "update", "cleared"]
    assert star.multipliers == {}


def test_early_dyson_dimming_turns_into_a_sphere_without_a_jump():
    market = make_market()
    star = market.stars["kora"]
    dimming = market.start_event("mysterious_dimming", "kora")
    dimming.early_dyson = True
    while dimming.id in market.events:
        before = star.event_multiplier
        report = market.advance()
    [sphere] = report.events
    assert sphere.type == "dyson_sphere" and sphere.asset_id == "kora"
    assert star.event_multiplier == pytest.approx(before, abs=0.02)
    assert ("dyson_sphere", "start") in [(n.event_type, n.moment) for n in report.event_news]


def test_major_event_limits():
    market = make_market()
    start_dyson(market, "sol-nova")
    with pytest.raises(MarketError):
        market.start_event("mysterious_dimming", "sol-nova", director=True)  # one major per star
    for star_id in ("kora", "ember", "fenwick"):
        market.start_event("dyson_sphere" if star_id == "kora" else "mysterious_dimming", star_id, director=True)
    assert market.major_event_count() == 4
    assert not market.can_start_dyson()  # two building already
    assert not any(eligible(t, market.stars["altra"], market) for t in MAJOR_TYPES)  # market-wide cap
    market.start_event("meteor_strike", "altra")  # minor events don't count


def test_a_dyson_sphere_starts_by_minute_eight():
    market = Market(rng=random.Random(3))
    for _ in range(seconds_to_ticks(config.DYSON_DEADLINE_SECONDS + 120)):
        market.advance()
    assert market.dysons_started >= 1


def test_every_event_news_moment_is_known():
    market = Market(rng=random.Random(4))
    moments = news_moments(market, 3000)
    assert moments and all(moment in MOMENTS[event_type] for event_type, moment in moments)
