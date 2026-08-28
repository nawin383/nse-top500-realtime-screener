import React, { useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import ThemeToggle from './ThemeToggle.jsx'
import AccentPicker from './AccentPicker.jsx'
import LoginManager from './auth/LoginManager.jsx'
import { IconGear } from './icons.jsx'

// Theme, accent, and account live behind one gear icon instead of three
// permanent header widgets -- they're preferences you set once and forget,
// not something that earns a permanent slice of the header on every screen.
export default function SettingsMenu(){
  const [open, setOpen] = useState(false)
  const ref = useRef(null)
  useEffect(()=>{
    const onDoc=(e)=>{ if(ref.current && !ref.current.contains(e.target)) setOpen(false) }
    document.addEventListener('mousedown', onDoc)
    return ()=> document.removeEventListener('mousedown', onDoc)
  },[])
  return (
    <div ref={ref} style={{position:'relative'}}>
      <button aria-haspopup="menu" aria-expanded={open} aria-label="Settings" onClick={()=> setOpen(v=>!v)}
        style={{display:'flex', alignItems:'center', justifyContent:'center', width:32, height:32, borderRadius:8, border:'1px solid var(--border)', cursor:'pointer', background: open?'rgba(var(--accent-rgb),0.14)':'rgba(255,255,255,0.04)', color:'var(--text2)'}}>
        <IconGear width={16} height={16}/>
      </button>
      <AnimatePresence>
        {open && (
          <motion.div role="menu" initial={{opacity:0,y:-6,scale:0.98}} animate={{opacity:1,y:0,scale:1}} exit={{opacity:0,y:-6,scale:0.98}} transition={{duration:0.14}}
            style={{position:'absolute', top:'calc(100% + 8px)', right:0, minWidth:230, background:'var(--bg2)', border:'1px solid var(--border)', borderRadius:12, boxShadow:'var(--shadow-xl)', overflow:'hidden', zIndex:80, padding:12, display:'flex', flexDirection:'column', gap:12}}>
            <div style={{display:'flex', flexDirection:'column', gap:6}}>
              <span style={{fontSize:10, fontWeight:800, letterSpacing:'0.08em', textTransform:'uppercase', color:'var(--text3)'}}>Theme</span>
              <ThemeToggle />
            </div>
            <div style={{display:'flex', flexDirection:'column', gap:6}}>
              <span style={{fontSize:10, fontWeight:800, letterSpacing:'0.08em', textTransform:'uppercase', color:'var(--text3)'}}>Accent</span>
              <AccentPicker />
            </div>
            <div style={{display:'flex', flexDirection:'column', gap:6, borderTop:'1px solid var(--border)', paddingTop:10}}>
              <span style={{fontSize:10, fontWeight:800, letterSpacing:'0.08em', textTransform:'uppercase', color:'var(--text3)'}}>Account</span>
              <LoginManager />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
