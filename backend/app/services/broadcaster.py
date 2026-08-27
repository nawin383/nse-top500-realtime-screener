"""WebSocket broadcaster for frontend clients.

Backend maintains single market data connection (via DataEngine)
and distributes normalized minimal JSON to multiple frontend clients efficiently.
"""
from __future__ import annotations
import asyncio
import json
import logging
from typing import Set, Dict, Any, List
from fastapi import WebSocket

logger = logging.getLogger(__name__)

class Broadcaster:
    def __init__(self):
        self._clients: Set[WebSocket] = set()
        self._lock = asyncio.Lock()
        self._broadcast_queue: asyncio.Queue = asyncio.Queue()

    async def register(self, ws: WebSocket):
        await ws.accept()
        async with self._lock:
            self._clients.add(ws)
        logger.info(f"Frontend client connected total={len(self._clients)}")

    async def unregister(self, ws: WebSocket):
        async with self._lock:
            self._clients.discard(ws)
        logger.info(f"Frontend client disconnected total={len(self._clients)}")

    async def broadcast(self, payload: Dict[str,Any]):
        # payload will be json dumped with minimal size
        if not self._clients:
            return
        # create message once
        msg = json.dumps(payload, default=str, separators=(",",":"))
        async with self._lock:
            clients = list(self._clients)
        # gather sends with return_exceptions
        coros = []
        for c in clients:
            coros.append(self._send_safe(c, msg))
        if coros:
            await asyncio.gather(*coros, return_exceptions=True)

    async def _send_safe(self, ws: WebSocket, msg: str):
        try:
            await ws.send_text(msg)
        except Exception as e:
            logger.debug(f"broadcast send failed {e}")
            async with self._lock:
                self._clients.discard(ws)

    async def send_to(self, ws: WebSocket, payload: Dict[str,Any]):
        msg = json.dumps(payload, default=str, separators=(",",":"))
        await ws.send_text(msg)

broadcaster = Broadcaster()
