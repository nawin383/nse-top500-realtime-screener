package com.puretext.launcher.ui.settings

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import com.puretext.launcher.LauncherUiState
import com.puretext.launcher.data.AppSettings
import com.puretext.launcher.data.DatePreset
import com.puretext.launcher.ui.components.CycleRow
import com.puretext.launcher.ui.components.SectionLabel
import com.puretext.launcher.ui.components.SettingsScaffold
import com.puretext.launcher.ui.components.ToggleRow
import com.puretext.launcher.util.next

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

@Composable
fun SearchSettingsScreen(
    uiState: LauncherUiState,
    onUpdate: ((AppSettings) -> AppSettings) -> Unit,
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val settings = uiState.settings
    SettingsScaffold(title = "Search", onBack = onBack, modifier = modifier) { contentModifier ->
        Column(modifier = contentModifier.verticalScroll(rememberScrollState())) {
            ToggleRow("Open keyboard automatically", settings.searchAutoKeyboard, onToggle = { onUpdate { s -> s.copy(searchAutoKeyboard = it) } })
            ToggleRow("Include hidden apps in results", settings.searchIncludeHidden, onToggle = { onUpdate { s -> s.copy(searchIncludeHidden = it) } })
            ToggleRow("Also search package name", settings.searchByPackageName, onToggle = { onUpdate { s -> s.copy(searchByPackageName = it) } })
        }
    }
}
