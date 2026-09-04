package com.puretext.launcher.ui.settings

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
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.puretext.launcher.LauncherUiState
import com.puretext.launcher.data.BUILT_IN_PRESETS
import com.puretext.launcher.data.StylePreset
import com.puretext.launcher.ui.components.ConfirmDialog
import com.puretext.launcher.ui.components.LauncherText
import com.puretext.launcher.ui.components.SectionLabel
import com.puretext.launcher.ui.components.SettingsScaffold
import com.puretext.launcher.ui.components.TextInputDialog
import com.puretext.launcher.ui.theme.LocalLauncherColors

@Composable
fun PresetsSettingsScreen(
    uiState: LauncherUiState,
    onApply: (StylePreset) -> Unit,
    onSave: (String) -> Unit,
    onDuplicate: (StylePreset, String) -> Unit,
    onRename: (String, String) -> Unit,
    onDelete: (String) -> Unit,
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = LocalLauncherColors.current
    var saveDialog by remember { mutableStateOf(false) }
    var duplicateTarget by remember { mutableStateOf<StylePreset?>(null) }
    var renameTarget by remember { mutableStateOf<StylePreset?>(null) }
    var deleteTarget by remember { mutableStateOf<StylePreset?>(null) }

    SettingsScaffold(title = "Presets", onBack = onBack, modifier = modifier) { contentModifier ->
        Column(modifier = contentModifier.verticalScroll(rememberScrollState())) {
            LauncherText(
                text = "Apply a bundle of typography and layout settings at once. Always black and white -- presets never change your theme.",
                fontSizeSp = 13,
                color = colors.foreground.copy(alpha = 0.6f),
                applyCase = false,
                modifier = Modifier.padding(bottom = 4.dp),
            )

            SectionLabel("Built-in")
            BUILT_IN_PRESETS.forEach { preset ->
                PresetRow(
                    name = preset.name,
                    onApply = { onApply(preset) },
                    onDuplicate = { duplicateTarget = preset },
                )
            }

            SectionLabel("Custom (${uiState.state.presets.size})")
            if (uiState.state.presets.isEmpty()) {
                LauncherText(
                    text = "None yet.",
                    fontSizeSp = 13,
                    color = colors.foreground.copy(alpha = 0.5f),
                    applyCase = false,
                )
            }
            uiState.state.presets.forEach { preset ->
                PresetRow(
                    name = preset.name,
                    onApply = { onApply(preset) },
                    onDuplicate = { duplicateTarget = preset },
                    onRename = { renameTarget = preset },
                    onDelete = { deleteTarget = preset },
                )
            }

            LauncherText(
                text = "+ Save Current Style",
                fontSizeSp = 15,
                color = colors.foreground,
                applyCase = false,
                modifier = Modifier.fillMaxWidth().clickable { saveDialog = true }.padding(vertical = 12.dp),
            )
            Box(Modifier.padding(bottom = 32.dp))
        }
    }

    if (saveDialog) {
        TextInputDialog(
            title = "Save Current Style",
            placeholder = "e.g. My Style",
            confirmLabel = "Save",
            onConfirm = {
                onSave(it)
                saveDialog = false
            },
            onDismiss = { saveDialog = false },
        )
    }

    duplicateTarget?.let { preset ->
        TextInputDialog(
            title = "Duplicate \"${preset.name}\"",
            initialValue = "${preset.name} Copy",
            confirmLabel = "Duplicate",
            onConfirm = {
                onDuplicate(preset, it)
                duplicateTarget = null
            },
            onDismiss = { duplicateTarget = null },
        )
    }

    renameTarget?.let { preset ->
        TextInputDialog(
            title = "Rename Preset",
            initialValue = preset.name,
            onConfirm = {
                onRename(preset.id, it)
                renameTarget = null
            },
            onDismiss = { renameTarget = null },
        )
    }

    deleteTarget?.let { preset ->
        ConfirmDialog(
            title = "Delete \"${preset.name}\"?",
            confirmLabel = "Delete",
            onConfirm = {
                onDelete(preset.id)
                deleteTarget = null
            },
            onDismiss = { deleteTarget = null },
        )
    }
}

@Composable
private fun PresetRow(
    name: String,
    onApply: () -> Unit,
    onDuplicate: () -> Unit,
    onRename: (() -> Unit)? = null,
    onDelete: (() -> Unit)? = null,
) {
    val colors = LocalLauncherColors.current
    Row(
        modifier = Modifier.fillMaxWidth().padding(vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.SpaceBetween,
    ) {
        LauncherText(
            text = name,
            fontSizeSp = 16,
            color = colors.foreground,
            applyCase = false,
            modifier = Modifier.weight(1f).clickable(onClick = onApply),
        )
        Row(verticalAlignment = Alignment.CenterVertically) {
            PresetActionText("Duplicate", onDuplicate)
            if (onRename != null) PresetActionText("Rename", onRename)
            if (onDelete != null) PresetActionText("Delete", onDelete)
        }
    }
}

@Composable
private fun PresetActionText(label: String, onClick: () -> Unit) {
    val colors = LocalLauncherColors.current
    LauncherText(
        text = label,
        fontSizeSp = 12,
        color = colors.foreground.copy(alpha = 0.7f),
        applyCase = false,
        modifier = Modifier.clickable(onClick = onClick).padding(horizontal = 6.dp),
    )
}
