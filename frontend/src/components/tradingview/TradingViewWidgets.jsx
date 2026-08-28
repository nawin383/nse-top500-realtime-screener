import React, { useEffect, useRef } from 'react'

function useTradingView(containerRef, src, config){
  useEffect(()=>{
    const el = containerRef.current
    if(!el) return
    el.innerHTML = ''
    const outer = document.createElement('div')
    outer.className = 'tradingview-widget-container'
    outer.style.height = '100%'
    outer.style.width = '100%'
    const widget = document.createElement('div')
    widget.className = 'tradingview-widget-container__widget'
    widget.style.height = '100%'
    widget.style.width = '100%'
    const s = document.createElement('script')
    s.type = 'text/javascript'
    s.async = true
    s.src = src
    s.innerHTML = JSON.stringify(config)
    outer.appendChild(widget)
    outer.appendChild(s)
    el.appendChild(outer)
    return ()=>{ if(el) el.innerHTML='' }
  },[src, JSON.stringify(config)])
}

function TVWrap({src, config, height=400, style, className, title}){
  const ref = useRef(null)
  useTradingView(ref, src, config)
  return <div ref={ref} style={{height, width:'100%', ...style}} className={className} aria-label={title} role="region" />
}

export function TickerTape({ symbols, colorTheme='dark' }){
  const syms = symbols || [
    { proName: 'NSE:NIFTY', title:'NIFTY 50' },
    { proName: 'BSE:SENSEX', title:'SENSEX' },
    { proName: 'NSE:BANKNIFTY', title:'BANKNIFTY' },
    { proName: 'NSE:RELIANCE', title:'RELIANCE' },
    { proName: 'NSE:TCS', title:'TCS' },
    { proName: 'NSE:INFY', title:'INFY' },
    { proName: 'NSE:HDFCBANK', title:'HDFCBANK' },
    { proName: 'NSE:ICICIBANK', title:'ICICIBANK' },
  ]
  return <TVWrap title="Ticker Tape" height={46} src="https://s3.tradingview.com/external-embedding/embed-widget-ticker-tape.js" config={{
    symbols: syms, showSymbolLogo:true, colorTheme: colorTheme==='light'?'light':'dark', isTransparent:false, displayMode:'adaptive', locale:'en'
  }} />
}

export function AdvancedChart({ symbol='NSE:RELIANCE', theme='dark', interval='D', height=420 }){
  const tvSym = symbol.includes(':') ? symbol : `NSE:${symbol}`
  const colorTheme = theme==='light' ? 'light':'dark'
  return <TVWrap title={`Advanced Chart ${tvSym}`} height={height} src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js" config={{
    allow_symbol_change:true, calendar:false, details:false, hide_side_toolbar:false, hide_top_toolbar:false,
    hide_legend:false, hide_volume:false, hotlist:false, interval, locale:'en', save_image:true,
    style:'1', symbol: tvSym, theme: colorTheme, timezone:'Asia/Kolkata', backgroundColor: colorTheme==='dark'?'#0f141c':'#ffffff',
    gridColor: colorTheme==='dark'?'rgba(255,255,255,0.06)':'rgba(0,0,0,0.06)', withdateranges:true, autosize:true
  }} style={{minHeight: height}} />
}

export function MarketOverviewTV({ theme='dark', height=400 }){
  const ct = theme==='light'?'light':'dark'
  return <TVWrap title="Market Overview" height={height} src="https://s3.tradingview.com/external-embedding/embed-widget-market-overview.js" config={{
    colorTheme: ct, dateRange:'12M', showChart:true, locale:'en', largeChartUrl:'', isTransparent:false, showSymbolLogo:true, showFloatingTooltip:false,
    width:'100%', height: height, plotLineColorGrowing:'rgba(0,230,160,1)', plotLineColorFalling:'rgba(255,59,74,1)', gridLineColor:'rgba(255,255,255,0.06)',
    scaleFontColor: ct==='dark'?'rgba(142,160,184,1)':'rgba(71,85,105,1)', belowLineFillColorGrowing:'rgba(0,230,160,0.12)', belowLineFillColorFalling:'rgba(255,59,74,0.12)',
    tabs:[
      { title:'Indices', symbols:[{s:'BSE:SENSEX',d:'Sensex'},{s:'NSE:NIFTY',d:'Nifty 50'},{s:'NSE:BANKNIFTY',d:'Bank Nifty'}], originalTitle:'Indices' },
      { title:'Futures', symbols:[{s:'NSE:RELIANCE',d:'RELIANCE'},{s:'NSE:TCS',d:'TCS'}], originalTitle:'Futures' },
    ]
  }} />
}

export function ScreenerTV({ theme='dark', height=420 }){
  const ct = theme==='light'?'light':'dark'
  return <TVWrap title="Screener" height={height} src="https://s3.tradingview.com/external-embedding/embed-widget-screener.js" config={{
    width:'100%', height, defaultColumn:'overview', defaultScreen:'general', market:'india', showToolbar:true, colorTheme: ct, locale:'en', isTransparent:false
  }} />
}

export function EconomicCalendar({ theme='dark', height=400 }){
  const ct = theme==='light'?'light':'dark'
  return <TVWrap title="Economic Calendar" height={height} src="https://s3.tradingview.com/external-embedding/embed-widget-events.js" config={{
    width:'100%', height, colorTheme: ct, isTransparent:false, locale:'en', importanceFilter:'-1,0,1', currencyFilter:'INR,USD'
  }} />
}

export function TechnicalAnalysis({ symbol='NSE:RELIANCE', theme='dark', height=425, interval='1D' }){
  const tvSym = symbol.includes(':') ? symbol : `NSE:${symbol}`
  const ct = theme==='light'?'light':'dark'
  return <TVWrap title={`Technical Analysis ${tvSym}`} height={height} src="https://s3.tradingview.com/external-embedding/embed-widget-technical-analysis.js" config={{
    interval, width:'100%', isTransparent:false, height, symbol: tvSym, showIntervalTabs:true, displayMode:'single', locale:'en', colorTheme: ct
  }} />
}

export function SymbolInfo({ symbol='NSE:RELIANCE', theme='dark', height=180 }){
  const tvSym = symbol.includes(':') ? symbol : `NSE:${symbol}`
  const ct = theme==='light'?'light':'dark'
  return <TVWrap title={`Symbol Info ${tvSym}`} height={height} src="https://s3.tradingview.com/external-embedding/embed-widget-symbol-info.js" config={{
    symbol: tvSym, width:'100%', locale:'en', colorTheme: ct, isTransparent:false
  }} />
}

export function Heatmap({ theme='dark', height=400, dataSource='SPX500' }){
  const ct = theme==='light'?'light':'dark'
  return <TVWrap title="Heatmap" height={height} src="https://s3.tradingview.com/external-embedding/embed-widget-stock-heatmap.js" config={{
    exchanges:[], dataSource, grouping:'no_group', blockSize:'market_cap_basic', blockColor:'change', locale:'en', symbolUrl:'', colorTheme: ct, hasTopBar:true, isDataSetEnabled:false, isZoomEnabled:true, hasSymbolTooltip:true, width:'100%', height
  }} />
}

export function LazyTV({ children, fallback }){
  const [vis, setVis] = React.useState(false)
  const ref = React.useRef(null)
  useEffect(()=>{
    const el = ref.current
    if(!el) return
    const io = new IntersectionObserver(([e])=>{ if(e.isIntersecting){ setVis(true); io.disconnect() } }, {rootMargin:'200px'})
    io.observe(el)
    return ()=> io.disconnect()
  },[])
  return <div ref={ref}>{vis ? children : (fallback || <div style={{height:120, display:'grid', placeItems:'center', color:'#5b728c', background:'rgba(255,255,255,0.03)', borderRadius:12, border:'1px solid rgba(255,255,255,0.06)'}}>Loading widget…</div>)}</div>
}

export default { TickerTape, AdvancedChart, MarketOverviewTV, ScreenerTV, EconomicCalendar, Heatmap, TechnicalAnalysis, SymbolInfo }
