package com.puretext.launcher.data

import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import android.content.pm.ApplicationInfo
import android.content.pm.PackageManager
import android.net.Uri
import android.provider.Settings
import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.withContext

/**
 * Owns the installed-app snapshot. Every PackageManager call goes through
 * here so the rest of the app never touches it directly, and every call is
 * wrapped defensively -- OEM PackageManager implementations are a well
 * known source of launcher crashes (NameNotFoundException, SecurityException,
 * malformed ResolveInfo entries), so a single bad app must never take the
 * whole list down with it.
 */
class AppRepository(private val context: Context) {

    private val packageManager: PackageManager = context.packageManager

    private val _apps = MutableStateFlow<List<AppInfo>>(emptyList())
    val apps = _apps.asStateFlow()

    private val ownPackage = context.packageName

    suspend fun refresh() {
        val loaded = withContext(Dispatchers.Default) { queryInstalledApps() }
        _apps.value = loaded
    }

    @Suppress("DEPRECATION")
    private fun queryInstalledApps(): List<AppInfo> {
        return try {
            val intent = Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_LAUNCHER)
            val resolved = packageManager.queryIntentActivities(intent, 0)
            resolved.mapNotNull { info ->
                try {
                    val activityInfo = info.activityInfo ?: return@mapNotNull null
                    val pkg = activityInfo.packageName ?: return@mapNotNull null
                    if (pkg == ownPackage) return@mapNotNull null
                    val label = info.loadLabel(packageManager)?.toString()?.trim()
                        .takeUnless { it.isNullOrEmpty() } ?: pkg
                    val isSystem = (activityInfo.applicationInfo?.flags ?: 0) and
                        ApplicationInfo.FLAG_SYSTEM != 0
                    AppInfo(
                        packageName = pkg,
                        activityName = activityInfo.name ?: return@mapNotNull null,
                        label = label,
                        isSystemApp = isSystem,
                    )
                } catch (e: Exception) {
                    Log.w(TAG, "Skipping unreadable app entry", e)
                    null
                }
            }.distinctBy { it.key }.sortedBy { it.label.lowercase() }
        } catch (e: Exception) {
            Log.e(TAG, "queryIntentActivities failed", e)
            emptyList()
        }
    }

    /** Best-effort launch. Returns false on any failure so callers can react safely. */
    fun launch(app: AppInfo): Boolean {
        return try {
            val intent = Intent(Intent.ACTION_MAIN).apply {
                addCategory(Intent.CATEGORY_LAUNCHER)
                component = android.content.ComponentName(app.packageName, app.activityName)
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            context.startActivity(intent)
            true
        } catch (e: ActivityNotFoundException) {
            Log.w(TAG, "App no longer available: ${app.key}", e)
            false
        } catch (e: SecurityException) {
            Log.w(TAG, "Not allowed to launch: ${app.key}", e)
            false
        } catch (e: Exception) {
            Log.w(TAG, "Launch failed: ${app.key}", e)
            false
        }
    }

    fun openAppInfo(app: AppInfo): Boolean = try {
        val intent = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
            data = Uri.fromParts("package", app.packageName, null)
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        context.startActivity(intent)
        true
    } catch (e: Exception) {
        Log.w(TAG, "Could not open app info for ${app.packageName}", e)
        false
    }

    fun uninstall(app: AppInfo): Boolean = try {
        val intent = Intent(Intent.ACTION_DELETE).apply {
            data = Uri.fromParts("package", app.packageName, null)
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        context.startActivity(intent)
        true
    } catch (e: Exception) {
        Log.w(TAG, "Could not start uninstall for ${app.packageName}", e)
        false
    }

    companion object {
        private const val TAG = "AppRepository"
    }
}
