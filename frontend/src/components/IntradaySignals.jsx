import React, { useEffect, useState } from 'react'

const safeFetch = async (url) => {
  try {
    const r = await fetch(url)
    const j = await r.json()
    if (!r.ok || j?.detail) return null
    return j
  } catch { return null }
}

const fmt = (n, d = 2) => (n == null ? '—' : Number(n).toFixed(d))

const STATUS_COLOR = {
  CONFIRMED: '#10b981', TRIGGERED: '#10b981',
  PENDING_RETEST: '#f59e0b', WEAK_BREAK: '#f59e0b', WEAK: '#f59e0b',
  FAILED: '#ef5350',
  WATCHING: '#64748b', NOT_APPLICABLE: '#475569',
}

function Pill({ status }) {
  const color = STATUS_COLOR[status] || '#94a3b8'
  return <span style={{ fontSize: 9, fontWeight: 800, padding: '2px 8px', borderRadius: 999, background: `${color}22`, color, border: `1px solid ${color}44` }}>{status}</span>
}

function TradeRow({ s }) {
  const dirColor = s.direction === 'long' ? '#10b981' : '#ef5350'
  return (
    <div style={{ display: 'flex', gap: 10, alignItems: 'center', padding: '8px 10px', borderRadius: 10, background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.05)', flexWrap: 'wrap' }}>
      <span style={{ fontWeight: 800, fontSize: 12, color: '#f1f5f9', minWidth: 90 }}>{s.symbol}</span>
      <span style={{ fontSize: 10, fontWeight: 800, color: dirColor, textTransform: 'uppercase' }}>{s.direction}</span>
      <Pill status={s.status} />
      {s.entry != null && <span className="mono" style={{ fontSize: 11, color: '#cbd5e1' }}>Entry {fmt(s.entry)}</span>}
      {s.stop != null && <span className="mono" style={{ fontSize: 11, color: '#ef5350' }}>Stop {fmt(s.stop)}</span>}
      {s.target1 != null && <span className="mono" style={{ fontSize: 11, color: '#10b981' }}>T1 {fmt(s.target1)}</span>}
      {s.target2 != null && <span className="mono" style={{ fontSize: 11, color: '#10b981' }}>T2 {fmt(s.target2)}</span>}
      {s.score != null && <span className="mono" style={{ fontSize: 10, color: '#2563eb', fontWeight: 700, marginLeft: 'auto' }}>Score {fmt(s.score, 0)}</span>}
      <div style={{ fontSize: 10, color: '#94a3b8', width: '100%' }}>{s.reason}</div>
    </div>
  )
}

function StrategyCard({ title, description, watchingCount, hitRate, rows }) {
  return (
    <div style={{ background: 'rgba(13,27,42,0.6)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: 14, padding: 14, display: 'flex', flexDirection: 'column', gap: 8 }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, flexWrap: 'wrap' }}>
        <div style={{ fontSize: 11, fontWeight: 800, letterSpacing: '0.06em', textTransform: 'uppercase', color: '#cbd5e1' }}>{title}</div>
        <div style={{ fontSize: 10, color: '#64748b' }}>{description}</div>
        <div style={{ marginLeft: 'auto', fontSize: 10, color: '#94a3b8' }}>
          {watchingCount != null && <span>{watchingCount} watching · </span>}
          {hitRate && hitRate.sample_size > 0
            ? <span style={{ color: hitRate.win_rate_pct >= 50 ? '#10b981' : '#ef5350', fontWeight: 700 }}>
                Session hit-rate {hitRate.win_rate_pct}% (n={hitRate.sample_size}{hitRate.provisional ? ', provisional' : ''})
              </span>
            : <span>no completed trades yet today</span>}
        </div>
      </div>
      {rows.length === 0
        ? <div style={{ fontSize: 11, color: '#475569', textAlign: 'center', padding: '10px 0' }}>No live signals right now</div>
        : <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>{rows.map((s, i) => <TradeRow key={s.symbol + i} s={s} />)}</div>}
    </div>
  )
}

const STRATEGY_META = {
  orb15: { title: 'ORB 15-min', description: 'opening-range-15 breakout, RVOL≥1.2x' },
  vwap_reversion: { title: 'VWAP Reversion', description: 'mean-revert to VWAP in range regime (ADX<20)' },
  supertrend_flip: { title: 'Supertrend Flip', description: 'momentum entry on a fresh Supertrend flip' },
  gap_classifier: { title: 'Gap-and-Go / Gap Fade', description: 'continuation vs reversal on the day\'s open gap' },
  vwap_pullback: { title: 'First VWAP Pullback', description: 'first pullback to VWAP after a strong directional open' },
}

export default function IntradaySignals() {
  const apiBase = import.meta.env.VITE_API_URL || ''
  const [breaker, setBreaker] = useState(null)
  const [intraday, setIntraday] = useState(null)
  const [note, setNote] = useState('')
  const [lastFetch, setLastFetch] = useState(null)

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      const [b, i] = await Promise.all([
        safeFetch(`${apiBase}/api/signals/breaker?min_score=0`),
        safeFetch(`${apiBase}/api/signals/intraday`),
      ])
      if (cancelled) return
      setBreaker(b)
      setIntraday(i)
      if (i?.note) setNote(i.note)
      setLastFetch(new Date())
    }
    load()
    const t = setInterval(load, 5000)
    return () => { cancelled = true; clearInterval(t) }
  }, [apiBase])

  const breakerRows = (breaker?.data || []).map(s => ({ ...s, score: s.score }))
  const strategies = intraday?.strategies || {}

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
        <h2 style={{ fontSize: 13, fontWeight: 800, letterSpacing: '0.06em', textTransform: 'uppercase', color: '#cbd5e1', margin: 0 }}>Intraday Signals</h2>
        <span style={{ fontSize: 10, color: '#64748b' }}>{lastFetch ? `updated ${lastFetch.toLocaleTimeString()}` : 'loading…'}</span>
      </div>

      <div style={{ background: 'rgba(13,27,42,0.6)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: 14, padding: 14, display: 'flex', flexDirection: 'column', gap: 8 }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, flexWrap: 'wrap' }}>
          <div style={{ fontSize: 11, fontWeight: 800, letterSpacing: '0.06em', textTransform: 'uppercase', color: '#cbd5e1' }}>OHLC Breaker</div>
          <div style={{ fontSize: 10, color: '#64748b' }}>prior-day / opening-range breakout, gated RVOL≥1.5x &amp; ADX≥20, retest-and-hold confirmed</div>
        </div>
        {!breaker
          ? <div style={{ fontSize: 11, color: '#475569', textAlign: 'center', padding: '10px 0' }}>Loading…</div>
          : breakerRows.length === 0
            ? <div style={{ fontSize: 11, color: '#475569', textAlign: 'center', padding: '10px 0' }}>No breakout candidates right now</div>
            : <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>{breakerRows.map((s, i) => <TradeRow key={s.symbol + i} s={{ ...s, reason: `${s.status} at ${fmt(s.level)} · RVOL ${fmt(s.rvol)}x · ADX ${fmt(s.adx, 1)}` }} />)}</div>}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: 14 }}>
        {Object.keys(STRATEGY_META).map(name => {
          const meta = STRATEGY_META[name]
          const payload = strategies[name]
          return (
            <StrategyCard key={name} title={meta.title} description={meta.description}
              watchingCount={payload?.watching_count}
              hitRate={payload?.hit_rate}
              rows={payload?.triggered || []} />
          )
        })}
      </div>

      {note && <div style={{ fontSize: 10, color: '#64748b', fontStyle: 'italic' }}>{note}</div>}
    </div>
  )
}
