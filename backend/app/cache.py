"""Caching layer: Redis with in-memory fallback + TTL.
Covers screener (5s), overview (10s), indicators."""
from __future__ import annotations
import time
import json
import hashlib
from typing import Any, Optional

try:
    import redis  # type: ignore
    _has_redis = True
except: _has_redis = False

class Cache:
    def __init__(self, url: str = ""):
        self._mem: dict[str, tuple[float, Any]] = {}
        self._r = None
        if _has_redis and url:
            try: self._r = redis.from_url(url, socket_connect_timeout=1, decode_responses=True)
            except: self._r = None
        self._h = {"hits":0,"miss":0}

    def _key(self, ns: str, params: dict) -> str:
        raw = json.dumps(params, sort_keys=True, default=str)
        return f"nse:{ns}:{hashlib.md5(raw.encode()).hexdigest()[:12]}"

    def get(self, ns: str, params: dict) -> Optional[Any]:
        k = self._key(ns, params)
        if self._r:
            try:
                v = self._r.get(k)
                if v: self._h["hits"]+=1; return json.loads(v)
            except: pass
        if k in self._mem:
            exp, val = self._mem[k]
            if time.time() < exp: self._h["hits"]+=1; return val
            else: del self._mem[k]
        self._h["miss"]+=1; return None

    def set(self, ns: str, params: dict, value: Any, ttl: int):
        k = self._key(ns, params)
        if self._r:
            try: self._r.setex(k, ttl, json.dumps(value, default=str)); return
            except: pass
        self._mem[k] = (time.time()+ttl, value)

    def stats(self): return self._h

cache = Cache(url="")
# factory for tests
def get_cache(): return cache
