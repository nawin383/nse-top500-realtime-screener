package com.puretext.launcher.data

/**
 * One launchable activity as reported by PackageManager. [key] is the
 * stable identity used everywhere else in the app (ordering, hiding,
 * aliases, favorites) since a bare package name isn't always unique to one
 * launcher activity.
 */
data class AppInfo(
    val packageName: String,
    val activityName: String,
    val label: String,
    val isSystemApp: Boolean,
) {
    val key: String get() = "$packageName/$activityName"
}
