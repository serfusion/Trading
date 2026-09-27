package com.xausignal.app

import android.content.Context
import org.json.JSONObject

/** Hasil satu strategi di satu periode backtest (dari research/winrate_study.py). */
data class PeriodResult(
    val period: String,
    val trades: Int,
    val winRate: Double,
    val avgR: Double,
    val totalR: Double,
    val profitFactor: Double,
    val drawdownR: Double,
)

data class StrategyResult(
    val name: String,
    val kind: String,
    val timeframe: String,
    val filter: String,
    val scheme: String,
    val pass: Boolean,
    val periods: List<PeriodResult>,
    val note: String,
) {
    /** Rata-rata win rate & R per trade di semua periode (tiap periode berbobot sama). */
    val meanWin: Double get() = if (periods.isEmpty()) 0.0 else periods.sumOf { it.winRate } / periods.size
    val meanR: Double get() = if (periods.isEmpty()) 0.0 else periods.sumOf { it.avgR } / periods.size
    val title: String get() = if (filter == "-" || filter.isBlank()) name else "$name ($filter)"
}

/** Rata-rata semua model per skema keluar; breakevenWin = win rate minimal agar impas (sebelum spread). */
data class SchemeSummary(
    val scheme: String,
    val winRate: Double,
    val avgR: Double,
    val positivePct: Double,
    val breakevenWin: Double?,
)

data class StrategyReport(
    val generated: String,
    val rule: String,
    val combos: Int,
    val combosPass: Int,
    val schemes: List<SchemeSummary>,
    val items: List<StrategyResult>,
) {
    /** Strategi dengan win rate rata-rata tertinggi (untuk contoh "win rate tinggi belum tentu untung"). */
    fun highestWinRate(): StrategyResult? = items.maxByOrNull { it.meanWin }
}

enum class StrategyFilter(val label: String) { ALL("Semua"), PASS("Lolos"), TREND("Trend"), SMC("SMC/ICT"), SCALPING("Scalping") }

enum class StrategySort(val label: String) { PROFIT("Profit"), WIN_RATE("Win rate") }

object Strategies {
    const val ASSET = "strategies.json"

    fun parse(text: String): StrategyReport {
        val j = JSONObject(text)
        val schemes = ArrayList<SchemeSummary>()
        j.optJSONArray("schemes")?.let { arr ->
            for (i in 0 until arr.length()) {
                val s = arr.getJSONObject(i)
                schemes.add(
                    SchemeSummary(
                        scheme = s.optString("scheme"),
                        winRate = s.optDouble("win", 0.0),
                        avgR = s.optDouble("avg_r", 0.0),
                        positivePct = s.optDouble("positive_pct", 0.0),
                        breakevenWin = if (s.isNull("breakeven_win")) null else s.optDouble("breakeven_win"),
                    )
                )
            }
        }
        val items = ArrayList<StrategyResult>()
        j.optJSONArray("items")?.let { arr ->
            for (i in 0 until arr.length()) {
                val o = arr.getJSONObject(i)
                val periods = ArrayList<PeriodResult>()
                o.optJSONArray("periods")?.let { ps ->
                    for (k in 0 until ps.length()) {
                        val p = ps.getJSONObject(k)
                        periods.add(
                            PeriodResult(
                                period = p.optString("period"),
                                trades = p.optInt("n", 0),
                                winRate = p.optDouble("win", 0.0),
                                avgR = p.optDouble("avg_r", 0.0),
                                totalR = p.optDouble("total_r", 0.0),
                                profitFactor = p.optDouble("pf", 0.0),
                                drawdownR = p.optDouble("dd_r", 0.0),
                            )
                        )
                    }
                }
                items.add(
                    StrategyResult(
                        name = o.optString("name"),
                        kind = o.optString("kind"),
                        timeframe = o.optString("tf"),
                        filter = o.optString("filter", "-"),
                        scheme = o.optString("scheme"),
                        pass = o.optBoolean("pass", false),
                        periods = periods,
                        note = o.optString("note"),
                    )
                )
            }
        }
        return StrategyReport(
            generated = j.optString("generated"),
            rule = j.optString("rule"),
            combos = j.optInt("combos", 0),
            combosPass = j.optInt("combos_pass", 0),
            schemes = schemes,
            items = items,
        )
    }

    fun load(context: Context): StrategyReport =
        parse(context.assets.open(ASSET).bufferedReader(Charsets.UTF_8).use { it.readText() })

    fun select(items: List<StrategyResult>, filter: StrategyFilter, sort: StrategySort): List<StrategyResult> {
        val kept = items.filter {
            when (filter) {
                StrategyFilter.ALL -> true
                StrategyFilter.PASS -> it.pass
                StrategyFilter.TREND -> it.kind == "Trend"
                StrategyFilter.SMC -> it.kind == "SMC/ICT"
                StrategyFilter.SCALPING -> it.kind == "Scalping"
            }
        }
        return when (sort) {
            StrategySort.PROFIT -> kept.sortedWith(compareByDescending<StrategyResult> { it.meanR }.thenBy { it.title })
            StrategySort.WIN_RATE -> kept.sortedWith(compareByDescending<StrategyResult> { it.meanWin }.thenBy { it.title })
        }
    }
}
