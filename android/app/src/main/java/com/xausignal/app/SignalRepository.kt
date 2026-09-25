package com.xausignal.app

import android.content.Context
import android.content.SharedPreferences
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import org.json.JSONArray
import org.json.JSONObject
import java.time.OffsetDateTime
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

/** Penyimpanan sinyal (memori + SharedPreferences) yang dipakai layar & service. */
object SignalRepository {
    private const val PREFS = "xau_signal"
    private const val MAX_EVENTS = 300

    private val _events = MutableStateFlow<List<SignalEvent>>(emptyList())
    val events: StateFlow<List<SignalEvent>> = _events

    private val _heartbeat = MutableStateFlow<SignalEvent?>(null)
    val heartbeat: StateFlow<SignalEvent?> = _heartbeat

    private val _connection = MutableStateFlow("Belum terhubung")
    val connection: StateFlow<String> = _connection

    private var prefs: SharedPreferences? = null

    @Synchronized
    fun init(context: Context) {
        if (prefs != null) return
        prefs = context.applicationContext.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        load()
    }

    fun server(): String = prefs?.getString("server", DEFAULT_SERVER) ?: DEFAULT_SERVER
    fun topic(): String = prefs?.getString("topic", "") ?: ""
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

    /** Sinyal terakhir yang belum punya sinyal TUTUP. */
    fun openSignal(events: List<SignalEvent>): SignalEvent? {
        val closed = events.filter { it.type == "close" }.map { it.id }.toSet()
        return events.firstOrNull {
            it.type == "signal" && (it.status == "signal" || it.status == "opened") && it.id !in closed
        }
    }

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
