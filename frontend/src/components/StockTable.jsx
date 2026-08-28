import React, { useRef, useState, useMemo } from 'react'
import { fmt, fmtPct, fmtVol, fmtPrice } from '../utils/format.js'
import Papa from 'papaparse'

const Row = React.memo(function Row({ s, idx, flashClass, isSelected, onSelect, density }){
  const isPos = (s.changePercent||0) >=0
  const scoreColor = s.score>=70 ? '#00e6a0' : s.score>=40 ? '#ffb020' : '#5b728c'
  const isAbove = s.isAboveVwap
  const rowH = density==='compact' ? 30 : 42
  return (
    <tr className={`${isSelected?'selected':''}`} onClick={()=> onSelect(s.symbol)} onKeyDown={(e)=>{ if(e.key==='Enter' || e.key===' '){ e.preventDefault(); onSelect(s.symbol)} }} tabIndex={0} role="row" aria-selected={isSelected} aria-label={`${s.symbol} ${s.companyName} price ${s.ltp} change ${s.changePercent?.toFixed?.(2) ?? ''} percent`} style={{cursor:'pointer', contentVisibility:'auto', containIntrinsicSize:`0 ${rowH}px`}}>
      <td className="mono" role="cell" style={{color:'#5b728c', fontWeight:600, fontSize:11}}>{s.rank || idx+1}</td>
      <td className={flashClass} role="cell" style={{fontWeight:800, minWidth:130}}>
        <div style={{display:'flex', gap:8, alignItems:'center'}}>
          <span style={{color:'#eef4ff', fontSize:12, letterSpacing:'-0.01em'}}>{s.symbol}</span>
          {s.synthetic && <span style={{fontSize:8, background:'rgba(255,255,255,0.06)', color:'#5b728c', padding:'2px 5px', borderRadius:999, border:'1px solid rgba(255,255,255,0.06)', fontWeight:700}}>CLOSED</span>}
        </div>
        <div style={{fontSize:10, color:'#5b728c', fontWeight:500, whiteSpace:'nowrap', overflow:'hidden', textOverflow:'ellipsis', maxWidth:130}}>{s.companyName}</div>
      </td>
      <td className={`mono ${flashClass}`} role="cell" style={{fontWeight:700, fontSize:12}}>{fmtPrice(s.ltp)}</td>
      <td className={`mono ${isPos?'pos':'neg'} ${flashClass}`} role="cell" style={{fontWeight:700}}><span style={{background: isPos?'rgba(0,230,160,0.10)':'rgba(255,59,74,0.10)', padding:'3px 6px', borderRadius:6, border:`1px solid ${isPos?'rgba(0,230,160,0.18)':'rgba(255,59,74,0.18)'}`}}>{fmtPct(s.changePercent)}</span></td>
      <td className="mono" role="cell" style={{fontSize:11}}>{fmtVol(s.volume)}</td>
      <td className="mono" role="cell" style={{color:(s.relVolume||0)>2?'#ffb020': (s.relVolume||0)>1?'#eef4ff': '#5b728c', fontWeight: (s.relVolume||0)>1.5?700:400}}>{s.relVolume ? s.relVolume.toFixed(2)+'x' : '—'}</td>
      <td className={`mono ${isAbove?'vwap-above':'vwap-below'}`} role="cell" style={{fontWeight:600}}>{s.vwap ? fmtPrice(s.vwap): '—'}</td>
      <td className="mono" role="cell" style={{color: s.rsi>70?'#ff3b4a': s.rsi<30?'#00e6a0':'#8ea0b8', fontWeight:600}}>{s.rsi ? s.rsi.toFixed(0): '—'}</td>
      <td className={`mono ${ (s.momentum5m||0)>=0?'pos':'neg'}`} role="cell" style={{fontWeight:600}}>{s.momentum5m!=null? fmtPct(s.momentum5m): '—'}</td>
      <td role="cell">
        <span className="mono" style={{fontWeight:800, color:scoreColor, fontSize:11}}>{fmt(s.score,0)}</span>
        <span className="score-bar" role="progressbar" aria-valuenow={Math.round(s.score||0)} aria-valuemin={0} aria-valuemax={100} style={{marginLeft:8, width:48, height:6, background:'rgba(255,255,255,0.06)'}}><span className="score-fill" style={{width:`${Math.min(100, s.score)}%`, background: scoreColor==='#00e6a0'?'linear-gradient(90deg,#00e6a0,#2f8bff)': scoreColor}} /></span>
      </td>
      <td role="cell"><span className={`signal ${s.signal}`} style={{fontSize:9, padding:'3px 7px'}}>{s.signal || '—'}</span></td>
      <td role="cell"><span style={{fontSize:10, color:'#8ea0b8', background:'rgba(255,255,255,0.04)', padding:'3px 7px', borderRadius:999, border:'1px solid rgba(255,255,255,0.06)', fontWeight:600}}>{s.sector}</span></td>
    </tr>
  )
})

const DEFAULT_COLS=[
  { key:'rank', label:'#', sortable:false, width:50, pinned:false },
  { key:'symbol', label:'Symbol', sortable:true, width:150, pinned:true },
  { key:'ltp', label:'LTP', sortable:true, width:90 },
  { key:'changePercent', label:'Chg %', sortable:true, width:90 },
  { key:'volume', label:'Volume', sortable:true, width:90 },
  { key:'relVolume', label:'Rel Vol', sortable:true, width:80 },
  { key:'vwap', label:'VWAP', sortable:true, width:90 },
  { key:'rsi', label:'RSI', sortable:true, width:70 },
  { key:'momentum5m', label:'Mom 5m', sortable:true, width:80 },
  { key:'score', label:'Score', sortable:true, width:110 },
  { key:'signal', label:'Signal', sortable:true, width:90 },
  { key:'sector', label:'Sector', sortable:false, width:120 },
]

export default function StockTable({ stocks, onSelect, selectedSymbol, sortBy, sortDir, onSort, density='comfortable' }){
  const containerRef = useRef(null)
  const [flashMap, setFlashMap] = useState({})
  const [cols,setCols]=useState(()=>{
    try{ const v=JSON.parse(localStorage.getItem('st_layout')); if(Array.isArray(v) && v.length) return v }catch{}
    return DEFAULT_COLS
  })
  const [multiSort,setMultiSort]=useState([])
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

  React.useEffect(()=>{ localStorage.setItem('st_layout', JSON.stringify(cols)) },[cols])

  const thClick = (k, e)=>{
    if(!k) return
    if(e.shiftKey){
      setMultiSort(prev=>{
        const exists=prev.find(x=>x.key===k)
        const next= exists? prev.map(x=>x.key===k? {...x,dir:x.dir==='asc'?'desc':'asc'}:x) : [...prev,{key:k,dir:'desc'}]
        // apply multi-sort externally if parent supports? fallback to single
        if(next.length) { const first=next[0]; onSort(first.key, first.dir) }
        return next.slice(0,3)
      })
      return
    }
    setMultiSort([])
    if(sortBy===k) onSort(k, sortDir==='asc'?'desc':'asc')
    else onSort(k, 'desc')
  }

  const onResize=(idx, delta)=>{
    setCols(c=> c.map((col,i)=> i===idx? {...col,width: Math.max(50, (col.width||100)+delta)}:col))
  }

  const exportCSV=()=>{
    const csv=Papa.unparse(stocks.map(s=>({symbol:s.symbol,company:s.companyName,ltp:s.ltp,change:s.changePercent,volume:s.volume,relVol:s.relVolume,vwap:s.vwap,rsi:s.rsi,mom5:s.momentum5m,score:s.score,signal:s.signal,sector:s.sector})))
    const blob=new Blob([csv],{type:'text/csv'}); const url=URL.createObjectURL(blob); const a=document.createElement('a'); a.href=url; a.download='screener.csv'; a.click(); URL.revokeObjectURL(url)
  }

  const togglePin=(idx)=> setCols(c=> c.map((col,i)=> i===idx? {...col,pinned:!col.pinned}:col))

  return (
    <div ref={containerRef} className={`table-density-${density}`} style={{height:'100%', overflow:'auto', position:'relative'}}>
      <div style={{position:'sticky',top:0,zIndex:3,display:'flex',gap:6,padding:'6px 8px',background:'rgba(15,20,28,0.95)',borderBottom:'1px solid rgba(255,255,255,0.06)'}}>
        <button className="btn sm" onClick={exportCSV} aria-label="Export screener as CSV">⬇ CSV</button>
        <button className="btn sm" onClick={()=>setCols(DEFAULT_COLS)} aria-label="Reset table layout">Reset Layout</button>
        {multiSort.length>0 && <span style={{fontSize:10,color:'var(--text2)',alignSelf:'center'}}>Multi: {multiSort.map(s=>`${s.key} ${s.dir}`).join(', ')}</span>}
        <span style={{marginLeft:'auto',fontSize:10,color:'var(--text3)'}}>Shift+click multi-sort • drag edge to resize • pin 📌</span>
      </div>
      <table role="table" aria-label="NSE Top 500 screener results" style={{minWidth:980}}>
        <thead>
          <tr role="row">
            {cols.map((h,i)=>(
              <th key={h.key} role="columnheader" aria-sort={sortBy===h.key ? (sortDir==='asc'?'ascending':'descending') : 'none'} tabIndex={h.sortable?0:undefined} onKeyDown={(e)=>{ if(h.sortable && (e.key==='Enter'||e.key===' ')){ e.preventDefault(); thClick(h.key,e) } if(h.sortable && e.key==='ArrowDown'){ onSort(h.key,'desc')} if(h.sortable && e.key==='ArrowUp'){ onSort(h.key,'asc')}}} aria-label={`${h.label} ${h.sortable?'sortable':''}`} style={{width:h.width, position: h.pinned?'sticky':undefined, left: h.pinned? (cols.slice(0,i).filter(c=>c.pinned).reduce((a,c)=>a+(c.width||100),0)):undefined, background: h.pinned?'rgba(15,20,28,0.98)':'', zIndex: h.pinned?2:1, borderRight: h.pinned?'1px solid var(--border)':''}} onClick={(e)=> h.sortable && thClick(h.key,e)}>
                <span style={{display:'flex', gap:6, alignItems:'center', position:'relative'}}>
                  {h.label} {sortBy===h.key ? <span aria-hidden="true" style={{color:'#2f8bff'}}>{sortDir==='asc'?'▲':'▼'}</span> : h.sortable ? <span aria-hidden="true" style={{opacity:0.25, fontSize:9}}>↕</span> : null}
                  <button aria-label={h.pinned ? `Unpin ${h.label} column` : `Pin ${h.label} column`} aria-pressed={h.pinned} onClick={(e)=>{e.stopPropagation(); togglePin(i)}} style={{background:'none',border:'none',cursor:'pointer',fontSize:10,opacity:h.pinned?1:0.3}}>📌</button>
                  <span onMouseDown={e=>{
                    const start=e.clientX, initW=h.width||100
                    const onMove=(ev)=> onResize(i, ev.clientX-start)
                    const onUp=()=>{ window.removeEventListener('mousemove',onMove); window.removeEventListener('mouseup',onUp)}
                    window.addEventListener('mousemove',onMove); window.addEventListener('mouseup',onUp)
                  }} style={{position:'absolute',right:-8,top:0,bottom:0,width:8,cursor:'col-resize'}} />
                </span>
              </th>
            ))}
            <th role="columnheader" style={{width:90}}>Status</th>
          </tr>
        </thead>
        <tbody>
          {stocks.map((s, idx)=> (
            <Row key={s.symbol} s={s} idx={idx} flashClass={flashMap[s.symbol]==='up' ? 'flash' : flashMap[s.symbol]==='down' ? 'flash-neg' : ''} isSelected={selectedSymbol===s.symbol} onSelect={onSelect} density={density} />
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
