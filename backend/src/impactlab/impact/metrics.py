"""Impact analysis metrics and data models.

Prices and notionals are in integer paise. Quantities are integers.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from impactlab.engine.models import Side


class SizeMode(StrEnum):
    """How the order size is specified."""

    SHARES = "shares"
    RUPEES = "rupees"


@dataclass(frozen=True, slots=True)
class LevelFill:
    """Detail of a single price level consumed during execution."""

    price: int  # in paise
    qty: int  # shares filled at this level
    notional: int  # in paise (price * qty)


@dataclass(frozen=True, slots=True)
class ImpactResult:
    """Comprehensive market impact calculation result."""

    side: Side
    requested_qty: int  # requested shares (or shares bought for rupee budget)
    filled_qty: int  # actual shares filled
    fill_ratio: float  # filled_qty / requested_qty (0.0 if requested_qty == 0)
    total_notional: int  # total cost paid or received in paise
    avg_price: float | None  # weighted average fill price in paise
    arrival_best: int | None  # best ask (BUY) or best bid (SELL) at arrival in paise
    arrival_mid: float | None  # arrival mid price in paise
    post_mid: float | None  # post-trade mid price in paise
    slippage_vs_best: float | None  # paise per share
    slippage_vs_mid: float | None  # paise per share (includes half-spread)
    slippage_bps: float | None  # basis points vs arrival mid
    price_impact_bps: float | None  # post-trade mid shift in basis points
    impl_shortfall: float | None  # total implementation shortfall in paise
    levels_consumed: int  # count of distinct price levels touched
    level_fills: tuple[LevelFill, ...]  # per-level breakdown
    unfilled_qty: int  # requested_qty - filled_qty
