import React, { useMemo } from 'react'
import { IconSparkle, IconTrendUp } from './icons.jsx'

const fmtPct = (n) => n == null ? '—' : `${n > 0 ? '+' : ''}${n.toFixed(2)}%`

// Deterministic, explainable trade-opportunity synthesis from the same
// technical fields already shown in the screener table (score, momentum,
// relative volume, VWAP position, breakout/RSI/MACD/Supertrend). No model
// call, no fabricated numbers -- every reason cited traces back to a real
// computed field on the stock, so the "why" is always verifiable against
// the table itself.
function buildInsight(s) {
  const reasons = []
  if (s.isBreakout) reasons.push('breaking out')
  if ((s.relVolume || 0) > 2) reasons.push(`${s.relVolume.toFixed(1)}x volume`)
  else if ((s.relVolume || 0) > 1.5) reasons.push(`elevated volume (${s.relVolume.toFixed(1)}x)`)
  if (s.isAboveVwap) reasons.push('above VWAP')
  if ((s.momentum5m || 0) > 1) reasons.push(`+${s.momentum5m.toFixed(1)}% in 5m`)
  if (s.rsi != null) {
    if (s.rsi >= 70) reasons.push(`RSI ${s.rsi.toFixed(0)} (overbought)`)
    else if (s.rsi >= 55) reasons.push(`RSI ${s.rsi.toFixed(0)} trending up`)
    else if (s.rsi <= 30) reasons.push(`RSI ${s.rsi.toFixed(0)} (oversold)`)
  }
  if (s.macdCross === 'bullish_cross') reasons.push('bullish MACD cross')
  if (s.macdCross === 'bearish_cross') reasons.push('bearish MACD cross')
  if (s.supertrendDirection === 1) reasons.push('Supertrend bullish')
  else if (s.supertrendDirection === -1) reasons.push('Supertrend bearish')

  const bullish = (s.changePercent || 0) >= 0
  const score = s.score || 0
  let verdict, verdictColor
  if (score >= 75) { verdict = bullish ? 'High-conviction long setup' : 'High-conviction short pressure'; verdictColor = bullish ? 'var(--green)' : 'var(--red)' }
  else if (score >= 55) { verdict = 'Constructive setup — monitor'; verdictColor = 'var(--yellow)' }
  else { verdict = 'Speculative — confirm before acting'; verdictColor = 'var(--text3)' }

  return { symbol: s.symbol, companyName: s.companyName, score, changePercent: s.changePercent, verdict, verdictColor, reasons: reasons.slice(0, 4), bullish }
}

export default function AIInsights({ stocks = [] }) {
  const insights = useMemo(() => {
    return stocks
      .filter(s => (s.score || 0) > 0)
      .map(buildInsight)
      .filter(i => i.reasons.length > 0)
      .sort((a, b) => (b.score || 0) - (a.score || 0))
      .slice(0, 8)
  }, [stocks])

  return (
    <div style={{ background: 'var(--bg2)', border: '1px solid var(--border)', borderRadius: 14, padding: 14, display: 'flex', flexDirection: 'column', gap: 10 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <IconSparkle style={{ color: 'var(--yellow)' }} />
        <span style={{ fontSize: 11, fontWeight: 800, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text2)' }}>Trade Opportunity Insights</span>
        <span style={{ marginLeft: 'auto', fontSize: 9, color: 'var(--text3)' }}>Derived from live technical signals — not investment advice</span>
      </div>
      {insights.length === 0 && <div style={{ fontSize: 11, color: 'var(--text3)', textAlign: 'center', padding: '16px 8px' }}>No standout setups right now — waiting for live signals</div>}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {insights.map(i => (
          <div key={i.symbol} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 10px', borderRadius: 10, background: 'var(--bg3)', border: '1px solid var(--border)' }}>
            <IconTrendUp style={{ color: i.bullish ? 'var(--green)' : 'var(--red)', transform: i.bullish ? 'none' : 'scaleY(-1)', flexShrink: 0 }} />
            <div style={{ minWidth: 74 }}>
              <div style={{ fontWeight: 800, fontSize: 12, color: 'var(--text)' }}>{i.symbol}</div>
              <div className="mono" style={{ fontSize: 10, color: i.bullish ? 'var(--green)' : 'var(--red)', fontWeight: 700 }}>{fmtPct(i.changePercent)}</div>
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: i.verdictColor }}>{i.verdict}</div>
              <div style={{ fontSize: 10, color: 'var(--text3)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{i.reasons.join(' · ')}</div>
            </div>
            <div style={{ textAlign: 'right', flexShrink: 0 }}>
              <div style={{ fontSize: 9, color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Score</div>
              <div className="mono" style={{ fontWeight: 800, fontSize: 13, color: i.verdictColor }}>{i.score.toFixed(0)}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
