import { useEffect, useState } from 'react'
import { api } from '../api'
import { Alert } from '../types'

export function AlertsPanel() {
  const [alerts,setAlerts]=useState<Alert[]>([])
  const [filter,setFilter]=useState('')
  useEffect(()=>{
    const fetch=()=> api.alerts(50).then((r:any)=> setAlerts(r.data||[])).catch(()=>{})
    fetch()
    const id=setInterval(fetch, 3000)
    return ()=> clearInterval(id)
  },[])
  const filtered = filter ? alerts.filter(a=> a.type===filter) : alerts
  return (
    <div className="p-2 bg-[#111820] border-t border-[#1e2a36]">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-semibold text-gray-300">Live Alerts ({alerts.length})</span>
        <select value={filter} onChange={e=>setFilter(e.target.value)} className="text-xs bg-[#0a0e13] border border-[#1e2a36] rounded px-1 py-0.5">
          <option value="">All types</option>
          <option value="breakout">Breakout</option>
          <option value="breakdown">Breakdown</option>
          <option value="volume_spike">Volume Spike</option>
          <option value="vwap_cross">VWAP Cross</option>
          <option value="rsi_threshold">RSI</option>
        </select>
      </div>
      <div className="max-h-40 overflow-auto space-y-1">
        {filtered.slice(0,20).map(a=>(
          <div key={a.id} className="flex items-center gap-2 text-xs bg-[#0a0e13] border border-[#1e2a36] rounded px-2 py-1">
            <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${badgeColor(a.type)}`}>{a.type}</span>
            <span className="font-mono font-semibold">{a.symbol}</span>
            <span className="text-gray-400 truncate flex-1">{a.message}</span>
            <span className="text-gray-500 text-[10px]">{new Date(a.timestamp).toLocaleTimeString()}</span>
          </div>
        ))}
        {filtered.length===0 && <div className="text-xs text-gray-500 text-center py-2">No alerts yet. Alerts have cooldown to avoid spam.</div>}
      </div>
    </div>
  )
}
function badgeColor(t:string){
  if(t==='breakout') return 'bg-emerald-700 text-white'
  if(t==='breakdown') return 'bg-red-700 text-white'
  if(t==='volume_spike') return 'bg-yellow-600 text-black'
  if(t==='vwap_cross') return 'bg-sky-700 text-white'
  return 'bg-gray-700 text-gray-200'
}
