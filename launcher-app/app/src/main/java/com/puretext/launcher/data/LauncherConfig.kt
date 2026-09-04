package com.puretext.launcher.data

import kotlinx.serialization.Serializable

/**
 * Everything keyed by app identity: reordering, hiding, renaming, favorites
 * and grouping. Stored in [LauncherState.entries] under [AppInfo.key].
 */
@Serializable
data class AppEntry(
    val alias: String? = null,
    val hidden: Boolean = false,
    val favorite: Boolean = false,
    val groupName: String? = null,
)

@Serializable
data class AppGroup(
    val name: String,
    val collapsed: Boolean = false,
)

enum class ShortcutType { APP, WEBSITE, SYSTEM_SETTING, CONTACT }

@Serializable
data class LauncherShortcut(
    val id: String,
    val name: String,
    val type: ShortcutType,
    /** APP: an [AppInfo.key]. WEBSITE: a URL. SYSTEM_SETTING: an intent action name. CONTACT: a contact URI string. */
    val target: String,
)

enum class GestureAction { SEARCH, ALL_APPS, NOTIFICATIONS, QUICK_SETTINGS, OPEN_APP, LAUNCHER_SETTINGS, LOCK_SCREEN, NOTHING }

@Serializable
data class GestureBinding(
    val action: GestureAction = GestureAction.NOTHING,
    /** Only meaningful when [action] == OPEN_APP: an [AppInfo.key]. */
    val appKey: String? = null,
)

@Serializable
data class GestureSettings(
    val swipeUp: GestureBinding = GestureBinding(GestureAction.SEARCH),
    val swipeDown: GestureBinding = GestureBinding(GestureAction.NOTIFICATIONS),
    val swipeLeft: GestureBinding = GestureBinding(GestureAction.NOTHING),
    val swipeRight: GestureBinding = GestureBinding(GestureAction.NOTHING),
    val doubleTap: GestureBinding = GestureBinding(GestureAction.LOCK_SCREEN),
    val longPress: GestureBinding = GestureBinding(GestureAction.LAUNCHER_SETTINGS),
)

enum class GestureSlot { SWIPE_UP, SWIPE_DOWN, SWIPE_LEFT, SWIPE_RIGHT, DOUBLE_TAP, LONG_PRESS }

fun GestureSettings.binding(slot: GestureSlot): GestureBinding = when (slot) {
    GestureSlot.SWIPE_UP -> swipeUp
    GestureSlot.SWIPE_DOWN -> swipeDown
    GestureSlot.SWIPE_LEFT -> swipeLeft
    GestureSlot.SWIPE_RIGHT -> swipeRight
    GestureSlot.DOUBLE_TAP -> doubleTap
    GestureSlot.LONG_PRESS -> longPress
}

fun GestureSettings.updated(slot: GestureSlot, newBinding: GestureBinding): GestureSettings = when (slot) {
    GestureSlot.SWIPE_UP -> copy(swipeUp = newBinding)
    GestureSlot.SWIPE_DOWN -> copy(swipeDown = newBinding)
    GestureSlot.SWIPE_LEFT -> copy(swipeLeft = newBinding)
    GestureSlot.SWIPE_RIGHT -> copy(swipeRight = newBinding)
    GestureSlot.DOUBLE_TAP -> copy(doubleTap = newBinding)
    GestureSlot.LONG_PRESS -> copy(longPress = newBinding)
}

/**
 * Which app the user picked for a given typed query, and how often --
 * lets Search rank the app they always mean to the top, and (combined
 * with a confidence threshold) drive predictive auto-launch. Keyed by the
 * exact lowercased query text, not by prefix, to keep the model simple
 * and easy to reset.
 */
@Serializable
data class SearchLearning(
    val queryAppCounts: Map<String, Map<String, Int>> = emptyMap(),
)

/**
 * The full JSON-serialized part of launcher config: everything that isn't a
 * simple scalar preference (see SettingsStore for those). Kept as one
 * versioned blob so backup/export and import are a single, atomic,
 * corruption-safe operation -- see ConfigStore.
 */
@Serializable
data class LauncherState(
    val schemaVersion: Int = CURRENT_SCHEMA_VERSION,
    val appOrder: List<String> = emptyList(),
    val entries: Map<String, AppEntry> = emptyMap(),
    val groups: List<AppGroup> = emptyList(),
    val shortcuts: List<LauncherShortcut> = emptyList(),
    val gestures: GestureSettings = GestureSettings(),
    val recentApps: List<String> = emptyList(),
    val book: BookState = BookState(),
    val searchLearning: SearchLearning = SearchLearning(),
    val presets: List<StylePreset> = emptyList(),
) {
    companion object {
        const val CURRENT_SCHEMA_VERSION = 1
    }
}
