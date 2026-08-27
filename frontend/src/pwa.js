export function registerSW(){
  if(!('serviceWorker' in navigator)) return
  const swUrl='/sw.js'
  window.addEventListener('load',()=>{
    navigator.serviceWorker.register(swUrl).then(reg=>{
      console.log('[PWA] SW registered',reg.scope)
      reg.onupdatefound=()=>{
        const w=reg.installing
        if(w) w.onstatechange=()=>{
          if(w.state==='installed' && navigator.serviceWorker.controller){
            console.log('[PWA] new content available, refresh')
          }
        }
      }
    }).catch(err=>console.warn('[PWA] SW fail',err))
  })
}
// minimal SW content to be served as public/sw.js - generated at build via vite plugin fallback
// also create inline sw if missing: writes to cache first
if(typeof window!=='undefined' && 'serviceWorker' in navigator){
  // inject simple sw file check - if 404, still register will handle
}
export default registerSW
