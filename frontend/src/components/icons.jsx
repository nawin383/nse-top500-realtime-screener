import React from 'react'

// Crafted inline-SVG icon set -- replaces ad hoc emoji (⛓ 📊 🏛 🎯 📜 🧰 🔔
// 🧪 ⏮) which render inconsistently across OS/browser emoji fonts and don't
// take a currentColor tint. Every icon shares a 24x24 viewBox, 1.8 stroke,
// round caps -- so mixing them anywhere reads as one deliberate system
// rather than a grab-bag of glyphs.
const base = { width: 15, height: 15, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 1.8, strokeLinecap: 'round', strokeLinejoin: 'round', 'aria-hidden': true }

export const IconScreener = (p) => <svg {...base} {...p}><rect x="3" y="4" width="7" height="7" rx="1.5"/><rect x="14" y="4" width="7" height="7" rx="1.5"/><rect x="3" y="15" width="7" height="5" rx="1.5"/><rect x="14" y="15" width="7" height="5" rx="1.5"/></svg>
export const IconTarget = (p) => <svg {...base} {...p}><circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="4"/><circle cx="12" cy="12" r="0.6" fill="currentColor"/></svg>
export const IconChain = (p) => <svg {...base} {...p}><path d="M9 15l6-6"/><path d="M8 13l-1.5 1.5a3 3 0 004.2 4.2L12 17"/><path d="M16 11l1.5-1.5a3 3 0 00-4.2-4.2L12 7"/></svg>
export const IconScroll = (p) => <svg {...base} {...p}><path d="M6 4h9a3 3 0 013 3v11a2 2 0 01-2 2H8a2 2 0 01-2-2V4z"/><path d="M6 4a2 2 0 00-2 2v12a2 2 0 002 2"/><path d="M9 9h6M9 13h6"/></svg>
export const IconToolbox = (p) => <svg {...base} {...p}><rect x="3" y="9" width="18" height="10" rx="2"/><path d="M8 9V6a2 2 0 012-2h4a2 2 0 012 2v3"/><path d="M3 13h18"/></svg>
export const IconFlask = (p) => <svg {...base} {...p}><path d="M10 3h4"/><path d="M10 3v6l-5.5 9.5A1.5 1.5 0 005.8 21h12.4a1.5 1.5 0 001.3-2.5L14 9V3"/><path d="M8.5 15h7"/></svg>
export const IconRewind = (p) => <svg {...base} {...p}><path d="M12 5v14l-9-7z"/><path d="M22 5v14l-9-7z"/></svg>
export const IconBell = (p) => <svg {...base} {...p}><path d="M6 10a6 6 0 1112 0c0 4 1.5 5.5 1.5 5.5H4.5S6 14 6 10z"/><path d="M10 20a2 2 0 004 0"/></svg>
export const IconGear = (p) => <svg {...base} {...p}><circle cx="12" cy="12" r="3"/><path d="M19.4 13.5a1.7 1.7 0 000-3l1-1.7-1.7-1.7-1.7 1a1.7 1.7 0 00-3-1.4L13.5 5h-3l-.5 1.7a1.7 1.7 0 00-3 1.4l-1.7-1L3.6 8.8l1 1.7a1.7 1.7 0 000 3l-1 1.7 1.7 1.7 1.7-1a1.7 1.7 0 003 1.4l.5 1.7h3l.5-1.7a1.7 1.7 0 003-1.4l1.7 1 1.7-1.7z"/></svg>
export const IconBuilding = (p) => <svg {...base} {...p}><rect x="4" y="3" width="10" height="18" rx="1"/><rect x="16" y="9" width="5" height="12" rx="1"/><path d="M7 7h1M11 7h1M7 11h1M11 11h1M7 15h1M11 15h1"/></svg>
export const IconChart = (p) => <svg {...base} {...p}><path d="M4 20V10M11 20V4M18 20v-7"/></svg>
export const IconExternal = (p) => <svg {...base} {...p}><path d="M14 5h5v5"/><path d="M19 5l-8 8"/><path d="M17 13v5a2 2 0 01-2 2H6a2 2 0 01-2-2V9a2 2 0 012-2h5"/></svg>
export const IconSparkle = (p) => <svg {...base} {...p}><path d="M12 3l1.6 4.9L18 9.5l-4.4 1.6L12 16l-1.6-4.9L6 9.5l4.4-1.6z"/><path d="M19 15l.7 2 2 .7-2 .7-.7 2-.7-2-2-.7 2-.7z"/></svg>
export const IconTrendUp = (p) => <svg {...base} {...p}><path d="M4 15l5.5-5.5L13 13l7-7"/><path d="M15 6h5v5"/></svg>
