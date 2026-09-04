package com.puretext.launcher

import com.puretext.launcher.data.AppInfo
import com.puretext.launcher.data.AppSettings
import com.puretext.launcher.data.BookPage
import com.puretext.launcher.data.LauncherState

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

    fun search(query: String, includeHidden: Boolean = false, byPackageName: Boolean = true): List<AppInfo> {
        if (query.isBlank()) return visibleApps(includeHidden)
        val q = query.trim().lowercase()
        return visibleApps(includeHidden).filter { app ->
            displayName(app).lowercase().contains(q) ||
                app.label.lowercase().contains(q) ||
                (byPackageName && app.packageName.lowercase().contains(q))
        }
    }
}
