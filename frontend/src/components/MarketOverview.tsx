import { useEffect, useState } from 'react'
import { api } from '../api'

export function MarketOverview() {
  const [data,setData]=useState<any>(null)
  useEffect(()=>{
    const fetch=()=> api.marketOverview().then(setData).catch(()=>{})
    fetch()
    const id=setInterval(fetch, 3000)
    return ()=> clearInterval(id)
  },[])
  if(!data) return <div className="p-2 text-xs text-gray-500">Loading overview...</div>
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-2 px-2 py-2 bg-[#111820] border-b border-[#1e2a36] text-xs">
      <div className="bg-[#0f1a24] p-2 rounded border border-[#1e2a36]"><div className="text-gray-400">Total</div><div className="text-white font-bold text-sm">{data.total}</div></div>
      <div className="bg-[#0f1a24] p-2 rounded border border-[#1e2a36]"><div className="text-gray-400">Adv / Dec</div><div className="font-bold"><span className="text-emerald-400">{data.advancing}</span> / <span className="text-red-400">{data.declining}</span> <span className="text-gray-400">({data.unchanged} flat)</span></div></div>
      <div className="bg-[#0f1a24] p-2 rounded border border-[#1e2a36]"><div className="text-gray-400">Above VWAP</div><div className="text-sky-400 font-bold">{data.above_vwap}</div><div className="text-gray-500">Below {data.below_vwap}</div></div>
      <div className="bg-[#0f1a24] p-2 rounded border border-[#1e2a36]"><div className="text-gray-400">Breakouts</div><div className="text-emerald-400 font-bold">{data.breakouts}</div><div className="text-red-400">{data.breakdowns} breakdowns</div></div>
      <div className="col-span-2 lg:col-span-4 bg-[#0f1a24] p-2 rounded border border-[#1e2a36]">
        <div className="text-gray-400 mb-1">Sector Performance</div>
        <div className="flex flex-wrap gap-1">
          {Object.entries(data.sector_performance||{}).slice(0,6).map(([k,v]:any)=>(
            <span key={k} className={`px-2 py-0.5 rounded text-[11px] ${v.avg_change>=0?'bg-emerald-900 text-emerald-300':'bg-red-900 text-red-300'}`}>{k}: {v.avg_change>0?'+':''}{v.avg_change}%</span>
          ))}
        </div>
      </div>
    </div>
  )
}
