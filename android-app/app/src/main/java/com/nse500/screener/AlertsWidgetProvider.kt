package com.nse500.screener

import android.app.PendingIntent
import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetProvider
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.view.View
import android.widget.RemoteViews
import androidx.core.content.ContextCompat

/**
 * Home screen widget showing the last-seen market status and most recent
 * alerts. Deliberately has no update schedule of its own -- AlertsWorker's
 * periodic background poll (see its doc comment) writes the data this
 * widget reads, and calls updateAllWidgets() after every poll, so there's
 * exactly one network poller feeding both notifications and the widget
 * rather than two independent ones drifting out of sync.
 */
class AlertsWidgetProvider : AppWidgetProvider() {

    companion object {
        private const val ACTION_REFRESH = "com.nse500.screener.action.WIDGET_REFRESH"

        fun updateAllWidgets(context: Context) {
            val manager = AppWidgetManager.getInstance(context)
            val ids = manager.getAppWidgetIds(ComponentName(context, AlertsWidgetProvider::class.java))
            val views = buildRemoteViews(context)
            for (id in ids) manager.updateAppWidget(id, views)
        }

        private fun buildRemoteViews(context: Context): RemoteViews {
            val views = RemoteViews(context.packageName, R.layout.widget_alerts)
            // ic_side_refresh (like the rest of this app's side-menu icons)
            // is a plain white vector, normally tinted by NavigationView's
            // own theme-driven itemIconTint -- a RemoteViews ImageButton has
            // no theme to tint it automatically, so without this it would
            // render as invisible white-on-near-white on the light widget
            // background.
            views.setInt(R.id.widget_refresh, "setColorFilter", ContextCompat.getColor(context, R.color.widget_text_secondary))
            val label = AlertsWorker.marketLabel(context)
            views.setTextViewText(R.id.widget_status, label ?: context.getString(R.string.status_connecting))

            val lines = AlertsWorker.widgetLines(context)
            val lineIds = intArrayOf(R.id.widget_line1, R.id.widget_line2, R.id.widget_line3)
            for ((i, viewId) in lineIds.withIndex()) {
                if (i < lines.size) {
                    views.setTextViewText(viewId, lines[i])
                    views.setViewVisibility(viewId, View.VISIBLE)
                } else {
                    views.setViewVisibility(viewId, View.GONE)
                }
            }
            views.setViewVisibility(R.id.widget_empty, if (lines.isEmpty()) View.VISIBLE else View.GONE)

            val openAppIntent = Intent(context, MainActivity::class.java)
            val openAppPending = PendingIntent.getActivity(
                context, 0, openAppIntent,
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
            )
            views.setOnClickPendingIntent(R.id.widget_root, openAppPending)

            val refreshIntent = Intent(context, AlertsWidgetProvider::class.java).apply { action = ACTION_REFRESH }
            val refreshPending = PendingIntent.getBroadcast(
                context, 0, refreshIntent,
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
            )
            views.setOnClickPendingIntent(R.id.widget_refresh, refreshPending)

            return views
        }
    }

    override fun onUpdate(context: Context, appWidgetManager: AppWidgetManager, appWidgetIds: IntArray) {
        val views = buildRemoteViews(context)
        for (id in appWidgetIds) appWidgetManager.updateAppWidget(id, views)
        // A newly-placed widget should show real data right away rather
        // than waiting for AlertsWorker's next scheduled 15-minute run.
        AlertsWorker.enqueueOneTime(context)
    }

    override fun onReceive(context: Context, intent: Intent) {
        super.onReceive(context, intent)
        if (intent.action == ACTION_REFRESH) {
            AlertsWorker.enqueueOneTime(context)
        }
    }
}
