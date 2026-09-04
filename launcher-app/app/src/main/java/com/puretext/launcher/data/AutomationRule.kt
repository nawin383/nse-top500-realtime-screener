package com.puretext.launcher.data

import kotlinx.serialization.Serializable

enum class RuleTrigger { TIME_OF_DAY, FOCUS_STARTED }
enum class RuleAction { SWITCH_PROFILE, OPEN_PAGE }

/**
 * A simple "when X, do Y" rule -- global (not per-profile), since its whole
 * point can be switching between profiles. Checked opportunistically
 * (a periodic ViewModel tick for TIME_OF_DAY, an immediate check right when
 * a Focus session starts) rather than via AlarmManager/exact alarms, so no
 * extra background-scheduling permission is ever needed.
 */
@Serializable
data class AutomationRule(
    val id: String,
    val name: String,
    val trigger: RuleTrigger,
    /** Only meaningful for TIME_OF_DAY: minutes since local midnight (0..1439). */
    val triggerMinuteOfDay: Int = 480,
    val action: RuleAction,
    /** Only meaningful for SWITCH_PROFILE: a [Profile.id]. */
    val targetProfileId: String? = null,
    /** Only meaningful for OPEN_PAGE: a [BookPage.id] in whichever profile is active when it fires. */
    val targetPageId: String? = null,
    val enabled: Boolean = true,
    /** Epoch day (see java.time.LocalDate.toEpochDay) this rule last fired -- keeps a TIME_OF_DAY rule to once per day. */
    val lastFiredEpochDay: Long? = null,
)
