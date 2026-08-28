import React, { Suspense, lazy, useMemo } from 'react'
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, Cell, Legend } from 'recharts'
import { fmt, fmtInt, Card, Empty, Skeleton } from './shared.jsx'
import VixOpenVolatility from './VixOpenVolatility.jsx'

const OpenInterestChart = lazy(() => import('../OpenInterestChart.jsx'))

export default function AnalyticsView({ data, theme }) {
  const { atm, pcr, oi, vol, ivhv, vix, unusual, strategies, sellerDash } = data

  // IV skew: CE vs PE implied vol per strike, from the real live chain.
  const skewData = useMemo(() => {
    if (!vol?.volSurface) return []
    const byStrike = {}
    for (const p of vol.volSurface) {
      byStrike[p.strike] = byStrike[p.strike] || { strike: p.strike }
      byStrike[p.strike][p.type === 'CE' ? 'ceIv' : 'peIv'] = p.iv
    }
    return Object.values(byStrike).sort((a, b) => a.strike - b.strike)
  }, [vol])

  // Where fresh OI is actually building right now (netOi per strike), not just
  // the static OI level (the Weekly/Monthly OI chart below already shows that).
  const oiChangeData = useMemo(() => {
    if (!oi?.heatmap) return []
    return oi.heatmap.map(h => ({ strike: h.strike, netOi: h.netOi })).sort((a, b) => a.strike - b.strike)
  }, [oi])

  const isDark = theme !== 'light'
  const axisColor = isDark ? '#94a3b8' : '#64748b'
  const gridColor = isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)'
  const tooltipStyle = { background: 'var(--bg2)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 11, color: 'var(--text)' }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px,1fr))', gap: 10 }}>
        <Card title="ATM Premium & Implied Move" delay={0}>
          {atm ? <>
            <div style={{ fontSize: 18, fontWeight: 800, color: 'var(--blue)' }}>{fmt(atm.straddle)} <span style={{ fontSize: 11, color: 'var(--text2)' }}>({fmt(atm.impliedMovePct)}%)</span></div>
            <div style={{ fontSize: 11, color: 'var(--text2)', marginTop: 4 }}>CE {fmt(atm.cePremium)} + PE {fmt(atm.pePremium)} — strike {atm.atmStrike}</div>
          </> : <Empty />}
        </Card>
        <Card title="PCR & Sentiment" delay={1}>
          {pcr ? <>
            <div style={{ fontSize: 20, fontWeight: 800, color: pcr.pcrOi > 1 ? 'var(--green)' : 'var(--red)' }}>{fmt(pcr.pcrOi, 3)}</div>
            <div style={{ fontSize: 11, color: 'var(--text2)', marginTop: 4 }}>Vol PCR {fmt(pcr.pcrVol, 3)} · <span style={{ color: pcr.sentiment === 'bullish' ? 'var(--green)' : pcr.sentiment === 'bearish' ? 'var(--red)' : 'var(--text2)', fontWeight: 700, textTransform: 'capitalize' }}>{pcr.sentiment}</span></div>
          </> : <Empty />}
        </Card>
        <Card title="Max Pain & Dealer Gamma" delay={2}>
          {oi ? <>
            <div style={{ fontSize: 20, fontWeight: 800, color: 'var(--yellow)' }}>{fmtInt(oi.maxPain)}</div>
            <div style={{ fontSize: 11, color: 'var(--text2)', marginTop: 4 }}>GEX {fmtInt(oi.totalGex)} · {oi.dealerPositioning}</div>
          </> : <Empty />}
        </Card>
        <Card title="IV vs HV" delay={3}>
          {ivhv ? <>
            <div style={{ fontSize: 16, fontWeight: 800 }}>{fmt(ivhv.iv)}% <span style={{ fontSize: 11, color: 'var(--text2)', fontWeight: 500 }}>IV</span></div>
            <div style={{ fontSize: 11, color: 'var(--text2)', marginTop: 4 }}>{ivhv.hv != null ? `HV ${fmt(ivhv.hv)}% · spread ${fmt(ivhv.ivMinusHv)}%` : 'HV needs ingested history'}</div>
          </> : <Empty />}
        </Card>
        <Card title="India VIX" delay={4}>
          {vix?.vix != null ? <>
            <div style={{ fontSize: 20, fontWeight: 800 }}>{fmt(vix.vix)}</div>
            <div style={{ fontSize: 11, color: 'var(--text2)', marginTop: 4 }}>Source: {vix.source}</div>
          </> : <Empty label="VIX unavailable (NSE unreachable)" />}
        </Card>
      </div>

      <VixOpenVolatility />

      <Card title="Open Interest — Weekly / Monthly Profile" delay={5}>
        <Suspense fallback={<Skeleton height={340} />}>
          <OpenInterestChart theme={theme} />
        </Suspense>
      </Card>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
        <Card title="IV Skew — Calls vs Puts by Strike" height={320} delay={6}>
          {skewData.length ? (
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={skewData} margin={{ top: 4, right: 16, bottom: 4, left: 0 }}>
                <CartesianGrid stroke={gridColor} strokeDasharray="3 3" />
                <XAxis dataKey="strike" tick={{ fill: axisColor, fontSize: 10 }} stroke={gridColor} />
                <YAxis tick={{ fill: axisColor, fontSize: 10 }} stroke={gridColor} unit="%" />
                <Tooltip contentStyle={tooltipStyle} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Line type="monotone" dataKey="ceIv" name="Call IV" stroke="#10b981" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="peIv" name="Put IV" stroke="#ef5350" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          ) : <Empty />}
        </Card>
        <Card title="Net OI Change by Strike (where flow is building now)" height={320} delay={7}>
          {oiChangeData.length ? (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={oiChangeData} margin={{ top: 4, right: 16, bottom: 4, left: 0 }}>
                <CartesianGrid stroke={gridColor} strokeDasharray="3 3" />
                <XAxis dataKey="strike" tick={{ fill: axisColor, fontSize: 10 }} stroke={gridColor} />
                <YAxis tick={{ fill: axisColor, fontSize: 10 }} stroke={gridColor} tickFormatter={fmtInt} />
                <Tooltip contentStyle={tooltipStyle} formatter={(v) => [fmtInt(v), 'Net OI (Put − Call)']} />
                <ReferenceLine y={0} stroke={axisColor} />
                <Bar dataKey="netOi">
                  {oiChangeData.map((d, i) => <Cell key={i} fill={d.netOi >= 0 ? '#ef5350' : '#10b981'} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : <Empty />}
        </Card>
      </div>

      <Card title="Unusual Activity" delay={8}>
        {unusual?.unusual?.length ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            {unusual.unusual.map(u => (
              <div key={`${u.strike}${u.side}`} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, padding: '6px 0', borderBottom: '1px solid var(--border)' }}>
                <span><b>{u.strike} {u.side}</b> <span style={{ color: 'var(--text2)' }}>{u.type}</span></span>
                <span style={{ color: 'var(--text2)' }}>{u.score ? `×${fmt(u.score)} avg` : ''} {u.oiChange != null ? `OI ${fmtInt(u.oiChange)}` : ''}</span>
              </div>
            ))}
          </div>
        ) : <Empty label="No unusual flow detected" />}
      </Card>

      <Card title="Options Strategy Panel" delay={9}>
        {strategies ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <div style={{ fontSize: 10, color: 'var(--text3)', marginBottom: 2 }}>IV rank (1y) {strategies.iv_rank_1y != null ? `${fmt(strategies.iv_rank_1y, 0)}%` : 'unavailable'} · ADX {strategies.adx != null ? fmt(strategies.adx, 1) : 'not supplied'}</div>
            {['short_strangle', 'iron_condor', 'bull_put_spread', 'bear_call_spread', 'iron_fly', 'ratio_spread_1x2', 'calendar_spread'].map(key => {
              const s = strategies[key]
              if (!s) return null
              if (s.error) return <div key={key} style={{ fontSize: 11, color: 'var(--text3)', padding: '6px 0', borderBottom: '1px solid var(--border)' }}><b style={{ color: 'var(--text2)' }}>{key.replace(/_/g, ' ')}</b> — {s.error}</div>
              const eligible = s.regime?.eligible
              return (
                <div key={key} style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap', fontSize: 11, padding: '6px 0', borderBottom: '1px solid var(--border)' }}>
                  <b style={{ color: 'var(--text)', minWidth: 130, textTransform: 'capitalize' }}>{key.replace(/_/g, ' ')}</b>
                  {eligible != null && <span style={{ fontSize: 9, fontWeight: 800, padding: '1px 7px', borderRadius: 999, background: eligible ? 'rgba(16,185,129,0.15)' : 'rgba(239,83,80,0.12)', color: eligible ? 'var(--green)' : 'var(--red)' }}>{eligible ? 'ELIGIBLE' : 'NOT ELIGIBLE'}</span>}
                  <span className="mono" style={{ color: 'var(--text2)' }}>Net {fmt(s.net_premium)}</span>
                  <span className="mono" style={{ color: 'var(--text3)' }}>Max L {typeof s.max_loss === 'string' ? s.max_loss : fmt(s.max_loss)}</span>
                  {s.pop_pct != null && <span className="mono" style={{ color: 'var(--blue)' }}>POP {fmt(s.pop_pct, 0)}%</span>}
                  {s.theta != null && <span className="mono" style={{ color: 'var(--text3)' }}>θ {fmt(s.theta)}</span>}
                  {s.margin_estimate != null && <span className="mono" style={{ color: 'var(--text3)' }}>Margin ~{fmtInt(s.margin_estimate)}</span>}
                </div>
              )
            })}
          </div>
        ) : <Empty label="Strategy panel needs a live option chain" />}
      </Card>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px,1fr))', gap: 10 }}>
        <Card title="Seller's Premium — Favorability Score" delay={10}>
          {sellerDash?.favorability_score?.score != null ? <>
            <div style={{ fontSize: 22, fontWeight: 800, color: sellerDash.favorability_score.score >= 65 ? 'var(--green)' : sellerDash.favorability_score.score <= 35 ? 'var(--red)' : 'var(--yellow)' }}>{fmt(sellerDash.favorability_score.score, 0)}<span style={{ fontSize: 11, color: 'var(--text3)' }}>/100</span></div>
            <div style={{ fontSize: 11, color: 'var(--text2)', marginTop: 4, textTransform: 'capitalize' }}>{sellerDash.favorability_score.label}</div>
            <div style={{ fontSize: 9, color: 'var(--text3)', marginTop: 2 }}>coverage {fmt(sellerDash.favorability_score.coverage_pct, 0)}% of components available</div>
          </> : <Empty label="Not enough regime data yet" />}
        </Card>
        <Card title="VIX Mean-Reversion Z-Score" delay={11}>
          {sellerDash?.vix_mean_reversion?.z_score != null ? <>
            <div style={{ fontSize: 20, fontWeight: 800, color: sellerDash.vix_mean_reversion.z_score > 1 ? 'var(--green)' : sellerDash.vix_mean_reversion.z_score < -1 ? 'var(--red)' : 'var(--text2)' }}>{fmt(sellerDash.vix_mean_reversion.z_score)}σ</div>
            <div style={{ fontSize: 11, color: 'var(--text2)', marginTop: 4 }}>{sellerDash.vix_mean_reversion.interpretation}</div>
            <div style={{ fontSize: 9, color: 'var(--text3)', marginTop: 2 }}>current {fmt(sellerDash.vix_mean_reversion.current)} · mean {fmt(sellerDash.vix_mean_reversion.mean)} · n={sellerDash.vix_mean_reversion.sample_size}</div>
          </> : <Empty label={sellerDash?.vix_mean_reversion?.reason || 'VIX history unavailable'} />}
        </Card>
        <Card title="IV − Realized Vol Spread" delay={12}>
          {sellerDash?.iv_rv_spread?.spread != null ? <>
            <div style={{ fontSize: 20, fontWeight: 800, color: sellerDash.iv_rv_spread.spread > 2 ? 'var(--green)' : sellerDash.iv_rv_spread.spread < -2 ? 'var(--red)' : 'var(--text2)' }}>{fmt(sellerDash.iv_rv_spread.spread)}pts</div>
            <div style={{ fontSize: 11, color: 'var(--text2)', marginTop: 4 }}>{sellerDash.iv_rv_spread.interpretation}</div>
            <div style={{ fontSize: 9, color: 'var(--text3)', marginTop: 2 }}>IV {fmt(sellerDash.iv_rv_spread.current_iv)}% · realized {fmt(sellerDash.iv_rv_spread.realized_vol)}%</div>
          </> : <Empty label={sellerDash?.iv_rv_spread?.reason || 'price history unavailable'} />}
        </Card>
        <Card title="Expiry-Day Pin Risk" delay={13}>
          {sellerDash?.expiry_pin_risk?.pin_risk_score != null ? <>
            <div style={{ fontSize: 20, fontWeight: 800, color: sellerDash.expiry_pin_risk.pin_risk_score >= 65 ? 'var(--yellow)' : 'var(--text2)' }}>{fmt(sellerDash.expiry_pin_risk.pin_risk_score, 0)}</div>
            <div style={{ fontSize: 11, color: 'var(--text2)', marginTop: 4, textTransform: 'capitalize' }}>{sellerDash.expiry_pin_risk.label}{sellerDash.expiry_pin_risk.is_expiry_day ? ' · TODAY IS EXPIRY' : ''}</div>
            <div style={{ fontSize: 9, color: 'var(--text3)', marginTop: 2 }}>{fmt(sellerDash.expiry_pin_risk.distance_to_max_pain_pct)}% from max pain · {fmt(sellerDash.expiry_pin_risk.oi_concentration_near_money_pct)}% OI near spot</div>
          </> : <Empty label={sellerDash?.expiry_pin_risk?.reason || 'chain/max-pain unavailable'} />}
        </Card>
      </div>
    </div>
  )
}
