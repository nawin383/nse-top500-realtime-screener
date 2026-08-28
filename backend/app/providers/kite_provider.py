"""Live Kite WebSocket provider - wraps websocket-client logic in async manner.

Uses kite_websocket library from original project pattern but isolated.
Supports reconnection, heartbeat, subscription management, duplicate handling, rate limit protection.
"""
from __future__ import annotations
import asyncio
import json
import logging
import struct
import time
from datetime import datetime
from typing import List, Dict, Any, Callable
import threading

try:
    from zoneinfo import ZoneInfo
    IST = ZoneInfo("Asia/Kolkata")
except ImportError:
    import pytz
    IST = pytz.timezone("Asia/Kolkata")

from .base import BaseProvider
from ..models import MarketTick

logger = logging.getLogger(__name__)

# Preserve proven WebSocket pattern from original repo: binary parsing + reconnect
# We reuse logic but run inside asyncio via thread

class KiteProvider(BaseProvider):
    ROOT_URI = "wss://ws.kite.trade/"

    def __init__(self, universe: List[Dict[str, Any]], api_key: str, access_token: str, websocket_url: str = None):
        super().__init__(universe)
        self.api_key = api_key
        self.access_token = access_token
        self.websocket_url = websocket_url or self.ROOT_URI
        self._on_ticks: Callable = None
        self._stop = False
        self._thread = None
        self._loop = None
        # token -> symbol
        self._token_to_symbol = {u["instrument_token"]: u["symbol"] for u in universe}
        self._symbol_to_token = {u["symbol"]: u["instrument_token"] for u in universe}
        # Load Nifty/Sensex options (up to 300 nearest expiry to stay <1000 total with 500 equities)
        self._options_tokens=[]
        try:
            from pathlib import Path
            import json
            # parents[3] is the repo root (this file is backend/app/providers/kite_provider.py);
            # parents[2] ("backend/") was a real bug -- config/ lives at the repo root, not
            # under backend/, so this silently never found the file and self._options_tokens
            # stayed empty, meaning the WS never actually subscribed to any option contracts.
            opt_path = Path(__file__).resolve().parents[3] / "config" / "nifty_sensex_options.json"
            if opt_path.exists():
                data=json.loads(opt_path.read_text())
                # take nearest expiry: sort by expiry, take 150 NIFTY + 150 SENSEX = 300
                nifty = sorted(data.get("NIFTY",[]), key=lambda x: (x["expiry"] or "", x["strike"]))[:200]
                sensex = sorted(data.get("SENSEX",[]), key=lambda x: (x["expiry"] or "", x["strike"]))[:150]
                for r in nifty+sensex:
                    token=r["instrument_token"]; sym=r["tradingsymbol"]
                    if token not in self._token_to_symbol:
                        self._token_to_symbol[token]=sym
                        self._symbol_to_token[sym]=token
                        self._options_tokens.append(token)
                logger.info(f"Options loaded {len(self._options_tokens)} (NIFTY {len(nifty)} + SENSEX {len(sensex)})")
        except Exception as e:
            logger.warning(f"Options load failed {e}")
        self._mode_map = {}
        self._ticks_processed = 0
        self._subscribed = set()

    @property
    def name(self) -> str:
        return "kite_live"

    async def start(self, on_ticks):
        self._on_ticks = on_ticks
        self._stop = False
        # captured here because we're genuinely inside the running loop; _on_message
        # runs on the websocket-client background thread, which has no event loop of
        # its own, so asyncio.get_event_loop() there raises "no current event loop"
        # (fatal in 3.10+) and every tick was silently dropped by the outer try/except.
        self._loop = asyncio.get_running_loop()
        # run websocket-client in thread (original pattern)
        self._thread = threading.Thread(target=self._run_blocking, daemon=True)
        self._thread.start()
        logger.info(f"KiteProvider start thread, universe {len(self.universe)} tokens")
        # keep async task alive
        while not self._stop:
            await asyncio.sleep(1)

    async def stop(self):
        self._stop = True
        logger.info("KiteProvider stopping")

    def _run_blocking(self):
        try:
            import websocket
        except ImportError:
            logger.error("websocket-client not installed")
            return
        # minimal reconnect loop preserving original logic
        reconnect_tries = 0
        max_tries = 30
        max_delay = 60
        while not self._stop and reconnect_tries <= max_tries:
            try:
                url = f"{self.websocket_url}?api_key={self.api_key}&access_token={self.access_token}"
                logger.info(f"Connecting to Kite WS {self.websocket_url}")
                ws = websocket.WebSocketApp(
                    url,
                    on_open=self._on_open,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close,
                    on_ping=lambda ws,msg: logger.debug("ping"),
                    on_pong=lambda ws,msg: logger.debug("pong"),
                )
                self._ws = ws
                ws.run_forever(ping_interval=3, ping_timeout=2)
                if self._stop:
                    break
                # reconnect
                reconnect_tries += 1
                delay = min(2**reconnect_tries, max_delay)
                logger.warning(f"Reconnect attempt {reconnect_tries} in {delay}s")
                time.sleep(delay)
            except Exception as e:
                logger.error(f"KiteProvider loop error {e}", exc_info=True)
                reconnect_tries += 1
                delay = min(2**reconnect_tries, max_delay)
                time.sleep(delay)

    def _on_open(self, ws):
        logger.info("Kite WS connected")
        # Mode split per Kite Connect best practice (websocket/#modes): equities use
        # "quote" (44 bytes/tick: last price, volume, and OHLC) while NIFTY/SENSEX
        # options use "full" (184 bytes/tick) for OI and best bid/ask depth. Still a
        # big bandwidth win over subscribing everything as "full" (~4x vs ~23x), but
        # unlike "ltp" mode (8 bytes, last price only) it actually carries OHLC —
        # ltp mode has no previous-close field, so change%/score would be stuck
        # against the flat placeholder previous_close forever, never self-correcting
        # from a live tick the way "quote" mode's ohlc.close does.
        equity_tokens = [u["instrument_token"] for u in self.universe]
        option_tokens = list(self._options_tokens)
        self._subscribe_batch(ws, equity_tokens, "quote")
        self._subscribe_batch(ws, option_tokens, "full")
        logger.info(f"Subscribed {len(self._subscribed)}/{len(equity_tokens)+len(option_tokens)} instruments "
                    f"(EQ {len(equity_tokens)} mode=quote + OPT {len(option_tokens)} mode=full)")

    def _subscribe_batch(self, ws, tokens: List[int], mode: str):
        for i in range(0, len(tokens), 200):
            chunk = tokens[i:i+200]
            if not chunk:
                continue
            try:
                ws.send(json.dumps({"a":"subscribe","v":chunk}))
                self._subscribed.update(chunk)
                for t in chunk:
                    self._mode_map[t] = mode
                ws.send(json.dumps({"a":"mode","v":[mode, chunk]}))
                logger.info(f"Subscribed {len(chunk)} tokens mode={mode} (batch {i//200+1})")
                time.sleep(0.2)
            except Exception as e:
                logger.error(f"subscribe failed mode={mode} {e}")

    def _on_message(self, ws, message):
        try:
            if isinstance(message, bytes):
                ticks = self._parse_binary(message)
                if ticks and self._on_ticks:
                    # normalize to MarketTick
                    normalized = []
                    for t in ticks:
                        try:
                            nt = self._normalize_tick(t)
                            if nt:
                                normalized.append(nt)
                        except Exception as e:
                            logger.error(f"normalize tick error {e}")
                    if normalized and self._loop:
                        asyncio.run_coroutine_threadsafe(self._dispatch(normalized), self._loop)
                    elif normalized:
                        logger.error("no event loop captured yet, dropping tick batch")
                    self._ticks_processed += len(ticks)
            elif isinstance(message, str):
                data = json.loads(message)
                logger.debug(f"Text message {data}")
        except Exception as e:
            logger.error(f"on_message error {e}", exc_info=True)

    async def _dispatch(self, ticks: List[MarketTick]):
        if self._on_ticks:
            # if on_ticks is async, await; else call
            res = self._on_ticks(ticks)
            if asyncio.iscoroutine(res):
                await res

    def _on_close(self, ws, code, reason):
        logger.warning(f"Kite WS close {code} {reason}")

    def _on_error(self, ws, error):
        logger.error(f"Kite WS error {error}")

    def _parse_binary(self, data: bytes):
        """Kite WS binary framing (websocket/#message-structure): 2 bytes packet count,
        then per packet: 2 bytes packet length + that many bytes of payload (payload
        starts with a 4-byte instrument token). The packet's own declared length tells
        us unambiguously whether it's LTP (8B) / quote (44B) / full (184B) — trusting
        that length instead of the subscribed mode also keeps parsing correct if Kite
        ever sends a smaller packet than requested (e.g. right after a mode change)."""
        ticks=[]
        try:
            if len(data) < 2:
                return ticks
            count = struct.unpack(">H", data[:2])[0]
            offset = 2
            for _ in range(count):
                if offset + 2 > len(data):
                    break
                packet_len = struct.unpack(">H", data[offset:offset+2])[0]
                offset += 2
                if offset + packet_len > len(data):
                    logger.warning(f"truncated tick packet: declared {packet_len}B, {len(data)-offset}B left")
                    break
                packet = data[offset:offset+packet_len]
                offset += packet_len
                tick = self._parse_packet(packet)
                if tick:
                    ticks.append(tick)
        except Exception as e:
            logger.error(f"binary parse error {e}", exc_info=True)
        return ticks

    def _parse_packet(self, packet: bytes):
        if len(packet) < 4:
            return None
        instrument_token = struct.unpack(">I", packet[0:4])[0]
        plen = len(packet)
        tick = {"instrument_token": instrument_token}
        if plen == 8:
            tick["mode"] = "ltp"
            tick["last_price"] = struct.unpack(">I", packet[4:8])[0] / 100.0
        elif plen in (28, 32):
            # index packet (NIFTY 50 / SENSEX spot) — not currently subscribed by this
            # provider (only equities + NIFTY/SENSEX options are), kept as a safe no-op
            # rather than mis-parsed as an equity packet.
            return None
        elif plen in (44, 184):
            tick["mode"] = "quote" if plen == 44 else "full"
            tick["last_price"] = struct.unpack(">I", packet[4:8])[0] / 100.0
            tick["last_quantity"] = struct.unpack(">I", packet[8:12])[0]
            tick["average_price"] = struct.unpack(">I", packet[12:16])[0] / 100.0
            tick["volume"] = struct.unpack(">I", packet[16:20])[0]
            tick["buy_quantity"] = struct.unpack(">I", packet[20:24])[0]
            tick["sell_quantity"] = struct.unpack(">I", packet[24:28])[0]
            tick["ohlc"] = {
                "open": struct.unpack(">I", packet[28:32])[0] / 100.0,
                "high": struct.unpack(">I", packet[32:36])[0] / 100.0,
                "low": struct.unpack(">I", packet[36:40])[0] / 100.0,
                "close": struct.unpack(">I", packet[40:44])[0] / 100.0,
            }
            if plen == 184:
                tick["change"] = struct.unpack(">I", packet[44:48])[0] / 100.0
                timestamp = struct.unpack(">I", packet[48:52])[0]
                tick["timestamp"] = datetime.fromtimestamp(timestamp, tz=IST)
                tick["oi"] = struct.unpack(">I", packet[52:56])[0]
                tick["oi_day_high"] = struct.unpack(">I", packet[56:60])[0]
                tick["oi_day_low"] = struct.unpack(">I", packet[60:64])[0]
                tick["depth"] = self._parse_depth(packet[64:184])
        else:
            logger.debug(f"unexpected tick packet length {plen} for token {instrument_token}")
            return None
        return tick

    def _parse_depth(self, buf: bytes) -> Dict[str, List[Dict[str, Any]]]:
        """Market depth (websocket/#market-depth-structure): 10 entries x 12 bytes
        (qty int32, price int32, orders int16 + 2 pad), first 5 = buy, last 5 = sell."""
        entries = []
        for i in range(10):
            chunk = buf[i*12:(i+1)*12]
            if len(chunk) < 12:
                break
            qty = struct.unpack(">I", chunk[0:4])[0]
            price = struct.unpack(">I", chunk[4:8])[0] / 100.0
            orders = struct.unpack(">H", chunk[8:10])[0]
            entries.append({"quantity": qty, "price": price, "orders": orders})
        return {"buy": entries[:5], "sell": entries[5:10]}

    def _normalize_tick(self, raw: Dict[str,Any]) -> MarketTick:
        token = raw.get("instrument_token")
        sym = self._token_to_symbol.get(token)
        if not sym:
            logger.warning(f"Unknown token {token}")
            return None
        # create normalized MarketTick
        ts = raw.get("timestamp") or datetime.now(tz=IST)
        ohlc = raw.get("ohlc", {})
        depth = raw.get("depth", {})
        bid = ask = bid_qty = ask_qty = None
        if depth and depth.get("buy"):
            bid = depth["buy"][0].get("price")
            bid_qty = depth["buy"][0].get("quantity")
        if depth and depth.get("sell"):
            ask = depth["sell"][0].get("price")
            ask_qty = depth["sell"][0].get("quantity")
        mt = MarketTick(
            symbol=sym,
            token=token,
            timestamp=ts,
            ltp=raw.get("last_price") or raw.get("ltp") or 0,
            last_quantity=raw.get("last_quantity",0),
            open=ohlc.get("open"),
            high=ohlc.get("high"),
            low=ohlc.get("low"),
            previousClose=ohlc.get("close"),
            volume=raw.get("volume",0),
            bid=bid,
            ask=ask,
            bid_qty=bid_qty,
            ask_qty=ask_qty,
            oi=raw.get("oi"),
        )
        return mt
