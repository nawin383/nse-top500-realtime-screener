import React from 'react'
import { useStore, store } from '../store/useStore.js'

const ACCENTS = [
  { k: 'blue', color: '#2563eb', label: 'Blue' },
  { k: 'emerald', color: '#10b981', label: 'Emerald' },
  { k: 'violet', color: '#8b5cf6', label: 'Violet' },
  { k: 'rose', color: '#f43f5e', label: 'Rose' },
]

export default function AccentPicker() {
  const accent = useStore(s => s.accent) || 'blue'
  return (
    <div role="group" aria-label="Accent color" style={{ display: 'flex', gap: 5, alignItems: 'center', padding: '3px 6px', background: 'var(--bg3)', border: '1px solid var(--border)', borderRadius: 999 }}>
      {ACCENTS.map(a => (
        <button key={a.k} onClick={() => store.setAccent(a.k)} title={a.label} aria-label={`${a.label} accent`} aria-pressed={accent === a.k}
          style={{
            width: 16, height: 16, borderRadius: '50%', background: a.color, border: accent === a.k ? '2px solid var(--text)' : '2px solid transparent',
            cursor: 'pointer', padding: 0, boxShadow: accent === a.k ? `0 0 0 2px ${a.color}55` : 'none', transition: 'transform .15s',
          }} />
      ))}
    </div>
  )
}
