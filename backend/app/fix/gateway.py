"""FIX protocol gateway stub (for institutional order routing)."""
from __future__ import annotations
import time, uuid
from dataclasses import dataclass
from enum import Enum

class FixMsgType(str, Enum): NEW_ORDER="D"; CANCEL="F"; EXEC_REPORT="8"

@dataclass
class FixOrder:
    cl_ord_id: str
    symbol: str
    side: str  # 1=Buy 2=Sell
    qty: int
    price: float | None
    ord_type: str = "2"  # 2=Limit

def encode_fix(order: FixOrder) -> str:
    # Simplified FIX 4.4 encoding (SOH = \x01)
    fields = [f"35={FixMsgType.NEW_ORDER}", f"11={order.cl_ord_id}", f"55={order.symbol}", f"54={order.side}", f"38={order.qty}"]
    if order.price: fields.append(f"44={order.price}")
    fields += [f"40={order.ord_type}", f"52={time.strftime('%Y%m%d-%H:%M:%S')}"]
    raw = "\x01".join(fields) + "\x01"
    return raw

def new_order(symbol: str, side: str, qty: int, price: float|None=None) -> FixOrder:
    return FixOrder(str(uuid.uuid4())[:8], symbol, "1" if side.lower()=="buy" else "2", qty, price)

# TODO: integrate quickfix/j via python quickfix or FIXT 1.1 for live brokerage
