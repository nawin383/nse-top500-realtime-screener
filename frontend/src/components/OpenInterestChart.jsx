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
    return data.heatmap.map(r => ({ ...r, ceOiNeg: r.ceOi, peOiNeg: -r.peOi })).sort((a, b) => a.strike - b.strike)
  }, [data])

  const isDark = theme !== 'light'
  const axisColor = isDark ? '#5b728c' : '#64748b'
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
                background: tenor === t ? 'linear-gradient(135deg,#00e6a0,#2f8bff)' : 'transparent',
                color: tenor === t ? '#0a0e13' : '#8ea0b8' }}>
              {t}
            </button>
          ))}
        </div>
        <span style={{ fontSize: 11, color: '#8ea0b8' }}>Expiry <b style={{ color: '#eef4ff' }}>{activeExpiry || '—'}</b></span>
        {data && <span style={{ fontSize: 11, color: '#8ea0b8' }}>Max Pain <b style={{ color: '#ffb020' }}>{fmtInt(data.maxPain)}</b></span>}
        {data && <span style={{ fontSize: 11, color: '#8ea0b8' }}>Dealer <b style={{ color: data.dealerPositioning === 'long gamma' ? '#00e6a0' : '#ff3b4a' }}>{data.dealerPositioning}</b></span>}
        <span style={{ marginLeft: 'auto', display: 'flex', gap: 10, fontSize: 10, color: '#5b728c' }}>
          <span style={{ display: 'flex', gap: 4, alignItems: 'center' }}><span style={{ width: 8, height: 8, borderRadius: 2, background: '#00e6a0' }} /> Call OI</span>
          <span style={{ display: 'flex', gap: 4, alignItems: 'center' }}><span style={{ width: 8, height: 8, borderRadius: 2, background: '#ff3b4a' }} /> Put OI</span>
        </span>
      </div>

      {loading && <div style={{ flex: 1, display: 'grid', placeItems: 'center', color: '#5b728c', fontSize: 12 }}>Loading live open interest…</div>}
      {!loading && error && <div style={{ flex: 1, display: 'grid', placeItems: 'center', color: '#8ea0b8', fontSize: 12, textAlign: 'center', padding: 20 }}>
        <div>No data available<div style={{ fontSize: 10, color: '#5b728c', marginTop: 6 }}>{error}</div></div>
      </div>}
      {!loading && !error && rows.length > 0 && (
        <ResponsiveContainer width="100%" height={Math.max(320, rows.length * 22)}>
          <BarChart data={rows} layout="vertical" margin={{ top: 4, right: 24, bottom: 4, left: 4 }} barGap={0} barCategoryGap="18%">
            <CartesianGrid strokeDasharray="3 3" stroke={gridColor} horizontal={false} />
            <XAxis type="number" tickFormatter={fmtInt} tick={{ fill: axisColor, fontSize: 10 }} stroke={gridColor} />
            <YAxis type="category" dataKey="strike" tick={{ fill: axisColor, fontSize: 10 }} stroke={gridColor} width={56} />
            <Tooltip
              contentStyle={{ background: isDark ? '#0f1a24' : '#fff', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, fontSize: 11 }}
              formatter={(value, name) => [fmtInt(value), name === 'peOiNeg' ? 'Put OI' : 'Call OI']}
              labelFormatter={(strike) => `Strike ${strike}`}
            />
            <ReferenceLine x={0} stroke={axisColor} />
            {data?.maxPain != null && (
              <ReferenceLine y={data.maxPain} stroke="#ffb020" strokeDasharray="4 4" ifOverflow="extendDomain" label={{ value: 'Max Pain', fill: '#ffb020', fontSize: 10, position: 'insideTopRight' }} />
            )}
            <Bar dataKey="peOiNeg" name="peOiNeg" fill="#ff3b4a" radius={[3, 0, 0, 3]}>
              {rows.map((r, i) => <Cell key={i} fillOpacity={r.strike === data?.maxPain ? 1 : 0.75} />)}
            </Bar>
            <Bar dataKey="ceOiNeg" name="ceOiNeg" fill="#00e6a0" radius={[0, 3, 3, 0]}>
              {rows.map((r, i) => <Cell key={i} fillOpacity={r.strike === data?.maxPain ? 1 : 0.75} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}
