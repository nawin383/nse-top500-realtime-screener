import React from 'react'
import { useAnimatedNumber } from '../hooks/useAnimatedNumber.js'

// Renders a live-updating price or percent that tweens between values instead
// of snapping. `format` receives the interpolated number at every animation
// frame, so it must be cheap (a toFixed/toLocaleString call, not a fetch).
export default function TickerValue({ value, format, duration = 450, className, style }) {
  const display = useAnimatedNumber(value, duration)
  if (value == null) return <span className={className} style={style}>—</span>
  return <span className={className} style={style}>{format(display)}</span>
}
