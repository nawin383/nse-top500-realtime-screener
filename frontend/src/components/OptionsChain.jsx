import React, { useEffect, useState } from 'react'

const fmt = (n, d=2) => n==null ? '-' : Number(n).toFixed(d)
const fmtInt = (n) => n==null ? '-' : Number(n).toLocaleString('en-IN')

export default function OptionsChain(){
  const [symbol, setSymbol] = useState('NIFTY')
  const [expiries, setExpiries] = useState([])
  const [expiry, setExpiry] = useState('')
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const [windowSize, setWindowSize] = useState(10)
  const [showGreeks, setShowGreeks] = useState(true)

  const apiBase = import.meta.env.VITE_API_URL || ''

  const fetchExpiries = async (sym)=>{
    try{
      const r = await fetch(`${apiBase}/api/options/expiries?symbol=${sym}`)
      const j = await r.json()
      setExpiries(j.expiries || [])
      if(j.expiries && j.expiries.length && !expiry) setExpiry(j.expiries[0])
    }catch(e){ console.error(e)}
  }
  const fetchChain = async ()=>{
    if(!symbol) return
    setLoading(true)
    try{
      const url = `${apiBase}/api/options/tshape?symbol=${symbol}&window=${windowSize}${expiry?`&expiry=${expiry}`:''}`
      const r = await fetch(url)
      const j = await r.json()
      if(!r.ok) throw new Error(j.detail || 'No data available')
      setData(j)
      setError(null)
      if(j.expiries && j.expiries.length) setExpiries(j.expiries)
    }catch(e){ setError(e.message); setData(null) }
    setLoading(false)
  }

  useEffect(()=>{ fetchExpiries(symbol) }, [symbol])
  useEffect(()=>{ fetchChain() }, [symbol, expiry, windowSize])
  useEffect(()=>{
    const id=setInterval(fetchChain, 10000) // refresh every 10s
    return ()=> clearInterval(id)
  }, [symbol, expiry, windowSize])

  const analytics = data?.analytics

  return (
    <div style={{padding:12, background:'#0a0e13', minHeight:'100%'}}>
      <div style={{display:'flex', gap:12, alignItems:'center', flexWrap:'wrap', marginBottom:12}}>
        <h2 style={{fontSize:16, fontWeight:800}}>Option Chain — T Shape + Greeks</h2>
        <select className="input" value={symbol} onChange={e=> setSymbol(e.target.value)}>
          <option value="NIFTY">NIFTY 50</option>
          <option value="SENSEX">SENSEX</option>
          <option value="BANKNIFTY">BANKNIFTY</option>
        </select>
        <select className="input" value={expiry} onChange={e=> setExpiry(e.target.value)} style={{minWidth:140}}>
          {expiries.map(e=> <option key={e} value={e}>{e}</option>)}
          {!expiries.length && <option>Loading...</option>}
        </select>
        <span style={{fontSize:11, color:'#8b9bb4'}}>Spot <b style={{color:'#e6eef8', fontSize:13}}>{data?.spot ?? '-'}</b> ATM <b style={{color:'#f6c343'}}>{data?.atmStrike ?? '-'}</b> <span style={{fontSize:10, color:'#5a6b84'}}>Src: {data?.source}</span></span>
        <label style={{fontSize:11, color:'#8b9bb4', display:'flex', gap:4, alignItems:'center'}}><input type="checkbox" checked={showGreeks} onChange={e=> setShowGreeks(e.target.checked)} /> Greeks</label>
        <select className="input" value={windowSize} onChange={e=> setWindowSize(Number(e.target.value))}>
          <option value={7}>±7 strikes</option>
          <option value={10}>±10 strikes</option>
          <option value={15}>±15 strikes</option>
        </select>
        <button className="btn sm" onClick={fetchChain}>↻ Refresh</button>
        <span style={{marginLeft:'auto', fontSize:10, color:'#5a6b84'}}>10s auto-refresh • Black-Scholes r=6%</span>
      </div>

      {analytics && (
        <div style={{display:'grid', gridTemplateColumns:'repeat(auto-fit, minmax(160px,1fr))', gap:8, marginBottom:12}}>
          <div style={{background:'#13181e', border:'1px solid #232d38', borderRadius:8, padding:10}}>
            <div style={{fontSize:11, color:'#8b9bb4'}}>PCR (PE/CE OI)</div><div style={{fontSize:18, fontWeight:700, color: analytics.pcr>1?'#00d38d':'#ff4757'}}>{fmt(analytics.pcr,3)}</div>
            <div style={{fontSize:10, color:'#5a6b84'}}>CE OI {fmtInt(analytics.totalCeOi)} | PE OI {fmtInt(analytics.totalPeOi)}</div>
          </div>
          <div style={{background:'#13181e', border:'1px solid #232d38', borderRadius:8, padding:10}}>
            <div style={{fontSize:11, color:'#8b9bb4'}}>Max Pain</div><div style={{fontSize:18, fontWeight:700, color:'#f6c343'}}>{fmtInt(analytics.maxPain)}</div>
            <div style={{fontSize:10, color:'#5a6b84'}}>Spot {fmt(analytics.spot)} ATM {fmtInt(analytics.atmStrike)}</div>
          </div>
          <div style={{background:'#13181e', border:'1px solid #232d38', borderRadius:8, padding:10}}>
            <div style={{fontSize:11, color:'#8b9bb4'}}>ATM Premium (Straddle)</div><div style={{fontSize:16, fontWeight:700}}>CE {fmt(analytics.atmCePremium)} + PE {fmt(analytics.atmPePremium)} = <span style={{color:'#3b9eff'}}>{fmt(analytics.atmStraddle)}</span></div>
            <div style={{fontSize:10, color:'#5a6b84'}}>Break-even ±{fmt(analytics.atmStraddle)} from ATM</div>
          </div>
          <div style={{background:'#13181e', border:'1px solid #232d38', borderRadius:8, padding:10}}>
            <div style={{fontSize:11, color:'#8b9bb4'}}>ATM IV / OI</div><div style={{fontSize:13, fontWeight:600}}>{data?.chain?.find(c=>c.strike===data.atmStrike)?.CE.iv ?? '-'}% IV</div>
            <div style={{fontSize:10, color:'#5a6b84'}}>Call OI {fmtInt(data?.chain?.find(c=>c.strike===data.atmStrike)?.CE.oi)} Put OI {fmtInt(data?.chain?.find(c=>c.strike===data.atmStrike)?.PE.oi)}</div>
          </div>
        </div>
      )}

      {loading && <div style={{color:'#5a6b84', padding:20}}>Loading chain…</div>}
      {!loading && error && <div style={{color:'#8b9bb4', padding:20, textAlign:'center'}}>No data available<div style={{fontSize:11, color:'#5a6b84', marginTop:6}}>{error}</div></div>}

      {data && (
        <div style={{overflow:'auto', border:'1px solid #232d38', borderRadius:8, background:'#0d1218'}}>
          <table style={{width:'100%', fontSize:11, borderCollapse:'collapse'}}>
            <thead style={{position:'sticky', top:0, background:'#0f141a', zIndex:1}}>
              <tr>
                <th colSpan={showGreeks? 9:4} style={{textAlign:'center', color:'#00d38d', borderBottom:'2px solid #00d38d'}}>CALLS (CE)</th>
                <th style={{textAlign:'center', background:'#1a2129', color:'#f6c343'}}>STRIKE</th>
                <th colSpan={showGreeks? 9:4} style={{textAlign:'center', color:'#ff4757', borderBottom:'2px solid #ff4757'}}>PUTS (PE)</th>
              </tr>
              <tr style={{fontSize:10, color:'#8b9bb4'}}>
                {/* CE */}
                <th>OI</th><th>ChgOI</th><th>Vol</th><th>LTP</th>
                {showGreeks && (<><th>IV%</th><th>Δ</th><th>Γ</th><th>θ</th><th>Vega</th></>)}
                <th style={{background:'#1a2129'}}>Price</th>
                {showGreeks && (<><th>Vega</th><th>θ</th><th>Γ</th><th>Δ</th><th>IV%</th></>)}
                <th>LTP</th><th>Vol</th><th>ChgOI</th><th>OI</th>
              </tr>
            </thead>
            <tbody>
              {data.chain.map(row=>{
                const ce=row.CE, pe=row.PE
                const ceOiPct = Math.min(100, (ce.oi/2000000)*100)
                const peOiPct = Math.min(100, (pe.oi/2000000)*100)
                return (
                  <tr key={row.strike} style={{background: row.isATM ? 'rgba(246,195,67,0.12)' : row.strike < data.spot ? 'rgba(0,211,141,0.04)' : 'rgba(255,71,87,0.04)', borderBottom:'1px solid #1a2129'}}>
                    {/* CE */}
                    <td style={{textAlign:'right'}}><div style={{display:'flex', alignItems:'center', gap:4}}><span style={{flex:1}}>{fmtInt(ce.oi)}</span><span style={{width:30, height:4, background:'#1e2a36', display:'inline-block'}}><span style={{display:'block', height:'100%', width:`${ceOiPct}%`, background:'#00d38d'}} /></span></div></td>
                    <td style={{textAlign:'right', color: ce.oiChange>=0?'#00d38d':'#ff4757'}}>{ce.oiChange>0?'+':''}{fmtInt(ce.oiChange)}</td>
                    <td style={{textAlign:'right'}}>{fmtInt(ce.volume)}</td>
                    <td style={{textAlign:'right', fontWeight:700, color: row.isITM_CE?'#00d38d':'#8b9bb4'}}>{fmt(ce.ltp)}</td>
                    {showGreeks && (<>
                      <td style={{textAlign:'right', color:'#f6c343'}}>{fmt(ce.iv,1)}</td>
                      <td style={{textAlign:'right'}}>{fmt(ce.delta,2)}</td>
                      <td style={{textAlign:'right'}}>{fmt(ce.gamma,3)}</td>
                      <td style={{textAlign:'right', color:'#ff4757'}}>{fmt(ce.theta,2)}</td>
                      <td style={{textAlign:'right'}}>{fmt(ce.vega,2)}</td>
                    </>)}
                    <td style={{textAlign:'center', fontWeight:800, background: row.isATM?'#f6c343':'#1a2129', color: row.isATM?'#000':'#e6eef8', borderLeft:'2px solid #f6c343', borderRight:'2px solid #f6c343'}}>{fmtInt(row.strike)}{row.isATM?' ★':''}</td>
                    {showGreeks && (<>
                      <td style={{textAlign:'left'}}>{fmt(pe.vega,2)}</td>
                      <td style={{textAlign:'left', color:'#ff4757'}}>{fmt(pe.theta,2)}</td>
                      <td style={{textAlign:'left'}}>{fmt(pe.gamma,3)}</td>
                      <td style={{textAlign:'left'}}>{fmt(pe.delta,2)}</td>
                      <td style={{textAlign:'left', color:'#f6c343'}}>{fmt(pe.iv,1)}</td>
                    </>)}
                    <td style={{textAlign:'left', fontWeight:700, color: row.isITM_PE?'#00d38d':'#8b9bb4'}}>{fmt(pe.ltp)}</td>
                    <td style={{textAlign:'left'}}>{fmtInt(pe.volume)}</td>
                    <td style={{textAlign:'left', color: pe.oiChange>=0?'#00d38d':'#ff4757'}}>{pe.oiChange>0?'+':''}{fmtInt(pe.oiChange)}</td>
                    <td style={{textAlign:'left'}}><div style={{display:'flex', alignItems:'center', gap:4}}><span style={{width:30, height:4, background:'#1e2a36', display:'inline-block'}}><span style={{display:'block', height:'100%', width:`${peOiPct}%`, background:'#ff4757'}} /></span><span style={{flex:1, textAlign:'right'}}>{fmtInt(pe.oi)}</span></div></td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      <div style={{marginTop:8, fontSize:10, color:'#5a6b84', display:'flex', gap:12, flexWrap:'wrap'}}>
        <span>★ ATM • Green left = ITM CE • Red right = ITM PE • OI bar = open interest • Δ Gamma θ Vega ρ per Black-Scholes (r=6%)</span>
        <span>Source: {data?.source} • {data?.generatedAt ? new Date(data.generatedAt).toLocaleString('en-IN') : ''}</span>
      </div>
    </div>
  )
}
