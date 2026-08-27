const cache=new Map()
const inflight=new Map()

function entryKey(k){ return typeof k==='string'?k:JSON.stringify(k) }

export async function fetchCached(key, fetcher, { ttl=15000, staleWhileRevalidate=true }={}){
  const k=entryKey(key)
  const now=Date.now()
  const e=cache.get(k)
  if(e && now - e.ts < ttl) return e.data
  if(e && staleWhileRevalidate){
    // revalidate in background
    if(!inflight.has(k)){
      const p=fetcher().then(d=>{ cache.set(k,{data:d,ts:Date.now()}); inflight.delete(k); return d }).catch(()=>{ inflight.delete(k) })
      inflight.set(k,p)
    }
    return e.data
  }
  if(inflight.has(k)) return inflight.get(k)
  const p=fetcher().then(d=>{ cache.set(k,{data:d,ts:Date.now()}); inflight.delete(k); return d }).catch(err=>{ inflight.delete(k); throw err })
  inflight.set(k,p)
  return p
}
export function invalidate(key){
  if(!key) cache.clear()
  else cache.delete(entryKey(key))
}
export function setCache(key,data){ cache.set(entryKey(key),{data,ts:Date.now()}) }
export function getCache(key){ return cache.get(entryKey(key))?.data }

const BASE=import.meta.env.VITE_API_URL||''
async function jget(path){
  const r=await fetch(`${BASE}${path}`)
  if(!r.ok) throw new Error(path+' '+r.status)
  return r.json()
}
export const apiCached={
  health:()=>fetchCached('health',()=>jget('/api/health')),
  marketStatus:()=>fetchCached('marketStatus',()=>jget('/api/market/status'),{ttl:5000}),
  overview:()=>fetchCached('overview',()=>jget('/api/market/overview'),{ttl:10000}),
  stock:(sym)=>fetchCached(['stock',sym],()=>jget(`/api/stocks/${sym}`),{ttl:5000}),
  historical:(sym,limit=100)=>fetchCached(['hist',sym,limit],()=>jget(`/api/historical/${sym}?limit=${limit}`),{ttl:30000}),
}
export const queryClient={ fetchCached, invalidate, setCache, getCache, apiCached }
export default queryClient
