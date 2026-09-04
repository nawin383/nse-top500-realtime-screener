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
import com.puretext.launcher.data.AutomationRule
import com.puretext.launcher.data.RuleAction
import com.puretext.launcher.data.RuleTrigger
import com.puretext.launcher.ui.components.ConfirmDialog
import com.puretext.launcher.ui.components.CycleRow
import com.puretext.launcher.ui.components.LauncherText
import com.puretext.launcher.ui.components.SectionLabel
import com.puretext.launcher.ui.components.SettingsScaffold
import com.puretext.launcher.ui.components.StepperRow
import com.puretext.launcher.ui.components.TextInputDialog
import com.puretext.launcher.ui.theme.LocalLauncherColors
import com.puretext.launcher.util.next
import com.puretext.launcher.util.titleCase

/**
 * Simple "when X, do Y" rules: at a time of day, or when a Focus session
 * starts, either switch to a profile or (Book Mode) jump to a page. Checked
 * opportunistically -- see MainViewModel -- never via AlarmManager.
 */
@Composable
fun AutomationSettingsScreen(
    uiState: LauncherUiState,
    onAdd: (AutomationRule) -> Unit,
    onUpdate: (AutomationRule) -> Unit,
    onDelete: (String) -> Unit,
    onSetEnabled: (String, Boolean) -> Unit,
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = LocalLauncherColors.current
    var editingRuleId by remember { mutableStateOf<String?>(null) }
    var creatingNew by remember { mutableStateOf(false) }
    var deleteTarget by remember { mutableStateOf<AutomationRule?>(null) }

    val editingRule = uiState.automationRules.find { it.id == editingRuleId }
    if (editingRule != null || creatingNew) {
        RuleEditorScreen(
            rule = editingRule,
            uiState = uiState,
            onSave = { rule ->
                if (editingRule != null) onUpdate(rule) else onAdd(rule)
                editingRuleId = null
                creatingNew = false
            },
            onBack = {
                editingRuleId = null
                creatingNew = false
            },
            modifier = modifier,
        )
        return
    }

    SettingsScaffold(title = "Automation", onBack = onBack, modifier = modifier) { contentModifier ->
        Column(modifier = contentModifier.verticalScroll(rememberScrollState())) {
            LauncherText(
                text = "Simple rules: at a time, or when Focus starts, switch profile or open a page.",
                fontSizeSp = 13,
                color = colors.foreground.copy(alpha = 0.6f),
                applyCase = false,
                modifier = Modifier.padding(bottom = 4.dp),
            )

            SectionLabel("Rules (${uiState.automationRules.size})")
            uiState.automationRules.forEach { rule ->
                RuleRow(
                    rule = rule,
                    uiState = uiState,
                    onToggle = { onSetEnabled(rule.id, it) },
                    onEdit = { editingRuleId = rule.id },
                    onDelete = { deleteTarget = rule },
                )
            }
            LauncherText(
                text = "+ New Rule",
                fontSizeSp = 15,
                color = colors.foreground,
                applyCase = false,
                modifier = Modifier.fillMaxWidth().clickable { creatingNew = true }.padding(vertical = 12.dp),
            )
            Box(Modifier.padding(bottom = 32.dp))
        }
    }

    deleteTarget?.let { rule ->
        ConfirmDialog(
            title = "Delete \"${rule.name}\"?",
            confirmLabel = "Delete",
            onConfirm = {
                onDelete(rule.id)
                deleteTarget = null
            },
            onDismiss = { deleteTarget = null },
        )
    }
}

@Composable
private fun RuleRow(
    rule: AutomationRule,
    uiState: LauncherUiState,
    onToggle: (Boolean) -> Unit,
    onEdit: () -> Unit,
    onDelete: () -> Unit,
) {
    val colors = LocalLauncherColors.current
    Column(modifier = Modifier.fillMaxWidth().padding(vertical = 8.dp)) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween,
        ) {
            LauncherText(
                text = rule.name,
                fontSizeSp = 16,
                color = colors.foreground,
                applyCase = false,
                modifier = Modifier.weight(1f).clickable(onClick = onEdit),
            )
            Row(verticalAlignment = Alignment.CenterVertically) {
                LauncherText(
                    text = if (rule.enabled) "ON" else "OFF",
                    fontSizeSp = 13,
                    color = colors.foreground.copy(alpha = 0.7f),
                    modifier = Modifier.clickable { onToggle(!rule.enabled) }.padding(horizontal = 6.dp),
                )
                LauncherText(
                    text = "Delete",
                    fontSizeSp = 12,
                    color = colors.foreground.copy(alpha = 0.6f),
                    applyCase = false,
                    modifier = Modifier.clickable(onClick = onDelete).padding(horizontal = 6.dp),
                )
            }
        }
        LauncherText(
            text = "${triggerLabel(rule)} -> ${actionLabel(rule, uiState)}",
            fontSizeSp = 13,
            color = colors.foreground.copy(alpha = 0.55f),
            applyCase = false,
        )
    }
}

private fun triggerLabel(rule: AutomationRule): String = when (rule.trigger) {
    RuleTrigger.TIME_OF_DAY -> "At " + minuteOfDayLabel(rule.triggerMinuteOfDay)
    RuleTrigger.FOCUS_STARTED -> "When Focus starts"
}

private fun actionLabel(rule: AutomationRule, uiState: LauncherUiState): String = when (rule.action) {
    RuleAction.SWITCH_PROFILE -> {
        val name = uiState.profiles.find { it.id == rule.targetProfileId }?.name ?: "(deleted profile)"
        "switch to $name"
    }
    RuleAction.OPEN_PAGE -> {
        val name = uiState.state.book.pages.find { it.id == rule.targetPageId }?.name ?: "(deleted page)"
        "open $name"
    }
}

private fun minuteOfDayLabel(minuteOfDay: Int): String {
    val hour = (minuteOfDay / 60).coerceIn(0, 23)
    val minute = (minuteOfDay % 60).coerceIn(0, 59)
    return "%02d:%02d".format(hour, minute)
}

@Composable
private fun RuleEditorScreen(
    rule: AutomationRule?,
    uiState: LauncherUiState,
    onSave: (AutomationRule) -> Unit,
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = LocalLauncherColors.current
    var name by remember { mutableStateOf(rule?.name ?: "New Rule") }
    var renameDialog by remember { mutableStateOf(false) }
    var trigger by remember { mutableStateOf(rule?.trigger ?: RuleTrigger.TIME_OF_DAY) }
    var hour by remember { mutableStateOf((rule?.triggerMinuteOfDay ?: 480) / 60) }
    var minute by remember { mutableStateOf((rule?.triggerMinuteOfDay ?: 480) % 60) }
    var action by remember { mutableStateOf(rule?.action ?: RuleAction.SWITCH_PROFILE) }
    var targetProfileId by remember { mutableStateOf(rule?.targetProfileId ?: uiState.profiles.firstOrNull()?.id) }
    var targetPageId by remember { mutableStateOf(rule?.targetPageId ?: uiState.state.book.pages.firstOrNull()?.id) }

    val pages = uiState.state.book.pages

    SettingsScaffold(title = if (rule == null) "New Rule" else "Edit Rule", onBack = onBack, modifier = modifier) { contentModifier ->
        Column(modifier = contentModifier.verticalScroll(rememberScrollState())) {
            LauncherText(
                text = name,
                fontSizeSp = 18,
                color = colors.foreground,
                applyCase = false,
                modifier = Modifier.fillMaxWidth().clickable { renameDialog = true }.padding(vertical = 10.dp),
            )

            SectionLabel("Trigger")
            CycleRow(
                label = "When",
                valueLabel = titleCase(trigger.name),
                onClick = { trigger = trigger.next() },
            )
            if (trigger == RuleTrigger.TIME_OF_DAY) {
                StepperRow(label = "Hour", value = hour, onChange = { hour = it }, min = 0, max = 23)
                StepperRow(label = "Minute", value = minute, onChange = { minute = it }, step = 5, min = 0, max = 55)
            }

            SectionLabel("Action")
            CycleRow(
                label = "Do",
                valueLabel = titleCase(action.name),
                onClick = { action = action.next() },
            )
            when (action) {
                RuleAction.SWITCH_PROFILE -> {
                    if (uiState.profiles.isEmpty()) {
                        LauncherText(text = "No profiles.", fontSizeSp = 13, color = colors.foreground.copy(alpha = 0.5f), applyCase = false)
                    } else {
                        val current = uiState.profiles.find { it.id == targetProfileId } ?: uiState.profiles.first()
                        CycleRow(
                            label = "Profile",
                            valueLabel = current.name,
                            onClick = {
                                val idx = uiState.profiles.indexOf(current)
                                targetProfileId = uiState.profiles[(idx + 1) % uiState.profiles.size].id
                            },
                        )
                    }
                }
                RuleAction.OPEN_PAGE -> {
                    if (pages.isEmpty()) {
                        LauncherText(text = "No Book Mode pages yet.", fontSizeSp = 13, color = colors.foreground.copy(alpha = 0.5f), applyCase = false)
                    } else {
                        val current = pages.find { it.id == targetPageId } ?: pages.first()
                        CycleRow(
                            label = "Page",
                            valueLabel = current.name,
                            onClick = {
                                val idx = pages.indexOf(current)
                                targetPageId = pages[(idx + 1) % pages.size].id
                            },
                        )
                    }
                }
            }

            val canSave = when (action) {
                RuleAction.SWITCH_PROFILE -> targetProfileId != null
                RuleAction.OPEN_PAGE -> targetPageId != null
            }
            LauncherText(
                text = "Save",
                fontSizeSp = 16,
                color = colors.foreground.copy(alpha = if (canSave) 1f else 0.35f),
                applyCase = false,
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable(enabled = canSave) {
                        onSave(
                            AutomationRule(
                                id = rule?.id ?: java.util.UUID.randomUUID().toString(),
                                name = name.trim().ifEmpty { "New Rule" },
                                trigger = trigger,
                                triggerMinuteOfDay = (hour * 60 + minute).coerceIn(0, 1439),
                                action = action,
                                targetProfileId = if (action == RuleAction.SWITCH_PROFILE) targetProfileId else null,
                                targetPageId = if (action == RuleAction.OPEN_PAGE) targetPageId else null,
                                enabled = rule?.enabled ?: true,
                                lastFiredEpochDay = rule?.lastFiredEpochDay,
                            ),
                        )
                    }
                    .padding(vertical = 16.dp),
            )
            Box(Modifier.padding(bottom = 32.dp))
        }
    }

    if (renameDialog) {
        TextInputDialog(
            title = "Rule Name",
            initialValue = name,
            onConfirm = {
                if (it.isNotBlank()) name = it
                renameDialog = false
            },
            onDismiss = { renameDialog = false },
        )
    }
}
