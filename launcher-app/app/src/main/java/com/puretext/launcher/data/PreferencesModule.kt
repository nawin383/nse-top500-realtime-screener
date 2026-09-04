package com.puretext.launcher.data

import android.content.Context
import androidx.datastore.preferences.preferencesDataStore

/**
 * A single DataStore file backs both SettingsStore (scalar prefs) and
 * ConfigStore (the JSON state blob). DataStore throws if two delegates for
 * the same file name are created, so the property lives here, once, and
 * both stores take it as a constructor argument.
 */
val Context.launcherDataStore by preferencesDataStore(name = "pure_launcher_prefs")
