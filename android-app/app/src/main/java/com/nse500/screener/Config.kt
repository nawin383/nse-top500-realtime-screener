package com.nse500.screener

/**
 * Single source of truth for the deployed backend's base URL. MainActivity's
 * WebView, AlertsWorker's background poll, and the home screen widget all
 * need this same value -- pulling it from one place means there's no way
 * for the worker to silently drift onto a different host than the app is
 * actually showing.
 */
object Nse500Config {
    const val HOME_URL = "https://nse-top500-realtime-screener-1.onrender.com/"
}
