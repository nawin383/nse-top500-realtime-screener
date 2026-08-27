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
  const r = await fetch(`${BASE}/api/market/overview`)
  if(!r.ok) throw new Error('overview failed')
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
  // try universe -> derive sectors; fallback to stocks distinct
  try{
    const r = await fetch(`${BASE}/api/universe`)
    if(r.ok){ const j=await r.json(); const data=j.data||j; if(Array.isArray(data)){ const map={}; data.forEach(x=>{ const s=x.sector||'Unknown'; map[s]=(map[s]||0)+1}); return {data: Object.entries(map).map(([sector,count])=>({sector,count}))} } }
  }catch(e){}
  try{
    const r2 = await fetch(`${BASE}/api/stocks?limit=500`)
    if(r2.ok){ const j=await r2.json(); const rows=j.data||[]; const map={}; rows.forEach(x=>{ const s=x.sector||'Unknown'; map[s]=(map[s]||0)+1}); return {data: Object.entries(map).map(([sector,count])=>({sector,count}))} }
  }catch(e){}
  return {data:[]}
}
export async function fetchVerify(path){ const r=await fetch(`${BASE}/api/verify/${path}`); return r.json()}
export async function fetchSubscription(){ return fetchVerify('subscription')}
export async function fetchVerifyUniverse(){ return fetchVerify('universe')}
export async function fetchVerifyTicks(){ return fetchVerify('ticks')}
export async function fetchWsHealth(){ const r=await fetch(`${BASE}/api/verify/ws`); return r.json()}
export async function fetchMemoryStats(){ const r=await fetch(`${BASE}/api/monitoring/memory`); return r.json()}
