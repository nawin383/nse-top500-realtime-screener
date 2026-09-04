package com.puretext.launcher

import android.app.role.RoleManager
import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.util.Log
import androidx.activity.ComponentActivity
import androidx.activity.compose.BackHandler
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalView
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.puretext.launcher.data.GestureAction
import com.puretext.launcher.data.GestureBinding
import com.puretext.launcher.data.HomeMode
import com.puretext.launcher.data.ThemeStyle
import com.puretext.launcher.gestures.LockAccessibilityService
import com.puretext.launcher.gestures.SystemPanels
import com.puretext.launcher.ui.home.BookHomeScreen
import com.puretext.launcher.ui.home.HomeScreen
import com.puretext.launcher.ui.navigation.Router
import com.puretext.launcher.ui.navigation.Screen
import com.puretext.launcher.ui.notifications.NotificationsListScreen
import com.puretext.launcher.ui.onboarding.OnboardingScreen
import com.puretext.launcher.ui.productivity.AgendaScreen
import com.puretext.launcher.ui.productivity.UsageStatsScreen
import com.puretext.launcher.ui.search.SearchScreen
import com.puretext.launcher.ui.settings.AboutSettingsScreen
import com.puretext.launcher.ui.settings.AdvancedSettingsScreen
import com.puretext.launcher.ui.settings.AppearanceSettingsScreen
import com.puretext.launcher.ui.settings.AppsSettingsScreen
import com.puretext.launcher.ui.settings.AutomationSettingsScreen
import com.puretext.launcher.ui.settings.BackupSettingsScreen
import com.puretext.launcher.ui.settings.BehaviorSettingsScreen
import com.puretext.launcher.ui.settings.ClockSettingsScreen
import com.puretext.launcher.ui.settings.DateSettingsScreen
import com.puretext.launcher.ui.settings.FocusSettingsScreen
import com.puretext.launcher.ui.settings.GesturesSettingsScreen
import com.puretext.launcher.ui.settings.HomeSettingsScreen
import com.puretext.launcher.ui.settings.LayoutSettingsScreen
import com.puretext.launcher.ui.settings.NotificationsSettingsScreen
import com.puretext.launcher.ui.settings.PagesSettingsScreen
import com.puretext.launcher.ui.settings.PresetsSettingsScreen
import com.puretext.launcher.ui.settings.ProductivitySettingsScreen
import com.puretext.launcher.ui.settings.ProfilesSettingsScreen
import com.puretext.launcher.ui.settings.SearchSettingsScreen
import com.puretext.launcher.ui.settings.SettingsRootScreen
import com.puretext.launcher.ui.settings.ShortcutsSettingsScreen
import com.puretext.launcher.ui.settings.TypographySettingsScreen
import com.puretext.launcher.ui.theme.LauncherTheme
import com.puretext.launcher.ui.theme.LocalLauncherColors

/**
 * Single-activity host. This *is* the home screen -- singleTask so the
 * system reuses this instance (see onNewIntent) instead of spawning a
 * second one every time the user presses Home.
 */
class MainActivity : ComponentActivity() {

    private val viewModel: MainViewModel by viewModels()
    private val router = Router(Screen.Home)

    private val requestRoleLauncher = registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { }
    private val requestCalendarPermission = registerForActivityResult(ActivityResultContracts.RequestPermission()) { }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        WindowCompat.setDecorFitsSystemWindows(window, true)
        setContent {
            LauncherApp(viewModel = viewModel, router = router, activity = this)
        }
    }

    override fun onResume() {
        super.onResume()
        viewModel.refreshApps()
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        if (intent.hasCategory(Intent.CATEGORY_HOME)) {
            router.popToHome()
        }
    }

    fun requestDefaultLauncher() {
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                val roleManager = getSystemService(RoleManager::class.java)
                if (roleManager != null && roleManager.isRoleAvailable(RoleManager.ROLE_HOME) && !roleManager.isRoleHeld(RoleManager.ROLE_HOME)) {
                    requestRoleLauncher.launch(roleManager.createRequestRoleIntent(RoleManager.ROLE_HOME))
                    return
                }
            }
            startActivity(Intent(Settings.ACTION_HOME_SETTINGS))
        } catch (e: Exception) {
            Log.w(TAG, "Could not open default launcher settings", e)
        }
    }

    fun requestCalendarAccess() {
        requestCalendarPermission.launch(android.Manifest.permission.READ_CALENDAR)
    }

    fun dispatchGesture(binding: GestureBinding) {
        when (binding.action) {
            GestureAction.SEARCH -> router.push(Screen.Search(autoFocusKeyboard = true))
            GestureAction.ALL_APPS -> router.push(Screen.Search(autoFocusKeyboard = false))
            GestureAction.NOTIFICATIONS -> SystemPanels.expandNotifications(this)
            GestureAction.QUICK_SETTINGS -> SystemPanels.expandQuickSettings(this)
            GestureAction.OPEN_APP -> {
                val app = binding.appKey?.let { viewModel.uiState.value.appByKey(it) }
                if (app != null) viewModel.launchApp(app)
            }
            GestureAction.LAUNCHER_SETTINGS -> router.push(Screen.SettingsRoot)
            GestureAction.LOCK_SCREEN -> LockAccessibilityService.lock()
            GestureAction.NOTHING -> Unit
        }
    }

    companion object {
        private const val TAG = "MainActivity"
    }
}

@Composable
private fun LauncherApp(viewModel: MainViewModel, router: Router, activity: MainActivity) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    val pendingOpenPageId by viewModel.pendingOpenPageId.collectAsStateWithLifecycle()

    LauncherTheme(settings = uiState.settings) {
        val colors = LocalLauncherColors.current
        SystemBarsEffect(statusBarVisible = uiState.settings.statusBarVisible, theme = uiState.settings.theme)
        BackHandler(enabled = router.canGoBack) { router.pop() }

        when {
            uiState.loading -> Box(Modifier.fillMaxSize().background(colors.background))

            !uiState.settings.onboardingCompleted -> OnboardingScreen(
                installedApps = uiState.allApps,
                currentTheme = uiState.settings.theme,
                onSetTheme = { style -> viewModel.updateSettings { it.copy(theme = style) } },
                onFinish = { selected ->
                    viewModel.completeOnboarding(selected)
                    router.reset(Screen.Home)
                },
                onRequestDefaultLauncher = { activity.requestDefaultLauncher() },
            )

            else -> when (val screen = router.current) {
                is Screen.Home -> if (uiState.settings.homeMode == HomeMode.BOOK) {
                    BookHomeScreen(
                        uiState = uiState,
                        onLaunch = { viewModel.launchApp(it) },
                        onSwipeUp = { activity.dispatchGesture(uiState.state.gestures.swipeUp) },
                        onSwipeDown = { activity.dispatchGesture(uiState.state.gestures.swipeDown) },
                        onDoubleTap = { activity.dispatchGesture(uiState.state.gestures.doubleTap) },
                        onLongPress = { activity.dispatchGesture(uiState.state.gestures.longPress) },
                        onOpenSettings = { router.push(Screen.SettingsRoot) },
                        onOpenFocus = { router.push(Screen.SettingsFocus) },
                        pendingOpenPageId = pendingOpenPageId,
                        onConsumePendingOpenPage = viewModel::consumePendingOpenPage,
                    )
                } else {
                    HomeScreen(
                        uiState = uiState,
                        onLaunch = { viewModel.launchApp(it) },
                        onSwipeUp = { activity.dispatchGesture(uiState.state.gestures.swipeUp) },
                        onSwipeDown = { activity.dispatchGesture(uiState.state.gestures.swipeDown) },
                        onSwipeLeft = { activity.dispatchGesture(uiState.state.gestures.swipeLeft) },
                        onSwipeRight = { activity.dispatchGesture(uiState.state.gestures.swipeRight) },
                        onDoubleTap = { activity.dispatchGesture(uiState.state.gestures.doubleTap) },
                        onLongPress = { activity.dispatchGesture(uiState.state.gestures.longPress) },
                        onOpenFocus = { router.push(Screen.SettingsFocus) },
                        onOpenNotifications = { router.push(Screen.NotificationsList) },
                    )
                }

                is Screen.Search -> SearchScreen(
                    uiState = uiState,
                    autoFocusKeyboard = uiState.settings.searchAutoKeyboard && screen.autoFocusKeyboard,
                    onLaunch = {
                        viewModel.launchApp(it)
                        router.pop()
                    },
                    onLaunchFromSearch = { app, query ->
                        viewModel.launchAppFromSearch(app, query)
                        router.pop()
                    },
                    onLaunchShortcut = {
                        viewModel.launchShortcut(it)
                        router.pop()
                    },
                    onBack = { router.pop() },
                    onToggleFavorite = viewModel::setFavorite,
                    onToggleHidden = viewModel::setHidden,
                    onRename = viewModel::setAlias,
                    onAppInfo = viewModel::openAppInfo,
                    onUninstall = viewModel::uninstall,
                )

                Screen.SettingsRoot -> SettingsRootScreen(
                    onBack = { router.pop() },
                    onNavigate = { router.push(it) },
                )

                Screen.SettingsHome -> HomeSettingsScreen(
                    uiState = uiState,
                    onUpdate = viewModel::updateSettings,
                    onNavigate = { router.push(it) },
                    onBack = { router.pop() },
                )

                Screen.SettingsProfiles -> ProfilesSettingsScreen(
                    uiState = uiState,
                    onAdd = viewModel::addProfile,
                    onSwitch = viewModel::switchProfile,
                    onRename = viewModel::renameProfile,
                    onDuplicate = viewModel::duplicateProfile,
                    onDelete = viewModel::deleteProfile,
                    onBack = { router.pop() },
                )

                Screen.SettingsApps -> AppsSettingsScreen(
                    uiState = uiState,
                    onToggleFavorite = viewModel::setFavorite,
                    onToggleHidden = viewModel::setHidden,
                    onRename = viewModel::setAlias,
                    onMoveFavorite = viewModel::moveFavorite,
                    onSetGroup = viewModel::setGroup,
                    onAddGroup = viewModel::addGroup,
                    onRenameGroup = viewModel::renameGroup,
                    onDeleteGroup = viewModel::deleteGroup,
                    onAppInfo = viewModel::openAppInfo,
                    onUninstall = viewModel::uninstall,
                    onBack = { router.pop() },
                )

                Screen.SettingsPages -> PagesSettingsScreen(
                    uiState = uiState,
                    onAddPage = viewModel::addPage,
                    onRenamePage = viewModel::renamePage,
                    onDeletePage = viewModel::deletePage,
                    onSetPageHidden = viewModel::setPageHidden,
                    onMovePage = viewModel::movePage,
                    onAddAppToPage = viewModel::addAppToPage,
                    onRemoveAppFromPage = viewModel::removeAppFromPage,
                    onMoveAppInPage = viewModel::moveAppInPage,
                    onSetCover = viewModel::setCover,
                    onSetBackCover = viewModel::setBackCover,
                    onSetPageIndicatorEnabled = viewModel::setPageIndicatorEnabled,
                    onSetPageFlipEnabled = { enabled -> viewModel.updateSettings { s -> s.copy(bookPageFlipEnabled = enabled) } },
                    onSetPageCustomStyleEnabled = viewModel::setPageCustomStyleEnabled,
                    onSetPageStyle = viewModel::setPageStyle,
                    onBack = { router.pop() },
                )

                Screen.SettingsTypography -> TypographySettingsScreen(uiState, viewModel::updateSettings, onBack = { router.pop() })
                Screen.SettingsLayout -> LayoutSettingsScreen(uiState, viewModel::updateSettings, onBack = { router.pop() })

                Screen.SettingsPresets -> PresetsSettingsScreen(
                    uiState = uiState,
                    onApply = viewModel::applyPreset,
                    onSave = viewModel::saveCurrentAsPreset,
                    onDuplicate = viewModel::duplicatePreset,
                    onRename = viewModel::renamePreset,
                    onDelete = viewModel::deletePreset,
                    onBack = { router.pop() },
                )
                Screen.SettingsClock -> ClockSettingsScreen(uiState, viewModel::updateSettings, onBack = { router.pop() })
                Screen.SettingsDate -> DateSettingsScreen(uiState, viewModel::updateSettings, onBack = { router.pop() })
                Screen.SettingsSearch -> SearchSettingsScreen(
                    uiState = uiState,
                    onUpdate = viewModel::updateSettings,
                    onResetSearchLearning = viewModel::resetSearchLearning,
                    onBack = { router.pop() },
                )
                Screen.SettingsGestures -> GesturesSettingsScreen(uiState, viewModel::setGestures, onBack = { router.pop() })

                Screen.SettingsShortcuts -> ShortcutsSettingsScreen(
                    uiState = uiState,
                    onAdd = viewModel::addShortcut,
                    onRemove = viewModel::removeShortcut,
                    onBack = { router.pop() },
                )

                Screen.SettingsAppearance -> AppearanceSettingsScreen(
                    uiState = uiState,
                    onUpdate = viewModel::updateSettings,
                    onSetHomeMode = viewModel::setHomeMode,
                    onBack = { router.pop() },
                )
                Screen.SettingsBehavior -> BehaviorSettingsScreen(uiState, viewModel::updateSettings, onBack = { router.pop() })
                Screen.SettingsNotifications -> NotificationsSettingsScreen(
                    settings = uiState.settings,
                    onUpdate = viewModel::updateSettings,
                    onOpenNotifications = { router.push(Screen.NotificationsList) },
                    onBack = { router.pop() },
                )

                Screen.SettingsFocus -> FocusSettingsScreen(
                    uiState = uiState,
                    onStart = viewModel::startFocus,
                    onStop = viewModel::stopFocus,
                    onSetAllowedApps = viewModel::setFocusAllowedApps,
                    onBack = { router.pop() },
                )

                Screen.NotificationsList -> NotificationsListScreen(onBack = { router.pop() })

                Screen.SettingsProductivity -> ProductivitySettingsScreen(
                    settings = uiState.settings,
                    onUpdate = viewModel::updateSettings,
                    onRequestCalendarPermission = { activity.requestCalendarAccess() },
                    onOpenAgenda = { router.push(Screen.Agenda) },
                    onOpenUsage = { router.push(Screen.UsageStats) },
                    onBack = { router.pop() },
                )

                Screen.Agenda -> AgendaScreen(
                    onRequestPermission = { activity.requestCalendarAccess() },
                    onBack = { router.pop() },
                )

                Screen.UsageStats -> UsageStatsScreen(onBack = { router.pop() })

                Screen.SettingsAutomation -> AutomationSettingsScreen(
                    uiState = uiState,
                    onAdd = viewModel::addAutomationRule,
                    onUpdate = viewModel::updateAutomationRule,
                    onDelete = viewModel::deleteAutomationRule,
                    onSetEnabled = viewModel::setAutomationRuleEnabled,
                    onBack = { router.pop() },
                )

                Screen.SettingsBackup -> BackupSettingsScreen(
                    exportJson = { viewModel.exportBackupJson() },
                    importJson = { viewModel.importBackupJson(it) },
                    onBack = { router.pop() },
                )

                Screen.SettingsAdvanced -> AdvancedSettingsScreen(
                    onResetAppearance = viewModel::resetAppearance,
                    onResetGestures = viewModel::resetGestures,
                    onResetAppLayout = viewModel::resetAppLayout,
                    onResetLauncherMisc = viewModel::resetLauncherMisc,
                    onResetEverything = { viewModel.resetEverything(); router.popToHome() },
                    onBack = { router.pop() },
                )

                Screen.SettingsAbout -> AboutSettingsScreen(onBack = { router.pop() })
            }
        }
    }
}

@Composable
private fun SystemBarsEffect(statusBarVisible: Boolean, theme: ThemeStyle) {
    val view = LocalView.current
    if (view.isInEditMode) return
    LaunchedEffect(statusBarVisible, theme) {
        val window = (view.context as? android.app.Activity)?.window ?: return@LaunchedEffect
        val controller = WindowCompat.getInsetsController(window, view)
        if (statusBarVisible) {
            controller.show(WindowInsetsCompat.Type.statusBars())
        } else {
            controller.hide(WindowInsetsCompat.Type.statusBars())
        }
        controller.isAppearanceLightStatusBars = theme == ThemeStyle.WHITE
    }
}
