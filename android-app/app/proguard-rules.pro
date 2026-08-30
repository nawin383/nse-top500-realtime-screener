# JS-interface bridges (DownloadBridge/ConnectionBridge/AlertsBridge, all
# inner classes of MainActivity) are only ever invoked by the WebView via
# reflection -- invisible to R8's static call-graph analysis -- so their
# @JavascriptInterface methods must be kept explicitly, or minification
# silently strips/renames them and every window.AndroidDownload /
# window.AndroidBridge / window.AndroidAlerts call from the web app starts
# failing with no error the app itself can see.
-keepclassmembers class * {
    @android.webkit.JavascriptInterface <methods>;
}
