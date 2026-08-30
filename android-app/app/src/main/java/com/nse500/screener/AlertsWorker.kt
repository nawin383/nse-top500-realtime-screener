package com.nse500.screener

import android.content.Context
import android.content.Intent
import android.content.SharedPreferences
import android.net.Uri
import android.util.Log
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.work.BackoffPolicy
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.util.concurrent.TimeUnit

/**
 * Polls the deployed backend for new alerts and market status, and posts a
 * real notification for anything new -- unlike window.AndroidAlerts.postAlert
 * (see MainActivity), this runs whether or not the app is open or even in
 * memory, because it's driven by WorkManager's own job scheduling, not the
 * page's live WebSocket. Also refreshes the home screen widget's cached data
 * on every run so the widget and notifications always agree.
 *
 * Real limitation, stated plainly: PeriodicWorkRequest's minimum interval is
 * 15 minutes (a WorkManager/JobScheduler platform floor, not a choice made
 * here) -- this is "alerts survive the app being backgrounded or killed",
 * not "real-time in the background". The in-app ticker (AndroidAlerts
 * bridge) is still the real-time path while the app is open.
 */
class AlertsWorker(appContext: Context, params: WorkerParameters) : CoroutineWorker(appContext, params) {

    companion object {
        private const val TAG = "NSE500Worker"
        private const val UNIQUE_PERIODIC_NAME = "alerts_poll_periodic"
        private const val UNIQUE_ONE_TIME_NAME = "alerts_poll_once"
        private const val PREFS_NAME = "nse500_alerts"
        private const val KEY_SEEN_IDS = "seen_alert_ids"
        private const val KEY_SEEDED = "seeded_once"
        private const val KEY_MARKET_LABEL = "market_label"
        private const val KEY_WIDGET_LINES = "widget_lines"
        private const val MAX_SEEN_IDS = 300
        private const val MAX_NOTIFICATIONS_PER_RUN = 5

        fun schedulePeriodic(context: Context) {
            val constraints = Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED)
                .build()
            val request = PeriodicWorkRequestBuilder<AlertsWorker>(15, TimeUnit.MINUTES)
                .setConstraints(constraints)
                .setBackoffCriteria(BackoffPolicy.LINEAR, androidx.work.WorkRequest.MIN_BACKOFF_MILLIS, TimeUnit.MILLISECONDS)
                .build()
            WorkManager.getInstance(context).enqueueUniquePeriodicWork(
                UNIQUE_PERIODIC_NAME, ExistingPeriodicWorkPolicy.KEEP, request,
            )
        }

        /** Used by the widget's manual refresh button for an immediate poll. */
        fun enqueueOneTime(context: Context) {
            val constraints = Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED)
                .build()
            val request = OneTimeWorkRequestBuilder<AlertsWorker>()
                .setConstraints(constraints)
                .build()
            WorkManager.getInstance(context).enqueueUniqueWork(
                UNIQUE_ONE_TIME_NAME, ExistingWorkPolicy.REPLACE, request,
            )
        }

        fun widgetLines(context: Context): List<String> {
            val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            val raw = prefs.getString(KEY_WIDGET_LINES, null) ?: return emptyList()
            return try {
                val arr = JSONArray(raw)
                (0 until arr.length()).map { arr.getString(it) }
            } catch (e: Exception) {
                emptyList()
            }
        }

        fun marketLabel(context: Context): String? =
            context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE).getString(KEY_MARKET_LABEL, null)
    }

    private val prefs: SharedPreferences
        get() = applicationContext.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)

    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        try {
            val marketLabel = fetchMarketLabel()
            val alerts = fetchAlerts()
            if (marketLabel != null) prefs.edit().putString(KEY_MARKET_LABEL, marketLabel).apply()
            processAlerts(alerts)
            AlertsWidgetProvider.updateAllWidgets(applicationContext)
            Result.success()
        } catch (e: Exception) {
            Log.w(TAG, "Alert poll failed", e)
            Result.retry()
        }
    }

    private fun httpGet(path: String): String {
        val url = URL(Nse500Config.HOME_URL.trimEnd('/') + path)
        val conn = url.openConnection() as HttpURLConnection
        conn.connectTimeout = 10_000
        conn.readTimeout = 10_000
        conn.requestMethod = "GET"
        try {
            if (conn.responseCode !in 200..299) throw java.io.IOException("HTTP ${conn.responseCode} for $path")
            return conn.inputStream.bufferedReader().use { it.readText() }
        } finally {
            conn.disconnect()
        }
    }

    private fun fetchMarketLabel(): String? = try {
        JSONObject(httpGet("/api/market/status")).optString("label", null)
    } catch (e: Exception) {
        Log.w(TAG, "market/status poll failed", e)
        null
    }

    private fun fetchAlerts(): List<JSONObject> {
        val body = JSONObject(httpGet("/api/alerts?limit=20"))
        val data = body.optJSONArray("data") ?: JSONArray()
        return (0 until data.length()).map { data.getJSONObject(it) }
    }

    private fun processAlerts(alerts: List<JSONObject>) {
        val seenIds = prefs.getStringSet(KEY_SEEN_IDS, emptySet())?.toMutableSet() ?: mutableSetOf()
        val firstRun = !prefs.getBoolean(KEY_SEEDED, false)

        // Newest first (the API already returns them that way) so a capped
        // MAX_NOTIFICATIONS_PER_RUN keeps the most recent ones, not the
        // oldest, if more than that fired in one 15-minute window.
        val newAlerts = alerts.filter { it.optString("id") !in seenIds }

        if (!firstRun) {
            for (alert in newAlerts.take(MAX_NOTIFICATIONS_PER_RUN)) {
                postAlertNotification(alert)
            }
        } // else: first run ever -- seed the seen set silently, don't replay history as new notifications

        for (alert in alerts) seenIds.add(alert.optString("id"))
        val trimmed = if (seenIds.size > MAX_SEEN_IDS) {
            // Order isn't preserved by a Set; this just bounds growth, it
            // doesn't need to evict the *oldest* specifically.
            seenIds.toList().takeLast(MAX_SEEN_IDS).toMutableSet()
        } else seenIds

        prefs.edit()
            .putStringSet(KEY_SEEN_IDS, trimmed)
            .putBoolean(KEY_SEEDED, true)
            .putString(KEY_WIDGET_LINES, buildWidgetLinesJson(alerts.take(3)))
            .apply()
    }

    private fun buildWidgetLinesJson(alerts: List<JSONObject>): String {
        val arr = JSONArray()
        for (alert in alerts) {
            val symbol = alert.optString("symbol", "?")
            val message = alert.optString("message", "")
            arr.put("$symbol · $message")
        }
        return arr.toString()
    }

    private fun postAlertNotification(alert: JSONObject) {
        val context = applicationContext
        val symbol = alert.optString("symbol", "")
        val type = alert.optString("type", "")
        val message = alert.optString("message", "$symbol $type")
        val id = alert.optString("id", "")

        val hasPermission = androidx.core.content.ContextCompat.checkSelfPermission(
            context, android.Manifest.permission.POST_NOTIFICATIONS,
        ) == android.content.pm.PackageManager.PERMISSION_GRANTED
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.TIRAMISU && !hasPermission) return

        // MainActivity is the app's own root/launcher activity, so a plain
        // PendingIntent targeting it is enough -- see MainActivity's
        // postAlertNotification for why TaskStackBuilder isn't used here.
        val deepLinkIntent = Intent(Intent.ACTION_VIEW, Uri.parse("nse500://symbol/$symbol")).apply {
            setPackage(context.packageName)
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        val pendingIntent = android.app.PendingIntent.getActivity(
            context, id.hashCode(), deepLinkIntent,
            android.app.PendingIntent.FLAG_UPDATE_CURRENT or android.app.PendingIntent.FLAG_IMMUTABLE,
        )

        val channelId = NotificationChannels.channelIdForAlertType(type)
        val notification = NotificationCompat.Builder(context, channelId)
            .setSmallIcon(R.drawable.ic_launcher_monochrome)
            .setContentTitle("$symbol · ${type.replace('_', ' ')}")
            .setContentText(message)
            .setStyle(NotificationCompat.BigTextStyle().bigText(message))
            .setPriority(NotificationCompat.PRIORITY_DEFAULT)
            .setAutoCancel(true)
            .setContentIntent(pendingIntent)
            .build()
        try {
            val notifId = 3000 + (id.hashCode() and 0xFFFF)
            NotificationManagerCompat.from(context).notify(notifId, notification)
        } catch (e: SecurityException) {
            Log.w(TAG, "Background notification post denied by system", e)
        }
    }
}
