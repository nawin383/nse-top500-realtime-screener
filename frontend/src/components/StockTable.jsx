import React, { useMemo, useRef, useCallback, useState } from 'react'
import { fmt, fmtPct, fmtVol, fmtPrice } from '../utils/format.js'

export default function StockTable({ stocks, onSelect, selectedSymbol, sortBy, sortDir, onSort }){
  const containerRef = useRef(null)
  const [flashMap, setFlashMap] = useState({}) // symbol -> 'up' | 'down'

  // detect flashes via prev ltp
  const prevRef = useRef({})
  const getFlash = (s)=>{
    const prev = prevRef.current[s.symbol]
    if(prev==null) return ''
    if(s.ltp > prev) return 'flash'
    if(s.ltp < prev) return 'flash-neg'
    return ''
  }

  // update prev after render
  React.useEffect(()=>{
    const next = {}
    stocks.forEach(s=> next[s.symbol]=s.ltp)
    prevRef.current = next
    // set flashMap for 600ms
    const fm={}
    stocks.forEach(s=>{
      const prev = prevRef.current[s.symbol] // note: we just overwrote, so need separate - keep old before overwrite
    })
  }, [stocks])

  // we handle flash via direct comparison with previous render stored in ref old
  const oldRef = useRef({})
  React.useEffect(()=>{
    const newFlash={}
    for(const s of stocks){
      const old = oldRef.current[s.symbol]
      if(old!=null && s.ltp !== old){
        newFlash[s.symbol] = s.ltp > old ? 'up' : 'down'
      }
    }
    if(Object.keys(newFlash).length){
      setFlashMap(newFlash)
      const t=setTimeout(()=> setFlashMap({}), 600)
      return ()=> clearTimeout(t)
    }
    // store for next
    const nxt={}
    stocks.forEach(s=> nxt[s.symbol]=s.ltp)
    oldRef.current=nxt
  }, [stocks])

  const headers = [
    { key:'rank', label:'#' , sortable:false, width:40 },
    { key:'symbol', label:'Symbol', sortable:true },
    { key:'ltp', label:'LTP', sortable:true },
    { key:'changePercent', label:'Chg %', sortable:true },
    { key:'volume', label:'Volume', sortable:true },
    { key:'relVolume', label:'Rel Vol', sortable:true },
    { key:'vwap', label:'VWAP', sortable:true },
    { key:'rsi', label:'RSI', sortable:true },
    { key:'momentum5m', label:'Mom 5m', sortable:true },
    { key:'score', label:'Score', sortable:true },
    { key:'signal', label:'Signal', sortable:true },
    { key:'sector', label:'Sector', sortable:false },
  ]

  const thClick = (k)=>{
    if(!k) return
    if(sortBy===k) onSort(k, sortDir==='asc'?'desc':'asc')
    else onSort(k, 'desc')
  }

  return (
    <div ref={containerRef} style={{height:'100%', overflow:'auto'}}>
      <table>
        <thead>
          <tr>
            {headers.map(h=>(
              <th key={h.key} style={h.width?{width:h.width}:null} onClick={()=> h.sortable && thClick(h.key)}>
                {h.label} {sortBy===h.key ? (sortDir==='asc'?'▲':'▼'):''}
              </th>
            ))}
            <th>Fresh</th>
          </tr>
        </thead>
        <tbody>
          {stocks.map((s, idx)=> {
            const isPos = (s.changePercent||0) >=0
            const flashClass = flashMap[s.symbol]==='up' ? 'flash' : flashMap[s.symbol]==='down' ? 'flash-neg' : ''
            const isSelected = selectedSymbol===s.symbol
            const scoreColor = s.score>=70 ? '#00d38d' : s.score>=40 ? '#f6c343' : '#5a6b84'
            const isAbove = s.isAboveVwap
            return (
              <tr key={s.symbol} className={`${isSelected?'selected':''}`} onClick={()=> onSelect(s.symbol)} style={{cursor:'pointer'}}>
                <td className="mono" style={{color:'#5a6b84'}}>{idx+1}</td>
                <td className={flashClass} style={{fontWeight:700, minWidth:110}}>
                  <span style={{color:'#e6eef8'}}>{s.symbol}</span>
                  <div style={{fontSize:10, color:'#5a6b84', fontWeight:400, whiteSpace:'nowrap', overflow:'hidden', textOverflow:'ellipsis', maxWidth:110}}>{s.companyName}</div>
                </td>
                <td className={`mono ${flashClass}`} style={{fontWeight:600}}>{fmtPrice(s.ltp)}</td>
                <td className={`mono ${isPos?'pos':'neg'} ${flashClass}`}>{fmtPct(s.changePercent)}</td>
                <td className="mono">{fmtVol(s.volume)}</td>
                <td className="mono" style={{color:(s.relVolume||0)>2?'#f6c343':''}}>{s.relVolume ? s.relVolume.toFixed(2)+'x' : '-'}</td>
                <td className={`mono ${isAbove?'vwap-above':'vwap-below'}`}>{s.vwap ? fmtPrice(s.vwap): '-'}</td>
                <td className="mono" style={{color: s.rsi>70?'#ff4757': s.rsi<30?'#00d38d':''}}>{s.rsi ? s.rsi.toFixed(0): '-'}</td>
                <td className={`mono ${ (s.momentum5m||0)>=0?'pos':'neg'}`}>{s.momentum5m!=null? fmtPct(s.momentum5m): '-'}</td>
                <td>
                  <span className="mono" style={{fontWeight:700, color:scoreColor}}>{fmt(s.score,1)}</span>
                  <span className="score-bar" style={{marginLeft:6}}><span className="score-fill" style={{width:`${Math.min(100, s.score)}%`, background:scoreColor}} /></span>
                </td>
                <td><span className={`signal ${s.signal}`}>{s.signal}</span></td>
                <td style={{fontSize:11, color:'#8b9bb4'}}>{s.sector}</td>
                <td><span className={`fresh-${s.freshness}`}>{s.freshness}</span></td>
              </tr>
            )
          })}
          {stocks.length===0 && (
            <tr><td colSpan={13} style={{textAlign:'center', padding:40, color:'#5a6b84'}}>No instruments match filters</td></tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
