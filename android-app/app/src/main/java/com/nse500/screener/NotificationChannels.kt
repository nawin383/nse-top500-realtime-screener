package com.nse500.screener

import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.os.Build

/**
 * One notification channel per alert *category* (not one generic "Market
 * Alerts" channel for everything) so a user who only cares about breakouts
 * can mute volume-spike noise, etc., from Android's own per-channel
 * settings -- without this, muting one alert type mutes all of them.
 * Shared between MainActivity (foreground alerts via the AndroidAlerts JS
 * bridge) and AlertsWorker (background poll) so both post through the same
 * channel for a given alert type.
 */
object NotificationChannels {
    const val BREAKOUT = "market_alerts_breakout"
    const val VOLUME = "market_alerts_volume"
    const val TECHNICAL = "market_alerts_technical"
    const val GENERAL = "market_alerts_general"

    fun channelIdForAlertType(type: String): String = when (type) {
        "breakout", "breakdown", "day_high", "day_low" -> BREAKOUT
        "volume_spike", "unusual_volume" -> VOLUME
        "vwap_cross", "momentum_acceleration", "rsi_threshold" -> TECHNICAL
        else -> GENERAL // pct_movement and any future/unknown alert type
    }

    fun createAll(context: Context) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        val channels = listOf(
            NotificationChannel(
                BREAKOUT, context.getString(R.string.notif_channel_breakout_name), NotificationManager.IMPORTANCE_DEFAULT,
            ).apply { description = context.getString(R.string.notif_channel_breakout_desc) },
            NotificationChannel(
                VOLUME, context.getString(R.string.notif_channel_volume_name), NotificationManager.IMPORTANCE_DEFAULT,
            ).apply { description = context.getString(R.string.notif_channel_volume_desc) },
            NotificationChannel(
                TECHNICAL, context.getString(R.string.notif_channel_technical_name), NotificationManager.IMPORTANCE_DEFAULT,
            ).apply { description = context.getString(R.string.notif_channel_technical_desc) },
            NotificationChannel(
                GENERAL, context.getString(R.string.notif_channel_general_name), NotificationManager.IMPORTANCE_DEFAULT,
            ).apply { description = context.getString(R.string.notif_channel_general_desc) },
        )
        manager.createNotificationChannels(channels)
    }
}
