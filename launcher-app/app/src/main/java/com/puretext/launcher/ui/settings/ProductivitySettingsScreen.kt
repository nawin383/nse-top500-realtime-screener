package com.puretext.launcher.ui.settings

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.unit.dp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import com.puretext.launcher.data.AppSettings
import com.puretext.launcher.ui.components.LauncherText
import com.puretext.launcher.ui.components.NavRow
import com.puretext.launcher.ui.components.SectionLabel
import com.puretext.launcher.ui.components.SettingsScaffold
import com.puretext.launcher.ui.components.ToggleRow
import com.puretext.launcher.ui.theme.LocalLauncherColors
import com.puretext.launcher.util.Agenda
import com.puretext.launcher.util.UsageAccess

/**
 * Two independent opt-in features, each following the same pattern: a
 * toggle turns the feature on, and only then is the system permission (a
 * runtime request for Calendar, a deep link to Usage Access settings for
 * usage stats) ever requested -- neither is asked for at first launch or
 * touched while the toggle is off.
 */
@Composable
fun ProductivitySettingsScreen(
    settings: AppSettings,
    onUpdate: ((AppSettings) -> AppSettings) -> Unit,
    onRequestCalendarPermission: () -> Unit,
    onOpenAgenda: () -> Unit,
    onOpenUsage: () -> Unit,
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = LocalLauncherColors.current
    val context = LocalContext.current
    var calendarGranted by remember { mutableStateOf(Agenda.hasPermission(context)) }
    var usageGranted by remember { mutableStateOf(UsageAccess.isEnabled(context)) }

    val lifecycleOwner = LocalLifecycleOwner.current
    DisposableEffect(lifecycleOwner) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_RESUME) {
                calendarGranted = Agenda.hasPermission(context)
                usageGranted = UsageAccess.isEnabled(context)
            }
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose { lifecycleOwner.lifecycle.removeObserver(observer) }
    }

    SettingsScaffold(title = "Productivity", onBack = onBack, modifier = modifier) { contentModifier ->
        Column(modifier = contentModifier.verticalScroll(rememberScrollState())) {
            SectionLabel("Today's Agenda")
            ToggleRow(
                "Show today's calendar events",
                settings.agendaEnabled,
                onToggle = { enabled ->
                    onUpdate { s -> s.copy(agendaEnabled = enabled) }
                    if (enabled && !calendarGranted) onRequestCalendarPermission()
                },
            )
            LauncherText(
                text = if (calendarGranted) "Calendar access is granted." else "Calendar access is not granted.",
                fontSizeSp = 13,
                color = colors.foreground.copy(alpha = 0.6f),
                applyCase = false,
                modifier = Modifier.padding(bottom = 4.dp),
            )
            if (settings.agendaEnabled) {
                NavRow("View Agenda", "Today's events", onClick = onOpenAgenda)
            }

            SectionLabel("App Usage")
            ToggleRow(
                "Show today's app usage",
                settings.usageStatsEnabled,
                onToggle = { enabled -> onUpdate { s -> s.copy(usageStatsEnabled = enabled) } },
            )
            LauncherText(
                text = if (usageGranted) "Usage access is granted." else "Usage access is not granted.",
                fontSizeSp = 13,
                color = colors.foreground.copy(alpha = 0.6f),
                applyCase = false,
                modifier = Modifier.padding(bottom = 4.dp),
            )
            if (settings.usageStatsEnabled && !usageGranted) {
                LauncherText(
                    text = "Grant Usage Access",
                    fontSizeSp = 15,
                    color = colors.foreground,
                    applyCase = false,
                    modifier = Modifier.fillMaxWidth().clickable { UsageAccess.openSettings(context) }.padding(vertical = 10.dp),
                )
            }
            if (settings.usageStatsEnabled) {
                NavRow("View Usage", "Screen time today", onClick = onOpenUsage)
            }
        }
    }
}
