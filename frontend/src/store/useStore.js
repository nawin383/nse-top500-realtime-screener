import { useSyncExternalStore, useCallback } from 'react'

const LS_KEY='nse_store_v2'
const defWatchlists=[
  {id:'default',name:'Default',symbols:[],alerts:{}},
  {id:'breakouts',name:'Breakouts',symbols:[],alerts:{}},
]

function load(){
  try{
    const raw=localStorage.getItem(LS_KEY)
    if(raw) return JSON.parse(raw)
  }catch{}
  return null
}
const persisted=load()
const initial={
  theme: persisted?.theme || (typeof window!=='undefined' && window.matchMedia('(prefers-color-scheme:light)').matches ? 'light':'dark'),
  watchlists: persisted?.watchlists || defWatchlists,
  activeWatchlistId: persisted?.activeWatchlistId || 'default',
  workspaces: persisted?.workspaces || [{id:'main',name:'Main',layout:'default'}],
  activeWorkspaceId: persisted?.activeWorkspaceId || 'main',
}

let state=initial
const listeners=new Set()
function emit(){ listeners.forEach(l=>l()); persist() }
function persist(){
  try{ localStorage.setItem(LS_KEY, JSON.stringify({theme:state.theme,watchlists:state.watchlists,activeWatchlistId:state.activeWatchlistId,workspaces:state.workspaces,activeWorkspaceId:state.activeWorkspaceId})) }catch{}
  if(typeof document!=='undefined') document.documentElement.setAttribute('data-theme',state.theme)
}
if(typeof document!=='undefined') document.documentElement.setAttribute('data-theme',state.theme)

export const store={
  getState:()=>state,
  setState(patch){
    state={...state,...(typeof patch==='function'?patch(state):patch)}
    emit()
  },
  subscribe(cb){ listeners.add(cb); return ()=>listeners.delete(cb) },
  getSnapshot:()=>state,
  // watchlist actions
  addWatchlist(name){
    const id=name.toLowerCase().replace(/\W+/g,'-')+'-'+Date.now().toString(36)
    store.setState(s=>({watchlists:[...s.watchlists,{id,name,symbols:[],alerts:{}}],activeWatchlistId:id}))
  },
  removeWatchlist(id){
    if(id==='default') return
    store.setState(s=>({watchlists:s.watchlists.filter(w=>w.id!==id),activeWatchlistId: s.activeWatchlistId===id?'default':s.activeWatchlistId}))
  },
  renameWatchlist(id,name){ store.setState(s=>({watchlists:s.watchlists.map(w=>w.id===id?{...w,name}:w)})) },
  addSymbol(wlId,symbol){
    store.setState(s=>({watchlists:s.watchlists.map(w=>w.id===wlId && !w.symbols.includes(symbol)?{...w,symbols:[...w.symbols,symbol]}:w)}))
  },
  removeSymbol(wlId,symbol){
    store.setState(s=>({watchlists:s.watchlists.map(w=>w.id===wlId?{...w,symbols:w.symbols.filter(x=>x!==symbol)}:w)}))
  },
  moveSymbol(srcId,dstId,symbol){
    store.setState(s=>({watchlists:s.watchlists.map(w=>{
      if(w.id===srcId) return {...w,symbols:w.symbols.filter(x=>x!==symbol)}
      if(w.id===dstId && !w.symbols.includes(symbol)) return {...w,symbols:[...w.symbols,symbol]}
      return w
    })}))
  },
  setAlert(wlId,symbol,cfg){
    store.setState(s=>({watchlists:s.watchlists.map(w=>w.id===wlId?{...w,alerts:{...w.alerts,[symbol]:cfg}}:w)}))
  },
  setTheme(t){ store.setState({theme:t}) },
  toggleTheme(){ store.setState(s=>({theme:s.theme==='dark'?'light':'dark'})) },
}

export function useStore(selector=(s)=>s){
  const snap=useSyncExternalStore(store.subscribe, store.getSnapshot, store.getSnapshot)
  return selector ? selector(snap) : snap
}
export function useStoreActions(){ return store }
export default store
