import React from 'react'

export default function MarketOverview({ data }){
  if(!data) return <div className="overview" style={{color:'#5a6b84'}}>Loading overview...</div>
  const cards = [
    { label:'Advancing', value: data.advancing, sub:`Declining ${data.declining} • Unchanged ${data.unchanged}`, color:'#00d38d' },
    { label:'Above VWAP', value: data.aboveVWAP, sub:`Below ${data.belowVWAP}`, color:'#3b9eff' },
    { label:'Breakouts', value: data.breakouts, sub:`Breakdowns ${data.breakdowns}`, color:'#f6c343' },
    { label:'Top Gainer', value: data.topGainers?.[0]?.symbol || '-', sub: data.topGainers?.[0] ? `${data.topGainers[0].changePercent?.toFixed(2)}% • ${data.topGainers[0].ltp}` : '' },
    { label:'Top Loser', value: data.topLosers?.[0]?.symbol || '-', sub: data.topLosers?.[0] ? `${data.topLosers[0].changePercent?.toFixed(2)}%` : '' },
    { label:'High Volume', value: data.highestVolume?.[0]?.symbol || '-', sub: data.highestVolume?.[0] ? `${(data.highestVolume[0].volume||0).toLocaleString()}` : '' },
  ]
  return (
    <div className="overview">
      {cards.map(c=>(
        <div key={c.label} className="ov-card">
          <div className="ov-label">{c.label}</div>
          <div className="ov-value" style={{color:c.color}}>{c.value}</div>
          <div className="ov-sub">{c.sub}</div>
        </div>
      ))}
      <div className="ov-card" style={{minWidth:200}}>
        <div className="ov-label">Market</div>
        <div className="ov-value" style={{fontSize:14}}>{data.marketStatus?.status} {data.marketStatus?.is_open ? '●' : '○'}</div>
        <div className="ov-sub">{data.total} stocks • 09:15-15:30 IST</div>
      </div>
    </div>
  )
}
