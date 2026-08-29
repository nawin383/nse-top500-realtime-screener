# NSE500 Screener — Android app

A thin native wrapper (a single WebView Activity) around the live web app at
https://nse-top500-realtime-screener-1.onrender.com/. All real functionality
lives in the deployed frontend — this project just makes it launchable as
its own app with its own icon, no browser address bar, and a working back
button, instead of being a bookmarked browser tab.

## Getting the APK

A GitHub Actions workflow (`.github/workflows/android-apk.yml`) builds a
debug APK on every push to `android-app/**` and on manual trigger:

1. Go to the repo's **Actions** tab → **Build Android APK** → run it (or
   just push a change under `android-app/`).
2. Open the finished run and download the `nse500-screener-debug-apk`
   artifact — it's a zip containing `app-debug.apk`.
3. On your Android phone: enable **Install unknown apps** for whichever app
   you use to open the file (Settings → Apps → Special access → Install
   unknown apps), then open the downloaded APK to install it.

This is a debug build (unsigned, fine for installing on your own device).
It is **not** published to the Play Store.

## Building locally

Requires the Android SDK (Android Studio, or just `cmdline-tools` +
`platform-tools` + `build-tools;34.0.0` + `platforms;android-34`) and a
`local.properties` file pointing `sdk.dir` at it — Android Studio creates
this for you automatically if you just open this folder as a project.

```
./gradlew assembleDebug
```

Output: `app/build/outputs/apk/debug/app-debug.apk`.

## What it does and doesn't do

- Loads the live site, keeps navigation inside the WebView for the app's
  own domain, and opens anything else (the external Google Apps Script
  dashboard links in the Tools menu, etc.) in the system browser instead.
- Back button navigates WebView history before exiting the app.
- Pull-to-refresh reloads the page.
- CSV/PDF export buttons in the Institutional Flow tab use browser
  `Blob`/`<a download>` APIs, which WebViews handle less reliably than a
  full browser — if a download doesn't save on your device, that's a
  WebView limitation, not a broken feature (it works in a normal mobile
  browser tab).
