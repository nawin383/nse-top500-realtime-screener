package com.puretext.launcher.ui.settings

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.puretext.launcher.LauncherUiState
import com.puretext.launcher.data.AppInfo
import com.puretext.launcher.ui.components.LauncherText
import com.puretext.launcher.ui.components.SectionLabel
import com.puretext.launcher.ui.components.SettingsScaffold
import com.puretext.launcher.ui.theme.LocalLauncherColors
import kotlinx.coroutines.delay

/**
 * Time-boxed home-screen restriction: pick an allow-list, then start a
 * session (fixed duration or "until I turn it off"). While active, Home
 * only shows the allowed apps -- Search still works normally, this is a
 * distraction nudge, not a lockdown.
 */
@Composable
fun FocusSettingsScreen(
    uiState: LauncherUiState,
    onStart: (durationMinutes: Int?, allowedApps: List<AppInfo>) -> Unit,
    onStop: () -> Unit,
    onSetAllowedApps: (List<AppInfo>) -> Unit,
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = LocalLauncherColors.current
    var now by remember { mutableStateOf(System.currentTimeMillis()) }
    LaunchedEffect(Unit) {
        while (true) {
            now = System.currentTimeMillis()
            delay(5_000)
        }
    }

    val active = uiState.isFocusActive(now)
    val allowedKeys = remember(uiState.state.focus.allowedAppKeys) { uiState.state.focus.allowedAppKeys.toSet() }

    SettingsScaffold(title = "Focus Mode", onBack = onBack, modifier = modifier) { contentModifier ->
        Column(modifier = contentModifier) {
            LauncherText(
                text = if (active) {
                    val endsAt = uiState.state.focus.endsAtMillis
                    if (endsAt == null) "Focus is ON -- until you turn it off." else "Focus is ON -- ${remainingLabel(endsAt - now)} left."
                } else {
                    "Focus is OFF."
                },
                fontSizeSp = 16,
                color = colors.foreground,
                applyCase = false,
                modifier = Modifier.padding(bottom = 8.dp),
            )
            if (active) {
                LauncherText(
                    text = "End Focus Now",
                    fontSizeSp = 15,
                    color = colors.foreground,
                    applyCase = false,
                    modifier = Modifier.fillMaxWidth().clickable(onClick = onStop).padding(vertical = 10.dp),
                )
            }

            SectionLabel("Start a Session")
            LauncherText(
                text = "Only the apps checked below will show on your home screen until the session ends.",
                fontSizeSp = 13,
                color = colors.foreground.copy(alpha = 0.6f),
                applyCase = false,
                modifier = Modifier.padding(bottom = 8.dp),
            )
            Row(modifier = Modifier.fillMaxWidth().padding(bottom = 4.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                DurationButton("30 min", enabled = allowedKeys.isNotEmpty()) { onStart(30, uiState.allApps.filter { it.key in allowedKeys }) }
                DurationButton("1 hr", enabled = allowedKeys.isNotEmpty()) { onStart(60, uiState.allApps.filter { it.key in allowedKeys }) }
                DurationButton("2 hr", enabled = allowedKeys.isNotEmpty()) { onStart(120, uiState.allApps.filter { it.key in allowedKeys }) }
            }
            LauncherText(
                text = "Until I Turn It Off",
                fontSizeSp = 15,
                color = colors.foreground.copy(alpha = if (allowedKeys.isNotEmpty()) 1f else 0.35f),
                applyCase = false,
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable(enabled = allowedKeys.isNotEmpty()) { onStart(null, uiState.allApps.filter { it.key in allowedKeys }) }
                    .padding(vertical = 10.dp),
            )

            SectionLabel("Allowed Apps (${allowedKeys.size})")
            LazyColumn(modifier = Modifier.fillMaxWidth().weight(1f)) {
                items(uiState.visibleApps(includeHidden = true), key = { it.key }) { app ->
                    val isAllowed = app.key in allowedKeys
                    LauncherText(
                        text = if (isAllowed) "[x] ${uiState.displayName(app)}" else "[ ] ${uiState.displayName(app)}",
                        fontSizeSp = 16,
                        color = colors.foreground,
                        applyCase = false,
                        modifier = Modifier
                            .fillMaxWidth()
                            .clickable {
                                val newAllowed = if (isAllowed) allowedKeys - app.key else allowedKeys + app.key
                                onSetAllowedApps(uiState.allApps.filter { it.key in newAllowed })
                            }
                            .padding(vertical = 8.dp),
                    )
                }
            }
        }
    }
}

@Composable
private fun DurationButton(label: String, enabled: Boolean, onClick: () -> Unit) {
    val colors = LocalLauncherColors.current
    LauncherText(
        text = label,
        fontSizeSp = 15,
        color = colors.foreground.copy(alpha = if (enabled) 1f else 0.35f),
        applyCase = false,
        modifier = Modifier.clickable(enabled = enabled, onClick = onClick).padding(vertical = 10.dp, horizontal = 4.dp),
    )
}

private fun remainingLabel(millis: Long): String {
    val totalMinutes = (millis / 60_000L).coerceAtLeast(0)
    val hours = totalMinutes / 60
    val minutes = totalMinutes % 60
    return if (hours > 0) "${hours}h ${minutes}m" else "${minutes}m"
}
