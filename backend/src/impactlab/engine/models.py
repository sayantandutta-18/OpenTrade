"""Core domain models and data structures for the matching engine.

All prices are stored as integers in paise (e.g., Rs 100.00 = 10000 paise).
All quantities are integers representing shares.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class Side(StrEnum):
    """Order side: BUY or SELL."""

    BUY = "BUY"
    SELL = "SELL"

    @property
    def opposite(self) -> Side:
        """Return the opposite side."""
        return Side.SELL if self == Side.BUY else Side.BUY


class OrderType(StrEnum):
    """Supported order types."""

    LIMIT = "LIMIT"
    MARKET = "MARKET"
    IOC = "IOC"
    FOK = "FOK"
    POST_ONLY = "POST_ONLY"


class Status(StrEnum):
    """Order lifecycle status."""

    NEW = "NEW"
    PARTIAL = "PARTIAL"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    REJECTED = "REJECTED"


@dataclass(slots=True)
class Order:
    """Represents an order in the matching engine."""

    id: int
    side: Side
    type: OrderType
    price: int | None  # in paise; None for MARKET orders
    qty: int  # initial quantity in shares
    remaining: int  # remaining open quantity in shares
    ts: int  # simulated sequence timestamp
    owner: str  # identifier, e.g. 'user', 'mm_0', 'trader_1'
    status: Status = Status.NEW


@dataclass(slots=True)
class Trade:
    """Represents an executed trade match."""

    id: int
    price: int  # execution price in paise
    qty: int  # filled quantity in shares
    taker_order_id: int
    maker_order_id: int
    taker_side: Side
    ts: int  # simulated sequence timestamp


@dataclass(slots=True)
class Event:
    """Represents a state change event in the matching engine."""

    seq: int
    ts: int
    kind: str  # ACCEPTED | TRADE | CANCELED | REJECTED | MODIFIED
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class LevelSummary:
    """Aggregated volume summary for a single price level."""

    price: int  # in paise
    qty: int  # total volume in shares
    order_count: int  # number of resting orders at this price


@dataclass(frozen=True, slots=True)
class BookSnapshot:
    """Immutable snapshot of the order book state."""

    ts: int
    bids: tuple[LevelSummary, ...]
    asks: tuple[LevelSummary, ...]
    best_bid: int | None
    best_ask: int | None
    spread: int | None
    mid: float | None
    total_bid_qty: int
    total_ask_qty: int
