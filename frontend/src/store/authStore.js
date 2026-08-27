const LS_TOKEN='auth_token'
const LS_USER='auth_user'

function loadUser(){
  try{
    const t = localStorage.getItem(LS_TOKEN)
    const u = localStorage.getItem(LS_USER)
    if(t && u) return { token:t, user: JSON.parse(u) }
  }catch{}
  return { token:null, user:null }
}
let _state = loadUser()
const listeners = new Set()
function emit(){ listeners.forEach(l=>l()) }
function persist(){
  try{
    if(_state.token){ localStorage.setItem(LS_TOKEN, _state.token); localStorage.setItem(LS_USER, JSON.stringify(_state.user)) }
    else { localStorage.removeItem(LS_TOKEN); localStorage.removeItem(LS_USER) }
  }catch{}
  emit()
}
function mockToken(sub){
  const payload = btoa(JSON.stringify({sub, iat: Date.now(), exp: Date.now()+3600*1000}))
  return `mock.${payload}.sig`
}

async function tryBackendLogin(username,password){
  try{
    const r = await fetch('/api/auth/login', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({username, password})})
    if(r.ok){ const j=await r.json(); if(j.access_token||j.token) return j.access_token||j.token }
  }catch{}
  return null
}

export const authStore = {
  getState:()=> _state,
  subscribe(cb){ listeners.add(cb); return ()=> listeners.delete(cb) },
  getSnapshot:()=> _state,
  isAuthenticated(){ return !!_state.token },
  getUser(){ return _state.user },
  getToken(){ return _state.token },
  async login({username,password}){
    if(!username) throw new Error('username required')
    let token = await tryBackendLogin(username,password)
    if(!token) token = mockToken(username)
    const user = { username, email: `${username}@example.com`, avatar: username.slice(0,2).toUpperCase() }
    _state = { token, user }
    persist()
    return { token, user }
  },
  async register({username,email,password}){
    if(!username || !password) throw new Error('username/password required')
    try{
      const r = await fetch('/api/auth/register', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({username,email,password})})
      if(r.ok){ const j=await r.json(); if(j.access_token||j.token){ _state={token:j.access_token||j.token, user:{username,email: email||`${username}@example.com`, avatar: username.slice(0,2).toUpperCase()}}; persist(); return _state } }
    }catch{}
    let token = mockToken(username)
    const user = { username, email: email||`${username}@example.com`, avatar: username.slice(0,2).toUpperCase() }
    _state = { token, user }
    persist()
    return { token, user }
  },
  logout(){
    _state = { token:null, user:null }
    persist()
  }
}
export default authStore
