"""Tests for execution strategies (Market, TWAP, VWAP, Passive) and dynamic simulation."""

from hypothesis import given
from hypothesis import strategies as st

from impactlab.engine.matcher import MatchingEngine
from impactlab.engine.models import Side
from impactlab.execution.passive import PassiveLimitStrategy
from impactlab.execution.twap import MarketStrategy, TWAPStrategy
from impactlab.execution.vwap import VWAPStrategy
from impactlab.flow.generators import FlowSimulator
from impactlab.flow.profiles import MID_CAP
from impactlab.impact.dynamic import simulate_dynamic_execution


@given(
    total_qty=st.integers(min_value=1, max_value=50_000),
    num_slices=st.integers(min_value=1, max_value=20),
)
def test_twap_slices_sum_to_total_quantity(total_qty: int, num_slices: int) -> None:
    strat = TWAPStrategy(duration_seconds=60.0, num_slices=num_slices)
    slices = strat.plan_slices(side=Side.BUY, total_qty=total_qty)
    assert sum(req.qty for _, req in slices) == total_qty


@given(
    total_qty=st.integers(min_value=1, max_value=50_000),
    num_slices=st.integers(min_value=1, max_value=20),
)
def test_vwap_slices_sum_to_total_quantity(total_qty: int, num_slices: int) -> None:
    strat = VWAPStrategy(duration_seconds=60.0, num_slices=num_slices)
    slices = strat.plan_slices(side=Side.BUY, total_qty=total_qty)
    assert sum(req.qty for _, req in slices) == total_qty


def test_market_strategy_single_slice() -> None:
    strat = MarketStrategy()
    slices = strat.plan_slices(side=Side.BUY, total_qty=500)
    assert len(slices) == 1
    assert slices[0][1].qty == 500


def test_passive_strategy_slices_sum() -> None:
    strat = PassiveLimitStrategy(num_slices=4)
    slices = strat.plan_slices(side=Side.SELL, total_qty=1000)
    assert sum(req.qty for _, req in slices) == 1000


def test_dynamic_simulation_does_not_mutate_live_engine() -> None:
    engine = MatchingEngine(tick_size=MID_CAP.tick_size)
    sim = FlowSimulator(MID_CAP, seed=42)
    sim.warmup(engine, seconds=10.0)

    events_before = len(engine.events)
    trades_before = len(engine.trades)
    best_bid_before = engine.book.best_bid
    best_ask_before = engine.book.best_ask

    strat = TWAPStrategy(duration_seconds=10.0, num_slices=3)
    res = simulate_dynamic_execution(
        engine=engine,
        simulator=sim,
        strategy=strat,
        side=Side.BUY,
        qty=300,
        quiet_seconds=5.0,
    )

    # Invariants on the live engine
    assert len(engine.events) == events_before
    assert len(engine.trades) == trades_before
    assert engine.book.best_bid == best_bid_before
    assert engine.book.best_ask == best_ask_before

    # Invariants on the dynamic result
    assert res.strategy_name == "twap"
    assert res.requested_qty == 300
    assert len(res.slice_executions) == 3
    assert sum(s.requested_qty for s in res.slice_executions) == 300


def test_dynamic_simulation_reproducibility() -> None:
    # Run 1
    engine1 = MatchingEngine(tick_size=MID_CAP.tick_size)
    sim1 = FlowSimulator(MID_CAP, seed=101)
    sim1.warmup(engine1, seconds=5.0)

    strat = TWAPStrategy(duration_seconds=10.0, num_slices=3)
    res1 = simulate_dynamic_execution(
        engine=engine1,
        simulator=sim1,
        strategy=strat,
        side=Side.BUY,
        qty=600,
        quiet_seconds=5.0,
    )

    # Run 2 with same setup
    engine2 = MatchingEngine(tick_size=MID_CAP.tick_size)
    sim2 = FlowSimulator(MID_CAP, seed=101)
    sim2.warmup(engine2, seconds=5.0)

    res2 = simulate_dynamic_execution(
        engine=engine2,
        simulator=sim2,
        strategy=strat,
        side=Side.BUY,
        qty=600,
        quiet_seconds=5.0,
    )

    assert res1.filled_qty == res2.filled_qty
    assert res1.total_notional == res2.total_notional
    assert res1.avg_price == res2.avg_price
    assert res1.slippage_bps == res2.slippage_bps
