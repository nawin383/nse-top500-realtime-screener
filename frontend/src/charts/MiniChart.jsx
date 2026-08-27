import React, { useRef, useEffect } from 'react'

export default function MiniChart({ candles, vwap, ema9, ema20 }){
  const canvasRef = useRef(null)
  // candles expected: array of {open,high,low,close,timestamp, volume}
  useEffect(()=>{
    const canvas = canvasRef.current
    if(!canvas || !candles || candles.length===0) return
    const ctx = canvas.getContext('2d')
    const dpr = window.devicePixelRatio || 1
    const rect = canvas.getBoundingClientRect()
    canvas.width = rect.width * dpr
    canvas.height = rect.height * dpr
    ctx.scale(dpr,dpr)
    const W = rect.width, H = rect.height
    ctx.clearRect(0,0,W,H)
    // background
    ctx.fillStyle = '#0d1218'
    ctx.fillRect(0,0,W,H)
    // find min/max
    const highs = candles.map(c=> c.high)
    const lows = candles.map(c=> c.low)
    let min = Math.min(...lows)
    let max = Math.max(...highs)
    const pad = (max-min)*0.1
    min-=pad; max+=pad
    if(min===max){ min-=1; max+=1 }
    const range = max-min
    const candleW = Math.max(2, (W-20) / candles.length * 0.7)
    const gap = (W-20) / candles.length - candleW
    candles.forEach((c,i)=>{
      const x = 10 + i * (candleW+gap)
      const yHigh = 10 + (max - c.high)/range * (H-40)
      const yLow = 10 + (max - c.low)/range * (H-40)
      const yOpen = 10 + (max - c.open)/range * (H-40)
      const yClose = 10 + (max - c.close)/range * (H-40)
      const isGreen = c.close >= c.open
      ctx.strokeStyle = isGreen ? '#00d38d' : '#ff4757'
      ctx.lineWidth = 1
      // wick
      ctx.beginPath()
      ctx.moveTo(x + candleW/2, yHigh)
      ctx.lineTo(x + candleW/2, yLow)
      ctx.stroke()
      // body
      ctx.fillStyle = isGreen ? '#00d38d' : '#ff4757'
      const bodyTop = Math.min(yOpen, yClose)
      const bodyH = Math.max(1, Math.abs(yOpen - yClose))
      ctx.fillRect(x, bodyTop, candleW, bodyH)
    })
    // VWAP line if exists
    if(vwap){
      ctx.strokeStyle = '#f6c343'
      ctx.lineWidth = 1
      ctx.setLineDash([3,3])
      const yVwap = 10 + (max - vwap)/range * (H-40)
      ctx.beginPath()
      ctx.moveTo(10, yVwap)
      ctx.lineTo(W-10, yVwap)
      ctx.stroke()
      ctx.setLineDash([])
      ctx.fillStyle = '#f6c343'
      ctx.font = '10px monospace'
      ctx.fillText(`VWAP ${vwap.toFixed(2)}`, W-80, yVwap-4)
    }
    // EMA lines
    const drawEMA = (value, color) => {
      if(!value) return
      const y = 10 + (max - value)/range * (H-40)
      ctx.strokeStyle = color
      ctx.lineWidth = 1
      ctx.beginPath()
      ctx.moveTo(10, y)
      ctx.lineTo(W-10, y)
      ctx.stroke()
    }
    drawEMA(ema9, '#3b9eff')
    drawEMA(ema20, '#8b5cf6')
    // volume bars at bottom
    const maxVol = Math.max(...candles.map(c=> c.volume||0))
    if(maxVol>0){
      candles.forEach((c,i)=>{
        const x = 10 + i * (candleW+gap)
        const h = (c.volume / maxVol) * 20
        ctx.fillStyle = 'rgba(139,155,180,0.3)'
        ctx.fillRect(x, H-22, candleW, h)
      })
    }
    // border
    ctx.strokeStyle = '#232d38'
    ctx.strokeRect(0.5,0.5,W-1,H-1)
  }, [candles, vwap, ema9, ema20])

  return <canvas ref={canvasRef} style={{width:'100%', height:'100%', display:'block'}} />
}
