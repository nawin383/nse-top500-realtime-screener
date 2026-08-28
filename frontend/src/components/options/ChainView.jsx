import React, { useState } from 'react'
import { fmt, fmtInt, Empty, Skeleton } from './shared.jsx'

export default function ChainView({ data, loading, hasLoadedOnce, windowSize, onWindowSize }) {
  const [showGreeks, setShowGreeks] = useState(true)
  const tshape = data.tshape
  const analytics = tshape?.analytics

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
        <span style={{ fontSize: 11, color: 'var(--text2)' }}>
          Spot <b style={{ color: 'var(--text)', fontSize: 13 }}>{tshape?.spot ?? '—'}</b> ATM <b style={{ color: 'var(--yellow)' }}>{tshape?.atmStrike ?? '—'}</b>{' '}
          <span style={{ fontSize: 10, color: 'var(--text3)' }}>Src: {tshape?.source}</span>
        </span>
        <label style={{ fontSize: 11, color: 'var(--text2)', display: 'flex', gap: 4, alignItems: 'center' }}>
          <input type="checkbox" checked={showGreeks} onChange={e => setShowGreeks(e.target.checked)} /> Greeks
        </label>
        <select className="input" value={windowSize} onChange={e => onWindowSize(Number(e.target.value))}>
          <option value={7}>±7 strikes</option>
          <option value={10}>±10 strikes</option>
          <option value={15}>±15 strikes</option>
        </select>
        <span style={{ marginLeft: 'auto', fontSize: 10, color: 'var(--text3)' }}>
          {loading && tshape ? '● updating…' : '15s auto-refresh'} • Black-Scholes r=6%
        </span>
      </div>

      {analytics && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px,1fr))', gap: 8 }}>
          <div style={{ background: 'var(--bg3)', border: '1px solid var(--border)', borderRadius: 8, padding: 10 }}>
            <div style={{ fontSize: 11, color: 'var(--text2)' }}>PCR (PE/CE OI)</div>
            <div style={{ fontSize: 18, fontWeight: 700, color: analytics.pcr > 1 ? 'var(--green)' : 'var(--red)' }}>{fmt(analytics.pcr, 3)}</div>
            <div style={{ fontSize: 10, color: 'var(--text3)' }}>CE OI {fmtInt(analytics.totalCeOi)} | PE OI {fmtInt(analytics.totalPeOi)}</div>
          </div>
          <div style={{ background: 'var(--bg3)', border: '1px solid var(--border)', borderRadius: 8, padding: 10 }}>
            <div style={{ fontSize: 11, color: 'var(--text2)' }}>Max Pain</div>
            <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--yellow)' }}>{fmtInt(analytics.maxPain)}</div>
            <div style={{ fontSize: 10, color: 'var(--text3)' }}>Spot {fmt(analytics.spot)} ATM {fmtInt(analytics.atmStrike)}</div>
          </div>
          <div style={{ background: 'var(--bg3)', border: '1px solid var(--border)', borderRadius: 8, padding: 10 }}>
            <div style={{ fontSize: 11, color: 'var(--text2)' }}>ATM Premium (Straddle)</div>
            <div style={{ fontSize: 16, fontWeight: 700 }}>CE {fmt(analytics.atmCePremium)} + PE {fmt(analytics.atmPePremium)} = <span style={{ color: 'var(--blue)' }}>{fmt(analytics.atmStraddle)}</span></div>
            <div style={{ fontSize: 10, color: 'var(--text3)' }}>Break-even ±{fmt(analytics.atmStraddle)} from ATM</div>
          </div>
          <div style={{ background: 'var(--bg3)', border: '1px solid var(--border)', borderRadius: 8, padding: 10 }}>
            <div style={{ fontSize: 11, color: 'var(--text2)' }}>ATM IV / OI</div>
            <div style={{ fontSize: 13, fontWeight: 600 }}>{tshape?.chain?.find(c => c.strike === tshape.atmStrike)?.CE.iv ?? '—'}% IV</div>
            <div style={{ fontSize: 10, color: 'var(--text3)' }}>Call OI {fmtInt(tshape?.chain?.find(c => c.strike === tshape.atmStrike)?.CE.oi)} Put OI {fmtInt(tshape?.chain?.find(c => c.strike === tshape.atmStrike)?.PE.oi)}</div>
          </div>
        </div>
      )}

      {!hasLoadedOnce && loading && <Skeleton height={400} />}
      {!hasLoadedOnce && !loading && !tshape && <Empty label="No live chain data available for this symbol/expiry right now" />}

      {tshape && (
        <div style={{ overflow: 'auto', border: '1px solid var(--border)', borderRadius: 8, background: 'var(--bg2)' }}>
          <table style={{ width: '100%', fontSize: 11, borderCollapse: 'collapse' }}>
            <thead style={{ position: 'sticky', top: 0, background: 'var(--bg3)', zIndex: 1 }}>
              <tr>
                <th colSpan={showGreeks ? 9 : 4} style={{ textAlign: 'center', color: 'var(--green)', borderBottom: '2px solid var(--green)' }}>CALLS (CE)</th>
                <th style={{ textAlign: 'center', background: 'var(--border)', color: 'var(--yellow)' }}>STRIKE</th>
                <th colSpan={showGreeks ? 9 : 4} style={{ textAlign: 'center', color: 'var(--red)', borderBottom: '2px solid var(--red)' }}>PUTS (PE)</th>
              </tr>
              <tr style={{ fontSize: 10, color: 'var(--text2)' }}>
                <th>OI</th><th>ChgOI</th><th>Vol</th><th>LTP</th>
                {showGreeks && (<><th>IV%</th><th>Δ</th><th>Γ</th><th>θ</th><th>Vega</th></>)}
                <th style={{ background: 'var(--border)' }}>Price</th>
                {showGreeks && (<><th>Vega</th><th>θ</th><th>Γ</th><th>Δ</th><th>IV%</th></>)}
                <th>LTP</th><th>Vol</th><th>ChgOI</th><th>OI</th>
              </tr>
            </thead>
            <tbody>
              {tshape.chain.map(row => {
                const ce = row.CE, pe = row.PE
                const ceOiPct = Math.min(100, (ce.oi / 2000000) * 100)
                const peOiPct = Math.min(100, (pe.oi / 2000000) * 100)
                return (
                  <tr key={row.strike} style={{ background: row.isATM ? 'rgba(245,158,11,0.12)' : row.strike < tshape.spot ? 'rgba(16,185,129,0.04)' : 'rgba(239,83,80,0.04)', borderBottom: '1px solid var(--border)' }}>
                    <td style={{ textAlign: 'right' }}><div style={{ display: 'flex', alignItems: 'center', gap: 4 }}><span style={{ flex: 1 }}>{fmtInt(ce.oi)}</span><span style={{ width: 30, height: 4, background: 'var(--border)', display: 'inline-block' }}><span style={{ display: 'block', height: '100%', width: `${ceOiPct}%`, background: 'var(--green)' }} /></span></div></td>
                    <td style={{ textAlign: 'right', color: ce.oiChange >= 0 ? 'var(--green)' : 'var(--red)' }}>{ce.oiChange > 0 ? '+' : ''}{fmtInt(ce.oiChange)}</td>
                    <td style={{ textAlign: 'right' }}>{fmtInt(ce.volume)}</td>
                    <td style={{ textAlign: 'right', fontWeight: 700, color: row.isITM_CE ? 'var(--green)' : 'var(--text2)' }}>{fmt(ce.ltp)}</td>
                    {showGreeks && (<>
                      <td style={{ textAlign: 'right', color: 'var(--yellow)' }}>{fmt(ce.iv, 1)}</td>
                      <td style={{ textAlign: 'right' }}>{fmt(ce.delta, 2)}</td>
                      <td style={{ textAlign: 'right' }}>{fmt(ce.gamma, 3)}</td>
                      <td style={{ textAlign: 'right', color: 'var(--red)' }}>{fmt(ce.theta, 2)}</td>
                      <td style={{ textAlign: 'right' }}>{fmt(ce.vega, 2)}</td>
                    </>)}
                    <td style={{ textAlign: 'center', fontWeight: 800, background: row.isATM ? 'var(--yellow)' : 'var(--border)', color: row.isATM ? '#000' : 'var(--text)', borderLeft: '2px solid var(--yellow)', borderRight: '2px solid var(--yellow)' }}>{fmtInt(row.strike)}{row.isATM ? ' ★' : ''}</td>
                    {showGreeks && (<>
                      <td style={{ textAlign: 'left' }}>{fmt(pe.vega, 2)}</td>
                      <td style={{ textAlign: 'left', color: 'var(--red)' }}>{fmt(pe.theta, 2)}</td>
                      <td style={{ textAlign: 'left' }}>{fmt(pe.gamma, 3)}</td>
                      <td style={{ textAlign: 'left' }}>{fmt(pe.delta, 2)}</td>
                      <td style={{ textAlign: 'left', color: 'var(--yellow)' }}>{fmt(pe.iv, 1)}</td>
                    </>)}
                    <td style={{ textAlign: 'left', fontWeight: 700, color: row.isITM_PE ? 'var(--green)' : 'var(--text2)' }}>{fmt(pe.ltp)}</td>
                    <td style={{ textAlign: 'left' }}>{fmtInt(pe.volume)}</td>
                    <td style={{ textAlign: 'left', color: pe.oiChange >= 0 ? 'var(--green)' : 'var(--red)' }}>{pe.oiChange > 0 ? '+' : ''}{fmtInt(pe.oiChange)}</td>
                    <td style={{ textAlign: 'left' }}><div style={{ display: 'flex', alignItems: 'center', gap: 4 }}><span style={{ width: 30, height: 4, background: 'var(--border)', display: 'inline-block' }}><span style={{ display: 'block', height: '100%', width: `${peOiPct}%`, background: 'var(--red)' }} /></span><span style={{ flex: 1, textAlign: 'right' }}>{fmtInt(pe.oi)}</span></div></td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {tshape && (
        <div style={{ fontSize: 10, color: 'var(--text3)', display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          <span>★ ATM • Green left = ITM CE • Red right = ITM PE • OI bar = open interest • Δ Gamma θ Vega per Black-Scholes (r=6%)</span>
          <span>Source: {tshape.source} • {tshape.generatedAt ? new Date(tshape.generatedAt).toLocaleString('en-IN') : ''}</span>
        </div>
      )}
    </div>
  )
}
