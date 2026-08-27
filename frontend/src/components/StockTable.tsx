import { useMemo, useState, useRef, useEffect } from 'react'
import { StockRow } from '../types'
import { fmt, fmtInt, fmtPct, colorPct } from '../utils/format'

interface Props {
  rows: StockRow[]
  onSelect: (s:StockRow)=>void
  selected?: string
}

const columns = [
  {k:'rank', label:'Rank', w:'50px'},
  {k:'symbol', label:'Symbol', w:'90px'},
  {k:'ltp', label:'LTP', w:'80px'},
  {k:'change_pct', label:'Chg%', w:'80px'},
  {k:'volume', label:'Vol', w:'90px'},
  {k:'rel_volume', label:'RelVol', w:'70px'},
  {k:'vwap', label:'VWAP', w:'80px'},
  {k:'rsi', label:'RSI', w:'55px'},
  {k:'momentum', label:'Mom 5m', w:'75px'},
  {k:'score', label:'Score', w:'60px'},
  {k:'signal', label:'Signal', w:'110px'},
  {k:'freshness', label:'Fresh', w:'70px'},
]

export function StockTable({rows, onSelect, selected}:Props) {
  const [sortKey,setSortKey]=useState('rank')
  const [order,setOrder]=useState<'asc'|'desc'>('asc')
  const [flashMap,setFlashMap]=useState<Record<string,string>>({})
  const prevRef=useRef<Record<string,number>>({})

  // detect flashes
  useEffect(()=>{
    const next:Record<string,string>={}
    for(const r of rows){
      const prev = prevRef.current[r.symbol]
      if(prev!==undefined && r.ltp!==prev){
        next[r.symbol] = r.ltp>prev ? 'flash-green' : 'flash-red'
      }
      prevRef.current[r.symbol]=r.ltp
    }
    if(Object.keys(next).length){ setFlashMap(next); setTimeout(()=> setFlashMap({}), 650) }
  },[rows])

  const sorted = useMemo(()=>{
    const copy=[...rows]
    copy.sort((a:any,b:any)=>{
      const va = sortKey==='momentum' ? (a.momentum?.ret_5m ?? -999) : (a[sortKey] ?? -999)
      const vb = sortKey==='momentum' ? (b.momentum?.ret_5m ?? -999) : (b[sortKey] ?? -999)
      if(va==null) return 1
      if(vb==null) return -1
      const cmp = typeof va==='string' ? va.localeCompare(vb) : va - vb
      return order==='asc'? cmp : -cmp
    })
    return copy
  },[rows,sortKey,order])

  const toggleSort=(k:string)=>{
    if(sortKey===k) setOrder(o=> o==='asc'?'desc':'asc')
    else { setSortKey(k); setOrder('desc') }
  }

  return (
    <div className="flex flex-col h-full">
      <div className="overflow-auto flex-1 border border-[#1e2a36] bg-[#0a0e13]" style={{maxHeight:'calc(100vh - 280px)'}}>
        <table className="w-full text-xs border-collapse">
          <thead className="sticky top-0 bg-[#111820] z-10">
            <tr>
              {columns.map(c=>(
                <th key={c.k} onClick={()=>toggleSort(c.k)} className="px-2 py-2 text-left font-semibold text-gray-400 border-b border-[#1e2a36] cursor-pointer select-none whitespace-nowrap hover:text-white" style={{minWidth:c.w}}>
                  {c.label} {sortKey===c.k ? (order==='asc'?'▲':'▼') : ''}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map(r=>{
              const isSel = selected===r.symbol
              const flash = flashMap[r.symbol] || ''
              return (
                <tr key={r.symbol} onClick={()=>onSelect(r)} className={`${flash} ${isSel?'bg-sky-900/30':''} hover:bg-[#1a2330] cursor-pointer border-b border-[#111820] even:bg-[#0f1a24]`}>
                  <td className="px-2 py-1 text-gray-400">{r.rank ?? '-'}</td>
                  <td className="px-2 py-1 font-mono font-semibold text-white sticky left-0 bg-inherit">{r.symbol}</td>
                  <td className="px-2 py-1 font-mono">{fmt(r.ltp,2)}</td>
                  <td className={`px-2 py-1 font-mono ${colorPct(r.change_pct)}`}>{fmtPct(r.change_pct)}</td>
                  <td className="px-2 py-1 text-gray-300">{fmtInt(r.volume)}</td>
                  <td className={`px-2 py-1 ${ (r.rel_volume||0)>1.5?'text-yellow-300 font-bold':''}`}>{r.rel_volume ? r.rel_volume.toFixed(2)+'x' : '-'}</td>
                  <td className={`px-2 py-1 font-mono ${r.vwap ? (r.ltp > r.vwap ? 'text-emerald-400':'text-red-400') : ''}`}>{r.vwap? fmt(r.vwap,2): '-'}</td>
                  <td className={`px-2 py-1 ${r.rsi ? (r.rsi>70?'text-red-400': r.rsi<30?'text-emerald-400':'') : ''}`}>{r.rsi? r.rsi.toFixed(0): '-'}</td>
                  <td className={`px-2 py-1 font-mono ${colorPct(r.momentum?.ret_5m)}`}>{r.momentum?.ret_5m!=null? fmtPct(r.momentum.ret_5m): '-'}</td>
                  <td className="px-2 py-1">
                    <span className={`px-1.5 py-0.5 rounded text-[11px] font-bold ${r.score>=70?'bg-emerald-600 text-white': r.score>=50?'bg-yellow-600 text-black': r.score>=30?'bg-gray-600 text-white':'bg-gray-800 text-gray-400'}`}>{Math.round(r.score)}</span>
                  </td>
                  <td className="px-2 py-1">
                    <span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${signalColor(r.signal)}`}>{r.signal}</span>
                  </td>
                  <td className="px-2 py-1">
                    <span className={`inline-block w-2 h-2 rounded-full mr-1 ${freshColor(r.freshness)}`} />{r.freshness}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
        {sorted.length===0 && <div className="p-6 text-center text-gray-500">No results</div>}
      </div>
      <div className="text-[11px] text-gray-500 px-2 py-1">Showing {sorted.length} / {rows.length} • Click row for detail • Updated via WebSocket (throttled)</div>
    </div>
  )
}
function signalColor(s:string){
  if(s==='STRONG_BUY') return 'bg-emerald-700 text-emerald-100'
  if(s==='BUY') return 'bg-emerald-900 text-emerald-200'
  if(s==='BREAKOUT') return 'bg-sky-700 text-white'
  if(s==='BREAKDOWN') return 'bg-red-700 text-white'
  if(s==='VOLUME_SPIKE') return 'bg-yellow-700 text-white'
  if(s==='SELL'||s==='STRONG_SELL') return 'bg-red-900 text-red-200'
  return 'bg-gray-700 text-gray-300'
}
function freshColor(f:string){
  if(f==='LIVE') return 'bg-emerald-500'
  if(f==='DELAYED') return 'bg-yellow-500'
  if(f==='STALE') return 'bg-red-500'
  return 'bg-gray-600'
}
