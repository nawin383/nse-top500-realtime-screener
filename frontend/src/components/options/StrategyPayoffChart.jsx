import React, { useMemo } from 'react'
import { ComposedChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine, ResponsiveContainer } from 'recharts'
import { computePayoffCurve } from './payoff.js'
import { fmt, fmtInt } from './shared.jsx'

export default function StrategyPayoffChart({ legs, spot, breakevens, axisColor, gridColor, tooltipStyle }) {
  const curve = useMemo(() => computePayoffCurve(legs, spot).map(p => ({
    ...p, gain: p.pnl > 0 ? p.pnl : 0, loss: p.pnl < 0 ? p.pnl : 0,
  })), [legs, spot])

  if (!curve.length) return null

  return (
    <ResponsiveContainer width="100%" height={220} minWidth={260}>
      <ComposedChart data={curve} margin={{ top: 8, right: 20, bottom: 4, left: 0 }}>
        <CartesianGrid stroke={gridColor} strokeDasharray="3 3" />
        <XAxis dataKey="price" tick={{ fill: axisColor, fontSize: 10 }} stroke={gridColor} tickFormatter={fmtInt} />
        <YAxis tick={{ fill: axisColor, fontSize: 10 }} stroke={gridColor} tickFormatter={fmtInt} />
        <Tooltip contentStyle={tooltipStyle}
          formatter={(v, name) => (name === 'gain' || name === 'loss') ? [fmt(v), 'P&L at expiry'] : [v, name]}
          labelFormatter={(v) => `Spot ${fmtInt(v)}`} />
        <ReferenceLine y={0} stroke={axisColor} />
        {spot != null && (
          <ReferenceLine x={spot} stroke="#64b5f6" strokeDasharray="4 4"
            label={{ value: 'Spot', position: 'top', fill: '#64b5f6', fontSize: 10 }} />
        )}
        {(breakevens || []).map((be, i) => (
          <ReferenceLine key={i} x={be} stroke="#f59e0b" strokeDasharray="2 2"
            label={{ value: `BE ${fmtInt(be)}`, position: i === 0 ? 'insideBottomLeft' : 'insideBottomRight', fill: '#f59e0b', fontSize: 9 }} />
        ))}
        <Area type="monotone" dataKey="gain" name="gain" stroke="#10b981" fill="#10b981" fillOpacity={0.25} isAnimationActive={false} />
        <Area type="monotone" dataKey="loss" name="loss" stroke="#ef5350" fill="#ef5350" fillOpacity={0.25} isAnimationActive={false} />
      </ComposedChart>
    </ResponsiveContainer>
  )
}
