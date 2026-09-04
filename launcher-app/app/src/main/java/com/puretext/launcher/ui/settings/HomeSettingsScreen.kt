package com.puretext.launcher.ui.settings

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import com.puretext.launcher.LauncherUiState
import com.puretext.launcher.data.AppSettings
import com.puretext.launcher.ui.components.NavRow
import com.puretext.launcher.ui.components.SectionLabel
import com.puretext.launcher.ui.components.SettingsScaffold
import com.puretext.launcher.ui.components.ToggleRow
import com.puretext.launcher.ui.navigation.Screen

@Composable
fun HomeSettingsScreen(
    uiState: LauncherUiState,
    onUpdate: ((AppSettings) -> AppSettings) -> Unit,
    onNavigate: (Screen) -> Unit,
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val settings = uiState.settings
    SettingsScaffold(title = "Home", onBack = onBack, modifier = modifier) { contentModifier ->
        Column(modifier = contentModifier.verticalScroll(rememberScrollState())) {
            ToggleRow("Show battery percentage", settings.batteryEnabled, onToggle = { onUpdate { s -> s.copy(batteryEnabled = it) } })

            SectionLabel("Manage")
            NavRow("Apps on home screen", "Favorites, order, hidden apps", onClick = { onNavigate(Screen.SettingsApps) })
            NavRow("Pages", "Book Mode pages, cover, back cover", onClick = { onNavigate(Screen.SettingsPages) })
            NavRow("Clock", "Format, seconds", onClick = { onNavigate(Screen.SettingsClock) })
            NavRow("Date", "Format", onClick = { onNavigate(Screen.SettingsDate) })
            NavRow("Layout", "Position, margins, spacing", onClick = { onNavigate(Screen.SettingsLayout) })
        }
    }
}
