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
import com.puretext.launcher.data.AppInfo
import com.puretext.launcher.data.BackCoverConfig
import com.puretext.launcher.data.BookPage
import com.puretext.launcher.data.CoverConfig
import com.puretext.launcher.ui.components.AppPickerDialog
import com.puretext.launcher.ui.components.ConfirmDialog
import com.puretext.launcher.ui.components.CycleRow
import com.puretext.launcher.ui.components.LauncherText
import com.puretext.launcher.ui.components.SectionLabel
import com.puretext.launcher.ui.components.SettingsScaffold
import com.puretext.launcher.ui.components.TextInputDialog
import com.puretext.launcher.ui.components.ToggleRow
import com.puretext.launcher.ui.theme.LocalLauncherColors

@Composable
fun PagesSettingsScreen(
    uiState: LauncherUiState,
    onAddPage: (String) -> Unit,
    onRenamePage: (String, String) -> Unit,
    onDeletePage: (String) -> Unit,
    onSetPageHidden: (String, Boolean) -> Unit,
    onMovePage: (String, Int) -> Unit,
    onAddAppToPage: (String, AppInfo) -> Unit,
    onRemoveAppFromPage: (String, AppInfo) -> Unit,
    onMoveAppInPage: (String, AppInfo, Int) -> Unit,
    onSetCover: (CoverConfig) -> Unit,
    onSetBackCover: (BackCoverConfig) -> Unit,
    onSetPageIndicatorEnabled: (Boolean) -> Unit,
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = LocalLauncherColors.current
    val pages = uiState.state.book.pages
    var editingPageId by remember { mutableStateOf<String?>(null) }
    var newPageDialog by remember { mutableStateOf(false) }
    var deleteConfirmId by remember { mutableStateOf<String?>(null) }
    var editCoverTitle by remember { mutableStateOf(false) }
    var editCoverSubtitle by remember { mutableStateOf(false) }
    var editBackCover by remember { mutableStateOf(false) }

    val editingPage = pages.find { it.id == editingPageId }
    if (editingPage != null) {
        PageEditorScreen(
            page = editingPage,
            uiState = uiState,
            onRename = { onRenamePage(editingPage.id, it) },
            onAddApp = { onAddAppToPage(editingPage.id, it) },
            onRemoveApp = { onRemoveAppFromPage(editingPage.id, it) },
            onMoveApp = { app, delta -> onMoveAppInPage(editingPage.id, app, delta) },
            onBack = { editingPageId = null },
            modifier = modifier,
        )
        return
    }

    SettingsScaffold(title = "Pages", onBack = onBack, modifier = modifier) { contentModifier ->
        Column(modifier = contentModifier.verticalScroll(rememberScrollState())) {
            ToggleRow(
                "Show page indicator",
                uiState.state.book.pageIndicatorEnabled,
                onToggle = onSetPageIndicatorEnabled,
            )

            SectionLabel("Cover")
            CycleRow("Title", uiState.state.book.cover.title, onClick = { editCoverTitle = true })
            CycleRow("Subtitle", uiState.state.book.cover.subtitle.ifBlank { "None" }, onClick = { editCoverSubtitle = true })

            SectionLabel("Back Cover")
            CycleRow("Text", uiState.state.book.backCover.text.ifBlank { "None" }, onClick = { editBackCover = true })

            SectionLabel("Pages (${pages.size})")
            pages.forEachIndexed { index, page ->
                PageRow(
                    page = page,
                    appCount = uiState.appsInPage(page).size,
                    canMoveUp = index > 0,
                    canMoveDown = index < pages.lastIndex,
                    onMoveUp = { onMovePage(page.id, -1) },
                    onMoveDown = { onMovePage(page.id, 1) },
                    onEdit = { editingPageId = page.id },
                    onToggleHidden = { onSetPageHidden(page.id, !page.hidden) },
                    onDelete = { deleteConfirmId = page.id },
                )
            }
            LauncherText(
                text = "+ New Page",
                fontSizeSp = 15,
                color = colors.foreground,
                applyCase = false,
                modifier = Modifier.fillMaxWidth().clickable { newPageDialog = true }.padding(vertical = 12.dp),
            )
            Box(Modifier.padding(bottom = 32.dp))
        }
    }

    if (newPageDialog) {
        TextInputDialog(
            title = "New Page",
            placeholder = "e.g. Work",
            confirmLabel = "Create",
            onConfirm = {
                if (it.isNotBlank()) onAddPage(it)
                newPageDialog = false
            },
            onDismiss = { newPageDialog = false },
        )
    }

    deleteConfirmId?.let { id ->
        val name = pages.find { it.id == id }?.name ?: ""
        ConfirmDialog(
            title = "Delete \"$name\"?",
            message = "The apps on this page are not uninstalled, just removed from this page.",
            confirmLabel = "Delete",
            onConfirm = {
                onDeletePage(id)
                deleteConfirmId = null
            },
            onDismiss = { deleteConfirmId = null },
        )
    }

    if (editCoverTitle) {
        TextInputDialog(
            title = "Cover Title",
            initialValue = uiState.state.book.cover.title,
            onConfirm = {
                onSetCover(uiState.state.book.cover.copy(title = it))
                editCoverTitle = false
            },
            onDismiss = { editCoverTitle = false },
        )
    }

    if (editCoverSubtitle) {
        TextInputDialog(
            title = "Cover Subtitle",
            initialValue = uiState.state.book.cover.subtitle,
            placeholder = "Optional",
            onConfirm = {
                onSetCover(uiState.state.book.cover.copy(subtitle = it))
                editCoverSubtitle = false
            },
            onDismiss = { editCoverSubtitle = false },
        )
    }

    if (editBackCover) {
        TextInputDialog(
            title = "Back Cover Text",
            initialValue = uiState.state.book.backCover.text,
            placeholder = "Optional",
            onConfirm = {
                onSetBackCover(BackCoverConfig(text = it))
                editBackCover = false
            },
            onDismiss = { editBackCover = false },
        )
    }
}

@Composable
private fun PageRow(
    page: BookPage,
    appCount: Int,
    canMoveUp: Boolean,
    canMoveDown: Boolean,
    onMoveUp: () -> Unit,
    onMoveDown: () -> Unit,
    onEdit: () -> Unit,
    onToggleHidden: () -> Unit,
    onDelete: () -> Unit,
) {
    val colors = LocalLauncherColors.current
    Row(
        modifier = Modifier.fillMaxWidth().padding(vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.SpaceBetween,
    ) {
        Column(Modifier.weight(1f).clickable(onClick = onEdit)) {
            LauncherText(
                text = page.name + if (page.hidden) "  (hidden)" else "",
                fontSizeSp = 16,
                color = colors.foreground,
                applyCase = false,
            )
            LauncherText(text = "$appCount apps", fontSizeSp = 12, color = colors.foreground.copy(alpha = 0.5f))
        }
        Row(verticalAlignment = Alignment.CenterVertically) {
            TinyButton("▲", enabled = canMoveUp, onClick = onMoveUp)
            TinyButton("▼", enabled = canMoveDown, onClick = onMoveDown)
            TinyButton(if (page.hidden) "Show" else "Hide", onClick = onToggleHidden)
            TinyButton("✕", onClick = onDelete)
        }
    }
}

@Composable
private fun PageEditorScreen(
    page: BookPage,
    uiState: LauncherUiState,
    onRename: (String) -> Unit,
    onAddApp: (AppInfo) -> Unit,
    onRemoveApp: (AppInfo) -> Unit,
    onMoveApp: (AppInfo, Int) -> Unit,
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = LocalLauncherColors.current
    var renameDialog by remember { mutableStateOf(false) }
    var addAppDialog by remember { mutableStateOf(false) }
    val apps = uiState.appsInPage(page)

    SettingsScaffold(title = page.name, onBack = onBack, modifier = modifier) { contentModifier ->
        Column(modifier = contentModifier.verticalScroll(rememberScrollState())) {
            LauncherText(
                text = "Rename Page",
                fontSizeSp = 15,
                color = colors.foreground,
                applyCase = false,
                modifier = Modifier.fillMaxWidth().clickable { renameDialog = true }.padding(vertical = 10.dp),
            )

            SectionLabel("Apps (${apps.size})")
            if (apps.isEmpty()) {
                LauncherText(
                    text = "No apps yet.",
                    fontSizeSp = 13,
                    color = colors.foreground.copy(alpha = 0.5f),
                    applyCase = false,
                )
            }
            apps.forEachIndexed { index, app ->
                Row(
                    modifier = Modifier.fillMaxWidth().padding(vertical = 6.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween,
                ) {
                    LauncherText(
                        text = uiState.displayName(app),
                        fontSizeSp = 16,
                        color = colors.foreground,
                        applyCase = false,
                        modifier = Modifier.weight(1f),
                    )
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        TinyButton("▲", enabled = index > 0, onClick = { onMoveApp(app, -1) })
                        TinyButton("▼", enabled = index < apps.lastIndex, onClick = { onMoveApp(app, 1) })
                        TinyButton("✕", onClick = { onRemoveApp(app) })
                    }
                }
            }
            LauncherText(
                text = "+ Add App",
                fontSizeSp = 15,
                color = colors.foreground,
                applyCase = false,
                modifier = Modifier.fillMaxWidth().clickable { addAppDialog = true }.padding(vertical = 12.dp),
            )
            Box(Modifier.padding(bottom = 32.dp))
        }
    }

    if (renameDialog) {
        TextInputDialog(
            title = "Rename Page",
            initialValue = page.name,
            onConfirm = {
                if (it.isNotBlank()) onRename(it)
                renameDialog = false
            },
            onDismiss = { renameDialog = false },
        )
    }

    if (addAppDialog) {
        AppPickerDialog(
            apps = uiState.visibleApps(includeHidden = true).filter { it.key !in page.appKeys },
            displayName = { uiState.displayName(it) },
            onSelect = {
                onAddApp(it)
                addAppDialog = false
            },
            onDismiss = { addAppDialog = false },
        )
    }
}

@Composable
private fun TinyButton(label: String, enabled: Boolean = true, onClick: () -> Unit) {
    val colors = LocalLauncherColors.current
    LauncherText(
        text = label,
        fontSizeSp = 13,
        color = colors.foreground.copy(alpha = if (enabled) 1f else 0.25f),
        applyCase = false,
        modifier = Modifier.clickable(enabled = enabled, onClick = onClick).padding(horizontal = 8.dp, vertical = 6.dp),
    )
}
