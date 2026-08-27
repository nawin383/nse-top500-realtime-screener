import React, { useState } from 'react'
import { useWatchlist } from '../hooks/useWatchlist.js'

export default function WatchlistManager({ onSelect }){
  const {watchlists,active,activeId,setActive,addList,removeList,addSymbol,removeSymbol,moveSymbol,exportJSON,importJSON,setAlert}=useWatchlist()
  const [newName,setNewName]=useState('')
  const [addSym,setAddSym]=useState('')
  const [dragSym,setDragSym]=useState(null)
  const [dragSrc,setDragSrc]=useState(null)

  return (
    <div style={{display:'flex',flexDirection:'column',gap:12,padding:12,background:'var(--bg2)',border:'1px solid var(--border)',borderRadius:12}}>
      <div style={{display:'flex',gap:8,flexWrap:'wrap',alignItems:'center'}}>
        <strong style={{fontSize:12}}>Watchlists</strong>
        <span style={{marginLeft:'auto',display:'flex',gap:6}}>
          <button className="btn sm" onClick={exportJSON}>Export</button>
          <label className="btn sm" style={{cursor:'pointer'}}>Import<input type="file" accept=".json" hidden onChange={e=>{if(e.target.files?.[0]) importJSON(e.target.files[0])}} /></label>
        </span>
      </div>
      <div style={{display:'flex',gap:6}}>
        <input className="input" placeholder="New list name" value={newName} onChange={e=>setNewName(e.target.value)} style={{flex:1}} />
        <button className="btn sm active" onClick={()=>{if(newName.trim()){addList(newName.trim());setNewName('')}}}>Add</button>
      </div>
      <div style={{display:'flex',gap:6,flexWrap:'wrap'}}>
        {watchlists.map(w=>(
          <button key={w.id} className={`chip ${activeId===w.id?'active':''}`} onClick={()=>setActive(w.id)} onDoubleClick={()=>{
            const n=prompt('Rename',w.name); if(n) removeList(w.id)
          }}>
            {w.name} <span style={{opacity:0.6,marginLeft:4}}>{w.symbols.length}</span>
            {w.id!=='default' && <span onClick={(e)=>{e.stopPropagation(); if(confirm('Delete '+w.name+'?')) removeList(w.id)}} style={{marginLeft:6,color:'var(--red)'}}>×</span>}
          </button>
        ))}
      </div>
      {active && (
        <div>
          <div style={{display:'flex',gap:6,marginBottom:8}}>
            <input className="input" placeholder="Add symbol e.g. RELIANCE" value={addSym} onChange={e=>setAddSym(e.target.value.toUpperCase())} style={{flex:1}} onKeyDown={e=>{if(e.key==='Enter' && addSym){addSymbol(active.id,addSym.trim());setAddSym('')}}} />
            <button className="btn sm" onClick={()=>{if(addSym.trim()){addSymbol(active.id,addSym.trim());setAddSym('')}}}>Add</button>
          </div>
          <div style={{display:'flex',flexDirection:'column',gap:4,maxHeight:180,overflow:'auto'}}>
            {active.symbols.length===0 && <span style={{fontSize:11,color:'var(--text3)'}}>No symbols yet. Drag between lists or add manually.</span>}
            {active.symbols.map(sym=>(
              <div key={sym} draggable onDragStart={()=>{setDragSym(sym);setDragSrc(active.id)}} onDragOver={e=>e.preventDefault()} style={{display:'flex',gap:6,alignItems:'center',padding:'6px 8px',border:'1px solid var(--border)',borderRadius:8,background:'var(--bg3)',cursor:'grab'}}>
                <span style={{fontWeight:700,fontFamily:'var(--mono)',fontSize:12,flex:1}} onClick={()=>onSelect?.(sym)}>{sym}</span>
                <button className="btn sm" onClick={()=>{
                  const price=prompt('Alert price for '+sym); if(price) setAlert(active.id,sym,{price:parseFloat(price),type: price?'above':'',enabled:true})
                }} title="Alert">🔔</button>
                <button className="btn sm" onClick={()=>removeSymbol(active.id,sym)}>×</button>
              </div>
            ))}
          </div>
          <div style={{display:'flex',gap:6,marginTop:8,flexWrap:'wrap'}}>
            {watchlists.filter(w=>w.id!==active.id).map(w=>(
              <div key={w.id} onDragOver={e=>e.preventDefault()} onDrop={()=>{if(dragSym) moveSymbol(dragSrc,w.id,dragSym)}} style={{flex:'1 1 120px',minHeight:36,border:'1px dashed var(--border-light)',borderRadius:8,display:'grid',placeItems:'center',fontSize:11,color:'var(--text2)',padding:6}}>
                Drop → {w.name}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
