package com.xausignal.app

import android.content.Context
import android.content.SharedPreferences
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import org.json.JSONArray
import org.json.JSONObject
import java.time.LocalDateTime
import java.time.OffsetDateTime
import java.time.ZoneOffset
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Locale

/** Satu pesan dari bot (signal / close / heartbeat / info). */
data class SignalEvent(val msgId: String, val type: String, val json: JSONObject) {
    val id: String get() = str("id").ifBlank { msgId }
    val dir: String get() = str("dir")
    val status: String get() = str("status")

    fun str(key: String): String =
        if (json.has(key) && !json.isNull(key)) json.optString(key, "") else ""

    fun num(key: String): Double? =
        if (json.has(key) && !json.isNull(key)) json.optDouble(key).takeIf { !it.isNaN() } else null

    fun timeText(): String = formatTime(str("time"))
}

private val WIB: ZoneId = ZoneId.of("Asia/Jakarta")
private val TIME_FMT: DateTimeFormatter = DateTimeFormatter.ofPattern("dd MMM HH:mm", Locale("id"))

fun formatTime(raw: String): String = try {
    OffsetDateTime.parse(raw.replace(" ", "T")).atZoneSameInstant(WIB).format(TIME_FMT) + " WIB"
} catch (e: Exception) {
    raw
}

fun fmt(value: Double?, digits: Int = 2): String =
    if (value == null) "-" else String.format(Locale.US, "%,.${digits}f", value)

data class Stats(val closed: Int, val wins: Int, val totalR: Double)

/** Pengaturan uang untuk menghitung profit/rugi dari sinyal. */
data class MoneySettings(val cent: Boolean, val legLot: Double, val idrRate: Double, val starLot: Double = legLot) {
    val currency: String get() = if (cent) "USC" else "USD"

    /** Lot per posisi: sinyal ⭐ memakai lot ⭐, sinyal biasa memakai lot biasa. */
    fun lotFor(star: Boolean): Double = if (star) starLot else legLot
}

fun SignalEvent.isStar(): Boolean = json.optBoolean("star", false)

/** Simbol sinyal (XAU/USD bila kosong). */
fun SignalEvent.symbol(): String = str("symbol").ifBlank { "XAU/USD" }

/** Harga dengan digit sesuai instrumen: JPY 3, forex lain 5, emas/indeks 2. */
fun SignalEvent.price(key: String): String {
    val v = num(key) ?: return "-"
    val sym = symbol()
    val digits = if (sym.contains("JPY")) 3 else if (v < 20) 5 else 2
    return fmt(v, digits)
}

/** Jumlah ⭐ (win rate historis) dan 💸 (profit historis). Sinyal lama: ⭐ = tanda kuat lama. */
fun SignalEvent.stars(): Int = if (json.has("stars")) json.optInt("stars") else if (isStar()) 1 else 0
fun SignalEvent.moneyBadge(): Int = json.optInt("money", 0)

/** "WR 82% • +0,26R/sinyal (2012–2020, 34 sinyal)" atau kosong untuk sinyal lama. */
fun SignalEvent.statsLine(): String {
    if (!json.has("wr")) return ""
    val avg = json.optDouble("avg_r")
    val sign = if (avg > 0) "+" else ""
    return "WR ${fmt(json.optDouble("wr"), 0)}% • ${sign}${fmt(avg, 2)}R/sinyal " +
        "(${str("period")}, ${json.optInt("n_hist")} sinyal)"
}

private val NEW_YORK: ZoneId = ZoneId.of("America/New_York")
private val STAMP: DateTimeFormatter = DateTimeFormatter.ofPattern("yyyyMMddHHmm")

/**
 * Sinyal batal: ditandai cloud (void) atau lahir dari candle akhir pekan saat pasar tutup
 * (Jumat 17:00 – Minggu 18:00 New York). ID sinyal cloud berakhiran waktu candle UTC, mis. ...-202609272100.
 */
fun SignalEvent.isVoid(): Boolean {
    if (json.optBoolean("void", false)) return true
    val stamp = id.substringAfterLast('-')
    if (stamp.length != 12 || !stamp.all { it.isDigit() }) return false
    return try {
        val ny = LocalDateTime.parse(stamp, STAMP).atZone(ZoneOffset.UTC).withZoneSameInstant(NEW_YORK)
        val wd = ny.dayOfWeek.value   // Senin = 1 ... Minggu = 7
        wd == 6 || (wd == 5 && ny.hour >= 17) || (wd == 7 && ny.hour < 18)
    } catch (e: Exception) {
        false
    }
}

data class PeriodStats(
    val label: String,
    val wins: Int,
    val losses: Int,
    val profit: Double,   // jumlah untung (mata uang akun)
    val loss: Double,     // jumlah rugi (negatif)
) {
    val net: Double get() = profit + loss
    val total: Int get() = wins + losses
}

/** Penyimpanan sinyal (memori + SharedPreferences) yang dipakai layar & service. */
object SignalRepository {
    private const val PREFS = "xau_signal"
    private const val MAX_EVENTS = 300

    private val _events = MutableStateFlow<List<SignalEvent>>(emptyList())
    val events: StateFlow<List<SignalEvent>> = _events

    private val _heartbeat = MutableStateFlow<SignalEvent?>(null)
    val heartbeat: StateFlow<SignalEvent?> = _heartbeat

    private val _connection = MutableStateFlow("Memuat...")
    val connection: StateFlow<String> = _connection

    private var prefs: SharedPreferences? = null

    @Synchronized
    fun init(context: Context) {
        if (prefs != null) return
        prefs = context.applicationContext.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        load()
    }

    fun server(): String = prefs?.getString("server", DEFAULT_SERVER) ?: DEFAULT_SERVER

    /**
     * Lot disimpan sebagai teks ("0.02"). Versi lama menyimpan Float: 0.01f dibaca sebagai Double menjadi
     * 0.009999999776482582, jadi nilai lama tetap dibaca lalu dibulatkan ke kelipatan 0,01.
     */
    fun money(): MoneySettings {
        val p = prefs
        val lot = p?.getString("leg_lot_text", null)?.toDoubleOrNull()
            ?: p?.let { if (it.contains("leg_lot")) it.getFloat("leg_lot", 0.01f).toDouble() else null }
            ?: 0.01
        val star = p?.getString("star_lot_text", null)?.toDoubleOrNull() ?: lot
        return MoneySettings(
            cent = p?.getBoolean("cent", true) ?: true,
            legLot = roundLot(lot).coerceAtLeast(0.01),
            idrRate = Math.round((p?.getFloat("idr_rate", 16500f) ?: 16500f).toDouble()).toDouble(),
            starLot = roundLot(star).coerceAtLeast(0.01),
        )
    }

    fun saveMoney(m: MoneySettings) {
        prefs?.edit()?.putBoolean("cent", m.cent)?.putString("leg_lot_text", lotText(m.legLot))?.remove("leg_lot")
            ?.putString("star_lot_text", lotText(m.starLot))
            ?.putFloat("idr_rate", m.idrRate.toFloat())?.apply()
        _moneyVersion.value = _moneyVersion.value + 1
    }

    private val _moneyVersion = MutableStateFlow(0)
    val moneyVersion: StateFlow<Int> = _moneyVersion

    /** Profit/rugi satu sinyal TUTUP dalam mata uang akun (USD atau USC). */
    fun amount(e: SignalEvent, m: MoneySettings): Double? {
        e.num("pnl")?.let { return it }
        val r = e.num("r") ?: return null
        val risk = e.num("risk_points") ?: return null
        val legs = e.num("legs") ?: 5.0
        // 0,01 lot = 1 oz -> 1 unit mata uang akun per 1 poin harga (USD untuk akun USD, USC untuk Cent)
        val pointValue = e.num("point_value") ?: 1.0     // forex: nilai 1,0 harga per 0,01 lot
        return r * risk * legs * Math.round(m.lotFor(e.isStar()) * 100.0) * pointValue
    }

    fun toIdr(amount: Double, m: MoneySettings): Double =
        if (m.cent) amount / 100.0 * m.idrRate else amount * m.idrRate

    private fun zoned(e: SignalEvent): java.time.ZonedDateTime? = try {
        OffsetDateTime.parse(e.str("time").replace(" ", "T")).atZoneSameInstant(WIB)
    } catch (ex: Exception) {
        null
    }

    fun periodStats(events: List<SignalEvent>, m: MoneySettings, keyOf: (java.time.ZonedDateTime) -> String,
                    labelOf: (String) -> String = { it }, star: Boolean? = null): List<PeriodStats> {
        val groups = LinkedHashMap<String, MutableList<Double>>()
        events.filter { it.type == "close" && !it.isVoid() && (star == null || it.isStar() == star) }.forEach { e ->
            val t = zoned(e) ?: return@forEach
            val a = amount(e, m) ?: return@forEach
            groups.getOrPut(keyOf(t)) { mutableListOf() }.add(a)
        }
        return groups.entries.sortedByDescending { it.key }.map { (k, v) ->
            PeriodStats(labelOf(k), v.count { it > 0 }, v.count { it <= 0 },
                v.filter { it > 0 }.sum(), v.filter { it <= 0 }.sum())
        }
    }
    fun topic(): String = prefs?.getString("topic", "") ?: ""

    fun termsAccepted(): Boolean = prefs?.getBoolean("terms_ok", false) ?: false
    fun acceptTerms() {
        prefs?.edit()?.putBoolean("terms_ok", true)?.apply()
    }

    fun lastMessageId(): String? = prefs?.getString("last_id", null)

    @Synchronized
    fun saveSettings(server: String, topic: String) {
        val changed = server != server() || topic != topic()
        prefs?.edit()?.putString("server", server.trim().trimEnd('/'))?.putString("topic", topic.trim())?.apply()
        if (changed) clear()
    }

    fun setConnection(text: String) {
        _connection.value = text
    }

    @Synchronized
    fun clear() {
        _events.value = emptyList()
        _heartbeat.value = null
        prefs?.edit()?.remove("last_id")?.remove("events")?.remove("heartbeat")?.apply()
    }

    /** Tambah pesan; return null bila duplikat. */
    @Synchronized
    fun add(msgId: String, payload: JSONObject): SignalEvent? {
        val type = payload.optString("type", "info")
        val event = SignalEvent(msgId, type, payload)
        prefs?.edit()?.putString("last_id", msgId)?.apply()
        if (type == "heartbeat") {
            _heartbeat.value = event
            prefs?.edit()?.putString("heartbeat", payload.toString())?.apply()
            return event
        }
        if (_events.value.any { it.msgId == msgId }) return null
        _events.value = (listOf(event) + _events.value).take(MAX_EVENTS)
        persist()
        return event
    }

    /** Semua sinyal (per set) yang belum punya sinyal TUTUP. */
    fun openSignals(events: List<SignalEvent>): List<SignalEvent> {
        val closed = events.filter { it.type == "close" }.map { it.id }.toSet()
        return events.filter {
            it.type == "signal" && (it.status == "signal" || it.status == "opened") && it.id !in closed && !it.isVoid()
        }
    }

    fun slPlusActive(events: List<SignalEvent>, signalId: String): Boolean = tp1Event(events, signalId) != null

    /** Info TP1 kena (lalu SL+) untuk sinyal ini, bila ada. */
    fun tp1Event(events: List<SignalEvent>, signalId: String): SignalEvent? =
        events.firstOrNull { it.type == "info" && it.str("id") == signalId && it.str("text").contains("TP1") }

    fun closeEvent(events: List<SignalEvent>, signalId: String): SignalEvent? =
        events.firstOrNull { it.type == "close" && it.id == signalId }

    fun stats(events: List<SignalEvent>): Stats {
        val closes = events.filter { it.type == "close" && it.num("r") != null }
        val rs = closes.mapNotNull { it.num("r") }
        return Stats(rs.size, rs.count { it > 0 }, rs.sum())
    }

    private fun persist() {
        val arr = JSONArray()
        _events.value.forEach { arr.put(JSONObject().put("m", it.msgId).put("p", it.json)) }
        prefs?.edit()?.putString("events", arr.toString())?.apply()
    }

    private fun load() {
        val p = prefs ?: return
        try {
            val arr = JSONArray(p.getString("events", "[]"))
            val list = ArrayList<SignalEvent>()
            for (i in 0 until arr.length()) {
                val o = arr.getJSONObject(i)
                val payload = o.getJSONObject("p")
                list.add(SignalEvent(o.getString("m"), payload.optString("type", "info"), payload))
            }
            _events.value = list
            p.getString("heartbeat", null)?.let {
                val hb = JSONObject(it)
                _heartbeat.value = SignalEvent("hb", "heartbeat", hb)
            }
        } catch (e: Exception) {
            _events.value = emptyList()
        }
    }

    const val DEFAULT_SERVER = "https://ntfy.sh"
}
