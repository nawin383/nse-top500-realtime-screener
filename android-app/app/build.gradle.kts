import java.util.Properties

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

// Release signing is intentionally sourced from outside the repo -- never a
// committed keystore. Either a local (untracked) `keystore.properties` file
// next to this build file, or env vars (what CI would set as encrypted
// secrets), can supply it. When neither is present, `assembleRelease` still
// produces a debug-signed, installable APK (same as today) instead of
// failing the build -- real Play Store signing is a drop-in the moment real
// credentials show up, nothing else about the build changes.
val keystorePropsFile = rootProject.file("keystore.properties")
val keystoreProps = Properties().apply {
    if (keystorePropsFile.exists()) keystorePropsFile.inputStream().use { load(it) }
}
fun signingProp(key: String, envVar: String): String? =
    keystoreProps.getProperty(key) ?: System.getenv(envVar)

val releaseStoreFile = signingProp("storeFile", "ANDROID_RELEASE_KEYSTORE")
val releaseStorePassword = signingProp("storePassword", "ANDROID_RELEASE_KEYSTORE_PASSWORD")
val releaseKeyAlias = signingProp("keyAlias", "ANDROID_RELEASE_KEY_ALIAS")
val releaseKeyPassword = signingProp("keyPassword", "ANDROID_RELEASE_KEY_PASSWORD")
val hasReleaseSigning = releaseStoreFile != null && file(releaseStoreFile).exists() &&
    releaseStorePassword != null && releaseKeyAlias != null && releaseKeyPassword != null

android {
    namespace = "com.nse500.screener"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.nse500.screener"
        minSdk = 24
        targetSdk = 35
        versionCode = 6
        versionName = "3.0.0"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    buildFeatures {
        buildConfig = true
    }

    signingConfigs {
        if (hasReleaseSigning) {
            create("release") {
                storeFile = file(releaseStoreFile!!)
                storePassword = releaseStorePassword
                keyAlias = releaseKeyAlias
                keyPassword = releaseKeyPassword
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
            signingConfig = if (hasReleaseSigning) signingConfigs.getByName("release") else signingConfigs.getByName("debug")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.core:core-splashscreen:1.0.1")
    implementation("androidx.activity:activity-ktx:1.9.0")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("androidx.swiperefreshlayout:swiperefreshlayout:1.1.0")
    implementation("androidx.drawerlayout:drawerlayout:1.2.0")
    implementation("com.google.android.material:material:1.12.0")

    // Background alert polling that survives the app being backgrounded or
    // killed (see AlertsWorker) -- WorkManager is the standard Jetpack
    // mechanism for deferrable, guaranteed background work on modern Android.
    implementation("androidx.work:work-runtime-ktx:2.9.0")
    // Optional biometric app lock (drawer toggle).
    implementation("androidx.biometric:biometric:1.1.0")
    // Lets the app lock prompt fire on real app-to-foreground transitions
    // (ProcessLifecycleOwner) instead of every Activity-level onResume,
    // which would also fire when just returning from the in-app browser.
    implementation("androidx.lifecycle:lifecycle-process:2.8.4")

    testImplementation("junit:junit:4.13.2")
    androidTestImplementation("androidx.test:core:1.6.1")
    androidTestImplementation("androidx.test.ext:junit:1.2.1")
    androidTestImplementation("androidx.test.espresso:espresso-core:3.6.1")
}
