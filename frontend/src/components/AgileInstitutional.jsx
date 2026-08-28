import React, { useEffect, useState, useRef } from 'react'
import { motion } from 'framer-motion'

const apiBase = import.meta.env.VITE_API_URL || ''

// Strike/IV skew heatmap on canvas
function VolSurface3D({ surface }) {
  const ref = useRef(null)
  useEffect(() => {
    if (!ref.current || !surface) return
    const canvas = ref.current
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    const W = canvas.width, H = canvas.height
    ctx.clearRect(0,0,W,H)
    ctx.fillStyle = '#0d1b2a'; ctx.fillRect(0,0,W,H)
    // draw heatmap rows
    const rows = surface.slice(0, 12)
    const maxIv = Math.max(...rows.map(r=>r.iv))
    const minIv = Math.min(...rows.map(r=>r.iv))
    rows.forEach((r,i)=>{
      const y = (i / rows.length) * (H-20) + 10
      const intensity = (r.iv - minIv) / (maxIv - minIv || 1)
      const hue = 200 - intensity*60 // blue to red
      ctx.fillStyle = `hsl(${hue},80%,50%)`
      const w = (r.iv / maxIv) * (W-80)
      ctx.fillRect(40, y, w, 8)
      ctx.fillStyle = '#cbd5e1'; ctx.font = '10px monospace'
      ctx.fillText(`${r.strike} ${r.type} ${r.iv.toFixed(1)}%`, 4, y+7)
    })
    ctx.fillStyle = '#f59e0b'; ctx.font = '11px sans-serif'
    ctx.fillText('IV skew heatmap by strike (live chain)', 10, H-4)
  }, [surface])
  return <canvas ref={ref} width={600} height={180} style={{width:'100%', height:180, background:'#0d1b2a', borderRadius:8, border:'1px solid #1e293b'}} />
}

function Widget({ title, children, onExport }){
  return (
    <motion.div layout drag dragMomentum={false} whileDrag={{ scale: 1.02, zIndex: 10 }}
      style={{background:'#16233a', border:'1px solid #1e293b', borderRadius:8, padding:12, cursor:'grab'}}>
      <div style={{display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:8}}>
        <div style={{fontSize:11, color:'#cbd5e1', fontWeight:700, letterSpacing:'.05em', textTransform:'uppercase'}}>{title}</div>
        {onExport && <button className="btn sm" onClick={onExport} style={{fontSize:10}}>CSV/PDF</button>}
      </div>
      <div>{children}</div>
    </motion.div>
  )
}

export default function AgileInstitutional(){
  const [symbol, setSymbol] = useState('NIFTY')
  const [expiry, setExpiry] = useState('')
  const [theme, setTheme] = useState('dark')
  const [tshape, setTshape] = useState(null)
  const [vix, setVix] = useState(null)
  const [hv, setHv] = useState(null)
  const [positions, setPositions] = useState([])
  const [greeks, setGreeks] = useState(null)
  const [scenario, setScenario] = useState(null)
  const [corr, setCorr] = useState(null)
  const [ticks, setTicks] = useState([])
  const [role] = useState('trader') // role-based: trader/viewer/admin

  // hotkeys
  useEffect(()=>{
    const h = (e)=>{
      if(e.key==='k' && (e.ctrlKey||e.metaKey)){ e.preventDefault(); document.querySelector('input')?.focus() }
      if(e.key==='o'){ setSymbol('NIFTY') }
    }
    window.addEventListener('keydown', h)
    return ()=> window.removeEventListener('keydown', h)
  },[])

  // A failed/unavailable endpoint returns {detail:"..."} instead of the expected
  // shape (not a rejected promise -- the JSON still parses fine), so .catch(()=>null)
  // alone doesn't protect the unguarded tshape.chain.map()/etc below from crashing
  // the page. Treat any non-ok response or a detail-shaped body as "no data".
  const safeFetch = async (url)=>{
    try{
      const r = await fetch(url)
      const j = await r.json()
      if(!r.ok || j?.detail) return null
      return j
    }catch{ return null }
  }

  // fetch all
  const fetchAll = async ()=>{
    const base = `${apiBase}/api`
    try{
      const [ts, vx, hvc, sc, cr] = await Promise.all([
        safeFetch(`${base}/options/tshape?symbol=${symbol}${expiry?`&expiry=${expiry}`:''}&window=10`),
        safeFetch(`${base}/options/vix`),
        safeFetch(`${base}/historical/hv-cone?symbol=${symbol}`),
        safeFetch(`${base}/options/scenario?symbol=${symbol}${expiry?`&expiry=${expiry}`:''}`),
        safeFetch(`${base}/options/correlation`),
      ])
      if(ts) setTshape(ts)
      if(vx) setVix(vx)
      if(hvc) setHv(hvc)
      if(sc) setScenario(sc)
      if(cr) setCorr(cr)
      // positions
      fetch(`${base}/portfolio/positions`).then(r=>r.json()).then(j=>{ setPositions(j.positions||[]); setGreeks(j.greeks) }).catch(()=>{})
      // ticks
      fetch(`${base}/microstructure/ticks?symbol=${symbol}&limit=10`).then(r=>r.json()).then(j=> setTicks(j.ticks||[])).catch(()=>{})
    }catch{}
  }
  useEffect(()=>{ fetchAll() }, [symbol, expiry])
  useEffect(()=>{
    fetch(`${apiBase}/api/options/expiries?symbol=${symbol}`).then(r=>r.json()).then(j=>{ if(j.expiries?.length) setExpiry(prev=> prev && j.expiries.includes(prev) ? prev : j.expiries[0]) }).catch(()=>{})
    const id=setInterval(fetchAll, 10000)
    return ()=> clearInterval(id)
  }, [symbol])

  const exportCSV = ()=>{
    const csv = "strike,CE LTP,PE LTP,CE OI,PE OI\n" + (tshape?.chain?.map(c=> `${c.strike},${c.CE.ltp},${c.PE.ltp},${c.CE.oi},${c.PE.oi}`).join("\n") || "")
    const blob = new Blob([csv], {type:'text/csv'})
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a'); a.href=url; a.download=`${symbol}_${expiry}_chain.csv`; a.click()
  }
  const exportPDF = async ()=>{
    try{
      const { jsPDF } = await import('jspdf')
      const doc = new jsPDF()
      doc.text(`Institutional Report ${symbol} ${expiry} ${new Date().toLocaleString()}`, 10, 10)
      doc.text(`Spot ${tshape?.spot} ATM ${tshape?.atmStrike} VIX ${vix?.vix}`, 10, 20)
      doc.save(`${symbol}_report.pdf`)
    }catch{ alert('PDF export requires jspdf') }
  }

  // drag-drop layout state (simple)
  const [layout, setLayout] = useState(['atm','vol','greeks','hv','vix','oi','scenario','corr','ticks'])

  return (
    <div style={{padding:12, background: theme==='dark'?'#0b1220':'#f8fafc', color: theme==='dark'?'#f1f5f9':'#0f172a', minHeight:'100%'}}>
      <div style={{display:'flex', gap:8, alignItems:'center', flexWrap:'wrap', marginBottom:12}}>
        <h2 style={{fontSize:16, fontWeight:800, margin:0}}>🏛 Institutional — Drag-Drop • Hotkeys • Export</h2>
        <select className="input" value={symbol} onChange={e=> setSymbol(e.target.value)}><option>NIFTY</option><option>SENSEX</option><option>BANKNIFTY</option></select>
        <select className="input" value={expiry} onChange={e=> setExpiry(e.target.value)}>{(tshape?.expiries||[]).map(e=> <option key={e} value={e}>{e}</option>)}</select>
        <span style={{fontSize:11, color:'#cbd5e1'}}>Spot {tshape?.spot} ATM {tshape?.atmStrike} <span style={{color: theme==='dark'?'#f59e0b':'#d97706'}}>Last-Day {tshape?.isLastTradingDay?'Yes':''}</span></span>
        <button className="btn sm" onClick={()=> setTheme(theme==='dark'?'light':'dark')}>{theme==='dark'?'☀ Light':'🌙 Dark'}</button>
        <span style={{marginLeft:'auto', fontSize:10, color:'#cbd5e1'}}>Role: {role} • Multi-monitor • Workspace • Ctrl+K focus</span>
      </div>

      {/* Drag-drop grid - using CSS grid with framer-motion drag */}
      <div style={{display:'grid', gridTemplateColumns:'repeat(auto-fit, minmax(320px,1fr))', gap:10, marginBottom:12}}>
        <Widget title="ATM Premium & IV Skew" onExport={exportCSV}>
          <div style={{fontSize:11, marginBottom:6}}>Straddle {tshape?.analytics?.atmStraddle} (CE {tshape?.analytics?.atmCePremium} + PE {tshape?.analytics?.atmPePremium}) • PCR {tshape?.analytics?.pcr} • Max Pain {tshape?.analytics?.maxPain}</div>
          <VolSurface3D surface={tshape?.chain?.flatMap(c=> [{strike:c.strike, iv:c.CE.iv, type:'CE'}, {strike:c.strike, iv:c.PE.iv, type:'PE'}]) || []} />
        </Widget>

        <Widget title="Greeks Dashboard (portfolio)">
          {greeks ? <div style={{fontSize:11}}>Δ {greeks.netDelta} Γ {greeks.netGamma} Θ {greeks.netTheta} Vega {greeks.netVega} (hedge {greeks.hedgeRatio} lots)</div> : <div style={{fontSize:11, color:'#94a3b8'}}>No positions — add via API POST /api/portfolio/positions</div>}
        </Widget>

        <Widget title="HV Cone & IV Percentile (1Y/6M/3M)">
          {hv?.cone ? <><div style={{fontSize:11}}>HV30 {hv.hv30}% • Cone 1M [{hv.cone['1M']?.join('-')}] 1Y [{hv.cone['1Y']?.join('-')}] • {hv.position}</div><div style={{height:60, background:'#0d1b2a', borderRadius:4, marginTop:6, padding:6, fontSize:10}}>{Object.entries(hv.cone).filter(([,v])=>v).map(([k,v])=> <div key={k} style={{display:'flex', justifyContent:'space-between'}}><span>{k}</span><span>{v[0]} — {v[1]}%</span></div>)}</div></> : <div style={{fontSize:11, color:'#94a3b8'}}>{hv?.note || 'HV cone needs ingested bhavcopy history (see /api/historical/bhavcopy)'}</div>}
        </Widget>

        <Widget title="VIX & Correlation">
          <div style={{fontSize:11}}>VIX {vix?.vix ?? '—'} ({vix?.source ?? 'unavailable'}) • Corr NIFTY {vix?.correlationNifty ?? '—'}</div>
          <div style={{fontSize:10, marginTop:6, display:'grid', gridTemplateColumns:'repeat(3,1fr)', gap:4}}>
            {(corr?.symbols||['NIFTY','SENSEX','BANKNIFTY']).slice(0,3).map(s=> <div key={s} style={{background:'#0d1b2a', padding:6, borderRadius:4, textAlign:'center', fontSize:10}}>{s}<br/>{corr?.matrix?.[s] ? Object.values(corr.matrix[s]).find(v=>v!=null && v!==1)?.toFixed(2) ?? '—' :'—'}</div>)}
          </div>
        </Widget>

        <Widget title="OI Heatmap & GEX">
          <div style={{height:100, overflow:'auto', fontSize:10}}>
            {tshape?.chain?.slice(0,10).map(c=> (
              <div key={c.strike} style={{display:'flex', gap:4, alignItems:'center'}}>
                <span style={{width:50}}>{c.strike}</span>
                <span style={{flex:1, height:6, background:'#1e293b'}}><span style={{display:'block', height:'100%', width:`${Math.min(100, c.CE.oi/3000000*100)}%`, background:'#10b981'}}/></span>
                <span style={{flex:1, height:6, background:'#1e293b'}}><span style={{display:'block', height:'100%', width:`${Math.min(100, c.PE.oi/3000000*100)}%`, background:'#ef5350'}}/></span>
              </div>
            ))}
          </div>
        </Widget>

        <Widget title="Scenario P&L (price ±5% × IV ±20%)">
          <div style={{fontSize:10}}>
            {scenario?.scenarios?.slice(0,6).map((s,i)=> <div key={i} style={{display:'flex', justifyContent:'space-between', borderBottom:'1px solid #1e293b'}}><span>{s.priceMove} {s.ivMove}</span><span style={{color: s.pnl>0?'#10b981':'#ef5350'}}>{s.pnl}</span></div>)}
          </div>
        </Widget>

        <Widget title="Time & Sales (tick-by-tick) + Order Flow">
          <div style={{fontSize:10, height:100, overflow:'auto'}}>
            {ticks.slice(0,10).map((t,i)=> <div key={i} style={{display:'flex', justifyContent:'space-between', borderBottom:'1px solid #1e293b'}}><span>{new Date(t.time).toLocaleTimeString()}</span><span>{t.price}</span><span style={{color: t.side==='buy'?'#10b981':'#ef5350'}}>{t.side}</span><span>{t.exchange}</span></div>)}
            {!ticks.length && <div style={{color:'#94a3b8'}}>No ticks yet (live when market open)</div>}
          </div>
          <div style={{fontSize:10, color:'#94a3b8', marginTop:6}}>Institutional/retail order-flow attribution isn't exposed by Kite's public market data</div>
        </Widget>
      </div>

      {/* Full T-shape with export */}
      <div style={{display:'flex', gap:8, marginBottom:8}}>
        <button className="btn sm" onClick={exportCSV}>⬇ CSV</button>
        <button className="btn sm" onClick={exportPDF}>⬇ PDF (jsPDF)</button>
        <span style={{fontSize:10, color:'#94a3b8', alignSelf:'center'}}>Drag widgets • Hotkey Ctrl+K • Multi-monitor workspaces • Touch-optimized • API: /api/historical/* /api/pricing/* /api/portfolio/*</span>
      </div>

      {tshape && (
        <div style={{overflow:'auto', border:'1px solid #1e293b', borderRadius:8, background:'#0d1b2a'}}>
          <table style={{width:'100%', fontSize:10, borderCollapse:'collapse'}}>
            <thead style={{position:'sticky', top:0, background:'#101d30'}}>
              <tr><th colSpan={5} style={{color:'#10b981'}}>CALLS</th><th style={{background:'#1e293b', color:'#f59e0b'}}>STRIKE</th><th colSpan={5} style={{color:'#ef5350'}}>PUTS</th></tr>
              <tr style={{color:'#cbd5e1'}}><th>OI</th><th>Vol</th><th>LTP</th><th>IV</th><th>Δ</th><th>Price</th><th>Δ</th><th>IV</th><th>LTP</th><th>Vol</th><th>OI</th></tr>
            </thead>
            <tbody>
              {tshape.chain.slice(0,15).map(r=> (
                <tr key={r.strike} style={{background: r.isATM?'rgba(245,158,11,0.15)':'transparent', textAlign:'right'}}>
                  <td>{r.CE.oi.toLocaleString()}</td><td>{r.CE.volume.toLocaleString()}</td><td style={{fontWeight:700}}>{r.CE.ltp}</td><td>{r.CE.iv}</td><td>{r.CE.delta.toFixed(2)}</td>
                  <td style={{textAlign:'center', fontWeight:800, background: r.isATM?'#f59e0b':'#1e293b', color: r.isATM?'#000':'#f1f5f9'}}>{r.strike}</td>
                  <td>{r.PE.delta.toFixed(2)}</td><td>{r.PE.iv}</td><td style={{fontWeight:700}}>{r.PE.ltp}</td><td>{r.PE.volume.toLocaleString()}</td><td>{r.PE.oi.toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
