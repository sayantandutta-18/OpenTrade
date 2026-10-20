"""Routes for calculating market impact and execution slippage."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from impactlab.api.schemas import (
    ChargesSchema,
    ImpactSimulateRequest,
    ImpactSimulateResponse,
    LevelFillSchema,
)
from impactlab.api.sessions import session_store
from impactlab.charges.calculator import ChargesCalculator
from impactlab.cli import format_inr
from impactlab.execution.base import ExecutionStrategy
from impactlab.execution.passive import PassiveLimitStrategy
from impactlab.execution.twap import MarketStrategy, TWAPStrategy
from impactlab.execution.vwap import VWAPStrategy
from impactlab.impact.dynamic import simulate_dynamic_execution
from impactlab.impact.metrics import SizeMode
from impactlab.impact.static_walk import walk_book

router = APIRouter(prefix="/impact", tags=["impact"])
charges_calc = ChargesCalculator()

DISCLAIMER_TEXT = (
    "Simulated results using synthetic data and simplifying assumptions. "
    "Not investment advice. Real execution costs will differ."
)


@router.post("/simulate", response_model=ImpactSimulateResponse)
def simulate_impact(req: ImpactSimulateRequest) -> ImpactSimulateResponse:
    """Calculate market impact and true execution costs for a hypothetical order.

    Does NOT mutate the live session book.
    """
    sess = session_store.get(req.session_id)
    if not sess:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{req.session_id}' not found",
        )

    mode = req.mode.lower()

    if mode == "dynamic":
        # Select strategy
        strategy_name = req.strategy.name.lower()
        strategy: ExecutionStrategy
        if strategy_name == "twap":
            strategy = TWAPStrategy(
                duration_seconds=req.strategy.duration_seconds,
                num_slices=req.strategy.num_slices,
            )
        elif strategy_name == "vwap":
            strategy = VWAPStrategy(
                duration_seconds=req.strategy.duration_seconds,
                num_slices=req.strategy.num_slices,
            )
        elif strategy_name in ("passive", "passive_limit"):
            strategy = PassiveLimitStrategy(
                duration_seconds=req.strategy.duration_seconds,
                num_slices=req.strategy.num_slices,
            )
        else:
            strategy = MarketStrategy()

        # Dynamic simulation works on shares mode
        dyn_res = simulate_dynamic_execution(
            engine=sess.engine,
            simulator=sess.simulator,
            strategy=strategy,
            side=req.side,
            qty=req.size.value,
            quiet_seconds=10.0,
        )

        charges = charges_calc.calculate(
            side=req.side,
            notional=dyn_res.total_notional,
            product_type=req.product_type,
        )

        all_in_cost = (dyn_res.impl_shortfall or 0.0) + charges.total_charges
        unfilled = max(0, dyn_res.requested_qty - dyn_res.filled_qty)

        return ImpactSimulateResponse(
            session_id=req.session_id,
            side=req.side,
            mode=req.mode,
            requested_qty=dyn_res.requested_qty,
            filled_qty=dyn_res.filled_qty,
            unfilled_qty=unfilled,
            fill_ratio=dyn_res.fill_ratio,
            total_notional=dyn_res.total_notional,
            total_notional_formatted=format_inr(dyn_res.total_notional),
            avg_price=dyn_res.avg_price,
            avg_price_formatted=format_inr(dyn_res.avg_price),
            arrival_best=dyn_res.arrival_best,
            arrival_best_formatted=format_inr(dyn_res.arrival_best),
            arrival_mid=dyn_res.arrival_mid,
            arrival_mid_formatted=format_inr(dyn_res.arrival_mid),
            post_mid=dyn_res.post_quiet_mid,
            post_mid_formatted=format_inr(dyn_res.post_quiet_mid),
            slippage_vs_best=dyn_res.slippage_vs_best,
            slippage_vs_best_formatted=format_inr(dyn_res.slippage_vs_best),
            slippage_vs_mid=dyn_res.slippage_vs_mid,
            slippage_vs_mid_formatted=format_inr(dyn_res.slippage_vs_mid),
            slippage_bps=dyn_res.slippage_bps,
            price_impact_bps=dyn_res.perm_price_impact_bps,
            impl_shortfall=dyn_res.impl_shortfall,
            impl_shortfall_formatted=format_inr(dyn_res.impl_shortfall),
            levels_consumed=len(dyn_res.slice_executions),
            level_fills=[],
            charges=ChargesSchema(
                product_type=charges.product_type,
                brokerage=charges.brokerage,
                brokerage_formatted=format_inr(charges.brokerage),
                stt=charges.stt,
                stt_formatted=format_inr(charges.stt),
                exchange_txn_fee=charges.exchange_txn_fee,
                exchange_txn_fee_formatted=format_inr(charges.exchange_txn_fee),
                sebi_fee=charges.sebi_fee,
                sebi_fee_formatted=format_inr(charges.sebi_fee),
                stamp_duty=charges.stamp_duty,
                stamp_duty_formatted=format_inr(charges.stamp_duty),
                gst=charges.gst,
                gst_formatted=format_inr(charges.gst),
                total_charges=charges.total_charges,
                total_charges_formatted=format_inr(charges.total_charges),
                as_of=charges.as_of,
                source_note=charges.source_note,
            ),
            all_in_cost=all_in_cost,
            all_in_cost_formatted=format_inr(all_in_cost),
            disclaimer=DISCLAIMER_TEXT,
        )

    # Default: Static walk
    snap = sess.engine.book.snapshot(ts=sess.simulator.current_time_us)
    size_mode = SizeMode.RUPEES if req.size.mode == SizeMode.RUPEES else SizeMode.SHARES
    res = walk_book(snapshot=snap, side=req.side, size=req.size.value, mode=size_mode)

    charges = charges_calc.calculate(
        side=req.side,
        notional=res.total_notional,
        product_type=req.product_type,
    )

    all_in_cost = (res.impl_shortfall or 0.0) + charges.total_charges

    return ImpactSimulateResponse(
        session_id=req.session_id,
        side=req.side,
        mode=req.mode,
        requested_qty=res.requested_qty,
        filled_qty=res.filled_qty,
        unfilled_qty=res.unfilled_qty,
        fill_ratio=res.fill_ratio,
        total_notional=res.total_notional,
        total_notional_formatted=format_inr(res.total_notional),
        avg_price=res.avg_price,
        avg_price_formatted=format_inr(res.avg_price),
        arrival_best=res.arrival_best,
        arrival_best_formatted=format_inr(res.arrival_best),
        arrival_mid=res.arrival_mid,
        arrival_mid_formatted=format_inr(res.arrival_mid),
        post_mid=res.post_mid,
        post_mid_formatted=format_inr(res.post_mid),
        slippage_vs_best=res.slippage_vs_best,
        slippage_vs_best_formatted=format_inr(res.slippage_vs_best),
        slippage_vs_mid=res.slippage_vs_mid,
        slippage_vs_mid_formatted=format_inr(res.slippage_vs_mid),
        slippage_bps=res.slippage_bps,
        price_impact_bps=res.price_impact_bps,
        impl_shortfall=res.impl_shortfall,
        impl_shortfall_formatted=format_inr(res.impl_shortfall),
        levels_consumed=res.levels_consumed,
        level_fills=[
            LevelFillSchema(
                price=lf.price,
                price_formatted=format_inr(lf.price),
                qty=lf.qty,
                notional=lf.notional,
                notional_formatted=format_inr(lf.notional),
            )
            for lf in res.level_fills
        ],
        charges=ChargesSchema(
            product_type=charges.product_type,
            brokerage=charges.brokerage,
            brokerage_formatted=format_inr(charges.brokerage),
            stt=charges.stt,
            stt_formatted=format_inr(charges.stt),
            exchange_txn_fee=charges.exchange_txn_fee,
            exchange_txn_fee_formatted=format_inr(charges.exchange_txn_fee),
            sebi_fee=charges.sebi_fee,
            sebi_fee_formatted=format_inr(charges.sebi_fee),
            stamp_duty=charges.stamp_duty,
            stamp_duty_formatted=format_inr(charges.stamp_duty),
            gst=charges.gst,
            gst_formatted=format_inr(charges.gst),
            total_charges=charges.total_charges,
            total_charges_formatted=format_inr(charges.total_charges),
            as_of=charges.as_of,
            source_note=charges.source_note,
        ),
        all_in_cost=all_in_cost,
        all_in_cost_formatted=format_inr(all_in_cost),
        disclaimer=DISCLAIMER_TEXT,
    )
