import { useEffect, useState } from 'react'

const FILTERS = [
  {k:'All', label:'All'},
  {k:'gainers', label:'Gainers'},
  {k:'losers', label:'Losers'},
  {k:'volume', label:'Volume Spike'},
  {k:'momentum', label:'Momentum'},
  {k:'breakout', label:'Breakout'},
  {k:'breakdown', label:'Breakdown'},
  {k:'vwap_above', label:'Above VWAP'},
  {k:'vwap_below', label:'Below VWAP'},
  {k:'unusual', label:'Unusual'},
]

export function ScreenerControls({onFilterChange, onSearch, onSector, sectors}: any) {
  const [active,setActive]=useState('All')
  const [search,setSearch]=useState('')
  const [sector,setSector]=useState('All')
  useEffect(()=> onSearch(search), [search])
  useEffect(()=> onSector(sector), [sector])
  const handleFilter=(k:string)=>{
    setActive(k)
    onFilterChange(k)
  }
  return (
    <div className="flex flex-wrap items-center gap-2 px-2 py-2 bg-[#0f1a24] border-b border-[#1e2a36]">
      <input placeholder="Search symbol/company..." value={search} onChange={e=>setSearch(e.target.value)} className="px-2 py-1 bg-[#0a0e13] border border-[#1e2a36] rounded text-sm w-48 focus:outline-none focus:border-sky-600" />
      <select value={sector} onChange={e=>setSector(e.target.value)} className="px-2 py-1 bg-[#0a0e13] border border-[#1e2a36] rounded text-sm">
        <option value="All">All Sectors</option>
        {sectors.map((s:string)=><option key={s} value={s}>{s}</option>)}
      </select>
      <div className="flex flex-wrap gap-1">
        {FILTERS.map(f=>(
          <button key={f.k} onClick={()=>handleFilter(f.k)} className={`px-2.5 py-1 rounded text-xs font-medium border ${active===f.k?'bg-sky-600 border-sky-500 text-white':'bg-[#1a2330] border-[#1e2a36] text-gray-300 hover:bg-[#223043]'}`}>{f.label}</button>
        ))}
      </div>
    </div>
  )
}
