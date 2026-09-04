package com.puretext.launcher.util

import android.app.AppOpsManager
import android.app.usage.UsageStatsManager
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Process
import android.provider.Settings
import java.util.Calendar

/**
 * Today's per-app screen time -- opt-in, via the same "deep-link to a
 * special system settings screen, never self-grant" pattern already used
 * for Notification Access and Accessibility. Usage Access is an AppOps
 * grant, not a manifest permission, so there's nothing to declare.
 */
object UsageAccess {

    data class Entry(val packageName: String, val label: String, val foregroundMillis: Long)

    fun isEnabled(context: Context): Boolean = try {
        val appOps = context.getSystemService(Context.APP_OPS_SERVICE) as AppOpsManager
        val mode = appOps.checkOpNoThrow("android:get_usage_stats", Process.myUid(), context.packageName)
        mode == AppOpsManager.MODE_ALLOWED
    } catch (e: Exception) {
        false
    }

    fun openSettings(context: Context) {
        try {
            context.startActivity(Intent(Settings.ACTION_USAGE_ACCESS_SETTINGS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
        } catch (e: Exception) {
            android.util.Log.w("UsageAccess", "Could not open usage access settings", e)
        }
    }

    /** Empty (never throws) if access isn't granted, or on any OEM quirk. */
    fun todayUsage(context: Context, limit: Int = 20): List<Entry> {
        if (!isEnabled(context)) return emptyList()
        return try {
            val usm = context.getSystemService(Context.USAGE_STATS_SERVICE) as UsageStatsManager
            val end = System.currentTimeMillis()
            val start = Calendar.getInstance().apply {
                set(Calendar.HOUR_OF_DAY, 0)
                set(Calendar.MINUTE, 0)
                set(Calendar.SECOND, 0)
                set(Calendar.MILLISECOND, 0)
            }.timeInMillis
            val stats = usm.queryUsageStats(UsageStatsManager.INTERVAL_DAILY, start, end) ?: emptyList()
            val pm = context.packageManager
            stats
                .filter { it.totalTimeInForeground > 0 && it.packageName != context.packageName }
                .groupBy { it.packageName }
                .map { (pkg, entries) -> pkg to entries.sumOf { it.totalTimeInForeground } }
                .sortedByDescending { it.second }
                .take(limit)
                .map { (pkg, millis) -> Entry(pkg, appLabel(pm, pkg), millis) }
        } catch (e: Exception) {
            emptyList()
        }
    }

    private fun appLabel(pm: PackageManager, packageName: String): String = try {
        pm.getApplicationLabel(pm.getApplicationInfo(packageName, 0)).toString()
    } catch (e: Exception) {
        packageName
    }
}
