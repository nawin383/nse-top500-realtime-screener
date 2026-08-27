"""Multi-provider adapter with failover, outlier reject >10%, gap handling."""
from __future__ import annotations
import logging, asyncio
from typing import List, Dict, Any, Callable
from ..models import MarketTick
from .base import BaseProvider
try: from .kite_provider import KiteProvider
except: KiteProvider=None
try: from .mock_provider import MockProvider
except: MockProvider=None

logger=logging.getLogger(__name__)

def _valid_tick(prev: Dict[str,float], tick: MarketTick)->bool:
    if prev and prev.get(tick.symbol):
        last=prev[tick.symbol]
        if last and tick.ltp:
            move=abs(tick.ltp-last)/last
            if move>0.10:  # >10% reject
                logger.warning(f"outlier reject {tick.symbol} {last}->{tick.ltp}")
                return False
    return True

class MultiProvider(BaseProvider):
    def __init__(self, universe: List[Dict[str,Any]], providers: List[str]=None):
        super().__init__(universe)
        self.universe=universe
        self.order=providers or ["kite","mock"]
        self._providers: List[BaseProvider]=[]
        for name in self.order:
            if name=="kite" and KiteProvider: 
                try: self._providers.append(KiteProvider(universe))
                except: pass
            elif name=="mock" and MockProvider:
                try: self._providers.append(MockProvider(universe))
                except: pass
        if not self._providers and MockProvider:
            self._providers=[MockProvider(universe)]
        self._active=None; self._last: Dict[str,float]={}; self._running=False

    @property
    def name(self)->str: return "multi:"+"+".join(self.order)

    async def start(self, on_ticks: Callable):
        self._running=True
        async def wrapped(ticks: List[MarketTick]):
            valid=[t for t in ticks if _valid_tick(self._last,t)]
            for t in valid: self._last[t.symbol]=t.ltp
            # gap handling: detect missing symbols vs universe
            if len(valid)< len(self.universe)*0.5:
                logger.debug("gap detected partial batch")
            await on_ticks(valid) if asyncio.iscoroutinefunction(on_ticks) else on_ticks(valid)
        for p in self._providers:
            try:
                await p.start(wrapped); self._active=p; logger.info(f"multi active {p.name}"); return
            except Exception as e:
                logger.warning(f"provider {p.name} failed {e}, failover")
                continue
        raise RuntimeError("no provider available")

    async def stop(self):
        self._running=False
        for p in self._providers:
            try: await p.stop()
            except: pass
