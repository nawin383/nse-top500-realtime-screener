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

## What's new in v3.0.0

Native-app depth beyond the WebView shell, plus real Play Store readiness --
the app was previously debug-build-only.

- **Background alert notifications.** Previously, `window.AndroidAlerts.
  postAlert(...)` only fired while the page's own JS was actually running,
  so alerts stopped the instant the app was backgrounded or killed by the
  OS -- a real gap for an app whose whole feature is market alerts.
  `AlertsWorker` (a `CoroutineWorker`, scheduled via `WorkManager.
  enqueueUniquePeriodicWork`) now polls the deployed backend's own
  `GET /api/alerts` endpoint independently of the WebView and posts
  notifications for anything new, whether or not the app is open. Stated
  plainly: `PeriodicWorkRequest`'s minimum interval is **15 minutes** -- a
  WorkManager/JobScheduler platform floor, not a choice made here -- so
  this is "alerts survive the app being backgrounded or killed", not
  "real-time in the background"; the in-app ticker is still the real-time
  path while the app is actually open. On first-ever run the worker seeds
  its "already seen" set silently instead of replaying the existing alert
  history as a burst of new notifications.
- **Per-category notification channels** (`NotificationChannels.kt`):
  breakouts, volume alerts, technical alerts (VWAP/RSI/momentum), and
  everything else are now four separate channels instead of one "Market
  Alerts" channel -- a user who only cares about breakouts can mute volume
  noise from Android's own per-channel settings, which wasn't possible
  before.
- **Notification tap deep links** (`nse500://symbol/<SYMBOL>`, declared on
  `MainActivity`'s manifest intent-filter): tapping an alert notification
  (foreground or background) now opens straight to the screener with that
  symbol already typed into its search box, via a new
  `window.__nativeSetSearch` bridge in `App.jsx` (same pattern as the
  existing `window.__nativeSetView`) -- previously a notification tap just
  opened the app to whatever state it happened to be in.
- **Home screen widget** (`AlertsWidgetProvider.kt` + `widget_alerts.xml`):
  shows the last-seen market status and the 3 most recent alerts. It has no
  update schedule of its own (`updatePeriodMillis="0"`) -- it's refreshed by
  `AlertsWorker` after every poll, so there's exactly one network poller
  feeding both notifications and the widget, not two drifting out of sync.
  A refresh button forces an immediate one-off poll rather than waiting for
  the next scheduled run.
- **Offline handling.** A failed main-frame load (no network, or the Render
  backend cold-starting) previously just left a blank page with no
  explanation. `MainActivity` now shows a native "You're offline" screen
  with a Retry button, and a `ConnectivityManager.NetworkCallback`
  auto-reloads the instant connectivity actually comes back rather than
  waiting for the user to notice and tap Retry themselves.
- **Optional biometric App Lock** (drawer toggle, `androidx.biometric`):
  prompts for fingerprint/face/device credential at cold start and whenever
  the whole app process (not just this Activity -- via
  `ProcessLifecycleOwner`, so returning from the in-app browser doesn't
  spuriously re-lock) returns to the foreground. Skipped silently on
  devices with no enrolled biometric/credential, since this is a
  convenience lock, not the app's real security boundary.
- **Play Store readiness**: `compileSdk`/`targetSdk` bumped to 35, R8
  minification + resource shrinking turned on for release builds (was
  entirely off), and a real release signing config wired up. The signing
  config is sourced from an untracked `android-app/keystore.properties`
  file or `ANDROID_RELEASE_KEYSTORE`/`_KEYSTORE_PASSWORD`/`_KEY_ALIAS`/
  `_KEY_PASSWORD` env vars -- **no keystore is or should ever be committed
  to this repo**. Without either, `assembleRelease` still falls back to
  debug signing (same as before), so nothing about the existing debug-APK
  release flow changes; real Play signing is a drop-in the moment real
  credentials exist. Because R8 is now on, `proguard-rules.pro` explicitly
  keeps every `@JavascriptInterface`-annotated bridge method (R8 can't see
  the WebView calling into them, since that happens from JS, not Kotlin) --
  without this, minified release builds would have silently broken the
  download bridge, connection-status bridge, and alerts bridge.
- **Instrumented smoke tests** (`androidTest/…/MainActivityTest.kt`) for
  the native chrome (bottom nav, drawer, toolbar) using Espresso -- CI now
  also runs `assembleDebugAndroidTest` to prove they at least compile
  against the current code (there's no emulator in that job to actually run
  them; that needs `connectedAndroidTest` on a device/emulator).
- **Dependabot** (`.github/dependabot.yml`) now watches this module's
  Gradle dependencies and the repo's GitHub Actions workflows weekly.

### Setting up real release signing (optional)

Only needed for an actual Play Store / signed release build -- everything
above works and CI stays green without this.

```properties
# android-app/keystore.properties (untracked -- see .gitignore)
storeFile=/absolute/path/to/release.jks
storePassword=...
keyAlias=...
keyPassword=...
```

Or, for CI, the equivalent `ANDROID_RELEASE_KEYSTORE` (a path the workflow
writes the secret keystore file to), `ANDROID_RELEASE_KEYSTORE_PASSWORD`,
`ANDROID_RELEASE_KEY_ALIAS`, `ANDROID_RELEASE_KEY_PASSWORD` environment
variables.

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
- **Background alerts poll at most every 15 minutes** (see v3.0.0 above) —
  a WorkManager/JobScheduler platform floor, not a tunable setting. Real-time
  alerts still require the app open in the foreground.
- **App Lock is a convenience lock, not a real security boundary** — it
  gates the native UI, not the backend session/data itself, and is skipped
  entirely on devices with no enrolled biometric or device credential.
- The v3.0.0 native features above (`AlertsWorker`, `AlertsWidgetProvider`,
  the offline screen, App Lock) were implemented and CI-verified to compile
  and package correctly, but **not verified on a real device or emulator**
  from this environment (same constraint as the chart fix above — no
  device/emulator available here). `assembleDebugAndroidTest` proves the
  instrumented smoke tests compile; it doesn't run them.
