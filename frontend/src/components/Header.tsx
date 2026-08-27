import { useEffect, useState } from 'react'
import { api } from '../api'
import { MarketStatus } from '../types'

export function Header({ wsStatus, lastUpdate }: { wsStatus:string, lastUpdate:string }) {
  const [status, setStatus] = useState<MarketStatus | null>(null)
  const [mode, setMode] = useState('')
  useEffect(()=>{
    api.marketStatus().then(setStatus).catch(()=>{})
    api.config().then((c:any)=> setMode(c.data_mode || c.dataMode || '')).catch(()=>{})
    const id=setInterval(()=> api.marketStatus().then(setStatus).catch(()=>{}), 5000)
    return ()=> clearInterval(id)
  },[])
  const isLive = status?.is_live
  return (
    <div className="flex items-center justify-between px-4 py-2 bg-[#0f1a24] border-b border-[#1e2a36] text-sm">
      <div className="flex items-center gap-4">
        <span className="font-bold tracking-widest text-white">NSE LIVE</span>
        <span className={`px-2 py-0.5 rounded text-xs font-semibold ${isLive?'bg-emerald-500 text-black':'bg-gray-600 text-white'}`}>{status?.label || '...'}</span>
        <span className="text-gray-400 hidden md:inline">Market: {status?.status || '-'}</span>
        <span className={`hidden md:inline px-2 py-0.5 rounded text-xs ${mode==='mock'?'bg-yellow-600': mode==='live'?'bg-emerald-600':'bg-gray-700'}`}>{mode ? mode.toUpperCase() : ''} {mode==='mock' ? 'MOCK DATA' : mode==='live' ? 'LIVE' : ''}</span>
      </div>
      <div className="flex items-center gap-4 text-xs text-gray-300">
        <span className={`w-2 h-2 rounded-full ${wsStatus==='open'?'bg-emerald-500':'bg-red-500 animate-pulse'}`} />
        <span>WS: {wsStatus}</span>
        <span className="hidden sm:inline">Last: {lastUpdate || '-'}</span>
        <span className="hidden sm:inline text-gray-500">{status?.server_time_ist ? new Date(status.server_time_ist).toLocaleTimeString('en-IN',{timeZone:'Asia/Kolkata'}) : ''} IST</span>
      </div>
    </div>
  )
}
