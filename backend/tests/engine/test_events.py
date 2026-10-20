"""Tests for Event logging, JSONL serialization, and deterministic replay."""

from impactlab.engine.events import events_from_jsonl, events_to_jsonl, replay
from impactlab.engine.matcher import MatchingEngine
from impactlab.engine.models import Order, OrderType, Side


def test_event_serialization_and_replay() -> None:
    engine = MatchingEngine(tick_size=5, lot_size=1)

    # 1. Place initial limit orders
    engine.submit(
        Order(
            id=1,
            side=Side.BUY,
            type=OrderType.LIMIT,
            price=9990,
            qty=100,
            remaining=100,
            ts=1,
            owner="u1",
        )
    )
    engine.submit(
        Order(
            id=2,
            side=Side.BUY,
            type=OrderType.LIMIT,
            price=9980,
            qty=200,
            remaining=200,
            ts=2,
            owner="u2",
        )
    )
    engine.submit(
        Order(
            id=3,
            side=Side.SELL,
            type=OrderType.LIMIT,
            price=10010,
            qty=150,
            remaining=150,
            ts=3,
            owner="u3",
        )
    )
    engine.submit(
        Order(
            id=4,
            side=Side.SELL,
            type=OrderType.LIMIT,
            price=10020,
            qty=300,
            remaining=300,
            ts=4,
            owner="u4",
        )
    )

    # 2. Modify an order (decrease qty of order 2)
    engine.modify(order_id=2, new_qty=120)

    # 3. Cancel an order (order 4)
    engine.cancel(order_id=4)

    # 4. Market order taking liquidity from order 3
    engine.submit(
        Order(
            id=5,
            side=Side.BUY,
            type=OrderType.MARKET,
            price=None,
            qty=50,
            remaining=50,
            ts=5,
            owner="buyer",
        )
    )

    # Check original book state
    orig_bids, orig_asks = engine.book.depth(10)
    orig_trades = list(engine.trades)

    # Serialize events to JSONL
    jsonl_output = events_to_jsonl(engine.events)
    assert len(jsonl_output.strip().splitlines()) == len(engine.events)

    # Deserialize back to events
    recovered_events = events_from_jsonl(jsonl_output)
    assert len(recovered_events) == len(engine.events)
    for orig_ev, rec_ev in zip(engine.events, recovered_events, strict=True):
        assert orig_ev.seq == rec_ev.seq
        assert orig_ev.ts == rec_ev.ts
        assert orig_ev.kind == rec_ev.kind
        assert orig_ev.payload == rec_ev.payload

    # Replay from events
    replayed_book, replayed_trades = replay(recovered_events, tick_size=5, lot_size=1)

    # Verify identical book state
    rep_bids, rep_asks = replayed_book.depth(10)
    assert orig_bids == rep_bids
    assert orig_asks == rep_asks
    assert engine.book.best_bid == replayed_book.best_bid
    assert engine.book.best_ask == replayed_book.best_ask
    assert engine.book.spread == replayed_book.spread

    # Verify identical trades
    assert len(orig_trades) == len(replayed_trades)
    for ot, rt in zip(orig_trades, replayed_trades, strict=True):
        assert ot.id == rt.id
        assert ot.price == rt.price
        assert ot.qty == rt.qty
        assert ot.taker_order_id == rt.taker_order_id
        assert ot.maker_order_id == rt.maker_order_id
        assert ot.taker_side == rt.taker_side
