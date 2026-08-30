import React, { useEffect, useState, useMemo, useCallback, useRef, Suspense, lazy } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import Header from './components/Header.jsx'
import MarketOverview from './components/MarketOverview.jsx'
import StockTable from './components/StockTable.jsx'
import DetailPanel from './components/DetailPanel.jsx'
import WatchlistManager from './components/WatchlistManager.jsx'
import AIInsights from './components/AIInsights.jsx'
import CommandPalette from './components/CommandPalette.jsx'
import SettingsMenu from './components/SettingsMenu.jsx'
import { useWebSocket } from './hooks/useWebSocket.js'
import { fetchOverview, fetchMarketStatus, fetchSectors } from './services/api.js'
import { useStore } from './store/useStore.js'
import DashboardLayouts from './components/layouts/DashboardLayouts.jsx'
import FilterBuilder, { matches as matchesAdvancedFilter } from './components/FilterBuilder.jsx'
import { IconScreener, IconTarget, IconChain, IconScroll, IconChart, IconFlask, IconRewind, IconBell, IconExternal, IconToolbox, IconBuilding } from './components/icons.jsx'

const OptionsHub = lazy(()=> import('./components/options/OptionsHub.jsx'))
const IntradaySignals = lazy(()=> import('./components/IntradaySignals.jsx'))
const OptionInstrumentsScreener = lazy(()=> import('./components/OptionInstrumentsScreener.jsx'))
const PaperTrading = lazy(()=> import('./components/PaperTrading.jsx'))
const MarketReplay = lazy(()=> import('./components/MarketReplay.jsx'))
const AlertsCenter = lazy(()=> import('./components/AlertsCenter.jsx'))
const ETFScreener = lazy(()=> import('./components/ETFScreener.jsx'))
const EliteQuantScreener = lazy(()=> import('./components/EliteQuantScreener.jsx'))

const NAV = [
  { k:'screener', label:'Screener', full:'Screener', icon:IconScreener },
  { k:'intraday', label:'Intraday', full:'Intraday Signals', icon:IconTarget },
  { k:'options', label:'Options', full:'Options', icon:IconChain },
  { k:'optioninstruments', label:'Instruments', full:'Option Instruments', icon:IconScroll },
  { k:'etf', label:'ETFs', full:'ETF Screener', icon:IconChart },
]
const TOOLS = [
  { k:'paper', label:'Paper Trading', icon:IconFlask },
  { k:'replay', label:'Market Replay', icon:IconRewind },
  { k:'alerts', label:'Alerts Center', icon:IconBell },
  { k:'elitequant', label:'Elite Quant', icon:IconBuilding },
]
// External dashboards the user runs outside this app -- opened in a new tab,
// never embedded (Apps Script deployments block framing via X-Frame-Options
// anyway, and this session has no access to edit them directly).
const EXTERNAL_LINKS = [
  { label:'Smart ETF Dashboard', url:'https://script.google.com/macros/s/AKfycbySs46EBlzP0vpAhtm9vImzIPqKUCVbxzXBigSe0HH_55iVB4kEyPv-M-BlF8ETyztu/exec' },
  { label:'Nifty Indices Dashboard', url:'https://script.google.com/macros/s/AKfycbzSHbc7_vKJkMdkDpCC5GPVRGoJUYdJkdTe_TAWHLgfazG-rSNRJjlaRUVtoDllyRVkWg/exec' },
]
const ALL_DESTINATIONS = [...NAV, ...TOOLS]

function ToolsMenu({ view, setView }){
  const [open, setOpen] = useState(false)
  const ref = useRef(null)
  const active = TOOLS.some(t=> t.k===view)
  useEffect(()=>{
    const onDoc=(e)=>{ if(ref.current && !ref.current.contains(e.target)) setOpen(false) }
    document.addEventListener('mousedown', onDoc)
    return ()=> document.removeEventListener('mousedown', onDoc)
  },[])
  return (
    <div ref={ref} className="tools-menu" style={{position:'relative'}}>
      <button aria-haspopup="menu" aria-expanded={open} onClick={()=> setOpen(v=>!v)}
        style={{display:'flex', alignItems:'center', gap:6, position:'relative', borderRadius:8, fontWeight:700, fontSize:12, padding:'7px 14px', border:'none', cursor:'pointer', background: active?'linear-gradient(135deg,var(--accent),var(--accent-light))':'transparent', color: active?'#04101f':'var(--text2)'}}>
        <IconToolbox/> Tools <span aria-hidden="true" style={{fontSize:9}}>{open?'▲':'▼'}</span>
      </button>
      <AnimatePresence>
        {open && (
          <motion.div role="menu" initial={{opacity:0,y:-6,scale:0.98}} animate={{opacity:1,y:0,scale:1}} exit={{opacity:0,y:-6,scale:0.98}} transition={{duration:0.14}}
            style={{position:'absolute', top:'calc(100% + 6px)', right:0, minWidth:220, background:'var(--bg2)', border:'1px solid var(--border)', borderRadius:10, boxShadow:'0 12px 32px rgba(0,0,0,0.35)', overflow:'hidden', zIndex:50}}>
            {TOOLS.map(t=>(
              <button key={t.k} role="menuitem" aria-pressed={view===t.k} onClick={()=>{ setView(t.k); setOpen(false) }}
                style={{display:'flex', alignItems:'center', gap:8, width:'100%', padding:'9px 12px', border:'none', cursor:'pointer', textAlign:'left', fontSize:12, fontWeight:600, background: view===t.k?'rgba(var(--accent-rgb),0.14)':'transparent', color:'var(--text)'}}>
                <t.icon/> {t.label}
              </button>
            ))}
            <div style={{borderTop:'1px solid var(--border)', padding:'6px 12px 4px', fontSize:9, fontWeight:800, letterSpacing:'0.08em', textTransform:'uppercase', color:'var(--text3)'}}>External</div>
            {EXTERNAL_LINKS.map(l=>(
              <a key={l.url} href={l.url} target="_blank" rel="noopener noreferrer" onClick={()=> setOpen(false)}
                style={{display:'flex', alignItems:'center', gap:8, width:'100%', padding:'9px 12px', textDecoration:'none', fontSize:12, fontWeight:600, color:'var(--text)'}}>
                <IconExternal/> {l.label}
              </a>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function ViewSkeleton(){
  return (
    <div style={{display:'flex', flexDirection:'column', gap:10}}>
      <div className="skeleton" style={{height:28, width:220, borderRadius:8}} />
      <div style={{display:'grid', gridTemplateColumns:'repeat(auto-fit, minmax(200px,1fr))', gap:10}}>
        {[0,1,2,3].map(i=> <div key={i} className="skeleton" style={{height:80, borderRadius:12}} />)}
      </div>
      <div className="skeleton" style={{height:320, borderRadius:12}} />
    </div>
  )
}


export default function App(){
  const [marketStatus,setMarketStatus]=useState(null)
  const [overview,setOverview]=useState(null)
  const [stocksMap,setStocksMap]=useState({})
  const [sectors,setSectors]=useState([])
  const [selected,setSelected]=useState(null)
  const [showDetail,setShowDetail]=useState(false)
  const [search,setSearch]=useState('')
  const [sectorFilter,setSectorFilter]=useState('')
  const [filters,setFilters]=useState({})
  const [advancedConds,setAdvancedConds]=useState([])
  const [showAdvancedFilters,setShowAdvancedFilters]=useState(false)
  const [sortBy,setSortBy]=useState('score')
  const [sortDir,setSortDir]=useState('desc')
  const [alerts,setAlerts]=useState([])
  const [dataMode,setDataMode]=useState('mock')
  const [view,setView]=useState('screener')
  const [showDashboard,setShowDashboard]=useState(()=>{ try{return localStorage.getItem('show_dashboard')==='1'}catch{return false} })
  const [density,setDensity]=useState(()=>{ try{return localStorage.getItem('row_density')||'compact'}catch{return 'compact'} })
  const theme = useStore(s=>s.theme) || 'dark'
  useEffect(()=>{ try{localStorage.setItem('show_dashboard', showDashboard?'1':'0')}catch{} },[showDashboard])
  useEffect(()=>{ try{localStorage.setItem('row_density',density)}catch{} },[density])

  const normalizeStock=(s)=>({ ...s, changePercent:s.changePercent??s.change_pct??s.changePct, relVolume:s.relVolume??s.rel_volume, companyName:s.companyName??s.company, isAboveVwap:s.isAboveVwap??s.is_above_vwap, volumeSpike:s.volumeSpike??s.volume_spike, isBreakout:s.isBreakout??s.momentum?.breakout, isBreakdown:s.isBreakdown??s.momentum?.breakdown, momentum5m:s.momentum5m??s.momentum?.ret_5m, gapPercent:s.gapPercent??s.gap_pct, vwap:s.vwap??s.indicators?.vwap, rsi:s.rsi??s.indicators?.rsi, ema9:s.ema9??s.indicators?.ema9, ema20:s.ema20??s.indicators?.ema20, synthetic:s.synthetic??s.freshness==='CLOSED',
    vwapUpper1:s.vwapUpper1??s.indicators?.vwap_upper1, vwapLower1:s.vwapLower1??s.indicators?.vwap_lower1,
    vwapUpper2:s.vwapUpper2??s.indicators?.vwap_upper2, vwapLower2:s.vwapLower2??s.indicators?.vwap_lower2,
    adx:s.adx??s.indicators?.adx, diPlus:s.diPlus??s.indicators?.di_plus, diMinus:s.diMinus??s.indicators?.di_minus,
    atr:s.atr??s.indicators?.atr, macd:s.macd??s.indicators?.macd, macdSignal:s.macdSignal??s.indicators?.macd_signal,
    macdHist:s.macdHist??s.indicators?.macd_hist, macdCross:s.macdCross??s.indicators?.macd_cross,
    bbUpper:s.bbUpper??s.indicators?.bb_upper, bbLower:s.bbLower??s.indicators?.bb_lower, bbMiddle:s.bbMiddle??s.indicators?.bb_middle, bbWidthPct:s.bbWidthPct??s.indicators?.bb_width_pct,
    supertrend:s.supertrend??s.indicators?.supertrend, supertrendDirection:s.supertrendDirection??s.indicators?.supertrend_direction, supertrendSignal:s.supertrendSignal??s.indicators?.supertrend_signal,
    rsiDivergence:s.rsiDivergence??s.indicators?.rsi_divergence,
    previousDayHigh:s.previousDayHigh??s.previous_day_high, previousDayLow:s.previousDayLow??s.previous_day_low,
    or15High:s.or15High??s.momentum?.or15_high, or15Low:s.or15Low??s.momentum?.or15_low,
    or30High:s.or30High??s.momentum?.or30_high, or30Low:s.or30Low??s.momentum?.or30_low,
    oi:s.oi, oiChangePct:s.oiChangePct??s.oi_change_pct, oiBuildup:s.oiBuildup??s.oi_buildup,
  })

  const overviewHistoryRef = useRef([])
  const applyOverview = (n) => {
    if(!n) return
    setOverview(n)
    const buf = overviewHistoryRef.current
    const point = { advancing:n.advancing, aboveVWAP:n.aboveVWAP, breakouts:n.breakouts }
    overviewHistoryRef.current = buf.length >= 40 ? [...buf.slice(1), point] : [...buf, point]
  }
  useEffect(()=>{
    const normOv=(d)=>{ if(!d) return null; const na=(a)=>(a||[]).map(x=>({...x,changePercent:x.changePercent??x.change_pct, relVolume:x.relVolume??x.rel_volume})); return {...d, advancing:d.advancing, declining:d.declining, unchanged:d.unchanged, aboveVWAP:d.above_vwap??d.aboveVWAP, belowVWAP:d.below_vwap??d.belowVWAP, breakouts:d.breakouts??d.breakouts_count, breakdowns:d.breakdowns??d.breakdowns_count, topGainers:na(d.top_gainers??d.topGainers), topLosers:na(d.top_losers??d.topLosers), highestVolume:na(d.highest_volume??d.highestVolume), marketStatus:d.marketStatus??{status:d.status,is_open:d.is_live??d.is_open}, total:d.total??500 } }
    fetchMarketStatus().then(d=>{ if(d) d.is_open=d.is_live??d.is_open??false; setMarketStatus(d)}).catch(()=>{})
    fetchOverview().then(d=> applyOverview(normOv(d))).catch(()=>{})
    fetchSectors().then(r=>{ const list=r.data||r.sectors||r; if(Array.isArray(list)){ if(list.length&&typeof list[0]==='object'&&list[0].sector) setSectors(list.map(x=>({sector:x.sector,count:x.count||0}))); else if(list.length&&typeof list[0]==='string') setSectors(list.map(s=>({sector:s,count:0}))); else setSectors(list)}}).catch(()=>{})
    const id=setInterval(()=>{ fetchMarketStatus().then(d=>{ if(d) d.is_open=d.is_live??d.is_open??false; setMarketStatus(d)}).catch(()=>{}); fetchOverview().then(d=>{ const n=normOv(d); applyOverview(n) }).catch(()=>{}) },15000)
    return ()=> clearInterval(id)
  },[])

  const onMessage=useCallback((msg)=>{
    if(msg.type==='snapshot'){ const map={}; for(const s of (msg.data||[])) map[normalizeStock(s).symbol]=normalizeStock(s); setStocksMap(map); if(msg.marketStatus) setMarketStatus(prev=>({...prev,...msg.marketStatus,is_open:msg.marketStatus.is_open??msg.marketStatus.is_live??false})); if(msg.meta?.mode) setDataMode(msg.meta.mode); if(msg.dataMode) setDataMode(msg.dataMode) }
    else if(msg.type==='ticks'){ setStocksMap(prev=>{ const n={...prev}; for(const s of (msg.data||[])){ const nn=normalizeStock(s); n[nn.symbol]={...n[nn.symbol],...nn}} return n}) }
    if(msg.alerts?.length){
      setAlerts(p=>[...msg.alerts,...p].slice(0,100))
      // Mirrors the same real alerts already shown in the in-page "LIVE
      // ALERTS" ticker to the Android app's system notifications (a no-op
      // outside the app -- window.AndroidAlerts only exists inside its
      // WebView, see MainActivity.configureNotifications).
      if(window.AndroidAlerts){ for(const a of msg.alerts){ window.AndroidAlerts.postAlert(a.symbol, a.type, a.message || `${a.symbol} ${a.type}`) } }
    }
    if(msg.meta?.mode) setDataMode(msg.meta.mode)
  },[])
  const { status: wsStatus, lastUpdate }=useWebSocket(null,{onMessage})

  // Bridge for the Android app's bottom navigation (android-app/…/MainActivity.kt).
  // The app has no client-side router -- one SPA, one URL -- so the native
  // bottom nav can't just load a different page per tab; it calls this
  // instead. A no-op object in a normal browser tab, so this is safe to
  // always expose.
  useEffect(()=>{
    window.__nativeSetView = (key)=>{ if(NAV.some(n=>n.k===key) || TOOLS.some(t=>t.k===key)) setView(key) }
    return ()=>{ delete window.__nativeSetView }
  },[])

  // Bridge for tapping an alert notification on Android (MainActivity's
  // postAlertNotification PendingIntent) -- jumps straight to the screener
  // tab and opens that symbol's detail panel, same as clicking it in the
  // table. No-op outside the app.
  useEffect(()=>{
    window.__nativeOpenSymbol = (sym)=>{ if(!sym) return; setView('screener'); handleSelect(sym) }
    return ()=>{ delete window.__nativeOpenSymbol }
  },[])

  // Marks the page as running inside the Android app (window.AndroidBridge
  // only exists there) so index.css can hide the header's own nav-tabs row
  // and Tools dropdown -- both now fully duplicated by the app's native
  // bottom nav and sidebar drawer, and (measured directly) the actual
  // elements that were overflowing past the screen edge on a phone-width
  // WebView with nowhere to scroll to reach them.
  useEffect(()=>{
    if(window.AndroidBridge) document.documentElement.classList.add('in-native-app')
  },[])

  // Mirrors the real WebSocket connection state to the native top app bar
  // (window.AndroidBridge is only defined when running inside the Android
  // app's WebView -- addJavascriptInterface -- so this is a harmless no-op
  // everywhere else, including the PWA).
  useEffect(()=>{
    window.AndroidBridge?.onConnectionState?.(wsStatus)
  },[wsStatus])
  const allStocks=useMemo(()=>Object.values(stocksMap),[stocksMap])
  const filtered=useMemo(()=>{
    let res=allStocks
    if(search){ const q=search.toLowerCase(); res=res.filter(s=> (s.symbol?.toLowerCase().includes(q))||(s.companyName?.toLowerCase().includes(q))) }
    if(sectorFilter) res=res.filter(s=> s.sector===sectorFilter)
    const getChg=s=>s.changePercent??0
    if(filters.gainers) res=res.filter(s=>getChg(s)>0)
    if(filters.losers) res=res.filter(s=>getChg(s)<0)
    if(filters.aboveVwap) res=res.filter(s=>s.isAboveVwap===true)
    if(filters.belowVwap) res=res.filter(s=>s.isAboveVwap===false)
    if(filters.volumeSpike) res=res.filter(s=>s.volumeSpike)
    if(filters.breakout) res=res.filter(s=>s.isBreakout)
    if(filters.breakdown) res=res.filter(s=>s.isBreakdown)
    if(filters.highMomentum) res=res.filter(s=>Math.abs(s.momentum5m??0)>1)
    if(advancedConds.length) res=res.filter(s=> matchesAdvancedFilter(s, advancedConds))
    const dir=sortDir==='asc'?1:-1
    res=[...res].sort((a,b)=>{ let av=a[sortBy],bv=b[sortBy]; if(av==null) av=sortDir==='asc'?Infinity:-Infinity; if(bv==null) bv=sortDir==='asc'?Infinity:-Infinity; if(typeof av==='string') return av.localeCompare(bv)*dir; return (av-bv)*dir })
    return res
  },[allStocks,search,sectorFilter,filters,advancedConds,sortBy,sortDir])

  const handleSelect=(sym)=>{ setSelected(sym); setShowDetail(true) }
  const toggleFilter=(key)=> setFilters(prev=>({...prev,[key]:!prev[key]}))
  const liveSelectedState=selected?stocksMap[selected]:null

  return (
    <div className="app">
      <a href="#main-content" className="skip-link">Skip to content</a>
      <div className="header">
        <Header marketStatus={marketStatus} dataMode={dataMode} />
        <nav className="header-nav" aria-label="Main navigation">
          {NAV.map(v=>(
            <button key={v.k} aria-label={`Switch to ${v.full} view`} aria-pressed={view===v.k} onClick={()=> setView(v.k)}
              style={{display:'flex', alignItems:'center', gap:6, position:'relative', borderRadius:8, fontWeight:700, fontSize:12, padding:'6px 12px', border:'none', cursor:'pointer', background:'transparent', color: view===v.k?'#04101f':'var(--text2)', zIndex:1, whiteSpace:'nowrap', flexShrink:0}}>
              {view===v.k && <motion.span layoutId="main-nav-pill" transition={{type:'spring', stiffness:500, damping:35}} style={{position:'absolute', inset:0, borderRadius:8, background:'linear-gradient(135deg,var(--accent),var(--accent-light))', zIndex:-1}} />}
              <v.icon/> {v.label} {v.k==='screener'?<span style={{background: view===v.k?'rgba(4,16,31,0.18)':'rgba(255,255,255,0.08)',padding:'1px 6px',borderRadius:999,fontSize:10}}>{filtered.length}</span>:null}
            </button>
          ))}
        </nav>
        <div style={{display:'flex', gap:10, alignItems:'center', flexShrink:0}}>
          <ToolsMenu view={view} setView={setView} />
          <span className={`status-dot ${wsStatus==='open'?'green':wsStatus==='connecting'?'yellow':'red'}`} title={`Live feed: ${wsStatus}`} aria-label={`Live feed ${wsStatus}`} />
          <span className="mono" title="Last update" style={{fontSize:10, color:'var(--text3)', whiteSpace:'nowrap'}}>{lastUpdate ? new Date(lastUpdate).toLocaleTimeString('en-IN',{timeZone:'Asia/Kolkata'}) : '--:--:--'}</span>
          <SettingsMenu />
        </div>
      </div>

      <div id="main-content" tabIndex={-1} style={{flex:1, overflow: view==='screener' && !showDashboard ? 'hidden':'auto', padding:'8px 20px 0 20px', display:'flex', flexDirection:'column', gap:10}}>
        <Suspense fallback={<ViewSkeleton/>}>
        <AnimatePresence mode="wait">
        <motion.div key={view} initial={{opacity:0,y:8}} animate={{opacity:1,y:0}} exit={{opacity:0,y:-8}} transition={{duration:0.2,ease:[0.16,1,0.3,1]}} style={{flex:1, display:'flex', flexDirection:'column', minHeight:0}}>
          {view==='options'?<div style={{flex:1}}><OptionsHub theme={theme} /></div>
          :view==='intraday'?<div style={{flex:1, overflow:'auto'}}><IntradaySignals /></div>
          :view==='optioninstruments'?<div style={{flex:1, overflow:'auto'}}><OptionInstrumentsScreener /></div>
          :view==='paper'?<div style={{flex:1, overflow:'auto'}}><PaperTrading stocksMap={stocksMap} /></div>
          :view==='replay'?<div style={{flex:1, overflow:'auto'}}><MarketReplay symbol={selected||'RELIANCE'} /></div>
          :view==='alerts'?<div style={{flex:1, overflow:'auto'}}><AlertsCenter alerts={alerts} /></div>
          :view==='etf'?<div style={{flex:1, overflow:'auto'}}><ETFScreener /></div>
          :view==='elitequant'?<div style={{flex:1, overflow:'auto'}}><EliteQuantScreener /></div>
          :(<>
            {showDashboard && (
              <DashboardLayouts layout="bento">
              <section aria-labelledby="pulse-heading">
                <h2 id="pulse-heading" style={{fontSize:13, fontWeight:800, letterSpacing:'0.06em', textTransform:'uppercase', color:'#cbd5e1', marginBottom:10, display:'flex', gap:8, alignItems:'center'}}><span style={{width:4,height:16,background:'linear-gradient(180deg,#10b981,var(--accent))',borderRadius:999}}/> Market Pulse</h2>
                <MarketOverview data={overview} history={overviewHistoryRef.current} />
              </section>

              <section aria-labelledby="watchlist-heading">
                <h2 id="watchlist-heading" style={{fontSize:13,fontWeight:800,letterSpacing:'0.06em',textTransform:'uppercase',color:'#cbd5e1',marginBottom:10}}>Watchlist</h2>
                <WatchlistManager onSelect={handleSelect} />
              </section>

              <section aria-labelledby="insights-heading">
                <h2 id="insights-heading" style={{fontSize:13,fontWeight:800,letterSpacing:'0.06em',textTransform:'uppercase',color:'#cbd5e1',marginBottom:10, display:'flex',gap:8,alignItems:'center'}}><span style={{width:4,height:16,background:'linear-gradient(180deg,#f59e0b,var(--accent))',borderRadius:999}}/> AI Insights</h2>
                <AIInsights stocks={allStocks} />
              </section>
              </DashboardLayouts>
            )}

            <section aria-labelledby="screener-heading" style={{flex:1, display:'flex', flexDirection:'column', gap:8, minHeight:0}}>
              {showDashboard && <h2 id="screener-heading" style={{fontSize:13,fontWeight:800,letterSpacing:'0.06em',textTransform:'uppercase',color:'#cbd5e1', display:'flex',gap:8,alignItems:'center'}}><span style={{width:4,height:16,background:'linear-gradient(180deg,var(--accent),#8b5cf6)',borderRadius:999}}/> Screener — {filtered.length} results</h2>}
              <div className="filters" style={{borderRadius:12, border:'1px solid rgba(255,255,255,0.06)', padding:'8px 12px', flexShrink:0}}>
                <div style={{position:'relative'}}><span aria-hidden="true" style={{position:'absolute',left:10,top:'50%',transform:'translateY(-50%)',color:'#94a3b8'}}>⌕</span><input aria-label="Search symbol or company" className="input" placeholder="Search symbol or company" value={search} onChange={e=> setSearch(e.target.value)} style={{minWidth:220,paddingLeft:28,borderRadius:12}} /></div>
                <select aria-label="Filter by sector" className="input" value={sectorFilter} onChange={e=>setSectorFilter(e.target.value)} style={{borderRadius:12, minWidth:150}}><option value="">All Sectors</option>{sectors.map(s=> <option key={s.sector} value={s.sector}>{s.sector} ({s.count})</option>)}</select>
                <div style={{display:'flex',gap:6,flexWrap:'wrap'}}><span style={{fontSize:11,color:'#94a3b8',fontWeight:700,letterSpacing:'0.06em',textTransform:'uppercase',alignSelf:'center'}}>Quick</span>
                  <button aria-pressed={!!filters.gainers} className={`chip ${filters.gainers?'active':''}`} onClick={()=> toggleFilter('gainers')} aria-label="Filter gainers">↗ Gainers</button>
                  <button aria-pressed={!!filters.losers} className={`chip ${filters.losers?'active':''}`} onClick={()=> toggleFilter('losers')} aria-label="Filter losers">↘ Losers</button>
                  <button aria-pressed={!!filters.aboveVwap} className={`chip ${filters.aboveVwap?'active':''}`} onClick={()=> toggleFilter('aboveVwap')} aria-label="Filter above VWAP">◈ Above VWAP</button>
                  <button aria-pressed={!!filters.volumeSpike} className={`chip ${filters.volumeSpike?'active':''}`} onClick={()=> toggleFilter('volumeSpike')} aria-label="Filter volume spike">Vol Spike</button>
                  <button aria-pressed={!!filters.breakout} className={`chip ${filters.breakout?'active':''}`} onClick={()=> toggleFilter('breakout')} aria-label="Filter breakout">Breakout</button>
                  <button className="chip" onClick={()=> setFilters({})} aria-label="Clear filters" style={{background:'rgba(37,99,235,0.08)',borderColor:'rgba(37,99,235,0.2)',color:'#2563eb'}}>Clear</button>
                  <button className={`chip ${showAdvancedFilters||advancedConds.length?'active':''}`} onClick={()=>setShowAdvancedFilters(v=>!v)} aria-label="Toggle advanced filter builder">⚙ Advanced{advancedConds.length?` (${advancedConds.length})`:''}</button>
                  <div style={{marginLeft:'auto', display:'flex', gap:8, alignItems:'center'}}>
                    {!showDashboard && <span style={{fontSize:11, color:'#94a3b8'}}>{filtered.length} results</span>}
                    <button className="btn sm" aria-pressed={showDashboard} onClick={()=>setShowDashboard(v=>!v)} style={{borderRadius:8, fontWeight:700}}>{showDashboard?'▴ Hide':'▾ Show'} Dashboard</button>
                    <div style={{display:'flex',gap:2,background:'rgba(255,255,255,0.04)',borderRadius:8,padding:2,border:'1px solid rgba(255,255,255,0.06)'}}>
                      {['compact','comfortable'].map(d=>(
                        <button key={d} onClick={()=>setDensity(d)} aria-pressed={density===d} style={{padding:'5px 10px', fontSize:11, fontWeight:700, textTransform:'capitalize', borderRadius:6, border:'none', cursor:'pointer', background: density===d?'linear-gradient(135deg,var(--accent),var(--accent-light))':'transparent', color: density===d?'#04101f':'var(--text2)'}}>{d}</button>
                      ))}
                    </div>
                  </div>
                </div>
                {showAdvancedFilters && <div style={{marginTop:8}}><FilterBuilder onApply={setAdvancedConds} sectors={sectors} /></div>}
              </div>
              <div className="main" style={{padding:0, flex:1, minHeight:0}}>
                <div className="table-wrap" style={{flex:1}}><StockTable stocks={filtered} onSelect={handleSelect} selectedSymbol={selected} sortBy={sortBy} sortDir={sortDir} onSort={(k,dir)=>{setSortBy(k); setSortDir(dir)}} density={density} />
                  {filtered.length===0 && allStocks.length===0 && <div style={{position:'absolute',inset:0,display:'grid',placeItems:'center',textAlign:'center'}}><div><div style={{width:48,height:48,borderRadius:16,background:'linear-gradient(135deg, rgba(37,99,235,0.15), rgba(16,185,129,0.1))',display:'grid',placeItems:'center',margin:'0 auto 12px'}}>◈</div><div style={{fontWeight:700,color:'#f1f5f9'}}>Waiting for market data…</div><div style={{fontSize:11,marginTop:6,color:'#94a3b8'}}>Backend in <b style={{color:'#f1f5f9'}}>{dataMode}</b> mode • Establishing stream</div></div></div>}
                </div>
                {(selected||showDetail)&& <DetailPanel symbol={selected} onClose={()=>{setSelected(null);setShowDetail(false)}} liveState={liveSelectedState} theme={theme} />}
              </div>
            </section>

          </>)}
        </motion.div>
        </AnimatePresence>
        </Suspense>
      </div>

      <div style={{height:36, background:'rgba(13,27,42,0.9)', backdropFilter:'blur(16px)', borderTop:'1px solid rgba(255,255,255,0.06)', display:'flex', alignItems:'center', padding:'0 20px', gap:16, overflow:'hidden', flexShrink:0}}>
        <span style={{fontSize:10,color:'#f59e0b',fontWeight:800,letterSpacing:'0.08em',whiteSpace:'nowrap',display:'flex',gap:6,alignItems:'center'}}><span style={{width:6,height:6,borderRadius:999,background:'#f59e0b',animation:'pulse 1.5s infinite'}} aria-hidden="true"/> LIVE ALERTS</span>
        <div style={{display:'flex',gap:16,overflow:'hidden',whiteSpace:'nowrap',fontSize:11,flex:1}}>{alerts.length===0?<span style={{color:'#94a3b8'}}>Monitoring breakouts, volume spikes, VWAP crosses, momentum, RSI…</span>: alerts.slice(0,6).map(a=>(<span key={a.id} style={{display:'flex',gap:6,alignItems:'center',color:a.level==='bullish'?'#10b981':a.level==='bearish'?'#ef5350':'var(--accent)',background:'rgba(255,255,255,0.04)',padding:'3px 8px',borderRadius:999,border:'1px solid rgba(255,255,255,0.06)',fontWeight:600}}>{a.symbol} <span style={{opacity:0.7}}>{a.type}</span></span>))}</div>
        <span style={{fontSize:10,color:'#94a3b8',whiteSpace:'nowrap',background:'rgba(255,255,255,0.04)',padding:'4px 10px',borderRadius:999,border:'1px solid rgba(255,255,255,0.06)'}}>Score: Mom 25 + Vol 25 + RelVol 20 + Breakout 15 + VWAP 10 + Volatility 5 • <span style={{color:'#cbd5e1'}}>NOT advice</span></span>
      </div>
      <CommandPalette commands={ALL_DESTINATIONS} stocks={allStocks} onNavigate={setView} onSelectSymbol={handleSelect} />
    </div>
  )
}
