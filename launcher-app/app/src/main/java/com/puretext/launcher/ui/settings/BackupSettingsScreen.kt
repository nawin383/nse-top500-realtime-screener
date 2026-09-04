package com.puretext.launcher.ui.settings

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.puretext.launcher.ui.components.LauncherText
import com.puretext.launcher.ui.components.SettingsScaffold
import com.puretext.launcher.ui.theme.LocalLauncherColors
import kotlinx.coroutines.launch

/**
 * Export/import goes through Storage Access Framework document pickers --
 * no storage permission needed, and the resulting file lives wherever the
 * user chose to put it, not in this app's own storage.
 */
@Composable
fun BackupSettingsScreen(
    exportJson: suspend () -> String,
    importJson: suspend (String) -> Boolean,
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = LocalLauncherColors.current
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var message by remember { mutableStateOf<String?>(null) }

    val exportLauncher = rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument("application/json")) { uri ->
        if (uri == null) return@rememberLauncherForActivityResult
        scope.launch {
            message = try {
                val json = exportJson()
                context.contentResolver.openOutputStream(uri)?.use { it.write(json.toByteArray(Charsets.UTF_8)) }
                "Backup saved."
            } catch (e: Exception) {
                "Could not save backup."
            }
        }
    }

    val importLauncher = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri == null) return@rememberLauncherForActivityResult
        scope.launch {
            message = try {
                val text = context.contentResolver.openInputStream(uri)?.use { it.readBytes().toString(Charsets.UTF_8) }
                if (text != null) {
                    if (importJson(text)) "Backup restored." else "That file isn't a valid backup."
                } else {
                    "Could not read that file."
                }
            } catch (e: Exception) {
                "Could not read that file."
            }
        }
    }

    SettingsScaffold(title = "Backup", onBack = onBack, modifier = modifier) { contentModifier ->
        Column(modifier = contentModifier.verticalScroll(rememberScrollState())) {
            LauncherText(
                text = "Export or import everything: theme, typography, layout, app order, hidden apps, groups, aliases, gestures, and shortcuts.",
                fontSizeSp = 13,
                color = colors.foreground.copy(alpha = 0.6f),
                applyCase = false,
                modifier = Modifier.padding(bottom = 20.dp),
            )
            LauncherText(
                text = "Export Settings",
                fontSizeSp = 16,
                color = colors.foreground,
                applyCase = false,
                modifier = Modifier.fillMaxWidth().clickable { exportLauncher.launch("pure-launcher-backup.json") }.padding(vertical = 10.dp),
            )
            LauncherText(
                text = "Import Settings",
                fontSizeSp = 16,
                color = colors.foreground,
                applyCase = false,
                modifier = Modifier.fillMaxWidth()
                    .clickable { importLauncher.launch(arrayOf("application/json", "text/plain", "*/*")) }
                    .padding(vertical = 10.dp),
            )
            message?.let {
                Box(Modifier.padding(top = 20.dp))
                LauncherText(text = it, fontSizeSp = 14, color = colors.foreground.copy(alpha = 0.75f), applyCase = false)
            }
        }
    }
}
