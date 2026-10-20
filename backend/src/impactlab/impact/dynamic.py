"""Dynamic execution simulation with active order flow.

Runs execution strategies (Market, TWAP, VWAP, Passive) through a cloned MatchingEngine
while synthetic flow continues, measuring slippage, temporary and permanent impact,
and implementation shortfall without mutating the live engine.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass

from impactlab.engine.matcher import MatchingEngine
from impactlab.engine.models import Order, OrderType, Side
from impactlab.execution.base import ExecutionStrategy, SliceExecution
from impactlab.flow.generators import FlowSimulator


@dataclass(frozen=True, slots=True)
class DynamicImpactResult:
    """Detailed result of dynamic execution simulation."""

    strategy_name: str
    side: Side
    requested_qty: int
    filled_qty: int
    fill_ratio: float
    total_notional: int  # in paise
    avg_price: float | None  # in paise
    arrival_best: int | None  # in paise
    arrival_mid: float | None  # in paise
    execution_end_mid: float | None  # in paise
    post_quiet_mid: float | None  # in paise
    slippage_vs_best: float | None  # in paise per share
    slippage_vs_mid: float | None  # in paise per share
    slippage_bps: float | None
    temp_price_impact_bps: float | None
    perm_price_impact_bps: float | None
    impl_shortfall: float | None  # in paise
    slice_executions: tuple[SliceExecution, ...]


def simulate_dynamic_execution(
    engine: MatchingEngine,
    simulator: FlowSimulator,
    strategy: ExecutionStrategy,
    side: Side,
    qty: int,
    quiet_seconds: float = 10.0,
) -> DynamicImpactResult:
    """Simulate dynamic order execution on an isolated clone of the engine and simulator.

    Guarantees that the live engine and simulator are NOT mutated.

    Args:
        engine: Live MatchingEngine instance.
        simulator: Live FlowSimulator instance.
        strategy: Algorithmic strategy to execute (Market, TWAP, VWAP, Passive).
        side: BUY or SELL.
        qty: Total shares to execute.
        quiet_seconds: Post-execution quiet period to measure permanent impact.

    Returns:
        DynamicImpactResult with execution metrics and per-slice details.
    """
    # 1. Deep copy engine and simulator to guarantee zero mutation of live session
    eng: MatchingEngine = copy.deepcopy(engine)
    sim: FlowSimulator = copy.deepcopy(simulator)

    # 2. Record arrival benchmarks
    arrival_best = eng.book.best_ask if side == Side.BUY else eng.book.best_bid
    arrival_mid = eng.book.mid

    # 3. Plan strategy slices
    scheduled_slices = strategy.plan_slices(side=side, total_qty=qty, start_time=0.0)

    slice_records: list[SliceExecution] = []
    current_sim_time = 0.0
    order_id_seq = 1_000_000  # distinct range for algo orders

    total_filled_qty = 0
    total_notional = 0

    for idx, (t_offset, req) in enumerate(scheduled_slices):
        # Advance simulation flow up to the scheduled slice time
        dt = max(0.0, t_offset - current_sim_time)
        if dt > 0:
            sim.advance(eng, dt)
            current_sim_time = t_offset

        # Determine price for passive limit orders if not set
        price = req.price
        if req.type == OrderType.LIMIT and price is None:
            touch = eng.book.best_bid if side == Side.BUY else eng.book.best_ask
            if touch is not None:
                price = touch
            else:
                price = int(round(eng.book.mid or sim.fundamental_price))

        order = Order(
            id=order_id_seq,
            side=req.side,
            type=req.type,
            price=price,
            qty=req.qty,
            remaining=req.qty,
            ts=sim.current_time_us,
            owner=req.owner,
        )
        order_id_seq += 1

        trades = eng.submit(order)
        slice_filled = sum(t.qty for t in trades)
        slice_notional = sum(t.price * t.qty for t in trades)
        slice_avg = (slice_notional / slice_filled) if slice_filled > 0 else None

        total_filled_qty += slice_filled
        total_notional += slice_notional

        slice_records.append(
            SliceExecution(
                slice_index=idx + 1,
                scheduled_time=t_offset,
                executed_time=current_sim_time,
                requested_qty=req.qty,
                filled_qty=slice_filled,
                avg_price=slice_avg,
                trades=tuple(trades),
            )
        )

    execution_end_mid = eng.book.mid

    # 4. Quiet period to measure recovery and permanent impact
    if quiet_seconds > 0:
        sim.advance(eng, quiet_seconds)
    post_quiet_mid = eng.book.mid

    # 5. Compute aggregate metrics
    avg_price = (total_notional / total_filled_qty) if total_filled_qty > 0 else None
    fill_ratio = (total_filled_qty / qty) if qty > 0 else 0.0

    slippage_vs_best: float | None = None
    slippage_vs_mid: float | None = None
    slippage_bps: float | None = None
    temp_impact_bps: float | None = None
    perm_impact_bps: float | None = None
    impl_shortfall: float | None = None

    if avg_price is not None:
        if side == Side.BUY:
            slippage_vs_best = avg_price - arrival_best if arrival_best else None
            if arrival_mid and arrival_mid > 0:
                slippage_vs_mid = avg_price - arrival_mid
                slippage_bps = (slippage_vs_mid / arrival_mid) * 10_000
                impl_shortfall = total_notional - (total_filled_qty * arrival_mid)
                if post_quiet_mid:
                    perm_impact_bps = ((post_quiet_mid - arrival_mid) / arrival_mid) * 10_000
                if execution_end_mid and post_quiet_mid:
                    temp_impact_bps = ((execution_end_mid - post_quiet_mid) / arrival_mid) * 10_000
        else:
            # SELL
            slippage_vs_best = arrival_best - avg_price if arrival_best else None
            if arrival_mid and arrival_mid > 0:
                slippage_vs_mid = arrival_mid - avg_price
                slippage_bps = (slippage_vs_mid / arrival_mid) * 10_000
                impl_shortfall = (total_filled_qty * arrival_mid) - total_notional
                if post_quiet_mid:
                    perm_impact_bps = ((arrival_mid - post_quiet_mid) / arrival_mid) * 10_000
                if execution_end_mid and post_quiet_mid:
                    temp_impact_bps = ((post_quiet_mid - execution_end_mid) / arrival_mid) * 10_000

    return DynamicImpactResult(
        strategy_name=strategy.name,
        side=side,
        requested_qty=qty,
        filled_qty=total_filled_qty,
        fill_ratio=fill_ratio,
        total_notional=total_notional,
        avg_price=avg_price,
        arrival_best=arrival_best,
        arrival_mid=arrival_mid,
        execution_end_mid=execution_end_mid,
        post_quiet_mid=post_quiet_mid,
        slippage_vs_best=slippage_vs_best,
        slippage_vs_mid=slippage_vs_mid,
        slippage_bps=slippage_bps,
        temp_price_impact_bps=temp_impact_bps,
        perm_price_impact_bps=perm_impact_bps,
        impl_shortfall=impl_shortfall,
        slice_executions=tuple(slice_records),
    )
