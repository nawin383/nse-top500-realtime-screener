"""Multi-market stub: BSE / MCX / Crypto (enable via config)."""
from __future__ import annotations
from enum import Enum
from dataclasses import dataclass

class Market(str, Enum): NSE="NSE"; BSE="BSE"; MCX="MCX"; CRYPTO="CRYPTO"

@dataclass
class MarketConfig: enabled: bool = False; ws_url: str = ""; universe: str = ""

MARKETS = {
    Market.NSE: MarketConfig(True, "wss://ws.kite.trade/", "config/nse_top500.json"),
    Market.BSE: MarketConfig(False, "wss://ws.kite.trade/", "config/bse_top100.json"),
    Market.MCX: MarketConfig(False, "", "config/mcx.json"),
    Market.CRYPTO: MarketConfig(False, "wss://stream.binance.com:9443/ws", "config/crypto.json"),
}

def active_markets() -> list[Market]:
    return [m for m,c in MARKETS.items() if c.enabled]

def set_market(market: Market, enabled: bool, ws_url: str|None=None):
    cfg = MARKETS.get(market)
    if cfg:
        cfg.enabled = enabled
        if ws_url: cfg.ws_url = ws_url
    return cfg
