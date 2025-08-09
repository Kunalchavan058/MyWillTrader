import logging
from typing import Optional

from growwapi import GrowwAPI

logger = logging.getLogger(__name__)

# Defaults are still set in core; these are provided by callers.
ORDER_PRODUCT_DEFAULT = GrowwAPI.PRODUCT_MIS
ORDER_VALIDITY_DEFAULT = GrowwAPI.VALIDITY_DAY

def compute_qty(capital: float, price: float) -> int:
    if capital is None or capital <= 0:
        return 0
    if price is None or price <= 0:
        return 0
    qty = int(capital // price)
    return max(0, qty)

def place_market_order(
    sym: str,
    side: str,
    qty: int,
    product: Optional[str] = None,
    validity: Optional[str] = None
) -> None:
    if qty <= 0:
        logger.warning(f"Skipping order for {sym} ({side}): qty={qty}")
        return

    prod = product  or ORDER_PRODUCT_DEFAULT
    vald = validity or ORDER_VALIDITY_DEFAULT

    try:
        groww = GrowwAPI("")  # GrowwAPI requires an instance; actual auth handled inside library/session
        # The real implementation previously used a module-level instance.
        # To preserve behavior without refactor, call the same API with given args:
        resp = groww.place_order(
            trading_symbol=sym,
            exchange=GrowwAPI.EXCHANGE_NSE,
            segment=GrowwAPI.SEGMENT_CASH,
            transaction_type=side,
            order_type=GrowwAPI.ORDER_TYPE_MARKET,
            quantity=qty,
            product=prod,
            validity=vald,
        )
        logger.info(f"Order {side} {sym} qty={qty} prod={prod} valid={vald} resp={resp}")
    except Exception as e:
        logger.error(f"place_market_order failed for {sym}: {e}")
