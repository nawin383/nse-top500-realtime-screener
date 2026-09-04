# Pure Launcher

A minimalist, text-only Android home-screen launcher: black-and-white only,
no app icons anywhere, deeply customizable underneath. Independent Gradle
project, unrelated to the NSE screener app in `android-app/` — it just lives
in the same repository.

"Zero visual noise. Maximum control. Text is the interface."

## What it does

- Replaces your phone's home screen. Installed apps show as plain text; tap
  a name to launch it. No icons, no colors beyond pure black/white, no
  Material theming.
- **Home**: clock, date, optional battery percentage, your favorite apps in
  the order you set.
- **Search**: swipe up (configurable) for instant text search across app
  names, aliases, and package names, plus your shortcuts and recent apps.
- **Apps**: show/hide apps, reorder favorites, rename any app's displayed
  name, group apps under text headers.
- **Typography / Layout**: font family, weight, case, letter/line spacing,
  per-element text sizes, margins, spacing, alignment, vertical position —
  with a live preview.
- **Gestures**: swipe up/down/left/right, double tap, and long press each
  map to Search, All Apps, Notifications, Quick Settings, a specific app,
  Launcher Settings, Lock Screen (optional, via Accessibility), or nothing.
- **Shortcuts**: named text links to an app, a website, a system settings
  screen, or a contact.
- **Backup**: export/import everything as one JSON file via the system file
  picker (Storage Access Framework) — no storage permission needed.
- **Advanced**: five separate resets (Appearance, Gestures, App Layout,
  Launcher, Everything), each behind a confirm dialog.

Local-first: no analytics, no tracking, no ads, no network access at all.
The only non-default permission is `EXPAND_STATUS_BAR` (normal-protection,
auto-granted), used solely for the optional notification-shade/quick-settings
gestures.

## Getting the APK

Every push to `launcher-app/**` (or a manual run) builds a debug APK via
`.github/workflows/launcher-apk.yml` and:

1. **Attaches it to a GitHub Release** — go to the repo's **Releases** page
   and grab the latest `launcher-v*` release.
2. Also uploads it as a workflow **Actions artifact** (`pure-launcher-debug-apk`).

On your phone: download the `.apk`, open it (Android will ask to allow
"install unknown apps" — expected outside the Play Store; this is a debug
build, not signed for the Play Store), then set it as your default launcher
from the app's own onboarding, or Settings > Home app.

## Building locally

Requires the Android SDK (Android Studio, or `cmdline-tools` +
`platform-tools` + `build-tools;34.0.0` + `platforms;android-34`) and a
`local.properties` pointing `sdk.dir` at it.

```
./gradlew assembleDebug
```

Output: `app/build/outputs/apk/debug/app-debug.apk`.

## Architecture

- Kotlin + Jetpack Compose (Foundation only — deliberately no Material
  dependency, so there's no default colored theme to accidentally pull in).
- Single Activity (`MainActivity`), a small hand-rolled back-stack router
  (`ui/navigation/Router.kt`) instead of androidx.navigation — this app has
  ~20 screens with no deep linking and no complex argument passing, so a
  full navigation graph would be pure overhead.
- Persistence: two DataStore Preferences-backed stores — `SettingsStore`
  for scalar settings (one key per field, so a partial write can't corrupt
  fields it didn't touch) and `ConfigStore` for the app ordering / hidden /
  favorites / groups / shortcuts / gestures state, serialized as one
  versioned JSON blob via kotlinx.serialization. Every read falls back to
  safe defaults — corrupted DataStore files, unknown enum values, and
  malformed imported backups never crash the app.
- `AppRepository` owns every `PackageManager` call, wrapped defensively; a
  manifest-registered `PackageChangeReceiver` keeps the app list correct
  across install/uninstall/update without a restart.
- Package visibility via a `<queries>` manifest declaration matching the
  launcher intent filter — no `QUERY_ALL_PACKAGES` permission.
