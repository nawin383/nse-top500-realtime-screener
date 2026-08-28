import React, { useEffect, useState } from 'react'
import { Card, Empty, fmt } from './shared.jsx'

const CLASS_COLOR = { EXTREME: 'var(--red)', HIGH: '#f59e0b', MODERATE: 'var(--yellow)', LOW: '#64b5f6', MINIMAL: 'var(--text3)' }

// Real Kite historical-candle analysis of India VIX's first 10 minutes of
// trading, over the last N sessions -- ported from a local batch script, now
// a live backend endpoint (cached for the day it's computed).
export default function VixOpenVolatility() {
  const apiBase = import.meta.env.VITE_API_URL || ''
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    fetch(`${apiBase}/api/analytics/vix-open-volatility?days=60`)
      .then(async r => {
        const j = await r.json()
        if (!r.ok) throw new Error(j.detail || 'unavailable')
        return j
      })
      .then(j => { if (!cancelled) { if (j.available) setData(j); else setError(j.reason || 'unavailable') } })
      .catch(e => { if (!cancelled) setError(e.message) })
    return () => { cancelled = true }
  }, [apiBase])

  return (
    <Card title="India VIX — First 10 Minutes Volatility">
      {!data && !error && <div style={{ fontSize: 11, color: 'var(--text3)' }}>Loading (analyzing up to 60 sessions)…</div>}
      {!data && error && <Empty label={error} />}
      {data && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', fontSize: 11 }}>
            <span>Avg open <b style={{ color: 'var(--text)' }}>{fmt(data.avgOpeningVix)}</b></span>
            <span>Avg 10m move <b style={{ color: 'var(--text)' }}>{fmt(data.avgPctChange)}%</b></span>
            <span>Avg 10m range <b style={{ color: 'var(--text)' }}>{fmt(data.avgRangePct)}%</b></span>
            <span>High-vol days (≥3% range) <b style={{ color: 'var(--yellow)' }}>{fmt(data.highVolatilityProbabilityPct, 1)}%</b></span>
          </div>
          <div style={{ display: 'flex', gap: 4 }}>
            {Object.entries(data.volatilityDistribution).map(([cls, count]) => (
              <div key={cls} title={`${cls}: ${count} of ${data.totalDays} days`} style={{ flex: count, minWidth: 4, height: 18, background: CLASS_COLOR[cls] || 'var(--text3)', borderRadius: 3 }} />
            ))}
          </div>
          <div style={{ display: 'flex', gap: 10, fontSize: 9, color: 'var(--text3)', flexWrap: 'wrap' }}>
            {Object.entries(data.volatilityDistribution).map(([cls, count]) => (
              <span key={cls} style={{ display: 'flex', gap: 4, alignItems: 'center' }}><span style={{ width: 7, height: 7, borderRadius: 2, background: CLASS_COLOR[cls] || 'var(--text3)' }} />{cls} ({count})</span>
            ))}
          </div>
          <div style={{ fontSize: 10, color: 'var(--text3)' }}>Best day {data.bestDay || '—'} · Worst day {data.worstDay || '—'} · {data.totalDays} sessions analyzed</div>
        </div>
      )}
    </Card>
  )
}
