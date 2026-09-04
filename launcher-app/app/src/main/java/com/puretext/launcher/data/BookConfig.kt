package com.puretext.launcher.data

import kotlinx.serialization.Serializable

/** One page of the book: a named, ordered list of apps. */
@Serializable
data class BookPage(
    val id: String,
    val name: String,
    val appKeys: List<String> = emptyList(),
    val hidden: Boolean = false,
    val style: BookPageStyle = BookPageStyle(),
)

@Serializable
data class CoverConfig(
    val title: String = "MY PHONE",
    val subtitle: String = "",
)

@Serializable
data class BackCoverConfig(
    val text: String = "Version 2.0",
)

/**
 * Everything Book Mode needs beyond the Classic-mode [LauncherState] fields.
 * Lives inside [LauncherState] so it rides along with backup/export for
 * free, and so a corrupt/missing value falls back to empty (no pages yet)
 * rather than crashing -- see [ConfigStore.ensureBookSeeded] for the
 * one-time migration that turns "no pages yet" into a real first page.
 */
@Serializable
data class BookState(
    val pages: List<BookPage> = emptyList(),
    val cover: CoverConfig = CoverConfig(),
    val backCover: BackCoverConfig = BackCoverConfig(),
    val pageIndicatorEnabled: Boolean = true,
)
