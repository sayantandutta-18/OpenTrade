"""Golden file test: assert event log byte-determinism and exact book replay."""

from pathlib import Path

from impactlab.engine.events import events_from_jsonl, events_to_jsonl, replay
from impactlab.engine.matcher import MatchingEngine
from impactlab.engine.models import Order, OrderType, Side

GOLDEN_DIR = Path(__file__).parent


def test_golden_scenario_reference() -> None:
    golden_path = GOLDEN_DIR / "scenario_reference.jsonl"
    assert golden_path.exists(), f"Golden file not found: {golden_path}"
    expected_content = golden_path.read_text(encoding="utf-8")

    # Run the exact reference scenario from scratch
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
    engine.submit(
        Order(
            id=7,
            side=Side.BUY,
            type=OrderType.MARKET,
            price=None,
            qty=400,
            remaining=400,
            ts=7,
            owner="user",
        )
    )

    actual_content = events_to_jsonl(engine.events)

    # 1. Byte-identical event log verification
    assert actual_content == expected_content

    # 2. Replay from the golden file
    golden_events = events_from_jsonl(expected_content)
    replayed_book, replayed_trades = replay(golden_events, tick_size=5, lot_size=1)

    # 3. Assert replayed state matches original
    assert replayed_book.best_bid == 9990
    assert replayed_book.best_ask == 10020
    assert len(replayed_trades) == 3
    assert sum(t.price * t.qty for t in replayed_trades) == 4_004_000
    assert sum(t.qty for t in replayed_trades) == 400
