"""Test the canonical PRD Section 6.5 reference example.

Tick size 5 paise (Rs 0.05).
Initial Book:
Ask: 100.00 (100), 100.10 (200), 100.20 (300)
Bid: 99.90 (100), 99.80 (200), 99.70 (300)

Market BUY 400:
Trades: 100 @ 100.00, 200 @ 100.10, 100 @ 100.20.
Total cost: Rs 40,040. Average: Rs 100.10.
Slippage vs best ask: Rs 0.10 / share, 10 bps.
After: best ask = 100.20 with 200 remaining.
"""

from impactlab.engine.matcher import MatchingEngine
from impactlab.engine.models import Order, OrderType, Side


def test_reference_example() -> None:
    engine = MatchingEngine(tick_size=5, lot_size=1)

    # Seed the asks
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

    # Seed the bids
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

    # State before order
    assert engine.book.best_bid == 9990
    assert engine.book.best_ask == 10000
    assert engine.book.spread == 10  # Rs 0.10

    # Market BUY 400 shares
    taker_order = Order(
        id=7,
        side=Side.BUY,
        type=OrderType.MARKET,
        price=None,
        qty=400,
        remaining=400,
        ts=7,
        owner="user",
    )
    trades = engine.submit(taker_order)

    # Validate trades
    assert len(trades) == 3
    assert trades[0].price == 10000 and trades[0].qty == 100
    assert trades[1].price == 10010 and trades[1].qty == 200
    assert trades[2].price == 10020 and trades[2].qty == 100

    # Total cost in paise and rupees
    total_cost_paise = sum(t.price * t.qty for t in trades)
    total_qty = sum(t.qty for t in trades)
    avg_price_paise = total_cost_paise / total_qty

    assert total_cost_paise == 4_004_000  # Rs 40,040 in paise
    assert avg_price_paise == 10010.0  # Rs 100.10

    # Slippage vs best ask (10000 paise)
    slippage_paise = avg_price_paise - 10000
    assert slippage_paise == 10.0  # Rs 0.10 per share

    # Slippage in basis points vs arrival best ask: 10 / 10000 * 10000 = 10 bps
    slippage_bps = (slippage_paise / 10000) * 10_000
    assert slippage_bps == 10.0

    # Book state after
    assert engine.book.best_ask == 10020
    remaining_at_10020 = engine.book.asks[10020][0].remaining
    assert remaining_at_10020 == 200

    engine.check_invariants()
