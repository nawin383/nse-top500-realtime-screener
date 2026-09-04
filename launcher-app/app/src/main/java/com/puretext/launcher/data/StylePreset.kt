package com.puretext.launcher.data

import kotlinx.serialization.Serializable

/**
 * A named bundle of typography + layout fields -- deliberately excludes
 * [ThemeStyle] and sizes/margins that read as "content," since "All
 * presets must remain black and white" and presets are about feel, not
 * about re-theming the app.
 */
@Serializable
data class StylePreset(
    val id: String,
    val name: String,
    val fontFamily: FontFamilyOption,
    val fontWeight: TextWeight,
    val textCase: TextCase,
    val letterSpacingSp: Float,
    val lineSpacingMultiplier: Float,
    val homeAlignment: HomeAlignment,
    val verticalPosition: VerticalPosition,
    val marginTopDp: Int,
    val marginBottomDp: Int,
    val marginHorizontalDp: Int,
    val appSpacingDp: Int,
    val compactLayout: Boolean,
)

fun StylePreset.applyTo(settings: AppSettings): AppSettings = settings.copy(
    fontFamily = fontFamily,
    fontWeight = fontWeight,
    textCase = textCase,
    letterSpacingSp = letterSpacingSp,
    lineSpacingMultiplier = lineSpacingMultiplier,
    homeAlignment = homeAlignment,
    verticalPosition = verticalPosition,
    marginTopDp = marginTopDp,
    marginBottomDp = marginBottomDp,
    marginHorizontalDp = marginHorizontalDp,
    appSpacingDp = appSpacingDp,
    compactLayout = compactLayout,
)

fun stylePresetFromSettings(id: String, name: String, settings: AppSettings): StylePreset = StylePreset(
    id = id,
    name = name,
    fontFamily = settings.fontFamily,
    fontWeight = settings.fontWeight,
    textCase = settings.textCase,
    letterSpacingSp = settings.letterSpacingSp,
    lineSpacingMultiplier = settings.lineSpacingMultiplier,
    homeAlignment = settings.homeAlignment,
    verticalPosition = settings.verticalPosition,
    marginTopDp = settings.marginTopDp,
    marginBottomDp = settings.marginBottomDp,
    marginHorizontalDp = settings.marginHorizontalDp,
    appSpacingDp = settings.appSpacingDp,
    compactLayout = settings.compactLayout,
)

/** Built-in presets -- not persisted, always available, apply-only (duplicate one to make an editable copy). */
val BUILT_IN_PRESETS: List<StylePreset> = listOf(
    StylePreset(
        id = "builtin-minimal",
        name = "Minimal",
        fontFamily = FontFamilyOption.SANS,
        fontWeight = TextWeight.REGULAR,
        textCase = TextCase.NORMAL,
        letterSpacingSp = 0f,
        lineSpacingMultiplier = 1f,
        homeAlignment = HomeAlignment.START,
        verticalPosition = VerticalPosition.CENTER,
        marginTopDp = 24,
        marginBottomDp = 24,
        marginHorizontalDp = 28,
        appSpacingDp = 14,
        compactLayout = false,
    ),
    StylePreset(
        id = "builtin-book",
        name = "Book",
        fontFamily = FontFamilyOption.SERIF,
        fontWeight = TextWeight.REGULAR,
        textCase = TextCase.NORMAL,
        letterSpacingSp = 0.5f,
        lineSpacingMultiplier = 1.2f,
        homeAlignment = HomeAlignment.START,
        verticalPosition = VerticalPosition.CENTER,
        marginTopDp = 36,
        marginBottomDp = 36,
        marginHorizontalDp = 36,
        appSpacingDp = 20,
        compactLayout = false,
    ),
    StylePreset(
        id = "builtin-compact",
        name = "Compact",
        fontFamily = FontFamilyOption.SANS,
        fontWeight = TextWeight.REGULAR,
        textCase = TextCase.NORMAL,
        letterSpacingSp = 0f,
        lineSpacingMultiplier = 0.9f,
        homeAlignment = HomeAlignment.START,
        verticalPosition = VerticalPosition.TOP,
        marginTopDp = 16,
        marginBottomDp = 16,
        marginHorizontalDp = 16,
        appSpacingDp = 6,
        compactLayout = true,
    ),
    StylePreset(
        id = "builtin-spacious",
        name = "Spacious",
        fontFamily = FontFamilyOption.SANS,
        fontWeight = TextWeight.REGULAR,
        textCase = TextCase.NORMAL,
        letterSpacingSp = 0.5f,
        lineSpacingMultiplier = 1.3f,
        homeAlignment = HomeAlignment.CENTER,
        verticalPosition = VerticalPosition.CENTER,
        marginTopDp = 40,
        marginBottomDp = 40,
        marginHorizontalDp = 32,
        appSpacingDp = 26,
        compactLayout = false,
    ),
    StylePreset(
        id = "builtin-focus",
        name = "Focus",
        fontFamily = FontFamilyOption.SANS,
        fontWeight = TextWeight.MEDIUM,
        textCase = TextCase.NORMAL,
        letterSpacingSp = 0f,
        lineSpacingMultiplier = 1.1f,
        homeAlignment = HomeAlignment.CENTER,
        verticalPosition = VerticalPosition.CENTER,
        marginTopDp = 32,
        marginBottomDp = 32,
        marginHorizontalDp = 32,
        appSpacingDp = 22,
        compactLayout = false,
    ),
    StylePreset(
        id = "builtin-terminal",
        name = "Terminal",
        fontFamily = FontFamilyOption.MONOSPACE,
        fontWeight = TextWeight.REGULAR,
        textCase = TextCase.UPPERCASE,
        letterSpacingSp = 1f,
        lineSpacingMultiplier = 1f,
        homeAlignment = HomeAlignment.START,
        verticalPosition = VerticalPosition.TOP,
        marginTopDp = 16,
        marginBottomDp = 16,
        marginHorizontalDp = 16,
        appSpacingDp = 8,
        compactLayout = true,
    ),
)

/** Per-page typography/layout overrides -- every field null means "use the global style." */
@Serializable
data class BookPageStyle(
    val fontFamily: FontFamilyOption? = null,
    val fontWeight: TextWeight? = null,
    val textCase: TextCase? = null,
    val homeAlignment: HomeAlignment? = null,
    val verticalPosition: VerticalPosition? = null,
    val appSpacingDp: Int? = null,
) {
    val isCustom: Boolean get() = fontFamily != null || fontWeight != null || textCase != null ||
        homeAlignment != null || verticalPosition != null || appSpacingDp != null
}

fun bookPageStyleFromGlobal(settings: AppSettings): BookPageStyle = BookPageStyle(
    fontFamily = settings.fontFamily,
    fontWeight = settings.fontWeight,
    textCase = settings.textCase,
    homeAlignment = settings.homeAlignment,
    verticalPosition = settings.verticalPosition,
    appSpacingDp = settings.appSpacingDp,
)
