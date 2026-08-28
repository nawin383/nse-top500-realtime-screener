import React from 'react'

export default function Header({ marketStatus, connectionStatus, lastUpdate, dataMode }){
  const ms = marketStatus
  const isLive = ms?.is_open ?? ms?.is_live ?? ms?.isLive ?? false
  const dotClass = connectionStatus==='open' ? 'green' : connectionStatus==='connecting' ? 'yellow' : 'red'
  const badgeClass = dataMode==='mock' ? 'mock' : isLive ? 'live' : 'closed'
  const badgeLabel = dataMode==='mock' ? 'MOCK • SIM' : isLive ? '● LIVE' : (ms?.status || 'CLOSED')
  return (
    <div className="header">
      <div className="brand">
        <div className="brand-icon">◉</div>
        <div style={{display:'flex', flexDirection:'column', lineHeight:1}}>
          <span style={{fontSize:13, fontWeight:900, letterSpacing:'-0.03em'}}>NSE TOP500 <span style={{fontWeight:800, background:'linear-gradient(135deg,#00e6a0,#2f8bff)', WebkitBackgroundClip:'text', WebkitTextFillColor:'transparent'}}>SCREENER</span></span>
          <span style={{fontSize:9, color:'#5b728c', fontWeight:700, letterSpacing:'0.12em'}}>REAL-TIME • INSTITUTIONAL GRADE</span>
        </div>
        <span className={`badge ${badgeClass}`} style={{marginLeft:8}}>{badgeLabel}</span>
        <span style={{fontSize:10, color:'#5b728c', background:'rgba(255,255,255,0.04)', padding:'3px 8px', borderRadius:999, border:'1px solid rgba(255,255,255,0.06)', fontWeight:600}}>{ms?.status || '...'} • IST</span>
      </div>
      <div style={{display:'flex',gap:16, alignItems:'center', fontSize:12, color:'#8ea0b8'}}>
        <span style={{display:'flex',gap:8, alignItems:'center', background:'rgba(255,255,255,0.04)', padding:'6px 12px', borderRadius:999, border:'1px solid rgba(255,255,255,0.06)'}}>
          <span className={`status-dot ${dotClass}`} /> <b style={{color:'#eef4ff', fontSize:11, letterSpacing:'0.06em'}}>{connectionStatus.toUpperCase()}</b>
        </span>
        <span style={{fontFamily:'JetBrains Mono', fontSize:11, background:'rgba(15,20,28,0.8)', padding:'6px 10px', borderRadius:8, border:'1px solid rgba(255,255,255,0.06)'}}>Last <b style={{color:'#eef4ff'}}>{lastUpdate ? new Date(lastUpdate).toLocaleTimeString('en-IN',{timeZone:'Asia/Kolkata'}) : '--:--:--'}</b></span>
        <span style={{color:'#5b728c', fontSize:11, display:'none'}} className="hide-mobile">500 • 09:15-15:30 IST</span>
      </div>
    </div>
  )
}
