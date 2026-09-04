package com.puretext.launcher.ui.settings

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.puretext.launcher.LauncherUiState
import com.puretext.launcher.data.AppSettings
import com.puretext.launcher.ui.components.CycleRow
import com.puretext.launcher.ui.components.FloatStepperRow
import com.puretext.launcher.ui.components.LauncherText
import com.puretext.launcher.ui.components.SectionLabel
import com.puretext.launcher.ui.components.SettingsScaffold
import com.puretext.launcher.ui.components.StepperRow
import com.puretext.launcher.ui.theme.LocalLauncherColors
import com.puretext.launcher.util.next
import com.puretext.launcher.util.titleCase

@Composable
fun TypographySettingsScreen(
    uiState: LauncherUiState,
    onUpdate: ((AppSettings) -> AppSettings) -> Unit,
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val settings = uiState.settings
    SettingsScaffold(title = "Typography", onBack = onBack, modifier = modifier) { contentModifier ->
        Column(modifier = contentModifier.verticalScroll(rememberScrollState())) {
            PreviewBlock(settings)

            SectionLabel("Font")
            CycleRow("Family", titleCase(settings.fontFamily.name), onClick = { onUpdate { it.copy(fontFamily = it.fontFamily.next()) } })
            CycleRow("Weight", titleCase(settings.fontWeight.name), onClick = { onUpdate { it.copy(fontWeight = it.fontWeight.next()) } })
            CycleRow("Case", titleCase(settings.textCase.name), onClick = { onUpdate { it.copy(textCase = it.textCase.next()) } })
            FloatStepperRow(
                label = "Letter Spacing",
                value = settings.letterSpacingSp,
                onChange = { onUpdate { s -> s.copy(letterSpacingSp = it) } },
                step = 0.5f,
                min = 0f,
                max = 6f,
            )
            FloatStepperRow(
                label = "Line Spacing",
                value = settings.lineSpacingMultiplier,
                onChange = { onUpdate { s -> s.copy(lineSpacingMultiplier = it) } },
                step = 0.1f,
                min = 0.8f,
                max = 2.5f,
            )

            SectionLabel("Sizes")
            StepperRow(
                label = "Clock",
                value = settings.clockTextSizeSp,
                onChange = { onUpdate { s -> s.copy(clockTextSizeSp = it) } },
                step = 4,
                min = 20,
                max = 120,
                suffix = " sp",
            )
            StepperRow(
                label = "Date",
                value = settings.dateTextSizeSp,
                onChange = { onUpdate { s -> s.copy(dateTextSizeSp = it) } },
                step = 2,
                min = 10,
                max = 40,
                suffix = " sp",
            )
            StepperRow(
                label = "App names",
                value = settings.appTextSizeSp,
                onChange = { onUpdate { s -> s.copy(appTextSizeSp = it) } },
                step = 2,
                min = 12,
                max = 40,
                suffix = " sp",
            )
            StepperRow(
                label = "Secondary text",
                value = settings.secondaryTextSizeSp,
                onChange = { onUpdate { s -> s.copy(secondaryTextSizeSp = it) } },
                step = 1,
                min = 10,
                max = 24,
                suffix = " sp",
            )
            Box(Modifier.padding(bottom = 32.dp))
        }
    }
}

@Composable
private fun PreviewBlock(settings: AppSettings) {
    val colors = LocalLauncherColors.current
    Column(Modifier.fillMaxWidth().padding(top = 4.dp, bottom = 8.dp)) {
        SectionLabel("Preview")
        LauncherText(text = "23:14", fontSizeSp = settings.clockTextSizeSp, color = colors.foreground)
        Box(Modifier.padding(top = 4.dp))
        LauncherText(text = "Wednesday", fontSizeSp = settings.dateTextSizeSp, color = colors.foreground)
        Box(Modifier.padding(top = 14.dp))
        listOf("Phone", "WhatsApp", "Chrome", "Gmail").forEach { name ->
            LauncherText(text = name, fontSizeSp = settings.appTextSizeSp, color = colors.foreground, modifier = Modifier.padding(vertical = 3.dp))
        }
    }
}
