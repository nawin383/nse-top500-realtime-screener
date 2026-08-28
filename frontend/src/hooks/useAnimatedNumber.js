import { useEffect, useRef, useState } from 'react'

const prefersReducedMotion = () =>
  typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

// Smoothly counts a displayed number from its previous value to the next one
// instead of snapping -- the single most recognizable "premium fintech" tell
// (Robinhood/Coinbase/Bloomberg all tween price changes rather than blit them).
// Respects prefers-reduced-motion by snapping immediately.
export function useAnimatedNumber(value, duration = 450) {
  const [display, setDisplay] = useState(value)
  const fromRef = useRef(value)
  const rafRef = useRef()

  useEffect(() => {
    if (value == null || Number.isNaN(value)) return
    if (prefersReducedMotion()) { setDisplay(value); fromRef.current = value; return }
    const from = fromRef.current ?? value
    const to = value
    if (from === to) return
    const start = performance.now()
    cancelAnimationFrame(rafRef.current)
    const tick = (now) => {
      const t = Math.min(1, (now - start) / duration)
      const eased = 1 - Math.pow(1 - t, 3) // ease-out-cubic
      setDisplay(from + (to - from) * eased)
      if (t < 1) rafRef.current = requestAnimationFrame(tick)
      else fromRef.current = to
    }
    rafRef.current = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(rafRef.current)
  }, [value, duration])

  return display
}
