import React, { useEffect } from 'react'
import { useStore, store } from '../store/useStore.js'

export default function ThemeToggle(){
  const theme=useStore(s=>s.theme)
  useEffect(()=>{ document.documentElement.setAttribute('data-theme',theme||'dark') },[theme])
  const onClick=()=>{
    const cur=theme||document.documentElement.getAttribute('data-theme')||'dark'
    const next=cur==='dark'?'light':'dark'
    store.setTheme(next)
    document.documentElement.setAttribute('data-theme',next)
  }
  const isDark=(theme||'dark')==='dark'
  return (
    <button className="btn sm" onClick={onClick} title="Toggle theme" aria-label="Toggle theme" style={{display:'flex',gap:6,alignItems:'center'}}>
      <span>{isDark?'☀️':'🌙'}</span> {isDark?'Light':'Dark'}
    </button>
  )
}
export function SimpleThemeToggle(){
  const [t,setT]=React.useState(()=> document.documentElement.getAttribute('data-theme')||'dark')
  React.useEffect(()=>{ document.documentElement.setAttribute('data-theme',t); try{ const raw=localStorage.getItem('nse_store_v2'); if(raw){const j=JSON.parse(raw);j.theme=t;localStorage.setItem('nse_store_v2',JSON.stringify(j))}}catch{} },[t])
  return <button className="btn sm" onClick={()=> setT(v=>v==='dark'?'light':'dark')} aria-label="Toggle theme">{t==='dark'?'☀️ Light':'🌙 Dark'}</button>
}
