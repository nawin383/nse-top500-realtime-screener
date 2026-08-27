"""5y historical tick store - file-based Parquet-like JSON, with HV cone, IV percentile, earnings IV crush."""
from __future__ import annotations
import json
import math
import statistics
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional

try:
    from zoneinfo import ZoneInfo
    IST = ZoneInfo("Asia/Kolkata")
except ImportError:
    import pytz
    IST = pytz.timezone("Asia/Kolkata")

HIST_DIR = Path(__file__).resolve().parents[2] / "data" / "historical"
HIST_DIR.mkdir(parents=True, exist_ok=True)

def _hist_path(symbol: str) -> Path:
    return HIST_DIR / f"{symbol.upper()}_1d.json"

def ingest_bhavcopy_row(symbol: str, date: str, open: float, high: float, low: float, close: float, volume: int):
    """Ingest one bhavcopy row into 1d store."""
    p = _hist_path(symbol)
    data = []
    if p.exists():
        try:
            data = json.loads(p.read_text())
        except:
            data = []
    # deduplicate by date
    data = [d for d in data if d["date"] != date]
    data.append({"date": date, "open": open, "high": high, "low": low, "close": close, "volume": volume})
    data.sort(key=lambda x: x["date"])
    # keep 5y (~1260 trading days)
    if len(data) > 1260:
        data = data[-1260:]
    p.write_text(json.dumps(data))

def ingest_nse_bhavcopy(date: str = None):
    """Fetch NSE bhavcopy for date (YYYY-MM-DD) and ingest. If date None, today."""
    import requests
    if not date:
        date = datetime.now(tz=IST).strftime("%Y-%m-%d")
    # NSE bhavcopy URL: https://www.nseindia.com/api/historical/equities?symbol=NIFTY&series=[%22EQ%22]&from=...
    # Simplified: try to fetch from NSE's archives
    # For institutional grade, we would use NSE's CM bhavcopy: https://archives.nseindia.com/content/historical/EQUITIES/2024/...
    # Here we try a simple fetch and fallback to synthetic if not available
    dt = datetime.strptime(date, "%Y-%m-%d")
    url = f"https://archives.nseindia.com/content/historical/EQUITIES/{dt.strftime('%Y')}/{dt.strftime('%b').upper()}/cm{dt.strftime('%d%b%Y').upper()}bhav.csv"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200 and "SYMBOL" in r.text:
            lines = r.text.splitlines()
            header = lines[0].split(",")
            for line in lines[1:]:
                parts = line.split(",")
                if len(parts) < 10:
                    continue
                try:
                    rec = dict(zip(header, parts))
                    if rec.get("SERIES") != "EQ":
                        continue
                    sym = rec["SYMBOL"].strip()
                    # only ingest for universe symbols (check file exists or top 500)
                    # For now ingest all
                    ingest_bhavcopy_row(sym, date, float(rec["OPEN"]), float(rec["HIGH"]), float(rec["LOW"]), float(rec["CLOSE"]), int(rec["TOTTRDQTY"]))
                except:
                    continue
            return True
    except Exception as e:
        print(f"bhavcopy ingest failed {date}: {e}")
    return False

def get_history(symbol: str, days: int = 365) -> List[Dict]:
    p = _hist_path(symbol)
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text())
        return data[-days:]
    except:
        return []

def hv_cone(symbol: str, current_iv: Optional[float] = None) -> Dict[str, Any]:
    """Historical volatility cone 1M/3M/6M/1Y (from real ingested daily closes,
    see ingest_nse_bhavcopy) + where the option chain's real current ATM IV
    (pass current_iv from the caller's live chain fetch) sits within it."""
    hist = get_history(symbol, 365)
    if len(hist) < 30:
        return {"currentIv": current_iv, "cone": None, "position": None, "hv": None,
                "note": f"Only {len(hist)} days of ingested history for {symbol} — need 30+. Run /historical/bhavcopy to ingest more."}
    closes = [d["close"] for d in hist]
    def hv(window: int):
        if len(closes) < window+1:
            return None
        rets = [math.log(closes[i]/closes[i-1]) for i in range(1, len(closes))][-window:]
        return round(statistics.stdev(rets) * math.sqrt(252) * 100, 2)
    def band(window: int):
        h = hv(window)
        return [round(h*0.7, 2), round(h*1.3, 2)] if h else None
    cone = {"1M": band(21), "3M": band(63), "6M": band(126), "1Y": band(252)}
    hv_30 = hv(30)
    position = None
    if current_iv and cone["1M"]:
        if current_iv < cone["1M"][0]:
            position = "low"
        elif current_iv > cone["1M"][1]:
            position = "high"
        else:
            position = "mid"
    return {"currentIv": current_iv, "hv30": hv_30, "cone": cone, "position": position, "hv": hv_30}

def iv_percentile(symbol: str, current_iv: float) -> Dict[str, Any]:
    """IV rank/percentile 1Y/6M/3M. Needs 1y IV history; we approximate from HV history."""
    hist = get_history(symbol, 252)
    if len(hist) < 50:
        return {"ivRank1Y": None, "ivPercentile1Y": None, "ivRank6M": None, "ivRank3M": None}
    # Approximate IV history as HV * 1.1 with noise
    iv_hist = []
    closes = [d["close"] for d in hist]
    for i in range(30, len(closes)):
        window = closes[i-30:i]
        rets = [math.log(window[j]/window[j-1]) for j in range(1, len(window))]
        hv = statistics.stdev(rets) * math.sqrt(252) * 100 if len(rets) > 1 else 16
        iv_hist.append(hv * 1.1)
    if not iv_hist:
        return {"ivRank1Y": None, "ivPercentile1Y": None}
    # percentile
    sorted_hist = sorted(iv_hist)
    rank = sum(1 for v in sorted_hist if v <= current_iv) / len(sorted_hist) * 100
    # 1Y, 6M, 3M slices
    def percentile(slice_days):
        sl = iv_hist[-slice_days:] if len(iv_hist) >= slice_days else iv_hist
        s = sorted(sl)
        return round(sum(1 for v in s if v <= current_iv) / len(s) * 100,1) if s else None
    return {
        "ivRank1Y": round(rank,1),
        "ivPercentile1Y": round(rank,1),
        "ivRank6M": percentile(126),
        "ivRank3M": percentile(63),
        "ivHistory": iv_hist[-30:],
    }

def earnings_iv_crush(symbol: str) -> Dict[str, Any]:
    return {"nextEarnings": None, "historicalCrush": None, "expectedMove": None,
            "note": "Earnings calendar/IV-crush history requires a corporate-announcements feed that isn't wired up yet."}
