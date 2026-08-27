import React, { useEffect, useState } from 'react'
import { fetchStockDetail } from '../services/api.js'
import MiniChart from '../charts/MiniChart.jsx'
import { fmtPrice, fmtPct, fmtVol } from '../utils/format.js'

export default function DetailPanel({ symbol, onClose, liveState }){
  const [detail, setDetail] = useState(null)
  const [loading, setLoading] = useState(false)
  const [interval, setInterval] = useState('1m')

  useEffect(()=>{
    if(!symbol) return
    setLoading(true)
    fetchStockDetail(symbol).then(d=> setDetail(d)).catch(()=> setDetail(liveState)).finally(()=> setLoading(false))
    const id=setInterval(()=> fetchStockDetail(symbol).then(d=> setDetail(d)).catch(()=>{}), 5000)
    return ()=> clearInterval(id)
  }, [symbol])

  // merge live ticks into detail for real-time
  // normalize detail if it comes from flat API
  const normDetail = detail ? {
    ...detail,
    companyName: detail.companyName || detail.company,
    changePercent: detail.changePercent ?? detail.change_pct,
    previousClose: detail.previousClose ?? detail.previous_close,
    relVolume: detail.relVolume ?? detail.rel_volume,
    isAboveVwap: detail.isAboveVwap ?? detail.is_above_vwap,
    vwap: detail.vwap ?? detail.indicators?.vwap,
    rsi: detail.rsi ?? detail.indicators?.rsi,
    ema9: detail.ema9 ?? detail.indicators?.ema9,
    ema20: detail.ema20 ?? detail.indicators?.ema20,
    atr: detail.atr ?? detail.indicators?.atr,
  } : null
  const stateRaw = liveState || normDetail || detail
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
  if(!symbol) return <div className="detail-panel" style={{padding:20, color:'#5a6b84'}}>Select a stock to see details</div>
  if(!state) return <div className="detail-panel" style={{padding:20}}>Loading {symbol}...</div>

  // candles: try multiple key formats (detail.candles is object with "1","5" etc, also "1m")
  const getCandles = (src, iv)=>{
    if(!src) return []
    return src[iv] || src[iv.replace('m','')] || src[iv.replace('m','m')] || []
  }
  const candles = getCandles(detail?.candles, interval) || getCandles(liveState?.candles, interval) || []
  // if no candles, fabricate from ltp? just show single

  return (
    <div className="detail-panel open" style={{padding:14, gap:12, display:'flex', flexDirection:'column'}}>
      <div style={{display:'flex', justifyContent:'space-between', alignItems:'center'}}>
        <div>
          <div style={{fontSize:18, fontWeight:800}}>{state.symbol} <span style={{fontSize:11, fontWeight:400, color:'#8b9bb4'}}>{state.companyName}</span></div>
          <div style={{fontSize:11, color:'#8b9bb4'}}>{state.sector} • {state.industry}</div>
        </div>
        <button className="btn sm" onClick={onClose}>✕</button>
      </div>

      <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:8}}>
        <div style={{background:'#0d1218', border:'1px solid #232d38', borderRadius:8, padding:10}}>
          <div style={{fontSize:22, fontWeight:700}}>{fmtPrice(state.ltp)} <span style={{fontSize:12, color: (state.changePercent||0)>=0 ? '#00d38d' : '#ff4757'}}>{fmtPct(state.changePercent)}</span></div>
          <div style={{fontSize:11, color:'#8b9bb4'}}>O {fmtPrice(state.open)} H {fmtPrice(state.high)} L {fmtPrice(state.low)} C {fmtPrice(state.previousClose)}</div>
          <div style={{fontSize:11, color:'#8b9bb4'}}>Vol {fmtVol(state.volume)} • Rel {state.relVolume? state.relVolume.toFixed(2)+'x':'-'} • Bid {state.bid? fmtPrice(state.bid):'-'} / Ask {state.ask? fmtPrice(state.ask):'-'}</div>
        </div>
        <div style={{background:'#0d1218', border:'1px solid #232d38', borderRadius:8, padding:10}}>
          <div style={{fontSize:11, color:'#8b9bb4'}}>Signal</div>
          <div><span className={`signal ${state.signal}`}>{state.signal}</span> <span style={{fontSize:11, color:'#8b9bb4'}}>{state.signalStrength}</span></div>
          <div style={{marginTop:6, fontSize:12}}>Score <b style={{color: state.score>=70?'#00d38d': state.score>=40?'#f6c343':'#8b9bb4'}}>{state.score?.toFixed(1)}</b></div>
          <div className="score-bar"><span className="score-fill" style={{width:`${Math.min(100,state.score)}%`, background: state.score>=70?'#00d38d': state.score>=40?'#f6c343':'#5a6b84'}} /></div>
          <div style={{fontSize:10, color:'#5a6b84', marginTop:4}}>NOT investment advice</div>
        </div>
      </div>

      <div style={{display:'flex', gap:6, flexWrap:'wrap'}}>
        <div style={{fontSize:11, color:'#8b9bb4'}}>VWAP</div> <b style={{fontSize:12, color: state.isAboveVwap? '#00d38d':'#ff4757'}}>{state.vwap? fmtPrice(state.vwap): '-'}</b> <span style={{fontSize:11}}>{state.isAboveVwap? 'ABOVE':'BELOW'}</span>
        <span style={{marginLeft:8, fontSize:11, color:'#8b9bb4'}}>RSI</span> <b>{state.rsi? state.rsi.toFixed(1):'-'}</b>
        <span style={{marginLeft:8, fontSize:11, color:'#8b9bb4'}}>EMA9</span> <b>{state.ema9? fmtPrice(state.ema9):'-'}</b>
        <span style={{marginLeft:8, fontSize:11, color:'#8b9bb4'}}>EMA20</span> <b>{state.ema20? fmtPrice(state.ema20):'-'}</b>
        <span style={{marginLeft:8, fontSize:11, color:'#8b9bb4'}}>ATR</span> <b>{state.atr? fmtPrice(state.atr):'-'}</b>
      </div>

      <div style={{display:'flex', gap:4}}>
        {['1m','3m','5m','15m','30m'].map(it=>(
          <button key={it} className={`btn sm ${interval===it?'active':''}`} onClick={()=> setInterval(it)}>{it}</button>
        ))}
      </div>

      <div className="chart-wrap">
        <MiniChart candles={candles.slice(-50)} vwap={state.vwap} ema9={state.ema9} ema20={state.ema20} />
        <div className="legend" style={{position:'absolute', top:8, left:12}}>
          <span style={{color:'#f6c343'}}>─ VWAP</span> <span style={{color:'#3b9eff'}}>─ EMA9</span> <span style={{color:'#8b5cf6'}}>─ EMA20</span>
        </div>
      </div>

      {state.indicators && (
        <div style={{background:'#0d1218', border:'1px solid #232d38', borderRadius:8, padding:10, fontSize:11}}>
          <div style={{color:'#8b9bb4', marginBottom:6}}>Indicators • Derived</div>
          <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:6}}>
            <div>RSI <b>{state.indicators?.rsi?.toFixed(1) || state.rsi?.toFixed(1) || '-'}</b></div>
            <div>ATR <b>{state.indicators?.atr?.toFixed(2) || '-'}</b></div>
            <div>MACD <b>{state.indicators?.macd?.toFixed(2) || '-'}</b> / {state.indicators?.macd_signal?.toFixed(2) || '-'}</div>
            <div>BB <b>{state.indicators?.bb_upper?.toFixed(1) || '-'}</b> - {state.indicators?.bb_lower?.toFixed(1) || '-'}</div>
            <div>ADX <b>{state.indicators?.adx?.toFixed(1) || '-'}</b></div>
            <div>Gap <b>{state.gapPercent? state.gapPercent.toFixed(2)+'%':'-'}</b></div>
            <div>Mom 1m <b>{state.derived?.ret_1m?.toFixed(2) || state.momentum1m?.toFixed(2) || '-' }%</b></div>
            <div>Mom 5m <b>{state.derived?.ret_5m?.toFixed(2) || state.momentum5m?.toFixed(2) || '-' }%</b></div>
            <div>Range <b>{state.derived?.range_percent?.toFixed(2) || '-' }%</b></div>
            <div>Dist High <b>{state.derived?.distance_from_high?.toFixed(2) || state.distanceFromHigh?.toFixed(2) || '-' }%</b></div>
          </div>
          <div style={{marginTop:8, fontSize:10, color:'#5a6b84'}}>Stale handling: <b style={{color: state.freshness==='LIVE'?'#00d38d':'#ff4757'}}>{state.freshness}</b> • Breakout {String(state.isBreakout)} • Volume spike {String(state.volumeSpike || state.derived?.volume_spike)}</div>
        </div>
      )}

      <div style={{background:'#0d1218', border:'1px solid #232d38', borderRadius:8, padding:10}}>
        <div style={{fontSize:12, fontWeight:700, marginBottom:6}}>Score Breakdown</div>
        {state.scoreBreakdown && Object.entries(state.scoreBreakdown).map(([k,v])=>(
          <div key={k} style={{display:'flex', justifyContent:'space-between', fontSize:11, padding:'2px 0'}}>
            <span style={{textTransform:'capitalize', color:'#8b9bb4'}}>{k}</span><span>{v}</span>
          </div>
        ))}
        {!state.scoreBreakdown && <div style={{fontSize:11, color:'#5a6b84'}}>No breakdown yet</div>}
      </div>

      <div>
        <div style={{fontSize:12, fontWeight:700, marginBottom:6}}>Recent Alerts</div>
        {detail?.recentAlerts?.length ? detail.recentAlerts.map(a=>(
          <div key={a.id} className={`alert ${a.level}`}>
            <span style={{fontWeight:700}}>{a.type}</span> {a.message} <span style={{marginLeft:'auto', fontSize:10, color:'#5a6b84'}}>{new Date(a.timestamp).toLocaleTimeString()}</span>
          </div>
        )) : <div style={{fontSize:11, color:'#5a6b84'}}>No alerts yet</div>}
      </div>
    </div>
  )
}
