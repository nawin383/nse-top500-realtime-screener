import { useEffect, useRef, useState, useCallback } from 'react'

interface WSOptions {
  url: string
  onMessage: (msg:any)=>void
}

export function useWebSocket(url: string, onMessage: (msg:any)=>void) {
  const [status, setStatus] = useState<'connecting'|'open'|'closed'|'error'>('connecting')
  const wsRef = useRef<WebSocket|null>(null)
  const reconnectRef = useRef<number>(0)
  const onMessageRef = useRef(onMessage)
  onMessageRef.current = onMessage

  const connect = useCallback(()=>{
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = url.startsWith('ws') ? url : `${proto}//${location.host}${url}`
    // fallback for dev where vite proxy handles ws
    const finalUrl = url === '/ws' ? `${proto}//${location.host}/ws` : wsUrl
    // Actually use relative for ws: new WebSocket will handle proxy via vite; but direct ws to backend is ws://localhost:8000/ws
    // Try ws://localhost:8000/ws then fallback to relative
    let target = url
    if (url === '/ws') {
      // if frontend dev server is vite (5173), we need to connect to backend (8000)
      // location.port 5173 => backend 8000
      if (location.port === '5173') {
        target = `ws://localhost:8000/ws`
      } else {
        target = `${proto}//${location.host}/ws`
      }
    }
    const ws = new WebSocket(target)
    wsRef.current = ws
    ws.onopen = () => { setStatus('open'); reconnectRef.current=0 }
    ws.onclose = () => {
      setStatus('closed')
      if (reconnectRef.current < 10) {
        const delay = Math.min(2000 * Math.pow(1.5, reconnectRef.current), 10000)
        reconnectRef.current++
        setTimeout(connect, delay)
      }
    }
    ws.onerror = () => setStatus('error')
    ws.onmessage = (ev)=>{
      try {
        const data = JSON.parse(ev.data)
        onMessageRef.current(data)
      } catch {}
    }
  }, [url])

  useEffect(()=>{
    connect()
    return ()=> { wsRef.current?.close() }
  }, [connect])

  const send = useCallback((obj:any)=>{
    if (wsRef.current?.readyState===WebSocket.OPEN) wsRef.current.send(JSON.stringify(obj))
  },[])

  return { status, send }
}
