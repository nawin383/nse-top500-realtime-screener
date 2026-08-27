"""Social trading: share screener configs (stub)."""
from __future__ import annotations
import hashlib, json, time
from typing import Any

SHARES: dict[str, dict] = {}

def share_screener(name: str, params: dict[str, Any], user: str = "anon") -> dict:
    key = json.dumps({"name": name, "params": params}, sort_keys=True)
    sid = hashlib.sha256(key.encode()).hexdigest()[:10]
    SHARES[sid] = {"id": sid, "name": name, "params": params, "user": user, "created": int(time.time()), "views": 0, "url": f"/s/{sid}"}
    return SHARES[sid]

def get_share(sid: str) -> dict | None:
    s = SHARES.get(sid)
    if s: s["views"] += 1
    return s

def list_trending(limit: int = 10) -> list[dict]:
    return sorted(SHARES.values(), key=lambda x: x["views"], reverse=True)[:limit]
