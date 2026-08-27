import React, { useEffect, useState, useMemo, useCallback, useRef } from 'react'
import Header from './components/Header.jsx'
import MarketOverview from './components/MarketOverview.jsx'
import StockTable from './components/StockTable.jsx'
import DetailPanel from './components/DetailPanel.jsx'
import { useWebSocket } from './hooks/useWebSocket.js'
import { fetchOverview, fetchMarketStatus, fetchSectors } from './services/api.js'

export default function App(){
  const [marketStatus, setMarketStatus] = useState(null)
  const [overview, setOverview] = useState(null)
  const [stocksMap, setStocksMap] = useState({}) // symbol -> state
  const [sectors, setSectors] = useState([])
  const [selected, setSelected] = useState(null)
  const [showDetail, setShowDetail] = useState(false)
  const [search, setSearch] = useState('')
  const [sectorFilter, setSectorFilter] = useState('')
  const [filters, setFilters] = useState({}) // gainer etc chips
  const [sortBy, setSortBy] = useState('score')
  const [sortDir, setSortDir] = useState('desc')
  const [alerts, setAlerts] = useState([])
  const [dataMode, setDataMode] = useState('mock')
  const [columnFilters, setColumnFilters] = useState({})

  // normalize helper
  const normalizeStock = (s)=>{
    // s may have snake_case or camelCase
    return {
      ...s,
      changePercent: s.changePercent ?? s.change_pct ?? s.changePct,
      change_pct: s.change_pct ?? s.changePercent,
      relVolume: s.relVolume ?? s.rel_volume,
      rel_volume: s.rel_volume ?? s.relVolume,
      companyName: s.companyName ?? s.company,
      company: s.company ?? s.companyName,
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
    }
  }

  // initial fetch
  useEffect(()=>{
    fetchMarketStatus().then(d=>{
      // backend market/status returns is_live vs is_open, normalize
      if(d) d.is_open = d.is_live ?? d.is_open ?? false
      setMarketStatus(d)
    }).catch(()=>{})
    fetchOverview().then(d=>{
      if(d){
        const normArr = (arr)=> (arr||[]).map(x=> ({...x, changePercent: x.changePercent ?? x.change_pct, relVolume: x.relVolume ?? x.rel_volume}))
        const norm = {
          ...d,
          advancing: d.advancing,
          declining: d.declining,
          unchanged: d.unchanged,
          aboveVWAP: d.above_vwap ?? d.aboveVWAP,
          belowVWAP: d.below_vwap ?? d.belowVWAP,
          breakouts: d.breakouts ?? d.breakouts,
          breakdowns: d.breakdowns ?? d.breakdowns,
          topGainers: normArr(d.top_gainers ?? d.topGainers),
          topLosers: normArr(d.top_losers ?? d.topLosers),
          highestVolume: normArr(d.highest_volume ?? d.highestVolume),
          highestRelVolume: normArr(d.highest_rel_volume ?? d.highestRelVolume),
          strongestMomentum: normArr(d.strongest_momentum ?? d.strongestMomentum),
          weakestMomentum: normArr(d.weakest_momentum ?? d.weakestMomentum),
          marketStatus: d.marketStatus ?? {status: d.status, is_open: d.is_live},
        }
        setOverview(norm)
      }
    }).catch(()=>{})
    // sectors are available via universe or sectors endpoint; try both
    fetchSectors().then(r=> {
      // r may be {data: [...] } or {sectors: [...] } or flat
      const list = r.data || r.sectors || r
      if(Array.isArray(list)){
        // list may be objects with sector field
        if(list.length && typeof list[0]==='object' && list[0].sector){
          setSectors(list.map(x=> ({sector: x.sector, count: x.count || x.avg_change || 0})))
        } else if(list.length && typeof list[0]==='string'){
          setSectors(list.map(s=> ({sector:s, count:0})))
        } else {
          setSectors(list)
        }
      }
    }).catch(()=>{})
    const id=setInterval(()=>{
      fetchMarketStatus().then(d=>{
        if(d) d.is_open = d.is_live ?? d.is_open ?? false
        setMarketStatus(d)
      }).catch(()=>{})
      fetchOverview().then(d=>{
        if(d){
          const normArr = (arr)=> (arr||[]).map(x=> ({...x, changePercent: x.changePercent ?? x.change_pct, relVolume: x.relVolume ?? x.rel_volume}))
          const norm = {
            ...d,
            aboveVWAP: d.above_vwap ?? d.aboveVWAP,
            belowVWAP: d.below_vwap ?? d.belowVWAP,
            topGainers: normArr(d.top_gainers ?? d.topGainers),
            topLosers: normArr(d.top_losers ?? d.topLosers),
            highestVolume: normArr(d.highest_volume ?? d.highestVolume),
            highestRelVolume: normArr(d.highest_rel_volume ?? d.highestRelVolume),
            strongestMomentum: normArr(d.strongest_momentum ?? d.strongestMomentum),
            weakestMomentum: normArr(d.weakest_momentum ?? d.weakestMomentum),
          }
          setOverview(norm)
        }
      }).catch(()=>{})
    }, 5000)
    return ()=> clearInterval(id)
  }, [])

  const onMessage = useCallback((msg)=>{
    if(msg.type==='snapshot'){
      const map={}
      for(const s of (msg.data||[])) {
        const n = normalizeStock(s)
        map[n.symbol]=n
      }
      setStocksMap(map)
      if(msg.marketStatus) setMarketStatus(prev=> ({...(prev||{}), ...msg.marketStatus, is_open: msg.marketStatus.is_open ?? msg.marketStatus.is_live ?? false}))
      if(msg.meta?.mode) setDataMode(msg.meta.mode)
      if(msg.dataMode) setDataMode(msg.dataMode)
      if(msg.meta?.total) ; // not needed
    } else if(msg.type==='ticks'){
      setStocksMap(prev=>{
        const next={...prev}
        for(const s of (msg.data||[])) {
          const n = normalizeStock(s)
          const existing=next[n.symbol]||{}
          next[n.symbol]={...existing, ...n}
        }
        return next
      })
      if(msg.alerts){
        setAlerts(prev=> [...msg.alerts, ...prev].slice(0,100))
      }
    } else if(msg.type==='heartbeat'){
      // keep alive
    }
    if(msg.alerts) setAlerts(prev=> [...msg.alerts, ...prev].slice(0,100))
    if(msg.meta?.mode) setDataMode(msg.meta.mode)
  }, [])

  const { status: wsStatus, lastUpdate } = useWebSocket(null, { onMessage })

  const allStocks = useMemo(()=> Object.values(stocksMap), [stocksMap])

  // filtered + sorted
  const filtered = useMemo(()=>{
    let res = allStocks
    if(search){
      const q=search.toLowerCase()
      res = res.filter(s=> (s.symbol && s.symbol.toLowerCase().includes(q)) || (s.companyName && s.companyName.toLowerCase().includes(q)) || (s.company && s.company.toLowerCase().includes(q)))
    }
    if(sectorFilter) res = res.filter(s=> s.sector===sectorFilter)
    // chip filters
    const getChg = s=> s.changePercent ?? s.change_pct ?? 0
    if(filters.gainers) res = res.filter(s=> getChg(s)>0)
    if(filters.losers) res = res.filter(s=> getChg(s)<0)
    if(filters.aboveVwap) res = res.filter(s=> s.isAboveVwap===true || s.is_above_vwap===true)
    if(filters.belowVwap) res = res.filter(s=> s.isAboveVwap===false || s.is_above_vwap===false)
    if(filters.volumeSpike) res = res.filter(s=> s.volumeSpike || s.volume_spike)
    if(filters.breakout) res = res.filter(s=> s.isBreakout || s.is_breakout)
    if(filters.breakdown) res = res.filter(s=> s.isBreakdown || s.is_breakdown)
    if(filters.highMomentum) res = res.filter(s=> Math.abs(s.momentum5m ?? s.momentum?.ret_5m ?? 0)>1)
    if(filters.scoreAbove) res = res.filter(s=> (s.score ?? 0) > Number(filters.scoreAbove))
    if(filters.rsiAbove) res = res.filter(s=> (s.rsi ?? 0) > Number(filters.rsiAbove))
    // sort
    const dir = sortDir==='asc'?1:-1
    res = [...res].sort((a,b)=>{
      let av = a[sortBy], bv = b[sortBy]
      // handle nulls
      if(av==null) av = sortDir==='asc'? Infinity : -Infinity
      if(bv==null) bv = sortDir==='asc'? Infinity : -Infinity
      if(typeof av==='string') return av.localeCompare(bv)*dir
      return (av - bv)*dir
    })
    return res
  }, [allStocks, search, sectorFilter, filters, sortBy, sortDir])

  const handleSelect = (sym)=>{
    setSelected(sym)
    setShowDetail(true)
  }

  const toggleFilter = (key)=>{
    setFilters(prev=> ({...prev, [key]: !prev[key]}))
  }

  const liveSelectedState = selected ? stocksMap[selected] : null

  return (
    <div className="app">
      <Header marketStatus={marketStatus} connectionStatus={wsStatus} lastUpdate={lastUpdate} dataMode={dataMode} />
      <MarketOverview data={overview} />

      <div className="filters">
        <input className="input" placeholder="Search symbol / company (e.g., RELIANCE)" value={search} onChange={e=> setSearch(e.target.value)} style={{minWidth:260}} />
        <select className="input" value={sectorFilter} onChange={e=> setSectorFilter(e.target.value)}>
          <option value="">All Sectors</option>
          {sectors.map(s=> <option key={s.sector} value={s.sector}>{s.sector} ({s.count})</option>)}
        </select>
        <div style={{display:'flex', gap:6, flexWrap:'wrap', alignItems:'center'}}>
          <span style={{fontSize:11, color:'#8b9bb4'}}>Filters:</span>
          <button className={`chip ${filters.gainers?'active':''}`} onClick={()=> toggleFilter('gainers')}>Gainers</button>
          <button className={`chip ${filters.losers?'active':''}`} onClick={()=> toggleFilter('losers')}>Losers</button>
          <button className={`chip ${filters.aboveVwap?'active':''}`} onClick={()=> toggleFilter('aboveVwap')}>Above VWAP</button>
          <button className={`chip ${filters.belowVwap?'active':''}`} onClick={()=> toggleFilter('belowVwap')}>Below VWAP</button>
          <button className={`chip ${filters.volumeSpike?'active':''}`} onClick={()=> toggleFilter('volumeSpike')}>Vol Spike</button>
          <button className={`chip ${filters.breakout?'active':''}`} onClick={()=> toggleFilter('breakout')}>Breakout</button>
          <button className={`chip ${filters.breakdown?'active':''}`} onClick={()=> toggleFilter('breakdown')}>Breakdown</button>
          <button className={`chip ${filters.highMomentum?'active':''}`} onClick={()=> toggleFilter('highMomentum')}>High Mom</button>
          <button className="chip" onClick={()=> setFilters({})}>Clear</button>
        </div>
        <div style={{marginLeft:'auto', display:'flex', gap:8, alignItems:'center', fontSize:12, color:'#8b9bb4'}}>
          <span>{filtered.length} / {allStocks.length} shown</span>
          <span style={{color:'#5a6b84'}}>|</span>
          <span>Sort: {sortBy} {sortDir}</span>
          <button className="btn sm" onClick={()=> setSelected(null)}>Clear Selection</button>
        </div>
      </div>

      <div className="main">
        <div className="table-wrap">
          <StockTable stocks={filtered} onSelect={handleSelect} selectedSymbol={selected} sortBy={sortBy} sortDir={sortDir} onSort={(k,dir)=>{setSortBy(k); setSortDir(dir)}} />
          {filtered.length===0 && allStocks.length===0 && (
            <div style={{position:'absolute', top:'50%', left:'50%', transform:'translate(-50%,-50%)', textAlign:'center', color:'#5a6b84'}}>
              <div style={{fontSize:14}}>Waiting for market data...</div>
              <div style={{fontSize:11, marginTop:6}}>Backend is in <b>{dataMode}</b> mode • Establishing WebSocket stream</div>
            </div>
          )}
        </div>
        {(selected || showDetail) && (
          <DetailPanel symbol={selected} onClose={()=> {setSelected(null); setShowDetail(false)}} liveState={liveSelectedState} />
        )}
      </div>

      {/* alerts ticker */}
      <div style={{height:32, background:'#0f141a', borderTop:'1px solid #232d38', display:'flex', alignItems:'center', padding:'0 16px', gap:12, overflow:'hidden', flexShrink:0}}>
        <span style={{fontSize:11, color:'#f6c343', fontWeight:700, whiteSpace:'nowrap'}}>● LIVE ALERTS</span>
        <div style={{display:'flex', gap:12, overflow:'hidden', whiteSpace:'nowrap', fontSize:11}}>
          {alerts.length===0 ? <span style={{color:'#5a6b84'}}>No alerts yet — system monitoring breakouts, volume spikes, VWAP crosses, momentum, RSI...</span> :
            alerts.slice(0,8).map(a=>(
              <span key={a.id} style={{color: a.level==='bullish'?'#00d38d': a.level==='bearish'?'#ff4757':'#3b9eff'}}>{a.symbol} {a.type} • {a.message}</span>
            ))
          }
        </div>
        <span style={{marginLeft:'auto', fontSize:10, color:'#5a6b84', whiteSpace:'nowrap'}}>Score = Momentum 25 + Volume 25 + RelVol 20 + Breakout 15 + VWAP 10 + Volatility 5 • NOT investment advice</span>
      </div>
    </div>
  )
}
