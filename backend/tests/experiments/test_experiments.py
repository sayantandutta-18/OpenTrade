"""Tests for Monte Carlo experiments runner and statistical aggregation."""

from impactlab.experiments.runner import derive_child_seeds, run_experiment
from impactlab.experiments.stats import aggregate_series


def test_aggregate_series_metrics() -> None:
    vals = [10.0, 20.0, 30.0, 40.0, 50.0]
    stats = aggregate_series(vals)
    assert stats.count == 5
    assert stats.mean == 30.0
    assert stats.median == 30.0
    assert stats.min == 10.0
    assert stats.max == 50.0
    assert stats.p5 <= stats.p25 <= stats.median <= stats.p75 <= stats.p95


def test_aggregate_series_empty() -> None:
    stats = aggregate_series([])
    assert stats.count == 0
    assert stats.mean == 0.0


def test_derive_child_seeds_determinism() -> None:
    seeds1 = derive_child_seeds(master_seed=123, count=10)
    seeds2 = derive_child_seeds(master_seed=123, count=10)
    assert seeds1 == seeds2
    assert len(set(seeds1)) == 10


def test_experiment_determinism_and_worker_independence() -> None:
    params = {
        "profile": "mid_cap",
        "sizes": [100, 500, 1000],
        "side": "BUY",
        "warmup_seconds": 3.0,
    }

    # Run single-worker
    res1 = run_experiment(
        experiment_type="size_sweep",
        params=params,
        master_seed=42,
        runs=5,
        max_workers=1,
    )

    # Run multi-worker
    res2 = run_experiment(
        experiment_type="size_sweep",
        params=params,
        master_seed=42,
        runs=5,
        max_workers=2,
    )

    assert res1.summary == res2.summary
    assert res1.chart_data == res2.chart_data


def test_strategy_comparison_experiment() -> None:
    params = {
        "profile": "mid_cap",
        "qty": 500,
        "side": "BUY",
        "warmup_seconds": 3.0,
        "duration_seconds": 5.0,
        "num_slices": 3,
    }

    res = run_experiment(
        experiment_type="strategy_comparison",
        params=params,
        master_seed=99,
        runs=3,
        max_workers=1,
    )

    assert res.experiment_type == "strategy_comparison"
    assert "market" in res.summary
    assert "twap" in res.summary
    assert "vwap" in res.summary
    assert len(res.chart_data) == 4


def test_200_run_monte_carlo_sweep() -> None:
    # 200 runs on size sweep finishes quickly and produces statistical confidence intervals
    params = {
        "profile": "large_cap",
        "sizes": [100, 1000],
        "side": "BUY",
        "warmup_seconds": 1.0,
    }

    res = run_experiment(
        experiment_type="size_sweep",
        params=params,
        master_seed=777,
        runs=200,
        max_workers=4,
    )

    assert res.runs == 200
    assert len(res.chart_data) == 2
    # Verify p5 <= median <= p95
    for pt in res.chart_data:
        assert pt["p5"] <= pt["median"] <= pt["p95"]
