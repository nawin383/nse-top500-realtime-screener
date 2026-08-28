import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useOptionsData } from '../../hooks/useOptionsData.js'
import ChainView from './ChainView.jsx'
import AnalyticsView from './AnalyticsView.jsx'
import InstitutionalView from './InstitutionalView.jsx'

const SUBTABS = [
  { k: 'chain', label: 'Chain', icon: '⛓' },
  { k: 'analytics', label: 'Analytics', icon: '📊' },
  { k: 'institutional', label: 'Institutional Flow', icon: '🏛' },
]

// One shared symbol/expiry/data-fetch layer feeding three sub-views. This
// replaces four separately-coded tabs (Options, Options Insights,
// Institutional, Agile Pro) that each re-fetched overlapping PCR/Max
// Pain/Greeks/VIX endpoints with their own copy-pasted guard logic, and each
// had its own independent (and inconsistent) symbol/expiry selection.
export default function OptionsHub({ theme }) {
  const [symbol, setSymbol] = useState('NIFTY')
  const [expiry, setExpiry] = useState('')
  const [sub, setSub] = useState('chain')
  const [windowSize, setWindowSize] = useState(10)
  const { data, expiries, loading, lastFetch, hasLoadedOnce } = useOptionsData(symbol, expiry, { windowSize })

  // keep expiry valid whenever the symbol changes or the expiry list refreshes
  React.useEffect(() => {
    if (expiries.length && (!expiry || !expiries.includes(expiry))) setExpiry(expiries[0])
  }, [expiries, expiry])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
        <h2 style={{ fontSize: 16, fontWeight: 800, margin: 0 }}>Options</h2>
        <select className="input" value={symbol} onChange={e => { setSymbol(e.target.value); setExpiry('') }}>
          <option value="NIFTY">NIFTY 50</option>
          <option value="SENSEX">SENSEX</option>
          <option value="BANKNIFTY">BANKNIFTY</option>
        </select>
        <select className="input" value={expiry} onChange={e => setExpiry(e.target.value)} style={{ minWidth: 140 }}>
          {expiries.map(e => <option key={e} value={e}>{e}</option>)}
          {!expiries.length && <option>Loading…</option>}
        </select>
        {lastFetch && <span style={{ fontSize: 10, color: 'var(--text3)' }}>as of {lastFetch.toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata' })}</span>}
        <span style={{ marginLeft: 'auto', fontSize: 10, color: 'var(--text3)' }}>All figures from the live option chain • real data only, gaps shown as "no data"</span>
      </div>

      <div role="tablist" aria-label="Options sub-view" style={{ display: 'flex', gap: 4, background: 'var(--bg3)', padding: 4, borderRadius: 12, border: '1px solid var(--border)', width: 'fit-content' }}>
        {SUBTABS.map(t => (
          <button key={t.k} role="tab" aria-selected={sub === t.k} onClick={() => setSub(t.k)}
            style={{ position: 'relative', padding: '7px 14px', fontSize: 12, fontWeight: 700, borderRadius: 9, border: 'none', cursor: 'pointer', background: 'transparent', color: sub === t.k ? '#04101f' : 'var(--text2)', zIndex: 1 }}>
            {sub === t.k && (
              <motion.span layoutId="options-subtab-pill" transition={{ type: 'spring', stiffness: 500, damping: 35 }}
                style={{ position: 'absolute', inset: 0, borderRadius: 9, background: 'linear-gradient(135deg,var(--accent),var(--accent-light))', zIndex: -1 }} />
            )}
            <span aria-hidden="true">{t.icon}</span> {t.label}
          </button>
        ))}
      </div>

      <AnimatePresence mode="wait">
        <motion.div key={sub}
          initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }}
          transition={{ duration: 0.18, ease: [0.16, 1, 0.3, 1] }}>
          {sub === 'chain' && <ChainView data={data} loading={loading} hasLoadedOnce={hasLoadedOnce} windowSize={windowSize} onWindowSize={setWindowSize} />}
          {sub === 'analytics' && <AnalyticsView data={data} theme={theme} />}
          {sub === 'institutional' && <InstitutionalView symbol={symbol} expiry={expiry} data={data} />}
        </motion.div>
      </AnimatePresence>
    </div>
  )
}
