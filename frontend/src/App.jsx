import React, { useEffect, useState, useMemo, useCallback, Suspense, lazy } from 'react'
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
import { LayoutSwitcher } from './components/layouts/DashboardLayouts.jsx'

const OptionsChain = lazy(()=> import('./components/OptionsChain.jsx'))
const OpenInterestChart = lazy(()=> import('./components/OpenInterestChart.jsx'))
const InstitutionalOptions = lazy(()=> import('./components/InstitutionalOptions.jsx'))
const AgileInstitutional = lazy(()=> import('./components/AgileInstitutional.jsx'))
const OptionsInsights = lazy(()=> import('./components/OptionsInsights.jsx'))


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
  const [showDashboard,setShowDashboard]=useState(()=>{ try{return localStorage.getItem('show_dashboard')==='1'}catch{return false} })
  const [density,setDensity]=useState(()=>{ try{return localStorage.getItem('row_density')||'compact'}catch{return 'compact'} })
  const theme = useStore(s=>s.theme) || 'dark'
  useEffect(()=>{ try{localStorage.setItem('dashboard_layout',dashLayout)}catch{} },[dashLayout])
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
  })

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
  const nextOpen=marketStatus?.next_open? new Date(marketStatus.next_open).toLocaleString('en-IN',{weekday:'short',hour:'2-digit',minute:'2-digit',timeZone:'Asia/Kolkata'})+' IST':'09:15 IST'

  return (
    <div className="app">
      <a href="#main-content" className="skip-link">Skip to content</a>
      <Header marketStatus={marketStatus} connectionStatus={wsStatus} lastUpdate={lastUpdate} dataMode={dataMode} />
      <div style={{display:'flex', gap:8, padding:'4px 20px', background:'rgba(13,27,42,0.7)', borderBottom:'1px solid rgba(255,255,255,0.06)', alignItems:'center', flexWrap:'wrap'}}>
        <div style={{display:'flex', gap:6, alignItems:'center', fontSize:11, color:'#cbd5e1'}}><span style={{width:6,height:6,borderRadius:999, background: wsStatus==='open'?'#10b981':'#ef5350'}}/> {allStocks.length} symbols</div>
        <div style={{marginLeft:'auto', display:'flex', gap:8, alignItems:'center'}}>
          <LayoutSwitcher value={dashLayout} onChange={setDashLayout} />
          <ThemeToggle />
          <LoginManager />
        </div>
      </div>
      {isClosed && (
        <div style={{background:'linear-gradient(90deg, rgba(245,158,11,0.12), rgba(217,119,6,0.08))', padding:'5px 20px', fontSize:12, color:'#f59e0b', display:'flex', gap:12, alignItems:'center', flexWrap:'wrap'}}>
          <span style={{fontWeight:800, display:'flex',gap:8,alignItems:'center'}}><span style={{width:8,height:8,borderRadius:999,background:'#f59e0b'}}/> MARKET CLOSED</span>
          <span style={{color:'#f1f5f9',fontWeight:600}}>Showing last close</span><span style={{color:'#cbd5e1',fontSize:11}}>Next open • {nextOpen}</span>
        </div>
      )}
      <div style={{display:'flex', gap:6, padding:'6px 20px', background:'rgba(13,27,42,0.5)', borderTop:'1px solid rgba(255,255,255,0.03)', borderBottom:'1px solid rgba(255,255,255,0.06)', flexWrap:'wrap', alignItems:'center'}}>
        {[{k:'screener',label:'Screener',icon:'◈',count:filtered.length},{k:'options',label:'Options',icon:'⛓'},{k:'insights',label:'Options Insights',icon:'📊'},{k:'institutional',label:'Institutional',icon:'🏛'},{k:'agile',label:'Agile Pro',icon:'⚡'}].map(v=>(
          <button key={v.k} aria-label={`Switch to ${v.label} view`} aria-pressed={view===v.k} className={`btn ${view===v.k?'active':''}`} onClick={()=> setView(v.k)} style={{borderRadius:8, fontWeight:700, fontSize:12}}><span aria-hidden="true">{v.icon}</span> {v.label} {v.count!=null&&view==='screener'?<span style={{background:view===v.k?'rgba(255,255,255,0.2)':'rgba(255,255,255,0.08)',padding:'1px 6px',borderRadius:999,fontSize:10}}>{v.count}</span>:null}</button>
        ))}
        {view==='screener' && (
          <div style={{marginLeft:'auto', display:'flex', gap:6, alignItems:'center'}}>
            <button className="btn sm" aria-pressed={showDashboard} onClick={()=>setShowDashboard(v=>!v)} style={{borderRadius:8, fontWeight:700}}>{showDashboard?'▴ Hide':'▾ Show'} Dashboard</button>
            <div style={{display:'flex',gap:2,background:'rgba(255,255,255,0.04)',borderRadius:8,padding:2,border:'1px solid rgba(255,255,255,0.06)'}}>
              {['compact','comfortable'].map(d=>(
                <button key={d} onClick={()=>setDensity(d)} aria-pressed={density===d} style={{padding:'5px 10px', fontSize:11, fontWeight:700, textTransform:'capitalize', borderRadius:6, border:'none', cursor:'pointer', background: density===d?'linear-gradient(135deg,#2563eb,#64b5f6)':'transparent', color: density===d?'#fff':'#cbd5e1'}}>{d}</button>
              ))}
            </div>
          </div>
        )}
      </div>

      <div id="main-content" tabIndex={-1} style={{flex:1, overflow: view==='screener' && !showDashboard ? 'hidden':'auto', padding:'8px 20px 0 20px', display:'flex', flexDirection:'column', gap:10}}>
        <Suspense fallback={<div style={{color:'#94a3b8',textAlign:'center'}}>Loading view…</div>}>
          {view==='options'?<div style={{flex:1, display:'flex', flexDirection:'column', gap:14}}>
            <div style={{background:'rgba(13,27,42,0.6)', border:'1px solid rgba(255,255,255,0.06)', borderRadius:14, padding:14}}>
              <h3 style={{fontSize:11,fontWeight:800,letterSpacing:'0.06em',textTransform:'uppercase',color:'#cbd5e1',marginBottom:10}}>Open Interest — Weekly / Monthly</h3>
              <Suspense fallback={<div style={{height:320,background:'rgba(255,255,255,0.04)',borderRadius:12}}/>}><OpenInterestChart theme={theme} /></Suspense>
            </div>
            <OptionsChain/>
          </div>
          :view==='insights'?<div style={{flex:1}}><OptionsInsights theme={theme} /></div>
          :view==='institutional'?<div style={{flex:1}}><InstitutionalOptions/></div>
          :view==='agile'?<div style={{flex:1}}><AgileInstitutional/></div>
          :(<>
            {showDashboard && (<>
              <section aria-labelledby="pulse-heading">
                <h2 id="pulse-heading" style={{fontSize:13, fontWeight:800, letterSpacing:'0.06em', textTransform:'uppercase', color:'#cbd5e1', marginBottom:10, display:'flex', gap:8, alignItems:'center'}}><span style={{width:4,height:16,background:'linear-gradient(180deg,#10b981,#2563eb)',borderRadius:999}}/> Market Pulse</h2>
                <MarketOverview data={overview} />
              </section>

              <section aria-labelledby="watchlist-heading">
                <h2 id="watchlist-heading" style={{fontSize:13,fontWeight:800,letterSpacing:'0.06em',textTransform:'uppercase',color:'#cbd5e1',marginBottom:10}}>Watchlist</h2>
                <WatchlistManager onSelect={handleSelect} />
              </section>
            </>)}

            <section aria-labelledby="screener-heading" style={{flex:1, display:'flex', flexDirection:'column', gap:8, minHeight:0}}>
              {showDashboard && <h2 id="screener-heading" style={{fontSize:13,fontWeight:800,letterSpacing:'0.06em',textTransform:'uppercase',color:'#cbd5e1', display:'flex',gap:8,alignItems:'center'}}><span style={{width:4,height:16,background:'linear-gradient(180deg,#2563eb,#8b5cf6)',borderRadius:999}}/> Screener — {filtered.length} results</h2>}
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
                  {!showDashboard && <span style={{marginLeft:'auto', fontSize:11, color:'#94a3b8', alignSelf:'center'}}>{filtered.length} results</span>}
                </div>
              </div>
              <div className="main" style={{padding:0, flex:1, minHeight:0}}>
                <div className="table-wrap" style={{flex:1}}><StockTable stocks={filtered} onSelect={handleSelect} selectedSymbol={selected} sortBy={sortBy} sortDir={sortDir} onSort={(k,dir)=>{setSortBy(k); setSortDir(dir)}} density={density} />
                  {filtered.length===0 && allStocks.length===0 && <div style={{position:'absolute',inset:0,display:'grid',placeItems:'center',textAlign:'center'}}><div><div style={{width:48,height:48,borderRadius:16,background:'linear-gradient(135deg, rgba(37,99,235,0.15), rgba(16,185,129,0.1))',display:'grid',placeItems:'center',margin:'0 auto 12px'}}>◈</div><div style={{fontWeight:700,color:'#f1f5f9'}}>Waiting for market data…</div><div style={{fontSize:11,marginTop:6,color:'#94a3b8'}}>Backend in <b style={{color:'#f1f5f9'}}>{dataMode}</b> mode • Establishing stream</div></div></div>}
                </div>
                {(selected||showDetail)&& <DetailPanel symbol={selected} onClose={()=>{setSelected(null);setShowDetail(false)}} liveState={liveSelectedState} theme={theme} />}
              </div>
            </section>

          </>)}
        </Suspense>
      </div>

      <div style={{height:36, background:'rgba(13,27,42,0.9)', backdropFilter:'blur(16px)', borderTop:'1px solid rgba(255,255,255,0.06)', display:'flex', alignItems:'center', padding:'0 20px', gap:16, overflow:'hidden', flexShrink:0}}>
        <span style={{fontSize:10,color:'#f59e0b',fontWeight:800,letterSpacing:'0.08em',whiteSpace:'nowrap',display:'flex',gap:6,alignItems:'center'}}><span style={{width:6,height:6,borderRadius:999,background:'#f59e0b',animation:'pulse 1.5s infinite'}} aria-hidden="true"/> LIVE ALERTS</span>
        <div style={{display:'flex',gap:16,overflow:'hidden',whiteSpace:'nowrap',fontSize:11,flex:1}}>{alerts.length===0?<span style={{color:'#94a3b8'}}>Monitoring breakouts, volume spikes, VWAP crosses, momentum, RSI…</span>: alerts.slice(0,6).map(a=>(<span key={a.id} style={{display:'flex',gap:6,alignItems:'center',color:a.level==='bullish'?'#10b981':a.level==='bearish'?'#ef5350':'#2563eb',background:'rgba(255,255,255,0.04)',padding:'3px 8px',borderRadius:999,border:'1px solid rgba(255,255,255,0.06)',fontWeight:600}}>{a.symbol} <span style={{opacity:0.7}}>{a.type}</span></span>))}</div>
        <span style={{fontSize:10,color:'#94a3b8',whiteSpace:'nowrap',background:'rgba(255,255,255,0.04)',padding:'4px 10px',borderRadius:999,border:'1px solid rgba(255,255,255,0.06)'}}>Score: Mom 25 + Vol 25 + RelVol 20 + Breakout 15 + VWAP 10 + Volatility 5 • <span style={{color:'#cbd5e1'}}>NOT advice</span></span>
      </div>
    </div>
  )
}
