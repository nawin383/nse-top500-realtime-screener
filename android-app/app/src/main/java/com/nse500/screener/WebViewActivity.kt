package com.nse500.screener

import android.annotation.SuppressLint
import android.os.Bundle
import android.view.View
import android.webkit.WebChromeClient
import android.webkit.WebView
import androidx.activity.addCallback
import androidx.appcompat.app.AppCompatActivity
import com.google.android.material.appbar.MaterialToolbar

/**
 * A minimal in-app browser for the external dashboard links (the Google
 * Apps Script deployments linked from the sidebar and the web page's own
 * Tools menu) so visiting them doesn't leave the app and hand off to
 * Chrome -- back returns straight to the main screen instead of requiring
 * an app switch. Not used for arbitrary/unknown external links (see
 * MainActivity's shouldOverrideUrlLoading), only for these known,
 * first-party-adjacent destinations.
 */
class WebViewActivity : AppCompatActivity() {

    private lateinit var webView: WebView

    companion object {
        const val EXTRA_URL = "extra_url"
        const val EXTRA_TITLE = "extra_title"
    }

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_web)

        val toolbar = findViewById<MaterialToolbar>(R.id.web_toolbar)
        val progress = findViewById<android.widget.ProgressBar>(R.id.web_progress)
        webView = findViewById(R.id.web_content)

        toolbar.title = intent.getStringExtra(EXTRA_TITLE) ?: ""
        toolbar.setNavigationOnClickListener { finish() }

        with(webView.settings) {
            javaScriptEnabled = true
            domStorageEnabled = true
            useWideViewPort = true
            loadWithOverviewMode = true
        }
        webView.webChromeClient = object : WebChromeClient() {
            override fun onProgressChanged(view: WebView, newProgress: Int) {
                progress.progress = newProgress
                progress.visibility = if (newProgress >= 100) View.GONE else View.VISIBLE
            }

            override fun onReceivedTitle(view: WebView, title: String?) {
                if (!title.isNullOrBlank() && intent.getStringExtra(EXTRA_TITLE).isNullOrBlank()) {
                    toolbar.title = title
                }
            }
        }

        val url = intent.getStringExtra(EXTRA_URL)
        if (url != null) webView.loadUrl(url)

        onBackPressedDispatcher.addCallback(this) {
            if (webView.canGoBack()) webView.goBack() else finish()
        }
    }
}
