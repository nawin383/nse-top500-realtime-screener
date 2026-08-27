import { useEffect, useRef, useState, useCallback } from 'react'

/**
 * Web Speech API placeholder
 * usage: const { listening, transcript, start, stop } = useVoice({ onCommand })
 * Commands: "show gainers" | "filter reliance" | "clear" | "export"
 */
export function useVoice({ onCommand, lang='en-IN' }={}) {
  const [listening, setListening] = useState(false)
  const [transcript, setTranscript] = useState('')
  const [supported, setSupported] = useState(false)
  const recRef = useRef(null)

  useEffect(()=>{
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition
    setSupported(!!SR)
    if(!SR) return
    const rec = new SR()
    rec.continuous = false
    rec.interimResults = false
    rec.lang = lang
    rec.onstart = ()=> setListening(true)
    rec.onend = ()=> setListening(false)
    rec.onresult = (e)=>{
      const t = e.results[0][0].transcript.toLowerCase().trim()
      setTranscript(t)
      if(onCommand){
        if(t.includes('gainer')) onCommand({ action:'screener', value:'gainers' })
        else if(t.includes('loser')) onCommand({ action:'screener', value:'losers' })
        else if(t.includes('volume')) onCommand({ action:'screener', value:'volume' })
        else if(t.includes('breakout')) onCommand({ action:'screener', value:'breakout' })
        else if(t.includes('clear')) onCommand({ action:'clear' })
        else if(t.includes('export')) onCommand({ action:'export' })
        else onCommand({ action:'search', value:t })
      }
    }
    recRef.current = rec
  },[onCommand, lang])

  const start = useCallback(()=> recRef.current?.start(), [])
  const stop = useCallback(()=> recRef.current?.stop(), [])
  return { listening, transcript, supported, start, stop }
}
