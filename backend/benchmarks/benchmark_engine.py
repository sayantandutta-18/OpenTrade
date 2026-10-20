"""Engine benchmark measuring order throughput, latency percentiles, and book depth speed."""

from __future__ import annotations

import time

import numpy as np

from impactlab.engine.matcher import MatchingEngine
from impactlab.engine.models import Order, OrderType, Side
from impactlab.flow.generators import FlowSimulator
from impactlab.flow.profiles import get_profile
from impactlab.impact.metrics import SizeMode
from impactlab.impact.static_walk import walk_book


def benchmark_engine_throughput(total_orders: int = 100_000) -> dict[str, float]:
    """Benchmark matching engine submit throughput with realistic Poisson flow."""
    profile = get_profile("large_cap")
    engine = MatchingEngine(tick_size=profile.tick_size, lot_size=profile.lot_size)
    sim = FlowSimulator(profile=profile, seed=12345)

    # Pre-warm book
    sim.warmup(engine, seconds=30.0)

    # Generate test orders
    rng = np.random.default_rng(42)
    latencies_us: list[float] = []

    mid_paise = 250_000  # Rs 2,500
    start_time = time.perf_counter()

    for i in range(total_orders):
        is_buy = rng.random() < 0.5
        side = Side.BUY if is_buy else Side.SELL
        is_limit = rng.random() < 0.85
        qty = int(rng.integers(10, 200))

        if is_limit:
            # +/- 10 ticks around mid
            tick_offset = int(rng.integers(-10, 10)) * 5
            price = mid_paise + tick_offset
            order = Order(
                id=1_000_000 + i,
                side=side,
                type=OrderType.LIMIT,
                price=price,
                qty=qty,
                remaining=qty,
                ts=i * 1000,
                owner="benchmark",
            )
        else:
            order = Order(
                id=1_000_000 + i,
                side=side,
                type=OrderType.MARKET,
                price=None,
                qty=qty,
                remaining=qty,
                ts=i * 1000,
                owner="benchmark",
            )

        t0 = time.perf_counter_ns()
        engine.submit(order)
        t1 = time.perf_counter_ns()

        if i < 20_000:
            latencies_us.append((t1 - t0) / 1000.0)

    elapsed_sec = time.perf_counter() - start_time
    orders_per_sec = total_orders / elapsed_sec

    p50 = float(np.percentile(latencies_us, 50))
    p95 = float(np.percentile(latencies_us, 95))
    p99 = float(np.percentile(latencies_us, 99))

    return {
        "total_orders": float(total_orders),
        "elapsed_sec": elapsed_sec,
        "orders_per_sec": orders_per_sec,
        "p50_us": p50,
        "p95_us": p95,
        "p99_us": p99,
        "trade_count": float(len(engine.trades)),
    }


def benchmark_static_walk(iterations: int = 25_000) -> dict[str, float]:
    """Benchmark static impact walk speed on a realistic book snapshot."""
    profile = get_profile("large_cap")
    engine = MatchingEngine(tick_size=profile.tick_size, lot_size=profile.lot_size)
    sim = FlowSimulator(profile=profile, seed=42)
    sim.warmup(engine, seconds=60.0)
    snap = engine.book.snapshot()

    t0 = time.perf_counter()
    for _ in range(iterations):
        walk_book(snap, side=Side.BUY, size=5000, mode=SizeMode.SHARES)
    elapsed = time.perf_counter() - t0

    return {
        "iterations": float(iterations),
        "elapsed_sec": elapsed,
        "walks_per_sec": iterations / elapsed,
        "avg_walk_us": (elapsed / iterations) * 1_000_000,
    }


def main() -> None:
    print("=" * 65)
    print(" ImpactLab Performance Benchmarks")
    print(" Matching Engine Throughput & Microstructure Analysis Speed")
    print("=" * 65)

    print("\nRunning MatchingEngine throughput benchmark (100,000 orders)...")
    res = benchmark_engine_throughput(100_000)

    print("-" * 65)
    print(f" Total Orders Processed : {int(res['total_orders']):,}")
    print(f" Elapsed Time           : {res['elapsed_sec']:.3f} s")
    print(f" Engine Throughput      : {res['orders_per_sec']:,.0f} orders/sec")
    print(f" Latency Median (p50)   : {res['p50_us']:.2f} us")
    print(f" Latency 95th (p95)     : {res['p95_us']:.2f} us")
    print(f" Latency 99th (p99)     : {res['p99_us']:.2f} us")
    print(f" Executed Trades        : {int(res['trade_count']):,}")

    target = 50_000
    if res["orders_per_sec"] >= target:
        print(f" [PASS] Throughput exceeds PRD target ({target:,} orders/sec).")
    else:
        print(f" [WARN] Throughput under PRD target ({target:,} orders/sec).")

    print("\nRunning Static Impact Walk benchmark (25,000 iterations)...")
    walk_res = benchmark_static_walk(25_000)
    print("-" * 65)
    print(f" Iterations             : {int(walk_res['iterations']):,}")
    print(f" Elapsed Time           : {walk_res['elapsed_sec']:.3f} s")
    print(f" Walks Throughput       : {walk_res['walks_per_sec']:,.0f} walks/sec")
    print(f" Average Latency        : {walk_res['avg_walk_us']:.2f} us/walk")
    print("=" * 65)


if __name__ == "__main__":
    main()
