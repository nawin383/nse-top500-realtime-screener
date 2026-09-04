package com.puretext.launcher.ui.settings

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.puretext.launcher.BuildConfig
import com.puretext.launcher.LauncherUiState
import com.puretext.launcher.data.AppSettings
import com.puretext.launcher.data.ThemeStyle
import com.puretext.launcher.ui.components.CycleRow
import com.puretext.launcher.ui.components.LauncherText
import com.puretext.launcher.ui.components.SectionLabel
import com.puretext.launcher.ui.components.SettingsScaffold
import com.puretext.launcher.ui.components.ToggleRow
import com.puretext.launcher.ui.theme.LocalLauncherColors

@Composable
fun AppearanceSettingsScreen(
    uiState: LauncherUiState,
    onUpdate: ((AppSettings) -> AppSettings) -> Unit,
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val settings = uiState.settings
    SettingsScaffold(title = "Appearance", onBack = onBack, modifier = modifier) { contentModifier ->
        Column(modifier = contentModifier.verticalScroll(rememberScrollState())) {
            CycleRow(
                label = "Style",
                valueLabel = settings.theme.name,
                onClick = {
                    onUpdate { s -> s.copy(theme = if (s.theme == ThemeStyle.BLACK) ThemeStyle.WHITE else ThemeStyle.BLACK) }
                },
            )
            if (settings.theme == ThemeStyle.BLACK) {
                ToggleRow("True AMOLED black", settings.trueAmoled, onToggle = { onUpdate { s -> s.copy(trueAmoled = it) } })
            }
            ToggleRow("Animations", settings.animationsEnabled, onToggle = { onUpdate { s -> s.copy(animationsEnabled = it) } })
        }
    }
}

@Composable
fun BehaviorSettingsScreen(
    uiState: LauncherUiState,
    onUpdate: ((AppSettings) -> AppSettings) -> Unit,
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val settings = uiState.settings
    SettingsScaffold(title = "Behavior", onBack = onBack, modifier = modifier) { contentModifier ->
        Column(modifier = contentModifier.verticalScroll(rememberScrollState())) {
            ToggleRow("Show status bar", settings.statusBarVisible, onToggle = { onUpdate { s -> s.copy(statusBarVisible = it) } })
            ToggleRow("Remember recent apps", settings.recentAppsEnabled, onToggle = { onUpdate { s -> s.copy(recentAppsEnabled = it) } })
        }
    }
}

@Composable
fun AboutSettingsScreen(onBack: () -> Unit, modifier: Modifier = Modifier) {
    val colors = LocalLauncherColors.current
    SettingsScaffold(title = "About", onBack = onBack, modifier = modifier) { contentModifier ->
        Column(modifier = contentModifier.verticalScroll(rememberScrollState())) {
            LauncherText(text = "Pure Launcher", fontSizeSp = 18, color = colors.foreground)
            Box(Modifier.padding(top = 4.dp))
            LauncherText(
                text = "Version ${BuildConfig.VERSION_NAME}",
                fontSizeSp = 14,
                color = colors.foreground.copy(alpha = 0.6f),
                applyCase = false,
            )
            SectionLabel("Philosophy")
            LauncherText(
                text = "Zero visual noise. Maximum control. Text is the interface.",
                fontSizeSp = 14,
                color = colors.foreground.copy(alpha = 0.8f),
                applyCase = false,
            )
            SectionLabel("Privacy")
            LauncherText(
                text = "Local-first. No analytics, no tracking, no advertising, no network access. " +
                    "Everything you set here stays on this device unless you export a backup yourself.",
                fontSizeSp = 14,
                color = colors.foreground.copy(alpha = 0.8f),
                applyCase = false,
            )
        }
    }
}
