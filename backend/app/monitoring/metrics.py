"""Health metrics: tick latency p50/p95/p99, WS health, memory per symbol, alert rate."""
from __future__ import annotations
import time, os
try: import psutil
except: psutil=None
from typing import Dict, List
from collections import deque

_latencies: deque = deque(maxlen=2000)
_ws_clients: Dict[str,float] = {}
_alert_ok=0; _alert_fail=0
_sym_mem: Dict[str,int] = {}

def record_tick_latency(ms: float): _latencies.append(ms)
def record_ws_heartbeat(client_id: str): _ws_clients[client_id]=time.time()
def remove_ws_client(client_id: str): _ws_clients.pop(client_id,None)
def record_alert(success: bool):
    global _alert_ok,_alert_fail
    if success: _alert_ok+=1
    else: _alert_fail+=1
def set_symbol_mem(symbol:str, items:int): _sym_mem[symbol]=items

def _percentile(data: List[float], p: float)->float:
    if not data: return 0.0
    s=sorted(data); k=(len(s)-1)*p/100; f=int(k); c=min(f+1,len(s)-1)
    if f==c: return s[f]
    d=k-f; return s[f]*(1-d)+s[c]*d

def get_metrics()->dict:
    lat=list(_latencies)
    now=time.time()
    ws_health={cid: round(now-ts,1) for cid,ts in _ws_clients.items()}
    stale_ws=sum(1 for v in ws_health.values() if v>30)
    total_alert=_alert_ok+_alert_fail
    try: mem_mb=psutil.Process(os.getpid()).memory_info().rss/1024/1024 if psutil else 0
    except: mem_mb=0
    return {
        "tick_latency_ms": {"p50":round(_percentile(lat,50),2),"p95":round(_percentile(lat,95),2),"p99":round(_percentile(lat,99),2),"count":len(lat)},
        "ws": {"clients":len(_ws_clients),"stale":stale_ws,"health": ws_health},
        "memory": {"process_mb":round(mem_mb,1),"per_symbol": dict(list(_sym_mem.items())[:50])},
        "alerts": {"ok":_alert_ok,"fail":_alert_fail,"success_rate": round(_alert_ok/total_alert,3) if total_alert else 1.0},
        "uptime_sec": round(time.time()- _start,1)
    }

_start=time.time()
