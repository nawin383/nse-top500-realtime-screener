# User Guide

## 1. Login & Mode Badge

![header](screenshots/header.png) Header shows `MOCK DATA` (mock) or `LIVE`/`MARKET CLOSED` (live). Check `Last data received`.

## 2. Filters

![filters](screenshots/filters.png) Search symbol, sector dropdown, freshness pills, screener tabs (Gainers/Losers/Volume/Breakout).

## 3. Stock Table

![table](screenshots/table.png) Sorted by score. Hover row -> spark sparkline. Click row -> Detail panel.

## 4. Detail Panel

![detail](screenshots/detail.png) Shows OHLC, VWAP, RSI/EMA, score, 1/3/5/15/30 chart (Recharts). Real-time.

## 5. Alerts

![alerts](screenshots/alerts.png) Bell icon lists breakout/volume/RSI with cooldown badge.

## 6. Export

Click `Export CSV` -> downloads filtered view (PapaParse). `Share screener` -> copy link.

## 7. Common Tasks

| Task | Steps |
|------|-------|
| Find movers | Click Screener `Gainers` -> sort `changePercent` |
| Sector scan | Filter `Sector=Banking` -> overview shows breadth |
| Set alert | In detail panel `Add alert: if price > X` |
| Voice | Say “show gainers” (mic icon) -> filters |

## 8. Troubleshooting

Market closed outside 09:15-15:30 IST is expected. Switch `DATA_MODE=mock` to test.
