import React, { useEffect, useMemo, useState } from 'react'
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

const CATEGORIES = ['CONVICTION BUY', 'STRONG BUY', 'BUY', 'HOLD', 'WEAK HOLD', 'AVOID']
const RISK_LEVELS = ['LOW', 'MEDIUM', 'MEDIUM-HIGH', 'HIGH']
const MAX_RENDERED_ROWS = 500

const COLUMNS = [
  { key: 'symbol', label: 'Symbol' }, { key: 'sector', label: 'Sector' },
  { key: 'price', label: 'Price' }, { key: 'marketCap', label: 'Mkt Cap' },
  { key: 'eliteComposite', label: 'Elite Score' }, { key: 'hedgeFundAppeal', label: 'HF Appeal' },
  { key: 'roe', label: 'ROE %' }, { key: 'revenueGrowth', label: 'Rev Growth %' },
  { key: 'sharpeRatio', label: 'Sharpe' }, { key: 'maxDrawdownPct', label: 'Max DD %' },
  { key: 'beta', label: 'Beta' }, { key: 'riskLevel', label: 'Risk' }, { key: 'thesis', label: 'Thesis' },
]

const REC_SECTIONS = [
  { key: 'convictionBuys', label: 'Conviction Buys', metric: null, suffix: '' },
  { key: 'bestRiskAdjusted', label: 'Best Risk-Adjusted', metric: 'sharpeRatio', suffix: ' Sharpe' },
  { key: 'momentumLeaders', label: 'Momentum Leaders', metric: 'momentum3m', suffix: '' },
  { key: 'valuePicks', label: 'Value Picks', metric: 'peRatio', suffix: ' PE' },
  { key: 'lowDrawdownQuality', label: 'Defensive Quality', metric: 'maxDrawdownPct', suffix: '% DD' },
]

function RecommendationCard({ item, metric, suffix }) {
  return (
    <div style={{ minWidth: 130, flex: '0 0 auto', background: 'var(--bg3)', border: '1px solid var(--border)', borderRadius: 10, padding: '8px 10px' }}>
      <div className="mono" style={{ fontWeight: 800, fontSize: 12, color: 'var(--text)' }}>{item.symbol}</div>
      <div style={{ fontSize: 9, color: 'var(--text3)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{item.sector || '—'}</div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4 }}>
        <span style={{ fontSize: 9, fontWeight: 800, padding: '1px 5px', borderRadius: 999, background: `${CATEGORY_COLOR[item.category] || 'var(--text3)'}22`, color: CATEGORY_COLOR[item.category] || 'var(--text3)' }}>{item.category || '—'}</span>
        {metric && <span className="mono" style={{ fontSize: 10, color: 'var(--text2)' }}>{fmt(item[metric], metric === 'momentum3m' ? 3 : 1)}{suffix}</span>}
      </div>
    </div>
  )
}

function RecommendationStrips({ recommendations }) {
  if (!recommendations) return null
  const sections = REC_SECTIONS.filter(s => (recommendations[s.key] || []).length > 0)
  if (!sections.length) return null
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {sections.map(s => (
        <div key={s.key}>
          <div style={{ fontSize: 10, fontWeight: 800, letterSpacing: '0.05em', textTransform: 'uppercase', color: 'var(--text3)', marginBottom: 4 }}>{s.label}</div>
          <div style={{ display: 'flex', gap: 6, overflowX: 'auto', paddingBottom: 2 }}>
            {recommendations[s.key].map(item => <RecommendationCard key={s.key + item.symbol} item={item} metric={s.metric} suffix={s.suffix} />)}
          </div>
        </div>
      ))}
    </div>
  )
}

// Reads the once-a-day cached scan (backend/app/analytics/elite_quant.py) --
// this is deliberately NOT live data. yfinance can't serve a per-request
// scan across a multi-thousand-symbol universe with 5 years of history
// each, so the backend runs it once a day in the background (now over the
// real full NSE equity list + a broad real US-listed universe, not a
// hand-picked top 100) and this just displays whatever the last run
// produced, with an honest "as of" timestamp and, if no run has completed
// yet, a plain explanation rather than a fake loading spinner that never
// resolves.
export default function EliteQuantScreener() {
  const apiBase = import.meta.env.VITE_API_URL || ''
  const [market, setMarket] = useState('IN')
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [expanded, setExpanded] = useState(null)
  const [search, setSearch] = useState('')
  const [sector, setSector] = useState('')
  const [category, setCategory] = useState('')
  const [riskLevel, setRiskLevel] = useState('')
  const [minScore, setMinScore] = useState(0)
  const [sort, setSort] = useState({ key: 'eliteComposite', dir: -1 })

  useEffect(() => {
    let cancelled = false
    setData(null)
    setError(null)
    setSearch(''); setSector(''); setCategory(''); setRiskLevel(''); setMinScore(0)
    fetch(`${apiBase}/api/analytics/elite-quant?market=${market}&limit=5000`)
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

  const sectors = useMemo(() => [...new Set(rows.map(r => r.sector).filter(Boolean))].sort(), [rows])

  const filteredRows = useMemo(() => {
    const q = search.trim().toUpperCase()
    let out = rows.filter(r =>
      (!q || r.symbol.includes(q)) &&
      (!sector || r.sector === sector) &&
      (!category || r.category === category) &&
      (!riskLevel || r.riskLevel === riskLevel) &&
      ((r.eliteComposite ?? 0) >= minScore)
    )
    out.sort((a, b) => {
      const av = a[sort.key], bv = b[sort.key]
      if (av == null && bv == null) return 0
      if (av == null) return 1
      if (bv == null) return -1
      if (typeof av === 'string') return sort.dir * av.localeCompare(bv)
      return sort.dir * (av - bv)
    })
    return out
  }, [rows, search, sector, category, riskLevel, minScore, sort])

  const shownRows = filteredRows.slice(0, MAX_RENDERED_ROWS)

  const toggleSort = (key) => setSort(s => s.key === key ? { key, dir: -s.dir } : { key, dir: -1 })

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
        {data?.available && (
          <span style={{ fontSize: 10, color: 'var(--text3)' }}>
            {data.partial ? '⏳ scan in progress — ' : ''}as of {new Date(data.generatedAt).toLocaleString('en-IN')} · {data.analyzed}/{data.universeSize} analyzed
          </span>
        )}
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

      {data?.available && <RecommendationStrips recommendations={data.recommendations} />}

      {rows.length > 0 && (
        <>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center', background: 'var(--bg2)', border: '1px solid var(--border)', borderRadius: 10, padding: 8 }}>
            <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search symbol…"
              style={{ background: 'var(--bg3)', border: '1px solid var(--border)', borderRadius: 6, padding: '5px 8px', fontSize: 11, color: 'var(--text)', width: 120 }} />
            <select value={sector} onChange={e => setSector(e.target.value)} style={{ background: 'var(--bg3)', border: '1px solid var(--border)', borderRadius: 6, padding: '5px 8px', fontSize: 11, color: 'var(--text)' }}>
              <option value="">All sectors</option>
              {sectors.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
            <select value={category} onChange={e => setCategory(e.target.value)} style={{ background: 'var(--bg3)', border: '1px solid var(--border)', borderRadius: 6, padding: '5px 8px', fontSize: 11, color: 'var(--text)' }}>
              <option value="">All categories</option>
              {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
            <select value={riskLevel} onChange={e => setRiskLevel(e.target.value)} style={{ background: 'var(--bg3)', border: '1px solid var(--border)', borderRadius: 6, padding: '5px 8px', fontSize: 11, color: 'var(--text)' }}>
              <option value="">All risk levels</option>
              {RISK_LEVELS.map(r => <option key={r} value={r}>{r}</option>)}
            </select>
            <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: 'var(--text2)' }}>
              Min score
              <input type="number" min={0} max={10} step={0.5} value={minScore} onChange={e => setMinScore(Number(e.target.value) || 0)}
                style={{ width: 48, background: 'var(--bg3)', border: '1px solid var(--border)', borderRadius: 6, padding: '4px 6px', fontSize: 11, color: 'var(--text)' }} />
            </label>
            <span style={{ marginLeft: 'auto', fontSize: 10, color: 'var(--text3)' }}>
              {filteredRows.length} match{filteredRows.length === 1 ? '' : 'es'}{filteredRows.length > MAX_RENDERED_ROWS ? ` (showing top ${MAX_RENDERED_ROWS} by ${sort.key})` : ''}
            </span>
          </div>

          <div style={{ background: 'var(--bg2)', border: '1px solid var(--border)', borderRadius: 14, overflow: 'auto', maxHeight: 640 }}>
            <table style={{ width: '100%', fontSize: 11, borderCollapse: 'collapse' }}>
              <thead style={{ position: 'sticky', top: 0, background: 'var(--bg3)', zIndex: 1 }}>
                <tr>
                  {COLUMNS.map(c => (
                    <th key={c.key} onClick={() => c.key !== 'thesis' && toggleSort(c.key)}
                      style={{ padding: '8px 10px', textAlign: 'left', color: sort.key === c.key ? 'var(--accent)' : 'var(--text3)', fontWeight: 700, borderBottom: '1px solid var(--border)', whiteSpace: 'nowrap', cursor: c.key === 'thesis' ? 'default' : 'pointer', userSelect: 'none' }}>
                      {c.label}{sort.key === c.key ? (sort.dir === -1 ? ' ▼' : ' ▲') : ''}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {shownRows.map(r => (
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
        </>
      )}
    </div>
  )
}
