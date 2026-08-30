package com.nse500.screener

import android.Manifest
import android.annotation.SuppressLint
import android.app.DownloadManager
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.ContentValues
import android.content.Intent
import android.content.pm.PackageManager
import android.content.res.Configuration
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Environment
import android.os.Message
import android.provider.MediaStore
import android.util.Base64
import android.util.Log
import android.view.View
import android.webkit.ConsoleMessage
import android.webkit.JavascriptInterface
import android.webkit.URLUtil
import android.webkit.WebChromeClient
import android.webkit.WebResourceRequest
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Toast
import androidx.activity.addCallback
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import androidx.core.splashscreen.SplashScreen.Companion.installSplashScreen
import androidx.core.view.GravityCompat
import androidx.drawerlayout.widget.DrawerLayout
import androidx.swiperefreshlayout.widget.SwipeRefreshLayout
import com.google.android.material.appbar.MaterialToolbar
import com.google.android.material.bottomnavigation.BottomNavigationView
import com.google.android.material.navigation.NavigationView
import com.google.android.material.snackbar.Snackbar
import org.json.JSONObject
import java.io.File
import java.io.FileOutputStream
import java.net.HttpURLConnection
import java.net.URL
import java.util.concurrent.atomic.AtomicInteger

/**
 * Thin native wrapper around the live web app -- all real functionality
 * (screener, options, elite quant, everything) lives in the deployed
 * frontend at HOME_URL. This class hosts one WebView plus the native
 * chrome around it: a Material 3 top bar with a real (not static)
 * connection-state subtitle, a bottom nav that drives the SPA's own
 * internal view state via a JS bridge (the web app has no client-side
 * router -- see window.__nativeSetView in App.jsx), and export handling
 * for the app's Blob-based CSV/PDF downloads, which a plain
 * DownloadListener cannot see (blob: URLs never touch the network layer).
 */
class MainActivity : AppCompatActivity() {

    private lateinit var webView: WebView
    private lateinit var swipeRefresh: SwipeRefreshLayout
    private lateinit var toolbar: MaterialToolbar
    private lateinit var bottomNav: BottomNavigationView
    private lateinit var fadeOverlay: View
    private lateinit var drawerLayout: DrawerLayout
    private lateinit var navView: NavigationView

    private var toolbarHiddenByScroll = false
    private var suppressNavListener = false
    private val tabBackStack = ArrayDeque<Int>()
    private var pageReady = false
    private var pendingOpenSymbol: String? = null

    companion object {
        private const val TAG = "NSE500"
        private const val HOME_URL = "https://nse-top500-realtime-screener-1.onrender.com/"
        private val HOME_HOST = Uri.parse(HOME_URL).host

        // Maps each bottom-nav destination to the exact view key the SPA's
        // own NAV array uses internally (frontend/src/App.jsx) -- there is
        // no client-side router/URL per section, so navigation is done by
        // calling into the page's own React state via evaluateJavascript,
        // not by loading a different URL.
        private val NAV_KEYS = mapOf(
            R.id.nav_screener to "screener",
            R.id.nav_intraday to "intraday",
            R.id.nav_options to "options",
            R.id.nav_instruments to "optioninstruments",
            R.id.nav_etf to "etf",
        )

        // Sidebar "Tools" entries -- these map to App.jsx's TOOLS array (the
        // same secondary views previously only reachable through the web
        // page's own Tools dropdown), not the primary NAV_KEYS above.
        private val DRAWER_TOOL_KEYS = mapOf(
            R.id.drawer_paper to "paper",
            R.id.drawer_replay to "replay",
            R.id.drawer_alerts to "alerts",
            R.id.drawer_elitequant to "elitequant",
        )

        // The same external dashboard links the web page lists under its
        // Tools menu (frontend/src/App.jsx EXTERNAL_LINKS) -- opened in the
        // in-app browser (see IN_APP_BROWSER_HOSTS below) from the sidebar,
        // same destination the WebView's own target="_blank" handling opens.
        private val DRAWER_EXTERNAL_LINKS = mapOf(
            R.id.drawer_etf_dashboard to ("https://script.google.com/macros/s/AKfycbySs46EBlzP0vpAhtm9vImzIPqKUCVbxzXBigSe0HH_55iVB4kEyPv-M-BlF8ETyztu/exec" to "Smart ETF Dashboard"),
            R.id.drawer_nifty_dashboard to ("https://script.google.com/macros/s/AKfycbzSHbc7_vKJkMdkDpCC5GPVRGoJUYdJkdTe_TAWHLgfazG-rSNRJjlaRUVtoDllyRVkWg/exec" to "Nifty Indices Dashboard"),
        )

        // Known first-party-adjacent hosts that open inside this app's own
        // in-app browser (WebViewActivity) instead of handing off to Chrome.
        // Google Apps Script deployments redirect through
        // script.googleusercontent.com before rendering, so both hosts need
        // to stay in-app for the redirect chain to actually work. Anything
        // else external still goes to the system browser as a safe default.
        private val IN_APP_BROWSER_HOSTS = setOf("script.google.com", "script.googleusercontent.com")

        private const val NOTIF_CHANNEL_ID = "market_alerts"

        // Key for the extra a tapped alert notification's PendingIntent
        // carries the symbol under, and the key an update check reads the
        // app's own live GitHub Releases feed from (see checkForUpdate()).
        // The release workflow (.github/workflows/android-apk.yml) tags
        // every build "android-v{versionName}-{run_number}".
        const val EXTRA_OPEN_SYMBOL = "open_symbol"
        private const val GITHUB_RELEASES_API =
            "https://api.github.com/repos/nawin383/nse-top500-realtime-screener/releases/latest"
        private val RELEASE_TAG_VERSION = Regex("""android-v([0-9]+(?:\.[0-9]+)*)""")
    }

    private val alertNotificationId = AtomicInteger(2000)

    private val requestNotificationPermission = registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        Log.d(TAG, "POST_NOTIFICATIONS permission ${if (granted) "granted" else "denied"} by user")
    }

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        installSplashScreen()
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        webView = findViewById(R.id.webview)
        swipeRefresh = findViewById(R.id.swipe_refresh)
        toolbar = findViewById(R.id.toolbar)
        bottomNav = findViewById(R.id.bottom_nav)
        fadeOverlay = findViewById(R.id.fade_overlay)
        drawerLayout = findViewById(R.id.drawer_layout)
        navView = findViewById(R.id.nav_view)

        // Root-caused fix #1 (see android-app/README.md "Chart rendering
        // fix" section for the full write-up): lets `chrome://inspect` on a
        // PC attach to this WebView, and pipes every page console message
        // (including uncaught JS errors) to Logcat under the "NSE500" tag,
        // so a real report next time is "here's the console error" instead
        // of a guess. Debug builds only -- this is a real security-relevant
        // toggle and must never ship enabled in a release build.
        WebView.setWebContentsDebuggingEnabled(BuildConfig.DEBUG)

        configureWebSettings()
        configureWebViewClient()
        configureWebChromeClient()
        configureDownloadHandling()
        configureNotifications()
        configureBottomNav()
        configureDrawer()
        configureScrollAwareToolbar()
        configureBackStack()

        swipeRefresh.setOnRefreshListener { webView.reload() }

        if (savedInstanceState != null) {
            webView.restoreState(savedInstanceState)
        } else {
            webView.loadUrl(HOME_URL)
            tabBackStack.addLast(R.id.nav_screener)
        }

        handleOpenSymbolIntent(intent)
        checkForUpdate()
    }

    // A tapped alert notification (see postAlertNotification's
    // PendingIntent) relaunches this singleTask activity through here
    // instead of onCreate when the app is already running.
    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        handleOpenSymbolIntent(intent)
    }

    // Queues the symbol carried by a notification tap and forwards it to
    // the page's own window.__nativeOpenSymbol bridge (frontend/src/App.jsx)
    // as soon as the WebView has actually finished loading -- on a cold
    // start this intent arrives well before onPageFinished, and the page's
    // React effect that defines the bridge hasn't run yet either.
    private fun handleOpenSymbolIntent(intent: Intent?) {
        val symbol = intent?.getStringExtra(EXTRA_OPEN_SYMBOL) ?: return
        intent.removeExtra(EXTRA_OPEN_SYMBOL)
        pendingOpenSymbol = symbol
        openPendingSymbolIfReady()
    }

    private fun openPendingSymbolIfReady() {
        if (!pageReady) return
        val symbol = pendingOpenSymbol ?: return
        pendingOpenSymbol = null
        webView.evaluateJavascript(
            "window.__nativeOpenSymbol && window.__nativeOpenSymbol(${JSONObject.quote(symbol)});",
            null,
        )
    }

    private fun configureWebSettings() {
        with(webView.settings) {
            // Required: the SPA is a React app, nothing renders without JS.
            javaScriptEnabled = true
            // Required: the app persists theme/watchlist state to
            // localStorage (see frontend/src/hooks) -- without this,
            // settings silently reset on every app restart.
            domStorageEnabled = true
            // Some legacy paths in the bundle still touch WebSQL-adjacent
            // APIs; cheap to leave on, costs nothing to enable.
            databaseEnabled = true
            // Tells the WebView to honor the page's own
            // <meta name="viewport"> tag (frontend/index.html sets
            // width=device-width) instead of assuming a fixed ~980px
            // desktop-style layout width -- required for a responsive site
            // to lay out correctly at all on a phone screen.
            useWideViewPort = true
            // Zooms the initial render out to fit the wide-viewport content
            // to the actual screen width. Used together with
            // useWideViewPort per Android's own guidance for responsive
            // web content.
            loadWithOverviewMode = true
            mediaPlaybackRequiresUserGesture = false
            cacheMode = WebSettings.LOAD_DEFAULT
            // The site itself is HTTPS-only (usesCleartextTraffic=false in
            // the manifest already enforces that for the app's own
            // requests), but some embedded third-party widget could in
            // principle serve an http:// sub-resource on an https:// page.
            // COMPATIBILITY_MODE lets that load rather than silently
            // failing, without weakening the app's own network security
            // config.
            mixedContentMode = WebSettings.MIXED_CONTENT_COMPATIBILITY_MODE
            // Disabling zoom entirely (rather than just hiding the on-screen
            // zoom controls) removes pinch-zoom as a source of runtime
            // scale/pan drift -- part of the fix for content rendering
            // shifted/panned relative to the viewport (see forceReflow()'s
            // doc comment for the full root-cause writeup); the page is
            // already laid out responsively via useWideViewPort, so there's
            // nothing useful to zoom into.
            setSupportZoom(false)
            builtInZoomControls = false
            displayZoomControls = false
            // Root cause of external links "not working": without both of
            // these, WebView never invokes WebChromeClient.onCreateWindow at
            // all for a target="_blank" click -- the click is silently
            // swallowed before it ever reaches the override below. This is
            // why the dashboard links in the web page's own Tools dropdown
            // (target="_blank" anchors) appeared completely dead regardless
            // of what onCreateWindow did.
            javaScriptCanOpenWindowsAutomatically = true
            setSupportMultipleWindows(true)
        }
        // Explicit hardware layer: default since API19, but some OEM
        // WebView builds (Samsung's included, historically) have shipped
        // with software-layer fallbacks in specific configurations that
        // produce blank/partially-rendered canvas & SVG content -- forcing
        // it removes that as a variable rather than assuming the default
        // held.
        webView.setLayerType(View.LAYER_TYPE_HARDWARE, null)
    }

    private fun configureWebViewClient() {
        webView.webViewClient = object : WebViewClient() {
            override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean {
                val uri = request.url
                return when (uri.host) {
                    HOME_HOST -> false // let the WebView load it
                    in IN_APP_BROWSER_HOSTS -> { openInAppBrowser(uri.toString()); true }
                    else -> { startActivity(Intent(Intent.ACTION_VIEW, uri)); true }
                }
            }

            override fun onPageFinished(view: WebView, url: String) {
                super.onPageFinished(view, url)
                swipeRefresh.isRefreshing = false
                syncThemeWithSystem(view)
                injectDownloadBridgeScript(view)
                // Root-caused fix #2, the actual chart/table rendering fix:
                // see forceReflow() below for the full explanation. Fired
                // once immediately and once again after a short delay to
                // also cover cases where the WebView's own compositor
                // settles its viewport/zoom slightly after onPageFinished.
                forceReflow(view)
                view.postDelayed({ forceReflow(view) }, 400)
                pageReady = true
                openPendingSymbolIfReady()
            }

            override fun onReceivedError(
                view: WebView,
                request: WebResourceRequest,
                error: android.webkit.WebResourceError,
            ) {
                super.onReceivedError(view, request, error)
                if (request.isForMainFrame) {
                    Log.e(TAG, "Main frame load error: ${error.description} (${error.errorCode}) for ${request.url}")
                }
            }
        }
    }

    private fun configureWebChromeClient() {
        webView.webChromeClient = object : WebChromeClient() {
            // Every console.log/warn/error from the page lands here. This
            // is the real diagnostic channel requested: connect
            // `adb logcat -s NSE500Console` (or chrome://inspect on a PC
            // with the phone on USB debugging) to see actual JS runtime
            // errors instead of guessing at them.
            override fun onConsoleMessage(consoleMessage: ConsoleMessage): Boolean {
                val level = consoleMessage.messageLevel()
                val text = "${consoleMessage.message()} -- ${consoleMessage.sourceId()}:${consoleMessage.lineNumber()}"
                when (level) {
                    ConsoleMessage.MessageLevel.ERROR -> Log.e("NSE500Console", text)
                    ConsoleMessage.MessageLevel.WARNING -> Log.w("NSE500Console", text)
                    else -> Log.d("NSE500Console", text)
                }
                return true
            }

            // target="_blank" links (e.g. the external Google Apps Script
            // dashboard links in the Tools menu) open a new WebView window
            // by default, which this app never displays -- intercept and
            // route known dashboard hosts to the in-app browser, anything
            // else to the system browser instead of a dead link.
            override fun onCreateWindow(
                view: WebView,
                isDialog: Boolean,
                isUserGesture: Boolean,
                resultMsg: Message,
            ): Boolean {
                val transport = resultMsg.obj as? WebView.WebViewTransport
                val newWebView = WebView(this@MainActivity)
                newWebView.webViewClient = object : WebViewClient() {
                    override fun shouldOverrideUrlLoading(v: WebView, request: WebResourceRequest): Boolean {
                        if (request.url.host in IN_APP_BROWSER_HOSTS) {
                            openInAppBrowser(request.url.toString())
                        } else {
                            startActivity(Intent(Intent.ACTION_VIEW, request.url))
                        }
                        return true
                    }
                }
                transport?.webView = newWebView
                resultMsg.sendToTarget()
                return true
            }
        }
    }

    // ------------------------------------------------------------------
    // Root cause of the Samsung S21 FE chart/table rendering bug:
    //
    // The chart library actually used here (verified in the repo, not
    // guessed -- see frontend/node_modules/recharts/lib/component/
    // ResponsiveContainer.js) sizes every chart from a single synchronous
    // `containerRef.current.getBoundingClientRect()` call inside a
    // useEffect that runs once on mount, *before* it starts observing
    // further changes via ResizeObserver. If that one-time read happens to
    // return 0x0 -- which it can, on some WebView builds, if the WebView's
    // internal compositor hasn't finished resolving the page's
    // useWideViewPort/initial-scale zoom by the time React's post-paint
    // effect fires -- the chart renders as a genuine but literally 0x0
    // element and stays that way forever, because nothing subsequently
    // changes that element's real box size to give ResizeObserver a reason
    // to fire again. Recharts has no window-resize fallback for this (only
    // ResizeObserver), so the commonly-suggested `dispatchEvent(new
    // Event('resize'))` trick does NOT fix it either -- confirmed by
    // reading the source rather than assumed, since ResizeObserver only
    // fires on an actual measured size change, not a synthetic DOM event.
    //
    // The real fix has to force an actual reflow of the page after the
    // WebView has visually settled, so ResizeObserver sees a genuine size
    // delta and reports the correct final dimensions. Toggling
    // document.body's min-height by 1px and back (via requestAnimationFrame)
    // does exactly that: it's a real, measurable layout change, so any
    // chart container stuck at a stale 0x0 reading gets a fresh, correct
    // ResizeObserver callback.
    // ------------------------------------------------------------------
    private fun forceReflow(view: WebView) {
        view.evaluateJavascript(
            """
            (function(){
              try {
                var b = document.body;
                var prevMinHeight = b.style.minHeight;
                var target = (document.documentElement.clientHeight || window.innerHeight) + 1;
                b.style.minHeight = target + 'px';
                requestAnimationFrame(function(){
                  b.style.minHeight = prevMinHeight;
                  window.dispatchEvent(new Event('resize'));
                });
              } catch (e) {
                console.error('[NSE500 native] forceReflow failed', e);
              }
            })();
            """.trimIndent(),
            null,
        )
    }

    private fun syncThemeWithSystem(view: WebView) {
        val isDark = (resources.configuration.uiMode and Configuration.UI_MODE_NIGHT_MASK) == Configuration.UI_MODE_NIGHT_YES
        val theme = if (isDark) "dark" else "light"
        // frontend/src/components/ThemeToggle.jsx already drives the whole
        // app's palette off this exact attribute -- this only sets the
        // *initial* value to match the system, the user's own in-app
        // toggle still works normally afterwards.
        view.evaluateJavascript("document.documentElement.setAttribute('data-theme','$theme');", null)
    }

    override fun onConfigurationChanged(newConfig: Configuration) {
        super.onConfigurationChanged(newConfig)
        if (::webView.isInitialized) syncThemeWithSystem(webView)
    }

    // ------------------------------------------------------------------
    // CSV/PDF export fix. InstitutionalView.jsx's exportCSV/exportPDF build
    // a Blob, URL.createObjectURL() it, and synthetically click a
    // `<a download>` -- a plain WebView DownloadListener never fires for
    // this because blob: URLs never reach the network stack (this is the
    // known limitation flagged in the previous version's README). The
    // actual fix: intercept the click in-page, read the blob back to a
    // base64 string via FileReader, and hand it to a JS interface that
    // writes it through MediaStore/DownloadManager natively.
    // ------------------------------------------------------------------
    private fun configureDownloadHandling() {
        webView.addJavascriptInterface(DownloadBridge(), "AndroidDownload")
        webView.addJavascriptInterface(ConnectionBridge(), "AndroidBridge")

        // Real (non-blob) network downloads still go through the normal
        // Android download path.
        webView.setDownloadListener { url, userAgent, contentDisposition, mimeType, _ ->
            try {
                val filename = URLUtil.guessFileName(url, contentDisposition, mimeType)
                val request = DownloadManager.Request(Uri.parse(url)).apply {
                    setMimeType(mimeType)
                    addRequestHeader("User-Agent", userAgent)
                    setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED)
                    setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS, filename)
                    setTitle(filename)
                }
                (getSystemService(DOWNLOAD_SERVICE) as DownloadManager).enqueue(request)
                Toast.makeText(this, "Downloading $filename…", Toast.LENGTH_SHORT).show()
            } catch (e: Exception) {
                Log.e(TAG, "DownloadListener failed for $url", e)
                Toast.makeText(this, "Download failed", Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun injectDownloadBridgeScript(view: WebView) {
        view.evaluateJavascript(
            """
            (function(){
              if (window.__nseDownloadHooked) return;
              window.__nseDownloadHooked = true;
              document.addEventListener('click', function(e){
                var a = e.target && e.target.closest ? e.target.closest('a[download]') : null;
                if (!a || !a.href || a.href.indexOf('blob:') !== 0) return;
                e.preventDefault();
                fetch(a.href).then(function(r){ return r.blob(); }).then(function(blob){
                  var reader = new FileReader();
                  reader.onloadend = function(){
                    try {
                      var base64 = String(reader.result).split(',')[1] || '';
                      var mime = blob.type || 'application/octet-stream';
                      if (window.AndroidDownload) {
                        window.AndroidDownload.saveBase64File(base64, a.download || 'download', mime);
                      }
                    } catch (e) { console.error('[NSE500 native] download bridge failed', e); }
                  };
                  reader.readAsDataURL(blob);
                }).catch(function(e){ console.error('[NSE500 native] blob fetch failed', e); });
              }, true);
            })();
            """.trimIndent(),
            null,
        )
    }

    private inner class DownloadBridge {
        @JavascriptInterface
        fun saveBase64File(base64Data: String, filename: String, mimeType: String) {
            runOnUiThread { saveDownload(base64Data, filename, mimeType) }
        }
    }

    @Suppress("DEPRECATION") // legacy external-storage path, only used below API 29 (Q)
    private fun saveDownloadLegacy(bytes: ByteArray, filename: String, mimeType: String) {
        val downloadsDir = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS)
        if (!downloadsDir.exists()) downloadsDir.mkdirs()
        val file = File(downloadsDir, filename)
        FileOutputStream(file).use { it.write(bytes) }
        val dm = getSystemService(DOWNLOAD_SERVICE) as DownloadManager
        dm.addCompletedDownload(filename, filename, true, mimeType, file.absolutePath, bytes.size.toLong(), true)
    }

    private fun saveDownload(base64Data: String, filename: String, mimeType: String) {
        try {
            val bytes = Base64.decode(base64Data, Base64.DEFAULT)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                val values = ContentValues().apply {
                    put(MediaStore.MediaColumns.DISPLAY_NAME, filename)
                    put(MediaStore.MediaColumns.MIME_TYPE, mimeType)
                    put(MediaStore.MediaColumns.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS)
                }
                val uri = contentResolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values)
                    ?: throw IllegalStateException("MediaStore insert returned null")
                contentResolver.openOutputStream(uri)?.use { it.write(bytes) }
            } else {
                saveDownloadLegacy(bytes, filename, mimeType)
            }
            Toast.makeText(this, "Saved $filename to Downloads", Toast.LENGTH_SHORT).show()
        } catch (e: Exception) {
            Log.e(TAG, "Failed to save download $filename", e)
            Toast.makeText(this, "Download failed: ${e.message}", Toast.LENGTH_SHORT).show()
        }
    }

    // ------------------------------------------------------------------
    // Real push notifications for market alerts. frontend/src/App.jsx calls
    // window.AndroidAlerts.postAlert(...) for every new breakout/volume
    // spike/VWAP cross/etc. alert that already appears in the web app's own
    // "LIVE ALERTS" ticker (a no-op when not running inside this app), so
    // the same real alerts also land as system notifications instead of
    // only being visible while the app is open and in the foreground.
    // ------------------------------------------------------------------
    private fun configureNotifications() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                NOTIF_CHANNEL_ID, "Market Alerts", NotificationManager.IMPORTANCE_DEFAULT,
            ).apply { description = "Breakouts, volume spikes, VWAP crosses and other screener alerts" }
            (getSystemService(NOTIFICATION_SERVICE) as NotificationManager).createNotificationChannel(channel)
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
            ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED
        ) {
            // Posted rather than called directly: requesting a runtime
            // permission in the same frame as onCreate, while the Splash
            // Screen API's exit transition is still animating off, is a
            // known way for the system permission dialog to never actually
            // appear (or get auto-dismissed) on some OEM builds. Posting to
            // the decor view runs this after that transition has settled.
            window.decorView.post {
                if (ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
                    requestNotificationPermission.launch(Manifest.permission.POST_NOTIFICATIONS)
                }
            }
        }
        webView.addJavascriptInterface(AlertsBridge(), "AndroidAlerts")
    }

    private inner class AlertsBridge {
        @JavascriptInterface
        fun postAlert(symbol: String, type: String, message: String) {
            Log.d(TAG, "AndroidAlerts.postAlert called: $symbol / $type / $message")
            runOnUiThread { postAlertNotification(symbol, type, message) }
        }
    }

    private fun postAlertNotification(symbol: String, type: String, message: String) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
            ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED
        ) {
            Log.w(TAG, "Not posting notification for $symbol -- POST_NOTIFICATIONS not granted")
            return // user hasn't granted it (or declined the prompt) -- nothing to post
        }
        // Tapping the notification should land the user on exactly the
        // stock the alert is about, not just a generic app-open -- routes
        // through the same window.__nativeOpenSymbol bridge onNewIntent
        // uses for a warm start.
        val contentIntent = PendingIntent.getActivity(
            this,
            symbol.hashCode(),
            Intent(this, MainActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
                putExtra(EXTRA_OPEN_SYMBOL, symbol)
            },
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        val notification = NotificationCompat.Builder(this, NOTIF_CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_launcher_monochrome)
            .setContentTitle("$symbol · ${type.replace('_', ' ')}")
            .setContentText(message)
            .setStyle(NotificationCompat.BigTextStyle().bigText(message))
            .setPriority(NotificationCompat.PRIORITY_DEFAULT)
            .setAutoCancel(true)
            .setContentIntent(contentIntent)
            .build()
        try {
            val id = alertNotificationId.incrementAndGet()
            NotificationManagerCompat.from(this).notify(id, notification)
            Log.d(TAG, "Notification #$id posted for $symbol")
        } catch (e: SecurityException) {
            Log.w(TAG, "Notification post denied by system", e)
        }
    }

    // ------------------------------------------------------------------
    // Live connection status in the top bar. frontend/src/App.jsx calls
    // window.AndroidBridge.onConnectionState(status) whenever its own
    // WebSocket status changes (a no-op when not running inside this app),
    // so the subtitle reflects the real socket state, not a static label.
    // ------------------------------------------------------------------
    private inner class ConnectionBridge {
        @JavascriptInterface
        fun onConnectionState(state: String) {
            runOnUiThread {
                toolbar.subtitle = when (state) {
                    "open" -> getString(R.string.status_live)
                    "connecting" -> getString(R.string.status_connecting)
                    else -> getString(R.string.status_reconnecting)
                }
            }
        }
    }

    // ------------------------------------------------------------------
    // Bottom navigation. The web app has no client-side router (single
    // SPA view state, see App.jsx's `view`/`setView`), so tabs don't load
    // different URLs -- they call window.__nativeSetView(key), which
    // App.jsx exposes as a thin bridge onto its own setView.
    // ------------------------------------------------------------------
    private fun configureBottomNav() {
        bottomNav.setOnItemSelectedListener { item ->
            if (!suppressNavListener) {
                if (tabBackStack.lastOrNull() != item.itemId) tabBackStack.addLast(item.itemId)
                navigateToTab(item.itemId)
            }
            true
        }
    }

    private fun navigateToTab(itemId: Int) {
        val key = NAV_KEYS[itemId] ?: return
        crossFade {
            webView.evaluateJavascript("window.__nativeSetView && window.__nativeSetView('$key');", null)
        }
    }

    // ------------------------------------------------------------------
    // Sidebar (broker-app style secondary navigation, e.g. Nuvama Market).
    // The bottom nav only has room for the 5 primary sections; this drawer
    // surfaces everything else that otherwise only lived inside the web
    // page's own in-page Tools dropdown.
    // ------------------------------------------------------------------
    private fun configureDrawer() {
        toolbar.setNavigationOnClickListener { drawerLayout.openDrawer(GravityCompat.START) }

        navView.setNavigationItemSelectedListener { item ->
            when {
                DRAWER_TOOL_KEYS.containsKey(item.itemId) -> {
                    val key = DRAWER_TOOL_KEYS.getValue(item.itemId)
                    crossFade {
                        webView.evaluateJavascript("window.__nativeSetView && window.__nativeSetView('$key');", null)
                    }
                }
                DRAWER_EXTERNAL_LINKS.containsKey(item.itemId) -> {
                    val (url, title) = DRAWER_EXTERNAL_LINKS.getValue(item.itemId)
                    openInAppBrowser(url, title)
                }
                item.itemId == R.id.drawer_refresh -> {
                    webView.reload()
                }
            }
            drawerLayout.closeDrawer(GravityCompat.START)
            true
        }
    }

    private fun openInAppBrowser(url: String, title: String = "") {
        startActivity(Intent(this, WebViewActivity::class.java).apply {
            putExtra(WebViewActivity.EXTRA_URL, url)
            putExtra(WebViewActivity.EXTRA_TITLE, title)
        })
    }

    // A real (if simple) Material fade-through: fade the overlay in over
    // the WebView, swap the underlying view while it's covered, fade back
    // out. Nothing custom-hacked -- plain ViewPropertyAnimator, standard
    // Material motion duration/feel for a fade-through transition.
    private fun crossFade(action: () -> Unit) {
        fadeOverlay.alpha = 0f
        fadeOverlay.visibility = View.VISIBLE
        fadeOverlay.animate().alpha(1f).setDuration(90).withEndAction {
            action()
            fadeOverlay.animate().alpha(0f).setDuration(150).withEndAction {
                fadeOverlay.visibility = View.GONE
            }.start()
        }.start()
    }

    private fun configureBackStack() {
        onBackPressedDispatcher.addCallback(this) {
            when {
                drawerLayout.isDrawerOpen(GravityCompat.START) -> drawerLayout.closeDrawer(GravityCompat.START)
                webView.canGoBack() -> webView.goBack()
                tabBackStack.size > 1 -> {
                    tabBackStack.removeLast()
                    val previous = tabBackStack.last()
                    suppressNavListener = true
                    bottomNav.selectedItemId = previous
                    suppressNavListener = false
                    navigateToTab(previous)
                }
                else -> {
                    isEnabled = false
                    onBackPressedDispatcher.onBackPressed()
                }
            }
        }
    }

    // ------------------------------------------------------------------
    // Scroll-aware top app bar: hides on scroll-down, reappears on
    // scroll-up. A full CollapsingToolbarLayout needs the scrolled content
    // to be a nested-scrolling child, which a plain WebView isn't without
    // a custom NestedScrollingChild subclass -- driving the toolbar's
    // translationY directly off the WebView's own scroll deltas is the
    // standard, much simpler alternative that doesn't require replacing
    // WebView with a custom class.
    // ------------------------------------------------------------------
    private fun configureScrollAwareToolbar() {
        webView.setOnScrollChangeListener { _, _, scrollY, _, oldScrollY ->
            val dy = scrollY - oldScrollY
            if (dy > 12 && !toolbarHiddenByScroll) {
                toolbarHiddenByScroll = true
                toolbar.animate().translationY(-toolbar.height.toFloat()).setDuration(150).start()
            } else if (dy < -12 && toolbarHiddenByScroll) {
                toolbarHiddenByScroll = false
                toolbar.animate().translationY(0f).setDuration(150).start()
            }
        }
    }

    override fun onSaveInstanceState(outState: Bundle) {
        super.onSaveInstanceState(outState)
        webView.saveState(outState)
    }

    // ------------------------------------------------------------------
    // In-app update check. There's no Play Store listing for this app --
    // the only real distribution channel is the GitHub Release the CI
    // workflow attaches the APK to (.github/workflows/android-apk.yml,
    // tag format "android-v{versionName}-{run_number}") -- so this hits
    // that same repo's public Releases API directly instead of a store
    // SDK that doesn't apply here. Best-effort and silent on any failure
    // (offline, rate-limited, no releases yet): never blocks or nags the
    // user, it only surfaces something when a strictly newer version
    // actually exists.
    // ------------------------------------------------------------------
    private fun checkForUpdate() {
        Thread {
            try {
                val connection = URL(GITHUB_RELEASES_API).openConnection() as HttpURLConnection
                connection.connectTimeout = 8000
                connection.readTimeout = 8000
                connection.setRequestProperty("Accept", "application/vnd.github+json")
                val body = connection.inputStream.bufferedReader().use { it.readText() }
                val json = JSONObject(body)
                val tag = json.optString("tag_name")
                val releaseUrl = json.optString("html_url")
                val match = RELEASE_TAG_VERSION.find(tag) ?: return@Thread
                val latestVersion = match.groupValues[1]
                if (releaseUrl.isNotEmpty() && isNewerVersion(latestVersion, BuildConfig.VERSION_NAME)) {
                    runOnUiThread { showUpdateAvailable(latestVersion, releaseUrl) }
                }
            } catch (e: Exception) {
                Log.d(TAG, "Update check skipped: ${e.message}")
            }
        }.start()
    }

    // Plain dotted-integer version comparison (e.g. "2.3.0" vs "2.2.1") --
    // both this app's versionName and the CI tag's embedded version follow
    // that scheme, so no external version-compare library is needed.
    private fun isNewerVersion(remote: String, current: String): Boolean {
        val r = remote.split(".").map { it.toIntOrNull() ?: 0 }
        val c = current.split(".").map { it.toIntOrNull() ?: 0 }
        for (i in 0 until maxOf(r.size, c.size)) {
            val rv = r.getOrElse(i) { 0 }
            val cv = c.getOrElse(i) { 0 }
            if (rv != cv) return rv > cv
        }
        return false
    }

    private fun showUpdateAvailable(version: String, releaseUrl: String) {
        Snackbar.make(swipeRefresh, "Update available: v$version", Snackbar.LENGTH_INDEFINITE)
            .setAction("View") { startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(releaseUrl))) }
            .show()
    }
}
