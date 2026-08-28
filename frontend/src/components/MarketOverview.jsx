import React, { useEffect, useRef, useState } from 'react'

export default function MarketOverview({ data }){
  // This panel refetches via its own REST poll (every 15s from App.jsx),
  // independent of the WS tick stream the header's global "Last" clock
  // reflects -- so it needs its own freshness timestamp, tracking when the
  // `data` payload itself actually changed rather than just render time.
  const [updatedAt, setUpdatedAt] = useState(null)
  const prevRef = useRef(null)
  useEffect(()=>{
    if(data && JSON.stringify(data) !== prevRef.current){
      prevRef.current = JSON.stringify(data)
      setUpdatedAt(new Date())
    }
  }, [data])

  if(!data) return (
    <div className="overview">
      {[1,2,3,4,5,6].map(i=> <div key={i} className="ov-card" style={{height:86, background:'linear-gradient(135deg, rgba(22,35,58,0.6), rgba(13,27,42,0.4))', animation:`pulse 1.5s ease ${i*0.1}s infinite`}} />)}
    </div>
  )
  const cards = [
    { label:'Advancing', value: data.advancing, sub:`Declining ${data.declining} • Unchanged ${data.unchanged}`, color:'#10b981', icon:'↗', bg:'linear-gradient(135deg, rgba(16,185,129,0.12), rgba(16,185,129,0.04))' },
    { label:'Above VWAP', value: data.aboveVWAP, sub:`Below ${data.belowVWAP} • VWAP skew`, color:'#2563eb', icon:'◈', bg:'linear-gradient(135deg, rgba(37,99,235,0.12), rgba(37,99,235,0.04))' },
    { label:'Breakouts', value: data.breakouts, sub:`Breakdowns ${data.breakdowns} • Momentum`, color:'#f59e0b', icon:'⚡', bg:'linear-gradient(135deg, rgba(245,158,11,0.12), rgba(245,158,11,0.04))' },
    { label:'Top Gainer', value: data.topGainers?.[0]?.symbol || '-', sub: data.topGainers?.[0] ? `${data.topGainers[0].changePercent?.toFixed(2)}% • ${data.topGainers[0].ltp?.toFixed(2)}` : '—', accent: data.topGainers?.[0]?.changePercent>0 },
    { label:'Top Loser', value: data.topLosers?.[0]?.symbol || '-', sub: data.topLosers?.[0] ? `${data.topLosers[0].changePercent?.toFixed(2)}%` : '—', accent: false },
    { label:'High Volume', value: data.highestVolume?.[0]?.symbol || '-', sub: data.highestVolume?.[0] ? `${(data.highestVolume[0].volume||0).toLocaleString('en-IN')}` : '—' },
  ]
  return (
    <div style={{display:'flex', flexDirection:'column', gap:10}}>
      <div className="overview">
        {cards.map(c=>(
          <div key={c.label} className="ov-card" style={c.bg?{background:c.bg}:null}>
            <div style={{display:'flex', justifyContent:'space-between', alignItems:'flex-start'}}>
              <div className="ov-label">{c.label}</div>
              {c.icon && <span style={{width:22, height:22, borderRadius:6, background:'rgba(255,255,255,0.06)', display:'grid', placeItems:'center', fontSize:10, color:c.color}}>{c.icon}</span>}
            </div>
            <div className="ov-value" style={{color:c.color || (c.accent===true?'#10b981': c.accent===false?'#ef5350':'#f1f5f9')}}>{c.value}</div>
            <div className="ov-sub">{c.sub}</div>
          </div>
        ))}
      </div>
      <div style={{margin:'0 20px', padding:'10px 16px', borderRadius:12, background:'linear-gradient(90deg, rgba(37,99,235,0.10), rgba(139,92,246,0.08))', border:'1px solid rgba(37,99,235,0.15)', display:'flex', alignItems:'center', gap:12, flexWrap:'wrap'}}>
        <span style={{fontSize:10, fontWeight:800, letterSpacing:'0.06em', textTransform:'uppercase', color:'#2563eb'}}>Market Status</span>
        <span style={{fontSize:13, fontWeight:700, color:'#f1f5f9'}}>{data.marketStatus?.status || data.status || '—'} {data.marketStatus?.is_open ? '●' : '○'}</span>
        <span style={{fontSize:11, color:'#cbd5e1', marginLeft:'auto'}}>{data.total || 500} stocks • 09:15-15:30 IST</span>
        <span style={{fontSize:10, color:'#64748b'}}>{updatedAt ? `overview as of ${updatedAt.toLocaleTimeString('en-IN',{timeZone:'Asia/Kolkata'})}` : ''}</span>
      </div>
    </div>
  )
}
