import React from 'react'
import { motion } from 'framer-motion'

export const fmt = (n, d = 2) => n == null ? '—' : Number(n).toFixed(d)
export const fmtInt = (n) => n == null ? '—' : Number(n).toLocaleString('en-IN')

// Every card below is themed entirely through CSS custom properties (var(--bg2)
// etc, defined per [data-theme] in index.css) rather than hardcoded hex, unlike
// the old Options/Institutional/Agile Pro tabs this hub replaces -- that's what
// made those tabs unreadable under the light theme.
export function Card({ title, action, children, height, delay = 0 }) {
  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: delay * 0.04, duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
      style={{
        background: 'var(--bg2)', border: '1px solid var(--border)', borderRadius: 14,
        padding: 14, height, boxShadow: '0 4px 16px rgba(0,0,0,0.12)',
      }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
        <div style={{ fontSize: 10, fontWeight: 800, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text2)' }}>{title}</div>
        {action}
      </div>
      {children}
    </motion.div>
  )
}

export function Empty({ label = 'No live data available right now' }) {
  return <div style={{ fontSize: 11, color: 'var(--text3)', textAlign: 'center', padding: '20px 8px' }}>{label}</div>
}

export function Skeleton({ height = 90 }) {
  return <div className="skeleton" style={{ height, borderRadius: 10 }} />
}
