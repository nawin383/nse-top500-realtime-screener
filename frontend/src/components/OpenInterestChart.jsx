import React, { useEffect, useMemo, useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, Cell } from 'recharts'

const fmtInt = (n) => n == null ? '-' : Math.abs(Number(n)).toLocaleString('en-IN')

// A monthly contract is the LAST expiry that falls within its own calendar month
// among the exchange's published expiry list — no guessing, just grouping real dates.
function classifyExpiries(expiries) {
  if (!expiries || !expiries.length) return { weekly: null, monthly: null }
  const sorted = [...expiries].sort()
  const weekly = sorted[0]
  const weeklyDate = new Date(weekly)
  const sameMonth = sorted.filter(e => {
    const d = new Date(e)
    return d.getFullYear() === weeklyDate.getFullYear() && d.getMonth() === weeklyDate.getMonth()
  })
  const monthly = sameMonth[sameMonth.length - 1] || weekly
  return { weekly, monthly }
}

export default function OpenInterestChart({ theme = 'dark' }) {
  const apiBase = import.meta.env.VITE_API_URL || ''
  const [symbol, setSymbol] = useState('NIFTY')
  const [expiries, setExpiries] = useState([])
  const [tenor, setTenor] = useState('weekly') // weekly | monthly
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  const { weekly, monthly } = useMemo(() => classifyExpiries(expiries), [expiries])
  const activeExpiry = tenor === 'monthly' ? monthly : weekly

  useEffect(() => {
    let cancelled = false
    fetch(`${apiBase}/api/options/expiries?symbol=${symbol}`)
      .then(r => r.json())
      .then(j => { if (!cancelled) setExpiries(j.expiries || []) })
      .catch(() => {})
    return () => { cancelled = true }
  }, [symbol, apiBase])

  useEffect(() => {
    if (!activeExpiry) return
    let cancelled = false
    setLoading(true)
    fetch(`${apiBase}/api/options/oi-analysis?symbol=${symbol}&expiry=${activeExpiry}`)
      .then(async r => {
        const j = await r.json()
        if (!r.ok) throw new Error(j.detail || 'No data available')
        return j
      })
      .then(j => { if (!cancelled) { setData(j); setError(null) } })
      .catch(e => { if (!cancelled) { setError(e.message); setData(null) } })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [symbol, activeExpiry, apiBase])

  const rows = useMemo(() => {
    if (!data?.heatmap) return []
    return data.heatmap.map(r => ({ ...r, peOiNeg: -r.peOi })).sort((a, b) => a.strike - b.strike)
  }, [data])

  const isDark = theme !== 'light'
  const axisColor = isDark ? '#94a3b8' : '#64748b'
  const gridColor = isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)'

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10, height: '100%' }}>
      <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
        <select className="input" value={symbol} onChange={e => setSymbol(e.target.value)} style={{ fontSize: 11, borderRadius: 8 }}>
          <option value="NIFTY">NIFTY 50</option>
          <option value="SENSEX">SENSEX</option>
          <option value="BANKNIFTY">BANKNIFTY</option>
        </select>
        <div style={{ display: 'flex', gap: 2, background: 'rgba(255,255,255,0.04)', borderRadius: 8, padding: 2, border: '1px solid rgba(255,255,255,0.06)' }}>
          {['weekly', 'monthly'].map(t => (
            <button key={t} onClick={() => setTenor(t)}
              style={{ padding: '4px 12px', fontSize: 11, fontWeight: 700, textTransform: 'capitalize', borderRadius: 6, border: 'none', cursor: 'pointer',
                background: tenor === t ? 'linear-gradient(135deg,#10b981,#2563eb)' : 'transparent',
                color: tenor === t ? '#0b1220' : '#cbd5e1' }}>
              {t}
            </button>
          ))}
        </div>
        <span style={{ fontSize: 11, color: '#cbd5e1' }}>Expiry <b style={{ color: '#f1f5f9' }}>{activeExpiry || '—'}</b></span>
        {data && <span style={{ fontSize: 11, color: '#cbd5e1' }}>Max Pain <b style={{ color: '#f59e0b' }}>{fmtInt(data.maxPain)}</b></span>}
        {data && <span style={{ fontSize: 11, color: '#cbd5e1' }}>Dealer <b style={{ color: data.dealerPositioning === 'long gamma' ? '#10b981' : '#ef5350' }}>{data.dealerPositioning}</b></span>}
        <span style={{ marginLeft: 'auto', display: 'flex', gap: 10, fontSize: 10, color: '#94a3b8' }}>
          <span style={{ display: 'flex', gap: 4, alignItems: 'center' }}><span style={{ width: 8, height: 8, borderRadius: 2, background: '#10b981' }} /> Call OI</span>
          <span style={{ display: 'flex', gap: 4, alignItems: 'center' }}><span style={{ width: 8, height: 8, borderRadius: 2, background: '#ef5350' }} /> Put OI</span>
        </span>
      </div>

      {loading && <div style={{ height: 340, display: 'grid', placeItems: 'center', color: '#94a3b8', fontSize: 12 }}>Loading live open interest…</div>}
      {!loading && error && <div style={{ height: 340, display: 'grid', placeItems: 'center', color: '#cbd5e1', fontSize: 12, textAlign: 'center', padding: 20 }}>
        <div>No data available<div style={{ fontSize: 10, color: '#94a3b8', marginTop: 6 }}>{error}</div></div>
      </div>}
      {!loading && !error && rows.length > 0 && (
        // Fixed medium-height box (doesn't grow with strike count); a wide chart
        // scrolls horizontally inside it instead of stretching the whole page.
        <div style={{ height: 340, overflowX: 'auto', overflowY: 'hidden', border: '1px solid rgba(255,255,255,0.06)', borderRadius: 10 }}>
          <div style={{ width: Math.max(560, rows.length * 46), height: 340 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={rows} margin={{ top: 12, right: 16, bottom: 28, left: 4 }} barGap={0} barCategoryGap="30%">
                <CartesianGrid strokeDasharray="3 3" stroke={gridColor} vertical={false} />
                <XAxis type="category" dataKey="strike" tick={{ fill: axisColor, fontSize: 10 }} stroke={gridColor} height={30} tickMargin={8} />
                <YAxis type="number" tickFormatter={fmtInt} tick={{ fill: axisColor, fontSize: 10 }} stroke={gridColor} width={54} />
                <Tooltip
                  contentStyle={{ background: isDark ? '#0d1b2a' : '#fff', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, fontSize: 11 }}
                  formatter={(value, name) => [fmtInt(value), name === 'peOiNeg' ? 'Put OI' : 'Call OI']}
                  labelFormatter={(strike) => `Strike ${strike}`}
                />
                <ReferenceLine y={0} stroke={axisColor} />
                {data?.maxPain != null && rows.some(r => r.strike === data.maxPain) && (
                  <ReferenceLine x={data.maxPain} stroke="#f59e0b" strokeDasharray="4 4" label={{ value: 'Max Pain', fill: '#f59e0b', fontSize: 10, position: 'top' }} />
                )}
                <Bar dataKey="ceOi" name="ceOi" fill="#10b981" radius={[3, 3, 0, 0]}>
                  {rows.map((r, i) => <Cell key={i} fillOpacity={r.strike === data?.maxPain ? 1 : 0.75} />)}
                </Bar>
                <Bar dataKey="peOiNeg" name="peOiNeg" fill="#ef5350" radius={[0, 0, 3, 3]}>
                  {rows.map((r, i) => <Cell key={i} fillOpacity={r.strike === data?.maxPain ? 1 : 0.75} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  )
}
