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

## What's new in this version (v2.0.0)

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
