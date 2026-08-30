package com.nse500.screener

import android.app.PendingIntent
import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetProvider
import android.content.Context
import android.content.Intent
import android.util.Log
import android.widget.RemoteViews
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * Home-screen widget: the same real breadth (advancing/declining) and top
 * gainers the web app's own Overview cards show, read from the live
 * GET /api/market/overview endpoint (see backend/app/api/market.py and
 * market_state.py's market_overview() for the exact real field names used
 * below -- total/advancing/declining/top_gainers[].symbol/.change_pct).
 * No placeholder/mock numbers: a failed refresh just leaves the widget
 * showing whatever it last successfully fetched.
 */
class OverviewWidgetProvider : AppWidgetProvider() {

    companion object {
        private const val TAG = "NSE500Widget"
        private const val OVERVIEW_URL =
            "https://nse-top500-realtime-screener-1.onrender.com/api/market/overview"
    }

    override fun onUpdate(context: Context, appWidgetManager: AppWidgetManager, appWidgetIds: IntArray) {
        // AppWidgetManager forbids network I/O on the receiver's own thread;
        // goAsync() keeps this BroadcastReceiver alive across the background
        // fetch instead of Android killing it as soon as onUpdate returns.
        val pendingResult = goAsync()
        Thread {
            try {
                val json = fetchOverview()
                val views = buildViews(context, json)
                for (id in appWidgetIds) appWidgetManager.updateAppWidget(id, views)
            } catch (e: Exception) {
                Log.d(TAG, "Widget refresh skipped: ${e.message}")
            } finally {
                pendingResult.finish()
            }
        }.start()
    }

    private fun fetchOverview(): JSONObject {
        val connection = URL(OVERVIEW_URL).openConnection() as HttpURLConnection
        connection.connectTimeout = 10000
        connection.readTimeout = 10000
        val body = connection.inputStream.bufferedReader().use { it.readText() }
        return JSONObject(body)
    }

    private fun buildViews(context: Context, json: JSONObject): RemoteViews {
        val views = RemoteViews(context.packageName, R.layout.widget_overview)

        val advancing = json.optInt("advancing")
        val declining = json.optInt("declining")
        val total = json.optInt("total")
        views.setTextViewText(R.id.widget_breadth, "▲ $advancing   ▼ $declining   of $total")

        val gainers = json.optJSONArray("top_gainers") ?: JSONArray()
        val lines = StringBuilder()
        for (i in 0 until minOf(gainers.length(), 5)) {
            val g = gainers.optJSONObject(i) ?: continue
            val symbol = g.optString("symbol")
            val changePct = g.optDouble("change_pct", 0.0)
            if (lines.isNotEmpty()) lines.append('\n')
            lines.append(String.format(Locale.US, "%-10s +%.2f%%", symbol, changePct))
        }
        views.setTextViewText(
            R.id.widget_gainers,
            if (lines.isEmpty()) context.getString(R.string.widget_loading) else lines.toString(),
        )

        views.setTextViewText(R.id.widget_updated, "Updated ${SimpleDateFormat("h:mm a", Locale.US).format(Date())}")

        // Tapping anywhere on the widget opens the app itself -- there's no
        // per-symbol deep link from here (the widget shows a summary, not a
        // stock list to pick from), same behavior as tapping the launcher icon.
        val openAppIntent = PendingIntent.getActivity(
            context,
            0,
            Intent(context, MainActivity::class.java),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        views.setOnClickPendingIntent(R.id.widget_root, openAppIntent)

        return views
    }
}
