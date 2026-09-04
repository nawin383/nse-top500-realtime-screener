package com.puretext.launcher.ui.home

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.os.BatteryManager
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import com.puretext.launcher.LauncherUiState
import com.puretext.launcher.data.AppInfo
import com.puretext.launcher.data.DatePreset
import com.puretext.launcher.data.HomeAlignment
import com.puretext.launcher.data.VerticalPosition
import com.puretext.launcher.ui.components.AppRow
import com.puretext.launcher.ui.components.LauncherText
import com.puretext.launcher.ui.theme.LocalLauncherColors
import java.time.LocalDateTime
import java.time.format.DateTimeFormatter
import java.util.Locale
import kotlinx.coroutines.delay

@Composable
fun HomeScreen(
    uiState: LauncherUiState,
    onLaunch: (AppInfo) -> Unit,
    onSwipeUp: () -> Unit,
    onSwipeDown: () -> Unit,
    onSwipeLeft: () -> Unit,
    onSwipeRight: () -> Unit,
    onDoubleTap: () -> Unit,
    onLongPress: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val settings = uiState.settings
    val colors = LocalLauncherColors.current
    val density = LocalDensity.current
    val swipeThresholdPx = with(density) { 48.dp.toPx() }

    val verticalArrangement = when (settings.verticalPosition) {
        VerticalPosition.TOP -> Arrangement.Top
        VerticalPosition.CENTER -> Arrangement.Center
        VerticalPosition.BOTTOM -> Arrangement.Bottom
    }
    val horizontalAlignment = when (settings.homeAlignment) {
        HomeAlignment.START -> Alignment.Start
        HomeAlignment.CENTER -> Alignment.CenterHorizontally
        HomeAlignment.END -> Alignment.End
    }
    val textAlign = when (settings.homeAlignment) {
        HomeAlignment.START -> TextAlign.Start
        HomeAlignment.CENTER -> TextAlign.Center
        HomeAlignment.END -> TextAlign.End
    }

    val favorites = remember(uiState) { uiState.favoriteApps() }

    Box(
        modifier = modifier
            .fillMaxSize()
            .background(colors.background)
            .homeGestures(
                swipeThresholdPx = swipeThresholdPx,
                onSwipeUp = onSwipeUp,
                onSwipeDown = onSwipeDown,
                onSwipeLeft = onSwipeLeft,
                onSwipeRight = onSwipeRight,
                onDoubleTap = onDoubleTap,
                onLongPress = onLongPress,
            ),
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(
                    top = settings.marginTopDp.dp,
                    bottom = settings.marginBottomDp.dp,
                    start = settings.marginHorizontalDp.dp,
                    end = settings.marginHorizontalDp.dp,
                ),
            verticalArrangement = verticalArrangement,
            horizontalAlignment = horizontalAlignment,
        ) {
            if (settings.clockEnabled || settings.dateEnabled || settings.batteryEnabled) {
                ClockDateBlock(settings = settings, textAlign = textAlign, horizontalAlignment = horizontalAlignment)
                Box(Modifier.padding(top = settings.dateAppsSpacingDp.dp))
            }

            favorites.forEachIndexed { index, app ->
                AppRow(
                    name = uiState.displayName(app),
                    onClick = { onLaunch(app) },
                    fontSizeSp = settings.appTextSizeSp,
                    textAlign = textAlign,
                )
                if (index != favorites.lastIndex) {
                    Box(Modifier.padding(top = settings.appSpacingDp.dp))
                }
            }

            if (favorites.isEmpty()) {
                LauncherText(
                    text = "No favorite apps yet.\nOpen Search and mark some as favorites.",
                    fontSizeSp = settings.secondaryTextSizeSp,
                    textAlign = textAlign,
                    color = colors.foreground.copy(alpha = 0.55f),
                    applyCase = false,
                )
            }
        }
    }
}

@Composable
private fun ClockDateBlock(
    settings: com.puretext.launcher.data.AppSettings,
    textAlign: TextAlign,
    horizontalAlignment: Alignment.Horizontal,
) {
    var now by remember { mutableStateOf(LocalDateTime.now()) }
    LaunchedEffect(Unit) {
        while (true) {
            now = LocalDateTime.now()
            delay(1000)
        }
    }
    val colors = LocalLauncherColors.current

    Column(horizontalAlignment = horizontalAlignment) {
        if (settings.clockEnabled) {
            val hourPart = if (settings.clock24Hour) "HH" else "h"
            val secondsPart = if (settings.clockShowSeconds) ":ss" else ""
            val amPmPart = if (settings.clock24Hour) "" else " a"
            val pattern = "$hourPart:mm$secondsPart$amPmPart"
            val timeText = safeFormat(now, pattern)
            LauncherText(
                text = timeText,
                fontSizeSp = settings.clockTextSizeSp,
                textAlign = textAlign,
                color = colors.foreground,
                applyCase = false,
            )
        }
        if (settings.dateEnabled) {
            if (settings.clockEnabled) Box(Modifier.padding(top = settings.clockDateSpacingDp.dp))
            val pattern = when (settings.datePreset) {
                DatePreset.LONG -> "EEEE\ndd MMMM"
                DatePreset.SHORT -> "EEE, dd MMM"
                DatePreset.NUMERIC -> "dd/MM/yyyy"
                DatePreset.ISO -> "yyyy-MM-dd"
            }
            val dateText = safeFormat(now, pattern)
            LauncherText(
                text = dateText,
                fontSizeSp = settings.dateTextSizeSp,
                textAlign = textAlign,
                color = colors.foreground,
            )
        }
        if (settings.batteryEnabled) {
            val percent = rememberBatteryPercent()
            if (percent != null) {
                Box(Modifier.padding(top = 4.dp))
                LauncherText(
                    text = "$percent%",
                    fontSizeSp = settings.secondaryTextSizeSp,
                    textAlign = textAlign,
                    color = colors.foreground.copy(alpha = 0.75f),
                    applyCase = false,
                )
            }
        }
    }
}

private fun safeFormat(now: LocalDateTime, pattern: String): String = try {
    now.format(DateTimeFormatter.ofPattern(pattern, Locale.getDefault()))
} catch (e: Exception) {
    now.toString()
}

@Composable
private fun rememberBatteryPercent(): Int? {
    val context = LocalContext.current
    var percent by remember { mutableStateOf(readBatteryPercent(context)) }
    DisposableEffect(Unit) {
        val receiver = object : BroadcastReceiver() {
            override fun onReceive(c: Context, intent: Intent) {
                percent = readBatteryPercent(context)
            }
        }
        try {
            ContextCompat.registerReceiver(
                context,
                receiver,
                IntentFilter(Intent.ACTION_BATTERY_CHANGED),
                ContextCompat.RECEIVER_NOT_EXPORTED,
            )
        } catch (e: Exception) {
            // Nothing to do -- battery display just stays at its last known value.
        }
        onDispose {
            try {
                context.unregisterReceiver(receiver)
            } catch (e: Exception) {
                // Already unregistered or never registered -- safe to ignore.
            }
        }
    }
    return percent
}

private fun readBatteryPercent(context: Context): Int? = try {
    val bm = context.getSystemService(Context.BATTERY_SERVICE) as? BatteryManager
    val value = bm?.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY)
    value?.takeIf { it in 0..100 }
} catch (e: Exception) {
    null
}
