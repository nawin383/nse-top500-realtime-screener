import React from 'react'

export default function MarketOverview({ data }){
  if(!data) return (
    <div className="overview">
      {[1,2,3,4,5,6].map(i=> <div key={i} className="ov-card" style={{height:86, background:'linear-gradient(135deg, rgba(21,29,39,0.6), rgba(17,24,32,0.4))', animation:`pulse 1.5s ease ${i*0.1}s infinite`}} />)}
    </div>
  )
  const cards = [
    { label:'Advancing', value: data.advancing, sub:`Declining ${data.declining} • Unchanged ${data.unchanged}`, color:'#00e6a0', icon:'↗', bg:'linear-gradient(135deg, rgba(0,230,160,0.12), rgba(0,230,160,0.04))' },
    { label:'Above VWAP', value: data.aboveVWAP, sub:`Below ${data.belowVWAP} • VWAP skew`, color:'#2f8bff', icon:'◈', bg:'linear-gradient(135deg, rgba(47,139,255,0.12), rgba(47,139,255,0.04))' },
    { label:'Breakouts', value: data.breakouts, sub:`Breakdowns ${data.breakdowns} • Momentum`, color:'#ffb020', icon:'⚡', bg:'linear-gradient(135deg, rgba(255,176,32,0.12), rgba(255,176,32,0.04))' },
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
            <div className="ov-value" style={{color:c.color || (c.accent===true?'#00e6a0': c.accent===false?'#ff3b4a':'#eef4ff')}}>{c.value}</div>
            <div className="ov-sub">{c.sub}</div>
          </div>
        ))}
      </div>
      <div style={{margin:'0 20px', padding:'10px 16px', borderRadius:12, background:'linear-gradient(90deg, rgba(47,139,255,0.10), rgba(139,92,246,0.08))', border:'1px solid rgba(47,139,255,0.15)', display:'flex', alignItems:'center', gap:12, flexWrap:'wrap'}}>
        <span style={{fontSize:10, fontWeight:800, letterSpacing:'0.06em', textTransform:'uppercase', color:'#2f8bff'}}>Market Status</span>
        <span style={{fontSize:13, fontWeight:700, color:'#eef4ff'}}>{data.marketStatus?.status || data.status || '—'} {data.marketStatus?.is_open ? '●' : '○'}</span>
        <span style={{fontSize:11, color:'#8ea0b8', marginLeft:'auto'}}>{data.total || 500} stocks • 09:15-15:30 IST</span>
      </div>
    </div>
  )
}
