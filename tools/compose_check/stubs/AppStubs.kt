package com.xausignal.app

import android.content.Context
import org.json.JSONObject
import java.util.Locale

fun idrText(value: Double): String = "Rp" + String.format(Locale("id", "ID"), "%,.0f", Math.abs(value))
fun moneyMain(value: Double, m: MoneySettings): String = "${signed(value)} ${m.currency}"
fun idrLine(value: Double, m: MoneySettings): String {
    val idr = SignalRepository.toIdr(value, m)
    val sign = if (idr > 0) "+" else if (idr < 0) "−" else ""
    return "≈ $sign${idrText(idr)}"
}

object NewsAlarm {
    const val OPEN_REFRESH = 15 * 60_000L
    data class Item(val at: Long, val title: String, val whenText: String, val info: String, val specific: Boolean = false)
    fun enabled(context: Context): Boolean = true
    fun setEnabled(context: Context, on: Boolean) {}
    fun update(context: Context, calendar: List<CalEvent>, persiapan: JSONObject?) {}
    fun next(context: Context, now: Long = System.currentTimeMillis()): Item? = null
    fun refreshIfStale(context: Context, maxAge: Long = 0) {}
}

object SignalPoller { fun poll(context: Context): Int = 0 }
