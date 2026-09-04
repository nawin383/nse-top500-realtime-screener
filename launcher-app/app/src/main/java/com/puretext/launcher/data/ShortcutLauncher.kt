package com.puretext.launcher.data

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.util.Log

/**
 * Resolves and launches one [LauncherShortcut]. Every branch is wrapped --
 * a shortcut pointing at an uninstalled app, a malformed URL, or a settings
 * action an OEM removed must degrade to "nothing happens", never a crash.
 */
object ShortcutLauncher {
    fun launch(context: Context, shortcut: LauncherShortcut, appRepository: AppRepository, resolveApp: (String) -> AppInfo?): Boolean = try {
        when (shortcut.type) {
            ShortcutType.APP -> {
                val app = resolveApp(shortcut.target)
                if (app != null) appRepository.launch(app) else false
            }
            ShortcutType.WEBSITE -> {
                val url = if ("://" in shortcut.target) shortcut.target else "https://${shortcut.target}"
                context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
                true
            }
            ShortcutType.SYSTEM_SETTING -> {
                context.startActivity(Intent(shortcut.target).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
                true
            }
            ShortcutType.CONTACT -> {
                context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(shortcut.target)).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
                true
            }
        }
    } catch (e: Exception) {
        Log.w("ShortcutLauncher", "Failed to launch shortcut ${shortcut.name}", e)
        false
    }
}
