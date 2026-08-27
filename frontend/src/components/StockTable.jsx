import React, { useRef, useState } from 'react'
import { fmt, fmtPct, fmtVol, fmtPrice } from '../utils/format.js'

const Row = React.memo(function Row({ s, idx, flashClass, isSelected, onSelect }){
  const isPos = (s.changePercent||0) >=0
  const scoreColor = s.score>=70 ? '#00e6a0' : s.score>=40 ? '#ffb020' : '#5b728c'
  const isAbove = s.isAboveVwap
  return (
    <tr className={`${isSelected?'selected':''}`} onClick={()=> onSelect(s.symbol)} style={{cursor:'pointer', contentVisibility:'auto', containIntrinsicSize:'0 42px'}}>
      <td className="mono" style={{color:'#5b728c', fontWeight:600, fontSize:11}}>{s.rank || idx+1}</td>
      <td className={flashClass} style={{fontWeight:800, minWidth:130}}>
        <div style={{display:'flex', gap:8, alignItems:'center'}}>
          <span style={{color:'#eef4ff', fontSize:12, letterSpacing:'-0.01em'}}>{s.symbol}</span>
          {s.synthetic && <span style={{fontSize:8, background:'rgba(255,255,255,0.06)', color:'#5b728c', padding:'2px 5px', borderRadius:999, border:'1px solid rgba(255,255,255,0.06)', fontWeight:700}}>CLOSED</span>}
        </div>
        <div style={{fontSize:10, color:'#5b728c', fontWeight:500, whiteSpace:'nowrap', overflow:'hidden', textOverflow:'ellipsis', maxWidth:130}}>{s.companyName}</div>
      </td>
      <td className={`mono ${flashClass}`} style={{fontWeight:700, fontSize:12}}>{fmtPrice(s.ltp)}</td>
      <td className={`mono ${isPos?'pos':'neg'} ${flashClass}`} style={{fontWeight:700}}><span style={{background: isPos?'rgba(0,230,160,0.10)':'rgba(255,59,74,0.10)', padding:'3px 6px', borderRadius:6, border:`1px solid ${isPos?'rgba(0,230,160,0.18)':'rgba(255,59,74,0.18)'}`}}>{fmtPct(s.changePercent)}</span></td>
      <td className="mono" style={{fontSize:11}}>{fmtVol(s.volume)}</td>
      <td className="mono" style={{color:(s.relVolume||0)>2?'#ffb020': (s.relVolume||0)>1?'#eef4ff': '#5b728c', fontWeight: (s.relVolume||0)>1.5?700:400}}>{s.relVolume ? s.relVolume.toFixed(2)+'x' : '—'}</td>
      <td className={`mono ${isAbove?'vwap-above':'vwap-below'}`} style={{fontWeight:600}}>{s.vwap ? fmtPrice(s.vwap): '—'}</td>
      <td className="mono" style={{color: s.rsi>70?'#ff3b4a': s.rsi<30?'#00e6a0':'#8ea0b8', fontWeight:600}}>{s.rsi ? s.rsi.toFixed(0): '—'}</td>
      <td className={`mono ${ (s.momentum5m||0)>=0?'pos':'neg'}`} style={{fontWeight:600}}>{s.momentum5m!=null? fmtPct(s.momentum5m): '—'}</td>
      <td>
        <span className="mono" style={{fontWeight:800, color:scoreColor, fontSize:11}}>{fmt(s.score,0)}</span>
        <span className="score-bar" style={{marginLeft:8, width:48, height:6, background:'rgba(255,255,255,0.06)'}}><span className="score-fill" style={{width:`${Math.min(100, s.score)}%`, background: scoreColor==='#00e6a0'?'linear-gradient(90deg,#00e6a0,#2f8bff)': scoreColor}} /></span>
      </td>
      <td><span className={`signal ${s.signal}`} style={{fontSize:9, padding:'3px 7px'}}>{s.signal || '—'}</span></td>
      <td><span style={{fontSize:10, color:'#8ea0b8', background:'rgba(255,255,255,0.04)', padding:'3px 7px', borderRadius:999, border:'1px solid rgba(255,255,255,0.06)', fontWeight:600}}>{s.sector}</span></td>
      <td><span className={`fresh-${s.freshness}`} style={s.freshness==='CLOSED'?{background:'rgba(255,255,255,0.06)', padding:'3px 7px', borderRadius:999, border:'1px solid rgba(255,255,255,0.06)'}:null}>{s.freshness}</span></td>
    </tr>
  )
})

export default function StockTable({ stocks, onSelect, selectedSymbol, sortBy, sortDir, onSort }){
  const containerRef = useRef(null)
  const [flashMap, setFlashMap] = useState({})
  const oldRef = useRef({})

  React.useEffect(()=>{
    const newFlash={}
    for(const s of stocks){
      const old = oldRef.current[s.symbol]
      if(old!=null && s.ltp !== old) newFlash[s.symbol] = s.ltp > old ? 'up' : 'down'
    }
    if(Object.keys(newFlash).length){
      setFlashMap(newFlash)
      const t=setTimeout(()=> setFlashMap({}), 550)
      const nxt={}; stocks.forEach(x=> nxt[x.symbol]=x.ltp); oldRef.current=nxt
      return ()=> clearTimeout(t)
    }
    const nxt={}; stocks.forEach(x=> nxt[x.symbol]=x.ltp); oldRef.current=nxt
  }, [stocks])

  const headers = [
    { key:'rank', label:'#', sortable:false, width:50 },
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
      <table style={{minWidth:980}}>
        <thead>
          <tr>
            {headers.map(h=>(
              <th key={h.key} style={h.width?{width:h.width}:null} onClick={()=> h.sortable && thClick(h.key)}>
                <span style={{display:'flex', gap:6, alignItems:'center'}}>{h.label} {sortBy===h.key ? <span style={{background: 'linear-gradient(135deg,#2f8bff,#00e6a0)', WebkitBackgroundClip:'text', WebkitTextFillColor:'transparent', fontSize:11}}>{sortDir==='asc'?'▲':'▼'}</span> : h.sortable ? <span style={{opacity:0.25, fontSize:9}}>↕</span> : null}</span>
              </th>
            ))}
            <th style={{width:90}}>Status</th>
          </tr>
        </thead>
        <tbody>
          {stocks.map((s, idx)=> (
            <Row key={s.symbol} s={s} idx={idx} flashClass={flashMap[s.symbol]==='up' ? 'flash' : flashMap[s.symbol]==='down' ? 'flash-neg' : ''} isSelected={selectedSymbol===s.symbol} onSelect={onSelect} />
          ))}
          {stocks.length===0 && (
            <tr><td colSpan={13} style={{textAlign:'center', padding:48, color:'#5b728c'}}>
              <div style={{width:40,height:40, borderRadius:12, background:'rgba(255,255,255,0.04)', display:'grid', placeItems:'center', margin:'0 auto 10px', border:'1px solid rgba(255,255,255,0.06)'}}>◈</div>
              No instruments match filters
              <div style={{fontSize:11, marginTop:6}}>Try clearing chips or search</div>
            </td></tr>
          )}
        </tbody>
      </table>
      <div style={{height:12}} />
    </div>
  )
}
