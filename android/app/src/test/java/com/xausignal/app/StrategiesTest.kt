package com.xausignal.app

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

class StrategiesTest {
    /** File asli yang dibundel ke APK (dibuat oleh research/winrate_study.py). */
    private val asset = File("src/main/assets/strategies.json")

    @Test
    fun bundledReportIsValid() {
        val report = Strategies.parse(asset.readText())
        assertTrue(report.items.size >= 10)
        assertTrue(report.combos > 0)
        assertTrue(report.combosPass in 0..report.combos)
        assertTrue(report.schemes.isNotEmpty())
        for (item in report.items) {
            assertTrue(item.name.isNotBlank())
            assertTrue(item.kind in setOf("Trend", "SMC/ICT", "Scalping"))
            assertTrue(item.periods.isNotEmpty())
            for (p in item.periods) {
                assertTrue(p.winRate in 0.0..100.0)
                assertFalse(p.avgR.isNaN() || p.totalR.isNaN() || p.profitFactor.isNaN())
            }
            // LOLOS harus konsisten dengan angka: untung di semua periode
            if (item.pass) assertTrue(item.periods.all { it.avgR > 0 && it.trades >= 30 })
        }
        // kunci daftar di layar harus unik (LazyColumn crash bila kunci dobel)
        val keys = report.items.map { "${it.title}|${it.scheme}" }
        assertEquals(keys.size, keys.toSet().size)
    }

    @Test
    fun filterAndSort() {
        val report = Strategies.parse(asset.readText())
        val passed = Strategies.select(report.items, StrategyFilter.PASS, StrategySort.PROFIT)
        assertTrue(passed.all { it.pass })
        val scalping = Strategies.select(report.items, StrategyFilter.SCALPING, StrategySort.WIN_RATE)
        assertTrue(scalping.isNotEmpty() && scalping.all { it.kind == "Scalping" })
        assertTrue(scalping.zipWithNext().all { (a, b) -> a.meanWin >= b.meanWin })
        val all = Strategies.select(report.items, StrategyFilter.ALL, StrategySort.PROFIT)
        assertEquals(report.items.size, all.size)
        assertTrue(all.zipWithNext().all { (a, b) -> a.meanR >= b.meanR })
        assertNotNull(report.highestWinRate())
    }

    @Test
    fun parseToleratesMissingFields() {
        val report = Strategies.parse(
            """{"items":[{"name":"X","kind":"Scalping","periods":[{"period":"2025-26","n":5,"win":60,"avg_r":-0.1}]}],
               "schemes":[{"scheme":"TP 1R","win":41,"avg_r":-0.2,"breakeven_win":null}]}"""
        )
        assertEquals(1, report.items.size)
        assertEquals("X", report.items[0].title)
        assertEquals(60.0, report.items[0].meanWin, 1e-9)
        assertEquals(null, report.schemes[0].breakevenWin)
        assertEquals(0, Strategies.parse("{}").items.size)
    }
}
