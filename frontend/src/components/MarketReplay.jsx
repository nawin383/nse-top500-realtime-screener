import React, { useState, useEffect, useRef } from 'react'

export default function MarketReplay({ symbol='RELIANCE', onTick }){
  const [data,setData]=useState([])
  const [idx,setIdx]=useState(0)
  const [playing,setPlaying]=useState(false)
  const [speed,setSpeed]=useState(1)
  const timer=useRef(null)

  useEffect(()=>{
    async function load(){
      try{
        const r=await fetch(`/api/historical/${symbol}?limit=200`)
        if(!r.ok) throw new Error('no hist')
        const j=await r.json()
        const arr=j.data||j.candles||j||[]
        setData(arr); setIdx(0)
      }catch{
        const mock=Array.from({length:100},(_,i)=>({open:100+i*0.3,high:101+i*0.3,low:99+i*0.3,close:100+i*0.3+ (Math.random()-0.5),volume:100000,timestamp:Date.now()- (100-i)*60000}))
        setData(mock); setIdx(0)
      }
    }
    load()
  },[symbol])

  useEffect(()=>{
    if(!playing || !data.length) return
    const ms=Math.max(80, 600/speed)
    timer.current=setInterval(()=>{
      setIdx(i=>{
        const n=Math.min(data.length-1,i+1)
        if(onTick) onTick(data[n])
        if(n>=data.length-1) setPlaying(false)
        return n
      })
    },ms)
    return ()=>clearInterval(timer.current)
  },[playing,speed,data,onTick])

  const cur=data[idx]

  return (
    <div style={{border:'1px solid var(--border)',borderRadius:12,background:'var(--bg2)',padding:12,display:'flex',flexDirection:'column',gap:10}}>
      <div style={{display:'flex',gap:8,alignItems:'center',flexWrap:'wrap'}}>
        <strong style={{fontSize:12}}>Market Replay</strong>
        <span style={{fontSize:11,color:'var(--text2)'}}>{symbol} • {idx+1}/{data.length}</span>
        <span style={{marginLeft:'auto',display:'flex',gap:6,alignItems:'center'}}>
          <button className={`btn sm ${playing?'active':''}`} onClick={()=>setPlaying(v=>!v)}>{playing?'⏸ Pause':'▶ Play'}</button>
          <button className="btn sm" onClick={()=>setIdx(0)}>⏮</button>
          <button className="btn sm" onClick={()=>setIdx(i=>Math.min(data.length-1,i+1))}>⏭</button>
        </span>
      </div>
      <input type="range" min={0} max={Math.max(0,data.length-1)} value={idx} onChange={e=>{const v=Number(e.target.value);setIdx(v); onTick?.(data[v])}} style={{width:'100%'}} />
      <div style={{display:'flex',gap:6,alignItems:'center'}}>
        <span style={{fontSize:11,color:'var(--text2)'}}>Speed</span>
        {[0.5,1,2,5,10].map(s=> <button key={s} className={`btn sm ${speed===s?'active':''}`} onClick={()=>setSpeed(s)}>{s}x</button>)}
      </div>
      {cur && <div style={{display:'flex',gap:12,fontSize:11,fontFamily:'var(--mono)',background:'var(--bg3)',padding:'8px 10px',borderRadius:8,border:'1px solid var(--border)'}}>
        <span>O {cur.open?.toFixed?cur.open.toFixed(2):cur.open}</span>
        <span>H {cur.high?.toFixed?cur.high.toFixed(2):cur.high}</span>
        <span>L {cur.low?.toFixed?cur.low.toFixed(2):cur.low}</span>
        <span>C {cur.close?.toFixed?cur.close.toFixed(2):cur.close}</span>
        <span style={{marginLeft:'auto',color:'var(--text2)'}}>{cur.volume||''}</span>
      </div>}
    </div>
  )
}
