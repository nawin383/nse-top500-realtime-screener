package com.puretext.launcher.data

import kotlinx.serialization.Serializable

enum class ThemeStyle { BLACK, WHITE }
enum class FontFamilyOption { SANS, SERIF, MONOSPACE }
enum class TextWeight { REGULAR, MEDIUM, BOLD }
enum class TextCase { NORMAL, UPPERCASE, LOWERCASE, CAPITALIZED }
enum class HomeAlignment { START, CENTER, END }
enum class VerticalPosition { TOP, CENTER, BOTTOM }
enum class DatePreset { LONG, SHORT, NUMERIC, ISO }

/**
 * Every scalar (non-list, non-map) preference. Persisted field-by-field in
 * DataStore (see SettingsStore) but also serialized whole for backup/export
 * -- so every field needs a safe default and every enum a fallback so an
 * old or hand-edited backup never crashes deserialization.
 */
@Serializable
data class AppSettings(
    val schemaVersion: Int = CURRENT_SCHEMA_VERSION,
    val onboardingCompleted: Boolean = false,

    // Appearance
    val theme: ThemeStyle = ThemeStyle.BLACK,
    val trueAmoled: Boolean = true,
    val animationsEnabled: Boolean = true,

    // Typography
    val fontFamily: FontFamilyOption = FontFamilyOption.SANS,
    val fontWeight: TextWeight = TextWeight.REGULAR,
    val textCase: TextCase = TextCase.NORMAL,
    val letterSpacingSp: Float = 0f,
    val lineSpacingMultiplier: Float = 1f,
    val clockTextSizeSp: Int = 56,
    val dateTextSizeSp: Int = 16,
    val appTextSizeSp: Int = 20,
    val secondaryTextSizeSp: Int = 14,

    // Layout
    val homeAlignment: HomeAlignment = HomeAlignment.START,
    val verticalPosition: VerticalPosition = VerticalPosition.CENTER,
    val marginTopDp: Int = 24,
    val marginBottomDp: Int = 24,
    val marginHorizontalDp: Int = 28,
    val appSpacingDp: Int = 14,
    val clockDateSpacingDp: Int = 4,
    val dateAppsSpacingDp: Int = 32,
    val compactLayout: Boolean = false,

    // Clock
    val clockEnabled: Boolean = true,
    val clock24Hour: Boolean = true,
    val clockShowSeconds: Boolean = false,

    // Date
    val dateEnabled: Boolean = true,
    val datePreset: DatePreset = DatePreset.LONG,

    // Optional home info
    val batteryEnabled: Boolean = false,

    // Search
    val searchAutoKeyboard: Boolean = true,
    val searchIncludeHidden: Boolean = false,
    val searchByPackageName: Boolean = true,

    // Behavior
    val statusBarVisible: Boolean = true,
    val recentAppsEnabled: Boolean = true,

    // Notifications (optional info item; actual access is a live system
    // permission check, this only reflects whether the user turned the
    // home-screen item on)
    val notificationCountEnabled: Boolean = false,
) {
    companion object {
        const val CURRENT_SCHEMA_VERSION = 1
    }
}

/** The full backup payload: scalar settings + the list/map config blob. */
@Serializable
data class LauncherBackup(
    val backupVersion: Int = CURRENT_BACKUP_VERSION,
    val settings: AppSettings = AppSettings(),
    val state: LauncherState = LauncherState(),
) {
    companion object {
        const val CURRENT_BACKUP_VERSION = 1
    }
}
