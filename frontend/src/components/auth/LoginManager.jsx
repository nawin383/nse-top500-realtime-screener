import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useAuth } from '../../hooks/useAuth.js'

export default function LoginManager(){
  const { user, isAuthenticated, login, register, logout } = useAuth()
  const [open, setOpen] = useState(false)
  const [mode, setMode] = useState('login')
  const [form, setForm] = useState({username:'', email:'', password:''})
  const [err, setErr] = useState('')
  const [loading, setLoading] = useState(false)

  const submit = async (e)=>{
    e.preventDefault()
    setErr(''); setLoading(true)
    try{
      if(mode==='login') await login({username:form.username, password:form.password})
      else await register(form)
      setOpen(false); setForm({username:'',email:'',password:''})
    }catch(ex){ setErr(ex.message||'Failed') }
    finally{ setLoading(false) }
  }

  if(isAuthenticated){
    return (
      <div style={{display:'flex',gap:8,alignItems:'center'}}>
        <div aria-label={`Logged in as ${user.username}`} title={user.username} style={{display:'flex',gap:8,alignItems:'center', background:'rgba(255,255,255,0.06)', padding:'4px 10px 4px 4px', borderRadius:999, border:'1px solid rgba(255,255,255,0.08)'}}>
          <span style={{width:28,height:28,borderRadius:999, background:'linear-gradient(135deg,#2563eb,#10b981)', display:'grid', placeItems:'center', fontWeight:800, fontSize:11, color:'#001a0c'}}>{user.avatar}</span>
          <span style={{fontSize:12, fontWeight:700, color:'#f1f5f9'}}>{user.username}</span>
        </div>
        <button className="btn sm" onClick={logout} aria-label="Logout">Logout</button>
      </div>
    )
  }
  return (
    <>
      <button className="btn sm active" onClick={()=> setOpen(true)} aria-label="Login" style={{borderRadius:999, fontWeight:800}}>Login</button>
      <AnimatePresence>
        {open && (
          <motion.div initial={{opacity:0}} animate={{opacity:1}} exit={{opacity:0}} onClick={()=> setOpen(false)} style={{position:'fixed', inset:0, background:'rgba(0,0,0,0.55)', backdropFilter:'blur(8px)', zIndex:60, display:'grid', placeItems:'center', padding:16}} aria-modal="true" role="dialog">
            <motion.div initial={{scale:0.96,y:8,opacity:0}} animate={{scale:1,y:0,opacity:1}} exit={{scale:0.96,opacity:0}} onClick={e=>e.stopPropagation()} style={{width:'100%', maxWidth:380, background:'linear-gradient(135deg, rgba(22,35,58,0.98), rgba(13,27,42,0.98))', border:'1px solid rgba(255,255,255,0.08)', borderRadius:18, padding:20, boxShadow:'0 20px 60px rgba(0,0,0,0.5)'}}>
              <div style={{display:'flex',justifyContent:'space-between',alignItems:'center', marginBottom:12}}>
                <h3 style={{fontSize:16,fontWeight:800, color:'#f1f5f9'}}>{mode==='login'?'Welcome back':'Create account'}</h3>
                <button className="btn sm" onClick={()=> setOpen(false)} aria-label="Close login modal">✕</button>
              </div>
              <div style={{display:'flex',gap:6, marginBottom:14}}>
                <button className={`btn sm ${mode==='login'?'active':''}`} onClick={()=> setMode('login')}>Login</button>
                <button className={`btn sm ${mode==='register'?'active':''}`} onClick={()=> setMode('register')}>Register</button>
              </div>
              <form onSubmit={submit} style={{display:'flex',flexDirection:'column',gap:10}}>
                <label style={{fontSize:11, color:'#cbd5e1', fontWeight:700}}>Username
                  <input className="input" aria-label="Username" required value={form.username} onChange={e=> setForm({...form, username:e.target.value})} placeholder="trader2026" style={{width:'100%', marginTop:4}} />
                </label>
                {mode==='register' && <label style={{fontSize:11, color:'#cbd5e1', fontWeight:700}}>Email
                  <input className="input" type="email" aria-label="Email" value={form.email} onChange={e=> setForm({...form,email:e.target.value})} placeholder="you@example.com" style={{width:'100%', marginTop:4}} />
                </label>}
                <label style={{fontSize:11, color:'#cbd5e1', fontWeight:700}}>Password
                  <input className="input" type="password" aria-label="Password" required value={form.password} onChange={e=> setForm({...form,password:e.target.value})} placeholder="••••••••" style={{width:'100%', marginTop:4}} />
                </label>
                {err && <div role="alert" style={{color:'#ef5350', fontSize:12, background:'rgba(239,83,80,0.08)', padding:'6px 10px', borderRadius:8, border:'1px solid rgba(239,83,80,0.2)'}}>{err}</div>}
                <button type="submit" disabled={loading} className="btn active" style={{marginTop:4, borderRadius:10, fontWeight:800}}>{loading?'Please wait…': mode==='login'?'Login':'Create account'}</button>
                <span style={{fontSize:10, color:'#94a3b8', textAlign:'center'}}>JWT mock • persisted to localStorage • backend /api/auth/login if available</span>
              </form>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}

export function RequireAuth({children, fallback}){
  const {isAuthenticated} = useAuth()
  if(!isAuthenticated) return fallback || <div style={{padding:20,color:'#94a3b8'}}>Login required</div>
  return children
}
