// Real per-unit P&L at expiry for a multi-leg options position, computed
// straight from the same legs (type/strike/premium/qty/side) the backend's
// strategy builder (backend/app/options/strategies.py) already returns for
// each strategy. This is the textbook expiry payoff formula applied across a
// spot range -- not a separate pricing model, so it can only ever agree with
// the backend's own net_premium/max_profit/max_loss figures at the extremes.
export function computePayoffCurve(legs, spot, { points = 61, rangePct = 0.15 } = {}) {
  if (!legs?.length || !spot) return []
  const strikes = legs.map(l => l.strike)
  const lo = Math.min(spot * (1 - rangePct), ...strikes)
  const hi = Math.max(spot * (1 + rangePct), ...strikes)
  const step = (hi - lo) / (points - 1)
  const curve = []
  for (let i = 0; i < points; i++) {
    const price = lo + step * i
    let pnl = 0
    for (const leg of legs) {
      const intrinsic = leg.type === 'CE' ? Math.max(price - leg.strike, 0) : Math.max(leg.strike - price, 0)
      const legPnl = leg.side === 'sell' ? (leg.premium - intrinsic) : (intrinsic - leg.premium)
      pnl += legPnl * (leg.qty || 1)
    }
    curve.push({ price: Math.round(price * 100) / 100, pnl: Math.round(pnl * 100) / 100 })
  }
  return curve
}
