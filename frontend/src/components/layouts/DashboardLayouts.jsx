import React, { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import GridLayout from 'react-grid-layout'

// bento card wrapper with staggered entrance
export function BentoCard({ children, delay=0, style }){
  return (
    <motion.div initial={{opacity:0, y:12}} animate={{opacity:1, y:0}} transition={{delay: delay*0.05, duration:0.35, ease:[0.16,1,0.3,1]}}
      whileHover={{ y:-2, transition:{duration:0.15} }}
      style={{ background:'linear-gradient(135deg, rgba(22,35,58,0.9), rgba(13,27,42,0.75))', border:'1px solid rgba(255,255,255,0.06)', borderRadius:16, padding:14, backdropFilter:'blur(16px)', boxShadow:'0 8px 24px rgba(0,0,0,0.25)', ...style }}>
      {children}
    </motion.div>
  )
}

export function BentoGrid({ children }){
  const items = React.Children.toArray(children)
  return (
    <div style={{display:'grid', gridTemplateColumns:'repeat(auto-fit, minmax(320px,1fr))', gap:14, gridAutoRows:'minmax(120px, auto)'}}>
      {items.map((c,i)=><BentoCard key={i} delay={i}>{c}</BentoCard>)}
    </div>
  )
}

export function Split2x2({ children }){
  const items = React.Children.toArray(children).slice(0,4)
  return <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gridTemplateRows:'1fr 1fr', gap:14, minHeight: 520}}>{items.map((c,i)=><BentoCard key={i} delay={i}>{c}</BentoCard>)}</div>
}

export function Split4x({ children }){
  const items = React.Children.toArray(children)
  return <div style={{display:'grid', gridTemplateColumns:'repeat(4,1fr)', gap:12}}>{items.map((c,i)=><BentoCard key={i} delay={i} style={{minHeight:180}}>{c}</BentoCard>)}</div>
}

export function FullWidth({ children }){
  const items = React.Children.toArray(children)
  return <div style={{display:'flex', flexDirection:'column', gap:14}}>{items.map((c,i)=><BentoCard key={i} delay={i}>{c}</BentoCard>)}</div>
}

// drag grid using react-grid-layout
export function DragGrid({ items }){
  const layout = items.map((_,i)=>({i:`${i}`, x: i%2, y: Math.floor(i/2), w:1, h:2}))
  return (
    <GridLayout className="layout" layout={layout} cols={2} rowHeight={140} width={1200} isResizable draggableHandle=".drag-handle" style={{margin:'-8px'}}>
      {items.map((c,i)=>(
        <div key={`${i}`} style={{background:'rgba(22,35,58,0.9)', border:'1px solid rgba(255,255,255,0.06)', borderRadius:16, padding:12}}>
          <div className="drag-handle" style={{fontSize:10,color:'#94a3b8',cursor:'grab',marginBottom:6}}>⋮⋮ drag</div>{c}
        </div>
      ))}
    </GridLayout>
  )
}

export function LayoutSwitcher({ value, onChange }){
  const opts = [
    {k:'bento', label:'Bento'},
    {k:'2x2', label:'2×2'},
    {k:'4x', label:'4×'},
    {k:'full', label:'Full'},
    {k:'drag', label:'Drag'},
  ]
  return (
    <div role="tablist" aria-label="Layout switcher" style={{display:'flex', gap:4, background:'rgba(255,255,255,0.04)', padding:4, borderRadius:999, border:'1px solid rgba(255,255,255,0.06)'}}>
      {opts.map(o=>(
        <button key={o.k} role="tab" aria-selected={value===o.k} className={`btn sm ${value===o.k?'active':''}`} onClick={()=> onChange(o.k)} style={{borderRadius:999, fontSize:11, fontWeight:800}}>{o.label}</button>
      ))}
    </div>
  )
}

export function DashboardLayouts({ layout='bento', children }){
  const [cur, setCur] = useState(()=>{
    try{ return localStorage.getItem('dashboard_layout') || layout }catch{ return layout }
  })
  useEffect(()=>{ try{ localStorage.setItem('dashboard_layout', cur) }catch{} },[cur])
  const val = layout || cur
  const items = React.Children.toArray(children)
  if(val==='2x2') return <Split2x2>{items}</Split2x2>
  if(val==='4x') return <Split4x>{items}</Split4x>
  if(val==='full') return <FullWidth>{items}</FullWidth>
  if(val==='drag') return <DragGrid items={items} />
  return <BentoGrid>{items}</BentoGrid>
}

export default DashboardLayouts
