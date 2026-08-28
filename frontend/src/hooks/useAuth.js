import React, { useSyncExternalStore } from 'react'
import { authStore } from '../store/authStore.js'

export function useAuth(){
  const snap = useSyncExternalStore(authStore.subscribe, authStore.getSnapshot, authStore.getSnapshot)
  return {
    user: snap.user,
    token: snap.token,
    isAuthenticated: !!snap.token,
    login: authStore.login.bind(authStore),
    register: authStore.register.bind(authStore),
    logout: authStore.logout.bind(authStore),
  }
}

export function RequireAuth({ children, fallback }){
  const { isAuthenticated } = useAuth()
  if(!isAuthenticated){
    return fallback || React.createElement('div', {role:'alert', style:{padding:24, textAlign:'center', color:'#94a3b8', background:'rgba(255,255,255,0.04)', border:'1px solid rgba(255,255,255,0.06)', borderRadius:12}}, 'Please log in to view this content.')
  }
  return children
}

export function AuthProvider({ children }){
  return React.createElement(React.Fragment, null, children)
}
export default useAuth
