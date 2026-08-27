import React from 'react'

export default function Header({ marketStatus, connectionStatus, lastUpdate, dataMode }){
  const ms = marketStatus
  const isLive = ms?.is_open ?? ms?.is_live ?? ms?.isLive ?? false
  const dotClass = connectionStatus==='open' ? 'green' : connectionStatus==='connecting' ? 'yellow' : 'red'
  const badgeClass = dataMode==='mock' ? 'mock' : isLive ? 'live' : 'closed'
  const badgeLabel = dataMode==='mock' ? 'MOCK DATA' : isLive ? 'LIVE' : (ms?.status || ms?.label || 'CLOSED')
  return (
    <div className="header">
      <div className="brand">
        <span>◉</span> NSE TOP500 <span style={{color:'#8b9bb4',fontWeight:400}}>REAL-TIME SCREENER</span>
        <span className={`badge ${badgeClass}`}>{badgeLabel}</span>
        <span className={`badge ${isLive ? 'live':'closed'}`} style={{marginLeft:4}}>{ms?.status || '...'}</span>
      </div>
      <div style={{display:'flex',gap:16, alignItems:'center', fontSize:12, color:'#8b9bb4'}}>
        <span style={{display:'flex',gap:6, alignItems:'center'}}>
          <span className={`status-dot ${dotClass}`} /> {connectionStatus.toUpperCase()}
        </span>
        <span>Last: {lastUpdate ? new Date(lastUpdate).toLocaleTimeString('en-IN') : '--:--:--'}</span>
        <span>IST {ms?.timestamp ? new Date(ms.timestamp).toLocaleTimeString('en-IN') : ms?.server_time_ist ? new Date(ms.server_time_ist).toLocaleTimeString('en-IN') : ''}</span>
        <span style={{color:'#5a6b84', fontSize:11}}>500 instruments • Asia/Kolkata</span>
      </div>
    </div>
  )
}
