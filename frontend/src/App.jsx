import React, { useEffect, useState, useMemo, useCallback, Suspense, lazy } from 'react'
import Header from './components/Header.jsx'
import MarketOverview from './components/MarketOverview.jsx'
import StockTable from './components/StockTable.jsx'
import DetailPanel from './components/DetailPanel.jsx'
import { useWebSocket } from './hooks/useWebSocket.js'
import { fetchOverview, fetchMarketStatus, fetchSectors } from './services/api.js'

// lazy heavy views - code-split (saves ~300kb initial)
const OptionsChain = lazy(()=> import('./components/OptionsChain.jsx'))
const InstitutionalOptions = lazy(()=> import('./components/InstitutionalOptions.jsx'))
const AgileInstitutional = lazy(()=> import('./components/AgileInstitutional.jsx'))

export default function App(){
  const [marketStatus, setMarketStatus] = useState(null)
  const [overview, setOverview] = useState(null)
  const [stocksMap, setStocksMap] = useState({})
  const [sectors, setSectors] = useState([])
  const [selected, setSelected] = useState(null)
  const [showDetail, setShowDetail] = useState(false)
  const [search, setSearch] = useState('')
  const [sectorFilter, setSectorFilter] = useState('')
  const [filters, setFilters] = useState({})
  const [sortBy, setSortBy] = useState('score')
  const [sortDir, setSortDir] = useState('desc')
  const [alerts, setAlerts] = useState([])
  const [dataMode, setDataMode] = useState('mock')
  const [view, setView] = useState('screener')

  const normalizeStock = (s)=> ({
    ...s,
    changePercent: s.changePercent ?? s.change_pct ?? s.changePct,
    relVolume: s.relVolume ?? s.rel_volume,
    companyName: s.companyName ?? s.company,
    isAboveVwap: s.isAboveVwap ?? s.is_above_vwap,
    volumeSpike: s.volumeSpike ?? s.volume_spike,
    isBreakout: s.isBreakout ?? s.momentum?.breakout ?? s.momentum?.day_high_breakout,
    isBreakdown: s.isBreakdown ?? s.momentum?.breakdown ?? s.momentum?.day_low_breakdown,
    momentum5m: s.momentum5m ?? s.momentum?.ret_5m,
    gapPercent: s.gapPercent ?? s.gap_pct,
    vwap: s.vwap ?? s.indicators?.vwap,
    rsi: s.rsi ?? s.indicators?.rsi,
    ema9: s.ema9 ?? s.indicators?.ema9,
    ema20: s.ema20 ?? s.indicators?.ema20,
    synthetic: s.synthetic ?? s.freshness==='CLOSED',
  })

  useEffect(()=>{
    const normalizeOverview = (d)=>{
      if(!d) return null
      const normArr = (arr)=> (arr||[]).map(x=> ({...x, changePercent: x.changePercent ?? x.change_pct, relVolume: x.relVolume ?? x.rel_volume}))
      return {
        ...d,
        advancing: d.advancing,
        declining: d.declining,
        unchanged: d.unchanged,
        aboveVWAP: d.above_vwap ?? d.aboveVWAP,
        belowVWAP: d.below_vwap ?? d.belowVWAP,
        breakouts: d.breakouts ?? d.breakouts_count ?? d.breakouts,
        breakdowns: d.breakdowns ?? d.breakdowns_count,
        topGainers: normArr(d.top_gainers ?? d.topGainers),
        topLosers: normArr(d.top_losers ?? d.topLosers),
        highestVolume: normArr(d.highest_volume ?? d.highestVolume),
        marketStatus: d.marketStatus ?? {status: d.status, is_open: d.is_live ?? d.is_open},
        total: d.total ?? 500,
      }
    }
    fetchMarketStatus().then(d=>{ if(d) d.is_open = d.is_live ?? d.is_open ?? false; setMarketStatus(d)}).catch(()=>{})
    fetchOverview().then(d=> setOverview(normalizeOverview(d))).catch(()=>{})
    fetchSectors().then(r=> {
      const list = r.data || r.sectors || r
      if(Array.isArray(list)){
        if(list.length && typeof list[0]==='object' && list[0].sector) setSectors(list.map(x=> ({sector: x.sector, count: x.count || 0})))
        else if(list.length && typeof list[0]==='string') setSectors(list.map(s=> ({sector:s, count:0})))
        else setSectors(list)
      }
    }).catch(()=>{})
    // lighter poll - 15s instead of 5s, WS handles ticks
    const id=setInterval(()=>{
      fetchMarketStatus().then(d=>{ if(d) d.is_open = d.is_live ?? d.is_open ?? false; setMarketStatus(d)}).catch(()=>{})
      fetchOverview().then(d=> { const n=normalizeOverview(d); if(n) setOverview(n)}).catch(()=>{})
    }, 15000)
    return ()=> clearInterval(id)
  }, [])

  const onMessage = useCallback((msg)=>{
    if(msg.type==='snapshot'){
      const map={}
      for(const s of (msg.data||[])) map[normalizeStock(s).symbol]=normalizeStock(s)
      setStocksMap(map)
      if(msg.marketStatus) setMarketStatus(prev=> ({...(prev||{}), ...msg.marketStatus, is_open: msg.marketStatus.is_open ?? msg.marketStatus.is_live ?? false}))
      if(msg.meta?.mode) setDataMode(msg.meta.mode)
      if(msg.dataMode) setDataMode(msg.dataMode)
    } else if(msg.type==='ticks'){
      setStocksMap(prev=>{
        const next={...prev}
        for(const s of (msg.data||[])) {
          const n = normalizeStock(s)
          next[n.symbol]={...(next[n.symbol]||{}), ...n}
        }
        return next
      })
      if(msg.alerts) setAlerts(prev=> [...msg.alerts, ...prev].slice(0,100))
    }
    if(msg.alerts) setAlerts(prev=> [...msg.alerts, ...prev].slice(0,100))
    if(msg.meta?.mode) setDataMode(msg.meta.mode)
  }, [])

  const { status: wsStatus, lastUpdate } = useWebSocket(null, { onMessage })
  const allStocks = useMemo(()=> Object.values(stocksMap), [stocksMap])

  const filtered = useMemo(()=>{
    let res = allStocks
    if(search){
      const q=search.toLowerCase()
      res = res.filter(s=> (s.symbol?.toLowerCase().includes(q)) || (s.companyName?.toLowerCase().includes(q)))
    }
    if(sectorFilter) res = res.filter(s=> s.sector===sectorFilter)
    const getChg = s=> s.changePercent ?? 0
    if(filters.gainers) res = res.filter(s=> getChg(s)>0)
    if(filters.losers) res = res.filter(s=> getChg(s)<0)
    if(filters.aboveVwap) res = res.filter(s=> s.isAboveVwap===true)
    if(filters.belowVwap) res = res.filter(s=> s.isAboveVwap===false)
    if(filters.volumeSpike) res = res.filter(s=> s.volumeSpike)
    if(filters.breakout) res = res.filter(s=> s.isBreakout)
    if(filters.breakdown) res = res.filter(s=> s.isBreakdown)
    if(filters.highMomentum) res = res.filter(s=> Math.abs(s.momentum5m ?? 0)>1)
    const dir = sortDir==='asc'?1:-1
    res = [...res].sort((a,b)=>{
      let av = a[sortBy], bv = b[sortBy]
      if(av==null) av = sortDir==='asc'? Infinity : -Infinity
      if(bv==null) bv = sortDir==='asc'? Infinity : -Infinity
      if(typeof av==='string') return av.localeCompare(bv)*dir
      return (av - bv)*dir
    })
    return res
  }, [allStocks, search, sectorFilter, filters, sortBy, sortDir])

  const handleSelect = (sym)=>{ setSelected(sym); setShowDetail(true) }
  const toggleFilter = (key)=> setFilters(prev=> ({...prev, [key]: !prev[key]}))
  const liveSelectedState = selected ? stocksMap[selected] : null
  const isClosed = marketStatus && !marketStatus.is_open
  const nextOpen = marketStatus?.next_open ? new Date(marketStatus.next_open).toLocaleString('en-IN', {weekday:'short', hour:'2-digit', minute:'2-digit'}) : '09:15 IST'

  return (
    <div className="app">
      <Header marketStatus={marketStatus} connectionStatus={wsStatus} lastUpdate={lastUpdate} dataMode={dataMode} />
      {isClosed && (
        <div style={{background:'linear-gradient(90deg, rgba(255,176,32,0.12), rgba(255,138,0,0.08))', backdropFilter:'blur(12px)', borderBottom:'1px solid rgba(255,176,32,0.15)', padding:'8px 20px', fontSize:12, color:'#ffb020', display:'flex', gap:12, alignItems:'center', flexWrap:'wrap'}}>
          <span style={{fontWeight:800, display:'flex', gap:8, alignItems:'center'}}><span style={{width:8,height:8, borderRadius:999, background:'#ffb020', boxShadow:'0 0 8px rgba(255,176,32,0.6)'}} /> MARKET CLOSED</span>
          <span style={{color:'#eef4ff', fontWeight:600}}>Showing last trading day close</span>
          <span style={{color:'#8ea0b8', fontSize:11}}>Next open • {nextOpen} • Synthetic OHLC from prev_close • <span style={{color:'#ffb020'}}>CLOSED</span> freshness</span>
          <span style={{marginLeft:'auto', fontSize:11, color:'#5b728c', background:'rgba(255,255,255,0.06)', padding:'4px 10px', borderRadius:999}}>Tip: DATA_MODE=mock for simulated live</span>
        </div>
      )}
      <MarketOverview data={overview} />

      <div style={{display:'flex', gap:8, padding:'12px 20px', background:'rgba(15,20,28,0.5)', backdropFilter:'blur(12px)', borderTop:'1px solid rgba(255,255,255,0.03)', borderBottom:'1px solid rgba(255,255,255,0.06)', flexWrap:'wrap', alignItems:'center'}}>
        <div style={{display:'flex', gap:6, background:'rgba(255,255,255,0.04)', padding:4, borderRadius:12, border:'1px solid rgba(255,255,255,0.06)'}}>
          {[
            {k:'screener', label:'Screener', icon:'◈', count: filtered.length},
            {k:'options', label:'Options', icon:'⛓'},
            {k:'institutional', label:'Institutional', icon:'🏛'},
            {k:'agile', label:'Agile Pro', icon:'⚡'},
          ].map(v=>(
            <button key={v.k} className={`btn ${view===v.k?'active':''}`} onClick={()=> setView(v.k)} style={{borderRadius:8, fontWeight:700, fontSize:12, display:'flex', gap:6, alignItems:'center', border:'none'}}>
              <span style={{opacity: view===v.k?1:0.6}}>{v.icon}</span> {v.label} {v.count!=null && view==='screener' ? <span style={{background: view===v.k?'rgba(255,255,255,0.2)':'rgba(255,255,255,0.08)', padding:'1px 6px', borderRadius:999, fontSize:10}}>{v.count}</span> : null}
            </button>
          ))}
        </div>
        <span style={{marginLeft:'auto', fontSize:11, color:'#5b728c', display:'flex', gap:8, alignItems:'center'}}>
          <span style={{width:6,height:6, borderRadius:999, background: wsStatus==='open'?'#00e6a0':'#ff3b4a', boxShadow: wsStatus==='open'?'0 0 8px rgba(0,230,160,0.5)':''}} /> {wsStatus.toUpperCase()} • {allStocks.length} instruments
          <span style={{background:'rgba(255,255,255,0.06)', padding:'4px 8px', borderRadius:999, fontSize:10, fontWeight:700, letterSpacing:'0.06em'}}>⌘K to search</span>
        </span>
      </div>

      <Suspense fallback={<div style={{flex:1, display:'grid', placeItems:'center', color:'#5b728c'}}>Loading view…</div>}>
        {view==='options' ? <div style={{flex:1, overflow:'auto', padding:16}}><OptionsChain /></div>
        : view==='institutional' ? <div style={{flex:1, overflow:'auto', padding:16}}><InstitutionalOptions /></div>
        : view==='agile' ? <div style={{flex:1, overflow:'auto', padding:16}}><AgileInstitutional /></div>
        : (
          <>
            <div className="filters">
              <div style={{position:'relative'}}>
                <span style={{position:'absolute', left:10, top:'50%', transform:'translateY(-50%)', color:'#5b728c', fontSize:12}}>⌕</span>
                <input className="input" placeholder="Search symbol or company" value={search} onChange={e=> setSearch(e.target.value)} style={{minWidth:280, paddingLeft:28, borderRadius:12}} />
              </div>
              <select className="input" value={sectorFilter} onChange={e=> setSectorFilter(e.target.value)} style={{borderRadius:12, minWidth:160}}>
                <option value="">All Sectors</option>
                {sectors.map(s=> <option key={s.sector} value={s.sector}>{s.sector} ({s.count})</option>)}
              </select>
              <div style={{display:'flex', gap:6, flexWrap:'wrap', alignItems:'center'}}>
                <span style={{fontSize:11, color:'#5b728c', fontWeight:700, letterSpacing:'0.06em', textTransform:'uppercase'}}>Quick</span>
                <button className={`chip ${filters.gainers?'active':''}`} onClick={()=> toggleFilter('gainers')}>↗ Gainers</button>
                <button className={`chip ${filters.losers?'active':''}`} onClick={()=> toggleFilter('losers')}>↘ Losers</button>
                <button className={`chip ${filters.aboveVwap?'active':''}`} onClick={()=> toggleFilter('aboveVwap')}>◈ Above VWAP</button>
                <button className={`chip ${filters.belowVwap?'active':''}`} onClick={()=> toggleFilter('belowVwap')}>Below VWAP</button>
                <button className={`chip ${filters.volumeSpike?'active':''}`} onClick={()=> toggleFilter('volumeSpike')}>Vol Spike</button>
                <button className={`chip ${filters.breakout?'active':''}`} onClick={()=> toggleFilter('breakout')}>Breakout</button>
                <button className="chip" onClick={()=> setFilters({})} style={{background:'rgba(47,139,255,0.08)', borderColor:'rgba(47,139,255,0.2)', color:'#2f8bff'}}>Clear</button>
              </div>
              <div style={{marginLeft:'auto', display:'flex', gap:10, alignItems:'center', fontSize:11, color:'#8ea0b8', background:'rgba(255,255,255,0.04)', padding:'6px 12px', borderRadius:999, border:'1px solid rgba(255,255,255,0.06)'}}>
                <span style={{fontWeight:700, color:'#eef4ff'}}>{filtered.length} / {allStocks.length}</span>
                <span style={{width:1, height:12, background:'rgba(255,255,255,0.08)'}} />
                <span style={{fontFamily:'JetBrains Mono', fontSize:10}}>{sortBy} {sortDir==='asc'?'↑':'↓'}</span>
              </div>
            </div>

            <div className="main">
              <div className="table-wrap">
                <StockTable stocks={filtered} onSelect={handleSelect} selectedSymbol={selected} sortBy={sortBy} sortDir={sortDir} onSort={(k,dir)=>{setSortBy(k); setSortDir(dir)}} />
                {filtered.length===0 && allStocks.length===0 && (
                  <div style={{position:'absolute', inset:0, display:'grid', placeItems:'center', textAlign:'center'}}>
                    <div>
                      <div style={{width:48,height:48, borderRadius:16, background:'linear-gradient(135deg, rgba(47,139,255,0.15), rgba(0,230,160,0.1))', display:'grid', placeItems:'center', margin:'0 auto 12px', border:'1px solid rgba(255,255,255,0.06)'}}>◈</div>
                      <div style={{fontSize:14, fontWeight:700, color:'#eef4ff'}}>Waiting for market data…</div>
                      <div style={{fontSize:11, marginTop:6, color:'#5b728c'}}>Backend in <b style={{color:'#eef4ff'}}>{dataMode}</b> mode • Establishing WebSocket stream</div>
                      <div style={{marginTop:12, width:120, height:2, background:'rgba(255,255,255,0.06)', borderRadius:999, overflow:'hidden', marginLeft:'auto', marginRight:'auto'}}><div style={{height:'100%', width:'50%', background:'linear-gradient(90deg,#2f8bff,#00e6a0)', animation:'shimmer 1.2s infinite'}} /></div>
                    </div>
                  </div>
                )}
              </div>
              {(selected || showDetail) && (
                <DetailPanel symbol={selected} onClose={()=> {setSelected(null); setShowDetail(false)}} liveState={liveSelectedState} />
              )}
            </div>
          </>
        )}
      </Suspense>

      <div style={{height:36, background:'rgba(15,20,28,0.9)', backdropFilter:'blur(16px)', borderTop:'1px solid rgba(255,255,255,0.06)', display:'flex', alignItems:'center', padding:'0 20px', gap:16, overflow:'hidden', flexShrink:0}}>
        <span style={{fontSize:10, color:'#ffb020', fontWeight:800, letterSpacing:'0.08em', whiteSpace:'nowrap', display:'flex', gap:6, alignItems:'center'}}><span style={{width:6,height:6, borderRadius:999, background:'#ffb020', animation:'pulse 1.5s infinite'}} /> LIVE ALERTS</span>
        <div style={{display:'flex', gap:16, overflow:'hidden', whiteSpace:'nowrap', fontSize:11, flex:1}}>
          {alerts.length===0 ? <span style={{color:'#5b728c'}}>Monitoring breakouts, volume spikes, VWAP crosses, momentum, RSI…</span> :
            alerts.slice(0,6).map(a=>(
              <span key={a.id} style={{display:'flex', gap:6, alignItems:'center', color: a.level==='bullish'?'#00e6a0': a.level==='bearish'?'#ff3b4a':'#2f8bff', background:'rgba(255,255,255,0.04)', padding:'3px 8px', borderRadius:999, border:'1px solid rgba(255,255,255,0.06)', fontWeight:600}}>{a.symbol} <span style={{opacity:0.7}}>{a.type}</span></span>
            ))
          }
        </div>
        <span style={{fontSize:10, color:'#5b728c', whiteSpace:'nowrap', background:'rgba(255,255,255,0.04)', padding:'4px 10px', borderRadius:999, border:'1px solid rgba(255,255,255,0.06)'}}>Score: Mom 25 + Vol 25 + RelVol 20 + Breakout 15 + VWAP 10 + Volatility 5 • <span style={{color:'#8ea0b8'}}>NOT advice</span></span>
      </div>
    </div>
  )
}
