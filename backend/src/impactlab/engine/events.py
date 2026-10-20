"""Event log serialization, deserialization, and deterministic replay utilities."""

from __future__ import annotations

import json
from typing import Any

from impactlab.engine.book import OrderBook
from impactlab.engine.matcher import MatchingEngine
from impactlab.engine.models import Event, Order, OrderType, Side, Trade


def event_to_dict(ev: Event) -> dict[str, Any]:
    """Convert an Event to a JSON-serializable dictionary."""
    return {
        "seq": ev.seq,
        "ts": ev.ts,
        "kind": ev.kind,
        "payload": ev.payload,
    }


def event_from_dict(d: dict[str, Any]) -> Event:
    """Create an Event from a dictionary."""
    return Event(
        seq=int(d["seq"]),
        ts=int(d["ts"]),
        kind=str(d["kind"]),
        payload=dict(d.get("payload", {})),
    )


def events_to_jsonl(events: list[Event]) -> str:
    """Serialize a list of Events to a newline-delimited JSON string (JSONL)."""
    return "\n".join(json.dumps(event_to_dict(ev), separators=(",", ":")) for ev in events) + (
        "\n" if events else ""
    )


def events_from_jsonl(jsonl_str: str) -> list[Event]:
    """Deserialize a JSONL string to a list of Events."""
    events: list[Event] = []
    for line in jsonl_str.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        events.append(event_from_dict(json.loads(line)))
    return events


def replay(
    events: list[Event],
    tick_size: int = 5,
    lot_size: int = 1,
) -> tuple[OrderBook, list[Trade]]:
    """Rebuild an OrderBook and executed trades by replaying an event log.

    Args:
        events: List of chronological Event objects.
        tick_size: Minimum tick size in paise.
        lot_size: Minimum lot size.

    Returns:
        Tuple of (reconstructed_order_book, list_of_trades).
    """
    engine = MatchingEngine(tick_size=tick_size, lot_size=lot_size)

    for ev in events:
        if ev.kind == "ACCEPTED":
            p = ev.payload
            order = Order(
                id=int(p["order_id"]),
                side=Side(p["side"]),
                type=OrderType(p["type"]),
                price=int(p["price"]) if p.get("price") is not None else None,
                qty=int(p["qty"]),
                remaining=int(p["qty"]),
                ts=ev.ts,
                owner=str(p.get("owner", "replay")),
            )
            engine.submit(order)
        elif ev.kind == "CANCELED":
            # Only cancel if order is still resting in book (user cancel)
            oid = int(ev.payload["order_id"])
            if engine.book.get(oid) is not None:
                engine.cancel(oid)
        elif ev.kind == "MODIFIED":
            oid = int(ev.payload["order_id"])
            new_qty = ev.payload.get("new_qty")
            new_price = ev.payload.get("new_price")
            engine.modify(
                order_id=oid,
                new_qty=int(new_qty) if new_qty is not None else None,
                new_price=int(new_price) if new_price is not None else None,
            )

    return engine.book, engine.trades
