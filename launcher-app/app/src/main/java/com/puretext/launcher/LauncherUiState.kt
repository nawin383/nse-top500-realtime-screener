package com.puretext.launcher

import com.puretext.launcher.data.AppInfo
import com.puretext.launcher.data.AppSettings
import com.puretext.launcher.data.AutoLaunchLevel
import com.puretext.launcher.data.AutomationRule
import com.puretext.launcher.data.BookPage
import com.puretext.launcher.data.LauncherState
import com.puretext.launcher.data.Profile
import com.puretext.launcher.data.StylePreset

/**
 * One combined, always-consistent snapshot of everything the UI reads:
 * the live installed-app list plus persisted settings/state. Every
 * "which apps show where" question is answered here, in one place, so a
 * screen never has to reconcile [allApps] against [state] itself -- and an
 * app that's been uninstalled (present in [state] but absent from
 * [allApps]) is simply never returned by any of these, with no special
 * casing required at call sites.
 */
data class LauncherUiState(
    val allApps: List<AppInfo> = emptyList(),
    val settings: AppSettings = AppSettings(),
    val state: LauncherState = LauncherState(),
    /** Every profile, for the Profiles settings screen -- [state] above is always just the active one's. */
    val profiles: List<Profile> = emptyList(),
    val activeProfileId: String = "",
    val presets: List<StylePreset> = emptyList(),
    val automationRules: List<AutomationRule> = emptyList(),
    val loading: Boolean = true,
) {
    private val byKey: Map<String, AppInfo> by lazy { allApps.associateBy { it.key } }

    fun displayName(app: AppInfo): String = state.entries[app.key]?.alias?.takeUnless { it.isBlank() } ?: app.label

    fun isHidden(app: AppInfo): Boolean = state.entries[app.key]?.hidden == true

    fun isFavorite(app: AppInfo): Boolean = state.entries[app.key]?.favorite == true

    fun groupOf(app: AppInfo): String? = state.entries[app.key]?.groupName

    /** Home-screen list, in user-defined order, favorites only. */
    fun favoriteApps(): List<AppInfo> = state.appOrder.mapNotNull { byKey[it] }

    /** Everything visible in Search / All Apps, optionally including hidden apps. */
    fun visibleApps(includeHidden: Boolean = false): List<AppInfo> =
        allApps.filter { includeHidden || !isHidden(it) }.sortedBy { displayName(it).lowercase() }

    fun hiddenApps(): List<AppInfo> = allApps.filter { isHidden(it) }.sortedBy { displayName(it).lowercase() }

    fun recentApps(): List<AppInfo> = state.recentApps.mapNotNull { byKey[it] }

    fun appsInGroup(groupName: String, includeHidden: Boolean = false): List<AppInfo> =
        visibleApps(includeHidden).filter { groupOf(it) == groupName }

    fun ungroupedApps(includeHidden: Boolean = false): List<AppInfo> =
        visibleApps(includeHidden).filter { groupOf(it) == null }

    fun appByKey(key: String): AppInfo? = byKey[key]

    /** Book Mode content pages, in order, optionally including hidden ones. Uninstalled apps drop out automatically. */
    fun bookPages(includeHidden: Boolean = false): List<BookPage> =
        state.book.pages.filter { includeHidden || !it.hidden }

    fun appsInPage(page: BookPage): List<AppInfo> = page.appKeys.mapNotNull { byKey[it] }

    /** True while a Focus session is running and hasn't hit its end time yet ("until disabled" sessions never expire on their own). */
    fun isFocusActive(nowMillis: Long = System.currentTimeMillis()): Boolean {
        val focus = state.focus
        if (!focus.active) return false
        val endsAt = focus.endsAtMillis ?: return true
        return nowMillis < endsAt
    }

    fun focusAllowedApps(): List<AppInfo> = state.focus.allowedAppKeys.mapNotNull { byKey[it] }

    /** Apps a Home screen should actually show right now: the Focus allow-list while active, otherwise [apps] unchanged. */
    fun focusFilter(apps: List<AppInfo>, nowMillis: Long = System.currentTimeMillis()): List<AppInfo> =
        if (!isFocusActive(nowMillis)) apps else apps.filter { it.key in state.focus.allowedAppKeys }

    fun search(query: String, includeHidden: Boolean = false, byPackageName: Boolean = true, learningEnabled: Boolean = false): List<AppInfo> {
        if (query.isBlank()) return visibleApps(includeHidden)
        val q = query.trim().lowercase()
        val matches = visibleApps(includeHidden).filter { app ->
            displayName(app).lowercase().contains(q) ||
                app.label.lowercase().contains(q) ||
                (byPackageName && app.packageName.lowercase().contains(q))
        }
        if (!learningEnabled) return matches
        val learned = state.searchLearning.queryAppCounts[q] ?: return matches
        return matches.sortedWith(
            compareByDescending<AppInfo> { learned[it.key] ?: 0 }.thenBy { displayName(it).lowercase() },
        )
    }

    /**
     * The app Predictive Auto-Launch would jump straight to for [query], or
     * null if it shouldn't (nothing typed, no results, or not confident
     * enough at the current [level]). Deliberately conservative: with two or
     * more matches, it only fires once this exact query has a clear, learned
     * winner -- never a first-time guess.
     */
    fun predictedApp(query: String, results: List<AppInfo>, level: AutoLaunchLevel): AppInfo? {
        if (level == AutoLaunchLevel.OFF || query.isBlank() || results.isEmpty()) return null
        if (results.size == 1) return results.first()
        val q = query.trim().lowercase()
        val learned = state.searchLearning.queryAppCounts[q] ?: return null
        val ranked = learned.entries.sortedByDescending { it.value }
        val top = ranked.firstOrNull() ?: return null
        val topApp = byKey[top.key] ?: return null
        if (results.none { it.key == topApp.key }) return null
        val second = ranked.getOrNull(1)?.value ?: 0
        val minCount = when (level) {
            AutoLaunchLevel.HIGH -> 2
            AutoLaunchLevel.MEDIUM -> 3
            AutoLaunchLevel.LOW -> 5
            AutoLaunchLevel.OFF -> Int.MAX_VALUE
        }
        return if (top.value >= minCount && top.value > second) topApp else null
    }
}
