package com.xausignal.app

import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class AutoControlTest {
    @Test
    fun parseFullStatus() {
        val s = AutoControl.parse(
            JSONObject(
                """{"ok":true,"executor":true,"bias":"BULLISH","guard":"Batas rugi harian 3% tercapai",
                "session_block":"Rollover harian (spread lebar)",
                "control":{"auto":true,"paused":false,"leg_lot":0.02,"legs":4,"bias_filter":false,
                           "daily_loss_pct":2.5,"weekly_loss_pct":5},
                "account":{"balance":30000,"equity":29500.5,"currency":"USC"},
                "positions":[{"id":"7","dir":"BUY","volume":0.02,"open":4300.1,"sl":4250,"tp":null,"profit":12.3}]}"""
            )
        )
        assertTrue(s.auto && s.executor)
        assertFalse(s.paused || s.biasFilter)
        assertEquals(0.02, s.legLot, 1e-9)
        assertEquals(4, s.legs)
        assertEquals(2.5, s.dailyLoss, 1e-9)
        assertEquals(5.0, s.weeklyLoss, 1e-9)
        assertEquals("BULLISH", s.bias)
        assertTrue(s.guard.startsWith("Batas rugi harian"))
        assertEquals(29500.5, s.equity!!, 1e-9)
        assertEquals(1, s.positions.size)
        assertNull(s.positions[0].tp)
    }

    @Test
    fun parseDefaultsWhenCloudIsOld() {
        val s = AutoControl.parse(JSONObject("""{"ok":true,"executor":false,"control":{}}"""))
        assertFalse(s.auto)
        assertTrue(s.biasFilter)
        assertEquals(0.01, s.legLot, 1e-9)
        assertEquals(5, s.legs)
        assertEquals(3.0, s.dailyLoss, 1e-9)
        assertEquals(6.0, s.weeklyLoss, 1e-9)
        assertNull(s.balance)
        assertTrue(s.positions.isEmpty())
    }
}
