package com.puretext.launcher.gestures

import android.accessibilityservice.AccessibilityService
import android.content.Context
import android.content.Intent
import android.os.Build
import android.provider.Settings
import android.text.TextUtils
import android.view.accessibility.AccessibilityEvent

/**
 * Backs the optional "lock screen" gesture. Android gives no other way for
 * a launcher (not a device-admin app) to lock the screen. The user must
 * explicitly enable this in system Accessibility settings -- see
 * [isEnabled] / the Advanced settings deep link -- it is never self-granted.
 * Never crashes the launcher: [lock] simply returns false if the service
 * isn't connected or the OS is too old for GLOBAL_ACTION_LOCK_SCREEN (API 28+).
 */
class LockAccessibilityService : AccessibilityService() {

    override fun onServiceConnected() {
        super.onServiceConnected()
        instance = this
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        // Intentionally empty: this service only performs a global action,
        // it never inspects window content or events.
    }

    override fun onInterrupt() {}

    override fun onUnbind(intent: Intent?): Boolean {
        instance = null
        return super.onUnbind(intent)
    }

    companion object {
        @Volatile
        private var instance: LockAccessibilityService? = null

        fun isEnabled(context: Context): Boolean {
            val enabledServices = Settings.Secure.getString(
                context.contentResolver,
                Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES,
            ) ?: return false
            val expected = "${context.packageName}/${LockAccessibilityService::class.java.name}"
            val splitter = TextUtils.SimpleStringSplitter(':')
            splitter.setString(enabledServices)
            for (name in splitter) {
                if (name.equals(expected, ignoreCase = true)) return true
            }
            return false
        }

        fun openAccessibilitySettings(context: Context) {
            try {
                context.startActivity(
                    Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK),
                )
            } catch (e: Exception) {
                android.util.Log.w("LockAccessibilityService", "Could not open accessibility settings", e)
            }
        }

        /** Best-effort lock. False means the gesture silently does nothing. */
        fun lock(): Boolean {
            val service = instance ?: return false
            return try {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
                    service.performGlobalAction(AccessibilityService.GLOBAL_ACTION_LOCK_SCREEN)
                } else {
                    false
                }
            } catch (e: Exception) {
                false
            }
        }
    }
}
