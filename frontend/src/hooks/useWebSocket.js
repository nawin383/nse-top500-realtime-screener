import { useEffect, useRef, useState, useCallback } from 'react'

export function useWebSocket(url, { onMessage, onOpen, onClose } = {}) {
  const wsRef = useRef(null)
  const [status, setStatus] = useState('connecting')
  const [lastUpdate, setLastUpdate] = useState(null)
  const reconnectRef = useRef(0)
  const onMessageRef = useRef(onMessage)

  useEffect(()=>{ onMessageRef.current = onMessage }, [onMessage])

  const connect = useCallback(()=>{
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = location.host
    // fallback to ws://localhost:8000 if dev
    let wsUrl = url
    if(!wsUrl) {
      if(import.meta.env.VITE_WS_URL) wsUrl = import.meta.env.VITE_WS_URL
      else {
        // try current host's backend (if frontend served from backend, same host)
        // during dev, vite proxy expects ws://localhost:5173/ws/stream -> proxied to 8000
        wsUrl = `${proto}//${location.host}/ws/stream`
        // if vite dev and not proxied, fallback
        if(location.port === '5173') wsUrl = 'ws://localhost:8000/ws/stream'
      }
    }
    console.log('[WS] connecting', wsUrl)
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws
    ws.onopen = (e)=>{
      setStatus('open')
      reconnectRef.current = 0
      onOpen && onOpen(e)
      // ping keepalive
      ws._ping = setInterval(()=>{ try{ ws.send(JSON.stringify({a:'ping'}))}catch{} }, 15000)
    }
    ws.onmessage = (ev)=>{
      setLastUpdate(Date.now())
      try{
        const data = JSON.parse(ev.data)
        onMessageRef.current && onMessageRef.current(data)
      }catch(err){ console.warn('ws parse', err) }
    }
    ws.onclose = (e)=>{
      setStatus('closed')
      onClose && onClose(e)
      clearInterval(ws._ping)
      // reconnect with backoff
      const delay = Math.min(1000 * Math.pow(2, reconnectRef.current), 10000)
      reconnectRef.current += 1
      console.log(`[WS] closed, reconnect in ${delay}ms (attempt ${reconnectRef.current})`)
      setTimeout(connect, delay)
    }
    ws.onerror = (e)=>{
      console.error('[WS] error', e)
      try{ ws.close() }catch{}
    }
  }, [url, onOpen, onClose])

  useEffect(()=>{
    connect()
    return ()=>{
      try{ wsRef.current?.close() }catch{}
      clearInterval(wsRef.current?._ping)
    }
  }, [connect])

  const send = useCallback((obj)=>{
    if(wsRef.current && wsRef.current.readyState===1){
      wsRef.current.send(JSON.stringify(obj))
    }
  }, [])

  return { status, lastUpdate, send, ws: wsRef.current }
}
