import React, { useEffect, useState, useMemo, useCallback, Suspense, lazy } from 'react'
import { motion } from 'framer-motion'
import Header from './components/Header.jsx'
import MarketOverview from './components/MarketOverview.jsx'
import StockTable from './components/StockTable.jsx'
import DetailPanel from './components/DetailPanel.jsx'
import WatchlistManager from './components/WatchlistManager.jsx'
import ThemeToggle from './components/ThemeToggle.jsx'
import LoginManager from './components/auth/LoginManager.jsx'
import { useWebSocket } from './hooks/useWebSocket.js'
import { fetchOverview, fetchMarketStatus, fetchSectors } from './services/api.js'
import { useStore } from './store/useStore.js'
import { DashboardLayouts, LayoutSwitcher, BentoGrid, BentoCard } from './components/layouts/DashboardLayouts.jsx'

const OptionsChain = lazy(()=> import('./components/OptionsChain.jsx'))
const OpenInterestChart = lazy(()=> import('./components/OpenInterestChart.jsx'))
const InstitutionalOptions = lazy(()=> import('./components/InstitutionalOptions.jsx'))
const AgileInstitutional = lazy(()=> import('./components/AgileInstitutional.jsx'))
const TickerTape = lazy(()=> import('./components/tradingview/TradingViewWidgets.jsx').then(m=>({default:m.TickerTape})))
const AdvancedChart = lazy(()=> import('./components/tradingview/TradingViewWidgets.jsx').then(m=>({default:m.AdvancedChart})))
const MarketOverviewTV = lazy(()=> import('./components/tradingview/TradingViewWidgets.jsx').then(m=>({default:m.MarketOverviewTV})))
const ScreenerTV = lazy(()=> import('./components/tradingview/TradingViewWidgets.jsx').then(m=>({default:m.ScreenerTV})))
const EconomicCalendar = lazy(()=> import('./components/tradingview/TradingViewWidgets.jsx').then(m=>({default:m.EconomicCalendar})))
const Heatmap = lazy(()=> import('./components/tradingview/TradingViewWidgets.jsx').then(m=>({default:m.Heatmap})))


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
  const [sortBy,setSortBy]=useState('score')
  const [sortDir,setSortDir]=useState('desc')
  const [alerts,setAlerts]=useState([])
  const [dataMode,setDataMode]=useState('mock')
  const [view,setView]=useState('screener')
  const [dashLayout,setDashLayout]=useState(()=>{ try{return localStorage.getItem('dashboard_layout')||'bento'}catch{return 'bento'}})
  const theme = useStore(s=>s.theme) || 'dark'
  useEffect(()=>{ try{localStorage.setItem('dashboard_layout',dashLayout)}catch{} },[dashLayout])

  const normalizeStock=(s)=>({ ...s, changePercent:s.changePercent??s.change_pct??s.changePct, relVolume:s.relVolume??s.rel_volume, companyName:s.companyName??s.company, isAboveVwap:s.isAboveVwap??s.is_above_vwap, volumeSpike:s.volumeSpike??s.volume_spike, isBreakout:s.isBreakout??s.momentum?.breakout, isBreakdown:s.isBreakdown??s.momentum?.breakdown, momentum5m:s.momentum5m??s.momentum?.ret_5m, gapPercent:s.gapPercent??s.gap_pct, vwap:s.vwap??s.indicators?.vwap, rsi:s.rsi??s.indicators?.rsi, ema9:s.ema9??s.indicators?.ema9, ema20:s.ema20??s.indicators?.ema20, synthetic:s.synthetic??s.freshness==='CLOSED' })

  useEffect(()=>{
    const normOv=(d)=>{ if(!d) return null; const na=(a)=>(a||[]).map(x=>({...x,changePercent:x.changePercent??x.change_pct, relVolume:x.relVolume??x.rel_volume})); return {...d, advancing:d.advancing, declining:d.declining, unchanged:d.unchanged, aboveVWAP:d.above_vwap??d.aboveVWAP, belowVWAP:d.below_vwap??d.belowVWAP, breakouts:d.breakouts??d.breakouts_count, breakdowns:d.breakdowns??d.breakdowns_count, topGainers:na(d.top_gainers??d.topGainers), topLosers:na(d.top_losers??d.topLosers), highestVolume:na(d.highest_volume??d.highestVolume), marketStatus:d.marketStatus??{status:d.status,is_open:d.is_live??d.is_open}, total:d.total??500 } }
    fetchMarketStatus().then(d=>{ if(d) d.is_open=d.is_live??d.is_open??false; setMarketStatus(d)}).catch(()=>{})
    fetchOverview().then(d=> setOverview(normOv(d))).catch(()=>{})
    fetchSectors().then(r=>{ const list=r.data||r.sectors||r; if(Array.isArray(list)){ if(list.length&&typeof list[0]==='object'&&list[0].sector) setSectors(list.map(x=>({sector:x.sector,count:x.count||0}))); else if(list.length&&typeof list[0]==='string') setSectors(list.map(s=>({sector:s,count:0}))); else setSectors(list)}}).catch(()=>{})
    const id=setInterval(()=>{ fetchMarketStatus().then(d=>{ if(d) d.is_open=d.is_live??d.is_open??false; setMarketStatus(d)}).catch(()=>{}); fetchOverview().then(d=>{ const n=normOv(d); if(n) setOverview(n)}).catch(()=>{}) },15000)
    return ()=> clearInterval(id)
  },[])

  const onMessage=useCallback((msg)=>{
    if(msg.type==='snapshot'){ const map={}; for(const s of (msg.data||[])) map[normalizeStock(s).symbol]=normalizeStock(s); setStocksMap(map); if(msg.marketStatus) setMarketStatus(prev=>({...prev,...msg.marketStatus,is_open:msg.marketStatus.is_open??msg.marketStatus.is_live??false})); if(msg.meta?.mode) setDataMode(msg.meta.mode); if(msg.dataMode) setDataMode(msg.dataMode) }
    else if(msg.type==='ticks'){ setStocksMap(prev=>{ const n={...prev}; for(const s of (msg.data||[])){ const nn=normalizeStock(s); n[nn.symbol]={...n[nn.symbol],...nn}} return n}); if(msg.alerts) setAlerts(p=>[...msg.alerts,...p].slice(0,100)) }
    if(msg.alerts) setAlerts(p=>[...msg.alerts,...p].slice(0,100)); if(msg.meta?.mode) setDataMode(msg.meta.mode)
  },[])
  const { status: wsStatus, lastUpdate }=useWebSocket(null,{onMessage})
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
    const dir=sortDir==='asc'?1:-1
    res=[...res].sort((a,b)=>{ let av=a[sortBy],bv=b[sortBy]; if(av==null) av=sortDir==='asc'?Infinity:-Infinity; if(bv==null) bv=sortDir==='asc'?Infinity:-Infinity; if(typeof av==='string') return av.localeCompare(bv)*dir; return (av-bv)*dir })
    return res
  },[allStocks,search,sectorFilter,filters,sortBy,sortDir])

  const handleSelect=(sym)=>{ setSelected(sym); setShowDetail(true) }
  const toggleFilter=(key)=> setFilters(prev=>({...prev,[key]:!prev[key]}))
  const liveSelectedState=selected?stocksMap[selected]:null
  const isClosed=marketStatus && !marketStatus.is_open
  const nextOpen=marketStatus?.next_open? new Date(marketStatus.next_open).toLocaleString('en-IN',{weekday:'short',hour:'2-digit',minute:'2-digit'}):'09:15 IST'
  const chartSymbol = selected ? `NSE:${selected}` : 'NSE:RELIANCE'

  return (
    <div className="app">
      <a href="#main-content" className="skip-link">Skip to content</a>
      <Suspense fallback={<div style={{height:46, background:'rgba(255,255,255,0.04)'}}/>}><TickerTape symbols={undefined} colorTheme={theme} /></Suspense>
      <Header marketStatus={marketStatus} connectionStatus={wsStatus} lastUpdate={lastUpdate} dataMode={dataMode} />
      <div style={{display:'flex', gap:8, padding:'6px 20px', background:'rgba(15,20,28,0.7)', borderBottom:'1px solid rgba(255,255,255,0.06)', alignItems:'center', flexWrap:'wrap'}}>
        <div style={{display:'flex', gap:6, alignItems:'center', fontSize:11, color:'#8ea0b8'}}><span style={{width:6,height:6,borderRadius:999, background: wsStatus==='open'?'#00e6a0':'#ff3b4a'}}/> {allStocks.length} symbols</div>
        <div style={{marginLeft:'auto', display:'flex', gap:8, alignItems:'center'}}>
          <LayoutSwitcher value={dashLayout} onChange={setDashLayout} />
          <ThemeToggle />
          <LoginManager />
        </div>
      </div>
      {isClosed && (
        <div style={{background:'linear-gradient(90deg, rgba(255,176,32,0.12), rgba(255,138,0,0.08))', padding:'8px 20px', fontSize:12, color:'#ffb020', display:'flex', gap:12, alignItems:'center', flexWrap:'wrap'}}>
          <span style={{fontWeight:800, display:'flex',gap:8,alignItems:'center'}}><span style={{width:8,height:8,borderRadius:999,background:'#ffb020'}}/> MARKET CLOSED</span>
          <span style={{color:'#eef4ff',fontWeight:600}}>Showing last close</span><span style={{color:'#8ea0b8',fontSize:11}}>Next open • {nextOpen}</span>
        </div>
      )}
      <div style={{display:'flex', gap:6, padding:'10px 20px', background:'rgba(15,20,28,0.5)', borderTop:'1px solid rgba(255,255,255,0.03)', borderBottom:'1px solid rgba(255,255,255,0.06)', flexWrap:'wrap'}}>
        {[{k:'screener',label:'Screener',icon:'◈',count:filtered.length},{k:'options',label:'Options',icon:'⛓'},{k:'institutional',label:'Institutional',icon:'🏛'},{k:'agile',label:'Agile Pro',icon:'⚡'}].map(v=>(
          <button key={v.k} aria-label={`Switch to ${v.label} view`} aria-pressed={view===v.k} className={`btn ${view===v.k?'active':''}`} onClick={()=> setView(v.k)} style={{borderRadius:8, fontWeight:700, fontSize:12}}><span aria-hidden="true">{v.icon}</span> {v.label} {v.count!=null&&view==='screener'?<span style={{background:view===v.k?'rgba(255,255,255,0.2)':'rgba(255,255,255,0.08)',padding:'1px 6px',borderRadius:999,fontSize:10}}>{v.count}</span>:null}</button>
        ))}
      </div>

      <div id="main-content" tabIndex={-1} style={{flex:1, overflow:'auto', padding:'14px 20px 0 20px', display:'flex', flexDirection:'column', gap:16}}>
        <Suspense fallback={<div style={{color:'#5b728c',textAlign:'center'}}>Loading view…</div>}>
          {view==='options'?<div style={{flex:1, display:'flex', flexDirection:'column', gap:14}}>
            <div style={{background:'rgba(15,20,28,0.6)', border:'1px solid rgba(255,255,255,0.06)', borderRadius:14, padding:14}}>
              <h3 style={{fontSize:11,fontWeight:800,letterSpacing:'0.06em',textTransform:'uppercase',color:'#8ea0b8',marginBottom:10}}>Open Interest — Weekly / Monthly</h3>
              <Suspense fallback={<div style={{height:320,background:'rgba(255,255,255,0.04)',borderRadius:12}}/>}><OpenInterestChart theme={theme} /></Suspense>
            </div>
            <OptionsChain/>
          </div>
          :view==='institutional'?<div style={{flex:1}}><InstitutionalOptions/></div>
          :view==='agile'?<div style={{flex:1}}><AgileInstitutional/></div>
          :(<>
            <section aria-labelledby="pulse-heading">
              <h2 id="pulse-heading" style={{fontSize:13, fontWeight:800, letterSpacing:'0.06em', textTransform:'uppercase', color:'#8ea0b8', marginBottom:10, display:'flex', gap:8, alignItems:'center'}}><span style={{width:4,height:16,background:'linear-gradient(180deg,#00e6a0,#2f8bff)',borderRadius:999}}/> Market Pulse</h2>
              <MarketOverview data={overview} />
              <div style={{marginTop:12}}>
                <BentoGrid>
                  <div><h3 style={{fontSize:11,fontWeight:800,letterSpacing:'0.06em',color:'#8ea0b8',marginBottom:8}}>TradingView Overview</h3><Suspense fallback={<div style={{height:120,background:'rgba(255,255,255,0.04)',borderRadius:12}}/>}><MarketOverviewTV theme={theme} height={360} /></Suspense></div>
                  <div><h3 style={{fontSize:11,fontWeight:800,letterSpacing:'0.06em',color:'#8ea0b8',marginBottom:8}}>Heatmap</h3><Suspense fallback={<div style={{height:120,background:'rgba(255,255,255,0.04)',borderRadius:12}}/>}><Heatmap theme={theme} height={360} /></Suspense></div>
                </BentoGrid>
              </div>
            </section>

            <section aria-labelledby="watchlist-heading" style={{display:'grid', gridTemplateColumns:'360px 1fr', gap:14}}>
              <div><h2 id="watchlist-heading" style={{fontSize:13,fontWeight:800,letterSpacing:'0.06em',textTransform:'uppercase',color:'#8ea0b8',marginBottom:10}}>Watchlist</h2><WatchlistManager onSelect={handleSelect} /></div>
              <div><h2 style={{fontSize:13,fontWeight:800,letterSpacing:'0.06em',textTransform:'uppercase',color:'#8ea0b8',marginBottom:10}}>Chart — {chartSymbol}</h2><BentoCard delay={1}><Suspense fallback={<div style={{height:300,display:'grid',placeItems:'center',color:'#5b728c'}}>Loading chart…</div>}><AdvancedChart symbol={chartSymbol} theme={theme} height={380} /></Suspense></BentoCard></div>
            </section>

            <section aria-labelledby="screener-heading" style={{flex:1, display:'flex', flexDirection:'column', gap:10}}>
              <h2 id="screener-heading" style={{fontSize:13,fontWeight:800,letterSpacing:'0.06em',textTransform:'uppercase',color:'#8ea0b8', display:'flex',gap:8,alignItems:'center'}}><span style={{width:4,height:16,background:'linear-gradient(180deg,#2f8bff,#8b5cf6)',borderRadius:999}}/> Screener — {filtered.length} results</h2>
              <div className="filters" style={{borderRadius:12, border:'1px solid rgba(255,255,255,0.06)'}}>
                <div style={{position:'relative'}}><span aria-hidden="true" style={{position:'absolute',left:10,top:'50%',transform:'translateY(-50%)',color:'#5b728c'}}>⌕</span><input aria-label="Search symbol or company" className="input" placeholder="Search symbol or company" value={search} onChange={e=> setSearch(e.target.value)} style={{minWidth:260,paddingLeft:28,borderRadius:12}} /></div>
                <select aria-label="Filter by sector" className="input" value={sectorFilter} onChange={e=>setSectorFilter(e.target.value)} style={{borderRadius:12, minWidth:160}}><option value="">All Sectors</option>{sectors.map(s=> <option key={s.sector} value={s.sector}>{s.sector} ({s.count})</option>)}</select>
                <div style={{display:'flex',gap:6,flexWrap:'wrap'}}><span style={{fontSize:11,color:'#5b728c',fontWeight:700,letterSpacing:'0.06em',textTransform:'uppercase',alignSelf:'center'}}>Quick</span>
                  <button aria-pressed={!!filters.gainers} className={`chip ${filters.gainers?'active':''}`} onClick={()=> toggleFilter('gainers')} aria-label="Filter gainers">↗ Gainers</button>
                  <button aria-pressed={!!filters.losers} className={`chip ${filters.losers?'active':''}`} onClick={()=> toggleFilter('losers')} aria-label="Filter losers">↘ Losers</button>
                  <button aria-pressed={!!filters.aboveVwap} className={`chip ${filters.aboveVwap?'active':''}`} onClick={()=> toggleFilter('aboveVwap')} aria-label="Filter above VWAP">◈ Above VWAP</button>
                  <button aria-pressed={!!filters.volumeSpike} className={`chip ${filters.volumeSpike?'active':''}`} onClick={()=> toggleFilter('volumeSpike')} aria-label="Filter volume spike">Vol Spike</button>
                  <button aria-pressed={!!filters.breakout} className={`chip ${filters.breakout?'active':''}`} onClick={()=> toggleFilter('breakout')} aria-label="Filter breakout">Breakout</button>
                  <button className="chip" onClick={()=> setFilters({})} aria-label="Clear filters" style={{background:'rgba(47,139,255,0.08)',borderColor:'rgba(47,139,255,0.2)',color:'#2f8bff'}}>Clear</button>
                </div>
              </div>
              <div className="main" style={{padding:0, minHeight:420}}>
                <div className="table-wrap" style={{flex:1}}><StockTable stocks={filtered} onSelect={handleSelect} selectedSymbol={selected} sortBy={sortBy} sortDir={sortDir} onSort={(k,dir)=>{setSortBy(k); setSortDir(dir)}} />
                  {filtered.length===0 && allStocks.length===0 && <div style={{position:'absolute',inset:0,display:'grid',placeItems:'center',textAlign:'center'}}><div><div style={{width:48,height:48,borderRadius:16,background:'linear-gradient(135deg, rgba(47,139,255,0.15), rgba(0,230,160,0.1))',display:'grid',placeItems:'center',margin:'0 auto 12px'}}>◈</div><div style={{fontWeight:700,color:'#eef4ff'}}>Waiting for market data…</div><div style={{fontSize:11,marginTop:6,color:'#5b728c'}}>Backend in <b style={{color:'#eef4ff'}}>{dataMode}</b> mode • Establishing stream</div></div></div>}
                </div>
                {(selected||showDetail)&& <DetailPanel symbol={selected} onClose={()=>{setSelected(null);setShowDetail(false)}} liveState={liveSelectedState} theme={theme} />}
              </div>
            </section>

            <section aria-labelledby="calendar-heading">
              <h2 id="calendar-heading" style={{fontSize:13,fontWeight:800,letterSpacing:'0.06em',textTransform:'uppercase',color:'#8ea0b8',marginBottom:10, display:'flex',gap:8,alignItems:'center'}}><span style={{width:4,height:16,background:'linear-gradient(180deg,#ffb020,#ff8a00)',borderRadius:999}}/> News & Calendar — Screener</h2>
              <BentoGrid>
                <div><h3 style={{fontSize:11,fontWeight:800,letterSpacing:'0.06em',color:'#8ea0b8',marginBottom:8}}>Economic Calendar</h3><Suspense fallback={<div style={{height:200,background:'rgba(255,255,255,0.04)',borderRadius:12}}/>}><EconomicCalendar theme={theme} height={400} /></Suspense></div>
                <div><h3 style={{fontSize:11,fontWeight:800,letterSpacing:'0.06em',color:'#8ea0b8',marginBottom:8}}>TradingView Screener</h3><Suspense fallback={<div style={{height:200,background:'rgba(255,255,255,0.04)',borderRadius:12}}/>}><ScreenerTV theme={theme} height={400} /></Suspense></div>
              </BentoGrid>
            </section>
            <div style={{height:12}} />
          </>)}
        </Suspense>
      </div>

      <div style={{height:36, background:'rgba(15,20,28,0.9)', backdropFilter:'blur(16px)', borderTop:'1px solid rgba(255,255,255,0.06)', display:'flex', alignItems:'center', padding:'0 20px', gap:16, overflow:'hidden', flexShrink:0}}>
        <span style={{fontSize:10,color:'#ffb020',fontWeight:800,letterSpacing:'0.08em',whiteSpace:'nowrap',display:'flex',gap:6,alignItems:'center'}}><span style={{width:6,height:6,borderRadius:999,background:'#ffb020',animation:'pulse 1.5s infinite'}} aria-hidden="true"/> LIVE ALERTS</span>
        <div style={{display:'flex',gap:16,overflow:'hidden',whiteSpace:'nowrap',fontSize:11,flex:1}}>{alerts.length===0?<span style={{color:'#5b728c'}}>Monitoring breakouts, volume spikes, VWAP crosses, momentum, RSI…</span>: alerts.slice(0,6).map(a=>(<span key={a.id} style={{display:'flex',gap:6,alignItems:'center',color:a.level==='bullish'?'#00e6a0':a.level==='bearish'?'#ff3b4a':'#2f8bff',background:'rgba(255,255,255,0.04)',padding:'3px 8px',borderRadius:999,border:'1px solid rgba(255,255,255,0.06)',fontWeight:600}}>{a.symbol} <span style={{opacity:0.7}}>{a.type}</span></span>))}</div>
        <span style={{fontSize:10,color:'#5b728c',whiteSpace:'nowrap',background:'rgba(255,255,255,0.04)',padding:'4px 10px',borderRadius:999,border:'1px solid rgba(255,255,255,0.06)'}}>Score: Mom 25 + Vol 25 + RelVol 20 + Breakout 15 + VWAP 10 + Volatility 5 • <span style={{color:'#8ea0b8'}}>NOT advice</span></span>
      </div>
    </div>
  )
}
