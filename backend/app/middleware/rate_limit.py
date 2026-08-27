"""In-memory rate limiter 100 req/min per IP."""
from __future__ import annotations
import time
from collections import defaultdict, deque
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

WINDOW=60; LIMIT=100
_hits: dict[str, deque] = defaultdict(deque)

def is_allowed(ip: str)->bool:
    now=time.time(); q=_hits[ip]
    while q and now-q[0] > WINDOW: q.popleft()
    if len(q) >= LIMIT: return False
    q.append(now); return True

class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        ip=request.client.host if request.client else "unknown"
        # skip health
        if request.url.path in ("/api/health","/metrics","/docs","/openapi.json"):
            return await call_next(request)
        if not is_allowed(ip):
            raise HTTPException(status_code=429, detail="Rate limit exceeded 100/min")
        return await call_next(request)

# compat limiter object for main.py
class _Limiter:
    def limit(self, spec): 
        def dec(fn): return fn
        return dec
limiter=_Limiter()
def get_rate_limit_handler(): 
    from fastapi.responses import JSONResponse
    async def h(req, exc): return JSONResponse(status_code=429, content={"detail":"rate limit"})
    return h
