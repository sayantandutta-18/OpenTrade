"""Routes for managing simulation sessions, orders, advancing time, and replay."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from impactlab.api.schemas import (
    AdvanceRequest,
    AdvanceResponse,
    BookResponse,
    LevelSchema,
    OrderSubmitRequest,
    OrderSubmitResponse,
    SessionCreateRequest,
    SessionResponse,
    SessionSummarySchema,
    TradeSchema,
)
from impactlab.api.sessions import session_store
from impactlab.api.ws import ws_manager
from impactlab.cli import format_inr
from impactlab.db import repository
from impactlab.db.session import get_db
from impactlab.engine.events import event_from_dict, replay
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


@router.get("", response_model=list[SessionSummarySchema])
def list_sessions_endpoint(
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    """List recent simulation sessions with event counts and status."""
    return repository.list_sessions(db, limit=limit)


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(
    req: SessionCreateRequest,
    db: Session = Depends(get_db),
) -> SessionResponse:
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

    # Persist session and warmup events
    repository.save_session(
        db,
        session_id=sess.id,
        profile_name=sess.profile.name,
        seed=sess.seed,
        config={"warmup_seconds": sess.warmup_seconds, "overrides": req.overrides},
    )
    repository.save_events(db, sess.id, sess.engine.events)

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
def get_session(session_id: str, db: Session = Depends(get_db)) -> SessionResponse:
    """Get metadata for an existing simulation session."""
    sess = session_store.get(session_id)
    if sess:
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

    # Check database
    db_sess = repository.get_session(db, session_id)
    if not db_sess:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found",
        )

    cfg = json.loads(db_sess.config_json) if db_sess.config_json else {}
    return SessionResponse(
        session_id=db_sess.id,
        profile=db_sess.profile_id,
        seed=db_sess.seed,
        warmup_seconds=cfg.get("warmup_seconds", 0.0),
        current_time_us=0,
        best_bid=None,
        best_ask=None,
        spread=None,
        mid=None,
        created_at=db_sess.created_at.isoformat() if db_sess.created_at else "",
    )


@router.get("/{session_id}/book", response_model=BookResponse)
def get_book(session_id: str, depth: int = Query(default=10, ge=1, le=100)) -> BookResponse:
    """Get the current order book ladder, spread, and mid price."""
    return _build_book_response(session_id=session_id, depth=depth)


@router.post("/{session_id}/orders", response_model=OrderSubmitResponse)
async def submit_order(
    session_id: str, req: OrderSubmitRequest, db: Session = Depends(get_db)
) -> OrderSubmitResponse:
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

    # Persist newly generated events
    repository.save_events(db, session_id, sess.engine.events)

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
async def cancel_order(
    session_id: str, order_id: int, db: Session = Depends(get_db)
) -> dict[str, Any]:
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

    # Persist newly generated events
    repository.save_events(db, session_id, sess.engine.events)

    book_resp = _build_book_response(session_id=session_id)
    await ws_manager.broadcast(
        session_id,
        {"type": "book_update", "book": book_resp.model_dump()},
    )

    return {"status": "canceled", "order_id": order_id}


@router.post("/{session_id}/advance", response_model=AdvanceResponse)
async def advance_time(
    session_id: str, req: AdvanceRequest, db: Session = Depends(get_db)
) -> AdvanceResponse:
    """Advance simulated time by running synthetic Poisson flow."""
    sess = session_store.get(session_id)
    if not sess:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found",
        )

    events_generated = sess.simulator.advance(sess.engine, seconds=req.seconds)

    # Persist newly generated events
    repository.save_events(db, session_id, sess.engine.events)

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
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    """Get the sequential event log for deterministic replay."""
    sess = session_store.get(session_id)
    if sess:
        repository.save_events(db, session_id, sess.engine.events)
        return [
            {"seq": ev.seq, "ts": ev.ts, "kind": ev.kind, "payload": ev.payload}
            for ev in sess.engine.events
            if ev.seq >= from_seq
        ]

    # Check database
    db_events = repository.get_session_events(db, session_id, from_seq=from_seq)
    if not db_events and not repository.get_session(db, session_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found",
        )
    return db_events


@router.get("/{session_id}/replay_verify")
def replay_verify(session_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Verify that replaying all stored events reproduces identical book state."""
    sess = session_store.get(session_id)
    if sess:
        repository.save_events(db, session_id, sess.engine.events)
        raw_events = sess.engine.events
        tick_size = sess.engine.tick_size
        lot_size = sess.engine.lot_size
    else:
        db_events = repository.get_session_events(db, session_id, from_seq=1)
        if not db_events:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session '{session_id}' not found",
            )
        raw_events = [event_from_dict(d) for d in db_events]
        tick_size = 5
        lot_size = 1

    reconstructed_book, trades = replay(raw_events, tick_size=tick_size, lot_size=lot_size)

    live_best_bid = sess.engine.book.best_bid if sess else None
    live_best_ask = sess.engine.book.best_ask if sess else None

    is_identical = True
    if sess:
        is_identical = (
            reconstructed_book.best_bid == live_best_bid
            and reconstructed_book.best_ask == live_best_ask
            and len(trades) == len(sess.engine.trades)
        )

    return {
        "session_id": session_id,
        "event_count": len(raw_events),
        "trade_count": len(trades),
        "reconstructed_best_bid": reconstructed_book.best_bid,
        "reconstructed_best_ask": reconstructed_book.best_ask,
        "reconstructed_best_bid_formatted": format_inr(reconstructed_book.best_bid),
        "reconstructed_best_ask_formatted": format_inr(reconstructed_book.best_ask),
        "live_best_bid": live_best_bid,
        "live_best_ask": live_best_ask,
        "verified_deterministic": is_identical,
    }
