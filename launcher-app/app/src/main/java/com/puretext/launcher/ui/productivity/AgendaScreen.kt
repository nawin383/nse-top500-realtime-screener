package com.puretext.launcher.ui.productivity

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Box
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
import com.puretext.launcher.ui.components.LauncherText
import com.puretext.launcher.ui.components.SettingsScaffold
import com.puretext.launcher.ui.theme.LocalLauncherColors
import com.puretext.launcher.util.Agenda
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/** Read-only, text-only list of today's calendar events -- see [Agenda]. */
@Composable
fun AgendaScreen(onRequestPermission: () -> Unit, onBack: () -> Unit, modifier: Modifier = Modifier) {
    val colors = LocalLauncherColors.current
    val context = LocalContext.current
    var granted by remember { mutableStateOf(Agenda.hasPermission(context)) }
    var events by remember { mutableStateOf(Agenda.todayEvents(context)) }

    val lifecycleOwner = LocalLifecycleOwner.current
    DisposableEffect(lifecycleOwner) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_RESUME) {
                granted = Agenda.hasPermission(context)
                events = Agenda.todayEvents(context)
            }
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose { lifecycleOwner.lifecycle.removeObserver(observer) }
    }

    SettingsScaffold(title = "Today's Agenda", onBack = onBack, modifier = modifier) { contentModifier ->
        Column(modifier = contentModifier.verticalScroll(rememberScrollState())) {
            if (!granted) {
                LauncherText(
                    text = "Calendar access isn't granted yet.",
                    fontSizeSp = 14,
                    color = colors.foreground.copy(alpha = 0.7f),
                    applyCase = false,
                    modifier = Modifier.padding(bottom = 8.dp),
                )
                LauncherText(
                    text = "Grant Calendar Access",
                    fontSizeSp = 15,
                    color = colors.foreground,
                    applyCase = false,
                    modifier = Modifier.fillMaxWidth().clickable(onClick = onRequestPermission).padding(vertical = 10.dp),
                )
            } else if (events.isEmpty()) {
                LauncherText(
                    text = "No events today.",
                    fontSizeSp = 14,
                    color = colors.foreground.copy(alpha = 0.5f),
                    applyCase = false,
                    modifier = Modifier.padding(top = 8.dp),
                )
            } else {
                events.forEachIndexed { index, event ->
                    EventRow(event)
                    if (index != events.lastIndex) Box(Modifier.padding(top = 12.dp))
                }
            }
        }
    }
}

@Composable
private fun EventRow(event: Agenda.Event) {
    val colors = LocalLauncherColors.current
    val timeFormat = remember { SimpleDateFormat("HH:mm", Locale.getDefault()) }
    val timeLabel = if (event.allDay) "ALL DAY" else "${timeFormat.format(Date(event.startMillis))} - ${timeFormat.format(Date(event.endMillis))}"
    Column {
        LauncherText(text = timeLabel, fontSizeSp = 13, color = colors.foreground.copy(alpha = 0.55f), applyCase = false)
        Box(Modifier.padding(top = 2.dp))
        LauncherText(text = event.title, fontSizeSp = 16, color = colors.foreground, applyCase = false)
    }
}
