"""Static limit order book walk.

Takes a frozen BookSnapshot, walks price levels for a hypothetical order,
and computes market impact and slippage without mutating the book.
"""

from __future__ import annotations

from impactlab.engine.models import BookSnapshot, Side
from impactlab.impact.metrics import ImpactResult, LevelFill, SizeMode


def walk_book(
    snapshot: BookSnapshot,
    side: Side,
    size: int,
    mode: SizeMode = SizeMode.SHARES,
) -> ImpactResult:
    """Perform a static walk across the order book levels for a hypothetical order.

    Args:
        snapshot: Frozen immutable snapshot of the order book.
        side: Side of the hypothetical order (BUY or SELL).
        size: Size in shares (SizeMode.SHARES) or rupees (SizeMode.RUPEES).
        mode: Size mode (default: SHARES).

    Returns:
        ImpactResult containing price, slippage, and impact statistics.
    """
    levels = snapshot.asks if side == Side.BUY else snapshot.bids
    arrival_best = snapshot.best_ask if side == Side.BUY else snapshot.best_bid
    arrival_mid = snapshot.mid

    if not levels or arrival_best is None:
        # Empty side: no fills possible
        req_qty = size if mode == SizeMode.SHARES else 0
        return ImpactResult(
            side=side,
            requested_qty=req_qty,
            filled_qty=0,
            fill_ratio=0.0,
            total_notional=0,
            avg_price=None,
            arrival_best=arrival_best,
            arrival_mid=arrival_mid,
            post_mid=arrival_mid,
            slippage_vs_best=None,
            slippage_vs_mid=None,
            slippage_bps=None,
            price_impact_bps=None,
            impl_shortfall=0.0,
            levels_consumed=0,
            level_fills=(),
            unfilled_qty=req_qty,
        )

    # Budget / quantity setup
    if mode == SizeMode.RUPEES:
        remaining_budget = size * 100  # convert rupees to paise
        remaining_qty = 10**9  # large ceiling
    else:
        remaining_budget = 10**18  # large ceiling
        remaining_qty = size

    level_fills: list[LevelFill] = []
    filled_qty = 0
    total_notional = 0
    post_touch_price: int | None = None

    for idx, lvl in enumerate(levels):
        if remaining_qty <= 0:
            post_touch_price = lvl.price
            break

        if mode == SizeMode.RUPEES:
            if remaining_budget < lvl.price:
                post_touch_price = lvl.price
                break
            can_buy = remaining_budget // lvl.price
            fill_qty = min(lvl.qty, can_buy)
        else:
            fill_qty = min(lvl.qty, remaining_qty)

        if fill_qty > 0:
            level_notional = fill_qty * lvl.price
            level_fills.append(LevelFill(price=lvl.price, qty=fill_qty, notional=level_notional))
            filled_qty += fill_qty
            total_notional += level_notional
            remaining_qty -= fill_qty
            if mode == SizeMode.RUPEES:
                remaining_budget -= level_notional

            if fill_qty < lvl.qty:
                # Level was partially consumed, so it remains the best touch
                post_touch_price = lvl.price
                break
            # Level was fully consumed; if last level, next is None
            if idx + 1 < len(levels):
                post_touch_price = levels[idx + 1].price
            else:
                post_touch_price = None

    # Calculate post-trade mid
    post_mid: float | None = None
    if side == Side.BUY:
        if post_touch_price is not None and snapshot.best_bid is not None:
            post_mid = (snapshot.best_bid + post_touch_price) / 2.0
    else:
        if post_touch_price is not None and snapshot.best_ask is not None:
            post_mid = (post_touch_price + snapshot.best_ask) / 2.0

    # Fallback if post_mid could not be determined
    if post_mid is None:
        post_mid = arrival_mid

    # Requested quantity
    requested_qty = size if mode == SizeMode.SHARES else filled_qty
    fill_ratio = (filled_qty / requested_qty) if requested_qty > 0 else 0.0
    unfilled_qty = max(0, requested_qty - filled_qty)

    # Average price
    avg_price = (total_notional / filled_qty) if filled_qty > 0 else None

    # Slippage and impact metrics
    slippage_vs_best: float | None = None
    slippage_vs_mid: float | None = None
    slippage_bps: float | None = None
    price_impact_bps: float | None = None
    impl_shortfall: float | None = None

    if avg_price is not None:
        if side == Side.BUY:
            slippage_vs_best = avg_price - arrival_best
            if arrival_mid is not None:
                slippage_vs_mid = avg_price - arrival_mid
                if arrival_mid > 0:
                    slippage_bps = (slippage_vs_mid / arrival_mid) * 10_000
                impl_shortfall = total_notional - (filled_qty * arrival_mid)
            if post_mid is not None and arrival_mid is not None and arrival_mid > 0:
                price_impact_bps = ((post_mid - arrival_mid) / arrival_mid) * 10_000
        else:
            # SELL
            slippage_vs_best = arrival_best - avg_price
            if arrival_mid is not None:
                slippage_vs_mid = arrival_mid - avg_price
                if arrival_mid > 0:
                    slippage_bps = (slippage_vs_mid / arrival_mid) * 10_000
                impl_shortfall = (filled_qty * arrival_mid) - total_notional
            if post_mid is not None and arrival_mid is not None and arrival_mid > 0:
                price_impact_bps = ((arrival_mid - post_mid) / arrival_mid) * 10_000

    return ImpactResult(
        side=side,
        requested_qty=requested_qty,
        filled_qty=filled_qty,
        fill_ratio=fill_ratio,
        total_notional=total_notional,
        avg_price=avg_price,
        arrival_best=arrival_best,
        arrival_mid=arrival_mid,
        post_mid=post_mid,
        slippage_vs_best=slippage_vs_best,
        slippage_vs_mid=slippage_vs_mid,
        slippage_bps=slippage_bps,
        price_impact_bps=price_impact_bps,
        impl_shortfall=impl_shortfall,
        levels_consumed=len(level_fills),
        level_fills=tuple(level_fills),
        unfilled_qty=unfilled_qty,
    )
