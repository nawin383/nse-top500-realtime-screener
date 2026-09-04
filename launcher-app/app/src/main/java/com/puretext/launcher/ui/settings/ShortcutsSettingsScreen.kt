package com.puretext.launcher.ui.settings

import android.provider.Settings
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
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
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.puretext.launcher.LauncherUiState
import com.puretext.launcher.data.LauncherShortcut
import com.puretext.launcher.data.ShortcutType
import com.puretext.launcher.ui.components.AppPickerDialog
import com.puretext.launcher.ui.components.LauncherText
import com.puretext.launcher.ui.components.PickerDialog
import com.puretext.launcher.ui.components.SettingsScaffold
import com.puretext.launcher.ui.components.TextInputDialog
import com.puretext.launcher.ui.theme.LocalLauncherColors
import java.util.UUID

private val SYSTEM_SETTINGS = listOf(
    "Wi-Fi" to Settings.ACTION_WIFI_SETTINGS,
    "Bluetooth" to Settings.ACTION_BLUETOOTH_SETTINGS,
    "Display" to Settings.ACTION_DISPLAY_SETTINGS,
    "Sound" to Settings.ACTION_SOUND_SETTINGS,
    "Storage" to Settings.ACTION_INTERNAL_STORAGE_SETTINGS,
    "Apps" to Settings.ACTION_APPLICATION_SETTINGS,
    "Date & Time" to Settings.ACTION_DATE_SETTINGS,
    "Location" to Settings.ACTION_LOCATION_SOURCE_SETTINGS,
    "Accessibility" to Settings.ACTION_ACCESSIBILITY_SETTINGS,
    "Notification Access" to Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS,
    "All Settings" to Settings.ACTION_SETTINGS,
)

private sealed interface AddStep {
    data object ChooseType : AddStep
    data object ChooseApp : AddStep
    data object EnterUrl : AddStep
    data object ChooseSetting : AddStep
    data class EnterName(val type: ShortcutType, val target: String, val suggested: String) : AddStep
}

@Composable
fun ShortcutsSettingsScreen(
    uiState: LauncherUiState,
    onAdd: (LauncherShortcut) -> Unit,
    onRemove: (String) -> Unit,
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = LocalLauncherColors.current
    var step by remember { mutableStateOf<AddStep?>(null) }

    val contactPicker = rememberLauncherForActivityResult(ActivityResultContracts.PickContact()) { uri ->
        if (uri != null) {
            step = AddStep.EnterName(ShortcutType.CONTACT, uri.toString(), "Contact")
        }
    }

    SettingsScaffold(title = "Shortcuts", onBack = onBack, modifier = modifier) { contentModifier ->
        Column(modifier = contentModifier.verticalScroll(rememberScrollState())) {
            LauncherText(
                text = "Text links to apps, websites, settings, or a contact.",
                fontSizeSp = 13,
                color = colors.foreground.copy(alpha = 0.55f),
                applyCase = false,
                modifier = Modifier.padding(bottom = 8.dp),
            )
            uiState.state.shortcuts.forEach { shortcut ->
                Row(
                    modifier = Modifier.fillMaxWidth().padding(vertical = 10.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                ) {
                    Column(Modifier.weight(1f)) {
                        LauncherText(text = shortcut.name, fontSizeSp = 16, color = colors.foreground, applyCase = false)
                        LauncherText(
                            text = shortcut.type.name,
                            fontSizeSp = 12,
                            color = colors.foreground.copy(alpha = 0.5f),
                        )
                    }
                    LauncherText(
                        text = "Remove",
                        fontSizeSp = 13,
                        color = colors.foreground,
                        modifier = Modifier.clickable { onRemove(shortcut.id) }.padding(start = 8.dp),
                    )
                }
            }
            LauncherText(
                text = "+ New Shortcut",
                fontSizeSp = 15,
                color = colors.foreground,
                applyCase = false,
                modifier = Modifier.fillMaxWidth().clickable { step = AddStep.ChooseType }.padding(vertical = 12.dp),
            )
            Box(Modifier.padding(bottom = 32.dp))
        }
    }

    when (val current = step) {
        null -> Unit
        AddStep.ChooseType -> PickerDialog(
            title = "Shortcut Type",
            options = listOf("App" to ShortcutType.APP, "Website" to ShortcutType.WEBSITE, "System Setting" to ShortcutType.SYSTEM_SETTING, "Contact" to ShortcutType.CONTACT),
            onSelect = { type ->
                step = when (type) {
                    ShortcutType.APP -> AddStep.ChooseApp
                    ShortcutType.WEBSITE -> AddStep.EnterUrl
                    ShortcutType.SYSTEM_SETTING -> AddStep.ChooseSetting
                    ShortcutType.CONTACT -> {
                        contactPicker.launch(null)
                        null
                    }
                }
            },
            onDismiss = { step = null },
        )
        AddStep.ChooseApp -> AppPickerDialog(
            apps = uiState.visibleApps(includeHidden = true),
            displayName = { uiState.displayName(it) },
            onSelect = { app -> step = AddStep.EnterName(ShortcutType.APP, app.key, uiState.displayName(app)) },
            onDismiss = { step = null },
        )
        AddStep.EnterUrl -> TextInputDialog(
            title = "Website URL",
            placeholder = "example.com",
            confirmLabel = "Next",
            onConfirm = { url ->
                if (url.isNotBlank()) step = AddStep.EnterName(ShortcutType.WEBSITE, url.trim(), url.trim())
            },
            onDismiss = { step = null },
        )
        AddStep.ChooseSetting -> PickerDialog(
            title = "System Setting",
            options = SYSTEM_SETTINGS,
            onSelect = { action -> step = AddStep.EnterName(ShortcutType.SYSTEM_SETTING, action, SYSTEM_SETTINGS.first { it.second == action }.first) },
            onDismiss = { step = null },
        )
        is AddStep.EnterName -> TextInputDialog(
            title = "Name",
            initialValue = current.suggested,
            confirmLabel = "Add",
            onConfirm = { name ->
                if (name.isNotBlank()) {
                    onAdd(LauncherShortcut(id = UUID.randomUUID().toString(), name = name.trim(), type = current.type, target = current.target))
                }
                step = null
            },
            onDismiss = { step = null },
        )
    }
}
