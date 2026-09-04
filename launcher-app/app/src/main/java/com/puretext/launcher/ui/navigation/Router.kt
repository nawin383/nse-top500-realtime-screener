package com.puretext.launcher.ui.navigation

import androidx.compose.runtime.Composable
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.remember

sealed interface Screen {
    data object Home : Screen
    data class Search(val autoFocusKeyboard: Boolean = true) : Screen
    data object SettingsRoot : Screen
    data object SettingsHome : Screen
    data object SettingsApps : Screen
    data object SettingsTypography : Screen
    data object SettingsLayout : Screen
    data object SettingsClock : Screen
    data object SettingsDate : Screen
    data object SettingsSearch : Screen
    data object SettingsGestures : Screen
    data object SettingsShortcuts : Screen
    data object SettingsAppearance : Screen
    data object SettingsBehavior : Screen
    data object SettingsNotifications : Screen
    data object SettingsBackup : Screen
    data object SettingsAdvanced : Screen
    data object SettingsAbout : Screen
}

/**
 * A deliberately tiny back stack -- this app has ~20 screens with no deep
 * linking, argument passing beyond a couple of IDs (handled by ViewModel
 * state, not nav args), so androidx.navigation would be pure overhead. Not
 * @Composable itself so gesture/back-handler code can call push/pop from
 * plain callbacks.
 */
class Router(start: Screen = Screen.Home) {
    private val stack = mutableStateListOf(start)

    val current: Screen get() = stack.last()

    val canGoBack: Boolean get() = stack.size > 1

    fun push(screen: Screen) {
        stack.add(screen)
    }

    fun pop(): Boolean {
        if (stack.size <= 1) return false
        stack.removeAt(stack.lastIndex)
        return true
    }

    fun popToHome() {
        while (stack.size > 1) stack.removeAt(stack.lastIndex)
    }

    fun reset(screen: Screen) {
        stack.clear()
        stack.add(screen)
    }
}

@Composable
fun rememberRouter(start: Screen = Screen.Home): Router = remember { Router(start) }
