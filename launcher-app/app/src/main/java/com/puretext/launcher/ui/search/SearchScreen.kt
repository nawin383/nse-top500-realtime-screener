package com.puretext.launcher.ui.search

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalSoftwareKeyboardController
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.puretext.launcher.LauncherUiState
import com.puretext.launcher.data.AppInfo
import com.puretext.launcher.data.LauncherShortcut
import com.puretext.launcher.data.SearchCommand
import com.puretext.launcher.data.SearchCommands
import com.puretext.launcher.data.runWebSearch
import com.puretext.launcher.ui.components.AppActionsDialog
import com.puretext.launcher.ui.components.AppRow
import com.puretext.launcher.ui.components.LauncherText
import com.puretext.launcher.ui.components.SectionLabel
import com.puretext.launcher.ui.components.TextInputDialog
import com.puretext.launcher.ui.theme.LocalLauncherColors
import com.puretext.launcher.util.Calculator
import kotlinx.coroutines.delay

@Composable
fun SearchScreen(
    uiState: LauncherUiState,
    autoFocusKeyboard: Boolean,
    onLaunch: (AppInfo) -> Unit,
    onLaunchFromSearch: (AppInfo, String) -> Unit,
    onLaunchShortcut: (LauncherShortcut) -> Unit,
    onBack: () -> Unit,
    onToggleFavorite: (AppInfo, Boolean) -> Unit,
    onToggleHidden: (AppInfo, Boolean) -> Unit,
    onRename: (AppInfo, String) -> Unit,
    onAppInfo: (AppInfo) -> Unit,
    onUninstall: (AppInfo) -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = LocalLauncherColors.current
    val context = LocalContext.current
    val clipboard = LocalClipboardManager.current
    val settings = uiState.settings
    var query by remember { mutableStateOf("") }
    var actionsApp by remember { mutableStateOf<AppInfo?>(null) }
    var renameApp by remember { mutableStateOf<AppInfo?>(null) }
    val focusRequester = remember { FocusRequester() }
    val keyboard = LocalSoftwareKeyboardController.current

    BackHandler(onBack = onBack)

    LaunchedEffect(Unit) {
        if (autoFocusKeyboard) {
            try {
                focusRequester.requestFocus()
                keyboard?.show()
            } catch (e: Exception) {
                // Focus can legitimately fail if the screen was already
                // navigated away from before this ran -- never crash for it.
            }
        }
    }

    val results = remember(uiState, query, settings.searchIncludeHidden, settings.searchByPackageName, settings.searchLearningEnabled) {
        uiState.search(
            query,
            includeHidden = settings.searchIncludeHidden,
            byPackageName = settings.searchByPackageName,
            learningEnabled = settings.searchLearningEnabled,
        )
    }
    val showRecents = query.isBlank() && settings.recentAppsEnabled
    val recents = remember(uiState, showRecents) { if (showRecents) uiState.recentApps() else emptyList() }
    val matchingShortcuts = remember(uiState, query) {
        val q = query.trim().lowercase()
        uiState.state.shortcuts.filter { q.isEmpty() || it.name.lowercase().contains(q) }
    }
    val calcResult = remember(query) {
        if (Calculator.looksLikeExpression(query)) Calculator.evaluate(query) else null
    }
    val matchingCommands = remember(query) { SearchCommands.matching(query) }
    val webSearchQuery = remember(query) {
        val trimmed = query.trim()
        if (trimmed.startsWith("search ", ignoreCase = true)) {
            trimmed.removePrefix("search ").trim().takeIf { it.isNotEmpty() }
        } else {
            null
        }
    }

    val predicted = remember(uiState, query, results, settings.autoLaunchLevel) {
        uiState.predictedApp(query, results, settings.autoLaunchLevel)
    }
    LaunchedEffect(predicted, query) {
        val target = predicted ?: return@LaunchedEffect
        delay(settings.autoLaunchDelayMs.toLong())
        onLaunchFromSearch(target, query)
    }

    Column(
        modifier = modifier
            .fillMaxSize()
            .background(colors.background)
            .padding(horizontal = 24.dp, vertical = 20.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Box(Modifier.weight(1f)) {
                if (query.isEmpty()) {
                    LauncherText(
                        text = "Search apps",
                        fontSizeSp = 20,
                        color = colors.foreground.copy(alpha = 0.4f),
                        applyCase = false,
                    )
                }
                BasicTextField(
                    value = query,
                    onValueChange = { query = it },
                    textStyle = TextStyle(color = colors.foreground, fontSize = 20.sp),
                    cursorBrush = SolidColor(colors.foreground),
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth().focusRequester(focusRequester),
                    keyboardOptions = KeyboardOptions(imeAction = ImeAction.Go),
                    keyboardActions = KeyboardActions(onGo = { results.firstOrNull()?.let { onLaunchFromSearch(it, query) } }),
                )
            }
            LauncherText(
                text = "Cancel",
                fontSizeSp = 14,
                color = colors.foreground,
                applyCase = false,
                modifier = Modifier.clickable(onClick = onBack).padding(start = 12.dp),
            )
        }

        if (predicted != null) {
            LauncherText(
                text = "→ ${uiState.displayName(predicted)}",
                fontSizeSp = 14,
                color = colors.foreground.copy(alpha = 0.6f),
                applyCase = false,
                modifier = Modifier.padding(top = 6.dp),
            )
        }

        Box(Modifier.padding(top = 20.dp))

        LazyColumn(modifier = Modifier.weight(1f)) {
            if (calcResult != null) {
                item(key = "calc-label") { SectionLabel("Calculator") }
                item(key = "calc-result") {
                    val formatted = Calculator.formatResult(calcResult)
                    LauncherText(
                        text = "= $formatted",
                        fontSizeSp = settings.appTextSizeSp,
                        color = colors.foreground,
                        applyCase = false,
                        modifier = Modifier.fillMaxWidth()
                            .clickable { clipboard.setText(AnnotatedString(formatted)) }
                            .padding(vertical = 8.dp),
                    )
                }
            }

            if (webSearchQuery != null) {
                item(key = "websearch-label") { SectionLabel("Web") }
                item(key = "websearch") {
                    AppRow(
                        name = "Search: \"$webSearchQuery\"",
                        onClick = { runWebSearch(context, webSearchQuery) },
                        fontSizeSp = settings.appTextSizeSp,
                    )
                }
            }

            if (matchingCommands.isNotEmpty()) {
                item(key = "commands-label") { SectionLabel("Commands") }
                items(matchingCommands, key = { "cmd-${it.keyword}" }) { command: SearchCommand ->
                    AppRow(
                        name = command.label,
                        onClick = { command.run(context) },
                        fontSizeSp = settings.appTextSizeSp,
                    )
                }
            }

            if (matchingShortcuts.isNotEmpty()) {
                item(key = "shortcuts-label") { SectionLabel("Shortcuts") }
                items(matchingShortcuts, key = { "shortcut-${it.id}" }) { shortcut ->
                    AppRow(
                        name = shortcut.name,
                        onClick = { onLaunchShortcut(shortcut) },
                        fontSizeSp = settings.appTextSizeSp,
                    )
                }
            }
            if (showRecents && recents.isNotEmpty()) {
                item(key = "recent-label") { SectionLabel("Recent") }
                items(recents, key = { "recent-${it.key}" }) { app ->
                    AppRow(
                        name = uiState.displayName(app),
                        onClick = { onLaunch(app) },
                        onLongClick = { actionsApp = app },
                        fontSizeSp = settings.appTextSizeSp,
                    )
                }
                item(key = "all-label") { SectionLabel("All Apps") }
            }
            items(results, key = { it.key }) { app ->
                AppRow(
                    name = uiState.displayName(app),
                    onClick = { onLaunchFromSearch(app, query) },
                    onLongClick = { actionsApp = app },
                    fontSizeSp = settings.appTextSizeSp,
                    dimmed = uiState.isHidden(app),
                )
            }
            if (results.isEmpty() && !showRecents && calcResult == null && matchingCommands.isEmpty() && matchingShortcuts.isEmpty() && webSearchQuery == null) {
                item(key = "empty") {
                    LauncherText(
                        text = "No apps found",
                        fontSizeSp = 16,
                        color = colors.foreground.copy(alpha = 0.5f),
                        modifier = Modifier.padding(top = 12.dp),
                    )
                }
            }
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
}
