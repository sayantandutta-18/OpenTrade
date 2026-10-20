"""Routes for managing simulation sessions, orders, and advancing time."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, status

from impactlab.api.schemas import (
    AdvanceRequest,
    AdvanceResponse,
    BookResponse,
    LevelSchema,
    OrderSubmitRequest,
    OrderSubmitResponse,
    SessionCreateRequest,
    SessionResponse,
    TradeSchema,
)
from impactlab.api.sessions import session_store
from impactlab.api.ws import ws_manager
from impactlab.cli import format_inr
from impactlab.engine.models import Order

router = APIRouter(prefix="/sessions", tags=["sessions"])


def _build_book_response(session_id: str, depth: int = 10) -> BookResponse:
    sess = session_store.get(session_id)
    if not sess:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found",
        )
    snap = sess.engine.book.snapshot(ts=sess.simulator.current_time_us)
    bids_depth, asks_depth = sess.engine.book.depth(levels=depth)

    return BookResponse(
        session_id=session_id,
        ts=snap.ts,
        best_bid=snap.best_bid,
        best_bid_formatted=format_inr(snap.best_bid),
        best_ask=snap.best_ask,
        best_ask_formatted=format_inr(snap.best_ask),
        spread=snap.spread,
        spread_formatted=format_inr(snap.spread),
        mid=snap.mid,
        mid_formatted=format_inr(snap.mid),
        bids=[
            LevelSchema(
                price=lvl.price,
                price_formatted=format_inr(lvl.price),
                qty=lvl.qty,
                order_count=lvl.order_count,
            )
            for lvl in bids_depth
        ],
        asks=[
            LevelSchema(
                price=lvl.price,
                price_formatted=format_inr(lvl.price),
                qty=lvl.qty,
                order_count=lvl.order_count,
            )
            for lvl in asks_depth
        ],
    )


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(req: SessionCreateRequest) -> SessionResponse:
    """Create a new simulation session seeded with synthetic order flow."""
    try:
        sess = session_store.create(
            profile_name=req.profile,
            seed=req.seed,
            warmup_seconds=req.warmup_seconds,
            overrides=req.overrides,
        )
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e

    return SessionResponse(
        session_id=sess.id,
        profile=sess.profile.name,
        seed=sess.seed,
        warmup_seconds=sess.warmup_seconds,
        current_time_us=sess.simulator.current_time_us,
        best_bid=sess.engine.book.best_bid,
        best_ask=sess.engine.book.best_ask,
        spread=sess.engine.book.spread,
        mid=sess.engine.book.mid,
        created_at=sess.created_at,
    )


@router.get("/{session_id}", response_model=SessionResponse)
def get_session(session_id: str) -> SessionResponse:
    """Get metadata for an existing simulation session."""
    sess = session_store.get(session_id)
    if not sess:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found",
        )
    return SessionResponse(
        session_id=sess.id,
        profile=sess.profile.name,
        seed=sess.seed,
        warmup_seconds=sess.warmup_seconds,
        current_time_us=sess.simulator.current_time_us,
        best_bid=sess.engine.book.best_bid,
        best_ask=sess.engine.book.best_ask,
        spread=sess.engine.book.spread,
        mid=sess.engine.book.mid,
        created_at=sess.created_at,
    )


@router.get("/{session_id}/book", response_model=BookResponse)
def get_book(session_id: str, depth: int = Query(default=10, ge=1, le=100)) -> BookResponse:
    """Get the current order book ladder, spread, and mid price."""
    return _build_book_response(session_id=session_id, depth=depth)


@router.post("/{session_id}/orders", response_model=OrderSubmitResponse)
async def submit_order(session_id: str, req: OrderSubmitRequest) -> OrderSubmitResponse:
    """Submit a real or hypothetical order to the live session book."""
    sess = session_store.get(session_id)
    if not sess:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found",
        )

    order_id = sess.simulator._next_order_id()
    order = Order(
        id=order_id,
        side=req.side,
        type=req.type,
        price=req.price,
        qty=req.qty,
        remaining=req.qty,
        ts=sess.simulator.current_time_us,
        owner=req.owner,
    )

    trades = sess.engine.submit(order)
    filled_qty = sum(t.qty for t in trades)

    # Broadcast book update and trades over WebSocket
    book_resp = _build_book_response(session_id=session_id)
    await ws_manager.broadcast(
        session_id,
        {
            "type": "book_update",
            "book": book_resp.model_dump(),
            "trades": [
                {
                    "id": t.id,
                    "price": t.price,
                    "price_formatted": format_inr(t.price),
                    "qty": t.qty,
                    "taker_side": t.taker_side.value,
                }
                for t in trades
            ],
        },
    )

    return OrderSubmitResponse(
        order_id=order_id,
        status=order.status.value,
        filled_qty=filled_qty,
        remaining=order.remaining,
        trades=[
            TradeSchema(
                id=t.id,
                price=t.price,
                price_formatted=format_inr(t.price),
                qty=t.qty,
                taker_order_id=t.taker_order_id,
                maker_order_id=t.maker_order_id,
                taker_side=t.taker_side,
                ts=t.ts,
            )
            for t in trades
        ],
    )


@router.delete("/{session_id}/orders/{order_id}")
async def cancel_order(session_id: str, order_id: int) -> dict[str, Any]:
    """Cancel a resting order in the session book."""
    sess = session_store.get(session_id)
    if not sess:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found",
        )

    canceled = sess.engine.cancel(order_id)
    if not canceled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order {order_id} not found in book",
        )

    book_resp = _build_book_response(session_id=session_id)
    await ws_manager.broadcast(
        session_id,
        {"type": "book_update", "book": book_resp.model_dump()},
    )

    return {"status": "canceled", "order_id": order_id}


@router.post("/{session_id}/advance", response_model=AdvanceResponse)
async def advance_time(session_id: str, req: AdvanceRequest) -> AdvanceResponse:
    """Advance simulated time by running synthetic Poisson flow."""
    sess = session_store.get(session_id)
    if not sess:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found",
        )

    events_generated = sess.simulator.advance(sess.engine, seconds=req.seconds)
    book_resp = _build_book_response(session_id=session_id)

    # Broadcast update
    await ws_manager.broadcast(
        session_id,
        {"type": "book_update", "book": book_resp.model_dump()},
    )

    return AdvanceResponse(
        session_id=session_id,
        advanced_seconds=req.seconds,
        events_generated=events_generated,
        current_time_us=sess.simulator.current_time_us,
        book=book_resp,
    )


@router.get("/{session_id}/events")
def get_events(
    session_id: str,
    from_seq: int = Query(default=1, ge=1),
) -> list[dict[str, Any]]:
    """Get the sequential event log for deterministic replay."""
    sess = session_store.get(session_id)
    if not sess:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found",
        )

    events = [
        {"seq": ev.seq, "ts": ev.ts, "kind": ev.kind, "payload": ev.payload}
        for ev in sess.engine.events
        if ev.seq >= from_seq
    ]
    return events
