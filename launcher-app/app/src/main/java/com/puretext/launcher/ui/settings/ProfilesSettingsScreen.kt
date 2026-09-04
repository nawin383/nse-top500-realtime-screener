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
import com.puretext.launcher.data.Profile
import com.puretext.launcher.ui.components.ConfirmDialog
import com.puretext.launcher.ui.components.LauncherText
import com.puretext.launcher.ui.components.SettingsScaffold
import com.puretext.launcher.ui.components.TextInputDialog
import com.puretext.launcher.ui.theme.LocalLauncherColors

/**
 * Each profile is a fully separate app set, pages, groups, gestures and
 * shortcuts (see [Profile]) -- switching is instant, local-only, and never
 * touches installed apps themselves. Deleting the last remaining profile is
 * refused by ConfigStore, so there's nothing to guard against here.
 */
@Composable
fun ProfilesSettingsScreen(
    uiState: LauncherUiState,
    onAdd: (String) -> Unit,
    onSwitch: (String) -> Unit,
    onRename: (String, String) -> Unit,
    onDuplicate: (String, String) -> Unit,
    onDelete: (String) -> Unit,
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = LocalLauncherColors.current
    var addDialog by remember { mutableStateOf(false) }
    var renameTarget by remember { mutableStateOf<Profile?>(null) }
    var duplicateTarget by remember { mutableStateOf<Profile?>(null) }
    var deleteTarget by remember { mutableStateOf<Profile?>(null) }

    SettingsScaffold(title = "Profiles", onBack = onBack, modifier = modifier) { contentModifier ->
        Column(modifier = contentModifier.verticalScroll(rememberScrollState())) {
            LauncherText(
                text = "Separate app sets for separate parts of your life -- Work, Personal, whatever you want. Each has its own apps, pages and gestures.",
                fontSizeSp = 13,
                color = colors.foreground.copy(alpha = 0.6f),
                applyCase = false,
                modifier = Modifier.padding(bottom = 12.dp),
            )

            uiState.profiles.forEach { profile ->
                ProfileRow(
                    profile = profile,
                    active = profile.id == uiState.activeProfileId,
                    canDelete = uiState.profiles.size > 1,
                    onSwitch = { onSwitch(profile.id) },
                    onRename = { renameTarget = profile },
                    onDuplicate = { duplicateTarget = profile },
                    onDelete = { deleteTarget = profile },
                )
            }

            LauncherText(
                text = "+ Add Profile",
                fontSizeSp = 15,
                color = colors.foreground,
                applyCase = false,
                modifier = Modifier.fillMaxWidth().clickable { addDialog = true }.padding(vertical = 12.dp),
            )
            Box(Modifier.padding(bottom = 32.dp))
        }
    }

    if (addDialog) {
        TextInputDialog(
            title = "New Profile",
            placeholder = "e.g. Work",
            confirmLabel = "Add",
            onConfirm = {
                onAdd(it)
                addDialog = false
            },
            onDismiss = { addDialog = false },
        )
    }

    renameTarget?.let { profile ->
        TextInputDialog(
            title = "Rename Profile",
            initialValue = profile.name,
            onConfirm = {
                onRename(profile.id, it)
                renameTarget = null
            },
            onDismiss = { renameTarget = null },
        )
    }

    duplicateTarget?.let { profile ->
        TextInputDialog(
            title = "Duplicate \"${profile.name}\"",
            initialValue = "${profile.name} Copy",
            confirmLabel = "Duplicate",
            onConfirm = {
                onDuplicate(profile.id, it)
                duplicateTarget = null
            },
            onDismiss = { duplicateTarget = null },
        )
    }

    deleteTarget?.let { profile ->
        ConfirmDialog(
            title = "Delete \"${profile.name}\"?",
            message = "Its apps, pages and settings are gone for good. This can't be undone.",
            confirmLabel = "Delete",
            onConfirm = {
                onDelete(profile.id)
                deleteTarget = null
            },
            onDismiss = { deleteTarget = null },
        )
    }
}

@Composable
private fun ProfileRow(
    profile: Profile,
    active: Boolean,
    canDelete: Boolean,
    onSwitch: () -> Unit,
    onRename: () -> Unit,
    onDuplicate: () -> Unit,
    onDelete: () -> Unit,
) {
    val colors = LocalLauncherColors.current
    Row(
        modifier = Modifier.fillMaxWidth().padding(vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.SpaceBetween,
    ) {
        LauncherText(
            text = if (active) "${profile.name}  •" else profile.name,
            fontSizeSp = 16,
            color = colors.foreground,
            applyCase = false,
            modifier = Modifier.weight(1f).clickable(onClick = onSwitch),
        )
        Row(verticalAlignment = Alignment.CenterVertically) {
            ProfileActionText("Duplicate", onDuplicate)
            ProfileActionText("Rename", onRename)
            if (canDelete) ProfileActionText("Delete", onDelete)
        }
    }
}

@Composable
private fun ProfileActionText(label: String, onClick: () -> Unit) {
    val colors = LocalLauncherColors.current
    LauncherText(
        text = label,
        fontSizeSp = 12,
        color = colors.foreground.copy(alpha = 0.7f),
        applyCase = false,
        modifier = Modifier.clickable(onClick = onClick).padding(horizontal = 6.dp),
    )
}
