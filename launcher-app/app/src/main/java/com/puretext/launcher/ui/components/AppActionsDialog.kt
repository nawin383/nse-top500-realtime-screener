package com.puretext.launcher.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import com.puretext.launcher.LauncherUiState
import com.puretext.launcher.data.AppInfo
import com.puretext.launcher.ui.theme.LocalLauncherColors

/** Long-press quick actions for one app -- used from Search and Settings > Apps. */
@Composable
fun AppActionsDialog(
    app: AppInfo,
    uiState: LauncherUiState,
    onToggleFavorite: (Boolean) -> Unit,
    onToggleHidden: (Boolean) -> Unit,
    onRename: () -> Unit,
    onAppInfo: () -> Unit,
    onUninstall: () -> Unit,
    onDismiss: () -> Unit,
    onSetGroup: ((String?) -> Unit)? = null,
) {
    val colors = LocalLauncherColors.current
    val isFavorite = uiState.isFavorite(app)
    val isHidden = uiState.isHidden(app)
    Dialog(onDismissRequest = onDismiss) {
        Column(Modifier.background(colors.background).padding(20.dp)) {
            LauncherText(
                text = uiState.displayName(app),
                fontSizeSp = 18,
                color = colors.foreground,
                applyCase = false,
                modifier = Modifier.padding(bottom = 12.dp),
            )
            ActionRow(if (isFavorite) "Remove from Favorites" else "Add to Favorites") {
                onToggleFavorite(!isFavorite)
                onDismiss()
            }
            ActionRow("Rename") {
                onRename()
                onDismiss()
            }
            ActionRow(if (isHidden) "Unhide" else "Hide") {
                onToggleHidden(!isHidden)
                onDismiss()
            }
            if (onSetGroup != null) {
                val groups = uiState.state.groups.map { it.name }
                val current = uiState.groupOf(app)
                ActionRow("Group: ${current ?: "None"}") {
                    val options = listOf<String?>(null) + groups
                    val nextIndex = (options.indexOf(current) + 1).mod(options.size)
                    onSetGroup(options[nextIndex])
                }
            }
            ActionRow("App Info") {
                onAppInfo()
                onDismiss()
            }
            ActionRow("Uninstall") {
                onUninstall()
                onDismiss()
            }
            ActionRow("Cancel", onClick = onDismiss)
        }
    }
}

@Composable
private fun ActionRow(label: String, onClick: () -> Unit) {
    val colors = LocalLauncherColors.current
    LauncherText(
        text = label,
        fontSizeSp = 15,
        color = colors.foreground,
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .padding(vertical = 10.dp),
    )
}
