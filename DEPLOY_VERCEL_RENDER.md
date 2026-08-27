# Deploy — Option 2: Vercel (Frontend) + Render (Backend) — Free

Repo is already live at https://github.com/nawin383/nse-top500-realtime-screener

## 1) Backend on Render.com (Python, free)

1. Go to https://dashboard.render.com → **New + → Web Service** → connect `nawin383/nse-top500-realtime-screener`
2. Settings:
   - **Name:** `nse-top500-backend`
   - **Region:** Singapore (closest to NSE)
   - **Branch:** `main`
   - **Root Directory:** leave empty (repo root)
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`
3. **Environment → Add**:
   ```
   DATA_MODE=mock
   LOG_LEVEL=INFO
   NSE_UNIVERSE_FILE=config/nse_top500.json
   CORS_ORIGINS=https://YOUR_FRONTEND.vercel.app,http://localhost:5173
   # for live later:
   # KITE_API_KEY=xxx
   # KITE_ACCESS_TOKEN=yyy
   # WEBSOCKET_URL=wss://ws.kite.trade/
   ```
   Replace `YOUR_FRONTEND` after step 2 (you can update later).
4. Create → Render builds → wait for **Live** → copy backend URL e.g. `https://nse-top500-backend.onrender.com`
5. Test: `https://nse-top500-backend.onrender.com/api/health` → `{"status":"ok"}` and `.../api/market/status`

> `render.yaml` is already in repo for "Infrastructure as Code" — Render can also import it via **New → Blueprint**.

## 2) Frontend on Vercel (free)

1. Go to https://vercel.com → **Add New → Project** → Import `nawin383/nse-top500-realtime-screener`
2. **Configure Project:**
   - **Framework Preset:** Vite
   - **Root Directory:** `frontend`  (click Edit → select `frontend`)
   - **Build Command:** `npm run build` (auto)
   - **Output Directory:** `dist`
   - **Install Command:** `npm install`
3. **Environment Variables → Add:**
   ```
   VITE_API_URL=https://nse-top500-backend.onrender.com
   VITE_WS_URL=wss://nse-top500-backend.onrender.com/ws/stream
   ```
   Use the exact Render URL from step 1 (no trailing slash). `VITE_API_URL` is used in `frontend/src/services/api.js:1` (`BASE = import.meta.env.VITE_API_URL`), `VITE_WS_URL` in `frontend/src/hooks/useWebSocket.js:14`.
4. Deploy → Vercel builds → get URL e.g. `https://nse-top500-realtime-screener.vercel.app`
5. **Update Render CORS:** go back to Render → Environment → set `CORS_ORIGINS=https://nse-top500-realtime-screener.vercel.app` → Save → Re-deploy.

## 3) Verify Live

- Frontend: `https://...vercel.app` → header shows `MOCK DATA` (or `LIVE` if `DATA_MODE=live` + Kite creds) and 500 rows flashing.
- Backend WS: `wss://...onrender.com/ws/stream` → snapshot 500.
- API: `https://...onrender.com/docs` (FastAPI docs).

## 4) Switch to Live Kite later

In Render → Environment: set `DATA_MODE=live`, `KITE_API_KEY`, `KITE_ACCESS_TOKEN` → Save → Re-deploy. Frontend will show `LIVE` during NSE hours 09:15-15:30 IST, else `MARKET CLOSED` + `Last data received`.

## 5) Local still works (proxy)

For local dev, `frontend/vite.config.js:7` proxies `/api` and `/ws` to `localhost:8000`, so no `VITE_*` needed — `npm run dev` in `frontend` + `uvicorn backend.app.main:app` in backend.

## Troubleshooting

| Issue | Fix |
|---|---|
| CORS blocked | Add Vercel URL to Render `CORS_ORIGINS` comma-separated |
| WS fails (mixed content) | Use `wss://` not `ws://` for https frontend |
| 500 not showing | Check Render logs → `Loaded universe 500` |
| Render cold start (free) | First request after sleep ~30s, then live |

