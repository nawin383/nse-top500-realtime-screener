package com.puretext.launcher.gestures

import android.content.Context
import android.content.Intent
import android.provider.Settings
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import java.lang.ref.WeakReference
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow

/**
 * Backs the optional "notification count" home-screen item and the
 * in-launcher Notifications screen. Off by default; the user must grant
 * notification access in system settings -- see [isEnabled] / the deep
 * link in Settings > Notifications. Every read of the live notification
 * list is guarded: a service not yet connected, or an OEM quirk in
 * [getActiveNotifications], degrades to an empty list rather than a crash.
 */
class LauncherNotificationListenerService : NotificationListenerService() {

    override fun onListenerConnected() {
        super.onListenerConnected()
        instanceRef = WeakReference(this)
        refresh()
    }

    override fun onListenerDisconnected() {
        super.onListenerDisconnected()
        instanceRef = null
        _notificationCount.value = 0
        _notifications.value = emptyList()
    }

    override fun onNotificationPosted(sbn: StatusBarNotification?) = refresh()

    override fun onNotificationRemoved(sbn: StatusBarNotification?) = refresh()

    private fun refresh() {
        val list = try {
            activeNotifications?.filter { !it.isOngoing }?.sortedByDescending { it.postTime } ?: emptyList()
        } catch (e: Exception) {
            emptyList()
        }
        _notificationCount.value = list.size
        _notifications.value = list
    }

    companion object {
        private var instanceRef: WeakReference<LauncherNotificationListenerService>? = null

        private val _notificationCount = MutableStateFlow(0)
        val notificationCount = _notificationCount.asStateFlow()

        /** Every active, non-ongoing notification, newest first -- empty whenever the service isn't connected. */
        private val _notifications = MutableStateFlow<List<StatusBarNotification>>(emptyList())
        val notifications = _notifications.asStateFlow()

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

        /** No-op if the service isn't connected or the key is already gone. */
        fun dismiss(key: String) {
            try {
                instanceRef?.get()?.cancelNotification(key)
            } catch (e: Exception) {
                android.util.Log.w("NotificationListener", "Could not dismiss $key", e)
            }
        }

        fun dismissAll() {
            try {
                instanceRef?.get()?.cancelAllNotifications()
            } catch (e: Exception) {
                android.util.Log.w("NotificationListener", "Could not dismiss all notifications", e)
            }
        }

        /** Runs the notification's own tap action, same as tapping it in the system shade. */
        fun open(sbn: StatusBarNotification) {
            try {
                sbn.notification.contentIntent?.send()
            } catch (e: Exception) {
                android.util.Log.w("NotificationListener", "Could not open notification", e)
            }
        }

        fun appLabel(context: Context, packageName: String): String = try {
            val pm = context.packageManager
            pm.getApplicationLabel(pm.getApplicationInfo(packageName, 0)).toString()
        } catch (e: Exception) {
            packageName
        }
    }
}
