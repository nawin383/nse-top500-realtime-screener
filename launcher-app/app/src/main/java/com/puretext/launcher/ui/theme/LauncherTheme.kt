package com.puretext.launcher.ui.theme

import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.compositionLocalOf
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import com.puretext.launcher.data.AppSettings
import com.puretext.launcher.data.FontFamilyOption
import com.puretext.launcher.data.TextCase
import com.puretext.launcher.data.TextWeight
import com.puretext.launcher.data.ThemeStyle

/**
 * Only two colors ever exist in this app. Nothing else is allowed to define
 * a Color -- there is deliberately no Material dependency in this module,
 * so nothing can silently pull in a default colored scheme.
 */
data class LauncherColors(
    val background: Color,
    val foreground: Color,
)

val LocalLauncherColors = compositionLocalOf {
    LauncherColors(background = Color.Black, foreground = Color.White)
}

val LocalAppSettings = compositionLocalOf { AppSettings() }

fun FontFamilyOption.toComposeFontFamily(): FontFamily = when (this) {
    FontFamilyOption.SANS -> FontFamily.SansSerif
    FontFamilyOption.SERIF -> FontFamily.Serif
    FontFamilyOption.MONOSPACE -> FontFamily.Monospace
}

fun TextWeight.toComposeFontWeight(): FontWeight = when (this) {
    TextWeight.REGULAR -> FontWeight.Normal
    TextWeight.MEDIUM -> FontWeight.Medium
    TextWeight.BOLD -> FontWeight.Bold
}

fun applyTextCase(text: String, case: TextCase): String = when (case) {
    TextCase.NORMAL -> text
    TextCase.UPPERCASE -> text.uppercase()
    TextCase.LOWERCASE -> text.lowercase()
    TextCase.CAPITALIZED -> text.split(" ").joinToString(" ") { word ->
        word.replaceFirstChar { if (it.isLowerCase()) it.titlecase() else it.toString() }
    }
}

/**
 * The whole app's theme in one place: background/foreground swap based on
 * [AppSettings.theme]. Every screen reads [LocalLauncherColors] and
 * [LocalAppSettings] instead of hardcoding a color or font -- that's what
 * keeps live preview in Typography settings and instant theme swap free.
 */
@Composable
fun LauncherTheme(settings: AppSettings, content: @Composable () -> Unit) {
    val colors = if (settings.theme == ThemeStyle.BLACK) {
        LauncherColors(background = Color.Black, foreground = Color.White)
    } else {
        LauncherColors(background = Color.White, foreground = Color.Black)
    }
    CompositionLocalProvider(
        LocalLauncherColors provides colors,
        LocalAppSettings provides settings,
        content = content,
    )
}
