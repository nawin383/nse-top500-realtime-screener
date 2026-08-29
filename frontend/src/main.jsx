import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'
import { registerSW } from './pwa.js'
import { AuthProvider } from './hooks/useAuth.js'
registerSW()

// Surfaces otherwise-silent JS failures as real console.error calls, which
// the Android app's WebChromeClient.onConsoleMessage pipes to Logcat (and
// which any browser's own devtools already show) -- without this, a
// component tree crashing partway through initial render can silently
// leave the page half-built with nothing in the console to explain why.
window.addEventListener('error', (e) => {
  console.error('[unhandled error]', e.message, e.filename ? `${e.filename}:${e.lineno}:${e.colno}` : '', e.error?.stack || '')
})
window.addEventListener('unhandledrejection', (e) => {
  console.error('[unhandled promise rejection]', e.reason?.stack || e.reason)
})

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <AuthProvider>
      <App />
    </AuthProvider>
  </React.StrictMode>,
)
