import React from 'react'

// A crafted mark (an ascending candlestick/pulse motif) instead of a text
// glyph -- crisp at any size, renders identically across platforms/fonts,
// and reads at a glance as "market data" rather than a generic dot.
function BrandMark(){
  return (
    <svg width="19" height="19" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M4 15L9.5 9.5L13.5 13.5L20 6" stroke="#0b1220" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M14.5 6H20V11.5" stroke="#0b1220" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round"/>
      <circle cx="4" cy="18" r="1.6" fill="#0b1220"/>
    </svg>
  )
}

// Brand block only -- the rest of what used to be a 3-4 row header (status
// pills, connection indicator, layout switcher, theme/accent/login) now lives
// in one merged single-line bar in App.jsx, with secondary controls tucked
// behind SettingsMenu. Secondary info (next-open time) is a tooltip on the
// badge instead of a permanent banner row -- it's still there, just not
// taking up its own line at all times.
export default function Header({ marketStatus, dataMode }){
  const ms = marketStatus
  const isLive = ms?.is_open ?? ms?.is_live ?? ms?.isLive ?? false
  const badgeClass = dataMode==='mock' ? 'mock' : isLive ? 'live' : 'closed'
  const badgeLabel = dataMode==='mock' ? 'MOCK' : isLive ? '● LIVE' : 'CLOSED'
  const nextOpen = ms?.next_open ? new Date(ms.next_open).toLocaleString('en-IN',{weekday:'short',hour:'2-digit',minute:'2-digit',timeZone:'Asia/Kolkata'})+' IST' : '09:15 IST'
  const badgeTitle = dataMode==='mock' ? 'Mock/simulated data mode' : isLive ? 'Market is live' : `Showing last close • Next open ${nextOpen}`
  return (
    <div className="brand" style={{flexShrink:0}}>
      <div className="brand-icon"><BrandMark/></div>
      <span style={{fontSize:13, fontWeight:900, letterSpacing:'-0.03em', whiteSpace:'nowrap'}}>NSE TOP500 <span style={{fontWeight:800, background:'linear-gradient(135deg,#10b981,var(--accent))', WebkitBackgroundClip:'text', WebkitTextFillColor:'transparent'}}>SCREENER</span></span>
      <span className={`badge ${badgeClass}`} title={badgeTitle} style={{marginLeft:2, cursor:'help'}}>{badgeLabel}</span>
    </div>
  )
}
