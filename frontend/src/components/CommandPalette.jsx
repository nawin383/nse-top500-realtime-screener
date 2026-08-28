import React, { useEffect, useMemo, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

// Global Ctrl/Cmd+K palette: fuzzy-jump to any nav destination or straight to
// a symbol's detail panel without hunting through the tab bar. Opening it is
// the same gesture regardless of which tab you're currently on.
export default function CommandPalette({ commands, stocks = [], onNavigate, onSelectSymbol }) {
  const [open, setOpen] = useState(false)
  const [q, setQ] = useState('')
  const [idx, setIdx] = useState(0)
  const inputRef = useRef(null)

  useEffect(() => {
    const h = (e) => {
      if ((e.key === 'k' || e.key === 'K') && (e.ctrlKey || e.metaKey)) {
        e.preventDefault(); setOpen(v => !v)
      } else if (e.key === 'Escape') setOpen(false)
    }
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [])

  useEffect(() => { if (open) { setQ(''); setIdx(0); setTimeout(() => inputRef.current?.focus(), 30) } }, [open])

  const results = useMemo(() => {
    const query = q.trim().toLowerCase()
    const cmdResults = commands
      .filter(c => !query || c.label.toLowerCase().includes(query))
      .map(c => ({ type: 'command', ...c }))
    const symResults = query.length >= 1
      ? stocks.filter(s => s.symbol?.toLowerCase().includes(query) || s.companyName?.toLowerCase().includes(query))
        .slice(0, 8)
        .map(s => ({ type: 'symbol', symbol: s.symbol, label: s.symbol, sub: s.companyName }))
      : []
    return [...cmdResults, ...symResults].slice(0, 12)
  }, [q, commands, stocks])

  const choose = (item) => {
    if (!item) return
    if (item.type === 'command') onNavigate(item.key)
    else onSelectSymbol(item.symbol)
    setOpen(false)
  }

  const onKeyDown = (e) => {
    if (e.key === 'ArrowDown') { e.preventDefault(); setIdx(i => Math.min(results.length - 1, i + 1)) }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setIdx(i => Math.max(0, i - 1)) }
    else if (e.key === 'Enter') { e.preventDefault(); choose(results[idx]) }
  }

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
          onClick={() => setOpen(false)}
          style={{ position: 'fixed', inset: 0, background: 'rgba(4,10,20,0.55)', backdropFilter: 'blur(4px)', zIndex: 200, display: 'flex', alignItems: 'flex-start', justifyContent: 'center', paddingTop: '12vh' }}>
          <motion.div
            initial={{ opacity: 0, y: -12, scale: 0.98 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: -12, scale: 0.98 }}
            transition={{ duration: 0.16, ease: [0.16, 1, 0.3, 1] }}
            onClick={e => e.stopPropagation()}
            style={{ width: 'min(560px, 92vw)', background: 'var(--bg2)', border: '1px solid var(--border)', borderRadius: 14, boxShadow: '0 24px 64px rgba(0,0,0,0.45)', overflow: 'hidden' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '12px 14px', borderBottom: '1px solid var(--border)' }}>
              <span aria-hidden="true" style={{ color: 'var(--text3)' }}>⌘K</span>
              <input ref={inputRef} value={q} onChange={e => { setQ(e.target.value); setIdx(0) }} onKeyDown={onKeyDown}
                placeholder="Jump to a tab or search a symbol…" aria-label="Command palette"
                style={{ flex: 1, background: 'transparent', border: 'none', outline: 'none', color: 'var(--text)', fontSize: 14 }} />
              <kbd style={{ fontSize: 10, color: 'var(--text3)', border: '1px solid var(--border)', borderRadius: 4, padding: '2px 5px' }}>Esc</kbd>
            </div>
            <div style={{ maxHeight: '50vh', overflow: 'auto', padding: 6 }}>
              {results.length === 0 && <div style={{ padding: '18px 12px', fontSize: 12, color: 'var(--text3)', textAlign: 'center' }}>No matches</div>}
              {results.map((item, i) => (
                <div key={`${item.type}-${item.key || item.symbol}`}
                  onMouseEnter={() => setIdx(i)} onClick={() => choose(item)}
                  style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '9px 10px', borderRadius: 8, cursor: 'pointer', background: idx === i ? 'rgba(var(--accent-rgb),0.14)' : 'transparent' }}>
                  <span aria-hidden="true" style={{ width: 20, textAlign: 'center' }}>{item.type === 'symbol' ? '◈' : item.icon}</span>
                  <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--text)' }}>{item.label}</span>
                  {item.sub && <span style={{ fontSize: 11, color: 'var(--text3)' }}>{item.sub}</span>}
                  <span style={{ marginLeft: 'auto', fontSize: 10, color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{item.type === 'symbol' ? 'Symbol' : 'Go to'}</span>
                </div>
              ))}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
