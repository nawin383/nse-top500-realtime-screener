import React, { useEffect, useMemo, useState, Suspense, lazy } from 'react'
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, Cell, Legend } from 'recharts'

const OpenInterestChart = lazy(()=> import('./OpenInterestChart.jsx'))

const fmt = (n,d=2)=> n==null?'-':Number(n).toFixed(d)
const fmtInt = (n)=> n==null?'-':Number(n).toLocaleString('en-IN')

// Same rule as OpenInterestChart: any endpoint that fails or comes back
// {detail:"..."} resolves to null instead of a malformed object, so the JSX
// below only ever has to render "no data" per card -- never crashes the page.
const safeFetch = async (url)=>{
  try{
    const r = await fetch(url)
    const j = await r.json()
    if(!r.ok || j?.detail) return null
    return j
  }catch{ return null }
}

function Card({ title, children, height }){
  return (
    <div style={{background:'rgba(13,27,42,0.6)', border:'1px solid rgba(255,255,255,0.06)', borderRadius:14, padding:14, height}}>
      <div style={{fontSize:10, fontWeight:800, letterSpacing:'0.08em', textTransform:'uppercase', color:'#cbd5e1', marginBottom:10}}>{title}</div>
      {children}
    </div>
  )
}
function Empty({ label='No live data available right now' }){
  return <div style={{fontSize:11, color:'#94a3b8', textAlign:'center', padding:'20px 8px'}}>{label}</div>
}

export default function OptionsInsights({ theme='dark' }){
  const apiBase = import.meta.env.VITE_API_URL || ''
  const [symbol, setSymbol] = useState('NIFTY')
  const [expiries, setExpiries] = useState([])
  const [expiry, setExpiry] = useState('')
  const [atm, setAtm] = useState(null)
  const [pcr, setPcr] = useState(null)
  const [oi, setOi] = useState(null)
  const [vol, setVol] = useState(null)
  const [ivhv, setIvhv] = useState(null)
  const [vix, setVix] = useState(null)
  const [unusual, setUnusual] = useState(null)
  const [strategies, setStrategies] = useState(null)
  const [sellerDash, setSellerDash] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(()=>{
    let cancelled = false
    fetch(`${apiBase}/api/options/expiries?symbol=${symbol}`).then(r=>r.json()).then(j=>{
      if(cancelled) return
      setExpiries(j.expiries||[])
      if(j.expiries?.length) setExpiry(prev=> prev && j.expiries.includes(prev) ? prev : j.expiries[0])
    }).catch(()=>{})
    return ()=>{ cancelled = true }
  }, [symbol, apiBase])

  useEffect(()=>{
    if(!expiry) return
    let cancelled = false
    setLoading(true)
    const q = `symbol=${symbol}&expiry=${expiry}`
    Promise.all([
      safeFetch(`${apiBase}/api/options/atm-premium?${q}`),
      safeFetch(`${apiBase}/api/options/pcr?${q}`),
      safeFetch(`${apiBase}/api/options/oi-analysis?${q}`),
      safeFetch(`${apiBase}/api/options/vol-surface?${q}`),
      safeFetch(`${apiBase}/api/options/iv-hv?${q}`),
      safeFetch(`${apiBase}/api/options/vix`),
      safeFetch(`${apiBase}/api/options/unusual?${q}`),
      safeFetch(`${apiBase}/api/options/strategies?${q}`),
      safeFetch(`${apiBase}/api/options/sellers-premium-dashboard?${q}`),
    ]).then(([a,p,o,v,iv,vx,u,st,sd])=>{
      if(cancelled) return
      setAtm(a); setPcr(p); setOi(o); setVol(v); setIvhv(iv); setVix(vx); setUnusual(u); setStrategies(st); setSellerDash(sd)
    }).finally(()=>{ if(!cancelled) setLoading(false) })
    return ()=>{ cancelled = true }
  }, [symbol, expiry, apiBase])

  // IV skew: CE vs PE implied vol per strike, from the real live chain -- a chart
  // that isn't rendered anywhere else in the app.
  const skewData = useMemo(()=>{
    if(!vol?.volSurface) return []
    const byStrike = {}
    for(const p of vol.volSurface){
      byStrike[p.strike] = byStrike[p.strike] || { strike: p.strike }
      byStrike[p.strike][p.type === 'CE' ? 'ceIv' : 'peIv'] = p.iv
    }
    return Object.values(byStrike).sort((a,b)=> a.strike-b.strike)
  }, [vol])

  // Where fresh OI is actually building right now (|oiChange| per strike), not just
  // the static OI level (that's what the Weekly/Monthly OI chart below already shows).
  const oiChangeData = useMemo(()=>{
    if(!oi?.heatmap) return []
    return oi.heatmap.map(h=> ({ strike: h.strike, netOi: h.netOi })).sort((a,b)=> a.strike-b.strike)
  }, [oi])

  const isDark = theme !== 'light'
  const axisColor = isDark ? '#94a3b8' : '#64748b'
  const gridColor = isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)'

  return (
    <div style={{padding:'0 0 20px 0', display:'flex', flexDirection:'column', gap:14}}>
      <div style={{display:'flex', gap:10, alignItems:'center', flexWrap:'wrap'}}>
        <h2 style={{fontSize:16, fontWeight:800, margin:0}}>Options Insights</h2>
        <select className="input" value={symbol} onChange={e=>setSymbol(e.target.value)}>
          <option value="NIFTY">NIFTY 50</option>
          <option value="SENSEX">SENSEX</option>
          <option value="BANKNIFTY">BANKNIFTY</option>
        </select>
        <select className="input" value={expiry} onChange={e=>setExpiry(e.target.value)} style={{minWidth:140}}>
          {expiries.map(e=> <option key={e} value={e}>{e}</option>)}
          {!expiries.length && <option>Loading…</option>}
        </select>
        {loading && <span style={{fontSize:11, color:'#94a3b8'}}>Refreshing…</span>}
        <span style={{marginLeft:'auto', fontSize:10, color:'#94a3b8'}}>All figures from the live option chain • real data only, gaps shown as "no data"</span>
      </div>

      <div style={{display:'grid', gridTemplateColumns:'repeat(auto-fit, minmax(200px,1fr))', gap:10}}>
        <Card title="ATM Premium & Implied Move">
          {atm ? <>
            <div style={{fontSize:18, fontWeight:800, color:'#64b5f6'}}>{fmt(atm.straddle)} <span style={{fontSize:11, color:'#cbd5e1'}}>({fmt(atm.impliedMovePct)}%)</span></div>
            <div style={{fontSize:11, color:'#cbd5e1', marginTop:4}}>CE {fmt(atm.cePremium)} + PE {fmt(atm.pePremium)} — strike {atm.atmStrike}</div>
          </> : <Empty/>}
        </Card>
        <Card title="PCR & Sentiment">
          {pcr ? <>
            <div style={{fontSize:20, fontWeight:800, color: pcr.pcrOi>1?'#10b981':'#ef5350'}}>{fmt(pcr.pcrOi,3)}</div>
            <div style={{fontSize:11, color:'#cbd5e1', marginTop:4}}>Vol PCR {fmt(pcr.pcrVol,3)} · <span style={{color: pcr.sentiment==='bullish'?'#10b981': pcr.sentiment==='bearish'?'#ef5350':'#cbd5e1', fontWeight:700, textTransform:'capitalize'}}>{pcr.sentiment}</span></div>
          </> : <Empty/>}
        </Card>
        <Card title="Max Pain & Dealer Gamma">
          {oi ? <>
            <div style={{fontSize:20, fontWeight:800, color:'#f59e0b'}}>{fmtInt(oi.maxPain)}</div>
            <div style={{fontSize:11, color:'#cbd5e1', marginTop:4}}>GEX {fmtInt(oi.totalGex)} · {oi.dealerPositioning}</div>
          </> : <Empty/>}
        </Card>
        <Card title="IV vs HV">
          {ivhv ? <>
            <div style={{fontSize:16, fontWeight:800}}>{fmt(ivhv.iv)}% <span style={{fontSize:11, color:'#cbd5e1', fontWeight:500}}>IV</span></div>
            <div style={{fontSize:11, color:'#cbd5e1', marginTop:4}}>{ivhv.hv!=null ? `HV ${fmt(ivhv.hv)}% · spread ${fmt(ivhv.ivMinusHv)}%` : 'HV needs ingested history'}</div>
          </> : <Empty/>}
        </Card>
        <Card title="India VIX">
          {vix?.vix!=null ? <>
            <div style={{fontSize:20, fontWeight:800}}>{fmt(vix.vix)}</div>
            <div style={{fontSize:11, color:'#cbd5e1', marginTop:4}}>Source: {vix.source}</div>
          </> : <Empty label="VIX unavailable (NSE unreachable)"/>}
        </Card>
      </div>

      <Card title="Open Interest — Weekly / Monthly Profile">
        <Suspense fallback={<div style={{height:320,background:'rgba(255,255,255,0.04)',borderRadius:12}}/>}>
          <OpenInterestChart theme={theme} />
        </Suspense>
      </Card>

      <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:10}}>
        <Card title="IV Skew — Calls vs Puts by Strike" height={320}>
          {skewData.length ? (
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={skewData} margin={{top:4,right:16,bottom:4,left:0}}>
                <CartesianGrid stroke={gridColor} strokeDasharray="3 3" />
                <XAxis dataKey="strike" tick={{fill:axisColor,fontSize:10}} stroke={gridColor} />
                <YAxis tick={{fill:axisColor,fontSize:10}} stroke={gridColor} unit="%" />
                <Tooltip contentStyle={{background: isDark?'#0d1b2a':'#fff', border:'1px solid rgba(255,255,255,0.1)', borderRadius:8, fontSize:11}} />
                <Legend wrapperStyle={{fontSize:11}} />
                <Line type="monotone" dataKey="ceIv" name="Call IV" stroke="#10b981" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="peIv" name="Put IV" stroke="#ef5350" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          ) : <Empty/>}
        </Card>
        <Card title="Net OI Change by Strike (where flow is building now)" height={320}>
          {oiChangeData.length ? (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={oiChangeData} margin={{top:4,right:16,bottom:4,left:0}}>
                <CartesianGrid stroke={gridColor} strokeDasharray="3 3" />
                <XAxis dataKey="strike" tick={{fill:axisColor,fontSize:10}} stroke={gridColor} />
                <YAxis tick={{fill:axisColor,fontSize:10}} stroke={gridColor} tickFormatter={fmtInt} />
                <Tooltip contentStyle={{background: isDark?'#0d1b2a':'#fff', border:'1px solid rgba(255,255,255,0.1)', borderRadius:8, fontSize:11}} formatter={(v)=>[fmtInt(v),'Net OI (Put − Call)']} />
                <ReferenceLine y={0} stroke={axisColor} />
                <Bar dataKey="netOi">
                  {oiChangeData.map((d,i)=> <Cell key={i} fill={d.netOi>=0 ? '#ef5350' : '#10b981'} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : <Empty/>}
        </Card>
      </div>

      <Card title="Unusual Activity">
        {unusual?.unusual?.length ? (
          <div style={{display:'flex', flexDirection:'column', gap:4}}>
            {unusual.unusual.map(u=> (
              <div key={`${u.strike}${u.side}`} style={{display:'flex', justifyContent:'space-between', fontSize:11, padding:'6px 0', borderBottom:'1px solid rgba(255,255,255,0.04)'}}>
                <span><b>{u.strike} {u.side}</b> <span style={{color:'#cbd5e1'}}>{u.type}</span></span>
                <span style={{color:'#cbd5e1'}}>{u.score ? `×${fmt(u.score)} avg` : ''} {u.oiChange!=null ? `OI ${fmtInt(u.oiChange)}` : ''}</span>
              </div>
            ))}
          </div>
        ) : <Empty label="No unusual flow detected"/>}
      </Card>

      <Card title="Options Strategy Panel">
        {strategies ? (
          <div style={{display:'flex', flexDirection:'column', gap:6}}>
            <div style={{fontSize:10, color:'#94a3b8', marginBottom:2}}>IV rank (1y) {strategies.iv_rank_1y!=null ? `${fmt(strategies.iv_rank_1y,0)}%` : 'unavailable'} · ADX {strategies.adx!=null ? fmt(strategies.adx,1) : 'not supplied'}</div>
            {['short_strangle','iron_condor','bull_put_spread','bear_call_spread','iron_fly','ratio_spread_1x2','calendar_spread'].map(key=>{
              const s = strategies[key]
              if(!s) return null
              if(s.error) return <div key={key} style={{fontSize:11, color:'#475569', padding:'6px 0', borderBottom:'1px solid rgba(255,255,255,0.04)'}}><b style={{color:'#94a3b8'}}>{key.replace(/_/g,' ')}</b> — {s.error}</div>
              const eligible = s.regime?.eligible
              return (
                <div key={key} style={{display:'flex', gap:10, alignItems:'center', flexWrap:'wrap', fontSize:11, padding:'6px 0', borderBottom:'1px solid rgba(255,255,255,0.04)'}}>
                  <b style={{color:'#f1f5f9', minWidth:130, textTransform:'capitalize'}}>{key.replace(/_/g,' ')}</b>
                  {eligible!=null && <span style={{fontSize:9, fontWeight:800, padding:'1px 7px', borderRadius:999, background: eligible?'rgba(16,185,129,0.15)':'rgba(239,83,80,0.12)', color: eligible?'#10b981':'#ef5350'}}>{eligible?'ELIGIBLE':'NOT ELIGIBLE'}</span>}
                  <span className="mono" style={{color:'#cbd5e1'}}>Net {fmt(s.net_premium)}</span>
                  <span className="mono" style={{color:'#94a3b8'}}>Max L {typeof s.max_loss==='string'? s.max_loss : fmt(s.max_loss)}</span>
                  {s.pop_pct!=null && <span className="mono" style={{color:'#64b5f6'}}>POP {fmt(s.pop_pct,0)}%</span>}
                  {s.theta!=null && <span className="mono" style={{color:'#94a3b8'}}>θ {fmt(s.theta)}</span>}
                  {s.margin_estimate!=null && <span className="mono" style={{color:'#94a3b8'}}>Margin ~{fmtInt(s.margin_estimate)}</span>}
                </div>
              )
            })}
          </div>
        ) : <Empty label="Strategy panel needs a live option chain"/>}
      </Card>

      <div style={{display:'grid', gridTemplateColumns:'repeat(auto-fit, minmax(220px,1fr))', gap:10}}>
        <Card title="Seller's Premium — Favorability Score">
          {sellerDash?.favorability_score?.score!=null ? <>
            <div style={{fontSize:22, fontWeight:800, color: sellerDash.favorability_score.score>=65?'#10b981': sellerDash.favorability_score.score<=35?'#ef5350':'#f59e0b'}}>{fmt(sellerDash.favorability_score.score,0)}<span style={{fontSize:11,color:'#94a3b8'}}>/100</span></div>
            <div style={{fontSize:11, color:'#cbd5e1', marginTop:4, textTransform:'capitalize'}}>{sellerDash.favorability_score.label}</div>
            <div style={{fontSize:9, color:'#64748b', marginTop:2}}>coverage {fmt(sellerDash.favorability_score.coverage_pct,0)}% of components available</div>
          </> : <Empty label="Not enough regime data yet"/>}
        </Card>
        <Card title="VIX Mean-Reversion Z-Score">
          {sellerDash?.vix_mean_reversion?.z_score!=null ? <>
            <div style={{fontSize:20, fontWeight:800, color: sellerDash.vix_mean_reversion.z_score>1?'#10b981': sellerDash.vix_mean_reversion.z_score<-1?'#ef5350':'#cbd5e1'}}>{fmt(sellerDash.vix_mean_reversion.z_score)}σ</div>
            <div style={{fontSize:11, color:'#cbd5e1', marginTop:4}}>{sellerDash.vix_mean_reversion.interpretation}</div>
            <div style={{fontSize:9, color:'#64748b', marginTop:2}}>current {fmt(sellerDash.vix_mean_reversion.current)} · mean {fmt(sellerDash.vix_mean_reversion.mean)} · n={sellerDash.vix_mean_reversion.sample_size}</div>
          </> : <Empty label={sellerDash?.vix_mean_reversion?.reason || 'VIX history unavailable'}/>}
        </Card>
        <Card title="IV − Realized Vol Spread">
          {sellerDash?.iv_rv_spread?.spread!=null ? <>
            <div style={{fontSize:20, fontWeight:800, color: sellerDash.iv_rv_spread.spread>2?'#10b981': sellerDash.iv_rv_spread.spread<-2?'#ef5350':'#cbd5e1'}}>{fmt(sellerDash.iv_rv_spread.spread)}pts</div>
            <div style={{fontSize:11, color:'#cbd5e1', marginTop:4}}>{sellerDash.iv_rv_spread.interpretation}</div>
            <div style={{fontSize:9, color:'#64748b', marginTop:2}}>IV {fmt(sellerDash.iv_rv_spread.current_iv)}% · realized {fmt(sellerDash.iv_rv_spread.realized_vol)}%</div>
          </> : <Empty label={sellerDash?.iv_rv_spread?.reason || 'price history unavailable'}/>}
        </Card>
        <Card title="Expiry-Day Pin Risk">
          {sellerDash?.expiry_pin_risk?.pin_risk_score!=null ? <>
            <div style={{fontSize:20, fontWeight:800, color: sellerDash.expiry_pin_risk.pin_risk_score>=65?'#f59e0b':'#cbd5e1'}}>{fmt(sellerDash.expiry_pin_risk.pin_risk_score,0)}</div>
            <div style={{fontSize:11, color:'#cbd5e1', marginTop:4, textTransform:'capitalize'}}>{sellerDash.expiry_pin_risk.label}{sellerDash.expiry_pin_risk.is_expiry_day ? ' · TODAY IS EXPIRY' : ''}</div>
            <div style={{fontSize:9, color:'#64748b', marginTop:2}}>{fmt(sellerDash.expiry_pin_risk.distance_to_max_pain_pct)}% from max pain · {fmt(sellerDash.expiry_pin_risk.oi_concentration_near_money_pct)}% OI near spot</div>
          </> : <Empty label={sellerDash?.expiry_pin_risk?.reason || 'chain/max-pain unavailable'}/>}
        </Card>
      </div>
    </div>
  )
}
