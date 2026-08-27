# NSE Top 500 Real-Time Intraday Market Screener

Production-quality real-time intraday screener for **NSE Top 500** stocks streaming via **Kite WebSocket** (Kit WebSocket / Zerodha Kite Connect API) with mock & replay modes for development outside market hours.

**Original base:** [nawin383/socket](https://github.com/nawin383/socket) — Python Kite WebSocket client (binary tick parsing, auto-reconnect, relay server). This project preserves its proven WebSocket patterns and expands into a full-stack trading-terminal screener.

> **Core value:** Reliable real-time ingestion → efficient tick processing → correct intraday calculations → useful ranking/screening → fast live visualization.

---

## Features

- **500 instruments** in-memory streaming engine (WebSocket → Parser → Mapper → MarketState → Indicator → Signal → Broadcast → Frontend)
- **Normalized `MarketTick`** schema isolating provider code (add new provider without rewriting engine)
- **Candle aggregation** 1/3/5/15/30 min, IST timezone, correct boundaries, missing/duplicate/reconnect handling
- **Indicators:** VWAP, EMA9/20/50, RSI(14), ATR(14), MACD(12,26,9), Bollinger(20,2), ADX(14) — all guard against insufficient candles
- **Momentum:** 1/3/5/15/30m returns, opening-range breakout, day high/low breakout
- **Screeners:** Gainers, Losers, Volume Spike, Momentum, Breakout/Breakdown, VWAP above/below, Unusual Activity (score)
- **Score 0-100** configurable: Momentum 25 + Volume 25 + RelVolume 20 + Breakout 15 + VWAP 10 + Volatility 5 → labeled analytical score (NOT advice)
- **Alerts** with cooldown/debounce: breakout, breakdown, volume spike, VWAP cross, momentum, RSI, pct movement
- **Market Overview:** adv/dec, sector performance/breadth, top lists, VWAP skew, breakouts
- **Market Status:** NSE hours 09:15-15:30 IST, pre/post, holidays, LIVE/MARKET CLOSED, last data received
- **Dashboard:** dark trading terminal, virtualized-lean table (only changed rows update), sortable, filters, search, sector filter, freshness indicator (LIVE/DELAYED/STALE/NO_DATA), subtle flash on tick
- **Detail panel:** OHLC, VWAP, RSI/EMA/ATR, score, intraday chart (Recharts) with 1/3/5/15/30 switching, real-time
- **WebSocket fan-out:** Backend holds single Kite connection → broadcasts minimal JSON (~250ms batch) to many frontends; no API keys in browser
- **Modes:** `mock` (realistic walk for 500 symbols, no credentials), `live` (Kite), `replay` (recorded ticks at Nx speed)
- **Performance:** async, non-blocking WS, incremental VWAP/indicators, batched broadcasts, minimal payloads, no DB writes per tick, throttled UI
- **Robustness:** reconnect with exponential backoff, resubscription, heartbeat, stale detection, malformed handling, graceful shutdown, structured logs (no secrets)

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
│       ├── indicators.py           # EMA/RSI/ATR/MACD/BB/ADX (correct)
│       ├── scoring.py              # 0-100 configurable
│       ├── screeners.py            # gainer/loser/volume/momentum/breakout etc
│       ├── alerts.py               # cooldown engine
│       ├── market_hours.py         # NSE 09:15-15:30 IST + holidays
│       ├── providers/
│       │   ├── kite_provider.py    # live - preserves original binary parsing + reconnect
│       │   ├── mock_provider.py    # mock walk (500 symbols)
│       │   └── replay_provider.py  # replay from jsonl
│       ├── services/
│       │   ├── data_engine.py      # orchestrator (reconnect/broadcast/batch)
│       │   └── broadcaster.py      # fan-out to many frontends
│       ├── api/                    # health, market, stocks, screener, alerts
│       └── utils/                  # logging, freshness
│   └── tests/                      # pytest for all engines
├── frontend/
│   ├── src/
│   │   ├── App.tsx                 # terminal layout (header/overview/filters/table/detail)
│   │   ├── api.ts                  # REST helpers
│   │   ├── types.ts
│   │   ├── hooks/useWebSocket.ts   # auto-reconnect, incremental merge, throttle
│   │   ├── components/{Header,MarketOverview,ScreenerControls,StockTable,StockDetailPanel,AlertsPanel}
│   │   └── styles/index.css
│   ├── vite.config.ts (proxy /api + /ws → backend)
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

Tests cover: VWAP, RSI, EMA, ATR, momentum, relVolume, breakout, score, candle aggregation, WebSocket broadcast, API endpoints.

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
WS  /ws                      # snapshot + batched ticks {type:ticks|snapshot, data:[minimal rows], meta:{...}}
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

