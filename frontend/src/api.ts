const API_BASE = '' // vite proxy handles /api

export async function fetchJSON(path: string) {
  const res = await fetch(path)
  if (!res.ok) throw new Error(`${path} ${res.status}`)
  return res.json()
}

export const api = {
  health: () => fetchJSON('/api/health'),
  marketStatus: () => fetchJSON('/api/market/status'),
  marketOverview: () => fetchJSON('/api/market/overview'),
  stocks: (params: Record<string,string|number> = {}) => {
    const q = new URLSearchParams(params as any).toString()
    return fetchJSON(`/api/stocks?${q}`)
  },
  stockDetail: (symbol:string) => fetchJSON(`/api/stocks/${symbol}`),
  screener: (name:string, limit=20) => fetchJSON(`/api/screener/${name}?limit=${limit}`),
  alerts: (limit=50) => fetchJSON(`/api/alerts?limit=${limit}`),
  universe: () => fetchJSON(`/api/universe`),
  config: () => fetchJSON(`/api/config`),
  stats: () => fetchJSON(`/api/stats`),
}
