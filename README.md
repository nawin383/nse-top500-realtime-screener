# NSE Top 500 Real-Time Intraday Market Screener

Production-quality real-time intraday screener for **NSE Top 500** stocks streaming via **Kite WebSocket** (Kit WebSocket / Zerodha Kite Connect API) with mock & replay modes for development outside market hours.

**Original base:** [nawin383/socket](https://github.com/nawin383/socket) — Python Kite WebSocket client (binary tick parsing, auto-reconnect, relay server). This project preserves its proven WebSocket patterns and expands into a full-stack trading-terminal screener.

> **Core value:** Reliable real-time ingestion → efficient tick processing → correct intraday calculations → useful ranking/screening → fast live visualization.

---

## Features

- **500 instruments** in-memory streaming engine (WebSocket → Parser → Mapper → MarketState → Indicator → Signal → Broadcast → Frontend)
- **Normalized `MarketTick`** schema isolating provider code (add new provider without rewriting engine)
- **Candle aggregation** 1/3/5/15/30 min, IST timezone, correct boundaries, missing/duplicate/reconnect handling
- **Indicators:** VWAP + ±1σ/±2σ bands, EMA9/20/50, RSI(14) + divergence detection, ATR(14) (sizes every generated signal's stop/target), MACD(12,26,9) + zero-line cross detection, Bollinger(20,2) + band-width%, true Wilder ADX(14) + DI+/DI-, Supertrend(10,3) — all guard against insufficient candles, all selectable as screener columns
- **Momentum:** 1/3/5/15/30m returns, 15-min and 30-min opening range, previous-day high/low, day high/low breakout
- **OHLC Breaker module:** prior-day/opening-range breakout state machine (WATCHING → WEAK_BREAK → PENDING_RETEST → CONFIRMED → FAILED), gated on RVOL≥1.5x & ADX≥20, retest-and-hold false-breakout filter, 0-100 score, ATR-sized entry/stop/targets — `backend/app/breaker.py`
- **5 intraday strategies** (ORB 15-min, VWAP mean-reversion, Supertrend-flip momentum, Gap-and-Go/Gap-Fade classification, first VWAP pullback), each with live entry/stop/target and a same-session forward-tracked hit rate, ranked in one **Intraday Signals** tab — `backend/app/intraday_strategies.py`
- **Options strategy panel:** short strangle, iron condor, bull put/bear call credit spreads, iron fly, calendar spread, 1x2 ratio spread — each priced live off the option chain (net premium, max profit/loss, breakevens, real risk-neutral POP, theta, margin estimate), regime-gated on IV rank + ADX where applicable — `backend/app/options/strategies.py`
- **Seller's Premium Dashboard:** VIX mean-reversion z-score, real IV-minus-realized-vol spread, composite 0-100 premium-selling favorability score, expiry-day pin-risk — `backend/app/options/seller_premium.py`
- **Advanced filter bar:** sector multi-select, price/RVOL range bands, all technical indicators, F&O OI-buildup classification, screener-signal filters, combinable AND/OR conditions with named saved presets (localStorage) — `frontend/src/components/FilterBuilder.jsx`
- **Screeners:** Gainers, Losers, Volume Spike, Momentum, Breakout/Breakdown, VWAP above/below, Unusual Activity (score)
- **Score 0-100** configurable: Momentum 25 + Volume 25 + RelVolume 20 + Breakout 15 + VWAP 10 + Volatility 5 → labeled analytical score (NOT advice)
- **Alerts** with cooldown/debounce: breakout, breakdown, volume spike, VWAP cross, momentum, RSI, pct movement
- **Market Overview:** adv/dec, sector performance/breadth, top lists, VWAP skew, breakouts, own data-freshness timestamp
- **Market Status:** NSE hours 09:15-15:30 IST, pre/post, holidays, LIVE/MARKET CLOSED, last data received
- **Dashboard:** institutional navy/blue trading-desk theme, compact/comfortable density toggle, collapsible dashboard drawer, selectable/reorderable/pinnable columns, sortable, filters, search, sector filter, freshness indicator (LIVE/DELAYED/STALE/NO_DATA), subtle flash on tick
- **Detail panel:** OHLC, VWAP, RSI/EMA/ATR, score, intraday chart (Recharts) with 1/3/5/15/30 switching, real-time
- **WebSocket fan-out:** Backend holds single Kite connection → broadcasts minimal JSON (~250ms batch) to many frontends; no API keys in browser
- **Modes:** `mock` (realistic walk for 500 symbols, no credentials), `live` (Kite), `replay` (recorded ticks at Nx speed)
- **Performance:** async, non-blocking WS, incremental VWAP/indicators, batched broadcasts, minimal payloads, no DB writes per tick, throttled UI
- **Robustness:** reconnect with exponential backoff, resubscription, heartbeat, stale detection, malformed handling, graceful shutdown, structured logs (no secrets)
- **No fabricated data anywhere:** every indicator, signal, and score is computed from real fetched/streamed data. Where a real data source isn't available (no network access to backfill historical VIX/IV, no market-cap reference table, no futures OI feed for equities), the corresponding field is explicitly `null` with a stated reason rather than a placeholder number — see "New Modules" below for exactly where this applies.

---

## New Modules (indicators, signals, options strategies, filters)

Added across this engagement, each verified against hand-computed reference values (unit tests) and/or live/synthetic end-to-end runs before being considered done:

### Technical indicators (`backend/app/indicators.py`, `indicators_advanced.py`)
VWAP ±1σ/±2σ bands (volume-weighted variance), true Wilder-smoothed ADX + DI+/DI- (not a single-bar DX proxy), MACD histogram zero-line cross detection, RSI swing-point divergence (bullish/bearish), Bollinger band-width%, a stateful Supertrend with correctly ratcheting bands (an earlier single-bar version silently inverted trend direction in a clean trend — fixed and covered by a regression test), and `atr_stop_target()` which sizes every generated signal's stop/target off real ATR.

### OHLC Breaker (`backend/app/breaker.py`, `GET /api/signals/breaker`)
Tracks a prior-day-OHLC / 15-min-opening-range breakout level per symbol. A break only becomes a validated signal once gated by RVOL≥1.5x and ADX≥20; a retest-and-hold filter requires the last 2 *closed* 1-minute candles to hold beyond the level before calling it CONFIRMED, rejecting single-tick false breakouts. State machine: `WATCHING → WEAK_BREAK → PENDING_RETEST → CONFIRMED → FAILED`.

### Intraday Signals (`backend/app/intraday_strategies.py`, `GET /api/signals/intraday`)
Five strategies (ORB15, VWAP reversion, Supertrend flip, Gap-and-Go/Gap Fade, first VWAP pullback), each producing entry/stop/target/status. `hit_rate` is a **same-session forward-tracked** outcome rate (every fired signal is followed against real subsequent ticks) — not a historical backtest, since this environment has no network access to backfill multi-day Kite/NSE history and fabricating one would violate the no-dummy-data rule.

### Options strategy panel (`backend/app/options/strategies.py`, `GET /api/options/strategies`)
Six strategies priced off the live chain via the existing `profit_loss_diagram` payoff engine: short strangle, iron condor, bull put/bear call spreads, iron fly, calendar spread, 1x2 ratio spread. POP is a real risk-neutral lognormal probability (not a fabricated percentage); short_strangle/iron_condor/iron_fly are gated eligible only when IV rank ≥50 and ADX ≤25; calendar spread is gated on real contango (far-expiry IV > near-expiry IV).

### Seller's Premium Dashboard (`backend/app/options/seller_premium.py`, `GET /api/options/sellers-premium-dashboard`)
VIX mean-reversion z-score (current VIX vs its own historical mean/std), a real IV-minus-realized-vol spread (today's live IV against actual trailing realized vol from real historical closes — no historical IV series is fabricated), a composite 0-100 premium-selling favorability score (renormalized across whichever inputs are actually available), and expiry-day pin risk (distance to max pain + OI concentration near the money).

### Advanced filter bar (`frontend/src/components/FilterBuilder.jsx`)
Sector multi-select, price/RVOL range bands (market-cap band intentionally omitted — no market-cap data source exists in this app), every technical indicator above, F&O OI-buildup classification (long/short buildup, long unwinding, short covering — computed only for instruments whose ticks actually carry OI; equity spot ticks never do), screener-signal filters, combinable AND/OR conditions, named saved presets.

### A production bug found and fixed along the way
`_init_universe` pre-fills `state.open` with the previous close as a placeholder when the server boots with the market closed. The original `on_tick` guard (`if state.open is None`) never fired again once that placeholder was set — so `gap_pct` (and everything derived from it: gap classification, gap-based alerts/screeners) silently stayed ~0 forever in production, since the server almost never boots during exact live market hours. Fixed by tracking a dedicated per-symbol "real open captured today" set instead of relying on `None`-ness; covered by 3 regression tests.

---

## Architecture

```
                ┌─────────────────┐
     Internet → │ Frontend (Vite) │─╮
                └─────────────────┘ │
                                    ▼
                ┌─────────────────────────────────┐
                │ Backend FastAPI + WebSocket     │
                │  /api/*  +  /ws (fan-out)       │
                │─────────────────────────────────│
                │ Market Data Engine              │
                │  Provider (Mock/Live/Replay)    │
                │    ↓                            │
                │  Message Parser (binary, Kite)  │
                │    ↓                            │
                │  Symbol/Token Mapper            │
                │    ↓                            │
                │  InMemoryMarketState            │
                │    ↓                            │
                │  CandleEngine (IST)             │
                │    ↓                            │
                │  IndicatorEngine                │
                │    ↓                            │
                │  Scoring (0-100) + Screeners    │
                │    ↓                            │
                │  AlertEngine (cooldown)         │
                │    ↓                            │
                │  Broadcaster (batched, minimal) │
                └─────────────────────────────────┘
                                    │
                                    ▼
                          Kit/Kite WebSocket
```

**Data flow per spec:** `WebSocket Feed → Message Parser → Symbol/Token Mapper → In-Memory Market State → Indicator Engine → Signal Engine → WebSocket Broadcast → Frontend Dashboard`

---

## Project Structure

```
nse-top500-realtime-screener/
├── config/nse_top500.json          # universe (symbol, token, company, sector, industry, index, prev_close, avg_volume) - easy to update
├── backend/
│   └── app/
│       ├── main.py                 # FastAPI lifespan, /api/* + /ws
│       ├── config.py               # pydantic-settings + .env
│       ├── models.py               # MarketTick (normalized), StockState, Candle, Alert, etc
│       ├── market_state.py         # InMemoryMarketState + VWAP/relVolume + ranking
│       ├── candle_engine.py        # IST candle aggregation
│       ├── indicators.py           # VWAP bands/EMA/RSI+divergence/ATR/MACD+cross/BB/true ADX+DI, OI-buildup classifier
│       ├── indicators_advanced.py  # stateful Supertrend, Ichimoku, Fibonacci
│       ├── breaker.py              # Part 3: OHLC Breaker breakout state machine
│       ├── intraday_strategies.py  # Part 4: 5 intraday strategies + forward hit-rate tracker
│       ├── options/
│       │   ├── institutional.py    # ATM premium, vol surface, greeks, OI/max-pain, P&L engine, etc
│       │   ├── strategies.py       # Part 5: 6 options strategies priced off the live chain
│       │   └── seller_premium.py   # Part 6: VIX z-score, IV-RV spread, favorability score, pin risk
│       ├── scoring.py              # 0-100 configurable
│       ├── screeners.py            # gainer/loser/volume/momentum/breakout etc
│       ├── alerts.py               # cooldown engine
│       ├── market_hours.py         # NSE 09:15-15:30 IST + holidays
│       ├── historical/store.py     # get_history, hv_cone, iv_percentile — real-or-null
│       ├── providers/
│       │   ├── kite_provider.py    # live - preserves original binary parsing + reconnect
│       │   ├── mock_provider.py    # mock walk (500 symbols)
│       │   └── replay_provider.py  # replay from jsonl
│       ├── services/
│       │   ├── data_engine.py      # orchestrator (reconnect/broadcast/batch)
│       │   ├── broadcaster.py      # fan-out to many frontends
│       │   ├── kite_rest.py        # REST OHLC/LTP/quote fallback
│       │   ├── history_warmer.py   # boot-time real prev-close/avg-volume/candle warmup
│       │   └── token_refresher.py  # daily + boot-time Kite token refresh
│       ├── api/                    # health, market, stocks, screener, alerts, options, institutional, signals
│       └── utils/                  # logging, freshness
│   └── tests/                      # pytest for all engines (indicators, breaker, strategies, seller_premium, market_state, api)
├── frontend/
│   ├── src/
│   │   ├── App.jsx                 # terminal layout (header/overview/filters/table/detail, tab switcher)
│   │   ├── services/api.js         # REST helpers
│   │   ├── hooks/useWebSocket.js   # auto-reconnect, incremental merge, throttle
│   │   ├── components/
│   │   │   ├── Header, MarketOverview, StockTable, DetailPanel, WatchlistManager
│   │   │   ├── FilterBuilder.jsx        # Part 7: advanced combinable/saveable filter bar
│   │   │   ├── IntradaySignals.jsx      # Part 3+4: OHLC Breaker + 5 intraday strategies tab
│   │   │   ├── OptionsInsights.jsx      # options analytics + Part 5 strategy panel + Part 6 seller's premium dashboard
│   │   │   ├── OptionsChain, OpenInterestChart, InstitutionalOptions, AgileInstitutional
│   │   │   └── PaperTrading, MarketReplay, AlertsCenter, ThemeToggle, auth/LoginManager
│   │   └── index.css               # institutional navy/blue theme tokens
│   ├── vite.config.js (proxy /api + /ws → backend)
│   └── package.json
├── scripts/{start_backend.ps1,start_frontend.ps1,generate_universe.py}
├── deployment/{nginx.conf}
├── Dockerfile + docker-compose.yml
├── .env.example
├── requirements.txt
└── README.md
```

---

## Requirements

- Python 3.11+ (3.12 tested) + `pip`
- Node 18+ + `npm`
- No database required (in-memory; opt to add Redis later)

---

## Installation

```powershell
# 1. Clone base then create new project (already done in this repo)
git clone https://github.com/nawin383/socket.git
# create nse-top500-realtime-screener from this template (see repo)

# 2. Backend deps
pip install -r requirements.txt

# 3. Frontend deps
cd frontend
npm install
cd ..

# 4. Universe already included as config/nse_top500.json (500 entries)
# Validate:
python -c "import json; print(len(json.load(open('config/nse_top500.json'))))"
# → 500

# 5. Env
copy .env.example .env
# edit .env -> set DATA_MODE=mock for dev without credentials
```

---

## Environment Variables

`.env.example`:

```
KITE_API_KEY=
KITE_ACCESS_TOKEN=
KITE_CLIENT_ID=
WEBSOCKET_URL=wss://ws.kite.trade/
DATA_MODE=mock
NSE_UNIVERSE_FILE=config/nse_top500.json
LOG_LEVEL=INFO
HOST=0.0.0.0
PORT=8000
STALE_THRESHOLD_SEC=30
CANDLE_INTERVALS=1,3,5,15,30
WS_BROADCAST_INTERVAL_MS=250
MAX_ALERTS=1000
REPLAY_SPEED=10
REPLAY_FILE=
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

Never hard-code secrets; backend-only auth (frontend never sees `KITE_*`).

---

## Kite API Setup (live mode)

1. Create app at https://kite.trade → get `api_key`
2. Login flow → obtain `access_token` (via `kite-auto-trader` style auth or manual)
3. Set in `.env`:
   ```
   DATA_MODE=live
   KITE_API_KEY=xxx
   KITE_ACCESS_TOKEN=yyy
   WEBSOCKET_URL=wss://ws.kite.trade/
   ```
4. Run backend → provider subscribes in 200-token batches, full mode, auto resubscribes on reconnect.

Tokens in `config/nse_top500.json` must match Kite instrument tokens (NSE equity `instrument_token`). Update via `scripts/generate_universe.py` or by fetching `https://api.kite.trade/instruments/NSE` CSV and re-mapping.

---

## NSE Universe Setup

- File: `config/nse_top500.json`
- Each entry: `symbol`, `trading_symbol`, `company`, `exchange:"NSE"`, `instrument_token`, `sector`, `industry`, `prev_close`, `avg_volume`, `index_membership`
- Easy to update: edit JSON or regenerate via Kite instruments API (see `scripts/generate_universe.py` guidance)
- App handles: missing/invalid tokens → warning + skip; symbol changes → token→symbol map layer; adding/removing → just edit file and restart.

---

## Running

### Mock mode (dev, no credentials, 500 live symbols simulated)

```powershell
# terminal 1: backend
$env:DATA_MODE="mock"
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload

# terminal 2: frontend
cd frontend
npm run dev
# → http://localhost:5173 (proxy to backend)
# Header shows MOCK DATA, 500 rows live flashing
```

### Live mode

```powershell
# .env set DATA_MODE=live + KITE_API_KEY/ACCESS_TOKEN
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
cd frontend; npm run dev
# Header shows LIVE when NSE open (09:15-15:30 IST), else MARKET CLOSED + holiday handling
```

### Replay mode

```powershell
# Record first (one-time live):
# customize scripts/replay_record.py to dump ticks to replay.jsonl

# Then replay:
$env:DATA_MODE="replay"
$env:REPLAY_FILE="replay.jsonl"
$env:REPLAY_SPEED="10"
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

### Production (Docker)

```powershell
docker-compose up --build
# backend → http://localhost:8000
# frontend → http://localhost:3000
# nginx covers /api + /ws proxy (see deployment/nginx.conf)
```

---

## Testing

```powershell
# unit + integration
pytest backend/tests -v
# or
python -m pytest backend/tests -v

# Load test concept: MockProvider already simulates 500 instruments * 50-120 ticks per 200ms (~300 ticks/sec)
# Watch backend logs for "ticks_processed" and frontend remains smooth.
# For multi-client load, open multiple browser tabs → single upstream connection, fan-out.

# Lint (optional)
ruff backend/app  # or flake8
mypy backend/app  # if added
```

126+ tests covering: VWAP bands, RSI + divergence, EMA, ATR + stop/target sizing, true Wilder ADX/DI+/DI-, stateful Supertrend (including the trend-direction regression test), MACD cross, Bollinger, OI-buildup classification, momentum/relVolume/breakout/score, candle aggregation, the OHLC Breaker state machine (weak-break/pending-retest/confirmed/failed transitions, false-breakout detection), all 5 intraday strategies + forward hit-rate tracker, all 6 options strategies (delta-based strike selection, credit/debit sign, bounded-vs-unlimited risk, POP), the Seller's Premium Dashboard (VIX z-score, IV-RV spread, favorability score, pin risk — with hand-computed exact-value cases), the state.open/gap_pct production bug fix, WebSocket broadcast, and API endpoints.

---

## API Endpoints

```
GET /api/health
GET /api/ready
GET /api/config              # safe config (no secrets)
GET /api/stats               # ticks_processed, batches, errors
GET /api/market/status       # {status, is_live, label:LIVE/MARKET CLOSED, last_data_received, server_time_ist}
GET /api/market/overview     # adv/dec, top_gainers/losers, sector_performance, vwap skew, breakouts
GET /api/universe            # full 500
GET /api/stocks?search=&sector=&sort_by=&order=&limit=500&offset=0&freshness=
GET /api/stocks/:symbol      # detail + candles 1/3/5/15/30
GET /api/screener            # list available
GET /api/screener/:name?limit=20  # gainer|loser|volume|momentum|breakout|breakdown|vwap_above|vwap_below|unusual
GET /api/alerts?limit=&symbol=&type=
DELETE /api/alerts
GET /api/signals/breaker?min_score=&limit=          # Part 3: OHLC Breaker signals
GET /api/signals/intraday                           # Part 4: 5 intraday strategies + hit rates
GET /api/options/strategies?symbol=&expiry=&adx=    # Part 5: 6 options strategies, live-priced
GET /api/options/sellers-premium-dashboard?symbol=  # Part 6: VIX z-score, IV-RV spread, favorability score, pin risk
WS  /ws/ticks                # snapshot + batched ticks {type:ticks|snapshot, data:[minimal rows], meta:{...}}
```

Adapted to original repo’s `KiteWebSocket` / `KiteWebSocketServer` patterns rather than forcing new framework.

---

## Mock vs Live Labeling

- Mock: header badge `MOCK DATA` (yellow), all data generated via GBM walk
- Live: badge `LIVE` (emerald) only when data actually from Kite WS; else `MARKET CLOSED`/`HOLIDAY` + `Last data received`
- Never fabricate live LTP/volume when in live mode but provider down → shows STALE

---

## Performance Considerations

- Asyncio + threading for websocket-client (original) wrapped, batched broadcast 250ms (~4fps) throttled UI avoids re-render storm
- In-memory dicts + deque maxlen 500 per interval per symbol (no DB per tick)
- Minimal JSON (snake→camel trimmed, only changed symbols per batch)
- Table: relies on React incremental merge, only flashed rows animate; for 500 rows, consider `react-window` virtualization if needed (current handles 500 fine; add if >1000)
- Indicator engine incremental where possible (EMA incremental would be further optimize)

---

## Troubleshooting

| Issue | Cause | Fix |
|---|---|---|
| 500 not showing | universe file missing | check `NSE_UNIVERSE_FILE` exists, `python -c "import json;print(len(json.load(open('config/nse_top500.json'))))"` |
| WS closed repeatedly | credentials bad | check `KITE_*` in `.env` logs `KiteAuthenticationError`; switch to `mock` to verify frontend |
| Stale all rows | market closed | expected outside 09:15-15:30 IST; check `GET /api/market/status` → `is_live` false; use mock/replay to test |
| No ticks | DATA_MODE=live but not subscribed | logs `Subscribed X instruments`; ensure tokens valid, check `GET /api/stats` ticks_processed |
| Frontend blank table | CORS | ensure `CORS_ORIGINS` includes `http://localhost:5173`; vite proxy covers `/api` |
| Sector filter empty | universe sector missing | check `config/nse_top500.json` sector fields; regenerate |
| RSI None | insufficient candles | need ~14 1m candles (~14 min after open or mock running 14 ticks); wait orCheck `candles` in detail panel |
| Memory high | candle maxlen | `CandleEngine(max_candles=500)` caps; reduce if needed |

Logs: `INFO` covers startup, WS connect/subscribe/reconnect, errors, ticks processed, broadcast, alerts, stale. No API keys logged.

---

## Deployment

- **Docker:** `docker-compose up --build` (backend healthcheck + restart, frontend nginx, `deployment/nginx.conf` handles WS upgrade)
- **VPS:** systemd `backend.service` (see original `auto_trader/deploy/kite-trader.service` pattern) + nginx proxy
- **WebSocket stability:** `proxy_read_timeout 86400`, heartbeat 3s ping, auto resubscribe
- **Env:** keep `.env` on server, not in repo

Production architecture:

```
Internet → Frontend (nginx/Vite) → Backend (FastAPI/WS) → Market Data Engine → Kit/Kite WS
```

---

## Security

- Env-only secrets, never in frontend bundle
- Backend validates WS messages, safe CORS, input validation (symbol upper, limit clamped)
- Secrets redacted from logs, production-safe 500 error messages

---

## Disclaimer

Scores, signals, screeners are **analytical** only, **not investment advice**. `LIVE` vs `MOCK DATA` explicitly labeled.

---

## License

MIT (inherits from base `socket` project).

