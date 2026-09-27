package com.xausignal.app

import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

class SignalRepositoryTest {
    private val usd = MoneySettings(cent = false, legLot = 0.01, idrRate = 16000.0)

    private fun ev(id: String, json: String) = SignalEvent(id, JSONObject(json).optString("type"), JSONObject(json))

    @Before
    fun reset() = SignalRepository.clear()

    @Test
    fun amountFromRAndPnl() {
        val close = ev("1", """{"type":"close","r":1.0,"risk_points":10.0,"legs":5}""")
        assertEquals(50.0, SignalRepository.amount(close, usd)!!, 1e-9)            // 1R x 10 poin x 5 posisi
        assertEquals(100.0, SignalRepository.amount(close, usd.copy(legLot = 0.02))!!, 1e-9)
        val pnl = ev("2", """{"type":"close","pnl":-12.5,"r":1.0,"risk_points":10.0}""")
        assertEquals(-12.5, SignalRepository.amount(pnl, usd)!!, 1e-9)
        assertNull(SignalRepository.amount(ev("3", """{"type":"close"}"""), usd))
        assertEquals(16000.0, SignalRepository.toIdr(1.0, usd), 1e-9)
        assertEquals(160.0, SignalRepository.toIdr(1.0, usd.copy(cent = true)), 1e-9)
    }

    @Test
    fun periodStatsGroupsWinsAndLosses() {
        val events = listOf(
            ev("a", """{"type":"close","time":"2026-09-25T03:00:00+00:00","r":2.0,"risk_points":5,"legs":1}"""),
            ev("b", """{"type":"close","time":"2026-09-25T05:00:00+00:00","r":-1.0,"risk_points":5,"legs":1}"""),
            ev("c", """{"type":"close","time":"2026-09-26 05:00:00+00:00","r":1.0,"risk_points":5,"legs":1}"""),
            ev("d", """{"type":"close","time":"bukan-waktu","r":1.0,"risk_points":5,"legs":1}"""),
            ev("e", """{"type":"signal","time":"2026-09-26T05:00:00+00:00","status":"signal"}"""),
        )
        val daily = SignalRepository.periodStats(events, usd, { it.toLocalDate().toString() })
        assertEquals(listOf("2026-09-26", "2026-09-25"), daily.map { it.label })
        val d25 = daily[1]
        assertEquals(1, d25.wins)
        assertEquals(1, d25.losses)
        assertEquals(10.0, d25.profit, 1e-9)
        assertEquals(-5.0, d25.loss, 1e-9)
        assertEquals(5.0, d25.net, 1e-9)
    }

    @Test
    fun openSignalsIgnoreSkippedAndClosed() {
        val events = listOf(
            ev("1", """{"type":"signal","id":"A","status":"signal","dir":"BUY"}"""),
            ev("2", """{"type":"signal","id":"B","status":"skipped","dir":"SELL"}"""),
            ev("3", """{"type":"signal","id":"C","status":"opened","dir":"BUY"}"""),
            ev("4", """{"type":"close","id":"C","r":0.5}"""),
            ev("5", """{"type":"info","id":"A","text":"TP1 kena -> SL+ aktif"}"""),
        )
        assertEquals(listOf("A"), SignalRepository.openSignals(events).map { it.id })
        assertTrue(SignalRepository.slPlusActive(events, "A"))
        val st = SignalRepository.stats(events)
        assertEquals(1, st.closed)
        assertEquals(1, st.wins)
    }

    @Test
    fun addDeduplicatesAndKeepsHeartbeatSeparate() {
        val sig = JSONObject("""{"type":"signal","id":"X","status":"signal"}""")
        assertTrue(SignalRepository.add("m1", sig) != null)
        assertNull(SignalRepository.add("m1", sig))                                // pesan sama tidak dobel
        SignalRepository.add("hb", JSONObject("""{"type":"heartbeat","price":4300}"""))
        assertEquals(1, SignalRepository.events.value.size)
        assertEquals(4300.0, SignalRepository.heartbeat.value!!.num("price")!!, 1e-9)
    }

    @Test
    fun serverUrlIsNormalized() {
        assertEquals("https://ntfy.sh", SignalRepository.normalizeServer("ntfy.sh/"))
        assertEquals("http://10.0.2.2:8080", SignalRepository.normalizeServer(" http://10.0.2.2:8080 "))
        assertEquals(SignalRepository.DEFAULT_SERVER, SignalRepository.normalizeServer("  "))
    }

    @Test
    fun formatting() {
        assertEquals("1,234.50", fmt(1234.5))
        assertEquals("-", fmt(null))
        assertEquals("+0.25", signed(0.25))
        assertEquals("-1.0", signed(-1.0, 1))
        assertTrue(formatTime("2026-09-27T04:00:00+00:00").endsWith("11:00 WIB"))
        assertEquals("salah", formatTime("salah"))
    }
}
