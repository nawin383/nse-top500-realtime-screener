package com.puretext.launcher.data

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.provider.Settings
import android.util.Log
import com.puretext.launcher.util.Torch

/** One "universal command" typeable in Search -- e.g. typing "wifi" jumps straight to Wi-Fi settings. */
data class SearchCommand(
    val keyword: String,
    val label: String,
    val run: (Context) -> Unit,
)

object SearchCommands {
    val ALL: List<SearchCommand> = listOf(
        settingsCommand("wifi", "Wi-Fi Settings", Settings.ACTION_WIFI_SETTINGS),
        settingsCommand("bluetooth", "Bluetooth Settings", Settings.ACTION_BLUETOOTH_SETTINGS),
        settingsCommand("airplane", "Airplane Mode Settings", Settings.ACTION_AIRPLANE_MODE_SETTINGS),
        settingsCommand("battery", "Battery Settings", Settings.ACTION_BATTERY_SAVER_SETTINGS),
        settingsCommand("display", "Display Settings", Settings.ACTION_DISPLAY_SETTINGS),
        settingsCommand("sound", "Sound Settings", Settings.ACTION_SOUND_SETTINGS),
        settingsCommand("storage", "Storage Settings", Settings.ACTION_INTERNAL_STORAGE_SETTINGS),
        settingsCommand("apps", "App Settings", Settings.ACTION_APPLICATION_SETTINGS),
        settingsCommand("date", "Date & Time Settings", Settings.ACTION_DATE_SETTINGS),
        settingsCommand("location", "Location Settings", Settings.ACTION_LOCATION_SOURCE_SETTINGS),
        settingsCommand("accessibility", "Accessibility Settings", Settings.ACTION_ACCESSIBILITY_SETTINGS),
        settingsCommand("notifications", "Notification Access Settings", Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS),
        settingsCommand("settings", "All Settings", Settings.ACTION_SETTINGS),
        SearchCommand("torch on", "Turn On Flashlight") { Torch.toggle(it, forceOn = true) },
        SearchCommand("torch off", "Turn Off Flashlight") { Torch.toggle(it, forceOn = false) },
        SearchCommand("torch", "Toggle Flashlight") { Torch.toggle(it) },
    )

    /** Commands whose keyword is a prefix of (or equal to) the query, longest/most-specific match first. */
    fun matching(query: String): List<SearchCommand> {
        val q = query.trim().lowercase()
        if (q.isEmpty()) return emptyList()
        return ALL.filter { it.keyword.startsWith(q) || q.startsWith(it.keyword) }
            .sortedBy { kotlin.math.abs(it.keyword.length - q.length) }
    }

    private fun settingsCommand(keyword: String, label: String, action: String): SearchCommand =
        SearchCommand(keyword, label) { context ->
            try {
                context.startActivity(Intent(action).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
            } catch (e: Exception) {
                Log.w("SearchCommands", "Could not open $action", e)
            }
        }
}

/** "search bitcoin" -> hands off to the user's default browser/search app; makes no network call from this app itself. */
fun runWebSearch(context: Context, query: String) {
    try {
        val intent = Intent(Intent.ACTION_WEB_SEARCH).putExtra("query", query)
        if (intent.resolveActivity(context.packageManager) != null) {
            context.startActivity(intent)
        } else {
            context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse("https://www.google.com/search?q=${Uri.encode(query)}")).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
        }
    } catch (e: Exception) {
        Log.w("SearchCommands", "Could not run web search", e)
    }
}
