package com.puretext.launcher.ui.settings

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.puretext.launcher.LauncherUiState
import com.puretext.launcher.data.AppSettings
import com.puretext.launcher.ui.components.CycleRow
import com.puretext.launcher.ui.components.SectionLabel
import com.puretext.launcher.ui.components.SettingsScaffold
import com.puretext.launcher.ui.components.StepperRow
import com.puretext.launcher.ui.components.ToggleRow
import com.puretext.launcher.util.next
import com.puretext.launcher.util.titleCase

@Composable
fun LayoutSettingsScreen(
    uiState: LauncherUiState,
    onUpdate: ((AppSettings) -> AppSettings) -> Unit,
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val settings = uiState.settings
    SettingsScaffold(title = "Layout", onBack = onBack, modifier = modifier) { contentModifier ->
        Column(modifier = contentModifier.verticalScroll(rememberScrollState())) {
            SectionLabel("Position")
            CycleRow("Alignment", titleCase(settings.homeAlignment.name), onClick = { onUpdate { it.copy(homeAlignment = it.homeAlignment.next()) } })
            CycleRow("Vertical position", titleCase(settings.verticalPosition.name), onClick = { onUpdate { it.copy(verticalPosition = it.verticalPosition.next()) } })
            ToggleRow("Compact layout", settings.compactLayout, onToggle = { onUpdate { s -> s.copy(compactLayout = it) } })

            SectionLabel("Margins")
            StepperRow("Top", settings.marginTopDp, onChange = { onUpdate { s -> s.copy(marginTopDp = it) } }, step = 4, min = 0, max = 120, suffix = " dp")
            StepperRow("Bottom", settings.marginBottomDp, onChange = { onUpdate { s -> s.copy(marginBottomDp = it) } }, step = 4, min = 0, max = 120, suffix = " dp")
            StepperRow("Left / Right", settings.marginHorizontalDp, onChange = { onUpdate { s -> s.copy(marginHorizontalDp = it) } }, step = 4, min = 0, max = 80, suffix = " dp")

            SectionLabel("Spacing")
            StepperRow("Between apps", settings.appSpacingDp, onChange = { onUpdate { s -> s.copy(appSpacingDp = it) } }, step = 2, min = 0, max = 48, suffix = " dp")
            StepperRow("Clock to date", settings.clockDateSpacingDp, onChange = { onUpdate { s -> s.copy(clockDateSpacingDp = it) } }, step = 2, min = 0, max = 32, suffix = " dp")
            StepperRow("Date to apps", settings.dateAppsSpacingDp, onChange = { onUpdate { s -> s.copy(dateAppsSpacingDp = it) } }, step = 4, min = 0, max = 96, suffix = " dp")
            Box(Modifier.padding(bottom = 32.dp))
        }
    }
}
