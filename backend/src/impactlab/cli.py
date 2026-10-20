"""Command Line Interface for ImpactLab.

Run with: python -m impactlab.cli [book|impact|sweep] ...
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections.abc import Sequence
from pathlib import Path

from impactlab.charges.calculator import ChargesCalculator
from impactlab.engine.matcher import MatchingEngine
from impactlab.engine.models import BookSnapshot, Side
from impactlab.flow.generators import FlowSimulator
from impactlab.flow.profiles import PROFILES, StockProfile, get_profile
from impactlab.impact.metrics import SizeMode
from impactlab.impact.static_walk import walk_book


def format_inr(paise: int | float | None) -> str:
    """Format paise into INR rupees string (e.g. 10000 paise -> 'Rs 100.00')."""
    if paise is None:
        return "N/A"
    rupees = paise / 100.0
    return f"Rs {rupees:,.2f}"


def normalize_profile_name(name: str) -> str:
    """Normalize short profile aliases like 'mid', 'small', 'large'."""
    lower = name.strip().lower()
    if lower in ("large", "largecap", "large_cap"):
        return "large_cap"
    if lower in ("mid", "midcap", "mid_cap"):
        return "mid_cap"
    if lower in ("small", "smallcap", "small_cap"):
        return "small_cap"
    return lower


def setup_simulated_book(
    profile_name: str,
    seed: int = 1,
    warmup_seconds: float = 30.0,
) -> tuple[StockProfile, MatchingEngine, BookSnapshot]:
    """Create and warm up an order book for the given profile and seed."""
    norm_name = normalize_profile_name(profile_name)
    profile = get_profile(norm_name)
    engine = MatchingEngine(tick_size=profile.tick_size, lot_size=profile.lot_size)
    simulator = FlowSimulator(profile=profile, seed=seed)
    simulator.warmup(engine, seconds=warmup_seconds)
    snapshot = engine.book.snapshot()
    return profile, engine, snapshot


def cmd_book(args: argparse.Namespace) -> None:
    """Print the order book ladder."""
    profile, _engine, snap = setup_simulated_book(
        profile_name=args.profile,
        seed=args.seed,
        warmup_seconds=args.warmup,
    )

    depth = max(1, args.depth)
    print("=" * 65)
    print(f" ImpactLab Order Book Ladder: {profile.name.upper()} ({profile.description})")
    print(
        f" Seed: {args.seed} | Warmup: {args.warmup}s | Tick Size: Rs {profile.tick_size / 100:.2f}"
    )
    print("=" * 65)
    print(f"{'Side':<6} | {'Price (Rs)':>12} | {'Quantity':>12} | {'Cum Qty':>12}")
    print("-" * 65)

    # Asks: show in reverse (highest price at top, best ask at bottom of asks)
    top_asks = list(reversed(snap.asks[:depth]))
    cum_ask = sum(a.qty for a in top_asks)
    running_ask = cum_ask
    for lvl in top_asks:
        print(f"ASK    | {lvl.price / 100:>12.2f} | {lvl.qty:>12,d} | {running_ask:>12,d}")
        running_ask -= lvl.qty

    print("-" * 65)
    spread_str = format_inr(snap.spread)
    spread_ticks = (snap.spread // profile.tick_size) if snap.spread else 0
    mid_str = format_inr(snap.mid)
    print(f"SPREAD : {spread_str} ({spread_ticks} ticks) | MID : {mid_str}")
    print("-" * 65)

    # Bids: best bid at top, down to lowest price
    running_bid = 0
    for lvl in snap.bids[:depth]:
        running_bid += lvl.qty
        print(f"BID    | {lvl.price / 100:>12.2f} | {lvl.qty:>12,d} | {running_bid:>12,d}")

    print("=" * 65)


def cmd_impact(args: argparse.Namespace) -> None:
    """Simulate a hypothetical order and print impact metrics and charges."""
    side = Side.BUY if args.side.upper() == "BUY" else Side.SELL
    profile, _engine, snap = setup_simulated_book(
        profile_name=args.profile,
        seed=args.seed,
        warmup_seconds=args.warmup,
    )

    mode = SizeMode.RUPEES if args.mode.lower() == "rupees" else SizeMode.SHARES
    result = walk_book(snapshot=snap, side=side, size=args.qty, mode=mode)
    charges_calc = ChargesCalculator()
    charges = charges_calc.calculate(
        side=side,
        notional=result.total_notional,
        product_type=args.product_type,
    )

    print("=" * 65)
    print(" ImpactLab Market Impact Analysis")
    print(f" Profile: {profile.name} | Side: {side.value} | Size: {args.qty:,d} {mode.value}")
    print("=" * 65)
    print(f" Requested Qty       : {result.requested_qty:,d} shares")
    print(f" Filled Qty          : {result.filled_qty:,d} shares ({result.fill_ratio * 100:.1f}%)")
    print(f" Unfilled Qty        : {result.unfilled_qty:,d} shares")
    print(f" Total Order Value   : {format_inr(result.total_notional)}")
    print(f" Average Fill Price  : {format_inr(result.avg_price)}")
    print(f" Arrival Best Price  : {format_inr(result.arrival_best)}")
    print(f" Arrival Mid Price   : {format_inr(result.arrival_mid)}")
    print(f" Post-Trade Mid      : {format_inr(result.post_mid)}")
    print("-" * 65)
    print(f" Slippage vs Best    : {format_inr(result.slippage_vs_best)} / share")
    print(f" Slippage vs Mid     : {format_inr(result.slippage_vs_mid)} / share")
    sl_bps = f"{result.slippage_bps:.2f} bps" if result.slippage_bps is not None else "N/A"
    pi_bps = f"{result.price_impact_bps:.2f} bps" if result.price_impact_bps is not None else "N/A"
    print(f" Slippage (bps)      : {sl_bps}")
    print(f" Price Impact (bps)  : {pi_bps}")
    print(f" Levels Consumed     : {result.levels_consumed}")
    print("-" * 65)
    print(" Statutory & Broker Charges (Indian Equity Delivery/Intraday):")
    print(f"   Brokerage         : {format_inr(charges.brokerage)}")
    print(f"   STT / CTT         : {format_inr(charges.stt)}")
    print(f"   Exchange Txn Fee  : {format_inr(charges.exchange_txn_fee)}")
    print(f"   SEBI Turnover Fee : {format_inr(charges.sebi_fee)}")
    print(f"   Stamp Duty        : {format_inr(charges.stamp_duty)}")
    print(f"   GST (18%)         : {format_inr(charges.gst)}")
    print(f"   Total Charges     : {format_inr(charges.total_charges)}")
    print("-" * 65)
    all_in = (result.impl_shortfall or 0.0) + charges.total_charges
    print(f" Implementation Shortfall : {format_inr(result.impl_shortfall)}")
    print(f" All-In Execution Cost   : {format_inr(all_in)}")
    print("=" * 65)
    print(f" * Schedule As Of: {charges.as_of} | {charges.source_note}")
    print("=" * 65)


def cmd_sweep(args: argparse.Namespace) -> None:
    """Run an order size sweep and print/export slippage vs size table."""
    sizes = [int(s.strip()) for s in args.sizes.split(",") if s.strip()]
    side = Side.BUY if args.side.upper() == "BUY" else Side.SELL
    profiles_to_run = (
        list(PROFILES.keys())
        if args.profile.lower() == "all"
        else [normalize_profile_name(args.profile)]
    )

    csv_rows: list[dict[str, str | int | float | None]] = []

    for prof_name in profiles_to_run:
        profile, _engine, snap = setup_simulated_book(
            profile_name=prof_name,
            seed=args.seed,
            warmup_seconds=args.warmup,
        )

        print("\n" + "=" * 78)
        ref_rs = profile.reference_price / 100.0
        print(f" ImpactLab Size Sweep: {profile.name.upper()} (Ref: Rs {ref_rs:.2f})")
        print(f" Side: {side.value} | Seed: {args.seed} | Warmup: {args.warmup}s")
        print("=" * 78)
        print(
            f"{'Size (shares)':>13} | {'Avg Price':>12} | {'Slippage (Rs)':>14} | "
            f"{'Slippage (bps)':>14} | {'Fill Ratio':>10} | {'Levels':>6}"
        )
        print("-" * 78)

        for size in sizes:
            res = walk_book(snap, side=side, size=size, mode=SizeMode.SHARES)
            avg_p_str = format_inr(res.avg_price)
            slip_inr = format_inr(res.slippage_vs_best)
            slip_bps_str = f"{res.slippage_bps:.2f}" if res.slippage_bps is not None else "N/A"
            fill_pct_str = f"{res.fill_ratio * 100:.1f}%"

            print(
                f"{size:>13,d} | {avg_p_str:>12} | {slip_inr:>14} | "
                f"{slip_bps_str:>14} | {fill_pct_str:>10} | {res.levels_consumed:>6d}"
            )

            csv_rows.append(
                {
                    "profile": profile.name,
                    "side": side.value,
                    "size": size,
                    "filled_qty": res.filled_qty,
                    "fill_ratio": res.fill_ratio,
                    "avg_price_rs": (res.avg_price / 100.0) if res.avg_price else None,
                    "slippage_vs_best_rs": (res.slippage_vs_best / 100.0)
                    if res.slippage_vs_best
                    else None,
                    "slippage_bps": res.slippage_bps,
                    "price_impact_bps": res.price_impact_bps,
                    "levels_consumed": res.levels_consumed,
                    "total_cost_rs": res.total_notional / 100.0,
                }
            )

    if args.csv and csv_rows:
        csv_path = Path(args.csv)
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(csv_rows[0].keys()))
            writer.writeheader()
            writer.writerows(csv_rows)
        print(f"\n[+] Saved {len(csv_rows)} sweep rows to {csv_path.resolve()}")


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="python -m impactlab.cli",
        description="ImpactLab: Limit Order Book Simulator & Market Impact Analyzer",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # book
    p_book = subparsers.add_parser("book", help="Display simulated order book ladder")
    p_book.add_argument("--profile", default="mid_cap", help="large_cap | mid_cap | small_cap")
    p_book.add_argument("--seed", type=int, default=1, help="Random seed")
    p_book.add_argument("--warmup", type=float, default=30.0, help="Warmup duration in seconds")
    p_book.add_argument("--depth", type=int, default=10, help="Levels of depth to display")

    # impact
    p_impact = subparsers.add_parser("impact", help="Calculate impact for a hypothetical order")
    p_impact.add_argument("--profile", default="small_cap", help="large_cap | mid_cap | small_cap")
    p_impact.add_argument("--side", default="buy", help="buy | sell")
    p_impact.add_argument("--qty", type=int, default=5000, help="Shares or rupee budget")
    p_impact.add_argument("--mode", default="shares", help="shares | rupees")
    p_impact.add_argument("--seed", type=int, default=1, help="Random seed")
    p_impact.add_argument("--warmup", type=float, default=30.0, help="Warmup duration in seconds")
    p_impact.add_argument(
        "--product-type", default="equity_delivery", help="equity_delivery | equity_intraday"
    )

    # sweep
    p_sweep = subparsers.add_parser("sweep", help="Run size sweep and demonstrate nonlinearity")
    p_sweep.add_argument(
        "--profile", default="mid_cap", help="large_cap | mid_cap | small_cap | all"
    )
    p_sweep.add_argument(
        "--sizes", default="100,500,1000,5000,10000", help="Comma-separated order sizes"
    )
    p_sweep.add_argument("--side", default="buy", help="buy | sell")
    p_sweep.add_argument("--seed", type=int, default=1, help="Random seed")
    p_sweep.add_argument("--warmup", type=float, default=30.0, help="Warmup duration in seconds")
    p_sweep.add_argument("--csv", default="sweep_results.csv", help="CSV output path")

    return parser


def main(argv: Sequence[str] | None = None) -> None:
    """Entry point for the CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "book":
        cmd_book(args)
    elif args.command == "impact":
        cmd_impact(args)
    elif args.command == "sweep":
        cmd_sweep(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main(sys.argv[1:])
