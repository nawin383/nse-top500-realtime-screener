package com.puretext.launcher.util

/** Cycles a settings enum forward, wrapping around -- backs every "tap to cycle" settings row. */
inline fun <reified T : Enum<T>> T.next(): T {
    val values = enumValues<T>()
    return values[(this.ordinal + 1) % values.size]
}

fun titleCase(name: String): String = name.lowercase().split('_').joinToString(" ") { word ->
    word.replaceFirstChar { if (it.isLowerCase()) it.titlecase() else it.toString() }
}
