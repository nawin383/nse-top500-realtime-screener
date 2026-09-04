package com.puretext.launcher.ui.settings

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import com.puretext.launcher.LauncherUiState
import com.puretext.launcher.data.GestureAction
import com.puretext.launcher.data.GestureBinding
import com.puretext.launcher.data.GestureSettings
import com.puretext.launcher.data.GestureSlot
import com.puretext.launcher.data.binding
import com.puretext.launcher.data.updated
import com.puretext.launcher.ui.components.AppPickerDialog
import com.puretext.launcher.ui.components.CycleRow
import com.puretext.launcher.ui.components.LauncherText
import com.puretext.launcher.ui.components.PickerDialog
import com.puretext.launcher.ui.components.SettingsScaffold
import com.puretext.launcher.util.titleCase

private val SLOT_LABELS = mapOf(
    GestureSlot.SWIPE_UP to "Swipe up",
    GestureSlot.SWIPE_DOWN to "Swipe down",
    GestureSlot.SWIPE_LEFT to "Swipe left",
    GestureSlot.SWIPE_RIGHT to "Swipe right",
    GestureSlot.DOUBLE_TAP to "Double tap",
    GestureSlot.LONG_PRESS to "Long press",
)

@Composable
fun GesturesSettingsScreen(
    uiState: LauncherUiState,
    onSetGestures: (GestureSettings) -> Unit,
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val gestures = uiState.state.gestures
    var pickingActionFor by remember { mutableStateOf<GestureSlot?>(null) }
    var pickingAppFor by remember { mutableStateOf<GestureSlot?>(null) }

    fun describe(binding: GestureBinding): String = if (binding.action == GestureAction.OPEN_APP) {
        val app = binding.appKey?.let { key -> uiState.appByKey(key) }
        if (app != null) uiState.displayName(app) else "Choose app"
    } else {
        titleCase(binding.action.name)
    }

    SettingsScaffold(title = "Gestures", onBack = onBack, modifier = modifier) { contentModifier ->
        Column(modifier = contentModifier.verticalScroll(rememberScrollState())) {
            GestureSlot.entries.forEach { slot ->
                CycleRow(
                    label = SLOT_LABELS.getValue(slot),
                    valueLabel = describe(gestures.binding(slot)),
                    onClick = { pickingActionFor = slot },
                )
            }
        }
    }

    pickingActionFor?.let { slot ->
        PickerDialog(
            title = "Choose Action",
            options = GestureAction.entries.map { titleCase(it.name) to it },
            onSelect = { action ->
                pickingActionFor = null
                if (action == GestureAction.OPEN_APP) {
                    pickingAppFor = slot
                } else {
                    onSetGestures(gestures.updated(slot, GestureBinding(action)))
                }
            },
            onDismiss = { pickingActionFor = null },
        )
    }

    pickingAppFor?.let { slot ->
        AppPickerDialog(
            apps = uiState.visibleApps(includeHidden = true),
            displayName = { uiState.displayName(it) },
            onSelect = { app ->
                onSetGestures(gestures.updated(slot, GestureBinding(GestureAction.OPEN_APP, app.key)))
                pickingAppFor = null
            },
            onDismiss = { pickingAppFor = null },
        )
    }
}
