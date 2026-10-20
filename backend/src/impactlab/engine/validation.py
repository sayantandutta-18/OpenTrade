"""Validation functions for orders, prices, and quantities."""

from __future__ import annotations

from impactlab.engine.models import Order, OrderType


def validate_order(
    order: Order,
    tick_size: int = 5,
    lot_size: int = 1,
) -> tuple[bool, str | None]:
    """Validate an order against exchange rules (tick size, lot size, positive qty/price).

    Args:
        order: The Order to validate.
        tick_size: Minimum price movement in paise (default: 5 paise = Rs 0.05).
        lot_size: Minimum quantity multiple in shares (default: 1).

    Returns:
        Tuple of (is_valid, error_message).
    """
    if order.qty <= 0:
        return False, f"Quantity must be greater than 0, got {order.qty}"

    if order.remaining <= 0:
        return False, f"Remaining quantity must be greater than 0, got {order.remaining}"

    if order.qty % lot_size != 0:
        return False, f"Quantity {order.qty} must be a multiple of lot size {lot_size}"

    if order.type != OrderType.MARKET:
        if order.price is None or order.price <= 0:
            return False, f"Price must be greater than 0 for {order.type.value} orders"

        if order.price % tick_size != 0:
            return False, f"Price {order.price} must be a multiple of tick size {tick_size}"

    return True, None
