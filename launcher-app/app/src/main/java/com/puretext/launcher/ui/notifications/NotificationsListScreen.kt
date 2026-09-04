package com.puretext.launcher.ui.notifications

import android.app.Notification
import android.service.notification.StatusBarNotification
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.collectAsState
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
import com.puretext.launcher.gestures.LauncherNotificationListenerService
import com.puretext.launcher.ui.components.LauncherText
import com.puretext.launcher.ui.components.SettingsScaffold
import com.puretext.launcher.ui.theme.LocalLauncherColors

/**
 * A real, text-only, per-app notification list -- open or dismiss any of
 * them right here instead of pulling down the system shade. Reads the same
 * live [LauncherNotificationListenerService] flow the optional home-screen
 * count uses; if notification access was never granted, this is just an
 * empty list with a link to grant it (same pattern as Settings > Notifications).
 */
@Composable
fun NotificationsListScreen(onBack: () -> Unit, modifier: Modifier = Modifier) {
    val colors = LocalLauncherColors.current
    val context = LocalContext.current
    val notifications by LauncherNotificationListenerService.notifications.collectAsState()

    var granted by remember { mutableStateOf(LauncherNotificationListenerService.isEnabled(context)) }
    val lifecycleOwner = LocalLifecycleOwner.current
    DisposableEffect(lifecycleOwner) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_RESUME) granted = LauncherNotificationListenerService.isEnabled(context)
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose { lifecycleOwner.lifecycle.removeObserver(observer) }
    }

    SettingsScaffold(title = "Notifications", onBack = onBack, modifier = modifier) { contentModifier ->
        Column(modifier = contentModifier) {
            if (!granted) {
                LauncherText(
                    text = "Notification access isn't granted yet.",
                    fontSizeSp = 14,
                    color = colors.foreground.copy(alpha = 0.7f),
                    applyCase = false,
                    modifier = Modifier.padding(bottom = 8.dp),
                )
                LauncherText(
                    text = "Grant Notification Access",
                    fontSizeSp = 15,
                    color = colors.foreground,
                    applyCase = false,
                    modifier = Modifier.fillMaxWidth().clickable { LauncherNotificationListenerService.openSettings(context) }.padding(vertical = 10.dp),
                )
                return@Column
            }

            if (notifications.isEmpty()) {
                LauncherText(
                    text = "No notifications.",
                    fontSizeSp = 14,
                    color = colors.foreground.copy(alpha = 0.5f),
                    applyCase = false,
                    modifier = Modifier.padding(top = 8.dp),
                )
                return@Column
            }

            LauncherText(
                text = "Dismiss All",
                fontSizeSp = 14,
                color = colors.foreground.copy(alpha = 0.7f),
                applyCase = false,
                modifier = Modifier.fillMaxWidth().clickable { LauncherNotificationListenerService.dismissAll() }.padding(vertical = 8.dp),
            )
            LazyColumn(modifier = Modifier.fillMaxWidth()) {
                items(notifications, key = { it.key }) { sbn ->
                    NotificationRow(context = context.applicationContext, sbn = sbn)
                }
            }
        }
    }
}

@Composable
private fun NotificationRow(context: android.content.Context, sbn: StatusBarNotification) {
    val colors = LocalLauncherColors.current
    val (title, text) = remember(sbn) { extractText(sbn) }
    val appLabel = remember(sbn.packageName) { LauncherNotificationListenerService.appLabel(context, sbn.packageName) }

    Row(
        modifier = Modifier.fillMaxWidth().padding(vertical = 10.dp),
        verticalAlignment = Alignment.Top,
        horizontalArrangement = Arrangement.SpaceBetween,
    ) {
        Column(
            modifier = Modifier
                .weight(1f)
                .clickable { LauncherNotificationListenerService.open(sbn) },
        ) {
            LauncherText(text = appLabel, fontSizeSp = 13, color = colors.foreground.copy(alpha = 0.55f), applyCase = false)
            if (title.isNotBlank()) {
                Box(Modifier.padding(top = 2.dp))
                LauncherText(text = title, fontSizeSp = 16, color = colors.foreground, applyCase = false)
            }
            if (text.isNotBlank()) {
                Box(Modifier.padding(top = 2.dp))
                LauncherText(text = text, fontSizeSp = 14, color = colors.foreground.copy(alpha = 0.75f), applyCase = false)
            }
        }
        LauncherText(
            text = "Dismiss",
            fontSizeSp = 12,
            color = colors.foreground.copy(alpha = 0.6f),
            applyCase = false,
            modifier = Modifier.clickable { LauncherNotificationListenerService.dismiss(sbn.key) }.padding(start = 8.dp, top = 2.dp),
        )
    }
}

private fun extractText(sbn: StatusBarNotification): Pair<String, String> = try {
    val extras = sbn.notification.extras
    val title = extras.getCharSequence(Notification.EXTRA_TITLE)?.toString() ?: ""
    val text = extras.getCharSequence(Notification.EXTRA_TEXT)?.toString() ?: ""
    title to text
} catch (e: Exception) {
    "" to ""
}
