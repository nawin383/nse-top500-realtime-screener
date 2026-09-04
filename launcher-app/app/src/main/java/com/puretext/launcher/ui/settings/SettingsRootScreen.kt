package com.puretext.launcher.ui.settings

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.puretext.launcher.ui.components.LauncherText
import com.puretext.launcher.ui.components.NavRow
import com.puretext.launcher.ui.navigation.Screen
import com.puretext.launcher.ui.theme.LocalLauncherColors

private data class SettingsCategory(val label: String, val description: String, val screen: Screen)

private val CATEGORIES = listOf(
    SettingsCategory("Home", "What shows on your home screen", Screen.SettingsHome),
    SettingsCategory("Profiles", "Separate app sets and pages, e.g. Work / Personal", Screen.SettingsProfiles),
    SettingsCategory("Focus Mode", "Time-boxed home screen with only allowed apps", Screen.SettingsFocus),
    SettingsCategory("Productivity", "Today's agenda and app usage, both opt-in", Screen.SettingsProductivity),
    SettingsCategory("Apps", "Show, hide, rename, reorder, group", Screen.SettingsApps),
    SettingsCategory("Pages", "Book Mode pages, cover, back cover", Screen.SettingsPages),
    SettingsCategory("Typography", "Font, size, spacing, case", Screen.SettingsTypography),
    SettingsCategory("Layout", "Margins, alignment, position", Screen.SettingsLayout),
    SettingsCategory("Presets", "Built-in and custom style bundles", Screen.SettingsPresets),
    SettingsCategory("Clock", "Time format, seconds", Screen.SettingsClock),
    SettingsCategory("Date", "Date format", Screen.SettingsDate),
    SettingsCategory("Search", "Keyboard, hidden apps, package search", Screen.SettingsSearch),
    SettingsCategory("Gestures", "Swipe, double tap, long press", Screen.SettingsGestures),
    SettingsCategory("Shortcuts", "Quick text links to apps, sites, settings", Screen.SettingsShortcuts),
    SettingsCategory("Appearance", "Black or white, animations", Screen.SettingsAppearance),
    SettingsCategory("Behavior", "Status bar, recent apps", Screen.SettingsBehavior),
    SettingsCategory("Notifications", "Notification count on home", Screen.SettingsNotifications),
    SettingsCategory("Backup", "Export and import your settings", Screen.SettingsBackup),
    SettingsCategory("Advanced", "Reset options", Screen.SettingsAdvanced),
    SettingsCategory("About", "Version and philosophy", Screen.SettingsAbout),
)

@Composable
fun SettingsRootScreen(onBack: () -> Unit, onNavigate: (Screen) -> Unit, modifier: Modifier = Modifier) {
    val colors = LocalLauncherColors.current
    Column(
        modifier = modifier
            .fillMaxSize()
            .background(colors.background)
            .padding(horizontal = 24.dp),
    ) {
        LauncherText(
            text = "< Back",
            fontSizeSp = 15,
            color = colors.foreground,
            applyCase = false,
            modifier = Modifier
                .clickable(onClick = onBack)
                .padding(top = 20.dp, bottom = 8.dp),
        )
        LauncherText(text = "LAUNCHER SETTINGS", fontSizeSp = 24, color = colors.foreground, modifier = Modifier.padding(bottom = 8.dp))
        LazyColumn {
            items(CATEGORIES) { category ->
                NavRow(
                    label = category.label,
                    description = category.description,
                    onClick = { onNavigate(category.screen) },
                )
            }
        }
    }
}
