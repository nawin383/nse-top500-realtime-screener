import { useCallback } from 'react'
import { useStore, store } from '../store/useStore.js'

export function useWatchlist(){
  const wl=useStore(s=>s.watchlists)
  const activeId=useStore(s=>s.activeWatchlistId)
  const active=wl.find(w=>w.id===activeId) || wl[0]
  const setActive=(id)=> store.setState({activeWatchlistId:id})
  const addList=(name)=> store.addWatchlist(name)
  const removeList=(id)=> store.removeWatchlist(id)
  const rename=(id,name)=> store.renameWatchlist(id,name)
  const addSymbol=useCallback((wlId,sym)=> store.addSymbol(wlId,sym),[])
  const removeSymbol=useCallback((wlId,sym)=> store.removeSymbol(wlId,sym),[])
  const moveSymbol=useCallback((src,dst,sym)=> store.moveSymbol(src,dst,sym),[])
  const setAlert=useCallback((wlId,sym,cfg)=> store.setAlert(wlId,sym,cfg),[])
  const exportJSON=()=>{
    const data=JSON.stringify(wl,null,2)
    const blob=new Blob([data],{type:'application/json'})
    const url=URL.createObjectURL(blob)
    const a=document.createElement('a');a.href=url;a.download='watchlists.json';a.click();URL.revokeObjectURL(url)
  }
  const importJSON=(file)=>{
    return new Promise((res,rej)=>{
      const r=new FileReader()
      r.onload=()=>{
        try{
          const arr=JSON.parse(r.result)
          if(Array.isArray(arr)){ store.setState({watchlists:arr}); res(arr)}
          else rej('invalid')
        }catch(e){rej(e)}
      }
      r.onerror=rej
      r.readAsText(file)
    })
  }
  return {watchlists:wl, active, activeId, setActive, addList, removeList, rename, addSymbol, removeSymbol, moveSymbol, setAlert, exportJSON, importJSON}
}
export default useWatchlist
