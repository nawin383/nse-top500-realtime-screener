package com.puretext.launcher.ui.productivity

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
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
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.unit.dp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import com.puretext.launcher.ui.components.LauncherText
import com.puretext.launcher.ui.components.SettingsScaffold
import com.puretext.launcher.ui.theme.LocalLauncherColors
import com.puretext.launcher.util.UsageAccess

/** Read-only, text-only "today's screen time per app" list -- see [UsageAccess]. */
@Composable
fun UsageStatsScreen(onBack: () -> Unit, modifier: Modifier = Modifier) {
    val colors = LocalLauncherColors.current
    val context = LocalContext.current
    var granted by remember { mutableStateOf(UsageAccess.isEnabled(context)) }
    var entries by remember { mutableStateOf(UsageAccess.todayUsage(context)) }

    val lifecycleOwner = LocalLifecycleOwner.current
    DisposableEffect(lifecycleOwner) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_RESUME) {
                granted = UsageAccess.isEnabled(context)
                entries = UsageAccess.todayUsage(context)
            }
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose { lifecycleOwner.lifecycle.removeObserver(observer) }
    }

    SettingsScaffold(title = "App Usage Today", onBack = onBack, modifier = modifier) { contentModifier ->
        Column(modifier = contentModifier.verticalScroll(rememberScrollState())) {
            if (!granted) {
                LauncherText(
                    text = "Usage access isn't granted yet.",
                    fontSizeSp = 14,
                    color = colors.foreground.copy(alpha = 0.7f),
                    applyCase = false,
                    modifier = Modifier.padding(bottom = 8.dp),
                )
                LauncherText(
                    text = "Grant Usage Access",
                    fontSizeSp = 15,
                    color = colors.foreground,
                    applyCase = false,
                    modifier = Modifier.fillMaxWidth().clickable { UsageAccess.openSettings(context) }.padding(vertical = 10.dp),
                )
            } else if (entries.isEmpty()) {
                LauncherText(
                    text = "No usage recorded yet today.",
                    fontSizeSp = 14,
                    color = colors.foreground.copy(alpha = 0.5f),
                    applyCase = false,
                    modifier = Modifier.padding(top = 8.dp),
                )
            } else {
                entries.forEachIndexed { index, entry ->
                    Row(
                        modifier = Modifier.fillMaxWidth().padding(vertical = 8.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.SpaceBetween,
                    ) {
                        LauncherText(text = entry.label, fontSizeSp = 16, color = colors.foreground, applyCase = false, modifier = Modifier.weight(1f))
                        LauncherText(text = formatDuration(entry.foregroundMillis), fontSizeSp = 14, color = colors.foreground.copy(alpha = 0.6f), applyCase = false)
                    }
                    if (index != entries.lastIndex) Box(Modifier.padding(top = 2.dp))
                }
            }
        }
    }
}

private fun formatDuration(millis: Long): String {
    val totalMinutes = (millis / 60_000L).coerceAtLeast(0)
    val hours = totalMinutes / 60
    val minutes = totalMinutes % 60
    return if (hours > 0) "${hours}h ${minutes}m" else "${minutes}m"
}
