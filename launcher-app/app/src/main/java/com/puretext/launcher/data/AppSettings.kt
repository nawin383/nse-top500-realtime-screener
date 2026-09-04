package com.puretext.launcher.data

import kotlinx.serialization.Serializable

enum class ThemeStyle { BLACK, WHITE }
enum class FontFamilyOption { SANS, SERIF, MONOSPACE }
enum class TextWeight { REGULAR, MEDIUM, BOLD }
enum class TextCase { NORMAL, UPPERCASE, LOWERCASE, CAPITALIZED }
enum class HomeAlignment { START, CENTER, END }
enum class VerticalPosition { TOP, CENTER, BOTTOM }
enum class DatePreset { LONG, SHORT, NUMERIC, ISO }
enum class HomeMode { CLASSIC, BOOK }
enum class AutoLaunchLevel { OFF, LOW, MEDIUM, HIGH }

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
    // V1's flat favorites list stays the default -- Book Mode is opt-in
    // until it's been used on a real device.
    val homeMode: HomeMode = HomeMode.CLASSIC,

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
    // Predictive launch defaults OFF -- an unwanted auto-launch is worse
    // than typing one extra tap, so this is opt-in.
    val autoLaunchLevel: AutoLaunchLevel = AutoLaunchLevel.OFF,
    val autoLaunchDelayMs: Int = 500,
    val searchLearningEnabled: Boolean = true,

    // Behavior
    val statusBarVisible: Boolean = true,
    val recentAppsEnabled: Boolean = true,

    // Notifications (optional info item; actual access is a live system
    // permission check, this only reflects whether the user turned the
    // home-screen item on)
    val notificationCountEnabled: Boolean = false,

    // Productivity (both opt-in; actual access is a live system permission/
    // app-op check, these only reflect whether the user turned the feature on)
    val agendaEnabled: Boolean = false,
    val usageStatsEnabled: Boolean = false,

    // Book Mode: an optional 3D page-turn transform on the pager, driven purely
    // by a graphicsLayer rotation (GPU-composited, no bitmap/texture cost) --
    // off by default like every other opt-in animation flourish.
    val bookPageFlipEnabled: Boolean = false,
) {
    companion object {
        const val CURRENT_SCHEMA_VERSION = 1
    }
}

/** The full backup payload: scalar settings + every profile + presets. */
@Serializable
data class LauncherBackup(
    val backupVersion: Int = CURRENT_BACKUP_VERSION,
    val settings: AppSettings = AppSettings(),
    val state: ProfileCollection = ProfileCollection(),
) {
    companion object {
        const val CURRENT_BACKUP_VERSION = 2
    }
}
