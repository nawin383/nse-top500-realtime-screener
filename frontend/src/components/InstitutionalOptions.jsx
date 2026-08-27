import React, { useEffect, useState } from 'react'

const apiBase = import.meta.env.VITE_API_URL || ''
const fmt = (n,d=2)=> n==null?'-':Number(n).toFixed(d)
const fmtInt = n=> n==null?'-':Number(n).toLocaleString('en-IN')

function Card({title, children, action}){
  return <div style={{background:'#13181e', border:'1px solid #232d38', borderRadius:8, padding:12}}>
    <div style={{display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:8}}>
      <div style={{fontSize:11, color:'#8b9bb4', fontWeight:700, letterSpacing:'.05em', textTransform:'uppercase'}}>{title}</div>
      <div>{action}</div>
    </div>
    <div>{children}</div>
  </div>
}

export default function InstitutionalOptions(){
  const [symbol, setSymbol] = useState('NIFTY')
  const [expiry, setExpiry] = useState('')
  const [expiries, setExpiries] = useState([])
  const [tshape, setTshape] = useState(null)
  const [atm, setAtm] = useState(null)
  const [vol, setVol] = useState(null)
  const [greeks, setGreeks] = useState(null)
  const [vix, setVix] = useState(null)
  const [pcr, setPcr] = useState(null)
  const [oi, setOi] = useState(null)
  const [unusual, setUnusual] = useState(null)
  const [term, setTerm] = useState(null)
  const [scenario, setScenario] = useState(null)
  const [corr, setCorr] = useState(null)
  const [margin, setMargin] = useState(null)
  const [misprice, setMisprice] = useState(null)
  const [ivhv, setIvhv] = useState(null)

  const fetchAll = async ()=>{
    try{
      const base = `${apiBase}/api/options`
      const [ts, a, v, g, iv, pc, o, u, t, sc, cr, mg, mp] = await Promise.all([
        fetch(`${base}/tshape?symbol=${symbol}${expiry?`&expiry=${expiry}`:''}&window=10`).then(r=>r.json()),
        fetch(`${base}/atm-premium?symbol=${symbol}${expiry?`&expiry=${expiry}`:''}`).then(r=>r.json()),
        fetch(`${base}/vol-surface?symbol=${symbol}${expiry?`&expiry=${expiry}`:''}`).then(r=>r.json()),
        fetch(`${base}/greeks-dashboard?symbol=${symbol}${expiry?`&expiry=${expiry}`:''}`).then(r=>r.json()),
        fetch(`${base}/iv-hv?symbol=${symbol}${expiry?`&expiry=${expiry}`:''}`).then(r=>r.json()),
        fetch(`${base}/pcr?symbol=${symbol}${expiry?`&expiry=${expiry}`:''}`).then(r=>r.json()),
        fetch(`${base}/oi-analysis?symbol=${symbol}${expiry?`&expiry=${expiry}`:''}`).then(r=>r.json()),
        fetch(`${base}/unusual?symbol=${symbol}${expiry?`&expiry=${expiry}`:''}`).then(r=>r.json()),
        fetch(`${base}/term-structure?symbol=${symbol}`).then(r=>r.json()),
        fetch(`${base}/scenario?symbol=${symbol}${expiry?`&expiry=${expiry}`:''}`).then(r=>r.json()),
        fetch(`${base}/correlation`).then(r=>r.json()),
        fetch(`${base}/margin-risk?symbol=${symbol}${expiry?`&expiry=${expiry}`:''}`).then(r=>r.json()),
        fetch(`${base}/mispricing?symbol=${symbol}${expiry?`&expiry=${expiry}`:''}`).then(r=>r.json()),
      ])
      setTshape(ts); if(ts.expiries) setExpiries(ts.expiries); setAtm(a); setVol(v); setGreeks(g); setIvhv(iv); setPcr(pc); setOi(o); setUnusual(u); setTerm(t); setScenario(sc); setCorr(cr); setMargin(mg); setMisprice(mp)
      if(!expiry && ts.expiry) setExpiry(ts.expiry)
    }catch(e){ console.error(e)}
  }
  useEffect(()=>{ fetchAll() }, [symbol, expiry])
  useEffect(()=>{ // fetch expiries on symbol change
    fetch(`${apiBase}/api/options/expiries?symbol=${symbol}`).then(r=>r.json()).then(j=>{ setExpiries(j.expiries||[]); if(j.expiries?.length && !expiry) setExpiry(j.expiries[0]) }).catch(()=>{})
  }, [symbol])
  useEffect(()=>{
    // VIX
    fetch(`${apiBase}/api/options/vix`).then(r=>r.json()).then(setVix).catch(()=>{})
    const id=setInterval(fetchAll, 15000)
    return ()=> clearInterval(id)
  }, [symbol, expiry])

  return (
    <div style={{padding:12, background:'#0a0e13', color:'#e6eef8'}}>
      <div style={{display:'flex', gap:10, alignItems:'center', flexWrap:'wrap', marginBottom:12}}>
        <h2 style={{fontSize:16, fontWeight:800, margin:0}}>Institutional Options — {symbol} {expiry} {tshape?.isLastTradingDay && <span style={{fontSize:10, color:'#f6c343', border:'1px solid #f6c343', padding:'2px 6px', borderRadius:999}}>LAST TRADING DAY {tshape?.generatedAt?.slice(0,10)}</span>}</h2>
        <select className="input" value={symbol} onChange={e=> setSymbol(e.target.value)}><option>NIFTY</option><option>SENSEX</option><option>BANKNIFTY</option></select>
        <select className="input" value={expiry} onChange={e=> setExpiry(e.target.value)}>{expiries.map(e=> <option key={e} value={e}>{e}</option>)}</select>
        <span style={{fontSize:11, color:'#8b9bb4'}}>Spot <b style={{color:'#e6eef8'}}>{tshape?.spot}</b> ATM <b style={{color:'#f6c343'}}>{tshape?.atmStrike}</b> Src {tshape?.source}</span>
        <button className="btn sm" onClick={fetchAll}>↻ Refresh</button>
      </div>

      {/* Top analytics row */}
      <div style={{display:'grid', gridTemplateColumns:'repeat(auto-fit, minmax(180px,1fr))', gap:8, marginBottom:12}}>
        <Card title="ATM Premium & Implied Move">{atm && (<><div style={{fontSize:14, fontWeight:700}}>Straddle <span style={{color:'#3b9eff'}}>{fmt(atm.straddle)}</span> <span style={{fontSize:11, color:'#8b9bb4'}}>({fmt(atm.impliedMovePct)}%)</span></div><div style={{fontSize:11}}>CE {fmt(atm.cePremium)} + PE {fmt(atm.pePremium)} — ATM {atm.atmStrike}</div></>)}</Card>
        <Card title="PCR & Sentiment">{pcr && (<><div style={{fontSize:18, fontWeight:700, color: pcr.pcrOi>1?'#00d38d':'#ff4757'}}>{fmt(pcr.pcrOi,3)} <span style={{fontSize:11, color:'#8b9bb4'}}>Vol {fmt(pcr.pcrVol,3)}</span></div><div style={{fontSize:11, color: pcr.sentiment==='bullish'?'#00d38d': pcr.sentiment==='bearish'?'#ff4757':'#8b9bb4'}}>{pcr.sentiment}</div></>)}</Card>
        <Card title="Max Pain & GEX">{oi && (<><div>Max Pain <b style={{color:'#f6c343'}}>{fmtInt(oi.maxPain)}</b></div><div style={{fontSize:11}}>GEX <b style={{color: oi.totalGex>0?'#00d38d':'#ff4757'}}>{fmtInt(oi.totalGex)}</b> {oi.dealerPositioning}</div></>)}</Card>
        <Card title="VIX">{vix && (<><div style={{fontSize:18, fontWeight:700}}>{fmt(vix.vix)} <span style={{fontSize:10, color:'#5a6b84'}}>{vix.source}</span></div><div style={{fontSize:11, color:'#8b9bb4'}}>Corr NIFTY {vix.correlationNifty}</div></>)}</Card>
        <Card title="IV vs HV">{ivhv && (<><div>IV {fmt(ivhv.iv)}% vs HV {fmt(ivhv.hv)}% </div><div style={{fontSize:11, color: ivhv.ivMinusHv>0?'#ff4757':'#00d38d'}}>{ivhv.ivMinusHv? `${fmt(ivhv.ivMinusHv)}% spread`: 'no HV'}</div></>)}</Card>
        <Card title="Margin / VaR">{margin && (<><div>SPAN {fmtInt(margin.spanMargin)} Total {fmtInt(margin.totalMargin)}</div><div style={{fontSize:11}}>VaR99 <b style={{color:'#ff4757'}}>{fmtInt(margin.var99)}</b> ES {fmtInt(margin.expectedShortfall)}</div></>)}</Card>
      </div>

      {/* Vol surface + term structure */}
      <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:8, marginBottom:12}}>
        <Card title="Vol Surface & Skew (25Δ)">{vol && (<><div style={{fontSize:11}}>ATM IV {fmt(vol.atmIv)}% Skew 25Δ {fmt(vol.skew25Delta)}% (Put-CAll)</div><div style={{height:80, background:'#0d1218', borderRadius:4, padding:4, overflow:'auto'}}>{vol.volSurface?.slice(0,12).map((v,i)=> <div key={i} style={{fontSize:10, display:'flex', justifyContent:'space-between'}}><span>{v.strike} {v.type}</span><span style={{color:'#f6c343'}}>{fmt(v.iv)}%</span></div>)}</div></>)}</Card>
        <Card title="Term Structure & Calendar">{term && (<><div style={{fontSize:11}}>Roll Yield {fmt(term.rollYield)}% {term.contango?'Contango':'Backwardation'}</div><div style={{display:'flex', gap:4, marginTop:6}}>{term.points?.map(p=> <div key={p.expiry} style={{flex:1, background:'#0d1218', padding:6, borderRadius:4, textAlign:'center'}}><div style={{fontSize:10, color:'#8b9bb4'}}>{p.expiry.slice(5)}</div><div style={{fontWeight:700}}>{fmt(p.atmIv)}%</div></div>)}</div></>)}</Card>
      </div>

      {/* Greeks heatmap + OI heatmap */}
      <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:8, marginBottom:12}}>
        <Card title="Greeks Dashboard (portfolio)">{greeks && (<><div style={{fontSize:11}}>Δ {fmt(greeks.portfolioDelta)} Γ {fmt(greeks.portfolioGamma,3)} Θ {fmt(greeks.portfolioTheta)} Vega {fmt(greeks.portfolioVega)}</div><div style={{height:100, overflow:'auto', marginTop:6}}>{greeks.heatmap?.slice(0,10).map(h=> <div key={h.strike} style={{fontSize:10, display:'flex', gap:8}}><span style={{width:60}}>{h.strike}</span><span>ΔExp {fmt(h.deltaExposure)}</span><span>ΓExp {fmt(h.gammaExposure,1)}</span></div>)}</div></>)}</Card>
        <Card title="OI Heatmap & GEX Levels">{oi && (<><div style={{height:120, overflow:'auto'}}>{oi.heatmap?.slice(0,12).map(h=> <div key={h.strike} style={{fontSize:10, display:'flex', gap:6, alignItems:'center'}}><span style={{width:50}}>{h.strike}</span><span style={{flex:1, height:6, background:'#1e2a36'}}><span style={{display:'block', height:'100%', width:`${Math.min(100, h.ceOi/3000000*100)}%`, background:'#00d38d'}}/></span><span style={{flex:1, height:6, background:'#1e2a36'}}><span style={{display:'block', height:'100%', width:`${Math.min(100, h.peOi/3000000*100)}%`, background:'#ff4757'}}/></span><span>{fmtInt(h.netOi)}</span></div>)}</div><div style={{fontSize:10, color:'#5a6b84', marginTop:6}}>GEX levels: {oi.gexLevels?.slice(0,3).map(g=> `${g.strike}:${fmtInt(g.gex)}`).join(' • ')}</div></>)}</Card>
      </div>

      {/* Unusual + Mispricing + Scenario */}
      <div style={{display:'grid', gridTemplateColumns:'1fr 1fr 1fr', gap:8, marginBottom:12}}>
        <Card title="Unusual Activity">{unusual && (unusual.unusual?.length? unusual.unusual.map(u=> <div key={`${u.strike}${u.side}`} style={{fontSize:11, borderBottom:'1px solid #1a2129', padding:'4px 0'}}><b>{u.strike}{u.side}</b> {u.type} {u.score?`×${fmt(u.score)}`:''} {u.oiChange?`OI ${fmtInt(u.oiChange)}`:''}</div>) : <div style={{fontSize:11, color:'#5a6b84'}}>No unusual flow</div>)}</Card>
        <Card title="Mispricing Scanner">{misprice && (misprice.mispriced?.length? misprice.mispriced.slice(0,5).map(m=> <div key={`${m.strike}${m.side}`} style={{fontSize:11, display:'flex', justifyContent:'space-between'}}><span>{m.strike}{m.side} {m.arb}</span><span style={{color: m.diffPct>0?'#ff4757':'#00d38d'}}>{fmt(m.diffPct)}%</span></div>) : <div style={{fontSize:11, color:'#5a6b84'}}>{'No >5% mispricing'}</div>)}</Card>
        <Card title="Scenario P&L (ATM straddle)">{scenario && (<div style={{fontSize:10}}>{scenario.scenarios?.slice(0,5).map((s,i)=> <div key={i} style={{display:'flex', justifyContent:'space-between'}}><span>{s.priceMove} {s.ivMove}</span><span style={{color: s.pnl>0?'#00d38d':'#ff4757'}}>{fmt(s.pnl)}</span></div>)}</div>)}</Card>
      </div>

      {/* T-shape full */}
      {tshape && (
        <Card title={`T-Shape — ${tshape.symbol} ${tshape.expiry} ±10 strikes`}>
          <div style={{overflow:'auto', maxHeight:400}}>
            <table style={{width:'100%', fontSize:10, borderCollapse:'collapse'}}>
              <thead style={{position:'sticky', top:0, background:'#0f141a'}}>
                <tr><th colSpan={5} style={{color:'#00d38d'}}>CALLS</th><th style={{background:'#1a2129', color:'#f6c343'}}>STRIKE</th><th colSpan={5} style={{color:'#ff4757'}}>PUTS</th></tr>
                <tr style={{color:'#8b9bb4'}}><th>OI</th><th>Vol</th><th>LTP</th><th>IV</th><th>Δ</th><th>Price</th><th>Δ</th><th>IV</th><th>LTP</th><th>Vol</th><th>OI</th></tr>
              </thead>
              <tbody>
                {tshape.chain.map(r=> (
                  <tr key={r.strike} style={{background: r.isATM?'rgba(246,195,67,0.15)': r.strike < tshape.spot?'rgba(0,211,141,0.04)':'rgba(255,71,87,0.04)', textAlign:'right'}}>
                    <td>{fmtInt(r.CE.oi)}</td><td>{fmtInt(r.CE.volume)}</td><td style={{fontWeight:700}}>{fmt(r.CE.ltp)}</td><td>{fmt(r.CE.iv,1)}</td><td>{fmt(r.CE.delta,2)}</td>
                    <td style={{textAlign:'center', fontWeight:800, background: r.isATM?'#f6c343':'#1a2129', color: r.isATM?'#000':'#e6eef8'}}>{fmtInt(r.strike)}{r.isATM?' ★':''}</td>
                    <td>{fmt(r.PE.delta,2)}</td><td>{fmt(r.PE.iv,1)}</td><td style={{fontWeight:700}}>{fmt(r.PE.ltp)}</td><td>{fmtInt(r.PE.volume)}</td><td>{fmtInt(r.PE.oi)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Correlation + other */}
      <div style={{marginTop:12, display:'grid', gridTemplateColumns:'1fr 1fr', gap:8}}>
        <Card title="Correlation Matrix">{corr && (<div style={{fontSize:10}}><div style={{display:'grid', gridTemplateColumns:`repeat(${corr.symbols.length+1},1fr)`, gap:2}}><div></div>{corr.symbols.map(s=> <div key={s} style={{fontWeight:700, textAlign:'center'}}>{s.slice(0,4)}</div>)}{corr.symbols.map(a=> (<React.Fragment key={a}><div style={{fontWeight:700}}>{a.slice(0,4)}</div>{corr.symbols.map(b=> <div key={b} style={{textAlign:'center', background:`rgba(59,158,255,${corr.matrix[a][b]})`, padding:'2px'}}>{fmt(corr.matrix[a][b],2)}</div>)}</React.Fragment>))}</div></div>)}</Card>
        <Card title="VIX & Term">{vix && term && (<><div>VIX {fmt(vix.vix)} ({vix.source})</div><div style={{fontSize:11, color:'#8b9bb4'}}>Contango: {String(term.contango)} Roll {fmt(term.rollYield)}%</div></>)}</Card>
      </div>
    </div>
  )
}
