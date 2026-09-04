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
import com.puretext.launcher.gestures.LauncherNotificationListenerService
import com.puretext.launcher.ui.components.LauncherText
import com.puretext.launcher.ui.components.SectionLabel
import com.puretext.launcher.ui.components.SettingsScaffold
import com.puretext.launcher.ui.components.ToggleRow
import com.puretext.launcher.ui.theme.LocalLauncherColors

@Composable
fun NotificationsSettingsScreen(
    settings: AppSettings,
    onUpdate: ((AppSettings) -> AppSettings) -> Unit,
    onOpenNotifications: () -> Unit,
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = LocalLauncherColors.current
    val context = LocalContext.current
    var granted by remember { mutableStateOf(LauncherNotificationListenerService.isEnabled(context)) }

    val lifecycleOwner = LocalLifecycleOwner.current
    DisposableEffect(lifecycleOwner) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_RESUME) {
                granted = LauncherNotificationListenerService.isEnabled(context)
            }
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose { lifecycleOwner.lifecycle.removeObserver(observer) }
    }

    SettingsScaffold(title = "Notifications", onBack = onBack, modifier = modifier) { contentModifier ->
        Column(modifier = contentModifier.verticalScroll(rememberScrollState())) {
            ToggleRow(
                "Show notification count on home",
                settings.notificationCountEnabled,
                onToggle = { onUpdate { s -> s.copy(notificationCountEnabled = it) } },
            )
            LauncherText(
                text = "View Notifications",
                fontSizeSp = 15,
                color = colors.foreground,
                applyCase = false,
                modifier = Modifier.fillMaxWidth().clickable(onClick = onOpenNotifications).padding(vertical = 10.dp),
            )
            SectionLabel("Access")
            LauncherText(
                text = if (granted) "Notification access is granted." else "Notification access is not granted.",
                fontSizeSp = 14,
                color = colors.foreground.copy(alpha = 0.7f),
                applyCase = false,
                modifier = Modifier.padding(bottom = 8.dp),
            )
            LauncherText(
                text = "Open Notification Access Settings",
                fontSizeSp = 15,
                color = colors.foreground,
                applyCase = false,
                modifier = Modifier.fillMaxWidth().clickable { LauncherNotificationListenerService.openSettings(context) }.padding(vertical = 10.dp),
            )
        }
    }
}
