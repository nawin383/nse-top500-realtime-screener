# Legacy standalone scripts

These five scripts were originally written to run locally (desktop Python,
interactive prompts, local CSV/Excel output, `os.startfile` to auto-open
Excel). They're archived here as-is for reference/history. None of them run
as part of this app; the table below says what happened to each.

| Script | What it does | Status |
|---|---|---|
| `india_vix_first10min_analyzer.py` | Analyzes India VIX volatility in the first 10 minutes of trading over the last N days, using Kite historical minute candles. | **Ported** — rebuilt as `GET /api/analytics/vix-open-volatility` in the backend, using the app's existing Kite REST client instead of a standalone `aiohttp` session, and a new "VIX Open Volatility" panel in the frontend Options Analytics view. |
| `etf_tracker.py` | Live ETF breakout/score tracker writing to CSV + an auto-refreshing local Excel dashboard. | **Ported** (the live-scoring logic only) — rebuilt as `GET /api/etf/screener` reusing the app's existing Kite provider/quote client, surfaced as a new "ETF Screener" tab. The CSV/Excel/rich-console/auto-open-Excel machinery was dropped; it has no equivalent in a web app. |
| `elite_quant_india.py`, `elite_quant_usa.py` | "Nobel Prize" composite scoring (Markowitz, Fama-French, VaR/CVaR, PCA/clustering, behavioral-finance indicators) across ~2000 Indian / ~1000 US symbols, using `yfinance` for 5 years of daily history per symbol. | **Not ported.** Fetching 5 years of history for thousands of symbols from Yahoo Finance is not something a live web request can do — `yfinance` rate-limits aggressively and this would take on the order of hours per full run, not something a page load can wait on. Making this "live" would require a separate offline batch job (e.g. a nightly cron populating a cache) run somewhere with no request deadline, which is a materially different project. Left archived rather than wired in half-working. |
| `nobel_optionchain_sensibull.py` | Options Greeks/scoring analysis sourced from `oxide.sensibull.com` / `api.sensibull.com` — undocumented internal endpoints of a third party (Sensibull), not the user's own Kite account. | **Not ported.** This app's own options stack (`backend/app/options/`) already computes Black-Scholes Greeks, IV, PCR, max pain, etc. honestly from the user's own authorized Kite data. Scraping a third party's private API for a redundant metric would be a downgrade in reliability and authorization compared to what's already built, not an upgrade. |
