// Web Worker stub for indicator calculations off main thread
self.onmessage = (e)=>{
  const { id, type, payload } = e.data || {}
  try{
    let result=null
    if(type==='rsi'){
      const {closes,period=14}=payload||{}
      result=calcRSI(closes,period)
    } else if(type==='ema'){
      const {closes,period=9}=payload||{}
      result=calcEMA(closes,period)
    } else if(type==='vwap'){
      const {candles}=payload||{}
      result=calcVWAP(candles)
    } else if(type==='sma'){
      const {closes,period=20}=payload||{}
      result=calcSMA(closes,period)
    } else {
      result={error:'unknown type '+type}
    }
    self.postMessage({id,type,result})
  }catch(err){
    self.postMessage({id,type,error:err.message})
  }
}

function calcRSI(closes,period){
  if(!closes||closes.length<period+1) return null
  let gains=0,losses=0
  for(let i=1;i<=period;i++){
    const d=closes[i]-closes[i-1]
    if(d>=0) gains+=d; else losses-=d
  }
  let avgGain=gains/period, avgLoss=losses/period
  for(let i=period+1;i<closes.length;i++){
    const d=closes[i]-closes[i-1]
    if(d>=0){ avgGain=(avgGain*(period-1)+d)/period; avgLoss=(avgLoss*(period-1))/period }
    else { avgGain=(avgGain*(period-1))/period; avgLoss=(avgLoss*(period-1)-d)/period }
  }
  if(avgLoss===0) return 100
  const rs=avgGain/avgLoss
  return 100 - (100/(1+rs))
}
function calcEMA(closes,period){
  if(!closes||!closes.length) return null
  const k=2/(period+1)
  let ema=closes[0]
  for(let i=1;i<closes.length;i++) ema=closes[i]*k + ema*(1-k)
  return ema
}
function calcSMA(closes,period){
  if(!closes||closes.length<period) return null
  const slice=closes.slice(-period)
  return slice.reduce((a,b)=>a+b,0)/period
}
function calcVWAP(candles){
  if(!candles||!candles.length) return null
  let cumPV=0,cumV=0
  for(const c of candles){
    const tp=(c.high+c.low+c.close)/3
    cumPV+=tp*(c.volume||0); cumV+=c.volume||0
  }
  return cumV? cumPV/cumV : null
}
