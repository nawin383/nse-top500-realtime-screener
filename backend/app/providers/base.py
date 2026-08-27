"""Abstract provider interface."""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Callable, List, Dict, Any
from ..models import MarketTick

TickCallback = Callable[[List[MarketTick]], None]

class BaseProvider(ABC):
    def __init__(self, universe: List[Dict[str, Any]]):
        self.universe = universe

    @abstractmethod
    async def start(self, on_ticks: TickCallback):
        pass

    @abstractmethod
    async def stop(self):
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass
