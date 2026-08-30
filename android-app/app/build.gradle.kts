plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.nse500.screener"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.nse500.screener"
        minSdk = 24
        targetSdk = 34
        versionCode = 6
        versionName = "2.3.0"
    }

    buildFeatures {
        buildConfig = true
    }

    buildTypes {
        // Shipped via assembleDebug (see .github/workflows/android-apk.yml) --
        // there is no separate production signing keystore for this app yet,
        // so R8 minification + resource shrinking is enabled here, on the
        // debug build type, rather than gated behind an unused release build.
        // Still debug-signed: a real production keystore is a credential a
        // human has to generate/own, not something to invent unilaterally.
        debug {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
        }
        release {
            isMinifyEnabled = false
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
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
}
