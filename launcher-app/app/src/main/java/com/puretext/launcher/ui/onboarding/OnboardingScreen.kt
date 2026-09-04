package com.puretext.launcher.ui.onboarding

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.puretext.launcher.data.AppInfo
import com.puretext.launcher.data.ThemeStyle
import com.puretext.launcher.ui.components.LauncherText
import com.puretext.launcher.ui.theme.LocalLauncherColors

/**
 * Three short, text-only steps: pick black or white, pick a few favorites,
 * offer to set as default launcher. No carousel, no logo, matching the
 * spec's "extremely simple first launch" requirement.
 */
@Composable
fun OnboardingScreen(
    installedApps: List<AppInfo>,
    currentTheme: ThemeStyle,
    onSetTheme: (ThemeStyle) -> Unit,
    onFinish: (selectedApps: List<AppInfo>) -> Unit,
    onRequestDefaultLauncher: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = LocalLauncherColors.current
    var step by remember { mutableStateOf(0) }
    val selected = remember { mutableStateOf(setOf<String>()) }

    Column(
        modifier = modifier
            .fillMaxSize()
            .background(colors.background)
            .padding(horizontal = 28.dp, vertical = 40.dp),
    ) {
        when (step) {
            0 -> StyleStep(currentTheme = currentTheme, onSetTheme = onSetTheme, onContinue = { step = 1 })
            1 -> AppsStep(
                installedApps = installedApps,
                selectedKeys = selected.value,
                onToggle = { key ->
                    selected.value = if (key in selected.value) selected.value - key else selected.value + key
                },
                onContinue = { step = 2 },
            )
            else -> DefaultLauncherStep(
                onSetDefault = onRequestDefaultLauncher,
                onFinish = {
                    onFinish(installedApps.filter { it.key in selected.value })
                },
            )
        }
    }
}

@Composable
private fun StyleStep(currentTheme: ThemeStyle, onSetTheme: (ThemeStyle) -> Unit, onContinue: () -> Unit) {
    val colors = LocalLauncherColors.current
    Column(Modifier.fillMaxSize()) {
        LauncherText(text = "WELCOME", fontSizeSp = 22, color = colors.foreground, modifier = Modifier.padding(bottom = 24.dp))
        LauncherText(text = "Choose your style", fontSizeSp = 16, color = colors.foreground.copy(alpha = 0.7f), modifier = Modifier.padding(bottom = 20.dp))

        StyleOption("BLACK", selected = currentTheme == ThemeStyle.BLACK) { onSetTheme(ThemeStyle.BLACK) }
        StyleOption("WHITE", selected = currentTheme == ThemeStyle.WHITE) { onSetTheme(ThemeStyle.WHITE) }

        Box(Modifier.weight(1f))
        ContinueButton(onClick = onContinue)
    }
}

@Composable
private fun StyleOption(label: String, selected: Boolean, onClick: () -> Unit) {
    val colors = LocalLauncherColors.current
    LauncherText(
        text = if (selected) "> $label" else "  $label",
        fontSizeSp = 20,
        color = colors.foreground,
        applyCase = false,
        modifier = Modifier.fillMaxWidth().clickable(onClick = onClick).padding(vertical = 10.dp),
    )
}

@Composable
private fun AppsStep(
    installedApps: List<AppInfo>,
    selectedKeys: Set<String>,
    onToggle: (String) -> Unit,
    onContinue: () -> Unit,
) {
    val colors = LocalLauncherColors.current
    Column(Modifier.fillMaxSize()) {
        LauncherText(text = "CHOOSE YOUR APPS", fontSizeSp = 20, color = colors.foreground, modifier = Modifier.padding(bottom = 8.dp))
        LauncherText(
            text = "These show on your home screen. You can change this any time.",
            fontSizeSp = 13,
            color = colors.foreground.copy(alpha = 0.6f),
            applyCase = false,
            modifier = Modifier.padding(bottom = 16.dp),
        )
        LazyColumn(modifier = Modifier.weight(1f)) {
            items(installedApps, key = { it.key }) { app ->
                val isSelected = app.key in selectedKeys
                LauncherText(
                    text = if (isSelected) "[x] ${app.label}" else "[ ] ${app.label}",
                    fontSizeSp = 17,
                    color = colors.foreground,
                    applyCase = false,
                    modifier = Modifier.fillMaxWidth().clickable { onToggle(app.key) }.padding(vertical = 8.dp),
                )
            }
        }
        ContinueButton(onClick = onContinue)
    }
}

@Composable
private fun DefaultLauncherStep(onSetDefault: () -> Unit, onFinish: () -> Unit) {
    val colors = LocalLauncherColors.current
    Column(Modifier.fillMaxSize()) {
        LauncherText(text = "ONE LAST THING", fontSizeSp = 20, color = colors.foreground, modifier = Modifier.padding(bottom = 8.dp))
        LauncherText(
            text = "Set Pure Launcher as your default home screen to fully replace your current launcher.",
            fontSizeSp = 14,
            color = colors.foreground.copy(alpha = 0.7f),
            applyCase = false,
            modifier = Modifier.padding(bottom = 24.dp),
        )
        LauncherText(
            text = "Set as Default",
            fontSizeSp = 18,
            color = colors.foreground,
            applyCase = false,
            modifier = Modifier.clickable(onClick = onSetDefault).padding(vertical = 12.dp),
        )
        Box(Modifier.weight(1f))
        ContinueButton(label = "Finish", onClick = onFinish)
    }
}

@Composable
private fun ContinueButton(label: String = "Continue", onClick: () -> Unit) {
    val colors = LocalLauncherColors.current
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .padding(vertical = 16.dp),
    ) {
        LauncherText(text = label, fontSizeSp = 17, color = colors.foreground, applyCase = false)
    }
}
