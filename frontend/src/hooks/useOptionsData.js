import { useEffect, useRef, useState } from 'react'

// A failed/unavailable endpoint returns {detail:"..."} (or throws on a network
// error) instead of the expected shape -- resolve to null instead of letting
// any card crash the page.
export const safeFetch = async (url) => {
  try {
    const r = await fetch(url)
    const j = await r.json()
    if (!r.ok || j?.detail) return null
    return j
  } catch { return null }
}

const REFRESH_MS = 15000

// Single shared fetch layer for the whole Options Hub. Every sub-view (Chain,
// Analytics, Institutional Flow) reads from one `data` object instead of each
// re-fetching the same PCR/Max Pain/Greeks/VIX endpoints with its own copy of
// the same Promise.all -- that per-tab duplication was the actual redundancy
// across the old Options/Options Insights/Institutional/Agile Pro tabs.
//
// Stale-while-revalidate throughout: a background refresh (15s interval, or a
// windowSize change) only ever applies a field when that endpoint actually
// returned something this time, so switching symbol/expiry or a transient
// failure never blanks a card that already has good data.
export function useOptionsData(symbol, expiry, { windowSize = 10 } = {}) {
  const [data, setData] = useState({})
  const [expiries, setExpiries] = useState([])
  const [loading, setLoading] = useState(false)
  const [lastFetch, setLastFetch] = useState(null)
  const hasLoadedRef = useRef(false)
  const apiBase = import.meta.env.VITE_API_URL || ''

  useEffect(() => {
    let cancelled = false
    fetch(`${apiBase}/api/options/expiries?symbol=${symbol}`).then(r => r.json()).then(j => {
      if (cancelled) return
      setExpiries(j.expiries || [])
    }).catch(() => {})
    return () => { cancelled = true }
  }, [symbol, apiBase])

  useEffect(() => {
    if (!expiry) return
    let cancelled = false
    const load = async () => {
      setLoading(true)
      const q = `symbol=${symbol}&expiry=${expiry}`
      const [
        tshape, atm, pcr, oi, vol, ivhv, vix, unusual, strategies, sellerDash,
        greeksChain, margin, mispricing, correlation, term, scenario, hvCone,
        positions, ticks,
      ] = await Promise.all([
        safeFetch(`${apiBase}/api/options/tshape?${q}&window=${windowSize}`),
        safeFetch(`${apiBase}/api/options/atm-premium?${q}`),
        safeFetch(`${apiBase}/api/options/pcr?${q}`),
        safeFetch(`${apiBase}/api/options/oi-analysis?${q}`),
        safeFetch(`${apiBase}/api/options/vol-surface?${q}`),
        safeFetch(`${apiBase}/api/options/iv-hv?${q}`),
        safeFetch(`${apiBase}/api/options/vix`),
        safeFetch(`${apiBase}/api/options/unusual?${q}`),
        safeFetch(`${apiBase}/api/options/strategies?${q}`),
        safeFetch(`${apiBase}/api/options/sellers-premium-dashboard?${q}`),
        safeFetch(`${apiBase}/api/options/greeks-dashboard?${q}`),
        safeFetch(`${apiBase}/api/options/margin-risk?${q}`),
        safeFetch(`${apiBase}/api/options/mispricing?${q}`),
        safeFetch(`${apiBase}/api/options/correlation`),
        safeFetch(`${apiBase}/api/options/term-structure?symbol=${symbol}`),
        safeFetch(`${apiBase}/api/options/scenario?${q}`),
        safeFetch(`${apiBase}/api/historical/hv-cone?symbol=${symbol}`),
        safeFetch(`${apiBase}/api/portfolio/positions`),
        safeFetch(`${apiBase}/api/microstructure/ticks?symbol=${symbol}&limit=10`),
      ])
      if (cancelled) return
      setData(prev => ({
        tshape: tshape ?? prev.tshape,
        atm: atm ?? prev.atm,
        pcr: pcr ?? prev.pcr,
        oi: oi ?? prev.oi,
        vol: vol ?? prev.vol,
        ivhv: ivhv ?? prev.ivhv,
        vix: vix ?? prev.vix,
        unusual: unusual ?? prev.unusual,
        strategies: strategies ?? prev.strategies,
        sellerDash: sellerDash ?? prev.sellerDash,
        greeksChain: greeksChain ?? prev.greeksChain,
        margin: margin ?? prev.margin,
        mispricing: mispricing ?? prev.mispricing,
        correlation: correlation ?? prev.correlation,
        term: term ?? prev.term,
        scenario: scenario ?? prev.scenario,
        hvCone: hvCone ?? prev.hvCone,
        positions: positions ?? prev.positions,
        ticks: ticks ?? prev.ticks,
      }))
      if (tshape?.expiries?.length) setExpiries(tshape.expiries)
      if (tshape) hasLoadedRef.current = true
      setLastFetch(new Date())
      setLoading(false)
    }
    load()
    const id = setInterval(load, REFRESH_MS)
    return () => { cancelled = true; clearInterval(id) }
  }, [symbol, expiry, windowSize, apiBase])

  return { data, expiries, loading, lastFetch, hasLoadedOnce: hasLoadedRef.current }
}
