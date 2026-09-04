package com.puretext.launcher.gestures

import android.content.Context
import android.content.Intent
import android.provider.Settings
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow

/**
 * Backs the optional "notification count" home-screen item. Off by
 * default; the user must grant notification access in system settings --
 * see [isEnabled] / the deep link in Settings > Notifications. Every read
 * of the live notification list is guarded: a service not yet connected,
 * or an OEM quirk in [getActiveNotifications], degrades to a count of 0
 * rather than a crash.
 */
class LauncherNotificationListenerService : NotificationListenerService() {

    override fun onListenerConnected() {
        super.onListenerConnected()
        updateCount()
    }

    override fun onListenerDisconnected() {
        super.onListenerDisconnected()
        _notificationCount.value = 0
    }

    override fun onNotificationPosted(sbn: StatusBarNotification?) = updateCount()

    override fun onNotificationRemoved(sbn: StatusBarNotification?) = updateCount()

    private fun updateCount() {
        _notificationCount.value = try {
            activeNotifications?.count { !it.isOngoing } ?: 0
        } catch (e: Exception) {
            0
        }
    }

    companion object {
        private val _notificationCount = MutableStateFlow(0)
        val notificationCount = _notificationCount.asStateFlow()

        fun isEnabled(context: Context): Boolean {
            val enabled = Settings.Secure.getString(context.contentResolver, "enabled_notification_listeners")
                ?: return false
            return enabled.split(':').any { it.contains(context.packageName) }
        }

        fun openSettings(context: Context) {
            try {
                context.startActivity(
                    Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK),
                )
            } catch (e: Exception) {
                android.util.Log.w("NotificationListener", "Could not open notification access settings", e)
            }
        }
    }
}
