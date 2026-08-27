export interface StockRow {
  symbol: string
  token: number
  company?: string
  sector?: string
  industry?: string
  ltp: number
  change?: number
  change_pct?: number | null
  volume: number
  rel_volume?: number | null
  high?: number
  low?: number
  open?: number
  previous_close?: number
  vwap?: number | null
  rsi?: number | null
  ema9?: number | null
  ema20?: number | null
  score: number
  signal: string
  rank?: number
  freshness: string
  timestamp?: string
  momentum?: {
    ret_1m?: number
    ret_3m?: number
    ret_5m?: number
    ret_15m?: number
    ret_30m?: number
    breakout?: boolean
    breakdown?: boolean
  }
  range_pct?: number
  gap_pct?: number
}

export interface MarketStatus {
  status: string
  is_live: boolean
  label: string
  last_data_received?: string
  server_time_ist: string
}

export interface MarketOverviewData {
  total: number
  advancing: number
  declining: number
  unchanged: number
  above_vwap: number
  below_vwap: number
  breakouts: number
  breakdowns: number
  sector_performance: Record<string, {count:number, adv:number, avg_change:number, breadth:number}>
}

export interface Alert {
  id: string
  symbol: string
  token: number
  type: string
  message: string
  timestamp: string
  ltp: number
}

export interface Candle {
  timestamp: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  interval: number
}
