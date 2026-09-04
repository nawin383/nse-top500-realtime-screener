package com.puretext.launcher.ui.settings

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
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
import com.puretext.launcher.data.AppInfo
import com.puretext.launcher.ui.components.AppActionsDialog
import com.puretext.launcher.ui.components.ConfirmDialog
import com.puretext.launcher.ui.components.LauncherText
import com.puretext.launcher.ui.components.SectionLabel
import com.puretext.launcher.ui.components.SettingsScaffold
import com.puretext.launcher.ui.components.TextInputDialog
import com.puretext.launcher.ui.theme.LocalLauncherColors

@Composable
fun AppsSettingsScreen(
    uiState: LauncherUiState,
    onToggleFavorite: (AppInfo, Boolean) -> Unit,
    onToggleHidden: (AppInfo, Boolean) -> Unit,
    onRename: (AppInfo, String) -> Unit,
    onMoveFavorite: (AppInfo, Int) -> Unit,
    onSetGroup: (AppInfo, String?) -> Unit,
    onAddGroup: (String) -> Unit,
    onRenameGroup: (String, String) -> Unit,
    onDeleteGroup: (String) -> Unit,
    onAppInfo: (AppInfo) -> Unit,
    onUninstall: (AppInfo) -> Unit,
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = LocalLauncherColors.current
    val favorites = uiState.favoriteApps()
    val allApps = uiState.allApps.sortedBy { uiState.displayName(it).lowercase() }

    var actionsApp by remember { mutableStateOf<AppInfo?>(null) }
    var renameApp by remember { mutableStateOf<AppInfo?>(null) }
    var newGroupDialog by remember { mutableStateOf(false) }
    var renameGroup by remember { mutableStateOf<String?>(null) }
    var deleteGroup by remember { mutableStateOf<String?>(null) }

    SettingsScaffold(title = "Apps", onBack = onBack, modifier = modifier) { contentModifier ->
        Column(modifier = contentModifier.verticalScroll(rememberScrollState())) {
            SectionLabel("Favorites (on home)")
            if (favorites.isEmpty()) {
                LauncherText(
                    text = "None yet. Tap an app below and choose Add to Favorites.",
                    fontSizeSp = 13,
                    color = colors.foreground.copy(alpha = 0.55f),
                    applyCase = false,
                )
            }
            favorites.forEachIndexed { index, app ->
                FavoriteRow(
                    name = uiState.displayName(app),
                    canMoveUp = index > 0,
                    canMoveDown = index < favorites.lastIndex,
                    onMoveUp = { onMoveFavorite(app, -1) },
                    onMoveDown = { onMoveFavorite(app, 1) },
                    onRemove = { onToggleFavorite(app, false) },
                )
            }

            SectionLabel("Groups")
            uiState.state.groups.forEach { group ->
                Row(
                    modifier = Modifier.fillMaxWidth().padding(vertical = 10.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                ) {
                    LauncherText(
                        text = "${group.name} (${uiState.appsInGroup(group.name, includeHidden = true).size})",
                        fontSizeSp = 16,
                        color = colors.foreground,
                        applyCase = false,
                        modifier = Modifier.weight(1f),
                    )
                    LauncherText(
                        text = "Rename",
                        fontSizeSp = 13,
                        color = colors.foreground,
                        modifier = Modifier.clickable { renameGroup = group.name }.padding(horizontal = 8.dp),
                    )
                    LauncherText(
                        text = "Delete",
                        fontSizeSp = 13,
                        color = colors.foreground,
                        modifier = Modifier.clickable { deleteGroup = group.name }.padding(horizontal = 8.dp),
                    )
                }
            }
            LauncherText(
                text = "+ New Group",
                fontSizeSp = 15,
                color = colors.foreground,
                applyCase = false,
                modifier = Modifier.fillMaxWidth().clickable { newGroupDialog = true }.padding(vertical = 10.dp),
            )

            SectionLabel("All Apps (${allApps.size})")
            LauncherText(
                text = "Tap an app to favorite, hide, rename, or group it.",
                fontSizeSp = 13,
                color = colors.foreground.copy(alpha = 0.55f),
                applyCase = false,
                modifier = Modifier.padding(bottom = 6.dp),
            )
            allApps.forEach { app ->
                val hidden = uiState.isHidden(app)
                val label = uiState.displayName(app) + if (hidden) "  (hidden)" else ""
                LauncherText(
                    text = label,
                    fontSizeSp = 16,
                    color = if (hidden) colors.foreground.copy(alpha = 0.45f) else colors.foreground,
                    applyCase = false,
                    modifier = Modifier.fillMaxWidth().clickable { actionsApp = app }.padding(vertical = 8.dp),
                )
            }
            Box(Modifier.padding(bottom = 32.dp))
        }
    }

    actionsApp?.let { app ->
        AppActionsDialog(
            app = app,
            uiState = uiState,
            onToggleFavorite = { onToggleFavorite(app, it) },
            onToggleHidden = { onToggleHidden(app, it) },
            onRename = { renameApp = app },
            onAppInfo = { onAppInfo(app) },
            onUninstall = { onUninstall(app) },
            onSetGroup = { onSetGroup(app, it) },
            onDismiss = { actionsApp = null },
        )
    }

    renameApp?.let { app ->
        TextInputDialog(
            title = "Rename",
            initialValue = uiState.displayName(app),
            placeholder = app.label,
            onConfirm = {
                onRename(app, it)
                renameApp = null
            },
            onDismiss = { renameApp = null },
        )
    }

    if (newGroupDialog) {
        TextInputDialog(
            title = "New Group",
            placeholder = "e.g. Work",
            confirmLabel = "Create",
            onConfirm = {
                if (it.isNotBlank()) onAddGroup(it)
                newGroupDialog = false
            },
            onDismiss = { newGroupDialog = false },
        )
    }

    renameGroup?.let { name ->
        TextInputDialog(
            title = "Rename Group",
            initialValue = name,
            onConfirm = {
                if (it.isNotBlank()) onRenameGroup(name, it)
                renameGroup = null
            },
            onDismiss = { renameGroup = null },
        )
    }

    deleteGroup?.let { name ->
        ConfirmDialog(
            title = "Delete \"$name\"?",
            message = "Apps in this group are not removed, they just won't be grouped anymore.",
            confirmLabel = "Delete",
            onConfirm = {
                onDeleteGroup(name)
                deleteGroup = null
            },
            onDismiss = { deleteGroup = null },
        )
    }
}

@Composable
private fun FavoriteRow(
    name: String,
    canMoveUp: Boolean,
    canMoveDown: Boolean,
    onMoveUp: () -> Unit,
    onMoveDown: () -> Unit,
    onRemove: () -> Unit,
) {
    val colors = LocalLauncherColors.current
    Row(
        modifier = Modifier.fillMaxWidth().padding(vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.SpaceBetween,
    ) {
        LauncherText(text = name, fontSizeSp = 16, color = colors.foreground, applyCase = false, modifier = Modifier.weight(1f))
        Row(verticalAlignment = Alignment.CenterVertically) {
            SmallTextButton("▲", enabled = canMoveUp, onClick = onMoveUp)
            SmallTextButton("▼", enabled = canMoveDown, onClick = onMoveDown)
            SmallTextButton("✕", enabled = true, onClick = onRemove)
        }
    }
}

@Composable
private fun SmallTextButton(symbol: String, enabled: Boolean, onClick: () -> Unit) {
    val colors = LocalLauncherColors.current
    Box(
        modifier = Modifier
            .size(32.dp)
            .clickable(enabled = enabled, onClick = onClick),
        contentAlignment = Alignment.Center,
    ) {
        LauncherText(text = symbol, fontSizeSp = 15, color = colors.foreground.copy(alpha = if (enabled) 1f else 0.25f), applyCase = false)
    }
}
