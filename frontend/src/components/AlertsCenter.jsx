import React, { useEffect, useState, useRef } from 'react'

const LS='alerts_history_v1'
function beep(){
  try{
    const ctx=new (window.AudioContext||window.webkitAudioContext)()
    const o=ctx.createOscillator(), g=ctx.createGain()
    o.type='sine'; o.frequency.value=880; o.connect(g); g.connect(ctx.destination)
    g.gain.value=0.15; o.start(); g.gain.exponentialRampToValueAtTime(0.001,ctx.currentTime+0.35); setTimeout(()=>{o.stop();ctx.close()},400)
  }catch{}
}

export default function AlertsCenter({ alerts=[] }){
  const [muted,setMuted]=useState(()=> localStorage.getItem('alerts_muted')==='1')
  const [snoozeUntil,setSnoozeUntil]=useState(0)
  const [history,setHistory]=useState(()=>{ try{return JSON.parse(localStorage.getItem(LS)||'[]')}catch{return []}})
  const prevLen=useRef(0)

  useEffect(()=>{ localStorage.setItem('alerts_muted', muted?'1':'0') },[muted])
  useEffect(()=>{ localStorage.setItem(LS, JSON.stringify(history.slice(0,200))) },[history])

  useEffect(()=>{
    if(!alerts.length) return
    if(alerts.length>prevLen.current){
      const fresh=alerts.slice(0, alerts.length-prevLen.current)
      setHistory(h=>[...fresh,...h].slice(0,200))
      const now=Date.now()
      if(!muted && now>snoozeUntil){
        fresh.forEach(a=>{
          if(Notification && Notification.permission==='granted'){
            try{ new Notification(a.symbol+' '+a.type,{body:a.message||a.type}) }catch{}
          }
          beep()
        })
      }
    }
    prevLen.current=alerts.length
  },[alerts,muted,snoozeUntil])

  const requestPerm=async()=>{
    if(!('Notification' in window)) return alert('Notifications not supported')
    const p=await Notification.requestPermission()
    if(p==='granted') new Notification('Alerts enabled',{body:'You will receive push alerts'})
  }

  return (
    <div style={{border:'1px solid var(--border)',borderRadius:12,background:'var(--bg2)',overflow:'hidden',display:'flex',flexDirection:'column',maxHeight:320}}>
      <div style={{display:'flex',gap:8,alignItems:'center',padding:'10px 12px',borderBottom:'1px solid var(--border)',flexWrap:'wrap'}}>
        <strong style={{fontSize:12}}>Alerts Center</strong>
        <span style={{fontSize:10,background:'var(--bg3)',padding:'2px 6px',borderRadius:999,border:'1px solid var(--border)'}}>{history.length} total</span>
        <span style={{marginLeft:'auto',display:'flex',gap:6,flexWrap:'wrap'}}>
          <button className={`btn sm ${muted?'active':''}`} onClick={()=>setMuted(v=>!v)}>{muted?'🔇 Muted':'🔊 Sound'}</button>
          <button className="btn sm" onClick={()=>setSnoozeUntil(Date.now()+5*60*1000)}>Snooze 5m</button>
          <button className="btn sm" onClick={requestPerm}>Push</button>
          <button className="btn sm" onClick={()=>setHistory([])}>Clear</button>
        </span>
      </div>
      <div style={{overflow:'auto',flex:1}}>
        {history.length===0 && <div style={{padding:16,textAlign:'center',color:'var(--text3)',fontSize:12}}>No alerts yet. Monitoring breakouts, spikes…</div>}
        {history.map((a,i)=>(
          <div key={a.id||i} className={`alert ${a.level||'info'}`} style={{padding:'8px 12px'}}>
            <span style={{fontWeight:800,fontFamily:'var(--mono)',fontSize:11}}>{a.symbol}</span>
            <span style={{fontSize:11,background:'var(--bg3)',padding:'2px 6px',borderRadius:999,border:'1px solid var(--border)'}}>{a.type}</span>
            <span style={{fontSize:11,color:'var(--text2)',flex:1}}>{a.message||a.type}</span>
            <span style={{fontSize:10,color:'var(--text3)'}}>{a.time? new Date(a.time).toLocaleTimeString():''}</span>
          </div>
        ))}
      </div>
      <div style={{padding:'8px 12px',borderTop:'1px solid var(--border)',display:'flex',gap:6,alignItems:'center',fontSize:10,color:'var(--text3)',flexWrap:'wrap'}}>
        <span>Email/SMS placeholders:</span>
        <input className="input" placeholder="email@example.com" style={{flex:'1 1 140px',padding:'6px 8px'}} />
        <input className="input" placeholder="+91..." style={{width:110,padding:'6px 8px'}} />
        <button className="btn sm">Save</button>
      </div>
    </div>
  )
}
