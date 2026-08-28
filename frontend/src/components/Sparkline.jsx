import React, { useMemo } from 'react'

// Tiny inline trend line for a row -- no chart library, just a normalized SVG
// polyline. `data` is a rolling buffer of recent prices (oldest first).
export default function Sparkline({ data, width = 56, height = 20, strokeWidth = 1.5 }) {
  const { points, up } = useMemo(() => {
    if (!data || data.length < 2) return { points: '', up: true }
    const min = Math.min(...data)
    const max = Math.max(...data)
    const range = (max - min) || 1
    const step = width / (data.length - 1)
    const pts = data.map((v, i) => {
      const x = i * step
      const y = height - ((v - min) / range) * height
      return `${x.toFixed(1)},${y.toFixed(1)}`
    }).join(' ')
    return { points: pts, up: data[data.length - 1] >= data[0] }
  }, [data, width, height])

  if (!points) return <span style={{ display: 'inline-block', width, height }} aria-hidden="true" />

  const color = up ? 'var(--green)' : 'var(--red)'
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} aria-hidden="true" style={{ display: 'block', overflow: 'visible' }}>
      <polyline points={points} fill="none" stroke={color} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" opacity={0.9} />
    </svg>
  )
}
