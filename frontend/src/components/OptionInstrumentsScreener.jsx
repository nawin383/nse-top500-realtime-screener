import React, { useEffect, useState } from 'react'

const fmt = (n, d=2) => n==null ? '—' : Number(n).toFixed(d)
const fmtInt = (n) => n==null ? '—' : Number(n).toLocaleString('en-IN')

const BUILDUP_LABEL = {
  long_buildup: { label: 'Long Buildup', color: '#10b981' },
  short_buildup: { label: 'Short Buildup', color: '#ef5350' },
  short_covering: { label: 'Short Covering', color: '#64b5f6' },
  long_unwinding: { label: 'Long Unwinding', color: '#f59e0b' },
}

export default function OptionInstrumentsScreener() {
  const apiBase = import.meta.env.VITE_API_URL || ''
  const [underlying, setUnderlying] = useState('')
  const [optionType, setOptionType] = useState('')
  const [search, setSearch] = useState('')
  const [sortBy, setSortBy] = useState('oi_change_pct')
  const [order, setOrder] = useState('desc')
  const [rows, setRows] = useState([])
  const [count, setCount] = useState(0)
  const [lastFetch, setLastFetch] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    let cancelled = false
    const load = () => {
      setLoading(true)
      const params = new URLSearchParams({ sort_by: sortBy, order, limit: '200' })
      if (underlying) params.set('underlying', underlying)
      if (optionType) params.set('option_type', optionType)
      if (search) params.set('search', search)
      fetch(`${apiBase}/api/options/instruments-screener?${params}`)
        .then(r => r.json())
        .then(j => { if (cancelled) return; setRows(j.data || []); setCount(j.count || 0); setLastFetch(new Date()) })
        .catch(() => {})
        .finally(() => { if (!cancelled) setLoading(false) })
    }
    load()
    const id = setInterval(load, 5000)
    return () => { cancelled = true; clearInterval(id) }
  }, [underlying, optionType, search, sortBy, order, apiBase])

  const thClick = (key) => {
    if (sortBy === key) setOrder(o => o === 'desc' ? 'asc' : 'desc')
    else { setSortBy(key); setOrder('desc') }
  }

  const cols = [
    { key: 'symbol', label: 'Contract' },
    { key: 'ltp', label: 'LTP' },
    { key: 'change_pct', label: 'Chg %' },
    { key: 'volume', label: 'Volume' },
    { key: 'oi', label: 'OI' },
    { key: 'oi_change_pct', label: 'OI Chg %' },
  ]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
        <h2 style={{ fontSize: 13, fontWeight: 800, letterSpacing: '0.06em', textTransform: 'uppercase', color: '#cbd5e1', margin: 0 }}>Option Instruments</h2>
        <span style={{ fontSize: 10, color: '#64748b' }}>{lastFetch ? `as of ${lastFetch.toLocaleTimeString('en-IN',{timeZone:'Asia/Kolkata'})}` : 'loading…'}</span>
        <span style={{ fontSize: 10, color: '#64748b' }}>{count} contracts</span>
      </div>

      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
        <select className="input" value={underlying} onChange={e => setUnderlying(e.target.value)} style={{ fontSize: 11 }}>
          <option value="">All Underlyings</option>
          <option value="NIFTY">NIFTY</option>
          <option value="SENSEX">SENSEX</option>
        </select>
        <select className="input" value={optionType} onChange={e => setOptionType(e.target.value)} style={{ fontSize: 11 }}>
          <option value="">CE + PE</option>
          <option value="CE">CE only</option>
          <option value="PE">PE only</option>
        </select>
        <input className="input" placeholder="Search contract symbol" value={search} onChange={e => setSearch(e.target.value)} style={{ fontSize: 11, minWidth: 200 }} />
        <span style={{ fontSize: 10, color: '#94a3b8', marginLeft: 'auto' }}>Live NIFTY/SENSEX contracts, separate from the equity screener — WS-fed, OI buildup real-time</span>
      </div>

      <div style={{ background: 'rgba(13,27,42,0.6)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: 14, overflow: 'auto', maxHeight: 560 }}>
        <table style={{ width: '100%', fontSize: 11, borderCollapse: 'collapse' }}>
          <thead style={{ position: 'sticky', top: 0, background: 'rgba(13,27,42,0.98)', zIndex: 1 }}>
            <tr>
              {cols.map(c => (
                <th key={c.key} onClick={() => thClick(c.key)} style={{ padding: '8px 10px', textAlign: 'left', color: '#94a3b8', fontWeight: 700, cursor: 'pointer', borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                  {c.label} {sortBy === c.key ? (order === 'desc' ? '▼' : '▲') : ''}
                </th>
              ))}
              <th style={{ padding: '8px 10px', textAlign: 'left', color: '#94a3b8', fontWeight: 700, borderBottom: '1px solid rgba(255,255,255,0.06)' }}>Buildup</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(r => {
              const isPos = (r.change_pct || 0) >= 0
              const buildup = r.oi_buildup ? BUILDUP_LABEL[r.oi_buildup] : null
              return (
                <tr key={r.symbol} style={{ borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                  <td className="mono" style={{ padding: '6px 10px', fontWeight: 700, color: '#f1f5f9' }}>{r.symbol}</td>
                  <td className="mono" style={{ padding: '6px 10px' }}>{fmt(r.ltp)}</td>
                  <td className="mono" style={{ padding: '6px 10px', color: isPos ? '#10b981' : '#ef5350', fontWeight: 700 }}>{r.change_pct != null ? `${isPos?'+':''}${fmt(r.change_pct)}%` : '—'}</td>
                  <td className="mono" style={{ padding: '6px 10px' }}>{fmtInt(r.volume)}</td>
                  <td className="mono" style={{ padding: '6px 10px' }}>{fmtInt(r.oi)}</td>
                  <td className="mono" style={{ padding: '6px 10px', color: (r.oi_change_pct||0) >= 0 ? '#10b981' : '#ef5350' }}>{r.oi_change_pct != null ? `${fmt(r.oi_change_pct)}%` : '—'}</td>
                  <td style={{ padding: '6px 10px' }}>{buildup ? <span style={{ fontSize: 9, fontWeight: 800, padding: '2px 7px', borderRadius: 999, background: `${buildup.color}22`, color: buildup.color }}>{buildup.label}</span> : <span style={{ color: '#475569' }}>—</span>}</td>
                </tr>
              )
            })}
            {rows.length === 0 && !loading && (
              <tr><td colSpan={7} style={{ padding: 24, textAlign: 'center', color: '#94a3b8' }}>No live option contracts yet (WS not subscribed, or market closed)</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
