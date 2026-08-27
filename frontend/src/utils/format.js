export const fmt = (n, d=2) => {
  if(n==null || isNaN(n)) return '-'
  return Number(n).toFixed(d)
}
export const fmtPct = (n) => n==null ? '-' : `${n>0?'+':''}${n.toFixed(2)}%`
export const fmtVol = (n) => {
  if(n==null) return '-'
  if(n>=1e7) return (n/1e7).toFixed(1)+'Cr'
  if(n>=1e5) return (n/1e5).toFixed(1)+'L'
  if(n>=1e3) return (n/1e3).toFixed(1)+'k'
  return String(n)
}
export const fmtPrice = (n) => n==null? '-' : n.toLocaleString('en-IN', {minimumFractionDigits:2, maximumFractionDigits:2})
