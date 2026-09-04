package com.puretext.launcher.ui.components

import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.combinedClickable
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import com.puretext.launcher.ui.theme.LocalLauncherColors

/** One tappable app name -- the only "list item" this launcher ever draws. */
@OptIn(ExperimentalFoundationApi::class)
@Composable
fun AppRow(
    name: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    onLongClick: (() -> Unit)? = null,
    fontSizeSp: Int = 20,
    textAlign: TextAlign = TextAlign.Start,
    dimmed: Boolean = false,
) {
    val colors = LocalLauncherColors.current
    val rowModifier = if (onLongClick != null) {
        modifier.fillMaxWidth().combinedClickable(onClick = onClick, onLongClick = onLongClick)
    } else {
        modifier.fillMaxWidth().clickable(onClick = onClick)
    }
    LauncherText(
        text = name,
        fontSizeSp = fontSizeSp,
        textAlign = textAlign,
        color = if (dimmed) colors.foreground.copy(alpha = 0.5f) else colors.foreground,
        maxLines = 1,
        overflow = TextOverflow.Ellipsis,
        modifier = rowModifier.padding(vertical = 6.dp),
    )
}

/** A row that opens a settings sub-screen. */
@Composable
fun NavRow(label: String, description: String? = null, onClick: () -> Unit, modifier: Modifier = Modifier) {
    val colors = LocalLauncherColors.current
    Column(
        modifier = modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .padding(vertical = 14.dp),
    ) {
        LauncherText(text = label, fontSizeSp = 18, color = colors.foreground)
        if (description != null) {
            Box(Modifier.padding(top = 2.dp)) {
                LauncherText(
                    text = description,
                    fontSizeSp = 13,
                    color = colors.foreground.copy(alpha = 0.6f),
                    applyCase = false,
                )
            }
        }
    }
}

/** A tap-to-flip boolean setting, rendered as "Label ... ON/OFF" -- no graphical switch. */
@Composable
fun ToggleRow(label: String, checked: Boolean, onToggle: (Boolean) -> Unit, modifier: Modifier = Modifier) {
    val colors = LocalLauncherColors.current
    Row(
        modifier = modifier
            .fillMaxWidth()
            .clickable { onToggle(!checked) }
            .padding(vertical = 14.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
    ) {
        LauncherText(text = label, fontSizeSp = 17, color = colors.foreground, modifier = Modifier.weight(1f))
        LauncherText(text = if (checked) "ON" else "OFF", fontSizeSp = 15, color = colors.foreground)
    }
}

/** An integer setting stepped with tap targets: "− value +". */
@Composable
fun StepperRow(
    label: String,
    value: Int,
    onChange: (Int) -> Unit,
    modifier: Modifier = Modifier,
    step: Int = 1,
    min: Int = Int.MIN_VALUE,
    max: Int = Int.MAX_VALUE,
    suffix: String = "",
) {
    val colors = LocalLauncherColors.current
    Row(
        modifier = modifier.fillMaxWidth().padding(vertical = 14.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        LauncherText(text = label, fontSizeSp = 17, color = colors.foreground, modifier = Modifier.weight(1f))
        Row(verticalAlignment = Alignment.CenterVertically) {
            StepperButton("−") { onChange((value - step).coerceIn(min, max)) }
            Box(Modifier.padding(horizontal = 10.dp)) {
                LauncherText(text = "$value$suffix", fontSizeSp = 15, color = colors.foreground, applyCase = false)
            }
            StepperButton("+") { onChange((value + step).coerceIn(min, max)) }
        }
    }
}

/** A float setting stepped with tap targets: "− value +". */
@Composable
fun FloatStepperRow(
    label: String,
    value: Float,
    onChange: (Float) -> Unit,
    modifier: Modifier = Modifier,
    step: Float = 0.1f,
    min: Float = 0f,
    max: Float = 5f,
    decimals: Int = 1,
) {
    val colors = LocalLauncherColors.current
    Row(
        modifier = modifier.fillMaxWidth().padding(vertical = 14.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        LauncherText(text = label, fontSizeSp = 17, color = colors.foreground, modifier = Modifier.weight(1f))
        Row(verticalAlignment = Alignment.CenterVertically) {
            StepperButton("−") { onChange(roundTo(value - step, decimals).coerceIn(min, max)) }
            Box(Modifier.padding(horizontal = 10.dp)) {
                LauncherText(text = "%.${decimals}f".format(value), fontSizeSp = 15, color = colors.foreground, applyCase = false)
            }
            StepperButton("+") { onChange(roundTo(value + step, decimals).coerceIn(min, max)) }
        }
    }
}

private fun roundTo(value: Float, decimals: Int): Float {
    val factor = Math.pow(10.0, decimals.toDouble()).toFloat()
    return kotlin.math.round(value * factor) / factor
}

@Composable
private fun StepperButton(symbol: String, onClick: () -> Unit) {
    val colors = LocalLauncherColors.current
    Box(
        modifier = Modifier
            .size(36.dp)
            .clickable(onClick = onClick),
        contentAlignment = Alignment.Center,
    ) {
        LauncherText(text = symbol, fontSizeSp = 20, color = colors.foreground, applyCase = false)
    }
}

/** Cycles through a fixed set of text options on tap, e.g. font family or alignment. */
@Composable
fun CycleRow(label: String, valueLabel: String, onClick: () -> Unit, modifier: Modifier = Modifier) {
    val colors = LocalLauncherColors.current
    Row(
        modifier = modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .padding(vertical = 14.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
    ) {
        LauncherText(text = label, fontSizeSp = 17, color = colors.foreground, modifier = Modifier.weight(1f))
        LauncherText(text = valueLabel, fontSizeSp = 15, color = colors.foreground, applyCase = false)
    }
}

@Composable
fun SectionLabel(text: String, modifier: Modifier = Modifier) {
    val colors = LocalLauncherColors.current
    Box(modifier.fillMaxWidth().padding(top = 22.dp, bottom = 6.dp)) {
        LauncherText(text = text, fontSizeSp = 13, color = colors.foreground.copy(alpha = 0.55f))
    }
}

@Composable
fun Divider(modifier: Modifier = Modifier) {
    val colors = LocalLauncherColors.current
    Box(
        modifier
            .fillMaxWidth()
            .padding(vertical = 2.dp)
            .height(1.dp)
            .background(colors.foreground.copy(alpha = 0.15f)),
    )
}

/**
 * A full screen with a text-only back affordance and scrollable content --
 * every settings sub-screen is built on this.
 */
@Composable
fun SettingsScaffold(
    title: String,
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
    content: @Composable (Modifier) -> Unit,
) {
    val colors = LocalLauncherColors.current
    Column(
        modifier = modifier
            .fillMaxSize()
            .background(colors.background)
            .padding(horizontal = 24.dp),
    ) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(top = 20.dp, bottom = 8.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            LauncherText(
                text = "< Back",
                fontSizeSp = 15,
                color = colors.foreground,
                applyCase = false,
                modifier = Modifier.clickable(onClick = onBack).padding(end = 16.dp, top = 4.dp, bottom = 4.dp),
            )
        }
        LauncherText(text = title, fontSizeSp = 24, color = colors.foreground, modifier = Modifier.padding(bottom = 8.dp))
        content(Modifier.weight(1f))
    }
}

/** A single-line text prompt: rename an app, name a group, name a shortcut. */
@Composable
fun TextInputDialog(
    title: String,
    initialValue: String = "",
    placeholder: String = "",
    confirmLabel: String = "Save",
    onConfirm: (String) -> Unit,
    onDismiss: () -> Unit,
) {
    val colors = LocalLauncherColors.current
    var text by remember { mutableStateOf(initialValue) }
    Dialog(onDismissRequest = onDismiss) {
        Column(modifier = Modifier.background(colors.background).padding(24.dp)) {
            LauncherText(text = title, fontSizeSp = 18, color = colors.foreground, modifier = Modifier.padding(bottom = 16.dp))
            Box {
                if (text.isEmpty() && placeholder.isNotEmpty()) {
                    LauncherText(text = placeholder, fontSizeSp = 16, color = colors.foreground.copy(alpha = 0.4f), applyCase = false)
                }
                BasicTextField(
                    value = text,
                    onValueChange = { text = it },
                    textStyle = TextStyle(color = colors.foreground, fontSize = 16.sp),
                    cursorBrush = SolidColor(colors.foreground),
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                )
            }
            Row(
                modifier = Modifier.fillMaxWidth().padding(top = 24.dp),
                horizontalArrangement = Arrangement.End,
            ) {
                LauncherText(
                    text = "Cancel",
                    fontSizeSp = 15,
                    color = colors.foreground,
                    modifier = Modifier.clickable(onClick = onDismiss).padding(12.dp),
                )
                LauncherText(
                    text = confirmLabel,
                    fontSizeSp = 15,
                    color = colors.foreground,
                    modifier = Modifier.clickable { onConfirm(text) }.padding(12.dp),
                )
            }
        }
    }
}

/** A scrollable, text-only "choose an app" dialog -- used by Gestures and Shortcuts. */
@Composable
fun AppPickerDialog(
    apps: List<com.puretext.launcher.data.AppInfo>,
    displayName: (com.puretext.launcher.data.AppInfo) -> String,
    onSelect: (com.puretext.launcher.data.AppInfo) -> Unit,
    onDismiss: () -> Unit,
) {
    val colors = LocalLauncherColors.current
    Dialog(onDismissRequest = onDismiss) {
        Column(
            Modifier
                .background(colors.background)
                .padding(20.dp)
                .heightIn(max = 480.dp),
        ) {
            LauncherText(text = "Choose App", fontSizeSp = 18, color = colors.foreground, modifier = Modifier.padding(bottom = 12.dp))
            LazyColumn {
                items(apps, key = { it.key }) { app ->
                    LauncherText(
                        text = displayName(app),
                        fontSizeSp = 15,
                        color = colors.foreground,
                        applyCase = false,
                        modifier = Modifier.fillMaxWidth().clickable { onSelect(app) }.padding(vertical = 10.dp),
                    )
                }
            }
        }
    }
}

/** A scrollable, text-only single-choice picker for any labeled list of values. */
@Composable
fun <T> PickerDialog(title: String, options: List<Pair<String, T>>, onSelect: (T) -> Unit, onDismiss: () -> Unit) {
    val colors = LocalLauncherColors.current
    Dialog(onDismissRequest = onDismiss) {
        Column(
            Modifier
                .background(colors.background)
                .padding(20.dp)
                .heightIn(max = 480.dp),
        ) {
            LauncherText(text = title, fontSizeSp = 18, color = colors.foreground, modifier = Modifier.padding(bottom = 12.dp))
            LazyColumn {
                items(options) { (label, value) ->
                    LauncherText(
                        text = label,
                        fontSizeSp = 15,
                        color = colors.foreground,
                        applyCase = false,
                        modifier = Modifier.fillMaxWidth().clickable { onSelect(value) }.padding(vertical = 10.dp),
                    )
                }
            }
        }
    }
}

/** Text-only confirm dialog for destructive actions -- never a bare Material AlertDialog. */
@Composable
fun ConfirmDialog(
    title: String,
    message: String? = null,
    confirmLabel: String = "Reset",
    cancelLabel: String = "Cancel",
    onConfirm: () -> Unit,
    onDismiss: () -> Unit,
) {
    val colors = LocalLauncherColors.current
    Dialog(onDismissRequest = onDismiss) {
        Column(
            modifier = Modifier
                .background(colors.background)
                .padding(24.dp),
        ) {
            LauncherText(text = title, fontSizeSp = 19, color = colors.foreground, modifier = Modifier.padding(bottom = 8.dp))
            if (message != null) {
                LauncherText(
                    text = message,
                    fontSizeSp = 14,
                    color = colors.foreground.copy(alpha = 0.75f),
                    applyCase = false,
                    modifier = Modifier.padding(bottom = 20.dp),
                )
            }
            Row(
                modifier = Modifier.fillMaxWidth().padding(top = 8.dp),
                horizontalArrangement = Arrangement.End,
            ) {
                LauncherText(
                    text = cancelLabel,
                    fontSizeSp = 15,
                    color = colors.foreground,
                    modifier = Modifier.clickable(onClick = onDismiss).padding(12.dp),
                )
                LauncherText(
                    text = confirmLabel,
                    fontSizeSp = 15,
                    color = colors.foreground,
                    modifier = Modifier.clickable(onClick = onConfirm).padding(12.dp),
                )
            }
        }
    }
}
