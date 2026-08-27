import React, { useState, useEffect } from 'react'

const FIELDS=[
  {k:'changePercent',label:'Change %',type:'number'},
  {k:'relVolume',label:'Rel Volume',type:'number'},
  {k:'volume',label:'Volume',type:'number'},
  {k:'rsi',label:'RSI',type:'number'},
  {k:'score',label:'Score',type:'number'},
  {k:'momentum5m',label:'Momentum 5m',type:'number'},
  {k:'sector',label:'Sector',type:'string'},
]
const OPS={number:['>','<','>=','<=','=','!='],string:['=','!=','contains']}
const PRESETS={
  'Gap Up':[{field:'changePercent',op:'>',value:2},{logic:'AND',field:'relVolume',op:'>',value:1.5}],
  'Breakout':[{field:'score',op:'>',value:70},{logic:'AND',field:'relVolume',op:'>',value:1.2}],
  'Volume Surge':[{field:'relVolume',op:'>',value:2},{logic:'OR',field:'volume',op:'>',value:1000000}],
}

function evalCond(stock,c){
  const v=stock[c.field]
  const t=Number(c.value)
  switch(c.op){
    case '>': return v>t
    case '<': return v<t
    case '>=': return v>=t
    case '<=': return v<=t
    case '=': return String(v)===String(c.value)
    case '!=': return String(v)!==String(c.value)
    case 'contains': return String(v).toLowerCase().includes(String(c.value).toLowerCase())
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

export default function FilterBuilder({ onApply }){
  const [conds,setConds]=useState([{field:'changePercent',op:'>',value:1,logic:'AND'}])
  const [saved,setSaved]=useState(()=>{
    try{return JSON.parse(localStorage.getItem('custom_screeners')||'[]')}catch{return []}
  })
  useEffect(()=>{ localStorage.setItem('custom_screeners',JSON.stringify(saved)) },[saved])

  const update=(i,patch)=> setConds(c=>c.map((x,idx)=>idx===i?{...x,...patch}:x))
  const add=()=> setConds(c=>[...c,{field:'score',op:'>',value:50,logic:'AND'}])
  const apply=()=> onApply?.(conds)

  return (
    <div style={{padding:12,border:'1px solid var(--border)',borderRadius:12,background:'var(--bg2)',display:'flex',flexDirection:'column',gap:10}}>
      <div style={{display:'flex',gap:8,alignItems:'center',flexWrap:'wrap'}}>
        <strong style={{fontSize:12}}>Filter Builder</strong>
        <span style={{marginLeft:'auto',display:'flex',gap:6}}>
          {Object.keys(PRESETS).map(k=><button key={k} className="btn sm" onClick={()=>setConds(PRESETS[k])}>{k}</button>)}
        </span>
      </div>
      {conds.map((c,i)=>(
        <div key={i} style={{display:'flex',gap:6,alignItems:'center',flexWrap:'wrap'}}>
          {i>0 && <select className="input" value={c.logic} onChange={e=>update(i,{logic:e.target.value})} style={{width:70}}><option>AND</option><option>OR</option></select>}
          <select className="input" value={c.field} onChange={e=>update(i,{field:e.target.value})}>{FIELDS.map(f=><option key={f.k} value={f.k}>{f.label}</option>)}</select>
          <select className="input" value={c.op} onChange={e=>update(i,{op:e.target.value})} style={{width:90}}>{(OPS[FIELDS.find(f=>f.k===c.field)?.type||'number']||OPS.number).map(o=><option key={o}>{o}</option>)}</select>
          <input className="input" value={c.value} onChange={e=>update(i,{value:e.target.value})} style={{width:90}} placeholder="value" />
          <button className="btn sm" onClick={()=>setConds(v=>v.filter((_,idx)=>idx!==i))}>×</button>
        </div>
      ))}
      <div style={{display:'flex',gap:6}}>
        <button className="btn sm" onClick={add}>+ Condition</button>
        <button className="btn sm active" onClick={apply}>Apply</button>
        <button className="btn sm" onClick={()=>setConds([])}>Clear</button>
        <button className="btn sm" style={{marginLeft:'auto'}} onClick={()=>{
          const name=prompt('Save screener name'); if(!name) return
          setSaved(s=>[...s,{name,conds}])
        }}>Save Preset</button>
      </div>
      {saved.length>0 && <div style={{display:'flex',gap:6,flexWrap:'wrap'}}>{saved.map((s,idx)=>(
        <span key={idx} style={{display:'flex',gap:4,alignItems:'center',background:'var(--bg3)',border:'1px solid var(--border)',padding:'4px 8px',borderRadius:999,fontSize:11}}>
          <button onClick={()=>setConds(s.conds)} style={{background:'none',border:'none',color:'var(--text)',cursor:'pointer',fontWeight:600}}>{s.name}</button>
          <button onClick={()=>setSaved(v=>v.filter((_,i)=>i!==idx))} style={{background:'none',border:'none',color:'var(--red)',cursor:'pointer'}}>×</button>
        </span>
      ))}</div>}
    </div>
  )
}
