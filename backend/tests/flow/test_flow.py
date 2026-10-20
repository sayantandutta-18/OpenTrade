"""Tests for synthetic order flow generation, determinism, and profile stylized facts."""

from impactlab.engine.events import events_to_jsonl
from impactlab.engine.matcher import MatchingEngine
from impactlab.flow.generators import FlowSimulator
from impactlab.flow.profiles import LARGE_CAP, MID_CAP, SMALL_CAP, get_profile


def test_profile_lookup() -> None:
    p = get_profile("large_cap")
    assert p.name == "large_cap"
    assert p.reference_price == 250_000
    assert get_profile("mid_cap").reference_price == 45_000
    assert get_profile("small_cap").reference_price == 8_500


def test_seed_determinism() -> None:
    # Run 1
    engine1 = MatchingEngine(tick_size=LARGE_CAP.tick_size)
    sim1 = FlowSimulator(LARGE_CAP, seed=42)
    sim1.warmup(engine1, seconds=10.0)
    sim1.advance(engine1, seconds=20.0)
    log1 = events_to_jsonl(engine1.events)

    # Run 2 with same seed
    engine2 = MatchingEngine(tick_size=LARGE_CAP.tick_size)
    sim2 = FlowSimulator(LARGE_CAP, seed=42)
    sim2.warmup(engine2, seconds=10.0)
    sim2.advance(engine2, seconds=20.0)
    log2 = events_to_jsonl(engine2.events)

    assert log1 == log2
    assert engine1.book.best_bid == engine2.book.best_bid
    assert engine1.book.best_ask == engine2.book.best_ask
    assert len(engine1.trades) == len(engine2.trades)


def test_different_seeds_produce_different_runs() -> None:
    engine1 = MatchingEngine(tick_size=LARGE_CAP.tick_size)
    sim1 = FlowSimulator(LARGE_CAP, seed=42)
    sim1.advance(engine1, seconds=10.0)

    engine2 = MatchingEngine(tick_size=LARGE_CAP.tick_size)
    sim2 = FlowSimulator(LARGE_CAP, seed=999)
    sim2.advance(engine2, seconds=10.0)

    assert engine1.events != engine2.events


def test_long_run_10_minutes_invariants() -> None:
    # 10 simulated minutes = 600 simulated seconds on mid-cap
    engine = MatchingEngine(tick_size=MID_CAP.tick_size)
    sim = FlowSimulator(MID_CAP, seed=123)
    sim.warmup(engine, seconds=30.0)
    events_count = sim.advance(engine, seconds=600.0)

    assert events_count > 0
    assert engine.book.best_bid is not None
    assert engine.book.best_ask is not None
    assert engine.book.best_bid < engine.book.best_ask
    engine.check_invariants()


def test_profile_stylized_facts_spread_and_depth() -> None:
    # Run large cap
    eng_large = MatchingEngine(tick_size=LARGE_CAP.tick_size)
    sim_large = FlowSimulator(LARGE_CAP, seed=10)
    sim_large.warmup(eng_large, seconds=30.0)
    snap_large = eng_large.book.snapshot()

    # Run small cap
    eng_small = MatchingEngine(tick_size=SMALL_CAP.tick_size)
    sim_small = FlowSimulator(SMALL_CAP, seed=10)
    sim_small.warmup(eng_small, seconds=30.0)
    snap_small = eng_small.book.snapshot()

    # Relative spread in basis points: (spread / mid) * 10,000
    spread_bps_large = (
        (snap_large.spread / snap_large.mid) * 10_000 if snap_large.spread and snap_large.mid else 0
    )
    spread_bps_small = (
        (snap_small.spread / snap_small.mid) * 10_000 if snap_small.spread and snap_small.mid else 0
    )

    assert spread_bps_small > spread_bps_large, (
        f"Small cap spread bps {spread_bps_small} should be wider than Large cap {spread_bps_large}"
    )

    # Total resting liquidity is much deeper in large cap than small cap
    assert (
        snap_large.total_bid_qty + snap_large.total_ask_qty
        > snap_small.total_bid_qty + snap_small.total_ask_qty
    )
