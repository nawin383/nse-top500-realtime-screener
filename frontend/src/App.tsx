import { useEffect, useState, useMemo, useCallback } from 'react'
import { Header } from './components/Header'
import { MarketOverview } from './components/MarketOverview'
import { ScreenerControls } from './components/ScreenerControls'
import { StockTable } from './components/StockTable'
import { StockDetailPanel } from './components/StockDetailPanel'
import { AlertsPanel } from './components/AlertsPanel'
import { useWebSocket } from './hooks/useWebSocket'
import { StockRow } from './types'
import { api } from './api'

export default function App() {
  const [rows,setRows]=useState<StockRow[]>([])
  const [selected,setSelected]=useState<string|null>(null)
  const [lastUpdate,setLastUpdate]=useState('')
  const [filter,setFilter]=useState('All')
  const [search,setSearch]=useState('')
  const [sector,setSector]=useState('All')
  const [screenerSymbols,setScreenerSymbols]=useState<Set<string>|null>(null)
  const [sectors,setSectors]=useState<string[]>([])

  // initial load
  useEffect(()=>{
    api.stocks({limit:500}).then((r:any)=>{
      setRows(r.data||[])
      const secs = Array.from(new Set((r.data||[]).map((x:any)=> x.sector))).filter(Boolean) as string[]
      setSectors(secs)
    }).catch(()=>{})
    const id=setInterval(()=> {
      api.stocks({limit:500}).then((r:any)=> setRows(prev=>{
        // merge but keep ws updates prioritized? just replace if ws not active?
        // For mock, polling fallback
        if(prev.length===0) return r.data||[]
        return prev
      })).catch(()=>{})
    }, 10000)
    return ()=> clearInterval(id)
  },[])

  // screener filter effect
  useEffect(()=>{
    if(filter==='All'){
      setScreenerSymbols(null)
      return
    }
    api.screener(filter, 500).then((r:any)=>{
      const set = new Set<string>((r.data||[]).map((x:any)=> x.symbol))
      setScreenerSymbols(set)
    }).catch(()=> setScreenerSymbols(null))
  },[filter])

  const handleMessage = useCallback((msg:any)=>{
    if(msg.type==='ticks' && Array.isArray(msg.data)){
      setLastUpdate(new Date().toLocaleTimeString())
      // incremental update: merge into rows
      setRows(prev=>{
        if(prev.length===0) return msg.data
        const map = new Map(prev.map(p=>[p.symbol,p]))
        for(const upd of msg.data){
          const existing = map.get(upd.symbol)
          if(existing){
            map.set(upd.symbol, {...existing, ...upd})
          } else {
            map.set(upd.symbol, upd)
          }
        }
        return Array.from(map.values())
      })
    } else if(msg.type==='snapshot'){
      if(Array.isArray(msg.data) && msg.data.length>0){
        setLastUpdate(new Date().toLocaleTimeString())
        setRows(prev=>{
          if(prev.length===0) return msg.data
          // snapshot merges
          const map = new Map(prev.map(p=>[p.symbol,p]))
          for(const s of msg.data) map.set(s.symbol, {...map.get(s.symbol), ...s})
          return Array.from(map.values())
        })
      }
    }
  },[])

  const { status: wsStatus } = useWebSocket('/ws', handleMessage)

  const filteredRows = useMemo(()=>{
    let r = rows
    if(screenerSymbols) r = r.filter(x=> screenerSymbols.has(x.symbol))
    if(search){
      const s = search.toLowerCase()
      r = r.filter(x=> x.symbol.toLowerCase().includes(s) || (x.company||'').toLowerCase().includes(s))
    }
    if(sector!=='All') r = r.filter(x=> x.sector===sector)
    return r
  },[rows, screenerSymbols, search, sector])

  return (
    <div className="min-h-screen flex flex-col bg-[#0a0e13] text-white">
      <Header wsStatus={wsStatus} lastUpdate={lastUpdate} />
      <MarketOverview />
      <ScreenerControls onFilterChange={setFilter} onSearch={setSearch} onSector={setSector} sectors={sectors} />
      <div className="flex flex-1 overflow-hidden">
        <div className="flex-1 flex flex-col min-w-0">
          <div className="px-2 py-1 text-xs text-gray-400 flex justify-between">
            <span>TOP 500 • {filteredRows.length} shown • Throttled rendering (250ms batch) • Virtual scroll ready</span>
            <span className="hidden md:inline text-gray-500">Tip: click header to sort • click row for chart • data is {wsStatus==='open' ? 'live' : 'polling fallback'}</span>
          </div>
          <StockTable rows={filteredRows} onSelect={(s)=>setSelected(s.symbol)} selected={selected||undefined} />
          <AlertsPanel />
        </div>
        {selected ? (
          <StockDetailPanel symbol={selected} onClose={()=>setSelected(null)} />
        ) : (
          <div className="hidden lg:flex w-[420px] border-l border-[#1e2a36] bg-[#0f1a24] items-center justify-center text-gray-500 text-sm p-6">
            Select a stock for intraday chart (VWAP, EMA9/20, RSI, volume, candle)
          </div>
        )}
      </div>
      <footer className="px-4 py-1 text-[10px] text-gray-500 bg-[#0f1a24] border-t border-[#1e2a36] flex justify-between">
        <span>Analytical score 0-100 • NOT investment advice • Stale detection: 30s • IST (Asia/Kolkata) • NSE Top 500 Universe configurable via config/nse_top500.json</span>
        <span>Backend: FastAPI + WebSocket • Frontend: React Vite • Data: Kite WebSocket (mock/live/replay)</span>
      </footer>
    </div>
  )
}
