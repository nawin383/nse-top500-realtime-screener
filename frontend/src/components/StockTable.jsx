import React, { useRef, useState, useMemo } from 'react'
import { fmt, fmtPct, fmtVol, fmtPrice } from '../utils/format.js'
import Papa from 'papaparse'

const num = (v, d=2) => (v==null ? '—' : Number(v).toFixed(d))

// Single source of truth: every column's label + how to render/export it.
// Row rendering below iterates the user's chosen `cols` against this catalog,
// so pinning/reordering/adding a column all drive the same cells (previously
// the header list and the hardcoded <Row> cells could silently diverge).
const COLUMN_CATALOG = {
  rank: { label:'#', sortable:false, width:50,
    render:(s,idx)=> <td className="mono" role="cell" style={{color:'#94a3b8', fontWeight:600, fontSize:11}}>{s.rank || idx+1}</td>,
    csv:(s,idx)=> s.rank||idx+1 },
  symbol: { label:'Symbol', sortable:true, width:150,
    render:(s)=> <td role="cell" style={{fontWeight:800, minWidth:130}}>
      <div style={{display:'flex', gap:8, alignItems:'center'}}>
        <span style={{color:'#f1f5f9', fontSize:12, letterSpacing:'-0.01em'}}>{s.symbol}</span>
        {s.synthetic && <span style={{fontSize:8, background:'rgba(255,255,255,0.06)', color:'#94a3b8', padding:'2px 5px', borderRadius:999, border:'1px solid rgba(255,255,255,0.06)', fontWeight:700}}>CLOSED</span>}
      </div>
      <div style={{fontSize:10, color:'#94a3b8', fontWeight:500, whiteSpace:'nowrap', overflow:'hidden', textOverflow:'ellipsis', maxWidth:130}}>{s.companyName}</div>
    </td>,
    csv:(s)=> s.symbol },
  ltp: { label:'LTP', sortable:true, width:90,
    render:(s)=> <td className="mono" role="cell" style={{fontWeight:700, fontSize:12}}>{fmtPrice(s.ltp)}</td>, csv:(s)=>s.ltp },
  changePercent: { label:'Chg %', sortable:true, width:90,
    render:(s)=>{ const isPos=(s.changePercent||0)>=0; return <td className={`mono ${isPos?'pos':'neg'}`} role="cell" style={{fontWeight:700}}><span style={{background: isPos?'rgba(16,185,129,0.10)':'rgba(239,83,80,0.10)', padding:'3px 6px', borderRadius:6, border:`1px solid ${isPos?'rgba(16,185,129,0.18)':'rgba(239,83,80,0.18)'}`}}>{fmtPct(s.changePercent)}</span></td> },
    csv:(s)=>s.changePercent },
  volume: { label:'Volume', sortable:true, width:90,
    render:(s)=> <td className="mono" role="cell" style={{fontSize:11}}>{fmtVol(s.volume)}</td>, csv:(s)=>s.volume },
  relVolume: { label:'Rel Vol', sortable:true, width:80,
    render:(s)=> <td className="mono" role="cell" style={{color:(s.relVolume||0)>2?'#f59e0b': (s.relVolume||0)>1?'#f1f5f9': '#94a3b8', fontWeight: (s.relVolume||0)>1.5?700:400}}>{s.relVolume ? s.relVolume.toFixed(2)+'x' : '—'}</td>,
    csv:(s)=>s.relVolume },
  vwap: { label:'VWAP', sortable:true, width:90,
    render:(s)=> <td className={`mono ${s.isAboveVwap?'vwap-above':'vwap-below'}`} role="cell" style={{fontWeight:600}}>{s.vwap ? fmtPrice(s.vwap): '—'}</td>, csv:(s)=>s.vwap },
  vwapBands: { label:'VWAP ±1σ', sortable:false, width:150,
    render:(s)=> <td className="mono" role="cell" style={{fontSize:10, color:'#94a3b8'}}>{s.vwapLower1!=null && s.vwapUpper1!=null ? `${num(s.vwapLower1)} / ${num(s.vwapUpper1)}` : '—'}</td>,
    csv:(s)=> s.vwapLower1!=null?`${s.vwapLower1}-${s.vwapUpper1}`:'' },
  rsi: { label:'RSI', sortable:true, width:70,
    render:(s)=> <td className="mono" role="cell" style={{color: s.rsi>70?'#ef5350': s.rsi<30?'#10b981':'#cbd5e1', fontWeight:600}}>{s.rsi ? s.rsi.toFixed(0): '—'}</td>, csv:(s)=>s.rsi },
  rsiDivergence: { label:'RSI Div', sortable:false, width:90,
    render:(s)=> <td role="cell">{s.rsiDivergence ? <span style={{fontSize:9, padding:'2px 6px', borderRadius:999, fontWeight:700, background: s.rsiDivergence==='bearish'?'rgba(239,83,80,0.12)':'rgba(16,185,129,0.12)', color: s.rsiDivergence==='bearish'?'#ef5350':'#10b981'}}>{s.rsiDivergence}</span> : <span style={{color:'#475569'}}>—</span>}</td>,
    csv:(s)=>s.rsiDivergence||'' },
  momentum5m: { label:'Mom 5m', sortable:true, width:80,
    render:(s)=> <td className={`mono ${(s.momentum5m||0)>=0?'pos':'neg'}`} role="cell" style={{fontWeight:600}}>{s.momentum5m!=null? fmtPct(s.momentum5m): '—'}</td>, csv:(s)=>s.momentum5m },
  adx: { label:'ADX', sortable:true, width:70,
    render:(s)=> <td className="mono" role="cell" style={{color: (s.adx||0)>25?'#2563eb':'#94a3b8', fontWeight: (s.adx||0)>25?700:400}}>{s.adx!=null ? s.adx.toFixed(0) : '—'}</td>, csv:(s)=>s.adx },
  diDelta: { label:'DI+/DI-', sortable:false, width:100,
    render:(s)=> <td className="mono" role="cell" style={{fontSize:10}}>{s.diPlus!=null ? <><span style={{color:'#10b981'}}>{s.diPlus.toFixed(0)}</span>/<span style={{color:'#ef5350'}}>{s.diMinus.toFixed(0)}</span></> : '—'}</td>,
    csv:(s)=> s.diPlus!=null?`${s.diPlus}/${s.diMinus}`:'' },
  atr: { label:'ATR', sortable:true, width:70,
    render:(s)=> <td className="mono" role="cell">{s.atr!=null ? num(s.atr): '—'}</td>, csv:(s)=>s.atr },
  macdCross: { label:'MACD X', sortable:false, width:100,
    render:(s)=> <td role="cell">{s.macdCross ? <span style={{fontSize:9, padding:'2px 6px', borderRadius:999, fontWeight:700, background: s.macdCross==='bullish_cross'?'rgba(16,185,129,0.12)':'rgba(239,83,80,0.12)', color: s.macdCross==='bullish_cross'?'#10b981':'#ef5350'}}>{s.macdCross==='bullish_cross'?'BULL X':'BEAR X'}</span> : <span style={{color:'#475569'}}>—</span>}</td>,
    csv:(s)=>s.macdCross||'' },
  bbWidthPct: { label:'BB Width%', sortable:true, width:90,
    render:(s)=> <td className="mono" role="cell" style={{color:(s.bbWidthPct||99)<3?'#f59e0b':'#cbd5e1', fontWeight:(s.bbWidthPct||99)<3?700:400}}>{s.bbWidthPct!=null? s.bbWidthPct.toFixed(2)+'%':'—'}</td>, csv:(s)=>s.bbWidthPct },
  supertrend: { label:'Supertrend', sortable:false, width:110,
    render:(s)=> <td role="cell">{s.supertrendDirection!=null ? <span className="mono" style={{fontSize:10, fontWeight:700, color: s.supertrendDirection===1?'#10b981':'#ef5350'}}>{s.supertrendDirection===1?'▲ UP':'▼ DOWN'} {num(s.supertrend)}</span> : '—'}</td>,
    csv:(s)=> s.supertrendDirection!=null? `${s.supertrendDirection===1?'UP':'DOWN'} ${s.supertrend}`:'' },
  previousDayRange: { label:'Prev Day H/L', sortable:false, width:140,
    render:(s)=> <td className="mono" role="cell" style={{fontSize:10, color:'#94a3b8'}}>{s.previousDayHigh!=null? `${num(s.previousDayLow)} / ${num(s.previousDayHigh)}`:'—'}</td>,
    csv:(s)=> s.previousDayHigh!=null?`${s.previousDayLow}-${s.previousDayHigh}`:'' },
  openingRange15: { label:'OR 15m H/L', sortable:false, width:140,
    render:(s)=> <td className="mono" role="cell" style={{fontSize:10, color:'#94a3b8'}}>{s.or15High!=null? `${num(s.or15Low)} / ${num(s.or15High)}`:'—'}</td>,
    csv:(s)=> s.or15High!=null?`${s.or15Low}-${s.or15High}`:'' },
  score: { label:'Score', sortable:true, width:110,
    render:(s)=>{ const scoreColor = s.score>=70 ? '#10b981' : s.score>=40 ? '#f59e0b' : '#94a3b8'; return <td role="cell">
      <span className="mono" style={{fontWeight:800, color:scoreColor, fontSize:11}}>{fmt(s.score,0)}</span>
      <span className="score-bar" role="progressbar" aria-valuenow={Math.round(s.score||0)} aria-valuemin={0} aria-valuemax={100} style={{marginLeft:8, width:48, height:6, background:'rgba(255,255,255,0.06)'}}><span className="score-fill" style={{width:`${Math.min(100, s.score)}%`, background: scoreColor==='#10b981'?'linear-gradient(90deg,#10b981,#2563eb)': scoreColor}} /></span>
    </td> }, csv:(s)=>s.score },
  signal: { label:'Signal', sortable:true, width:90,
    render:(s)=> <td role="cell"><span className={`signal ${s.signal}`} style={{fontSize:9, padding:'3px 7px'}}>{s.signal || '—'}</span></td>, csv:(s)=>s.signal },
  sector: { label:'Sector', sortable:false, width:120,
    render:(s)=> <td role="cell"><span style={{fontSize:10, color:'#cbd5e1', background:'rgba(255,255,255,0.04)', padding:'3px 7px', borderRadius:999, border:'1px solid rgba(255,255,255,0.06)', fontWeight:600}}>{s.sector}</span></td>, csv:(s)=>s.sector },
}

const DEFAULT_KEYS = ['rank','symbol','ltp','changePercent','volume','relVolume','vwap','rsi','momentum5m','score','signal','sector']

const DEFAULT_COLS = DEFAULT_KEYS.map(key=>({ key, pinned: key==='symbol' }))

const Row = React.memo(function Row({ s, idx, flashClass, isSelected, onSelect, density, cols }){
  const rowH = density==='compact' ? 30 : 42
  return (
    <tr className={`${isSelected?'selected':''} ${flashClass||''}`} onClick={()=> onSelect(s.symbol)} onKeyDown={(e)=>{ if(e.key==='Enter' || e.key===' '){ e.preventDefault(); onSelect(s.symbol)} }} tabIndex={0} role="row" aria-selected={isSelected} aria-label={`${s.symbol} ${s.companyName} price ${s.ltp} change ${s.changePercent?.toFixed?.(2) ?? ''} percent`} style={{cursor:'pointer', contentVisibility:'auto', containIntrinsicSize:`0 ${rowH}px`}}>
      {cols.map(c=>{
        const def = COLUMN_CATALOG[c.key]
        if(!def) return null
        return React.cloneElement(def.render(s, idx), { key:c.key })
      })}
    </tr>
  )
})

export default function StockTable({ stocks, onSelect, selectedSymbol, sortBy, sortDir, onSort, density='comfortable' }){
  const containerRef = useRef(null)
  const [flashMap, setFlashMap] = useState({})
  const [showColPicker, setShowColPicker] = useState(false)
  const [cols,setCols]=useState(()=>{
    try{ const v=JSON.parse(localStorage.getItem('st_layout_v2')); if(Array.isArray(v) && v.length) return v.filter(c=>COLUMN_CATALOG[c.key]) }catch{}
    return DEFAULT_COLS
  })
  const [multiSort,setMultiSort]=useState([])
  const oldRef = useRef({})

  React.useEffect(()=>{
    const newFlash={}
    for(const s of stocks){
      const old = oldRef.current[s.symbol]
      if(old!=null && s.ltp !== old) newFlash[s.symbol] = s.ltp > old ? 'flash' : 'flash-neg'
    }
    if(Object.keys(newFlash).length){
      setFlashMap(newFlash)
      const t=setTimeout(()=> setFlashMap({}), 550)
      const nxt={}; stocks.forEach(x=> nxt[x.symbol]=x.ltp); oldRef.current=nxt
      return ()=> clearTimeout(t)
    }
    const nxt={}; stocks.forEach(x=> nxt[x.symbol]=x.ltp); oldRef.current=nxt
  }, [stocks])

  React.useEffect(()=>{ localStorage.setItem('st_layout_v2', JSON.stringify(cols)) },[cols])

  const thClick = (k, e)=>{
    if(!k) return
    if(e.shiftKey){
      setMultiSort(prev=>{
        const exists=prev.find(x=>x.key===k)
        const next= exists? prev.map(x=>x.key===k? {...x,dir:x.dir==='asc'?'desc':'asc'}:x) : [...prev,{key:k,dir:'desc'}]
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
    setCols(c=> c.map((col,i)=> i===idx? {...col,width: Math.max(50, (col.width||COLUMN_CATALOG[col.key]?.width||100)+delta)}:col))
  }

  const exportCSV=()=>{
    const csv=Papa.unparse(stocks.map((s,idx)=>{
      const row={}
      cols.forEach(c=>{ const def=COLUMN_CATALOG[c.key]; if(def) row[def.label]=def.csv(s,idx) })
      return row
    }))
    const blob=new Blob([csv],{type:'text/csv'}); const url=URL.createObjectURL(blob); const a=document.createElement('a'); a.href=url; a.download='screener.csv'; a.click(); URL.revokeObjectURL(url)
  }

  const togglePin=(idx)=> setCols(c=> c.map((col,i)=> i===idx? {...col,pinned:!col.pinned}:col))
  const toggleColumn=(key)=> setCols(c=>{
    if(c.find(x=>x.key===key)) return c.filter(x=>x.key!==key)
    return [...c, {key}]
  })

  const activeKeys = useMemo(()=> new Set(cols.map(c=>c.key)), [cols])

  return (
    <div ref={containerRef} className={`table-density-${density}`} style={{height:'100%', overflow:'auto', position:'relative'}}>
      <div style={{position:'sticky',top:0,zIndex:3,display:'flex',gap:6,padding:'6px 8px',background:'rgba(13,27,42,0.95)',borderBottom:'1px solid rgba(255,255,255,0.06)', flexWrap:'wrap'}}>
        <button className="btn sm" onClick={exportCSV} aria-label="Export screener as CSV">⬇ CSV</button>
        <button className="btn sm" onClick={()=>setShowColPicker(v=>!v)} aria-expanded={showColPicker} aria-label="Choose columns">☰ Columns</button>
        <button className="btn sm" onClick={()=>setCols(DEFAULT_COLS)} aria-label="Reset table layout">Reset Layout</button>
        {multiSort.length>0 && <span style={{fontSize:10,color:'var(--text2)',alignSelf:'center'}}>Multi: {multiSort.map(s=>`${s.key} ${s.dir}`).join(', ')}</span>}
        <span style={{marginLeft:'auto',fontSize:10,color:'var(--text3)'}}>Shift+click multi-sort • drag edge to resize • pin 📌</span>
      </div>
      {showColPicker && (
        <div style={{position:'sticky', top:35, zIndex:3, display:'flex', flexWrap:'wrap', gap:6, padding:'8px 10px', background:'var(--bg3, #16233a)', borderBottom:'1px solid var(--border,#1e293b)'}}>
          {Object.entries(COLUMN_CATALOG).map(([key,def])=>(
            <label key={key} style={{display:'flex', alignItems:'center', gap:4, fontSize:10, color:'var(--text2,#cbd5e1)', background: activeKeys.has(key)?'rgba(37,99,235,0.15)':'rgba(255,255,255,0.04)', padding:'3px 8px', borderRadius:999, cursor:'pointer', border:'1px solid rgba(255,255,255,0.06)'}}>
              <input type="checkbox" checked={activeKeys.has(key)} onChange={()=>toggleColumn(key)} style={{margin:0}} disabled={key==='rank'||key==='symbol'} />
              {def.label}
            </label>
          ))}
        </div>
      )}
      <table role="table" aria-label="NSE Top 500 screener results" style={{minWidth:980}}>
        <thead>
          <tr role="row">
            {cols.map((h,i)=>{
              const def = COLUMN_CATALOG[h.key]
              if(!def) return null
              const width = h.width || def.width
              return (
              <th key={h.key} role="columnheader" aria-sort={sortBy===h.key ? (sortDir==='asc'?'ascending':'descending') : 'none'} tabIndex={def.sortable?0:undefined} onKeyDown={(e)=>{ if(def.sortable && (e.key==='Enter'||e.key===' ')){ e.preventDefault(); thClick(h.key,e) } if(def.sortable && e.key==='ArrowDown'){ onSort(h.key,'desc')} if(def.sortable && e.key==='ArrowUp'){ onSort(h.key,'asc')}}} aria-label={`${def.label} ${def.sortable?'sortable':''}`} style={{width, position: h.pinned?'sticky':undefined, left: h.pinned? (cols.slice(0,i).filter(c=>c.pinned).reduce((a,c)=>a+(c.width||COLUMN_CATALOG[c.key]?.width||100),0)):undefined, background: h.pinned?'rgba(13,27,42,0.98)':'', zIndex: h.pinned?2:1, borderRight: h.pinned?'1px solid var(--border)':''}} onClick={(e)=> def.sortable && thClick(h.key,e)}>
                <span style={{display:'flex', gap:6, alignItems:'center', position:'relative'}}>
                  {def.label} {sortBy===h.key ? <span aria-hidden="true" style={{color:'#2563eb'}}>{sortDir==='asc'?'▲':'▼'}</span> : def.sortable ? <span aria-hidden="true" style={{opacity:0.25, fontSize:9}}>↕</span> : null}
                  <button aria-label={h.pinned ? `Unpin ${def.label} column` : `Pin ${def.label} column`} aria-pressed={h.pinned} onClick={(e)=>{e.stopPropagation(); togglePin(i)}} style={{background:'none',border:'none',cursor:'pointer',fontSize:10,opacity:h.pinned?1:0.3}}>📌</button>
                  <span onMouseDown={e=>{
                    const start=e.clientX, initW=width||100
                    const onMove=(ev)=> onResize(i, ev.clientX-start)
                    const onUp=()=>{ window.removeEventListener('mousemove',onMove); window.removeEventListener('mouseup',onUp)}
                    window.addEventListener('mousemove',onMove); window.addEventListener('mouseup',onUp)
                  }} style={{position:'absolute',right:-8,top:0,bottom:0,width:8,cursor:'col-resize'}} />
                </span>
              </th>
            )})}
          </tr>
        </thead>
        <tbody>
          {stocks.map((s, idx)=> (
            <Row key={s.symbol} s={s} idx={idx} flashClass={flashMap[s.symbol]} isSelected={selectedSymbol===s.symbol} onSelect={onSelect} density={density} cols={cols} />
          ))}
          {stocks.length===0 && (
            <tr><td colSpan={cols.length} style={{textAlign:'center', padding:48, color:'#94a3b8'}}>
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
