import React, { useEffect, useState } from 'react'
import { IconChart } from './icons.jsx'

const fmt = (n, d = 2) => n == null ? '—' : Number(n).toFixed(d)
const fmtVol = (n) => {
  if (n == null) return '—'
  if (n >= 1e7) return (n / 1e7).toFixed(1) + 'Cr'
  if (n >= 1e5) return (n / 1e5).toFixed(1) + 'L'
  if (n >= 1e3) return (n / 1e3).toFixed(1) + 'k'
  return String(n)
}

const SIGNAL_LABEL = { PDH: 'Prev-Day High Breakout', WHB: 'Weekly-High Breakout' }

export default function ETFScreener() {
  const apiBase = import.meta.env.VITE_API_URL || ''
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const [lastFetch, setLastFetch] = useState(null)

  useEffect(() => {
    let cancelled = false
    const load = () => {
      setLoading(true)
      fetch(`${apiBase}/api/etf/screener`)
        .then(async r => {
          const j = await r.json()
          if (!r.ok) throw new Error(j.detail || 'ETF screener unavailable')
          return j
        })
        .then(j => { if (!cancelled) { setData(j); setError(null); setLastFetch(new Date()) } })
        .catch(e => { if (!cancelled) setError(e.message) })
        .finally(() => { if (!cancelled) setLoading(false) })
    }
    load()
    const id = setInterval(load, 15000)
    return () => { cancelled = true; clearInterval(id) }
  }, [apiBase])

  const rows = data?.data || []
  const summary = data?.summary

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
        <IconChart style={{ color: 'var(--accent)' }} />
        <h2 style={{ fontSize: 13, fontWeight: 800, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--text2)', margin: 0 }}>ETF Screener</h2>
        {lastFetch && <span style={{ fontSize: 10, color: 'var(--text3)' }}>as of {lastFetch.toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata' })}</span>}
        {loading && data && <span style={{ fontSize: 10, color: 'var(--text3)' }}>● updating…</span>}
        <span style={{ marginLeft: 'auto', fontSize: 10, color: 'var(--text3)' }}>Live NSE ETFs via Kite — real quotes only</span>
      </div>

      {!data && loading && <div style={{ padding: 40, textAlign: 'center', color: 'var(--text3)' }}>Loading ETF screener…</div>}
      {!data && !loading && error && <div style={{ padding: 40, textAlign: 'center', color: 'var(--text2)' }}>No data available<div style={{ fontSize: 11, color: 'var(--text3)', marginTop: 6 }}>{error}</div></div>}

      {summary && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px,1fr))', gap: 8 }}>
          {[
            { label: 'Total ETFs', value: summary.totalEtfs },
            { label: 'Gainers', value: summary.gainers, color: 'var(--green)' },
            { label: 'Losers', value: summary.losers, color: 'var(--red)' },
            { label: 'Strong Breakouts', value: summary.strongBreakouts, color: 'var(--yellow)' },
            { label: 'Avg Change', value: `${summary.avgChangePct > 0 ? '+' : ''}${fmt(summary.avgChangePct)}%`, color: summary.avgChangePct >= 0 ? 'var(--green)' : 'var(--red)' },
            { label: 'Sentiment', value: summary.sentiment },
          ].map(s => (
            <div key={s.label} style={{ background: 'var(--bg2)', border: '1px solid var(--border)', borderRadius: 10, padding: 10 }}>
              <div style={{ fontSize: 9, fontWeight: 800, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--text3)' }}>{s.label}</div>
              <div style={{ fontSize: 16, fontWeight: 800, color: s.color || 'var(--text)' }}>{s.value ?? '—'}</div>
            </div>
          ))}
        </div>
      )}

      {rows.length > 0 && (
        <div style={{ background: 'var(--bg2)', border: '1px solid var(--border)', borderRadius: 14, overflow: 'auto', maxHeight: 560 }}>
          <table style={{ width: '100%', fontSize: 11, borderCollapse: 'collapse' }}>
            <thead style={{ position: 'sticky', top: 0, background: 'var(--bg3)', zIndex: 1 }}>
              <tr>
                {['ETF', 'Category', 'LTP', 'Chg %', 'Day High', 'Day Low', 'Volume', 'Score', 'Signals'].map(h => (
                  <th key={h} style={{ padding: '8px 10px', textAlign: 'left', color: 'var(--text3)', fontWeight: 700, borderBottom: '1px solid var(--border)' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map(r => {
                const isPos = r.changePct >= 0
                return (
                  <tr key={r.symbol} style={{ borderBottom: '1px solid var(--border)' }}>
                    <td className="mono" style={{ padding: '6px 10px', fontWeight: 700, color: 'var(--text)' }}>{r.symbol}</td>
                    <td style={{ padding: '6px 10px', color: 'var(--text3)' }}>{r.category}</td>
                    <td className="mono" style={{ padding: '6px 10px' }}>{fmt(r.ltp)}</td>
                    <td className="mono" style={{ padding: '6px 10px', color: isPos ? 'var(--green)' : 'var(--red)', fontWeight: 700 }}>{isPos ? '+' : ''}{fmt(r.changePct)}%</td>
                    <td className="mono" style={{ padding: '6px 10px' }}>{fmt(r.dayHigh)}</td>
                    <td className="mono" style={{ padding: '6px 10px' }}>{fmt(r.dayLow)}</td>
                    <td className="mono" style={{ padding: '6px 10px' }}>{fmtVol(r.volume)}</td>
                    <td className="mono" style={{ padding: '6px 10px', fontWeight: 700, color: r.etfScore >= 60 ? 'var(--yellow)' : 'var(--text2)' }}>{fmt(r.etfScore, 0)}</td>
                    <td style={{ padding: '6px 10px' }}>
                      {r.signals?.length ? r.signals.map(s => (
                        <span key={s} title={SIGNAL_LABEL[s] || s} style={{ fontSize: 9, fontWeight: 800, padding: '2px 6px', borderRadius: 999, background: 'rgba(245,158,11,0.15)', color: 'var(--yellow)', marginRight: 4 }}>{s}</span>
                      )) : <span style={{ color: 'var(--text3)' }}>—</span>}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
