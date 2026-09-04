package com.puretext.launcher.ui.home

import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.gestures.detectVerticalDragGestures
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.input.pointer.pointerInput
import kotlin.math.abs
import kotlin.math.max

/**
 * The home screen's whole gesture surface: 4-direction swipe, double tap,
 * long press. Two independent pointerInput detectors (tap-family and drag)
 * on the same node -- a drag cancels the tap detector's own gesture (it
 * bows out once movement passes touch slop) before this ever double-fires,
 * which is why this two-detector split is safe rather than a hand-rolled
 * single state machine that would be far easier to get subtly wrong.
 */
fun Modifier.homeGestures(
    swipeThresholdPx: Float,
    onSwipeUp: () -> Unit,
    onSwipeDown: () -> Unit,
    onSwipeLeft: () -> Unit,
    onSwipeRight: () -> Unit,
    onDoubleTap: () -> Unit,
    onLongPress: () -> Unit,
): Modifier = this
    .pointerInput(onDoubleTap, onLongPress) {
        detectTapGestures(
            onDoubleTap = { onDoubleTap() },
            onLongPress = { onLongPress() },
        )
    }
    .pointerInput(swipeThresholdPx, onSwipeUp, onSwipeDown, onSwipeLeft, onSwipeRight) {
        var totalDrag = Offset.Zero
        detectDragGestures(
            onDragStart = { totalDrag = Offset.Zero },
            onDragEnd = {
                val dx = totalDrag.x
                val dy = totalDrag.y
                if (max(abs(dx), abs(dy)) >= swipeThresholdPx) {
                    if (abs(dx) > abs(dy)) {
                        if (dx > 0) onSwipeRight() else onSwipeLeft()
                    } else {
                        if (dy > 0) onSwipeDown() else onSwipeUp()
                    }
                }
            },
            onDragCancel = { totalDrag = Offset.Zero },
        ) { change, dragAmount ->
            change.consume()
            totalDrag += dragAmount
        }
    }

/**
 * Book Mode's gesture surface: only vertical swipe + tap-family. Left/right
 * is deliberately NOT handled here -- it's reserved for HorizontalPager's
 * own page-turn drag. Both this and the pager recognize gestures by
 * direction-scoped touch slop (this one only claims once a drag is
 * vertical-dominant), so applying this to an ancestor of the pager and
 * letting horizontal-dominant drags fall through to the pager works without
 * a hand-rolled arbitration layer.
 */
fun Modifier.bookVerticalGestures(
    swipeThresholdPx: Float,
    onSwipeUp: () -> Unit,
    onSwipeDown: () -> Unit,
    onDoubleTap: () -> Unit,
    onLongPress: () -> Unit,
): Modifier = this
    .pointerInput(onDoubleTap, onLongPress) {
        detectTapGestures(
            onDoubleTap = { onDoubleTap() },
            onLongPress = { onLongPress() },
        )
    }
    .pointerInput(swipeThresholdPx, onSwipeUp, onSwipeDown) {
        var totalDrag = 0f
        detectVerticalDragGestures(
            onDragStart = { totalDrag = 0f },
            onDragEnd = {
                if (abs(totalDrag) >= swipeThresholdPx) {
                    if (totalDrag > 0) onSwipeDown() else onSwipeUp()
                }
            },
            onDragCancel = { totalDrag = 0f },
        ) { change, dragAmount ->
            change.consume()
            totalDrag += dragAmount
        }
    }
