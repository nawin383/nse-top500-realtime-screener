package com.puretext.launcher.ui.components

import androidx.compose.foundation.text.BasicText
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.sp
import com.puretext.launcher.ui.theme.LocalAppSettings
import com.puretext.launcher.ui.theme.LocalLauncherColors
import com.puretext.launcher.ui.theme.applyTextCase
import com.puretext.launcher.ui.theme.toComposeFontFamily
import com.puretext.launcher.ui.theme.toComposeFontWeight

/**
 * The one text primitive every screen uses. Deliberately built on
 * [BasicText] (Compose Foundation), not a Material Text -- this module has
 * no Material dependency, so there is no default colored theme to
 * accidentally inherit from. Always applies the user's font family/weight/
 * letter-spacing/line-spacing/case; color defaults to the theme foreground
 * but can be overridden (e.g. dimmer secondary text still stays pure B/W,
 * just via alpha, never a new hue).
 */
@Composable
fun LauncherText(
    text: String,
    modifier: Modifier = Modifier,
    fontSizeSp: Int,
    textAlign: TextAlign = TextAlign.Start,
    color: Color? = null,
    italic: Boolean = false,
    applyCase: Boolean = true,
    maxLines: Int = Int.MAX_VALUE,
    overflow: TextOverflow = TextOverflow.Clip,
) {
    val settings = LocalAppSettings.current
    val colors = LocalLauncherColors.current
    val displayText = if (applyCase) applyTextCase(text, settings.textCase) else text
    val lineHeight = if (settings.lineSpacingMultiplier != 1f) {
        (fontSizeSp * settings.lineSpacingMultiplier).sp
    } else {
        androidx.compose.ui.unit.TextUnit.Unspecified
    }
    BasicText(
        text = displayText,
        modifier = modifier,
        style = TextStyle(
            color = color ?: colors.foreground,
            fontSize = fontSizeSp.sp,
            fontFamily = settings.fontFamily.toComposeFontFamily(),
            fontWeight = settings.fontWeight.toComposeFontWeight(),
            fontStyle = if (italic) FontStyle.Italic else FontStyle.Normal,
            letterSpacing = settings.letterSpacingSp.sp,
            lineHeight = lineHeight,
            textAlign = textAlign,
        ),
        maxLines = maxLines,
        overflow = overflow,
    )
}
