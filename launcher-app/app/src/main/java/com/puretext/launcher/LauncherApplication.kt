package com.puretext.launcher

import android.app.Application
import com.puretext.launcher.data.AppRepository
import com.puretext.launcher.data.ConfigStore
import com.puretext.launcher.data.SettingsStore
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch

class LauncherApplication : Application() {

    /** Outlives any single Activity -- package-change broadcasts and the
     *  optional accessibility/notification services all need to reach the
     *  same repositories the UI reads from. */
    val applicationScope = CoroutineScope(SupervisorJob() + Dispatchers.Default)

    val appRepository by lazy { AppRepository(this) }
    val settingsStore by lazy { SettingsStore(this) }
    val configStore by lazy { ConfigStore(this) }

    override fun onCreate() {
        super.onCreate()
        applicationScope.launch {
            appRepository.refresh()
        }
    }
}
