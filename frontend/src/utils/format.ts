export const fmt = (n?:number|null, d=2) => n==null || isNaN(n) ? '-' : Number(n).toFixed(d)
export const fmtInt = (n?:number|null) => n==null ? '-' : Number(n).toLocaleString('en-IN')
export const fmtPct = (n?:number|null) => n==null ? '-' : `${n>0?'+':''}${n.toFixed(2)}%`
export const colorPct = (n?:number|null) => n==null ? 'text-gray-400' : n>0 ? 'text-emerald-400' : n<0 ? 'text-red-400' : 'text-gray-300'
export const freshnessColor = (f:string) => {
  if (f==='LIVE') return 'bg-emerald-500'
  if (f==='DELAYED') return 'bg-yellow-500'
  if (f==='STALE') return 'bg-red-500'
  return 'bg-gray-600'
}
