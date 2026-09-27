package com.xausignal.app

import android.Manifest
import android.os.Build
import androidx.compose.ui.test.hasTestTag
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollToNode
import androidx.compose.ui.test.performTextClearance
import androidx.compose.ui.test.performTextInput
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.rule.GrantPermissionRule
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.rules.RuleChain
import org.junit.rules.TestRule
import org.junit.runner.RunWith
import java.time.OffsetDateTime
import java.time.ZoneOffset

/** Uji jalan aplikasi sungguhan di emulator: semua tab, data sinyal, pengaturan, tab Auto & Riset. */
@RunWith(AndroidJUnit4::class)
class AppSmokeTest {
    @get:Rule(order = 0)
    val permissions: TestRule =
        if (Build.VERSION.SDK_INT >= 33) GrantPermissionRule.grant(Manifest.permission.POST_NOTIFICATIONS)
        else RuleChain.emptyRuleChain()

    @get:Rule(order = 1)
    val compose = createAndroidComposeRule<MainActivity>()

    private fun waitForText(text: String, substring: Boolean = true, timeout: Long = 10_000) {
        compose.waitUntil(timeout) {
            compose.onAllNodesWithText(text, substring = substring).fetchSemanticsNodes().isNotEmpty()
        }
    }

    /** Dialog Pengaturan otomatis terbuka bila topik masih kosong (instal baru). */
    private fun closeSettingsIfOpen() {
        compose.waitForIdle()
        if (compose.onAllNodesWithText("Batal").fetchSemanticsNodes().isNotEmpty()) {
            compose.onNodeWithText("Batal").performClick()
            compose.waitForIdle()
        }
    }

    private fun openTab(index: Int) {
        compose.onNodeWithTag("tab_$index").performClick()
        compose.waitForIdle()
    }

    /** Item LazyColumn di luar layar belum dibuat -> gulir dulu sampai terlihat. */
    private fun scrollTo(listTag: String, text: String) {
        compose.onNodeWithTag(listTag).performScrollToNode(hasText(text, substring = true))
    }

    private fun clickChip(tag: String) {
        compose.onNodeWithTag("research_list").performScrollToNode(hasTestTag(tag))
        compose.onNodeWithTag(tag).performClick()
        compose.waitForIdle()
    }

    @Test
    fun allTabsOpenWithoutCrash() {
        closeSettingsIfOpen()
        openTab(1)
        waitForText("Harian")
        openTab(2)
        waitForText("Koneksi cloud")
        openTab(3)
        waitForText("Perbandingan semua metode")
        openTab(0)
        scrollTo("signals_list", "Riwayat sinyal")
    }

    @Test
    fun signalEventsRenderInHistoryAndStats() {
        closeSettingsIfOpen()
        val now = OffsetDateTime.now(ZoneOffset.UTC).withNano(0).toString()
        compose.runOnIdle {
            SignalRepository.add("t-hb", JSONObject("""{"type":"heartbeat","time":"$now","symbol":"XAUUSD",
                "price":4310.5,"mode":"SINYAL (cloud)","trend":"Bias H4: BULLISH","block":""}"""))
            SignalRepository.add("t-sig", JSONObject("""{"type":"signal","id":"UJI-1","time":"$now","set":"T55/20",
                "dir":"BUY","entry":4300.0,"sl":4250.0,"tp1":4350.0,"lot":"5 x 0.01","status":"signal",
                "reason":"Breakout H1 (uji)"}"""))
            SignalRepository.add("t-skip", JSONObject("""{"type":"signal","id":"UJI-2","time":"$now","set":"T40/15",
                "dir":"SELL","entry":4300.0,"sl":4350.0,"tp1":4250.0,"status":"skipped",
                "note":"Bias struktur H4 BULLISH tidak searah SELL (filter SMC)"}"""))
            SignalRepository.add("t-info", JSONObject("""{"type":"info","id":"UJI-1","time":"$now",
                "text":"TP1 kena -> SL+ aktif (uji)"}"""))
            SignalRepository.add("t-close", JSONObject("""{"type":"close","id":"UJI-1","time":"$now","set":"T55/20",
                "dir":"BUY","price":4400.0,"points":100.0,"r":2.0,"risk_points":50.0,"legs":5,
                "reason":"Close H1 < low 20 bar (uji)"}"""))
        }
        openTab(0)
        scrollTo("signals_list", "Dilewati: Bias struktur H4")
        scrollTo("signals_list", "MENANG")
        scrollTo("signals_list", "TP1 kena -> SL+ aktif (uji)")
        openTab(1)
        waitForText("Win rate 100%")
    }

    @Test
    fun researchTabFiltersAndSorts() {
        closeSettingsIfOpen()
        openTab(3)
        waitForText("Perbandingan semua metode")
        clickChip("filter_PASS")
        scrollTo("research_list", "LOLOS")
        clickChip("filter_SCALPING")
        clickChip("sort_WIN_RATE")
        scrollTo("research_list", "Scalping RSI(2)")
        clickChip("filter_SMC")
        scrollTo("research_list", "Silver Bullet")
        clickChip("filter_TREND")
        scrollTo("research_list", "Trend F-ensemble")
        clickChip("filter_ALL")
        clickChip("sort_PROFIT")
        scrollTo("research_list", "Unicorn")
    }

    @Test
    fun settingsSaveRestartsServiceAndNormalizesServer() {
        closeSettingsIfOpen()
        compose.onNodeWithContentDescription("Pengaturan").performClick()
        waitForText("Topik")
        compose.onNodeWithText("Server").performTextClearance()
        compose.onNodeWithText("Server").performTextInput("ntfy.sh/")
        compose.onNodeWithText("Topik").performTextClearance()
        compose.onNodeWithText("Topik").performTextInput("xau-uji-otomatis-000")
        compose.onNodeWithText("Simpan").performClick()
        compose.waitForIdle()
        assertEquals("https://ntfy.sh", SignalRepository.server())
        assertEquals("xau-uji-otomatis-000", SignalRepository.topic())
        openTab(0)
        scrollTo("signals_list", "Riwayat sinyal")
    }

    @Test
    fun autoTabShowsErrorForUnreachableCloud() {
        closeSettingsIfOpen()
        openTab(2)
        waitForText("Koneksi cloud")
        if (compose.onAllNodesWithText("Ubah").fetchSemanticsNodes().isNotEmpty()) {
            compose.onNodeWithText("Ubah").performClick()
        }
        compose.onNodeWithText("URL cloud", substring = true).performTextClearance()
        compose.onNodeWithText("URL cloud", substring = true).performTextInput("http://127.0.0.1:9")
        compose.onNodeWithText("CONTROL_KEY", substring = true).performTextInput("kunci-uji")
        compose.onNodeWithText("Simpan & hubungkan").performClick()
        waitForText("❌", timeout = 30_000)                      // gagal konek -> pesan, bukan crash
    }
}
