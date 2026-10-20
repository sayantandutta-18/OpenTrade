"""Tests for database persistence, session history, and deterministic replay."""

from __future__ import annotations

from fastapi.testclient import TestClient

from impactlab.api.main import app
from impactlab.api.sessions import session_store
from impactlab.db import repository
from impactlab.db.session import SessionLocal
from impactlab.engine.events import event_from_dict, replay

client = TestClient(app)


def test_session_persistence_and_listing() -> None:
    """Test that creating a session persists to DB and shows in list."""
    res = client.post(
        "/api/v1/sessions",
        json={"profile": "small_cap", "seed": 999, "warmup_seconds": 5.0},
    )
    assert res.status_code == 201
    data = res.json()
    session_id = data["session_id"]

    # Verify listing
    list_res = client.get("/api/v1/sessions")
    assert list_res.status_code == 200
    sessions_list = list_res.json()
    assert any(s["id"] == session_id for s in sessions_list)

    # Check event count is positive from warmup
    matched = next(s for s in sessions_list if s["id"] == session_id)
    assert matched["event_count"] > 0
    assert matched["profile"] == "small_cap"
    assert matched["seed"] == 999


def test_replay_verification_live_and_cold_from_db() -> None:
    """Test that replay reproduces the exact book state both live and from cold DB."""
    # 1. Create a session
    res = client.post(
        "/api/v1/sessions",
        json={"profile": "mid_cap", "seed": 42, "warmup_seconds": 10.0},
    )
    assert res.status_code == 201
    sess_data = res.json()
    session_id = sess_data["session_id"]

    # 2. Advance time and submit an order
    client.post(f"/api/v1/sessions/{session_id}/advance", json={"seconds": 5.0})
    order_res = client.post(
        f"/api/v1/sessions/{session_id}/orders",
        json={"side": "BUY", "type": "LIMIT", "qty": 50, "price": 44900},
    )
    assert order_res.status_code == 200

    # 3. Live replay verification
    verify_res = client.get(f"/api/v1/sessions/{session_id}/replay_verify")
    assert verify_res.status_code == 200
    verify_data = verify_res.json()
    assert verify_data["verified_deterministic"] is True
    assert verify_data["reconstructed_best_bid"] == verify_data["live_best_bid"]
    assert verify_data["reconstructed_best_ask"] == verify_data["live_best_ask"]

    # 4. Evict from in-memory cache to simulate cold server restart
    session_store.delete(session_id)
    assert session_store.get(session_id) is None

    # 5. Cold replay from database events
    cold_events_res = client.get(f"/api/v1/sessions/{session_id}/events")
    assert cold_events_res.status_code == 200
    db_events = cold_events_res.json()
    assert len(db_events) == verify_data["event_count"]

    # Replay directly using engine logic
    events_objs = [event_from_dict(d) for d in db_events]
    reconstructed_book, trades = replay(events_objs, tick_size=5, lot_size=1)
    assert reconstructed_book.best_bid == verify_data["reconstructed_best_bid"]
    assert reconstructed_book.best_ask == verify_data["reconstructed_best_ask"]
    assert len(trades) == verify_data["trade_count"]

    # Cold replay endpoint
    cold_verify_res = client.get(f"/api/v1/sessions/{session_id}/replay_verify")
    assert cold_verify_res.status_code == 200
    assert cold_verify_res.json()["event_count"] == len(db_events)


def test_repository_save_and_query_events() -> None:
    """Direct repository unit test for event sequence integrity."""
    db = SessionLocal()
    try:
        from impactlab.engine.models import Event

        test_sess_id = "test-repo-session-123"
        repository.save_session(db, session_id=test_sess_id, profile_name="large_cap", seed=10)

        ev1 = Event(seq=1, ts=100, kind="ACCEPTED", payload={"order_id": 1, "qty": 10})
        ev2 = Event(seq=2, ts=200, kind="TRADE", payload={"trade_id": 1, "qty": 10})
        repository.save_events(db, test_sess_id, [ev1, ev2])

        events = repository.get_session_events(db, test_sess_id, from_seq=1)
        assert len(events) == 2
        assert events[0]["seq"] == 1
        assert events[1]["seq"] == 2

        # from_seq filter
        events_from_2 = repository.get_session_events(db, test_sess_id, from_seq=2)
        assert len(events_from_2) == 1
        assert events_from_2[0]["seq"] == 2
    finally:
        db.close()
