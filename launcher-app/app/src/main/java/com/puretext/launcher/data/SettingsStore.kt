package com.puretext.launcher.data

import android.content.Context
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.floatPreferencesKey
import androidx.datastore.preferences.core.intPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import java.io.IOException
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map

private inline fun <reified E : Enum<E>> safeEnumOf(name: String?, default: E): E {
    if (name == null) return default
    return try {
        java.lang.Enum.valueOf(E::class.java, name)
    } catch (e: IllegalArgumentException) {
        default
    }
}

/**
 * Persists [AppSettings] as individual DataStore keys (so a partial write --
 * process death mid-edit -- can never corrupt fields it didn't touch), while
 * still supporting whole-object read/replace for backup and reset flows.
 * Every read falls back to a safe default: a missing key, a corrupted
 * DataStore file, or an old/unknown enum name never crashes -- it just
 * yields [AppSettings]'s defaults for that field.
 */
class SettingsStore(context: Context) {
    private val dataStore = context.launcherDataStore

    val settings: Flow<AppSettings> = dataStore.data
        .catch { e ->
            if (e is IOException) emit(androidx.datastore.preferences.core.emptyPreferences()) else throw e
        }
        .map { it.toAppSettings() }

    suspend fun current(): AppSettings = settings.first()

    suspend fun update(transform: (AppSettings) -> AppSettings) {
        val next = transform(current())
        dataStore.edit { it.writeAppSettings(next) }
    }

    suspend fun replaceAll(newSettings: AppSettings) {
        dataStore.edit { it.writeAppSettings(newSettings) }
    }

    suspend fun resetAppearance() = update {
        val d = AppSettings()
        it.copy(
            theme = d.theme,
            homeMode = d.homeMode,
            trueAmoled = d.trueAmoled,
            animationsEnabled = d.animationsEnabled,
            fontFamily = d.fontFamily,
            fontWeight = d.fontWeight,
            textCase = d.textCase,
            letterSpacingSp = d.letterSpacingSp,
            lineSpacingMultiplier = d.lineSpacingMultiplier,
            clockTextSizeSp = d.clockTextSizeSp,
            dateTextSizeSp = d.dateTextSizeSp,
            appTextSizeSp = d.appTextSizeSp,
            secondaryTextSizeSp = d.secondaryTextSizeSp,
            homeAlignment = d.homeAlignment,
            verticalPosition = d.verticalPosition,
            marginTopDp = d.marginTopDp,
            marginBottomDp = d.marginBottomDp,
            marginHorizontalDp = d.marginHorizontalDp,
            appSpacingDp = d.appSpacingDp,
            clockDateSpacingDp = d.clockDateSpacingDp,
            dateAppsSpacingDp = d.dateAppsSpacingDp,
            compactLayout = d.compactLayout,
            clockEnabled = d.clockEnabled,
            clock24Hour = d.clock24Hour,
            clockShowSeconds = d.clockShowSeconds,
            dateEnabled = d.dateEnabled,
            datePreset = d.datePreset,
            batteryEnabled = d.batteryEnabled,
        )
    }

    suspend fun resetMisc() = update {
        val d = AppSettings()
        it.copy(
            searchAutoKeyboard = d.searchAutoKeyboard,
            searchIncludeHidden = d.searchIncludeHidden,
            searchByPackageName = d.searchByPackageName,
            statusBarVisible = d.statusBarVisible,
            recentAppsEnabled = d.recentAppsEnabled,
            notificationCountEnabled = d.notificationCountEnabled,
        )
    }

    private object Keys {
        val ONBOARDING = booleanPreferencesKey("onboarding_completed")
        val THEME = stringPreferencesKey("theme")
        val HOME_MODE = stringPreferencesKey("home_mode")
        val AMOLED = booleanPreferencesKey("true_amoled")
        val ANIMATIONS = booleanPreferencesKey("animations_enabled")
        val FONT_FAMILY = stringPreferencesKey("font_family")
        val FONT_WEIGHT = stringPreferencesKey("font_weight")
        val TEXT_CASE = stringPreferencesKey("text_case")
        val LETTER_SPACING = floatPreferencesKey("letter_spacing_sp")
        val LINE_SPACING = floatPreferencesKey("line_spacing_mult")
        val CLOCK_SIZE = intPreferencesKey("clock_text_size_sp")
        val DATE_SIZE = intPreferencesKey("date_text_size_sp")
        val APP_SIZE = intPreferencesKey("app_text_size_sp")
        val SECONDARY_SIZE = intPreferencesKey("secondary_text_size_sp")
        val ALIGNMENT = stringPreferencesKey("home_alignment")
        val VERTICAL_POS = stringPreferencesKey("vertical_position")
        val MARGIN_TOP = intPreferencesKey("margin_top_dp")
        val MARGIN_BOTTOM = intPreferencesKey("margin_bottom_dp")
        val MARGIN_H = intPreferencesKey("margin_horizontal_dp")
        val APP_SPACING = intPreferencesKey("app_spacing_dp")
        val CLOCK_DATE_SPACING = intPreferencesKey("clock_date_spacing_dp")
        val DATE_APPS_SPACING = intPreferencesKey("date_apps_spacing_dp")
        val COMPACT_LAYOUT = booleanPreferencesKey("compact_layout")
        val CLOCK_ENABLED = booleanPreferencesKey("clock_enabled")
        val CLOCK_24H = booleanPreferencesKey("clock_24_hour")
        val CLOCK_SECONDS = booleanPreferencesKey("clock_show_seconds")
        val DATE_ENABLED = booleanPreferencesKey("date_enabled")
        val DATE_PRESET = stringPreferencesKey("date_preset")
        val BATTERY_ENABLED = booleanPreferencesKey("battery_enabled")
        val SEARCH_AUTO_KEYBOARD = booleanPreferencesKey("search_auto_keyboard")
        val SEARCH_INCLUDE_HIDDEN = booleanPreferencesKey("search_include_hidden")
        val SEARCH_BY_PACKAGE = booleanPreferencesKey("search_by_package_name")
        val STATUS_BAR_VISIBLE = booleanPreferencesKey("status_bar_visible")
        val RECENT_APPS_ENABLED = booleanPreferencesKey("recent_apps_enabled")
        val NOTIFICATION_COUNT_ENABLED = booleanPreferencesKey("notification_count_enabled")
    }

    private fun Preferences.toAppSettings(): AppSettings {
        val d = AppSettings()
        return AppSettings(
            onboardingCompleted = this[Keys.ONBOARDING] ?: d.onboardingCompleted,
            theme = safeEnumOf(this[Keys.THEME], d.theme),
            homeMode = safeEnumOf(this[Keys.HOME_MODE], d.homeMode),
            trueAmoled = this[Keys.AMOLED] ?: d.trueAmoled,
            animationsEnabled = this[Keys.ANIMATIONS] ?: d.animationsEnabled,
            fontFamily = safeEnumOf(this[Keys.FONT_FAMILY], d.fontFamily),
            fontWeight = safeEnumOf(this[Keys.FONT_WEIGHT], d.fontWeight),
            textCase = safeEnumOf(this[Keys.TEXT_CASE], d.textCase),
            letterSpacingSp = this[Keys.LETTER_SPACING] ?: d.letterSpacingSp,
            lineSpacingMultiplier = this[Keys.LINE_SPACING] ?: d.lineSpacingMultiplier,
            clockTextSizeSp = this[Keys.CLOCK_SIZE] ?: d.clockTextSizeSp,
            dateTextSizeSp = this[Keys.DATE_SIZE] ?: d.dateTextSizeSp,
            appTextSizeSp = this[Keys.APP_SIZE] ?: d.appTextSizeSp,
            secondaryTextSizeSp = this[Keys.SECONDARY_SIZE] ?: d.secondaryTextSizeSp,
            homeAlignment = safeEnumOf(this[Keys.ALIGNMENT], d.homeAlignment),
            verticalPosition = safeEnumOf(this[Keys.VERTICAL_POS], d.verticalPosition),
            marginTopDp = this[Keys.MARGIN_TOP] ?: d.marginTopDp,
            marginBottomDp = this[Keys.MARGIN_BOTTOM] ?: d.marginBottomDp,
            marginHorizontalDp = this[Keys.MARGIN_H] ?: d.marginHorizontalDp,
            appSpacingDp = this[Keys.APP_SPACING] ?: d.appSpacingDp,
            clockDateSpacingDp = this[Keys.CLOCK_DATE_SPACING] ?: d.clockDateSpacingDp,
            dateAppsSpacingDp = this[Keys.DATE_APPS_SPACING] ?: d.dateAppsSpacingDp,
            compactLayout = this[Keys.COMPACT_LAYOUT] ?: d.compactLayout,
            clockEnabled = this[Keys.CLOCK_ENABLED] ?: d.clockEnabled,
            clock24Hour = this[Keys.CLOCK_24H] ?: d.clock24Hour,
            clockShowSeconds = this[Keys.CLOCK_SECONDS] ?: d.clockShowSeconds,
            dateEnabled = this[Keys.DATE_ENABLED] ?: d.dateEnabled,
            datePreset = safeEnumOf(this[Keys.DATE_PRESET], d.datePreset),
            batteryEnabled = this[Keys.BATTERY_ENABLED] ?: d.batteryEnabled,
            searchAutoKeyboard = this[Keys.SEARCH_AUTO_KEYBOARD] ?: d.searchAutoKeyboard,
            searchIncludeHidden = this[Keys.SEARCH_INCLUDE_HIDDEN] ?: d.searchIncludeHidden,
            searchByPackageName = this[Keys.SEARCH_BY_PACKAGE] ?: d.searchByPackageName,
            statusBarVisible = this[Keys.STATUS_BAR_VISIBLE] ?: d.statusBarVisible,
            recentAppsEnabled = this[Keys.RECENT_APPS_ENABLED] ?: d.recentAppsEnabled,
            notificationCountEnabled = this[Keys.NOTIFICATION_COUNT_ENABLED] ?: d.notificationCountEnabled,
        )
    }

    private fun androidx.datastore.preferences.core.MutablePreferences.writeAppSettings(s: AppSettings) {
        this[Keys.ONBOARDING] = s.onboardingCompleted
        this[Keys.THEME] = s.theme.name
        this[Keys.HOME_MODE] = s.homeMode.name
        this[Keys.AMOLED] = s.trueAmoled
        this[Keys.ANIMATIONS] = s.animationsEnabled
        this[Keys.FONT_FAMILY] = s.fontFamily.name
        this[Keys.FONT_WEIGHT] = s.fontWeight.name
        this[Keys.TEXT_CASE] = s.textCase.name
        this[Keys.LETTER_SPACING] = s.letterSpacingSp
        this[Keys.LINE_SPACING] = s.lineSpacingMultiplier
        this[Keys.CLOCK_SIZE] = s.clockTextSizeSp
        this[Keys.DATE_SIZE] = s.dateTextSizeSp
        this[Keys.APP_SIZE] = s.appTextSizeSp
        this[Keys.SECONDARY_SIZE] = s.secondaryTextSizeSp
        this[Keys.ALIGNMENT] = s.homeAlignment.name
        this[Keys.VERTICAL_POS] = s.verticalPosition.name
        this[Keys.MARGIN_TOP] = s.marginTopDp
        this[Keys.MARGIN_BOTTOM] = s.marginBottomDp
        this[Keys.MARGIN_H] = s.marginHorizontalDp
        this[Keys.APP_SPACING] = s.appSpacingDp
        this[Keys.CLOCK_DATE_SPACING] = s.clockDateSpacingDp
        this[Keys.DATE_APPS_SPACING] = s.dateAppsSpacingDp
        this[Keys.COMPACT_LAYOUT] = s.compactLayout
        this[Keys.CLOCK_ENABLED] = s.clockEnabled
        this[Keys.CLOCK_24H] = s.clock24Hour
        this[Keys.CLOCK_SECONDS] = s.clockShowSeconds
        this[Keys.DATE_ENABLED] = s.dateEnabled
        this[Keys.DATE_PRESET] = s.datePreset.name
        this[Keys.BATTERY_ENABLED] = s.batteryEnabled
        this[Keys.SEARCH_AUTO_KEYBOARD] = s.searchAutoKeyboard
        this[Keys.SEARCH_INCLUDE_HIDDEN] = s.searchIncludeHidden
        this[Keys.SEARCH_BY_PACKAGE] = s.searchByPackageName
        this[Keys.STATUS_BAR_VISIBLE] = s.statusBarVisible
        this[Keys.RECENT_APPS_ENABLED] = s.recentAppsEnabled
        this[Keys.NOTIFICATION_COUNT_ENABLED] = s.notificationCountEnabled
    }
}
