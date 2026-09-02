import React, { useEffect, useState } from 'react'
import { fetchStockDetail } from '../services/api.js'
import MiniChart from '../charts/MiniChart.jsx'
import { fmtPrice, fmtPct, fmtVol } from '../utils/format.js'

export default function DetailPanel({ symbol, onClose, liveState, theme='dark' }){
  const [detail, setDetail] = useState(null)
  const [intervalKey, setIntervalKey] = useState('1m')

  useEffect(()=>{
    if(!symbol) return
    fetchStockDetail(symbol).then(d=> setDetail(d)).catch(()=> setDetail(liveState))
    const id=window.setInterval(()=> fetchStockDetail(symbol).then(d=> setDetail(d)).catch(()=>{}), 8000)
    return ()=> window.clearInterval(id)
  }, [symbol])

  const stateRaw = liveState || detail
  const state = stateRaw ? {
    ...stateRaw,
    companyName: stateRaw.companyName || stateRaw.company,
    changePercent: stateRaw.changePercent ?? stateRaw.change_pct,
    previousClose: stateRaw.previousClose ?? stateRaw.previous_close,
    relVolume: stateRaw.relVolume ?? stateRaw.rel_volume,
    isAboveVwap: stateRaw.isAboveVwap ?? stateRaw.is_above_vwap,
    vwap: stateRaw.vwap ?? stateRaw.indicators?.vwap,
    rsi: stateRaw.rsi ?? stateRaw.indicators?.rsi,
    ema9: stateRaw.ema9 ?? stateRaw.indicators?.ema9,
    ema20: stateRaw.ema20 ?? stateRaw.indicators?.ema20,
    atr: stateRaw.atr ?? stateRaw.indicators?.atr,
  } : null

  if(!symbol) return <div className="detail-panel" style={{padding:24, color:'#94a3b8', display:'grid', placeItems:'center', textAlign:'center'}}><div><div style={{width:48,height:48, borderRadius:16, background:'linear-gradient(135deg, rgba(37,99,235,0.12), rgba(16,185,129,0.08))', display:'grid', placeItems:'center', margin:'0 auto 12px'}}>◈</div><div style={{fontWeight:700, color:'#f1f5f9'}}>Select a stock</div><div style={{fontSize:11, marginTop:4}}>Click any row to inspect depth, chart & signals</div></div></div>
  if(!state) return <div className="detail-panel" style={{padding:20}}>Loading {symbol}...</div>

  const getCandles = (src, iv)=> src ? (src[iv] || src[iv.replace('m','')] || []) : []
  const candles = getCandles(detail?.candles, intervalKey) || []
  const candleCount = candles.length
  const warming = candleCount < 14
  const isPos = (state.changePercent||0) >=0
  return (
    <div className="detail-panel open" style={{padding:16, gap:14, display:'flex', flexDirection:'column'}}>
      <div style={{display:'flex', justifyContent:'space-between', alignItems:'flex-start', gap:12}}>
        <div style={{minWidth:0}}>
          <div style={{fontSize:18, fontWeight:900, letterSpacing:'-0.02em', display:'flex', gap:8, alignItems:'center', flexWrap:'wrap'}}>{state.symbol} <span className={`signal ${state.signal}`} style={{fontSize:9}}>{state.signal}</span> {state.synthetic && <span style={{fontSize:9, background:'rgba(245,158,11,0.12)', color:'#f59e0b', padding:'3px 8px', borderRadius:999, border:'1px solid rgba(245,158,11,0.2)', fontWeight:800}}>MARKET CLOSED</span>}</div>
          <div style={{fontSize:11, color:'#cbd5e1', whiteSpace:'nowrap', overflow:'hidden', textOverflow:'ellipsis', fontWeight:600}}>{state.companyName}</div>
          <div style={{fontSize:10, color:'#94a3b8', background:'rgba(255,255,255,0.04)', padding:'3px 8px', borderRadius:999, display:'inline-block', marginTop:6, border:'1px solid rgba(255,255,255,0.06)'}}>{state.sector} • {state.industry}</div>
        </div>
        <button className="btn sm" onClick={onClose} style={{borderRadius:10, width:32, height:32, padding:0, display:'grid', placeItems:'center'}}>✕</button>
      </div>

      <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:10}}>
        <div style={{background:'linear-gradient(135deg, rgba(22,35,58,0.9), rgba(13,27,42,0.8))', border:'1px solid rgba(255,255,255,0.06)', borderRadius:14, padding:14, backdropFilter:'blur(12px)'}}>
          <div style={{fontSize:24, fontWeight:900, fontFamily:'JetBrains Mono', letterSpacing:'-0.03em'}}>{fmtPrice(state.ltp)} <span style={{fontSize:12, color: isPos ? '#10b981' : '#ef5350', background: isPos?'rgba(16,185,129,0.12)':'rgba(239,83,80,0.12)', padding:'3px 7px', borderRadius:999, border:`1px solid ${isPos?'rgba(16,185,129,0.2)':'rgba(239,83,80,0.2)'}`}}>{fmtPct(state.changePercent)}</span></div>
          <div style={{fontSize:11, color:'#cbd5e1', marginTop:6, fontFamily:'JetBrains Mono'}}>O {fmtPrice(state.open)} H {fmtPrice(state.high)} L {fmtPrice(state.low)} • C {fmtPrice(state.previousClose)}</div>
          <div style={{fontSize:11, color:'#94a3b8', marginTop:4}}>Vol {fmtVol(state.volume)} • Rel {state.relVolume? state.relVolume.toFixed(2)+'x':'—'} • <span style={{color: state.isAboveVwap?'#10b981':'#ef5350', fontWeight:700}}>{state.isAboveVwap?'Above':'Below'} VWAP</span></div>
        </div>
        <div style={{background:'linear-gradient(135deg, rgba(22,35,58,0.9), rgba(13,27,42,0.8))', border:'1px solid rgba(255,255,255,0.06)', borderRadius:14, padding:14}}>
          <div style={{fontSize:10, color:'#94a3b8', fontWeight:800, letterSpacing:'0.08em', textTransform:'uppercase'}}>Signal & Score</div>
          <div style={{marginTop:8, display:'flex', gap:8, alignItems:'center'}}><span className={`signal ${state.signal}`} style={{fontSize:11, padding:'4px 10px'}}>{state.signal}</span> <span style={{fontSize:11, color:'#cbd5e1', fontWeight:600}}>{state.signalStrength?.toFixed? state.signalStrength.toFixed(1): state.signalStrength || '—'}</span></div>
          <div style={{marginTop:10, display:'flex', gap:10, alignItems:'center'}}>
            <span style={{fontSize:18, fontWeight:900, color: state.score>=70?'#10b981': state.score>=40?'#f59e0b':'#cbd5e1', fontFamily:'JetBrains Mono'}}>{state.score?.toFixed(0) ?? '—'}</span>
            <span className="score-bar" style={{flex:1, height:8, borderRadius:999}}><span className="score-fill" style={{width:`${Math.min(100, state.score||0)}%`, background: state.score>=70?'linear-gradient(90deg,#10b981,#2563eb)': state.score>=40?'#f59e0b':'#94a3b8'}} /></span>
          </div>
          <div style={{fontSize:9, color:'#94a3b8', marginTop:6, fontWeight:600, letterSpacing:'0.04em'}}>NOT investment advice • Analytical only</div>
        </div>
      </div>

      <div style={{display:'flex', gap:8, flexWrap:'wrap', background:'rgba(255,255,255,0.03)', padding:8, borderRadius:12, border:'1px solid rgba(255,255,255,0.04)'}}>
        {[
          {k:'VWAP', v: state.vwap? fmtPrice(state.vwap): '—', c: state.isAboveVwap?'#10b981':'#ef5350'},
          {k:'RSI', v: state.rsi? state.rsi.toFixed(1):'—', c: state.rsi>70?'#ef5350': state.rsi<30?'#10b981':'#f1f5f9'},
          {k:'EMA9', v: state.ema9? fmtPrice(state.ema9):'—'},
          {k:'EMA20', v: state.ema20? fmtPrice(state.ema20):'—'},
          {k:'ATR', v: state.atr? fmtPrice(state.atr):'—'},
        ].map(x=> <span key={x.k} style={{fontSize:11, display:'flex', gap:6, alignItems:'center', background:'rgba(13,27,42,0.8)', padding:'6px 10px', borderRadius:999, border:'1px solid rgba(255,255,255,0.06)'}}><span style={{color:'#94a3b8', fontWeight:800, fontSize:9, letterSpacing:'0.06em'}}>{x.k}</span> <b style={{color:x.c||'#f1f5f9', fontFamily:'JetBrains Mono'}}>{x.v}</b></span>)}
      </div>
      {warming && (
        <div style={{background:'rgba(245,158,11,0.08)', border:'1px solid rgba(245,158,11,0.2)', borderRadius:10, padding:'8px 12px', fontSize:11}}>
          <div style={{fontWeight:700, color:'#f59e0b'}}>Warming: {candleCount}/14 candles — RSI needs 14 1m candles (~14min after open)</div>
          <div style={{height:6, background:'rgba(255,255,255,0.08)', borderRadius:999, overflow:'hidden', marginTop:6}}><div style={{height:'100%', width:`${Math.min(100, candleCount/14*100)}%`, background:'#f59e0b', borderRadius:999}} /></div>
          <div style={{fontSize:10, color:'#cbd5e1', marginTop:4}}>{state.rsi==null ? 'RSI = null until 14 candles' : `RSI ${state.rsi.toFixed(1)} warming`}</div>
        </div>
      )}

      <div style={{display:'flex', gap:6}}>
        {['1m','3m','5m','15m','30m'].map(it=>(
          <button key={it} className={`btn sm ${intervalKey===it?'active':''}`} onClick={()=> setIntervalKey(it)} style={{flex:1, borderRadius:10, fontWeight:800, fontFamily:'JetBrains Mono'}}>{it}</button>
        ))}
      </div>

      <div className="chart-wrap" style={{borderRadius:14}}>
        <MiniChart candles={candles.slice(-50)} vwap={state.vwap} ema9={state.ema9} ema20={state.ema20} />
        <div className="legend" style={{position:'absolute', top:10, left:14, background:'rgba(13,27,42,0.85)', padding:'6px 10px', borderRadius:999, border:'1px solid rgba(255,255,255,0.06)', backdropFilter:'blur(8px)'}}>
          <span style={{color:'#f59e0b'}}>─ VWAP</span> <span style={{color:'#2563eb'}}>─ EMA9</span> <span style={{color:'#8b5cf6'}}>─ EMA20</span>
        </div>
        {state.synthetic && <div style={{position:'absolute', bottom:10, right:14, background:'rgba(245,158,11,0.12)', color:'#f59e0b', padding:'4px 8px', borderRadius:999, fontSize:10, fontWeight:800, border:'1px solid rgba(245,158,11,0.2)'}}>LAST CLOSE</div>}
      </div>

      <div style={{background:'rgba(13,27,42,0.6)', border:'1px solid rgba(255,255,255,0.06)', borderRadius:14, padding:14, backdropFilter:'blur(12px)'}}>
        <div style={{fontSize:11, fontWeight:800, letterSpacing:'0.06em', textTransform:'uppercase', color:'#cbd5e1', marginBottom:10}}>Score Breakdown</div>
        {state.score_breakdown || state.scoreBreakdown ? Object.entries(state.score_breakdown||state.scoreBreakdown).map(([k,v])=>(
          <div key={k} style={{display:'flex', justifyContent:'space-between', fontSize:11, padding:'5px 0', borderBottom:'1px solid rgba(255,255,255,0.03)'}}>
            <span style={{textTransform:'capitalize', color:'#cbd5e1', fontWeight:600}}>{k}</span><span style={{fontFamily:'JetBrains Mono', fontWeight:700, color:'#f1f5f9'}}>{typeof v==='number'? v.toFixed(1): String(v)}</span>
          </div>
        )) : <div style={{fontSize:11, color:'#94a3b8', textAlign:'center', padding:12}}>Scoring after first ticks • Momentum 25 + Volume 25 + RelVol 20 + Breakout 15 + VWAP 10 + Volatility 5</div>}
      </div>
    </div>
  )
}
