package com.puretext.launcher.util

import android.Manifest
import android.content.ContentUris
import android.content.Context
import android.content.pm.PackageManager
import android.provider.CalendarContract
import androidx.core.content.ContextCompat
import java.util.Calendar

/**
 * Today's calendar agenda -- opt-in, and only ever reads (never writes) the
 * system Calendar Provider. READ_CALENDAR is a dangerous permission, so this
 * is entirely inert until the user turns the feature on in Settings >
 * Productivity, which is what triggers the runtime permission request.
 */
object Agenda {

    data class Event(val title: String, val startMillis: Long, val endMillis: Long, val allDay: Boolean)

    fun hasPermission(context: Context): Boolean =
        ContextCompat.checkSelfPermission(context, Manifest.permission.READ_CALENDAR) == PackageManager.PERMISSION_GRANTED

    /** Empty (never throws) if permission isn't granted, or on any provider/OEM quirk. */
    fun todayEvents(context: Context): List<Event> {
        if (!hasPermission(context)) return emptyList()
        return try {
            val startOfDay = Calendar.getInstance().apply {
                set(Calendar.HOUR_OF_DAY, 0)
                set(Calendar.MINUTE, 0)
                set(Calendar.SECOND, 0)
                set(Calendar.MILLISECOND, 0)
            }.timeInMillis
            val endOfDay = startOfDay + 24L * 60 * 60 * 1000

            val builder = CalendarContract.Instances.CONTENT_URI.buildUpon()
            ContentUris.appendId(builder, startOfDay)
            ContentUris.appendId(builder, endOfDay)
            val projection = arrayOf(
                CalendarContract.Instances.TITLE,
                CalendarContract.Instances.BEGIN,
                CalendarContract.Instances.END,
                CalendarContract.Instances.ALL_DAY,
            )
            val events = mutableListOf<Event>()
            context.contentResolver.query(builder.build(), projection, null, null, "${CalendarContract.Instances.BEGIN} ASC")?.use { cursor ->
                while (cursor.moveToNext()) {
                    val title = cursor.getString(0)?.takeUnless { it.isBlank() } ?: "(untitled)"
                    val begin = cursor.getLong(1)
                    val end = cursor.getLong(2)
                    val allDay = cursor.getInt(3) != 0
                    events.add(Event(title, begin, end, allDay))
                }
            }
            events
        } catch (e: Exception) {
            emptyList()
        }
    }
}
