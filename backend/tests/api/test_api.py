"""Tests for FastAPI endpoints using httpx.AsyncClient."""

import pytest
from httpx import ASGITransport, AsyncClient

from impactlab.api.main import app
from impactlab.api.sessions import session_store
from impactlab.engine.matcher import MatchingEngine
from impactlab.engine.models import Order, OrderType, Side
from impactlab.flow.generators import FlowSimulator
from impactlab.flow.profiles import MID_CAP


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_health_check() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


@pytest.mark.anyio
async def test_list_profiles() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/profiles")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 3
        names = [p["name"] for p in data]
        assert "large_cap" in names
        assert "mid_cap" in names
        assert "small_cap" in names


@pytest.mark.anyio
async def test_session_lifecycle_and_orders() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create session
        create_resp = await client.post(
            "/api/v1/sessions",
            json={"profile": "mid_cap", "seed": 42, "warmup_seconds": 5.0},
        )
        assert create_resp.status_code == 201
        sess_data = create_resp.json()
        session_id = sess_data["session_id"]
        assert session_id is not None

        # 2. Get session
        get_resp = await client.get(f"/api/v1/sessions/{session_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["profile"] == "mid_cap"

        # 3. Get book
        book_resp = await client.get(f"/api/v1/sessions/{session_id}/book?depth=5")
        assert book_resp.status_code == 200
        book_data = book_resp.json()
        assert len(book_data["bids"]) > 0
        assert len(book_data["asks"]) > 0
        assert book_data["best_bid"] is not None

        # 4. Advance time
        adv_resp = await client.post(
            f"/api/v1/sessions/{session_id}/advance",
            json={"seconds": 2.0},
        )
        assert adv_resp.status_code == 200
        assert adv_resp.json()["advanced_seconds"] == 2.0

        # 5. Submit limit order
        ord_resp = await client.post(
            f"/api/v1/sessions/{session_id}/orders",
            json={
                "side": "BUY",
                "type": "LIMIT",
                "qty": 50,
                "price": 10000,
                "owner": "test_user",
            },
        )
        assert ord_resp.status_code == 200
        assert ord_resp.json()["order_id"] > 0

        # 6. Get events
        ev_resp = await client.get(f"/api/v1/sessions/{session_id}/events?from_seq=1")
        assert ev_resp.status_code == 200
        assert len(ev_resp.json()) > 0


@pytest.mark.anyio
async def test_simulate_impact_endpoint_reference_example() -> None:
    # Set up session with the exact 6.5 reference example book
    sess = session_store.create(profile_name="mid_cap", seed=1, warmup_seconds=0.0)
    engine = MatchingEngine(tick_size=5, lot_size=1)
    engine.submit(
        Order(
            id=1,
            side=Side.SELL,
            type=OrderType.LIMIT,
            price=10000,
            qty=100,
            remaining=100,
            ts=1,
            owner="mm",
        )
    )
    engine.submit(
        Order(
            id=2,
            side=Side.SELL,
            type=OrderType.LIMIT,
            price=10010,
            qty=200,
            remaining=200,
            ts=2,
            owner="mm",
        )
    )
    engine.submit(
        Order(
            id=3,
            side=Side.SELL,
            type=OrderType.LIMIT,
            price=10020,
            qty=300,
            remaining=300,
            ts=3,
            owner="mm",
        )
    )
    engine.submit(
        Order(
            id=4,
            side=Side.BUY,
            type=OrderType.LIMIT,
            price=9990,
            qty=100,
            remaining=100,
            ts=4,
            owner="mm",
        )
    )
    engine.submit(
        Order(
            id=5,
            side=Side.BUY,
            type=OrderType.LIMIT,
            price=9980,
            qty=200,
            remaining=200,
            ts=5,
            owner="mm",
        )
    )
    engine.submit(
        Order(
            id=6,
            side=Side.BUY,
            type=OrderType.LIMIT,
            price=9970,
            qty=300,
            remaining=300,
            ts=6,
            owner="mm",
        )
    )
    sess.engine = engine
    sess.simulator = FlowSimulator(profile=MID_CAP, seed=1)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Simulate BUY 400 shares
        resp = await client.post(
            "/api/v1/impact/simulate",
            json={
                "session_id": sess.id,
                "side": "BUY",
                "size": {"mode": "shares", "value": 400},
                "mode": "static",
                "product_type": "equity_delivery",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["filled_qty"] == 400
        assert data["total_notional"] == 4_004_000  # Rs 40,040 in paise
        assert data["avg_price"] == 10010.0  # Rs 100.10
        assert data["slippage_vs_best"] == 10.0  # Rs 0.10
        assert data["levels_consumed"] == 3
        assert "Simulated results" in data["disclaimer"]
        assert data["charges"]["total_charges"] > 0
        assert data["all_in_cost"] > 0


@pytest.mark.anyio
async def test_simulate_impact_dynamic_mode() -> None:
    sess = session_store.create(profile_name="mid_cap", seed=42, warmup_seconds=5.0)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/impact/simulate",
            json={
                "session_id": sess.id,
                "side": "BUY",
                "size": {"mode": "shares", "value": 200},
                "mode": "dynamic",
                "strategy": {"name": "twap", "duration_seconds": 5.0, "num_slices": 2},
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["requested_qty"] == 200
        assert data["filled_qty"] > 0


@pytest.mark.anyio
async def test_experiments_endpoint() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Trigger size sweep experiment
        resp = await client.post(
            "/api/v1/experiments",
            json={
                "type": "size_sweep",
                "params": {"profile": "large_cap", "sizes": [100, 500], "warmup_seconds": 1.0},
                "seed": 10,
                "runs": 3,
            },
        )
        assert resp.status_code == 201
        exp_data = resp.json()
        exp_id = exp_data["experiment_id"]
        assert exp_data["status"] == "COMPLETED"
        assert len(exp_data["chart_data"]) == 2

        # Query experiment
        get_resp = await client.get(f"/api/v1/experiments/{exp_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["experiment_id"] == exp_id


@pytest.mark.anyio
async def test_error_formatting_404() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/sessions/non-existent-session-id")
        assert resp.status_code == 404
        data = resp.json()
        assert "error" in data
        assert data["error"]["code"] == "NOT_FOUND"
