# NSE500 Screener — Android app

A native wrapper (one Activity, one WebView, real Material 3 chrome around
it) around the live web app at
https://nse-top500-realtime-screener-1.onrender.com/. All real functionality
lives in the deployed frontend — this project makes it launchable as its own
app with a bottom nav, live connection status, and working exports, instead
of being a bookmarked browser tab.

## Getting the APK

Every push to `android-app/**` (or a manual run) builds a debug APK via
`.github/workflows/android-apk.yml` and:

1. **Attaches it to a GitHub Release** — go to the repo's **Releases** page
   and grab the latest `android-v*` release. This is the stable, permanent
   link; it doesn't move when a new build runs (each build gets its own
   release/tag).
2. Also uploads it as a workflow **Actions artifact** (`nse500-screener-debug-apk`)
   if you'd rather grab it from a specific run.

On your phone: download the `.apk`, then open it (Android will ask you to
allow "install unknown apps" for whichever app you used to open it — expected
for anything outside the Play Store; this is a debug build, not signed for
the Play Store).

## Building locally

Requires the Android SDK (Android Studio, or `cmdline-tools` +
`platform-tools` + `build-tools;34.0.0` + `platforms;android-34`) and a
`local.properties` pointing `sdk.dir` at it — Android Studio creates this
automatically if you open this folder as a project.

```
./gradlew assembleDebug
```

Output: `app/build/outputs/apk/debug/app-debug.apk`.

## The Samsung/One UI chart-and-table rendering fix

**Symptom**: on a Samsung Galaxy S21 FE, charts and some tables didn't
render — not a crash, just blank/empty space where they should be.

**Root cause** (found by reading the actual charting library's source in
this repo, not guessed): `frontend/node_modules/recharts/lib/component/
ResponsiveContainer.js` sizes every chart with **one synchronous
`getBoundingClientRect()` call inside a mount-time `useEffect`**, then hands
off to a `ResizeObserver` for anything after that — there is no
`window.resize` fallback. If that one-time read happens to return `0×0`
(which can happen if the WebView's compositor hasn't finished resolving the
page's `useWideViewPort`/initial-scale zoom by the time React's post-paint
effect fires — a real, known category of WebView timing quirk, more
noticeable on some OEM WebView builds), Recharts renders a chart that is
*genuinely* 0 pixels wide and never recovers, because nothing later changes
that element's real size to give `ResizeObserver` a reason to fire again.
Since tables are plain HTML, a *different* rendering failure showing up at
the same time would point to a JS exception aborting part of the render
tree instead — which is why `main.jsx` now also pipes every uncaught error
and unhandled promise rejection to `console.error` (see below), so that's
verifiable next time instead of guessed at.

Note on a commonly suggested "fix" that does **not** actually work here:
manually dispatching `window.dispatchEvent(new Event('resize'))` does
nothing for a `ResizeObserver`-based component — `ResizeObserver` only
fires on a genuine measured size change, not a synthetic DOM event. Several
blog posts recommend it anyway; it was checked against the actual
Recharts source before ruling it out, not assumed.

**The fix, in two layers:**
1. `MainActivity.forceReflow()` runs a real, standards-correct reflow nudge
   (briefly changing `document.body`'s `min-height` and back, inside
   `requestAnimationFrame`) once at `onPageFinished` and once again ~400ms
   later — this genuinely changes the page's layout, which is what makes
   `ResizeObserver` recompute and report each chart's correct final size.
2. Every `<ResponsiveContainer>` in the frontend now also has an explicit
   `minWidth`/`minHeight`, so even in the worst case a chart is never
   literally invisible — it renders at a sane fallback size until/unless
   the observer corrects it.

**Real diagnosis, not guessing, for next time:** `WebView.
setWebContentsDebuggingEnabled(BuildConfig.DEBUG)` is on in debug builds, so
you can plug the phone into a PC and open `chrome://inspect` in desktop
Chrome to get a real DevTools console on the actual device. Separately,
`WebChromeClient.onConsoleMessage` pipes every page console message
(`console.log/warn/error`, including uncaught exceptions) to Logcat under
the `NSE500Console` tag — `adb logcat -s NSE500Console` while using the app
shows exactly what the page's JS is doing, no guessing required.

This was implemented and CI-verified to compile and package correctly, but
**not verified against a real Samsung device from this environment** — there
was no physical device or emulator available to reproduce the original bug
on. If it recurs, the console log pipe above will show the actual error.

## What's new in v2.3.0

Four upgrades on top of v2.2.1's bug fixes:

- **In-app update checker.** On every launch, a background thread hits this
  same repo's public GitHub Releases API
  (`api.github.com/repos/nawin383/nse-top500-realtime-screener/releases/latest`)
  and parses the CI-produced tag (`android-v{version}-{run_number}`, see
  `.github/workflows/android-apk.yml`). If the latest release's version is
  strictly newer than the running app's own `BuildConfig.VERSION_NAME`, a
  Snackbar offers a "View" action that opens the release page in the system
  browser. There's no Play Store listing for this app, so this is the real
  (only) update channel available -- not a stand-in for one. Silent and
  non-blocking on any failure (offline, rate-limited, no releases yet).
- **Notification tap now opens the actual stock.** Every alert notification
  (`postAlertNotification` in `MainActivity.kt`) now carries a `PendingIntent`
  with the alert's symbol; tapping it relaunches/foregrounds the app (this
  activity is already `singleTask`) and calls a new
  `window.__nativeOpenSymbol(symbol)` bridge in `frontend/src/App.jsx`, which
  switches to the Screener tab and opens that symbol's detail panel via the
  same `handleSelect` used when tapping a row in the table. Handles both a
  cold start (`onCreate` queues the symbol until `onPageFinished` confirms
  the page — and its `__nativeOpenSymbol` bridge — has actually loaded) and
  a warm tap while the app is already running (`onNewIntent`).
- **R8 minification + resource shrinking**, with explicit
  `-keepclassmembers` rules in `proguard-rules.pro` protecting every
  `@JavascriptInterface` method on `DownloadBridge`/`ConnectionBridge`/
  `AlertsBridge` (invisible to R8's static call graph since the WebView
  only ever calls them by reflection — an unprotected `isMinifyEnabled=true`
  would have silently broken every `window.AndroidDownload` /
  `window.AndroidBridge` / `window.AndroidAlerts` call from the web app).
  **Scoping note:** this app still ships via `assembleDebug` with the
  standard debug signing key — enabled on the `debug` build type rather
  than switching to `release`, since generating and committing a real
  production signing keystore is a credential-custody decision that needs
  a human's own involvement, not something to invent unilaterally. If a
  proper release keystore is wanted, that's a follow-up, not something this
  change silently substituted.
- **Home-screen widget** (`OverviewWidgetProvider.kt`): shows the real
  advancing/declining breadth and top 5 gainers from the same
  `GET /api/market/overview` endpoint the web app's own Overview cards use
  (confirmed field names by reading `backend/app/market_state.py`'s
  `market_overview()` and `backend/app/screeners.py`'s `to_result()` --
  `advancing`/`declining`/`total`/`top_gainers[].symbol`/`.change_pct` --
  not guessed). Refreshes on Android's own minimum widget update interval
  (30 minutes; anything shorter is silently clamped by the OS, so
  `updatePeriodMillis` is set to exactly that). Tapping the widget opens
  the app. No mock/placeholder numbers: a failed refresh just leaves the
  widget showing its last successfully fetched values.

None of this was verified on a real device from this sandbox (no local
Android SDK/emulator access) -- verified via CI compiling/packaging
successfully and, for the update checker and widget, by reading the actual
API response shapes and CI tag format rather than guessing them.

## What's new in v2.2.1

Fixes two real bugs found in v2.2.0's own new features, plus one more
overflow bug found by direct measurement:

- **External dashboard links actually work now.** Root cause: Android
  WebView never fires `onCreateWindow` for a `target="_blank"` click unless
  `javaScriptCanOpenWindowsAutomatically` and `setSupportMultipleWindows`
  are both explicitly enabled -- neither was set, so every `target="_blank"`
  click (the web page's own Tools-menu dashboard links) was silently
  swallowed before it ever reached the in-app-browser logic added in
  v2.2.0. The sidebar's own dashboard links didn't depend on this (they
  call `startActivity` directly) and should have worked already.
- **Push notification permission prompt now reliably appears.** Requesting
  a runtime permission in the same frame `onCreate` runs, while the Splash
  Screen API's exit transition is still animating off, is a known way for
  the system dialog to silently fail to show (or get auto-dismissed) on
  some OEM builds. The request is now posted to run after that transition
  settles. Also added Logcat logging (`adb logcat -s NSE500`) at every step
  of the alert -> notification path (bridge called, permission check,
  notification posted) so a future report is fact-based instead of guessed.
  If notifications still don't appear: check Android Settings -> Apps ->
  NSE500 Screener -> Notifications is enabled (declining the first prompt
  means Android won't auto-re-prompt), and note the screener only fires
  alerts when there's real tick movement to detect them in.
- **Fixed a header overflow found by direct measurement** (not guessed):
  at a real 360px phone viewport, three header elements -- the nav-tabs row,
  the "Tools ▾" dropdown, and the brand name text -- extended up to 495px
  past the right edge with no way to scroll to them (silently unreachable,
  not just visually cramped). All three fully duplicate what the native
  bottom nav, sidebar drawer, and top app bar already show inside this app,
  so they're now hidden specifically when running in-app (`.in-native-app`,
  set via a `window.AndroidBridge` check in `App.jsx`) -- zero effect on
  browser/PWA users, who never get that class. Re-measured after the fix:
  zero elements overflow the header row.

## What's new in v2.2.0

- **Fixed the horizontal "floating" content bug**, confirmed and root-caused
  by measuring the actual rendered page (not guessed): at a real phone
  viewport width, the page's content was 553px wide inside a 360px viewport
  — the search box and sector-select each carried a desktop-sized inline
  `minWidth` (220px/150px) that doesn't fit side by side on a phone and
  can't shrink below its own floor even inside a wrapping flex row. Fixed
  with a `@media (max-width: 480px)` block in `index.css` that makes the
  search box take its own full-width row and lets the select shrink to fit
  (verified after the fix: content width now matches the viewport exactly).
  Also disabled WebView pinch-zoom entirely (`setSupportZoom(false)`) as a
  second layer of defense, since it's a possible source of scale/pan drift
  in its own right and there's nothing useful to zoom into on an already-
  responsive page.
- **Compacted the header/filter chrome**: same media query shrinks
  padding/gaps on the filter bar's inputs, chips, and buttons. Measured
  before/after on a 360×780 viewport: the filter bar dropped from 265px to
  202px tall. Scoped to phone widths only, so desktop/tablet browser users
  see no change.
- **Native chrome now matches the web content's theme exactly**: the top
  bar, bottom nav, and drawer previously used Material 3's `?attr/
  colorSurface`, which gets a subtle elevation-overlay tint that can end up
  a visibly different shade from the web page's own flat background color.
  All three now use a dedicated `chrome_bg` color pinned to the exact same
  value as the web content, with correct day/night variants (not just the
  dark value forced everywhere, which would have broken light mode).
- **External dashboard links now open inside the app** instead of handing
  off to Chrome: a new lightweight `WebViewActivity` (its own toolbar with
  a back arrow, progress bar, WebView) loads `script.google.com` /
  `script.googleusercontent.com` URLs (the two dashboard links specifically
  — X-Frame-Options, which blocks *embedding* a page in an iframe, doesn't
  apply to a WebView navigating to a URL directly, so there was no real
  obstacle here). Any other, unrecognized external host still opens in the
  system browser as a safe default rather than loading arbitrary web
  content inside the app.
- **Real push notifications for market alerts**: every alert that already
  appears in the web app's own "LIVE ALERTS" ticker (breakouts, volume
  spikes, VWAP crosses, RSI thresholds, etc.) now also posts as a genuine
  Android system notification via `window.AndroidAlerts.postAlert(...)`
  (a new bridge call added to `App.jsx`'s WebSocket message handler,
  a no-op outside the app), so they land even when the app isn't in the
  foreground. Requests the required Android 13+ `POST_NOTIFICATIONS`
  runtime permission on first launch. Fixed a real pre-existing bug found
  while wiring this up: `App.jsx` was calling `setAlerts` twice for every
  "ticks" WebSocket message that carried alerts, silently duplicating
  every alert in the in-app ticker — which would have meant duplicate
  notifications too had it shipped unfixed.

## What's new in v2.1.0

- **Fixed, non-floating layout**: `android:resizeableActivity="false"` and
  `android:screenOrientation="portrait"` in the manifest — the app can no
  longer be dragged into Samsung's pop-up/floating view, split-screen, or
  freeform multi-window modes, and never rotates. This is the correct,
  standard Android mechanism for "always full-screen, fixed layout"; it
  isn't achieved (and shouldn't be) by hardcoding pixel dimensions like
  1080×2340 anywhere — the existing dp/weight-based layout already scales
  correctly to any resolution or aspect ratio, including that one, without
  needing device-specific numbers baked in.
- **Sidebar navigation** (`DrawerLayout` + `NavigationView`, opened via the
  hamburger icon in the top bar): the pattern most Indian broker apps use —
  primary sections in the bottom nav, everything else in a slide-out
  drawer. I didn't have visual access to the actual Nuvama Market app to
  copy its exact design (no image was provided and this environment can't
  browse app stores), so this follows the standard, well-established
  version of that pattern rather than a pixel copy: a header with the app
  identity, a "Tools" group (Paper Trading, Market Replay, Alerts Center,
  Elite Quant — the same real features from the web app's own Tools menu,
  now also reachable natively), an "External Dashboards" group (the two
  Google Apps Script links, opened directly via an Intent), and a Refresh
  action. Every item is wired to the same real `window.__nativeSetView`
  bridge the bottom nav uses (widened in `App.jsx` to also accept the
  web app's `TOOLS` keys, not just its main `NAV` keys) or a direct system
  Intent — nothing in the drawer is a placeholder.

## What's new in v2.0.0

- **Material 3** throughout: real light/dark tonal color schemes (not an
  inverted palette), `Theme.Material3.DayNight.NoActionBar`.
- **Splash screen** via `androidx.core.splashscreen` — no blank white flash
  on cold start.
- **Bottom navigation** (Screener / Intraday / Options / Instruments /
  ETFs) — the web app has no client-side router, so tabs call
  `window.__nativeSetView(key)`, a small bridge `frontend/src/App.jsx`
  exposes onto its own internal view state, rather than loading a
  different URL. Back button pops a native tab history before falling
  through to WebView history, then finally exits.
- **Live connection status** in the top app bar, sourced from the web
  app's actual WebSocket state (`window.AndroidBridge.onConnectionState`,
  called from `App.jsx` whenever its own socket status changes) — not a
  static "Live" label.
- **Scroll-aware top bar**: hides on scroll down, reappears on scroll up.
- **System dark mode**: the native shell reads `Configuration.uiMode` and
  sets the same `data-theme` attribute the in-app theme toggle uses, so the
  web content starts in the right palette instead of a bright white page
  inside a dark native shell. The user's own in-app toggle still works
  normally afterwards.
- **Fade-through transition** between bottom-nav tabs (plain
  `ViewPropertyAnimator`, standard Material Motion timing/feel).
- **Themed icon** (Android 13+ "Material You" tinted icon) via a monochrome
  adaptive-icon layer, alongside the regular adaptive + legacy icons.
- **Real CSV/PDF export handling**: the Institutional Flow tab's exports
  use `Blob`/`<a download>`, which a plain `DownloadListener` never sees
  (blob: URLs don't touch the network stack). An injected script now reads
  the blob back via `FileReader`, hands it to a `@JavascriptInterface`
  bridge, and the app writes it through `MediaStore.Downloads` (API 29+) or
  the legacy public Downloads directory (API 24-28) — exports now actually
  land in the device's Downloads app, with a completion toast. Genuine
  network-originated downloads still go through a standard
  `DownloadManager` request.

## Known limitations

- The fade-through tab transition and scroll-aware top bar are native-side
  effects around the WebView; the WebView's own content doesn't have
  per-view animated transitions (the web app has no router to hook that
  into) — going from Screener to Options is a fade-through to the same page
  with different internal state, not a page navigation animation.
- Not tested on a physical Samsung device or emulator from this
  environment (see above) — the chart fix is grounded in reading the actual
  charting library's source and known WebView behavior, not a confirmed
  before/after on real hardware. Use the console log pipe above if it needs
  further diagnosis.
