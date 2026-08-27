import { useEffect, useState } from 'react'
import { api } from '../api'
import { StockRow, Candle } from '../types'
import { fmt, fmtPct } from '../utils/format'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ComposedChart, Bar, Area } from 'recharts'

export function StockDetailPanel({ symbol, onClose }: { symbol:string|null, onClose:()=>void }) {
  const [detail,setDetail]=useState<any>(null)
  const [candleInterval,setCandleInterval]=useState('5')
  const [liveRow,setLiveRow]=useState<StockRow|null>(null)

  useEffect(()=>{
    if(!symbol) return
    api.stockDetail(symbol).then(setDetail).catch(()=>{})
    const id=window.setInterval(()=> api.stockDetail(symbol).then(setDetail).catch(()=>{}), 5000)
    return ()=> window.clearInterval(id)
  },[symbol])

  if(!symbol) return <div className="p-6 text-gray-500 text-sm border-l border-[#1e2a36]">Select a stock to view details</div>
  if(!detail) return <div className="p-6 text-gray-400">Loading {symbol}...</div>

  const candles: Candle[] = detail.candles?.[candleInterval] || []
  const chartData = candles.map(c=> ({
    time: new Date(c.timestamp).toLocaleTimeString('en-IN',{hour:'2-digit',minute:'2-digit', timeZone:'Asia/Kolkata'}),
    close: c.close,
    open: c.open,
    high: c.high,
    low: c.low,
    volume: c.volume,
    ema9: detail.indicators?.ema9,
    ema20: detail.indicators?.ema20,
  }))

  return (
    <div className="p-3 bg-[#111820] border-l border-[#1e2a36] overflow-auto" style={{width:'420px', minWidth:'340px'}}>
      <div className="flex justify-between items-start mb-2">
        <div>
          <div className="font-bold text-white text-sm">{detail.symbol} <span className="text-gray-400 font-normal">{detail.company}</span></div>
          <div className="text-xs text-gray-400">{detail.sector} • {detail.industry}</div>
        </div>
        <button onClick={onClose} className="text-gray-400 hover:text-white">✕</button>
      </div>

      <div className="grid grid-cols-3 gap-2 text-xs mb-3">
        <div className="bg-[#0a0e13] p-2 rounded border border-[#1e2a36]"><div className="text-gray-400">LTP</div><div className="font-mono font-bold text-white">{fmt(detail.ltp,2)}</div><div className={detail.change_pct>=0?'text-emerald-400':'text-red-400'}>{fmtPct(detail.change_pct)}</div></div>
        <div className="bg-[#0a0e13] p-2 rounded border border-[#1e2a36]"><div className="text-gray-400">OHLC</div><div className="font-mono text-[11px]">O {fmt(detail.open)} H {fmt(detail.high)} L {fmt(detail.low)} C {fmt(detail.ltp)}</div><div className="text-gray-500">Prev {fmt(detail.previous_close)}</div></div>
        <div className="bg-[#0a0e13] p-2 rounded border border-[#1e2a36]"><div className="text-gray-400">Vol / RelVol</div><div className="font-mono">{detail.volume?.toLocaleString()}</div><div className={detail.rel_volume>1.5?'text-yellow-300':''}>{detail.rel_volume? detail.rel_volume.toFixed(2)+'x':'-'}</div></div>
      </div>

      <div className="grid grid-cols-2 gap-2 text-[11px] mb-3">
        <div className="bg-[#0a0e13] p-2 rounded border border-[#1e2a36]">VWAP <span className="font-mono float-right">{fmt(detail.indicators?.vwap)}</span><br/>RSI <span className="font-mono float-right">{detail.indicators?.rsi? detail.indicators.rsi.toFixed(1):'-'}</span><br/>ATR <span className="font-mono float-right">{fmt(detail.indicators?.atr)}</span></div>
        <div className="bg-[#0a0e13] p-2 rounded border border-[#1e2a36]">EMA9 <span className="font-mono float-right">{fmt(detail.indicators?.ema9)}</span><br/>EMA20 <span className="font-mono float-right">{fmt(detail.indicators?.ema20)}</span><br/>EMA50 <span className="font-mono float-right">{fmt(detail.indicators?.ema50)}</span></div>
        <div className="bg-[#0a0e13] p-2 rounded border border-[#1e2a36]">Score <span className="float-right font-bold">{Math.round(detail.score)}/100</span><br/><span className="text-[10px] text-gray-500">{JSON.stringify(detail.score_breakdown)}</span></div>
        <div className="bg-[#0a0e13] p-2 rounded border border-[#1e2a36]">Signal <span className="float-right font-bold">{detail.signal}</span><br/>Gap {fmtPct(detail.gap_pct)} Range {fmtPct(detail.range_pct)}</div>
      </div>

      <div className="mb-2 flex gap-1">
        {['1','3','5','15','30'].map(iv=>(
          <button key={iv} onClick={()=>setCandleInterval(iv)} className={`px-2 py-1 text-xs rounded ${candleInterval===iv?'bg-sky-600 text-white':'bg-[#1e2a36] text-gray-300'}`}>{iv}m</button>
        ))}
      </div>

      <div className="bg-[#0a0e13] p-2 rounded border border-[#1e2a36] mb-2">
        <div className="text-xs text-gray-400 mb-1">Intraday ({candleInterval}m) - Close + VWAP/EMA + Volume</div>
        <div style={{height:180}}>
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={chartData}>
              <XAxis dataKey="time" tick={{fontSize:10, fill:'#8a9bb0'}} interval="preserveStartEnd" />
              <YAxis domain={['auto','auto']} tick={{fontSize:10, fill:'#8a9bb0'}} width={50} />
              <Tooltip contentStyle={{background:'#0f1a24', border:'1px solid #1e2a36', fontSize:12}} />
              <Line type="monotone" dataKey="close" stroke="#00d395" dot={false} strokeWidth={1.5} />
              {/* EMAs as reference */}
            </ComposedChart>
          </ResponsiveContainer>
        </div>
        <div className="text-[10px] text-gray-500 mt-1">Candles show OHLC aggregated from ticks; chart updates in real-time via WebSocket</div>
      </div>

      <div className="text-xs">
        <div className="text-gray-400 mb-1">Momentum</div>
        <div className="flex gap-2 font-mono text-[11px]">
          <span>1m {fmtPct(detail.momentum?.ret_1m)}</span>
          <span>3m {fmtPct(detail.momentum?.ret_3m)}</span>
          <span>5m {fmtPct(detail.momentum?.ret_5m)}</span>
          <span>15m {fmtPct(detail.momentum?.ret_15m)}</span>
        </div>
        <div className="mt-1 text-[11px]">
          {detail.momentum?.day_high_breakout && <span className="px-1 py-0.5 bg-emerald-700 rounded mr-1">Day High Breakout</span>}
          {detail.momentum?.day_low_breakdown && <span className="px-1 py-0.5 bg-red-700 rounded mr-1">Breakdown</span>}
          {detail.momentum?.vwap_breakout && <span className="px-1 py-0.5 bg-sky-700 rounded mr-1">VWAP Breakout</span>}
        </div>
      </div>
    </div>
  )
}
