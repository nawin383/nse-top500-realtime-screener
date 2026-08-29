import React, { useEffect, useState } from 'react'
import { IconBuilding } from './icons.jsx'

const fmt = (n, d = 2) => n == null ? '—' : Number(n).toFixed(d)
const fmtCap = (n) => {
  if (n == null) return '—'
  if (n >= 1e12) return (n / 1e12).toFixed(1) + 'T'
  if (n >= 1e9) return (n / 1e9).toFixed(1) + 'B'
  if (n >= 1e6) return (n / 1e6).toFixed(1) + 'M'
  return String(n)
}

const CATEGORY_COLOR = {
  'CONVICTION BUY': 'var(--green)', 'STRONG BUY': 'var(--green)', 'BUY': '#64b5f6',
  'HOLD': 'var(--yellow)', 'WEAK HOLD': '#f59e0b', 'AVOID': 'var(--red)',
}

// Reads the once-a-day cached scan (backend/app/analytics/elite_quant.py) --
// this is deliberately NOT live data. yfinance can't serve a per-request
// scan across a 100-symbol universe with 5 years of history each, so the
// backend runs it once a day in the background and this just displays
// whatever the last run produced, with an honest "as of" timestamp and, if
// no run has completed yet, a plain explanation rather than a fake loading
// spinner that never resolves.
export default function EliteQuantScreener() {
  const apiBase = import.meta.env.VITE_API_URL || ''
  const [market, setMarket] = useState('IN')
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [expanded, setExpanded] = useState(null)

  useEffect(() => {
    let cancelled = false
    setData(null)
    setError(null)
    fetch(`${apiBase}/api/analytics/elite-quant?market=${market}&limit=100`)
      .then(async r => {
        const j = await r.json()
        if (!r.ok) throw new Error(j.detail || 'unavailable')
        return j
      })
      .then(j => { if (!cancelled) setData(j) })
      .catch(e => { if (!cancelled) setError(e.message) })
    return () => { cancelled = true }
  }, [market, apiBase])

  const rows = data?.rows || []

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
        <IconBuilding style={{ color: 'var(--accent)' }} />
        <h2 style={{ fontSize: 13, fontWeight: 800, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--text2)', margin: 0 }}>Elite Quant Screener</h2>
        <div style={{ display: 'flex', gap: 2, background: 'var(--bg3)', borderRadius: 8, padding: 2, border: '1px solid var(--border)' }}>
          {[{ k: 'IN', label: 'India' }, { k: 'US', label: 'United States' }].map(m => (
            <button key={m.k} onClick={() => setMarket(m.k)} aria-pressed={market === m.k}
              style={{ padding: '5px 12px', fontSize: 11, fontWeight: 700, borderRadius: 6, border: 'none', cursor: 'pointer', background: market === m.k ? 'linear-gradient(135deg,var(--accent),var(--accent-light))' : 'transparent', color: market === m.k ? '#04101f' : 'var(--text2)' }}>{m.label}</button>
          ))}
        </div>
        {data?.available && <span style={{ fontSize: 10, color: 'var(--text3)' }}>as of {new Date(data.generatedAt).toLocaleString('en-IN')} · {data.analyzed}/{data.universeSize} analyzed</span>}
        <span style={{ marginLeft: 'auto', fontSize: 9, color: 'var(--text3)' }}>Runs once/day from 5y history + fundamentals — not investment advice</span>
      </div>

      {!data && !error && <div style={{ padding: 40, textAlign: 'center', color: 'var(--text3)' }}>Loading…</div>}
      {data && !data.available && (
        <div style={{ padding: 40, textAlign: 'center', color: 'var(--text2)', background: 'var(--bg2)', border: '1px solid var(--border)', borderRadius: 14 }}>
          No scan available for this market yet
          <div style={{ fontSize: 11, color: 'var(--text3)', marginTop: 6 }}>{data.reason}</div>
        </div>
      )}
      {error && <div style={{ padding: 40, textAlign: 'center', color: 'var(--text2)' }}>Unable to load<div style={{ fontSize: 11, color: 'var(--text3)', marginTop: 6 }}>{error}</div></div>}

      {rows.length > 0 && (
        <div style={{ background: 'var(--bg2)', border: '1px solid var(--border)', borderRadius: 14, overflow: 'auto', maxHeight: 640 }}>
          <table style={{ width: '100%', fontSize: 11, borderCollapse: 'collapse' }}>
            <thead style={{ position: 'sticky', top: 0, background: 'var(--bg3)', zIndex: 1 }}>
              <tr>
                {['Symbol', 'Sector', 'Price', 'Mkt Cap', 'Elite Score', 'HF Appeal', 'ROE %', 'Rev Growth %', 'Sharpe', 'Max DD %', 'Beta', 'Risk', 'Thesis'].map(h => (
                  <th key={h} style={{ padding: '8px 10px', textAlign: 'left', color: 'var(--text3)', fontWeight: 700, borderBottom: '1px solid var(--border)', whiteSpace: 'nowrap' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map(r => (
                <tr key={r.symbol} style={{ borderBottom: '1px solid var(--border)' }}>
                  <td className="mono" style={{ padding: '6px 10px', fontWeight: 700, color: 'var(--text)' }}>{r.symbol}</td>
                  <td style={{ padding: '6px 10px', color: 'var(--text3)', whiteSpace: 'nowrap' }}>{r.sector}</td>
                  <td className="mono" style={{ padding: '6px 10px' }}>{fmt(r.price)}</td>
                  <td className="mono" style={{ padding: '6px 10px' }}>{fmtCap(r.marketCap)}</td>
                  <td className="mono" style={{ padding: '6px 10px', fontWeight: 800, color: r.eliteComposite >= 7 ? 'var(--green)' : r.eliteComposite >= 5 ? 'var(--yellow)' : 'var(--text2)' }}>{fmt(r.eliteComposite, 1)}</td>
                  <td className="mono" style={{ padding: '6px 10px' }}>{fmt(r.hedgeFundAppeal, 1)}</td>
                  <td className="mono" style={{ padding: '6px 10px', color: (r.roe || 0) > 15 ? 'var(--green)' : 'var(--text2)' }}>{fmt(r.roe, 1)}</td>
                  <td className="mono" style={{ padding: '6px 10px', color: (r.revenueGrowth || 0) > 10 ? 'var(--green)' : 'var(--text2)' }}>{fmt(r.revenueGrowth, 1)}</td>
                  <td className="mono" style={{ padding: '6px 10px' }}>{fmt(r.sharpeRatio)}</td>
                  <td className="mono" style={{ padding: '6px 10px', color: 'var(--red)' }}>{fmt(r.maxDrawdownPct, 1)}</td>
                  <td className="mono" style={{ padding: '6px 10px' }}>{fmt(r.beta)}</td>
                  <td style={{ padding: '6px 10px' }}><span style={{ fontSize: 9, fontWeight: 800, padding: '2px 6px', borderRadius: 999, background: 'rgba(255,255,255,0.06)', color: 'var(--text2)' }}>{r.riskLevel}</span></td>
                  <td style={{ padding: '6px 10px', maxWidth: 260, cursor: 'pointer' }} onClick={() => setExpanded(expanded === r.symbol ? null : r.symbol)}>
                    <span style={{ fontSize: 9, fontWeight: 800, padding: '2px 6px', borderRadius: 999, background: `${CATEGORY_COLOR[r.category] || 'var(--text3)'}22`, color: CATEGORY_COLOR[r.category] || 'var(--text3)', marginRight: 6 }}>{r.category}</span>
                    {expanded === r.symbol ? (
                      <div style={{ marginTop: 4, color: 'var(--text2)', whiteSpace: 'normal' }}>
                        {r.thesis}
                        <div style={{ marginTop: 4, color: 'var(--text3)', fontSize: 10 }}>Position {r.positionSize} · Horizon {r.timeHorizon} · Catalysts: {r.catalysts}</div>
                      </div>
                    ) : (
                      <span style={{ color: 'var(--text3)', overflow: 'hidden', textOverflow: 'ellipsis' }}>Click to expand</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
