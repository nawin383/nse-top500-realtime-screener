package com.puretext.launcher.ui.settings

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.puretext.launcher.LauncherUiState
import com.puretext.launcher.data.AppSettings
import com.puretext.launcher.data.AutoLaunchLevel
import com.puretext.launcher.data.DatePreset
import com.puretext.launcher.ui.components.ConfirmDialog
import com.puretext.launcher.ui.components.CycleRow
import com.puretext.launcher.ui.components.LauncherText
import com.puretext.launcher.ui.components.SectionLabel
import com.puretext.launcher.ui.components.SettingsScaffold
import com.puretext.launcher.ui.components.ToggleRow
import com.puretext.launcher.ui.theme.LocalLauncherColors
import com.puretext.launcher.util.next
import com.puretext.launcher.util.titleCase

@Composable
fun ClockSettingsScreen(
    uiState: LauncherUiState,
    onUpdate: ((AppSettings) -> AppSettings) -> Unit,
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val settings = uiState.settings
    SettingsScaffold(title = "Clock", onBack = onBack, modifier = modifier) { contentModifier ->
        Column(modifier = contentModifier.verticalScroll(rememberScrollState())) {
            ToggleRow("Show clock", settings.clockEnabled, onToggle = { onUpdate { s -> s.copy(clockEnabled = it) } })
            ToggleRow("24-hour format", settings.clock24Hour, onToggle = { onUpdate { s -> s.copy(clock24Hour = it) } })
            ToggleRow("Show seconds", settings.clockShowSeconds, onToggle = { onUpdate { s -> s.copy(clockShowSeconds = it) } })
        }
    }
}

private fun dateExample(preset: DatePreset): String = when (preset) {
    DatePreset.LONG -> "Wednesday, 03 September"
    DatePreset.SHORT -> "Wed, 03 Sep"
    DatePreset.NUMERIC -> "03/09/2026"
    DatePreset.ISO -> "2026-09-03"
}

@Composable
fun DateSettingsScreen(
    uiState: LauncherUiState,
    onUpdate: ((AppSettings) -> AppSettings) -> Unit,
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val settings = uiState.settings
    SettingsScaffold(title = "Date", onBack = onBack, modifier = modifier) { contentModifier ->
        Column(modifier = contentModifier.verticalScroll(rememberScrollState())) {
            ToggleRow("Show date", settings.dateEnabled, onToggle = { onUpdate { s -> s.copy(dateEnabled = it) } })
            SectionLabel("Format")
            CycleRow(
                label = "Style",
                valueLabel = dateExample(settings.datePreset),
                onClick = { onUpdate { s -> s.copy(datePreset = s.datePreset.next()) } },
            )
        }
    }
}

private val DELAY_OPTIONS = listOf(100, 250, 500, 750, 1000)

@Composable
fun SearchSettingsScreen(
    uiState: LauncherUiState,
    onUpdate: ((AppSettings) -> AppSettings) -> Unit,
    onResetSearchLearning: () -> Unit,
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val settings = uiState.settings
    val colors = LocalLauncherColors.current
    var confirmResetLearning by remember { mutableStateOf(false) }

    SettingsScaffold(title = "Search", onBack = onBack, modifier = modifier) { contentModifier ->
        Column(modifier = contentModifier.verticalScroll(rememberScrollState())) {
            ToggleRow("Open keyboard automatically", settings.searchAutoKeyboard, onToggle = { onUpdate { s -> s.copy(searchAutoKeyboard = it) } })
            ToggleRow("Include hidden apps in results", settings.searchIncludeHidden, onToggle = { onUpdate { s -> s.copy(searchIncludeHidden = it) } })
            ToggleRow("Also search package name", settings.searchByPackageName, onToggle = { onUpdate { s -> s.copy(searchByPackageName = it) } })

            SectionLabel("Predictive Launch")
            LauncherText(
                text = "Auto-open the top match after a short delay -- only once it's a clear, learned winner for what you typed.",
                fontSizeSp = 13,
                color = colors.foreground.copy(alpha = 0.6f),
                applyCase = false,
                modifier = Modifier.padding(bottom = 4.dp),
            )
            CycleRow(
                label = "Sensitivity",
                valueLabel = titleCase(settings.autoLaunchLevel.name),
                onClick = { onUpdate { s -> s.copy(autoLaunchLevel = s.autoLaunchLevel.next()) } },
            )
            if (settings.autoLaunchLevel != AutoLaunchLevel.OFF) {
                CycleRow(
                    label = "Delay",
                    valueLabel = "${settings.autoLaunchDelayMs} ms",
                    onClick = {
                        val currentIndex = DELAY_OPTIONS.indexOf(settings.autoLaunchDelayMs).let { if (it < 0) 2 else it }
                        val next = DELAY_OPTIONS[(currentIndex + 1) % DELAY_OPTIONS.size]
                        onUpdate { s -> s.copy(autoLaunchDelayMs = next) }
                    },
                )
            }

            SectionLabel("Search Learning")
            ToggleRow(
                "Learn from what you launch",
                settings.searchLearningEnabled,
                onToggle = { onUpdate { s -> s.copy(searchLearningEnabled = it) } },
            )
            LauncherText(
                text = "Reset Search Learning",
                fontSizeSp = 15,
                color = colors.foreground,
                applyCase = false,
                modifier = Modifier.fillMaxWidth().clickable { confirmResetLearning = true }.padding(vertical = 10.dp),
            )
        }
    }

    if (confirmResetLearning) {
        ConfirmDialog(
            title = "Reset search learning?",
            message = "Forgets which app you usually mean for each query. This cannot be undone.",
            confirmLabel = "Reset",
            onConfirm = {
                onResetSearchLearning()
                confirmResetLearning = false
            },
            onDismiss = { confirmResetLearning = false },
        )
    }
}
