package com.puretext.launcher.data

import android.content.Context
import android.util.Log
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.emptyPreferences
import androidx.datastore.preferences.core.stringPreferencesKey
import java.io.IOException
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import kotlinx.serialization.json.Json

private fun Map<String, AppEntry>.withEntry(key: String, transform: (AppEntry) -> AppEntry): Map<String, AppEntry> {
    val updated = transform(this[key] ?: AppEntry())
    return if (updated == AppEntry()) this - key else this + (key to updated)
}

/**
 * Persists [LauncherState] (app ordering, hidden/favorite/alias/group per
 * app, groups, shortcuts, gestures, recents) as one JSON blob. A single
 * blob -- rather than one DataStore key per list entry -- is what makes
 * backup/export and import atomic and easy to version; [parse] is the one
 * place malformed JSON (a hand-edited or corrupted import, a future/unknown
 * schema) is handled, and it always falls back to safe defaults rather than
 * throwing.
 */
class ConfigStore(context: Context) {
    private val dataStore = context.launcherDataStore
    private val json = Json {
        ignoreUnknownKeys = true
        encodeDefaults = true
        isLenient = true
    }

    val state: Flow<LauncherState> = dataStore.data
        .catch { e -> if (e is IOException) emit(emptyPreferences()) else throw e }
        .map { parse(it[STATE_KEY]) }

    suspend fun current(): LauncherState = state.first()

    suspend fun update(transform: (LauncherState) -> LauncherState) {
        write(transform(current()))
    }

    suspend fun replaceAll(newState: LauncherState) = write(newState)

    private fun parse(raw: String?): LauncherState {
        if (raw.isNullOrBlank()) return LauncherState()
        return try {
            json.decodeFromString(LauncherState.serializer(), raw)
        } catch (e: Exception) {
            Log.w(TAG, "Corrupt launcher state JSON, falling back to defaults", e)
            LauncherState()
        }
    }

    private suspend fun write(s: LauncherState) {
        val encoded = json.encodeToString(LauncherState.serializer(), s)
        dataStore.edit { it[STATE_KEY] = encoded }
    }

    // --- Per-app entry mutations -------------------------------------------------

    suspend fun setHidden(key: String, hidden: Boolean) = update { s ->
        s.copy(entries = s.entries.withEntry(key) { it.copy(hidden = hidden) })
    }

    suspend fun setFavorite(key: String, favorite: Boolean) = update { s ->
        val entries = s.entries.withEntry(key) { it.copy(favorite = favorite) }
        val order = if (favorite) {
            if (key in s.appOrder) s.appOrder else s.appOrder + key
        } else {
            s.appOrder - key
        }
        s.copy(entries = entries, appOrder = order)
    }

    suspend fun setAlias(key: String, alias: String?) = update { s ->
        val trimmed = alias?.trim()?.takeUnless { it.isEmpty() }
        s.copy(entries = s.entries.withEntry(key) { it.copy(alias = trimmed) })
    }

    suspend fun setGroup(key: String, groupName: String?) = update { s ->
        s.copy(entries = s.entries.withEntry(key) { it.copy(groupName = groupName) })
    }

    suspend fun moveFavorite(key: String, delta: Int) = update { s ->
        val list = s.appOrder.toMutableList()
        val idx = list.indexOf(key)
        if (idx < 0) return@update s
        val newIdx = (idx + delta).coerceIn(0, list.lastIndex)
        if (newIdx == idx) return@update s
        list.removeAt(idx)
        list.add(newIdx, key)
        s.copy(appOrder = list)
    }

    suspend fun reorderFavorites(newOrder: List<String>) = update { s -> s.copy(appOrder = newOrder) }

    // --- Groups --------------------------------------------------------------------

    suspend fun addGroup(name: String) = update { s ->
        val trimmed = name.trim()
        if (trimmed.isEmpty() || s.groups.any { it.name.equals(trimmed, ignoreCase = true) }) return@update s
        s.copy(groups = s.groups + AppGroup(name = trimmed))
    }

    suspend fun renameGroup(oldName: String, newName: String) = update { s ->
        val trimmed = newName.trim()
        if (trimmed.isEmpty() || s.groups.any { it.name.equals(trimmed, true) && !it.name.equals(oldName, true) }) {
            return@update s
        }
        s.copy(
            groups = s.groups.map { if (it.name == oldName) it.copy(name = trimmed) else it },
            entries = s.entries.mapValues { (_, e) -> if (e.groupName == oldName) e.copy(groupName = trimmed) else e },
        )
    }

    suspend fun deleteGroup(name: String) = update { s ->
        s.copy(
            groups = s.groups.filterNot { it.name == name },
            entries = s.entries.mapValues { (_, e) -> if (e.groupName == name) e.copy(groupName = null) else e },
        )
    }

    suspend fun setGroupCollapsed(name: String, collapsed: Boolean) = update { s ->
        s.copy(groups = s.groups.map { if (it.name == name) it.copy(collapsed = collapsed) else it })
    }

    suspend fun reorderGroups(newOrder: List<String>) = update { s ->
        val byName = s.groups.associateBy { it.name }
        val reordered = newOrder.mapNotNull { byName[it] } + s.groups.filter { it.name !in newOrder }
        s.copy(groups = reordered)
    }

    // --- Shortcuts -------------------------------------------------------------

    suspend fun addShortcut(shortcut: LauncherShortcut) = update { s -> s.copy(shortcuts = s.shortcuts + shortcut) }

    suspend fun removeShortcut(id: String) = update { s -> s.copy(shortcuts = s.shortcuts.filterNot { it.id == id }) }

    suspend fun resetShortcuts() = update { it.copy(shortcuts = emptyList()) }

    // --- Gestures ----------------------------------------------------------------

    suspend fun setGestures(g: GestureSettings) = update { it.copy(gestures = g) }

    suspend fun resetGestures() = update { it.copy(gestures = GestureSettings()) }

    // --- Recents -------------------------------------------------------------------

    suspend fun recordRecentApp(key: String) = update { s ->
        val updated = (listOf(key) + s.recentApps.filterNot { it == key }).take(MAX_RECENTS)
        s.copy(recentApps = updated)
    }

    // --- Housekeeping / resets -----------------------------------------------------

    suspend fun pruneRemovedPackage(packageName: String) = update { s ->
        val prefix = "$packageName/"
        s.copy(
            appOrder = s.appOrder.filterNot { it.startsWith(prefix) },
            entries = s.entries.filterKeys { !it.startsWith(prefix) },
            recentApps = s.recentApps.filterNot { it.startsWith(prefix) },
            shortcuts = s.shortcuts.filterNot { it.type == ShortcutType.APP && it.target.startsWith(prefix) },
        )
    }

    suspend fun resetAppLayout() = update { s ->
        s.copy(
            appOrder = emptyList(),
            entries = s.entries.mapValues { (_, e) -> e.copy(hidden = false, favorite = false, groupName = null) },
            groups = emptyList(),
        )
    }

    suspend fun resetAll() = replaceAll(LauncherState())

    companion object {
        private const val TAG = "ConfigStore"
        private const val MAX_RECENTS = 8
        private val STATE_KEY = stringPreferencesKey("launcher_state_json")
    }
}
