"""Structured logger with correlation IDs, loguru fallback."""
from __future__ import annotations
import logging, uuid, contextvars
from typing import Optional

_corr = contextvars.ContextVar("correlation_id", default="")

try:
    from loguru import logger as _loguru
    _has_loguru=True
except: _has_loguru=False; _loguru=None

_base = logging.getLogger("nse")
if not _base.handlers:
    h=logging.StreamHandler()
    h.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    _base.addHandler(h)
    _base.setLevel(logging.INFO)

def set_correlation_id(cid: Optional[str]=None)->str:
    cid=cid or uuid.uuid4().hex[:8]
    _corr.set(cid)
    return cid

def get_correlation_id()->str: return _corr.get()

class StructuredLogger:
    def __init__(self, name:str="app"): self.name=name; self.log=logging.getLogger(name)
    def _msg(self, m): 
        cid=get_correlation_id()
        return f"[{cid}] {m}" if cid else m
    def info(self,m,*a,**kw): ( _loguru.info(self._msg(m)) if _has_loguru else self.log.info(self._msg(m),*a,**kw))
    def warning(self,m,*a,**kw): ( _loguru.warning(self._msg(m)) if _has_loguru else self.log.warning(self._msg(m),*a,**kw))
    def error(self,m,*a,**kw): ( _loguru.error(self._msg(m)) if _has_loguru else self.log.error(self._msg(m),*a,**kw))
    def debug(self,m,*a,**kw): ( _loguru.debug(self._msg(m)) if _has_loguru else self.log.debug(self._msg(m),*a,**kw))

logger = StructuredLogger("nse")
__all__=["logger","StructuredLogger","set_correlation_id","get_correlation_id"]
