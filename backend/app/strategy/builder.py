"""No-code strategy builder: If RSI<30 AND price>VWAP then alert (stub)."""
from __future__ import annotations
from typing import Any

OPS = {"<": lambda a,b: a<b, ">": lambda a,b: a>b, "<=": lambda a,b: a<=b, ">=": lambda a,b: a>=b, "==": lambda a,b: a==b}

def eval_condition(cond: dict[str, Any], state) -> bool:
    # cond: {field: "rsi"|"price"|"vwap"|"volume", op: "<", value: 30}
    field, op, val = cond.get("field"), cond.get("op"), cond.get("value")
    ops_fn = OPS.get(op)
    if not ops_fn: return False
    actual = None
    if field=="rsi": actual = state.indicators.rsi
    elif field=="price": actual = state.ltp
    elif field=="vwap": actual = state.indicators.vwap
    elif field=="volume": actual = state.volume
    elif field=="relVolume": actual = state.rel_volume
    if actual is None: return False
    try: return bool(ops_fn(float(actual), float(val)))
    except: return False

def evaluate(strategy: dict, state) -> bool:
    """strategy: {logic: AND/OR, conditions: [...]} returns should_alert."""
    logic = strategy.get("logic","AND").upper()
    conds = strategy.get("conditions", [])
    results = [eval_condition(c, state) for c in conds]
    if not results: return False
    return all(results) if logic=="AND" else any(results)

EXAMPLE = {"logic":"AND","conditions":[{"field":"rsi","op":"<","value":30},{"field":"price","op":">","value":"vwap"}]}
# Note: for price>VWAP compare dynamically in caller; stub uses literal
