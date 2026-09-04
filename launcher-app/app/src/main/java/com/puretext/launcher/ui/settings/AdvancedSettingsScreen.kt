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
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.puretext.launcher.gestures.LockAccessibilityService
import com.puretext.launcher.ui.components.ConfirmDialog
import com.puretext.launcher.ui.components.LauncherText
import com.puretext.launcher.ui.components.SectionLabel
import com.puretext.launcher.ui.components.SettingsScaffold
import com.puretext.launcher.ui.theme.LocalLauncherColors

private enum class ResetKind(val title: String, val description: String) {
    APPEARANCE("Reset Appearance", "Theme, typography, layout, clock, date, and battery display"),
    GESTURES("Reset Gestures", "Back to the default swipe and tap actions"),
    APP_LAYOUT("Reset App Layout", "Favorites, order, and groups"),
    LAUNCHER("Reset Launcher", "Search, behavior, notifications, and shortcuts"),
    EVERYTHING("Reset Everything", "All settings above, back to first install"),
}

@Composable
fun AdvancedSettingsScreen(
    onResetAppearance: () -> Unit,
    onResetGestures: () -> Unit,
    onResetAppLayout: () -> Unit,
    onResetLauncherMisc: () -> Unit,
    onResetEverything: () -> Unit,
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = LocalLauncherColors.current
    val context = LocalContext.current
    var confirming by remember { mutableStateOf<ResetKind?>(null) }

    SettingsScaffold(title = "Advanced", onBack = onBack, modifier = modifier) { contentModifier ->
        Column(modifier = contentModifier.verticalScroll(rememberScrollState())) {
            SectionLabel("Reset")
            ResetKind.entries.forEach { kind ->
                ResetRow(kind) { confirming = kind }
            }

            SectionLabel("Accessibility")
            LauncherText(
                text = "Enable the Lock Screen gesture action in system Accessibility settings. " +
                    "Off by default; this app never turns it on for you.",
                fontSizeSp = 13,
                color = colors.foreground.copy(alpha = 0.6f),
                applyCase = false,
                modifier = Modifier.padding(bottom = 8.dp),
            )
            LauncherText(
                text = "Open Accessibility Settings",
                fontSizeSp = 15,
                color = colors.foreground,
                applyCase = false,
                modifier = Modifier.fillMaxWidth()
                    .clickable { LockAccessibilityService.openAccessibilitySettings(context) }
                    .padding(vertical = 10.dp),
            )
        }
    }

    confirming?.let { kind ->
        ConfirmDialog(
            title = "${kind.title}?",
            message = "${kind.description}. This cannot be undone.",
            confirmLabel = "Reset",
            onConfirm = {
                when (kind) {
                    ResetKind.APPEARANCE -> onResetAppearance()
                    ResetKind.GESTURES -> onResetGestures()
                    ResetKind.APP_LAYOUT -> onResetAppLayout()
                    ResetKind.LAUNCHER -> onResetLauncherMisc()
                    ResetKind.EVERYTHING -> onResetEverything()
                }
                confirming = null
            },
            onDismiss = { confirming = null },
        )
    }
}

@Composable
private fun ResetRow(kind: ResetKind, onClick: () -> Unit) {
    val colors = LocalLauncherColors.current
    Column(
        modifier = Modifier.fillMaxWidth().clickable(onClick = onClick).padding(vertical = 10.dp),
    ) {
        LauncherText(text = kind.title, fontSizeSp = 16, color = colors.foreground)
        LauncherText(
            text = kind.description,
            fontSizeSp = 12,
            color = colors.foreground.copy(alpha = 0.55f),
            applyCase = false,
        )
    }
}
