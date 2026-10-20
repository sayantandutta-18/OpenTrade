"""Monte Carlo experiment runner with parallel execution and reproducible child seeds."""

from __future__ import annotations

import uuid
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any

import numpy as np

from impactlab.engine.matcher import MatchingEngine
from impactlab.engine.models import Side
from impactlab.execution.base import ExecutionStrategy
from impactlab.execution.passive import PassiveLimitStrategy
from impactlab.execution.twap import MarketStrategy, TWAPStrategy
from impactlab.execution.vwap import VWAPStrategy
from impactlab.experiments.stats import SummaryStats, aggregate_series
from impactlab.flow.generators import FlowSimulator
from impactlab.flow.profiles import StockProfile, get_profile
from impactlab.impact.dynamic import simulate_dynamic_execution
from impactlab.impact.metrics import SizeMode
from impactlab.impact.static_walk import walk_book


@dataclass(frozen=True, slots=True)
class ExperimentResult:
    """Complete result of a Monte Carlo experiment."""

    experiment_id: str
    experiment_type: str
    master_seed: int
    runs: int
    params: dict[str, Any]
    summary: dict[str, Any]
    chart_data: list[dict[str, Any]]


def derive_child_seeds(master_seed: int, count: int) -> list[int]:
    """Deterministically derive child seeds from a master seed.

    Guarantees that run N receives the exact same child seed regardless
    of the number of parallel workers or execution ordering.
    """
    seq = np.random.SeedSequence(master_seed)
    children = seq.spawn(count)
    return [int(c.generate_state(1)[0]) for c in children]


def _worker_size_sweep(
    child_seed: int,
    profile_name: str,
    sizes: list[int],
    side_str: str,
    warmup_sec: float,
) -> dict[int, dict[str, float | None]]:
    """Worker task for a single Monte Carlo size sweep run."""
    profile = get_profile(profile_name)
    side = Side.BUY if side_str.upper() == "BUY" else Side.SELL
    engine = MatchingEngine(tick_size=profile.tick_size, lot_size=profile.lot_size)
    sim = FlowSimulator(profile=profile, seed=child_seed)
    sim.warmup(engine, seconds=warmup_sec)
    snap = engine.book.snapshot()

    results: dict[int, dict[str, float | None]] = {}
    for sz in sizes:
        res = walk_book(snap, side=side, size=sz, mode=SizeMode.SHARES)
        results[sz] = {
            "slippage_bps": res.slippage_bps,
            "slippage_vs_best_rs": (res.slippage_vs_best / 100.0) if res.slippage_vs_best else None,
            "price_impact_bps": res.price_impact_bps,
            "fill_ratio": res.fill_ratio,
            "impl_shortfall_rs": (res.impl_shortfall / 100.0) if res.impl_shortfall else None,
        }
    return results


def _worker_strategy_comparison(
    child_seed: int,
    profile_name: str,
    qty: int,
    side_str: str,
    warmup_sec: float,
    duration_sec: float,
    slices: int,
) -> dict[str, dict[str, float | None]]:
    """Worker task for a single Monte Carlo strategy comparison run."""
    profile = get_profile(profile_name)
    side = Side.BUY if side_str.upper() == "BUY" else Side.SELL
    engine = MatchingEngine(tick_size=profile.tick_size, lot_size=profile.lot_size)
    sim = FlowSimulator(profile=profile, seed=child_seed)
    sim.warmup(engine, seconds=warmup_sec)

    strategies: list[ExecutionStrategy] = [
        MarketStrategy(),
        TWAPStrategy(duration_seconds=duration_sec, num_slices=slices),
        VWAPStrategy(duration_seconds=duration_sec, num_slices=slices),
        PassiveLimitStrategy(duration_seconds=duration_sec, num_slices=slices),
    ]

    out: dict[str, dict[str, float | None]] = {}
    for strat in strategies:
        res = simulate_dynamic_execution(
            engine=engine,
            simulator=sim,
            strategy=strat,
            side=side,
            qty=qty,
            quiet_seconds=5.0,
        )
        out[strat.name] = {
            "slippage_bps": res.slippage_bps,
            "temp_impact_bps": res.temp_price_impact_bps,
            "perm_impact_bps": res.perm_price_impact_bps,
            "fill_ratio": res.fill_ratio,
            "impl_shortfall_rs": (res.impl_shortfall / 100.0) if res.impl_shortfall else None,
        }
    return out


def _worker_spread_sweep(
    child_seed: int,
    base_profile_name: str,
    spread_ticks_list: list[int],
    qty: int,
    side_str: str,
    warmup_sec: float,
) -> dict[int, dict[str, float | None]]:
    """Worker task for spread sweep."""
    base = get_profile(base_profile_name)
    side = Side.BUY if side_str.upper() == "BUY" else Side.SELL
    results: dict[int, dict[str, float | None]] = {}

    for spr in spread_ticks_list:
        custom_prof = StockProfile(
            name=f"{base.name}_spread_{spr}",
            description=base.description,
            reference_price=base.reference_price,
            tick_size=base.tick_size,
            lot_size=base.lot_size,
            typical_spread_ticks=spr,
            target_depth_shares=base.target_depth_shares,
            limit_arrival_rate=base.limit_arrival_rate,
            market_arrival_rate=base.market_arrival_rate,
            cancel_rate=base.cancel_rate,
            size_median=base.size_median,
            size_sigma=base.size_sigma,
            min_order_qty=base.min_order_qty,
            max_order_qty=base.max_order_qty,
            daily_volatility_pct=base.daily_volatility_pct,
        )
        engine = MatchingEngine(tick_size=custom_prof.tick_size, lot_size=custom_prof.lot_size)
        sim = FlowSimulator(profile=custom_prof, seed=child_seed)
        sim.warmup(engine, seconds=warmup_sec)
        snap = engine.book.snapshot()
        res = walk_book(snap, side=side, size=qty, mode=SizeMode.SHARES)
        results[spr] = {
            "slippage_bps": res.slippage_bps,
            "price_impact_bps": res.price_impact_bps,
            "realized_spread_ticks": (snap.spread // custom_prof.tick_size) if snap.spread else spr,
        }
    return results


def _run_size_sweep(
    exp_id: str,
    params: dict[str, Any],
    master_seed: int,
    child_seeds: list[int],
    max_workers: int,
) -> ExperimentResult:
    profile = params.get("profile", "mid_cap")
    sizes: list[int] = params.get("sizes", [100, 500, 1000, 2500, 5000])
    side = params.get("side", "BUY")
    warmup = float(params.get("warmup_seconds", 10.0))

    raw_outputs: list[dict[int, dict[str, float | None]]] = []
    if max_workers > 1 and len(child_seeds) > 1:
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(_worker_size_sweep, s, profile, sizes, side, warmup): idx
                for idx, s in enumerate(child_seeds)
            }
            indexed: list[tuple[int, dict[int, dict[str, float | None]]]] = []
            for fut in as_completed(futures):
                indexed.append((futures[fut], fut.result()))
            indexed.sort(key=lambda x: x[0])
            raw_outputs = [r for _, r in indexed]
    else:
        for s in child_seeds:
            raw_outputs.append(_worker_size_sweep(s, profile, sizes, side, warmup))

    chart_data: list[dict[str, Any]] = []
    summary: dict[str, Any] = {}

    for sz in sizes:
        slip_bps_vals: list[float] = []
        for r in raw_outputs:
            v = r[sz].get("slippage_bps")
            if v is not None:
                slip_bps_vals.append(float(v))

        stats: SummaryStats = aggregate_series(slip_bps_vals)
        summary[str(sz)] = stats.to_dict()
        chart_data.append(
            {
                "x": sz,
                "size": sz,
                "mean": stats.mean,
                "median": stats.median,
                "p5": stats.p5,
                "p25": stats.p25,
                "p75": stats.p75,
                "p95": stats.p95,
                "stderr": stats.stderr,
            }
        )

    return ExperimentResult(
        experiment_id=exp_id,
        experiment_type="size_sweep",
        master_seed=master_seed,
        runs=len(child_seeds),
        params=params,
        summary=summary,
        chart_data=chart_data,
    )


def _run_strategy_comparison(
    exp_id: str,
    params: dict[str, Any],
    master_seed: int,
    child_seeds: list[int],
    max_workers: int,
) -> ExperimentResult:
    profile = params.get("profile", "mid_cap")
    qty = int(params.get("qty", 1000))
    side = params.get("side", "BUY")
    warmup = float(params.get("warmup_seconds", 10.0))
    duration = float(params.get("duration_seconds", 30.0))
    slices = int(params.get("num_slices", 5))

    raw_outputs: list[dict[str, dict[str, float | None]]] = []
    if max_workers > 1 and len(child_seeds) > 1:
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    _worker_strategy_comparison,
                    s,
                    profile,
                    qty,
                    side,
                    warmup,
                    duration,
                    slices,
                ): idx
                for idx, s in enumerate(child_seeds)
            }
            indexed: list[tuple[int, dict[str, dict[str, float | None]]]] = []
            for fut in as_completed(futures):
                indexed.append((futures[fut], fut.result()))
            indexed.sort(key=lambda x: x[0])
            raw_outputs = [r for _, r in indexed]
    else:
        for s in child_seeds:
            raw_outputs.append(
                _worker_strategy_comparison(s, profile, qty, side, warmup, duration, slices)
            )

    strategies = ["market", "twap", "vwap", "passive_limit"]
    chart_data = []
    summary = {}

    for strat_name in strategies:
        vals: list[float] = []
        for r in raw_outputs:
            v = r.get(strat_name, {}).get("slippage_bps")
            if v is not None:
                vals.append(float(v))

        stats = aggregate_series(vals)
        summary[strat_name] = stats.to_dict()
        chart_data.append(
            {
                "strategy": strat_name,
                "mean_slippage_bps": stats.mean,
                "median_slippage_bps": stats.median,
                "std_slippage_bps": stats.std,
                "p5": stats.p5,
                "p95": stats.p95,
            }
        )

    return ExperimentResult(
        experiment_id=exp_id,
        experiment_type="strategy_comparison",
        master_seed=master_seed,
        runs=len(child_seeds),
        params=params,
        summary=summary,
        chart_data=chart_data,
    )


def _run_spread_sweep(
    exp_id: str,
    params: dict[str, Any],
    master_seed: int,
    child_seeds: list[int],
    max_workers: int,
) -> ExperimentResult:
    profile = params.get("profile", "mid_cap")
    spreads: list[int] = params.get("spread_ticks", [1, 2, 4, 8, 16])
    qty = int(params.get("qty", 500))
    side = params.get("side", "BUY")
    warmup = float(params.get("warmup_seconds", 10.0))

    raw_outputs: list[dict[int, dict[str, float | None]]] = []
    for s in child_seeds:
        raw_outputs.append(_worker_spread_sweep(s, profile, spreads, qty, side, warmup))

    chart_data = []
    summary = {}
    for spr in spreads:
        vals: list[float] = []
        for r in raw_outputs:
            v = r.get(spr, {}).get("slippage_bps")
            if v is not None:
                vals.append(float(v))

        stats = aggregate_series(vals)
        summary[str(spr)] = stats.to_dict()
        chart_data.append(
            {
                "spread_ticks": spr,
                "mean_slippage_bps": stats.mean,
                "p5": stats.p5,
                "p95": stats.p95,
            }
        )

    return ExperimentResult(
        experiment_id=exp_id,
        experiment_type="spread_sweep",
        master_seed=master_seed,
        runs=len(child_seeds),
        params=params,
        summary=summary,
        chart_data=chart_data,
    )


def run_experiment(
    experiment_type: str,
    params: dict[str, Any],
    master_seed: int = 42,
    runs: int = 100,
    max_workers: int = 4,
) -> ExperimentResult:
    """Run a reproducible Monte Carlo experiment across N seeds.

    Args:
        experiment_type: 'size_sweep' | 'strategy_comparison' | 'spread_sweep'.
        params: Configuration parameters dictionary.
        master_seed: Master integer random seed.
        runs: Number of independent simulation runs.
        max_workers: Parallel worker count (if 1, runs in main process).

    Returns:
        ExperimentResult containing chart data and summary statistics.
    """
    exp_id = str(uuid.uuid4())
    child_seeds = derive_child_seeds(master_seed, runs)

    if experiment_type == "size_sweep":
        return _run_size_sweep(exp_id, params, master_seed, child_seeds, max_workers)
    elif experiment_type == "strategy_comparison":
        return _run_strategy_comparison(exp_id, params, master_seed, child_seeds, max_workers)
    else:
        return _run_spread_sweep(exp_id, params, master_seed, child_seeds, max_workers)
