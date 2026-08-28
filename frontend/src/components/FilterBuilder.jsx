import React, { useState, useEffect } from 'react'

const FIELDS=[
  {k:'changePercent',label:'Change %',type:'number'},
  {k:'ltp',label:'Price',type:'number'},
  {k:'relVolume',label:'Rel Volume',type:'number'},
  {k:'volume',label:'Volume',type:'number'},
  {k:'rsi',label:'RSI',type:'number'},
  {k:'adx',label:'ADX',type:'number'},
  {k:'diPlus',label:'DI+',type:'number'},
  {k:'diMinus',label:'DI-',type:'number'},
  {k:'bbWidthPct',label:'BB Width % (squeeze)',type:'number'},
  {k:'atr',label:'ATR',type:'number'},
  {k:'score',label:'Score',type:'number'},
  {k:'momentum5m',label:'Momentum 5m',type:'number'},
  {k:'supertrendDirection',label:'Supertrend Dir (1/-1)',type:'number'},
  {k:'macdCross',label:'MACD Cross',type:'select',options:['bullish_cross','bearish_cross']},
  {k:'rsiDivergence',label:'RSI Divergence',type:'select',options:['bullish','bearish']},
  {k:'oiBuildup',label:'OI Buildup (F&O only)',type:'select',options:['long_buildup','short_buildup','short_covering','long_unwinding']},
  {k:'signal',label:'Screener Signal',type:'select',options:['STRONG_BUY','BUY','NEUTRAL','SELL','STRONG_SELL','BREAKOUT','BREAKDOWN','VOLUME_SPIKE']},
  {k:'sector',label:'Sector',type:'string'},
]
const OPS={number:['>','<','>=','<=','=','!='],string:['=','!=','contains'],select:['=','!=']}
const PRESETS={
  'Gap Up':[{field:'changePercent',op:'>',value:2},{logic:'AND',field:'relVolume',op:'>',value:1.5}],
  'Breakout':[{field:'score',op:'>',value:70},{logic:'AND',field:'relVolume',op:'>',value:1.2}],
  'Volume Surge':[{field:'relVolume',op:'>',value:2},{logic:'OR',field:'volume',op:'>',value:1000000}],
  'Trending (ADX Gate)':[{field:'adx',op:'>',value:25},{logic:'AND',field:'relVolume',op:'>',value:1.5}],
  'BB Squeeze':[{field:'bbWidthPct',op:'<',value:3}],
  'Long Buildup (F&O)':[{field:'oiBuildup',op:'=',value:'long_buildup'}],
  'Bullish Divergence':[{field:'rsiDivergence',op:'=',value:'bullish'}],
}

function evalCond(stock,c){
  const v=stock[c.field]
  if(c.op==='in') return Array.isArray(c.value) && c.value.includes(v)
  const t=Number(c.value)
  switch(c.op){
    case '>': return v>t
    case '<': return v<t
    case '>=': return v>=t
    case '<=': return v<=t
    case '=': return String(v)===String(c.value)
    case '!=': return String(v)!==String(c.value)
    case 'contains': return String(v||'').toLowerCase().includes(String(c.value).toLowerCase())
    default: return true
  }
}
export function matches(stock, conditions){
  if(!conditions.length) return true
  let res=evalCond(stock,conditions[0])
  for(let i=1;i<conditions.length;i++){
    const c=conditions[i]
    const cur=evalCond(stock,c)
    if(c.logic==='OR') res=res||cur
    else res=res&&cur
  }
  return res
}

const BAND_FIELDS=[
  {k:'ltp',label:'Price'},
  {k:'relVolume',label:'Rel Volume'},
]

export default function FilterBuilder({ onApply, sectors=[] }){
  const [conds,setConds]=useState([{field:'changePercent',op:'>',value:1,logic:'AND'}])
  const [selectedSectors,setSelectedSectors]=useState([])
  const [bands,setBands]=useState({}) // { ltp: {min,max}, relVolume: {min,max} }
  const [saved,setSaved]=useState(()=>{
    try{return JSON.parse(localStorage.getItem('custom_screeners')||'[]')}catch{return []}
  })
  useEffect(()=>{ localStorage.setItem('custom_screeners',JSON.stringify(saved)) },[saved])

  const update=(i,patch)=> setConds(c=>c.map((x,idx)=>idx===i?{...x,...patch}:x))
  const add=()=> setConds(c=>[...c,{field:'score',op:'>',value:50,logic:'AND'}])

  const toggleSector=(s)=> setSelectedSectors(prev=> prev.includes(s) ? prev.filter(x=>x!==s) : [...prev,s])
  const setBand=(field,which,val)=> setBands(prev=>({...prev, [field]:{...prev[field], [which]:val}}))

  const buildFullConds=()=>{
    let full=[...conds]
    if(selectedSectors.length){
      full=[...full, {logic: full.length?'AND':undefined, field:'sector', op:'in', value:selectedSectors}]
    }
    for(const bf of BAND_FIELDS){
      const b=bands[bf.k]
      if(b?.min!==undefined && b.min!=='') full=[...full, {logic: full.length?'AND':undefined, field:bf.k, op:'>=', value:Number(b.min)}]
      if(b?.max!==undefined && b.max!=='') full=[...full, {logic: full.length?'AND':undefined, field:bf.k, op:'<=', value:Number(b.max)}]
    }
    return full
  }

  const apply=()=> onApply?.(buildFullConds())
  const clearAll=()=>{ setConds([]); setSelectedSectors([]); setBands({}); onApply?.([]) }

  return (
    <div style={{padding:12,border:'1px solid var(--border)',borderRadius:12,background:'var(--bg2)',display:'flex',flexDirection:'column',gap:10}}>
      <div style={{display:'flex',gap:8,alignItems:'center',flexWrap:'wrap'}}>
        <strong style={{fontSize:12}}>Advanced Filter Builder</strong>
        <span style={{marginLeft:'auto',display:'flex',gap:6,flexWrap:'wrap'}}>
          {Object.keys(PRESETS).map(k=><button key={k} className="btn sm" onClick={()=>{setConds(PRESETS[k]); setSelectedSectors([]); setBands({})}}>{k}</button>)}
        </span>
      </div>

      {sectors.length>0 && (
        <div>
          <div style={{fontSize:10,color:'var(--text3)',fontWeight:700,textTransform:'uppercase',letterSpacing:'0.05em',marginBottom:4}}>Sectors (multi-select)</div>
          <div style={{display:'flex',gap:6,flexWrap:'wrap'}}>
            {sectors.map(s=>{
              const name = typeof s==='string' ? s : s.sector
              const active = selectedSectors.includes(name)
              return <button key={name} className={`chip ${active?'active':''}`} onClick={()=>toggleSector(name)}>{name}</button>
            })}
          </div>
        </div>
      )}

      <div style={{display:'flex',gap:16,flexWrap:'wrap'}}>
        {BAND_FIELDS.map(bf=>(
          <div key={bf.k} style={{display:'flex',gap:4,alignItems:'center'}}>
            <span style={{fontSize:11,color:'var(--text2)',fontWeight:600}}>{bf.label}:</span>
            <input className="input" type="number" placeholder="min" value={bands[bf.k]?.min??''} onChange={e=>setBand(bf.k,'min',e.target.value)} style={{width:70}} />
            <span style={{color:'var(--text3)'}}>–</span>
            <input className="input" type="number" placeholder="max" value={bands[bf.k]?.max??''} onChange={e=>setBand(bf.k,'max',e.target.value)} style={{width:70}} />
          </div>
        ))}
      </div>
      <div style={{fontSize:9, color:'var(--text3)'}}>Market cap band intentionally omitted -- no market-cap data source is wired into this app (no fabricated numbers).</div>

      {conds.map((c,i)=>{
        const fieldDef = FIELDS.find(f=>f.k===c.field)
        const type = fieldDef?.type||'number'
        return (
        <div key={i} style={{display:'flex',gap:6,alignItems:'center',flexWrap:'wrap'}}>
          {i>0 && <select className="input" value={c.logic} onChange={e=>update(i,{logic:e.target.value})} style={{width:70}}><option>AND</option><option>OR</option></select>}
          <select className="input" value={c.field} onChange={e=>update(i,{field:e.target.value, value:''})}>{FIELDS.map(f=><option key={f.k} value={f.k}>{f.label}</option>)}</select>
          <select className="input" value={c.op} onChange={e=>update(i,{op:e.target.value})} style={{width:90}}>{(OPS[type]||OPS.number).map(o=><option key={o}>{o}</option>)}</select>
          {type==='select' ? (
            <select className="input" value={c.value} onChange={e=>update(i,{value:e.target.value})}>
              <option value="">choose…</option>
              {fieldDef.options.map(o=><option key={o} value={o}>{o}</option>)}
            </select>
          ) : (
            <input className="input" value={c.value} onChange={e=>update(i,{value:e.target.value})} style={{width:90}} placeholder="value" />
          )}
          <button className="btn sm" onClick={()=>setConds(v=>v.filter((_,idx)=>idx!==i))}>×</button>
        </div>
      )})}
      <div style={{display:'flex',gap:6}}>
        <button className="btn sm" onClick={add}>+ Condition</button>
        <button className="btn sm active" onClick={apply}>Apply</button>
        <button className="btn sm" onClick={clearAll}>Clear</button>
        <button className="btn sm" style={{marginLeft:'auto'}} onClick={()=>{
          const name=prompt('Save screener name'); if(!name) return
          setSaved(s=>[...s,{name,conds:buildFullConds()}])
        }}>Save Preset</button>
      </div>
      {saved.length>0 && <div style={{display:'flex',gap:6,flexWrap:'wrap'}}>{saved.map((s,idx)=>(
        <span key={idx} style={{display:'flex',gap:4,alignItems:'center',background:'var(--bg3)',border:'1px solid var(--border)',padding:'4px 8px',borderRadius:999,fontSize:11}}>
          <button onClick={()=>{setConds(s.conds); onApply?.(s.conds)}} style={{background:'none',border:'none',color:'var(--text)',cursor:'pointer',fontWeight:600}}>{s.name}</button>
          <button onClick={()=>setSaved(v=>v.filter((_,i)=>i!==idx))} style={{background:'none',border:'none',color:'var(--red)',cursor:'pointer'}}>×</button>
        </span>
      ))}</div>}
    </div>
  )
}
