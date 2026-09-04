package com.puretext.launcher.gestures

import android.content.Context
import android.util.Log

/**
 * Expands the notification shade / quick settings the same way every other
 * text launcher does: StatusBarManager's expand methods are hidden API, so
 * this goes through reflection, guarded end-to-end -- a failure here (OEM
 * that removed the method, future Android restricting it further) degrades
 * to "gesture does nothing", never a crash.
 */
object SystemPanels {
    fun expandNotifications(context: Context): Boolean = invoke(context, "expandNotificationsPanel")

    fun expandQuickSettings(context: Context): Boolean = invoke(context, "expandSettingsPanel")

    private fun invoke(context: Context, methodName: String): Boolean = try {
        val statusBarService = context.getSystemService("statusbar")
        if (statusBarService == null) {
            false
        } else {
            val statusBarManager = Class.forName("android.app.StatusBarManager")
            val method = statusBarManager.getMethod(methodName)
            method.invoke(statusBarService)
            true
        }
    } catch (e: Exception) {
        Log.w("SystemPanels", "$methodName unavailable on this device", e)
        false
    }
}
