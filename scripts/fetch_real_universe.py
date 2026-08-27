"""Fetch real NSE Top500 + Nifty/Sensex options tokens from Kite instruments (public)."""
import csv, json, requests, pathlib
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "config" / "nse_top500.json"
OPT_OUT = ROOT / "config" / "nifty_sensex_options.json"

def fetch_csv(url):
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.text

print("Fetching NSE EQ...")
nse_text = fetch_csv("https://api.kite.trade/instruments/NSE")
nse_rows = list(csv.DictReader(nse_text.splitlines()))
# Filter EQ NSE
eq = [r for r in nse_rows if r["instrument_type"]=="EQ" and r["segment"]=="NSE" and r["exchange"]=="NSE"]
print(f"NSE EQ total {len(eq)}")
# Sort by tradingsymbol to get deterministic Top500 (or by last_price? use tradingsymbol alphabetical as proxy for liquidity)
# Better: sort by tradingsymbol and take 500 that overlap with known Nifty 500 - for now take 500 most liquid alphabetical? We'll take 500 sorted.
eq_sorted = sorted(eq, key=lambda x: x["tradingsymbol"])
# Try to prioritize Nifty 500 known symbols if available via NSE archive
try:
    nifty_csv = fetch_csv("https://archives.nseindia.com/content/indices/ind_nifty500list.csv")
    nifty_symbols = set()
    for row in csv.DictReader(nifty_csv.splitlines()):
        sym = row.get("Symbol") or row.get("symbol")
        if sym: nifty_symbols.add(sym.strip())
    print(f"Nifty500 list fetched {len(nifty_symbols)}")
    # intersect
    in_nifty = [r for r in eq if r["tradingsymbol"] in nifty_symbols]
    print(f"Intersect EQ+Nifty500 {len(in_nifty)}")
    if len(in_nifty) >= 500:
        selected = sorted(in_nifty, key=lambda x: x["tradingsymbol"])[:500]
    else:
        # fill remainder with EQ sorted
        selected = in_nifty + [r for r in eq_sorted if r not in in_nifty]
        selected = selected[:500]
except Exception as e:
    print(f"Nifty fetch failed {e}, fallback to EQ sorted")
    selected = eq_sorted[:500]

print(f"Selected {len(selected)} for universe")

# Real per-symbol prev_close / avg_volume / sector / industry: NSE's stockIndices API
# returns all Nifty 500 constituents in one response with previousClose,
# totalTradedVolume (source for a real avg_volume — see NOTE below) and a real
# NSE sector/industry classification under meta. This is the same
# session-cookie-warmup pattern already used by options/fetcher_v2.py.
# NOTE: totalTradedVolume here is a single day's volume, not a rolling average;
# for a real N-day average volume, run backend/app/services/history_warmer.py
# against Kite's historical daily candles once credentials + network access
# are available (it patches avg_volume onto the running MarketState directly).
real_data = {}
try:
    import requests
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
    }
    s = requests.Session()
    s.headers.update(headers)
    s.get("https://www.nseindia.com/market-data/live-equity-market", timeout=10)
    r = s.get("https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%20500", timeout=15)
    if r.status_code == 200:
        for row in r.json().get("data", []):
            sym = (row.get("symbol") or "").strip()
            if not sym:
                continue
            real_data[sym] = {
                "prev_close": row.get("previousClose"),
                "day_volume": row.get("totalTradedVolume"),
                "industry": (row.get("meta") or {}).get("industry"),
                "sector": (row.get("meta") or {}).get("sector") or (row.get("meta") or {}).get("industry"),
            }
        print(f"NSE stockIndices: real data fetched for {len(real_data)} symbols")
    else:
        print(f"NSE stockIndices HTTP {r.status_code} — universe will have null prev_close/sector, not fabricated placeholders")
except Exception as e:
    print(f"NSE stockIndices fetch failed ({e}) — universe will have null prev_close/sector, not fabricated placeholders")

universe=[]
missing_real_data = []
for r in selected:
    sym = r["tradingsymbol"]
    real = real_data.get(sym, {})
    if not real:
        missing_real_data.append(sym)
    universe.append({
        "symbol": sym,
        "trading_symbol": sym,
        "company": r["name"] or sym,
        "exchange": "NSE",
        "instrument_token": int(r["instrument_token"]),
        "sector": real.get("sector"),
        "industry": real.get("industry"),
        "prev_close": real.get("prev_close"),
        "avg_volume": real.get("day_volume"),
        "index_membership": ["Nifty 500"]
    })

# Ensure 500
assert len(universe)==500
OUT.write_text(json.dumps(universe, indent=2))
print(f"Wrote {OUT} {len(universe)} entries, sample {universe[0]['symbol']} {universe[0]['instrument_token']}")
if missing_real_data:
    print(f"WARNING: {len(missing_real_data)}/500 symbols have no real prev_close/sector/volume "
          f"(NSE fetch above failed or didn't cover them) — left null rather than fabricated: {missing_real_data[:15]}{'...' if len(missing_real_data)>15 else ''}")

# --- Options: Nifty/Sensex ---
print("Fetching NFO/BFO options...")
# NFO for NIFTY/BANKNIFTY
nfo_text = fetch_csv("https://api.kite.trade/instruments/NFO")
nfo_rows = list(csv.DictReader(nfo_text.splitlines()))
# BFO for SENSEX
bfo_text = fetch_csv("https://api.kite.trade/instruments/BFO")
bfo_rows = list(csv.DictReader(bfo_text.splitlines()))

# Filter NIFTY OPT
def opt_filter(rows, underlying):
    return [r for r in rows if r["name"]==underlying and r["instrument_type"] in ("CE","PE")]

nifty_opts = opt_filter(nfo_rows, "NIFTY") + opt_filter(nfo_rows, "BANKNIFTY")
sensex_opts = opt_filter(bfo_rows, "SENSEX") + opt_filter(nfo_rows, "SENSEX")

# Take nearest 3 expiries, each strike ±10% from spot (spot approx 25000, 80000)
# For token list, just take first 200 per underlying sorted by expiry strike
from datetime import datetime
def sort_opt(rows):
    return sorted(rows, key=lambda x: (x["expiry"] or "", int(float(x["strike"] or 0))))

nifty_sel = sort_opt(nifty_opts)[:400]
sensex_sel = sort_opt(sensex_opts)[:300]

opts_all = []
for r in nifty_sel+sensex_sel:
    opts_all.append({
        "tradingsymbol": r["tradingsymbol"],
        "instrument_token": int(r["instrument_token"]),
        "underlying": r["name"],
        "expiry": r["expiry"],
        "strike": float(r["strike"]) if r["strike"] else 0,
        "type": r["instrument_type"],
        "exchange": r["exchange"],
        "segment": r["segment"]
    })

OPT_OUT.write_text(json.dumps({"NIFTY": [x for x in opts_all if x["underlying"] in ("NIFTY","BANKNIFTY")], "SENSEX": [x for x in opts_all if x["underlying"]=="SENSEX"], "total": len(opts_all)}, indent=2))
print(f"Wrote options {OPT_OUT} total {len(opts_all)} (NIFTY {len([x for x in opts_all if x['underlying'] in ('NIFTY','BANKNIFTY')])} SENSEX {len([x for x in opts_all if x['underlying']=='SENSEX'])})")
print("Done fetch_real_universe")
