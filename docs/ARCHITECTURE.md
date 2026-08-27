# Architecture

## Diagram

```mermaid
graph TD
  KiteWS[Kite WebSocket] --> Parser[Message Parser<br/>binary tick parse]
  Parser --> Mapper[Token->Symbol Mapper]
  Mapper --> State[InMemoryMarketState<br/>500 symbols dict]
  State --> Candle[CandleEngine<br/>1/3/5/15/30 IST]
  Candle --> Ind[IndicatorEngine<br/>VWAP RSI EMA ATR MACD BB ADX]
  Ind --> Score[Scoring 0-100 + Screeners]
  Score --> Alert[AlertEngine<br/>cooldown 5m]
  Alert --> Broadcaster[WS Broadcaster<br/>batch 250ms minimal JSON]
  Broadcaster --> FE[Frontend React<br/>merge throttle flash]
  FE <--> API[FastAPI /api/*]
  API --> Cache[(Redis cache)]
  State --> Metrics[/metrics<br/>prometheus/]

  subgraph Infra
    Nginx[nginx-lb least_conn]
    K8s[HPA 3-10 + Ingress]
    ELK[Elastic Stack]
  end
  Nginx --> Broadcaster
  K8s --> Nginx
```

## Data Flow

1. **WebSocket Feed** (Kite/Mock/Replay) -> binary frames
2. **Message Parser** validates, extracts LTP/volume/OHLC
3. **Mapper** token->symbol via universe JSON
4. **MarketState** updates tick, freshness, gaps
5. **CandleEngine** aggregates IST boundaries (floor to interval)
6. **IndicatorEngine** incremental VWAP/RSI (guard <14 candles)
7. **Signal/Score** weighted 25/25/20/15/10/5
8. **Broadcaster** fan-out single upstream to N clients
9. **Frontend** merges delta, throttles render, flashes changed rows

## Component Table

| Layer | Tech | Scale | Notes |
|-------|------|-------|-------|
| Backend | FastAPI+uvicorn | HPA 3-10 | async, startup probe |
| WS | websocket-client | 1 upstream | resubscribe batches 200 |
| Cache | Redis | 1 | screener TTL 5s |
| Frontend | Vite+React | 2 replicas | static via nginx |
| LB | nginx least_conn | - | keepalive 64, 86400 ws timeout |
| Observability | prometheus+grafana+ELK | - | p95 tick latency dashboard |
```
