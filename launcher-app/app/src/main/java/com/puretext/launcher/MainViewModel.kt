package com.puretext.launcher

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.puretext.launcher.data.AppInfo
import com.puretext.launcher.data.AppSettings
import com.puretext.launcher.data.BackCoverConfig
import com.puretext.launcher.data.CoverConfig
import com.puretext.launcher.data.GestureSettings
import com.puretext.launcher.data.HomeMode
import com.puretext.launcher.data.LauncherBackup
import com.puretext.launcher.data.BookPageStyle
import com.puretext.launcher.data.LauncherShortcut
import com.puretext.launcher.data.ShortcutLauncher
import com.puretext.launcher.data.StylePreset
import com.puretext.launcher.data.applyTo
import com.puretext.launcher.data.bookPageStyleFromGlobal
import com.puretext.launcher.data.stylePresetFromSettings
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import kotlinx.serialization.json.Json

/**
 * The single source of truth for the UI. Every mutation goes through here
 * so screens never touch SettingsStore/ConfigStore/AppRepository directly --
 * that's what keeps every write on a background dispatcher (DataStore
 * already does this) without any screen having to think about coroutines.
 */
class MainViewModel(application: Application) : AndroidViewModel(application) {

    private val app = application as LauncherApplication
    private val appRepository = app.appRepository
    private val settingsStore = app.settingsStore
    private val configStore = app.configStore

    private val backupJson = Json {
        ignoreUnknownKeys = true
        isLenient = true
        encodeDefaults = true
    }

    val uiState: StateFlow<LauncherUiState> = combine(
        appRepository.apps,
        settingsStore.settings,
        configStore.state,
    ) { apps, settings, state ->
        LauncherUiState(allApps = apps, settings = settings, state = state, loading = false)
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), LauncherUiState())

    fun refreshApps() = viewModelScope.launch { appRepository.refresh() }

    /** Returns false (and refreshes the app list) if the app could no longer be launched. */
    fun launchApp(app: AppInfo) {
        viewModelScope.launch {
            val launched = appRepository.launch(app)
            if (launched) {
                if (uiState.value.settings.recentAppsEnabled) configStore.recordRecentApp(app.key)
            } else {
                appRepository.refresh()
            }
        }
    }

    /** Same as [launchApp], but also feeds Search Learning so this query ranks this app higher next time. */
    fun launchAppFromSearch(app: AppInfo, query: String) {
        launchApp(app)
        if (uiState.value.settings.searchLearningEnabled && query.isNotBlank()) {
            viewModelScope.launch { configStore.recordSearchLaunch(query, app.key) }
        }
    }

    fun openAppInfo(app: AppInfo) {
        appRepository.openAppInfo(app)
    }

    fun uninstall(app: AppInfo) {
        appRepository.uninstall(app)
    }

    fun setHidden(app: AppInfo, hidden: Boolean) = viewModelScope.launch { configStore.setHidden(app.key, hidden) }

    fun setFavorite(app: AppInfo, favorite: Boolean) = viewModelScope.launch { configStore.setFavorite(app.key, favorite) }

    fun setAlias(app: AppInfo, alias: String?) = viewModelScope.launch { configStore.setAlias(app.key, alias) }

    fun moveFavorite(app: AppInfo, delta: Int) = viewModelScope.launch { configStore.moveFavorite(app.key, delta) }

    fun setGroup(app: AppInfo, groupName: String?) = viewModelScope.launch { configStore.setGroup(app.key, groupName) }

    fun addGroup(name: String) = viewModelScope.launch { configStore.addGroup(name) }

    fun renameGroup(oldName: String, newName: String) = viewModelScope.launch { configStore.renameGroup(oldName, newName) }

    fun deleteGroup(name: String) = viewModelScope.launch { configStore.deleteGroup(name) }

    fun setGroupCollapsed(name: String, collapsed: Boolean) = viewModelScope.launch { configStore.setGroupCollapsed(name, collapsed) }

    fun addShortcut(shortcut: LauncherShortcut) = viewModelScope.launch { configStore.addShortcut(shortcut) }

    fun removeShortcut(id: String) = viewModelScope.launch { configStore.removeShortcut(id) }

    /** False means the shortcut's target is gone or couldn't be opened -- caller decides whether to surface that. */
    fun launchShortcut(shortcut: LauncherShortcut): Boolean =
        ShortcutLauncher.launch(getApplication(), shortcut, appRepository) { key -> uiState.value.appByKey(key) }

    fun setGestures(gestures: GestureSettings) = viewModelScope.launch { configStore.setGestures(gestures) }

    // --- Book Mode ---------------------------------------------------------------

    fun setHomeMode(mode: HomeMode) = viewModelScope.launch {
        if (mode == HomeMode.BOOK) {
            configStore.ensureBookSeeded(uiState.value.favoriteApps().map { it.key })
        }
        settingsStore.update { it.copy(homeMode = mode) }
    }

    fun addPage(name: String) = viewModelScope.launch { configStore.addPage(name) }

    fun renamePage(pageId: String, newName: String) = viewModelScope.launch { configStore.renamePage(pageId, newName) }

    fun deletePage(pageId: String) = viewModelScope.launch { configStore.deletePage(pageId) }

    fun setPageHidden(pageId: String, hidden: Boolean) = viewModelScope.launch { configStore.setPageHidden(pageId, hidden) }

    fun movePage(pageId: String, delta: Int) = viewModelScope.launch { configStore.movePage(pageId, delta) }

    fun addAppToPage(pageId: String, app: AppInfo) = viewModelScope.launch { configStore.addAppToPage(pageId, app.key) }

    fun removeAppFromPage(pageId: String, app: AppInfo) = viewModelScope.launch { configStore.removeAppFromPage(pageId, app.key) }

    fun moveAppInPage(pageId: String, app: AppInfo, delta: Int) = viewModelScope.launch { configStore.moveAppInPage(pageId, app.key, delta) }

    fun setCover(cover: CoverConfig) = viewModelScope.launch { configStore.setCover(cover) }

    fun setBackCover(backCover: BackCoverConfig) = viewModelScope.launch { configStore.setBackCover(backCover) }

    fun setPageIndicatorEnabled(enabled: Boolean) = viewModelScope.launch { configStore.setPageIndicatorEnabled(enabled) }

    fun setPageStyle(pageId: String, style: BookPageStyle) = viewModelScope.launch { configStore.setPageStyle(pageId, style) }

    /** Turning custom style on seeds it from the current global style so the page starts unchanged; turning it off clears back to "use global." */
    fun setPageCustomStyleEnabled(pageId: String, enabled: Boolean) = viewModelScope.launch {
        val style = if (enabled) bookPageStyleFromGlobal(uiState.value.settings) else BookPageStyle()
        configStore.setPageStyle(pageId, style)
    }

    // --- Presets -------------------------------------------------------------------

    fun applyPreset(preset: StylePreset) = viewModelScope.launch { settingsStore.update { preset.applyTo(it) } }

    fun saveCurrentAsPreset(name: String) = viewModelScope.launch {
        val preset = stylePresetFromSettings(java.util.UUID.randomUUID().toString(), name.trim().ifEmpty { "My Style" }, uiState.value.settings)
        configStore.addPreset(preset)
    }

    fun duplicatePreset(preset: StylePreset, newName: String) = viewModelScope.launch {
        configStore.addPreset(preset.copy(id = java.util.UUID.randomUUID().toString(), name = newName.trim().ifEmpty { "${preset.name} Copy" }))
    }

    fun renamePreset(id: String, newName: String) = viewModelScope.launch { configStore.renamePreset(id, newName) }

    fun deletePreset(id: String) = viewModelScope.launch { configStore.deletePreset(id) }

    fun updateSettings(transform: (AppSettings) -> AppSettings) = viewModelScope.launch { settingsStore.update(transform) }

    fun completeOnboarding(selectedFavorites: List<AppInfo>) = viewModelScope.launch {
        selectedFavorites.forEach { configStore.setFavorite(it.key, true) }
        settingsStore.update { it.copy(onboardingCompleted = true) }
    }

    // --- Resets --------------------------------------------------------------------

    fun resetAppearance() = viewModelScope.launch { settingsStore.resetAppearance() }

    fun resetGestures() = viewModelScope.launch { configStore.resetGestures() }

    fun resetAppLayout() = viewModelScope.launch { configStore.resetAppLayout() }

    fun resetLauncherMisc() = viewModelScope.launch {
        settingsStore.resetMisc()
        configStore.resetShortcuts()
        configStore.resetSearchLearning()
    }

    fun resetSearchLearning() = viewModelScope.launch { configStore.resetSearchLearning() }

    fun resetEverything() = viewModelScope.launch {
        val onboarded = settingsStore.current().onboardingCompleted
        settingsStore.replaceAll(AppSettings(onboardingCompleted = onboarded))
        configStore.resetAll()
    }

    // --- Backup ----------------------------------------------------------------------

    suspend fun exportBackupJson(): String {
        val backup = LauncherBackup(settings = settingsStore.current(), state = configStore.current())
        return backupJson.encodeToString(LauncherBackup.serializer(), backup)
    }

    /** Never throws: malformed/corrupt/foreign JSON returns false and leaves current config untouched. */
    suspend fun importBackupJson(raw: String): Boolean {
        val backup = try {
            backupJson.decodeFromString(LauncherBackup.serializer(), raw)
        } catch (e: Exception) {
            return false
        }
        val onboarded = settingsStore.current().onboardingCompleted
        settingsStore.replaceAll(backup.settings.copy(onboardingCompleted = onboarded))
        configStore.replaceAll(backup.state)
        return true
    }
}
