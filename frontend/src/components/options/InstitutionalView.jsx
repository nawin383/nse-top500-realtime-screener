import React, { useEffect, useRef, useState } from 'react'
import { fmt, fmtInt, Card, Empty } from './shared.jsx'

// IV skew heatmap on canvas. IV can be genuinely null for strikes where the
// bisection solver can't recover an implied vol (deep ITM/OTM) -- those rows
// are dropped before drawing so a null never reaches r.iv.toFixed().
function VolSurfaceCanvas({ surface }) {
  const ref = useRef(null)
  useEffect(() => {
    if (!ref.current) return
    const canvas = ref.current
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    const W = canvas.width, H = canvas.height
    const bg = getComputedStyle(document.documentElement).getPropertyValue('--bg2').trim() || '#0d1b2a'
    const fg = getComputedStyle(document.documentElement).getPropertyValue('--text2').trim() || '#cbd5e1'
    ctx.clearRect(0, 0, W, H)
    ctx.fillStyle = bg; ctx.fillRect(0, 0, W, H)
    const rows = (surface || []).filter(r => r.iv != null).slice(0, 12)
    if (!rows.length) {
      ctx.fillStyle = fg; ctx.font = '11px sans-serif'
      ctx.fillText('No IV data available for this chain window', 10, H / 2)
      return
    }
    const maxIv = Math.max(...rows.map(r => r.iv))
    const minIv = Math.min(...rows.map(r => r.iv))
    rows.forEach((r, i) => {
      const y = (i / rows.length) * (H - 20) + 10
      const intensity = (r.iv - minIv) / (maxIv - minIv || 1)
      const hue = 200 - intensity * 60
      ctx.fillStyle = `hsl(${hue},80%,50%)`
      const w = (r.iv / maxIv) * (W - 80)
      ctx.fillRect(40, y, w, 8)
      ctx.fillStyle = fg; ctx.font = '10px monospace'
      ctx.fillText(`${r.strike} ${r.type} ${r.iv.toFixed(1)}%`, 4, y + 7)
    })
    ctx.fillStyle = '#f59e0b'; ctx.font = '11px sans-serif'
    ctx.fillText('IV skew heatmap by strike (live chain)', 10, H - 4)
  }, [surface])
  return <canvas ref={ref} width={600} height={180} style={{ width: '100%', height: 180, background: 'var(--bg2)', borderRadius: 8, border: '1px solid var(--border)' }} />
}

const DEFAULT_ORDER = ['margin', 'mispricing', 'correlation', 'term', 'volsurface', 'ivheatmap', 'greeksChain', 'greeksPositions', 'oiHeatmap', 'scenario', 'hvcone', 'ticks']
const ORDER_KEY = 'options_institutional_card_order_v1'

export default function InstitutionalView({ symbol, expiry, data }) {
  const { margin, mispricing, correlation, term, vol, greeksChain, oi, scenario, hvCone, positions, ticks, tshape } = data
  const [order, setOrder] = useState(() => {
    try {
      const saved = JSON.parse(localStorage.getItem(ORDER_KEY) || 'null')
      if (Array.isArray(saved) && DEFAULT_ORDER.every(k => saved.includes(k))) return saved
    } catch {}
    return DEFAULT_ORDER
  })
  useEffect(() => { try { localStorage.setItem(ORDER_KEY, JSON.stringify(order)) } catch {} }, [order])
  const dragIdx = useRef(null)

  const onDragStart = (i) => () => { dragIdx.current = i }
  const onDrop = (i) => (e) => {
    e.preventDefault()
    const from = dragIdx.current
    if (from == null || from === i) return
    setOrder(prev => {
      const next = [...prev]
      const [moved] = next.splice(from, 1)
      next.splice(i, 0, moved)
      return next
    })
    dragIdx.current = null
  }

  const exportCSV = () => {
    const csv = 'strike,CE LTP,PE LTP,CE OI,PE OI\n' + (tshape?.chain?.map(c => `${c.strike},${c.CE.ltp},${c.PE.ltp},${c.CE.oi},${c.PE.oi}`).join('\n') || '')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a'); a.href = url; a.download = `${symbol}_${expiry}_chain.csv`; a.click()
    URL.revokeObjectURL(url)
  }
  const exportPDF = async () => {
    try {
      const { jsPDF } = await import('jspdf')
      const doc = new jsPDF()
      doc.text(`Institutional Report ${symbol} ${expiry} ${new Date().toLocaleString()}`, 10, 10)
      doc.text(`Spot ${tshape?.spot} ATM ${tshape?.atmStrike} VIX ${data.vix?.vix}`, 10, 20)
      doc.save(`${symbol}_report.pdf`)
    } catch { alert('PDF export requires jspdf') }
  }

  const cardMap = {
    margin: (
      <Card title="Margin / VaR">
        {margin ? <><div>SPAN {fmtInt(margin.spanMargin)} Total {fmtInt(margin.totalMargin)}</div><div style={{ fontSize: 11, marginTop: 4 }}>VaR99 <b style={{ color: 'var(--red)' }}>{fmtInt(margin.var99)}</b> ES {fmtInt(margin.expectedShortfall)}</div></> : <Empty />}
      </Card>
    ),
    mispricing: (
      <Card title="Mispricing Scanner">
        {mispricing?.mispriced?.length ? mispricing.mispriced.slice(0, 5).map(m => (
          <div key={`${m.strike}${m.side}`} style={{ fontSize: 11, display: 'flex', justifyContent: 'space-between' }}>
            <span>{m.strike}{m.side} {m.arb}</span><span style={{ color: m.diffPct > 0 ? 'var(--red)' : 'var(--green)' }}>{fmt(m.diffPct)}%</span>
          </div>
        )) : <Empty label="No >5% mispricing" />}
      </Card>
    ),
    correlation: (
      <Card title="Correlation Matrix">
        {correlation ? (
          <div style={{ fontSize: 10 }}>
            <div style={{ display: 'grid', gridTemplateColumns: `repeat(${correlation.symbols.length + 1},1fr)`, gap: 2 }}>
              <div></div>{correlation.symbols.map(s => <div key={s} style={{ fontWeight: 700, textAlign: 'center' }}>{s.slice(0, 4)}</div>)}
              {correlation.symbols.map(a => (
                <React.Fragment key={a}>
                  <div style={{ fontWeight: 700 }}>{a.slice(0, 4)}</div>
                  {correlation.symbols.map(b => <div key={b} style={{ textAlign: 'center', background: `rgba(100,181,246,${correlation.matrix[a][b]})`, padding: '2px' }}>{fmt(correlation.matrix[a][b], 2)}</div>)}
                </React.Fragment>
              ))}
            </div>
          </div>
        ) : <Empty />}
      </Card>
    ),
    term: (
      <Card title="Term Structure & Calendar">
        {term ? <>
          <div style={{ fontSize: 11 }}>Roll Yield {fmt(term.rollYield)}% {term.contango ? 'Contango' : 'Backwardation'}</div>
          <div style={{ display: 'flex', gap: 4, marginTop: 6 }}>{term.points?.map(p => <div key={p.expiry} style={{ flex: 1, background: 'var(--bg3)', padding: 6, borderRadius: 4, textAlign: 'center' }}><div style={{ fontSize: 10, color: 'var(--text2)' }}>{p.expiry.slice(5)}</div><div style={{ fontWeight: 700 }}>{fmt(p.atmIv)}%</div></div>)}</div>
        </> : <Empty />}
      </Card>
    ),
    volsurface: (
      <Card title="Vol Surface & Skew (25Δ)">
        {vol ? <>
          <div style={{ fontSize: 11 }}>ATM IV {fmt(vol.atmIv)}% Skew 25Δ {fmt(vol.skew25Delta)}% (Put-Call)</div>
          <div style={{ height: 80, background: 'var(--bg3)', borderRadius: 4, padding: 4, overflow: 'auto', marginTop: 6 }}>{vol.volSurface?.slice(0, 12).map((v, i) => <div key={i} style={{ fontSize: 10, display: 'flex', justifyContent: 'space-between' }}><span>{v.strike} {v.type}</span><span style={{ color: 'var(--yellow)' }}>{fmt(v.iv)}%</span></div>)}</div>
        </> : <Empty />}
      </Card>
    ),
    ivheatmap: (
      <Card title="ATM Premium & IV Skew Heatmap">
        <div style={{ fontSize: 11, marginBottom: 6 }}>Straddle {fmt(tshape?.analytics?.atmStraddle)} (CE {fmt(tshape?.analytics?.atmCePremium)} + PE {fmt(tshape?.analytics?.atmPePremium)}) • PCR {fmt(tshape?.analytics?.pcr, 3)} • Max Pain {fmtInt(tshape?.analytics?.maxPain)}</div>
        <VolSurfaceCanvas surface={tshape?.chain?.flatMap(c => [{ strike: c.strike, iv: c.CE.iv, type: 'CE' }, { strike: c.strike, iv: c.PE.iv, type: 'PE' }]) || []} />
      </Card>
    ),
    greeksChain: (
      <Card title="Greeks Dashboard (Chain Aggregate)">
        {greeksChain ? <>
          <div style={{ fontSize: 11 }}>Δ {fmt(greeksChain.portfolioDelta)} Γ {fmt(greeksChain.portfolioGamma, 3)} Θ {fmt(greeksChain.portfolioTheta)} Vega {fmt(greeksChain.portfolioVega)}</div>
          <div style={{ height: 100, overflow: 'auto', marginTop: 6 }}>{greeksChain.heatmap?.slice(0, 10).map(h => <div key={h.strike} style={{ fontSize: 10, display: 'flex', gap: 8 }}><span style={{ width: 60 }}>{h.strike}</span><span>ΔExp {fmt(h.deltaExposure)}</span><span>ΓExp {fmt(h.gammaExposure, 1)}</span></div>)}</div>
        </> : <Empty />}
      </Card>
    ),
    greeksPositions: (
      <Card title="Greeks Dashboard (Your Positions)">
        {positions?.greeks ? <div style={{ fontSize: 11 }}>Δ {positions.greeks.netDelta} Γ {positions.greeks.netGamma} Θ {positions.greeks.netTheta} Vega {positions.greeks.netVega} (hedge {positions.greeks.hedgeRatio} lots)</div>
          : <Empty label="No positions — add via API POST /api/portfolio/positions" />}
      </Card>
    ),
    oiHeatmap: (
      <Card title="OI Heatmap & GEX Levels">
        {oi ? <>
          <div style={{ height: 120, overflow: 'auto' }}>{oi.heatmap?.slice(0, 12).map(h => (
            <div key={h.strike} style={{ fontSize: 10, display: 'flex', gap: 6, alignItems: 'center' }}>
              <span style={{ width: 50 }}>{h.strike}</span>
              <span style={{ flex: 1, height: 6, background: 'var(--border)' }}><span style={{ display: 'block', height: '100%', width: `${Math.min(100, h.ceOi / 3000000 * 100)}%`, background: 'var(--green)' }} /></span>
              <span style={{ flex: 1, height: 6, background: 'var(--border)' }}><span style={{ display: 'block', height: '100%', width: `${Math.min(100, h.peOi / 3000000 * 100)}%`, background: 'var(--red)' }} /></span>
              <span>{fmtInt(h.netOi)}</span>
            </div>
          ))}</div>
          <div style={{ fontSize: 10, color: 'var(--text3)', marginTop: 6 }}>GEX levels: {oi.gexLevels?.slice(0, 3).map(g => `${g.strike}:${fmtInt(g.gex)}`).join(' • ')}</div>
        </> : <Empty />}
      </Card>
    ),
    scenario: (
      <Card title="Scenario P&L (ATM straddle, price ±5% × IV ±20%)">
        {scenario?.scenarios?.length ? scenario.scenarios.slice(0, 6).map((s, i) => (
          <div key={i} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, borderBottom: '1px solid var(--border)' }}>
            <span>{s.priceMove} {s.ivMove}</span><span style={{ color: s.pnl > 0 ? 'var(--green)' : 'var(--red)' }}>{fmt(s.pnl)}</span>
          </div>
        )) : <Empty />}
      </Card>
    ),
    hvcone: (
      <Card title="HV Cone & IV Percentile (1Y/6M/3M)">
        {hvCone?.cone ? <>
          <div style={{ fontSize: 11 }}>HV30 {hvCone.hv30}% • Cone 1M [{hvCone.cone['1M']?.join('-')}] 1Y [{hvCone.cone['1Y']?.join('-')}] • {hvCone.position}</div>
          <div style={{ height: 60, background: 'var(--bg3)', borderRadius: 4, marginTop: 6, padding: 6, fontSize: 10 }}>{Object.entries(hvCone.cone).filter(([, v]) => v).map(([k, v]) => <div key={k} style={{ display: 'flex', justifyContent: 'space-between' }}><span>{k}</span><span>{v[0]} — {v[1]}%</span></div>)}</div>
        </> : <Empty label={hvCone?.note || 'HV cone needs ingested bhavcopy history (see /api/historical/bhavcopy)'} />}
      </Card>
    ),
    ticks: (
      <Card title="Time & Sales (tick-by-tick) + Order Flow">
        <div style={{ fontSize: 10, height: 100, overflow: 'auto' }}>
          {(ticks?.ticks || []).slice(0, 10).map((t, i) => <div key={i} style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border)' }}><span>{new Date(t.time).toLocaleTimeString()}</span><span>{t.price}</span><span style={{ color: t.side === 'buy' ? 'var(--green)' : 'var(--red)' }}>{t.side}</span><span>{t.exchange}</span></div>)}
          {!(ticks?.ticks || []).length && <div style={{ color: 'var(--text3)' }}>No ticks yet (live when market open)</div>}
        </div>
        <div style={{ fontSize: 10, color: 'var(--text3)', marginTop: 6 }}>Institutional/retail order-flow attribution isn't exposed by Kite's public market data</div>
      </Card>
    ),
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
        <button className="btn sm" onClick={exportCSV}>⬇ CSV</button>
        <button className="btn sm" onClick={exportPDF}>⬇ PDF</button>
        <span style={{ fontSize: 10, color: 'var(--text3)' }}>Drag any card by its handle to reorder — your layout is remembered</span>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px,1fr))', gap: 10, alignItems: 'start' }}>
        {order.map((key, i) => (
          <div key={key}
            draggable
            onDragStart={onDragStart(i)}
            onDragOver={(e) => e.preventDefault()}
            onDrop={onDrop(i)}
            style={{ cursor: 'grab' }}
            title="Drag to reorder">
            {cardMap[key]}
          </div>
        ))}
      </div>
    </div>
  )
}
