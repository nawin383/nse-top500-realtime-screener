# R8 runs for release builds now (minifyEnabled true) -- these keep the
# things R8 can't see are used because they're only reached via reflection
# or the WebView JS bridge, not a normal Kotlin call site.

# WebView -> native JS interfaces (DownloadBridge, ConnectionBridge,
# AlertsBridge in MainActivity): every method the page calls via
# window.AndroidX.method(...) must survive both class and method renaming/
# removal, or the bridge silently breaks in release builds only.
-keepclassmembers class * {
    @android.webkit.JavascriptInterface <methods>;
}

# WorkManager instantiates ListenableWorker subclasses by class name via
# reflection (WorkerFactory) -- keep AlertsWorker's name and constructor.
-keep class com.nse500.screener.AlertsWorker { <init>(...); }

# AppWidgetProvider is instantiated by the system via the manifest-declared
# class name, not a normal call site.
-keep class com.nse500.screener.AlertsWidgetProvider { *; }
