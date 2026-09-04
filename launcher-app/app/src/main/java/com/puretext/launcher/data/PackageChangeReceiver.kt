package com.puretext.launcher.data

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import com.puretext.launcher.LauncherApplication
import kotlinx.coroutines.launch

/**
 * Keeps the app list correct across install/uninstall/update without the
 * user ever having to restart the launcher. Registered in the manifest --
 * PACKAGE_ADDED/REMOVED/REPLACED are exempt from the API 26+ implicit
 * broadcast restrictions, so this still fires from a cold process.
 */
class PackageChangeReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val packageName = intent.data?.schemeSpecificPart ?: return
        val app = context.applicationContext as? LauncherApplication ?: return
        val pendingResult = goAsync()
        app.applicationScope.launch {
            try {
                app.appRepository.refresh()
                val isRealRemoval = intent.action == Intent.ACTION_PACKAGE_REMOVED &&
                    !intent.getBooleanExtra(Intent.EXTRA_REPLACING, false)
                if (isRealRemoval) {
                    app.configStore.pruneRemovedPackage(packageName)
                }
            } catch (e: Exception) {
                android.util.Log.w("PackageChangeReceiver", "Failed to handle package change", e)
            } finally {
                pendingResult.finish()
            }
        }
    }
}
