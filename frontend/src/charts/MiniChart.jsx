import React, { useRef, useEffect, useState } from 'react'

function CanvasChart({ candles, vwap, ema9, ema20, syncKey }){
  const ref=useRef(null)
  useEffect(()=>{
    const canvas=ref.current; if(!canvas||!candles?.length) return
    const ctx=canvas.getContext('2d')
    const dpr=window.devicePixelRatio||1
    const rect=canvas.getBoundingClientRect()
    canvas.width=rect.width*dpr; canvas.height=rect.height*dpr; ctx.scale(dpr,dpr)
    const W=rect.width, H=rect.height
    ctx.clearRect(0,0,W,H); ctx.fillStyle='#0d1218'; ctx.fillRect(0,0,W,H)
    const highs=candles.map(c=>c.high), lows=candles.map(c=>c.low)
    let min=Math.min(...lows), max=Math.max(...highs)
    const pad=(max-min)*0.1; min-=pad; max+=pad; if(min===max){min-=1;max+=1}
    const range=max-min
    const candleW=Math.max(2,(W-20)/candles.length*0.7)
    const gap=(W-20)/candles.length - candleW
    candles.forEach((c,i)=>{
      const x=10+i*(candleW+gap)
      const yH=10+(max-c.high)/range*(H-40), yL=10+(max-c.low)/range*(H-40)
      const yO=10+(max-c.open)/range*(H-40), yC=10+(max-c.close)/range*(H-40)
      const green=c.close>=c.open
      ctx.strokeStyle=green?'#00d38d':'#ff4757'; ctx.lineWidth=1
      ctx.beginPath(); ctx.moveTo(x+candleW/2,yH); ctx.lineTo(x+candleW/2,yL); ctx.stroke()
      ctx.fillStyle=green?'#00d38d':'#ff4757'
      const top=Math.min(yO,yC), h=Math.max(1,Math.abs(yO-yC))
      ctx.fillRect(x,top,candleW,h)
    })
    const drawLine=(val,color,dash)=>{
      if(!val) return
      const y=10+(max-val)/range*(H-40)
      ctx.strokeStyle=color; ctx.lineWidth=1; if(dash) ctx.setLineDash(dash)
      ctx.beginPath(); ctx.moveTo(10,y); ctx.lineTo(W-10,y); ctx.stroke(); ctx.setLineDash([])
    }
    drawLine(vwap,'#f6c343',[3,3]); drawLine(ema9,'#3b9eff'); drawLine(ema20,'#8b5cf6')
    const maxVol=Math.max(...candles.map(c=>c.volume||0))
    if(maxVol>0) candles.forEach((c,i)=>{
      const x=10+i*(candleW+gap); const h=(c.volume/maxVol)*20
      ctx.fillStyle='rgba(139,155,180,0.3)'; ctx.fillRect(x,H-22,candleW,h)
    })
    ctx.strokeStyle='#232d38'; ctx.strokeRect(0.5,0.5,W-1,H-1)
    // crosshair sync via global mouse pos
    if(syncKey && window.__syncX!=null){
      const x=window.__syncX
      ctx.strokeStyle='rgba(255,255,255,0.15)'; ctx.beginPath(); ctx.moveTo(x,0); ctx.lineTo(x,H); ctx.stroke()
    }
  },[candles,vwap,ema9,ema20,syncKey])
  return <canvas ref={ref} style={{width:'100%',height:'100%',display:'block'}} onMouseMove={e=>{
    const rect=e.currentTarget.getBoundingClientRect(); window.__syncX=e.clientX-rect.left; window.dispatchEvent(new CustomEvent('chart-sync'))
  }} />
}

export default function MiniChart({ candles, vwap, ema9, ema20, grid }){
  const [useLW,setUseLW]=useState(false)
  const [lwReady,setLwReady]=useState(false)
  const containerRef=useRef(null)

  useEffect(()=>{
    let mounted=true
    import('lightweight-charts').then(()=>{ if(mounted) setLwReady(true)}).catch(()=>{})
    return ()=>{mounted=false}
  },[])

  const [syncTick,setSyncTick]=useState(0)
  useEffect(()=>{
    const h=()=>setSyncTick(v=>v+1)
    window.addEventListener('chart-sync',h); return ()=>window.removeEventListener('chart-sync',h)
  },[])

  // 2x2 grid layout when grid=true and candles is array of arrays
  if(grid && Array.isArray(candles) && Array.isArray(candles[0])){
    return (
      <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:8,height:'100%'}}>
        {candles.slice(0,4).map((c,i)=>(
          <div key={i} style={{height:180,border:'1px solid var(--border)',borderRadius:8,overflow:'hidden',background:'#0d1218',position:'relative'}}>
            <span style={{position:'absolute',top:6,left:8,fontSize:10,color:'var(--text2)',zIndex:1}}>#{i+1}</span>
            <CanvasChart candles={c} syncKey={syncTick} />
          </div>
        ))}
      </div>
    )
  }

  // Try lightweight-charts if available and toggled
  if(useLW && lwReady && candles?.length){
    return (
      <div style={{height:'100%',display:'flex',flexDirection:'column'}}>
        <div style={{display:'flex',gap:6,padding:4}}>
          <button className="btn sm" onClick={()=>setUseLW(false)} style={{fontSize:10}}>Canvas fallback</button>
          <span style={{fontSize:10,color:'var(--text3)',alignSelf:'center'}}>LW Charts • volume overlay • crosshair sync</span>
        </div>
        <div ref={containerRef} style={{flex:1,position:'relative'}}>
          <LWChart candles={candles} vwap={vwap} />
        </div>
      </div>
    )
  }

  return (
    <div style={{height:'100%',position:'relative'}}>
      {lwReady && <button className="btn sm" onClick={()=>setUseLW(true)} style={{position:'absolute',top:6,right:6,zIndex:2,fontSize:10}}>Try TradingView</button>}
      <CanvasChart candles={candles} vwap={vwap} ema9={ema9} ema20={ema20} syncKey={syncTick} />
      <div style={{position:'absolute',bottom:6,left:8,fontSize:9,color:'var(--text3)',background:'rgba(0,0,0,0.5)',padding:'2px 6px',borderRadius:999}}>Vol overlay • 2x2 grid via grid prop • crosshair sync</div>
    </div>
  )
}

function LWChart({ candles, vwap }){
  const ref=useRef(null)
  const chartRef=useRef(null)
  useEffect(()=>{
    let chart, series
    let alive=true
    import('lightweight-charts').then(({createChart, ColorType})=>{
      if(!alive || !ref.current) return
      chart=createChart(ref.current,{layout:{background:{type:ColorType.Solid,color:'#0d1218'},textColor:'#8ea0b8'},grid:{vertLines:{color:'#1e2e42'},horzLines:{color:'#1e2e42'}},width:ref.current.clientWidth,height:260, crosshair:{mode:1}})
      series=chart.addCandlestickSeries({upColor:'#00d38d',downColor:'#ff4757',borderVisible:false,wickUpColor:'#00d38d',wickDownColor:'#ff4757'})
      const data=candles.map(c=>({time: Math.floor((c.timestamp||Date.now())/1000), open:c.open, high:c.high, low:c.low, close:c.close}))
      series.setData(data)
      if(vwap){
        const line=chart.addLineSeries({color:'#f6c343',lineWidth:1,priceLineVisible:false})
        line.setData(data.map(d=>({time:d.time,value:vwap})))
      }
      const volSeries=chart.addHistogramSeries({priceScaleId:'', priceFormat:{type:'volume'}})
      volSeries.setData(candles.map(c=>({time:Math.floor((c.timestamp||Date.now())/1000), value:c.volume||0, color:'rgba(139,155,180,0.3)'})))
      chart.timeScale().fitContent()
      chartRef.current=chart
      const ro=new ResizeObserver(()=>{ try{ chart.applyOptions({width:ref.current.clientWidth}) }catch{}})
      ro.observe(ref.current)
      return ()=>ro.disconnect()
    })
    return ()=>{ alive=false; try{ chartRef.current?.remove()}catch{} }
  },[candles,vwap])
  return <div ref={ref} style={{width:'100%',height:260}} />
}
