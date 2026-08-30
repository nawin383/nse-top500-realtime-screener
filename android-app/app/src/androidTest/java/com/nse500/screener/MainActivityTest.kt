package com.nse500.screener

import androidx.test.core.app.ActivityScenario
import androidx.test.espresso.Espresso.onView
import androidx.test.espresso.action.ViewActions.click
import androidx.test.espresso.assertion.ViewAssertions.matches
import androidx.test.espresso.matcher.ViewMatchers.isDisplayed
import androidx.test.espresso.matcher.ViewMatchers.withId
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Test
import org.junit.runner.RunWith

/**
 * Smoke tests for the native chrome around the WebView -- bottom nav and
 * drawer, not the web content itself (that's the deployed frontend's own
 * concern). Needs a device/emulator to actually run (`connectedAndroidTest`,
 * not exercised by CI -- see android-apk.yml's compile-only check) since
 * there's no emulator available in the CI job that added these.
 */
@RunWith(AndroidJUnit4::class)
class MainActivityTest {

    @Test
    fun bottomNavSwitchesTabsWithoutCrashing() {
        ActivityScenario.launch(MainActivity::class.java).use {
            onView(withId(R.id.bottom_nav)).check(matches(isDisplayed()))
            onView(withId(R.id.nav_options)).perform(click())
            onView(withId(R.id.nav_screener)).perform(click())
        }
    }

    @Test
    fun launchesWithToolbarAndDrawerPresent() {
        ActivityScenario.launch(MainActivity::class.java).use {
            onView(withId(R.id.toolbar)).check(matches(isDisplayed()))
            onView(withId(R.id.drawer_layout)).check(matches(isDisplayed()))
        }
    }
}
