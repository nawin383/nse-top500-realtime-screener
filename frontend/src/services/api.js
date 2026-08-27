const BASE = import.meta.env.VITE_API_URL || ''

export async function fetchHealth() {
  const r = await fetch(`${BASE}/api/health`)
  return r.json()
}
export async function fetchMarketStatus() {
  const r = await fetch(`${BASE}/api/market/status`)
  return r.json()
}
export async function fetchStocks(params={}) {
  const q = new URLSearchParams(params).toString()
  const r = await fetch(`${BASE}/api/stocks?${q}`)
  return r.json()
}
export async function fetchStockDetail(symbol) {
  const r = await fetch(`${BASE}/api/stocks/${symbol}`)
  if(!r.ok) throw new Error('not found')
  return r.json()
}
export async function fetchOverview() {
  const r = await fetch(`${BASE}/api/overview`)
  return r.json()
}
export async function fetchScreener(name, params={}) {
  const q = new URLSearchParams(params).toString()
  const r = await fetch(`${BASE}/api/screener/${name}?${q}`)
  return r.json()
}
export async function fetchAlerts(params={}) {
  const q = new URLSearchParams(params).toString()
  const r = await fetch(`${BASE}/api/alerts?${q}`)
  return r.json()
}
export async function fetchSectors() {
  const r = await fetch(`${BASE}/api/sectors`)
  return r.json()
}
