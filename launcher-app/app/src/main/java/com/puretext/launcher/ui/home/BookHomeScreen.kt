package com.puretext.launcher.ui.home

import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.puretext.launcher.LauncherUiState
import com.puretext.launcher.data.AppInfo
import com.puretext.launcher.data.AppSettings
import com.puretext.launcher.data.BookPage
import com.puretext.launcher.ui.components.AppRow
import com.puretext.launcher.ui.components.LauncherText
import com.puretext.launcher.ui.theme.LocalLauncherColors
import com.puretext.launcher.ui.theme.toHorizontalAlignment
import com.puretext.launcher.ui.theme.toTextAlign

/**
 * Book Mode's home screen: cover, then one page per [BookPage], then a back
 * cover, navigated with a native HorizontalPager (cheap, smooth, no 3D/page
 * -curl rendering cost). Vertical swipe/tap gestures still work via
 * [bookVerticalGestures] on the surrounding Box; left/right is reserved
 * entirely for the pager.
 */
@OptIn(ExperimentalFoundationApi::class)
@Composable
fun BookHomeScreen(
    uiState: LauncherUiState,
    onLaunch: (AppInfo) -> Unit,
    onSwipeUp: () -> Unit,
    onSwipeDown: () -> Unit,
    onDoubleTap: () -> Unit,
    onLongPress: () -> Unit,
    onOpenSettings: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val settings = uiState.settings
    val colors = LocalLauncherColors.current
    val density = LocalDensity.current
    val swipeThresholdPx = with(density) { 48.dp.toPx() }

    val pages = remember(uiState) { uiState.bookPages() }
    val totalPages = pages.size + 2
    val pagerState = rememberPagerState(pageCount = { totalPages })

    val horizontalAlignment = settings.homeAlignment.toHorizontalAlignment()
    val textAlign = settings.homeAlignment.toTextAlign()

    Box(
        modifier = modifier
            .fillMaxSize()
            .background(colors.background)
            .bookVerticalGestures(
                swipeThresholdPx = swipeThresholdPx,
                onSwipeUp = onSwipeUp,
                onSwipeDown = onSwipeDown,
                onDoubleTap = onDoubleTap,
                onLongPress = onLongPress,
            ),
    ) {
        HorizontalPager(state = pagerState, modifier = Modifier.fillMaxSize()) { index ->
            when (index) {
                0 -> CoverPageContent(
                    title = uiState.state.book.cover.title,
                    subtitle = uiState.state.book.cover.subtitle,
                    settings = settings,
                    horizontalAlignment = horizontalAlignment,
                    textAlign = textAlign,
                )
                totalPages - 1 -> BackCoverPageContent(
                    text = uiState.state.book.backCover.text,
                    settings = settings,
                    horizontalAlignment = horizontalAlignment,
                    textAlign = textAlign,
                    onOpenSettings = onOpenSettings,
                )
                else -> {
                    val page = pages[index - 1]
                    ContentPageContent(
                        page = page,
                        uiState = uiState,
                        settings = settings,
                        horizontalAlignment = horizontalAlignment,
                        textAlign = textAlign,
                        onLaunch = onLaunch,
                    )
                }
            }
        }

        val currentIndex = pagerState.currentPage
        if (uiState.state.book.pageIndicatorEnabled && pages.isNotEmpty() && currentIndex in 1..pages.size) {
            Box(
                modifier = Modifier
                    .align(Alignment.BottomCenter)
                    .padding(bottom = 20.dp),
            ) {
                LauncherText(
                    text = "PAGE $currentIndex / ${pages.size}",
                    fontSizeSp = settings.secondaryTextSizeSp,
                    color = colors.foreground.copy(alpha = 0.5f),
                    applyCase = false,
                )
            }
        }
    }
}

@Composable
private fun CoverPageContent(
    title: String,
    subtitle: String,
    settings: AppSettings,
    horizontalAlignment: Alignment.Horizontal,
    textAlign: TextAlign,
) {
    val colors = LocalLauncherColors.current
    Column(
        modifier = Modifier.fillMaxSize().padding(32.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = horizontalAlignment,
    ) {
        LauncherText(text = title, fontSizeSp = settings.clockTextSizeSp, textAlign = textAlign, color = colors.foreground)
        if (subtitle.isNotBlank()) {
            Box(Modifier.padding(top = 12.dp))
            LauncherText(text = subtitle, fontSizeSp = settings.dateTextSizeSp, textAlign = textAlign, color = colors.foreground.copy(alpha = 0.7f))
        }
    }
}

@Composable
private fun BackCoverPageContent(
    text: String,
    settings: AppSettings,
    horizontalAlignment: Alignment.Horizontal,
    textAlign: TextAlign,
    onOpenSettings: () -> Unit,
) {
    val colors = LocalLauncherColors.current
    Column(
        modifier = Modifier.fillMaxSize().padding(32.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = horizontalAlignment,
    ) {
        LauncherText(text = "LAUNCHER", fontSizeSp = settings.appTextSizeSp + 4, textAlign = textAlign, color = colors.foreground)
        Box(Modifier.padding(top = 16.dp))
        LauncherText(
            text = "Settings",
            fontSizeSp = settings.appTextSizeSp,
            textAlign = textAlign,
            color = colors.foreground,
            modifier = Modifier.clickable(onClick = onOpenSettings).padding(vertical = 4.dp),
        )
        if (text.isNotBlank()) {
            Box(Modifier.padding(top = 24.dp))
            LauncherText(text = text, fontSizeSp = settings.secondaryTextSizeSp, textAlign = textAlign, color = colors.foreground.copy(alpha = 0.5f))
        }
    }
}

@Composable
private fun ContentPageContent(
    page: BookPage,
    uiState: LauncherUiState,
    settings: AppSettings,
    horizontalAlignment: Alignment.Horizontal,
    textAlign: TextAlign,
    onLaunch: (AppInfo) -> Unit,
) {
    val colors = LocalLauncherColors.current
    val apps = remember(page, uiState) { uiState.appsInPage(page) }
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(
                top = settings.marginTopDp.dp,
                bottom = settings.marginBottomDp.dp,
                start = settings.marginHorizontalDp.dp,
                end = settings.marginHorizontalDp.dp,
            ),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = horizontalAlignment,
    ) {
        if (page.name.isNotBlank()) {
            LauncherText(
                text = page.name,
                fontSizeSp = settings.secondaryTextSizeSp,
                textAlign = textAlign,
                color = colors.foreground.copy(alpha = 0.55f),
                modifier = Modifier.padding(bottom = settings.dateAppsSpacingDp.dp),
            )
        }
        if (apps.isEmpty()) {
            LauncherText(
                text = "No apps on this page yet.",
                fontSizeSp = settings.secondaryTextSizeSp,
                textAlign = textAlign,
                color = colors.foreground.copy(alpha = 0.4f),
                applyCase = false,
            )
        }
        apps.forEachIndexed { index, app ->
            AppRow(
                name = uiState.displayName(app),
                onClick = { onLaunch(app) },
                fontSizeSp = settings.appTextSizeSp,
                textAlign = textAlign,
            )
            if (index != apps.lastIndex) {
                Box(Modifier.padding(top = settings.appSpacingDp.dp))
            }
        }
    }
}
