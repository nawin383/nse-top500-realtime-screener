import React, { useState, useMemo, useEffect } from 'react'

const LS='paper_positions_v1'
function load(){ try{return JSON.parse(localStorage.getItem(LS)||'[]')}catch{return []}}
export default function PaperTrading({ stocksMap={} }){
  const [positions,setPositions]=useState(load)
  const [closed,setClosed]=useState(()=>{
    try{return JSON.parse(localStorage.getItem('paper_closed')||'[]')}catch{return []}
  })
  const [symbol,setSymbol]=useState('')
  const [qty,setQty]=useState(1)
  const [side,setSide]=useState('BUY')
  useEffect(()=> localStorage.setItem(LS, JSON.stringify(positions)),[positions])
  useEffect(()=> localStorage.setItem('paper_closed', JSON.stringify(closed)),[closed])

  const open=(sym)=>{
    const price=stocksMap[sym]?.ltp || 100
    const p={id:Date.now().toString(36),symbol:sym,qty:Number(qty),side,entry:price,time:Date.now()}
    setPositions(v=>[p,...v])
  }
  const close=(id)=>{
    const p=positions.find(x=>x.id===id); if(!p) return
    const cur=stocksMap[p.symbol]?.ltp ?? p.entry
    const pnl = p.side==='BUY' ? (cur-p.entry)*p.qty : (p.entry-cur)*p.qty
    setClosed(c=>[{...p,exit:cur,pnl,closedAt:Date.now()},...c].slice(0,100))
    setPositions(v=>v.filter(x=>x.id!==id))
  }
  const stats=useMemo(()=>{
    if(!closed.length) return {total:0,win:0,hit:0,pnl:0}
    const win=closed.filter(c=>c.pnl>0).length
    const pnl=closed.reduce((a,c)=>a+c.pnl,0)
    return {total:closed.length,win,hit:closed.length? Math.round(win/closed.length*100):0,pnl}
  },[closed])

  return (
    <div style={{border:'1px solid var(--border)',borderRadius:12,background:'var(--bg2)',padding:12,display:'flex',flexDirection:'column',gap:10}}>
      <div style={{display:'flex',gap:8,alignItems:'center',flexWrap:'wrap'}}>
        <strong style={{fontSize:12}}>Paper Trading</strong>
        <span style={{fontSize:11,color:'var(--text2)',background:'var(--bg3)',padding:'4px 8px',borderRadius:999,border:'1px solid var(--border)'}}>
          Hit {stats.hit}% • P&L <span style={{color:stats.pnl>=0?'var(--green)':'var(--red)',fontWeight:800}}>{stats.pnl.toFixed(2)}</span> • {stats.win}/{stats.total} wins
        </span>
        <button className="btn sm" style={{marginLeft:'auto'}} onClick={()=>{if(confirm('Reset paper trading?')){setPositions([]);setClosed([])}}}>Reset</button>
      </div>
      <div style={{display:'flex',gap:6,flexWrap:'wrap'}}>
        <input className="input" placeholder="SYMBOL" value={symbol} onChange={e=>setSymbol(e.target.value.toUpperCase())} style={{width:120}} />
        <input className="input" type="number" value={qty} onChange={e=>setQty(e.target.value)} style={{width:70}} min={1} />
        <select className="input" value={side} onChange={e=>setSide(e.target.value)}><option>BUY</option><option>SELL</option></select>
        <button className="btn sm active" onClick={()=>symbol && open(symbol)}>Open {side}</button>
      </div>
      <div style={{display:'flex',flexDirection:'column',gap:6,maxHeight:160,overflow:'auto'}}>
        {positions.length===0 && <span style={{fontSize:11,color:'var(--text3)'}}>No open positions. Simulate with virtual trades.</span>}
        {positions.map(p=>{
          const cur=stocksMap[p.symbol]?.ltp ?? p.entry
          const pnl= p.side==='BUY' ? (cur-p.entry)*p.qty : (p.entry-cur)*p.qty
          return (
            <div key={p.id} style={{display:'flex',gap:8,alignItems:'center',padding:'6px 8px',border:'1px solid var(--border)',borderRadius:8,background:'var(--bg3)',fontSize:12}}>
              <span style={{fontWeight:800,fontFamily:'var(--mono)'}}>{p.symbol}</span>
              <span style={{fontSize:10,background:p.side==='BUY'?'rgba(0,230,160,0.15)':'rgba(255,59,74,0.15)',padding:'2px 6px',borderRadius:999}}>{p.side} {p.qty}</span>
              <span className="mono">{p.entry.toFixed(2)} → {cur.toFixed(2)}</span>
              <span style={{color:pnl>=0?'var(--green)':'var(--red)',fontWeight:700}} className="mono">{pnl>=0?'+':''}{pnl.toFixed(2)}</span>
              <button className="btn sm" style={{marginLeft:'auto'}} onClick={()=>close(p.id)}>Close</button>
            </div>
          )
        })}
      </div>
      {closed.length>0 && <div style={{fontSize:11,maxHeight:100,overflow:'auto',display:'flex',flexDirection:'column',gap:4,borderTop:'1px solid var(--border)',paddingTop:8}}>
        <span style={{fontWeight:700,fontSize:10,letterSpacing:'0.06em',color:'var(--text2)'}}>HISTORY</span>
        {closed.slice(0,10).map(c=> <div key={c.id} style={{display:'flex',gap:8,color:'var(--text2)'}}><span>{c.symbol}</span><span style={{color:c.pnl>=0?'var(--green)':'var(--red'}}>{c.pnl.toFixed(2)}</span><span style={{marginLeft:'auto',fontSize:10}}>{new Date(c.closedAt).toLocaleTimeString()}</span></div>)}
      </div>}
    </div>
  )
}
