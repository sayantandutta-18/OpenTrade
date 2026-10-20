"""Pydantic schemas for request and response models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from impactlab.engine.models import OrderType, Side
from impactlab.impact.metrics import SizeMode


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


class ProfileResponse(BaseModel):
    name: str
    description: str
    reference_price: int
    reference_price_formatted: str
    tick_size: int
    lot_size: int
    typical_spread_ticks: int
    target_depth_shares: int
    limit_arrival_rate: float
    market_arrival_rate: float
    cancel_rate: float
    daily_volatility_pct: float


class SessionCreateRequest(BaseModel):
    profile: str = "mid_cap"
    seed: int = 1
    warmup_seconds: float = 30.0
    overrides: dict[str, Any] | None = None


class SessionResponse(BaseModel):
    session_id: str
    profile: str
    seed: int
    warmup_seconds: float
    current_time_us: int
    best_bid: int | None
    best_ask: int | None
    spread: int | None
    mid: float | None
    created_at: str


class SessionSummarySchema(BaseModel):
    id: str
    profile: str
    seed: int
    status: str
    created_at: str
    event_count: int


class LevelSchema(BaseModel):
    price: int
    price_formatted: str
    qty: int
    order_count: int


class BookResponse(BaseModel):
    session_id: str
    ts: int
    best_bid: int | None
    best_bid_formatted: str
    best_ask: int | None
    best_ask_formatted: str
    spread: int | None
    spread_formatted: str
    mid: float | None
    mid_formatted: str
    bids: list[LevelSchema]
    asks: list[LevelSchema]


class OrderSubmitRequest(BaseModel):
    side: Side
    type: OrderType = OrderType.LIMIT
    qty: int = Field(gt=0)
    price: int | None = None  # in paise
    owner: str = "user"


class TradeSchema(BaseModel):
    id: int
    price: int
    price_formatted: str
    qty: int
    taker_order_id: int
    maker_order_id: int
    taker_side: Side
    ts: int


class OrderSubmitResponse(BaseModel):
    order_id: int
    status: str
    filled_qty: int
    remaining: int
    trades: list[TradeSchema]


class AdvanceRequest(BaseModel):
    seconds: float = Field(gt=0, le=3600, default=1.0)


class AdvanceResponse(BaseModel):
    session_id: str
    advanced_seconds: float
    events_generated: int
    current_time_us: int
    book: BookResponse


class SizeInput(BaseModel):
    mode: SizeMode = SizeMode.SHARES
    value: int = Field(gt=0)


class StrategyInput(BaseModel):
    name: str = "market"
    duration_seconds: float = 60.0
    num_slices: int = 5


class ImpactSimulateRequest(BaseModel):
    session_id: str
    side: Side
    size: SizeInput
    mode: str = "static"  # static | dynamic
    product_type: str = "equity_delivery"
    strategy: StrategyInput = Field(default_factory=StrategyInput)


class LevelFillSchema(BaseModel):
    price: int
    price_formatted: str
    qty: int
    notional: int
    notional_formatted: str


class ChargesSchema(BaseModel):
    product_type: str
    brokerage: int
    brokerage_formatted: str
    stt: int
    stt_formatted: str
    exchange_txn_fee: int
    exchange_txn_fee_formatted: str
    sebi_fee: int
    sebi_fee_formatted: str
    stamp_duty: int
    stamp_duty_formatted: str
    gst: int
    gst_formatted: str
    total_charges: int
    total_charges_formatted: str
    as_of: str
    source_note: str


class ImpactSimulateResponse(BaseModel):
    session_id: str
    side: Side
    mode: str
    requested_qty: int
    filled_qty: int
    unfilled_qty: int
    fill_ratio: float
    total_notional: int
    total_notional_formatted: str
    avg_price: float | None
    avg_price_formatted: str
    arrival_best: int | None
    arrival_best_formatted: str
    arrival_mid: float | None
    arrival_mid_formatted: str
    post_mid: float | None
    post_mid_formatted: str
    slippage_vs_best: float | None
    slippage_vs_best_formatted: str
    slippage_vs_mid: float | None
    slippage_vs_mid_formatted: str
    slippage_bps: float | None
    price_impact_bps: float | None
    impl_shortfall: float | None
    impl_shortfall_formatted: str
    levels_consumed: int
    level_fills: list[LevelFillSchema]
    charges: ChargesSchema
    all_in_cost: float
    all_in_cost_formatted: str
    disclaimer: str


class ExperimentCreateRequest(BaseModel):
    type: str = "size_sweep"  # size_sweep | strategy_comparison | spread_sweep
    params: dict[str, Any] = Field(default_factory=dict)
    seed: int = 42
    runs: int = 50


class ExperimentResponse(BaseModel):
    experiment_id: str
    experiment_type: str
    status: str
    master_seed: int
    runs: int
    summary: dict[str, Any]
    chart_data: list[dict[str, Any]]
