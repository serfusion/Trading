package com.xausignal.app

import android.content.Context
import android.content.SharedPreferences
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone
import java.util.concurrent.TimeUnit

/**
 * 👁 Follow / unfollow copy trader (aplikasi 4.16, permintaan pengguna 7 Okt 2026). Daftar follow disimpan di CLOUD
 * (baris Supabase `ikuti`, POST /api/chat {"ikuti": …}); cloud memeriksa posisi trader tiap ±15 detik (cloud/api/
 * _ikuti.py) dan mengirim kejadian BUKA/TUTUP ke topik ntfy `<topik>-copy`. Layanan ⚡ (CopyStream.kt) mendengarkan
 * topik itu terus-menerus → notifikasi ±detik. Info saja — aplikasi TIDAK membuka order di akun Anda.
 */
object CopyFollow {
    private val client = OkHttpClient.Builder().connectTimeout(15, TimeUnit.SECONDS).readTimeout(30, TimeUnit.SECONDS).build()
    private var prefs: SharedPreferences? = null
    var keys by mutableStateOf<Set<String>>(emptySet())
    var instant by mutableStateOf(true)
    var status by mutableStateOf<JSONObject?>(null)
    var log by mutableStateOf<List<JSONObject>>(emptyList())
    var error by mutableStateOf("")

    @Synchronized
    fun init(context: Context) {
        if (prefs != null) return
        val p = context.applicationContext.getSharedPreferences("copy_follow", Context.MODE_PRIVATE)
        prefs = p
        keys = (p.getString("keys", "") ?: "").split("\n").filter { it.isNotBlank() }.toSet()
        instant = p.getBoolean("instant", true)
        log = runCatching {
            val a = JSONArray(p.getString("log", "[]") ?: "[]")
            (0 until a.length()).mapNotNull { a.optJSONObject(it) }
        }.getOrDefault(emptyList())
    }

    fun key(x: JSONObject): String = "${x.optString("platform")}|${x.optString("id")}"
    fun canFollow(x: JSONObject): Boolean = !x.optString("platform").startsWith("MQL5")
    fun isFollowed(x: JSONObject): Boolean = key(x) in keys

    private fun saveKeys(k: Set<String>) {
        keys = k
        prefs?.edit()?.putString("keys", k.joinToString("\n"))?.apply()
    }

    fun setInstant(context: Context, on: Boolean) {
        instant = on
        prefs?.edit()?.putBoolean("instant", on)?.apply()
        CopyStreamControl.sync(context)
    }

    /** ntfy id pesan terakhir topik -copy (layanan ⚡ & poll cadangan memakai yang sama → tidak ada yang terlewat). */
    fun lastId(): String? = prefs?.getString("last_id", null)
    fun setLastId(id: String) {
        prefs?.edit()?.putString("last_id", id)?.apply()
    }

    /** true bila pesan ini belum pernah diproses (layanan ⚡ dan poll cadangan bisa menerima pesan yang sama). */
    @Synchronized
    fun firstTime(msgId: String): Boolean {
        val p = prefs ?: return true
        val seen = (p.getString("seen", "") ?: "").split(",").filter { it.isNotBlank() }
        if (msgId in seen) return false
        p.edit().putString("seen", (seen + msgId).takeLast(60).joinToString(",")).apply()
        return true
    }

    @Synchronized
    fun addLog(events: List<JSONObject>) {
        if (events.isEmpty()) return
        val known = log.map { it.optString("id") }.toSet()
        log = (events.filter { it.optString("id") !in known }.reversed() + log).take(60)
        prefs?.edit()?.putString("log", JSONArray(log).toString())?.apply()
    }

    /** Follow / unfollow lewat cloud. Return null bila sukses, atau pesan galat. */
    suspend fun toggle(context: Context, x: JSONObject, on: Boolean): String? = withContext(Dispatchers.IO) {
        init(context)
        val base = SignalRepository.cloudUrl()
        if (base.isBlank()) return@withContext "Isi alamat cloud di Pengaturan dulu."
        val item = JSONObject().put("platform", x.optString("platform")).put("id", x.optString("id"))
            .put("name", x.optString("name")).put("url", x.optString("url")).put("on", on)
        val body = JSONObject().put("ikuti", item).toString().toRequestBody("application/json; charset=utf-8".toMediaType())
        try {
            client.newCall(Request.Builder().url("$base/api/chat").post(body)
                .header("X-Chat-Key", SignalRepository.topic()).build()).execute().use { res ->
                val j = JSONObject(res.body?.string().orEmpty())
                if (!j.optBoolean("ok")) return@withContext j.optString("error").ifBlank { "Cloud belum versi terbaru (HTTP ${res.code})." }
                syncKeys(j.optJSONArray("list"))
            }
            CopyStreamControl.sync(context)
            null
        } catch (e: Exception) {
            "Gagal: ${(e.message ?: e.javaClass.simpleName).take(60)}"
        }
    }

    private fun syncKeys(list: JSONArray?) {
        list ?: return
        saveKeys((0 until list.length()).mapNotNull { list.optJSONObject(it) }.map { key(it) }.toSet())
    }

    /** GET /api/chat?ikuti=1: trader diikuti + posisi terbuka terakhir + kejadian terbaru (cloud = sumber kebenaran). */
    suspend fun refresh(context: Context) = withContext(Dispatchers.IO) {
        init(context)
        val base = SignalRepository.cloudUrl()
        if (base.isBlank()) return@withContext
        try {
            client.newCall(Request.Builder().url("$base/api/chat?ikuti=1").get()
                .header("X-Chat-Key", SignalRepository.topic()).build()).execute().use { res ->
                val j = JSONObject(res.body?.string().orEmpty())
                if (j.optBoolean("ok")) {
                    status = j
                    error = ""
                    val before = keys
                    syncKeys(j.optJSONArray("list"))
                    val l = j.optJSONArray("log")
                    if (l != null) addLog((0 until l.length()).mapNotNull { l.optJSONObject(it) }.reversed())
                    if (before != keys) CopyStreamControl.sync(context)
                } else {
                    error = j.optString("error").ifBlank { "Cloud belum versi terbaru (HTTP ${res.code})" }
                }
            }
        } catch (e: Exception) {
            error = "Gagal memuat: ${(e.message ?: e.javaClass.simpleName).take(50)}"
        }
    }
}

private fun pxText(v: Double?): String = when {
    v == null || v.isNaN() -> "-"
    kotlin.math.abs(v) >= 1000 -> fmt(v, 1)
    kotlin.math.abs(v) >= 1 -> fmt(v, 3)
    else -> fmt(v, 6)
}

private fun JSONObject.numOrNull(k: String): Double? = if (isNull(k)) null else optDouble(k).takeIf { !it.isNaN() }

private fun localTime(iso: String): String = runCatching {
    val f = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.US).apply { timeZone = TimeZone.getTimeZone("UTC") }
    SimpleDateFormat("dd MMM HH:mm:ss", Locale("id", "ID")).format(f.parse(iso) ?: Date())
}.getOrDefault(iso.take(16))

/** Satu baris kejadian follow: "🟢 BUKA BUY BTC @ 85.110 • Budi (Bitget)". */
fun copyEventText(e: JSONObject): Pair<String, String> {
    val who = "${e.optString("name")} (${e.optString("platform")})"
    val sym = e.optString("symbol")
    val arah = e.optString("arah").takeIf { it == "BUY" || it == "SELL" } ?: ""
    return when (e.optString("type")) {
        "copy_open" -> {
            val extra = listOfNotNull(e.numOrNull("tp")?.let { "TP ${pxText(it)}" }, e.numOrNull("sl")?.let { "SL ${pxText(it)}" },
                e.numOrNull("lev")?.let { "${it.toInt()}x" }).joinToString(" • ")
            "🟢 BUKA $arah $sym @ ${pxText(e.numOrNull("entry"))}" to (if (extra.isBlank()) who else "$extra • $who")
        }
        "copy_close" -> {
            val g = e.numOrNull("gerak")
            "🏁 TUTUP $arah $sym" + (g?.let { " • ${if (it >= 0) "PROFIT" else "MINUS"} ${signed(it, 2)}%" } ?: "") to
                "${pxText(e.numOrNull("entry"))} → ${pxText(e.numOrNull("tutup"))} • $who"
        }
        "copy_follow" -> {
            val n = e.optJSONArray("posisi")?.length() ?: 0
            "👁 Mulai mengikuti ${e.optString("name")}" to "$n posisi terbuka saat follow • ${e.optString("platform")}"
        }
        else -> e.optString("type") to who
    }
}

/** Tombol Follow/Unfollow di jendela detail trader. */
@Composable
fun FollowButton(x: JSONObject) {
    val context = androidx.compose.ui.platform.LocalContext.current
    LaunchedEffect(Unit) { CopyFollow.init(context) }
    var busy by remember { mutableStateOf(false) }
    var msg by remember { mutableStateOf("") }
    var go by remember { mutableStateOf<Boolean?>(null) }
    LaunchedEffect(go) {
        val on = go ?: return@LaunchedEffect
        busy = true
        msg = CopyFollow.toggle(context, x, on) ?: if (on) "Diikuti ✓ — notifikasi saat trader BUKA/TUTUP posisi." else "Berhenti mengikuti."
        busy = false
        go = null
    }
    if (!CopyFollow.canFollow(x)) {
        Text("MQL5 tidak membuka posisi publik — tidak bisa di-follow.", style = MaterialTheme.typography.labelSmall, color = Muted)
        return
    }
    val on = CopyFollow.isFollowed(x)
    AppCard(accent = if (on) BuyColor else Gold) {
        Row(Modifier.fillMaxWidth().clickable(enabled = !busy) { go = !on }, verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text(if (busy) "Menyimpan…" else if (on) "✓ DIIKUTI • ketuk untuk Unfollow" else "➕ FOLLOW trader ini",
                    fontWeight = FontWeight.ExtraBold, color = if (on) BuyColor else Gold)
                Text(msg.ifBlank { "Notifikasi otomatis saat dia buka & tutup posisi (cek tiap ±15 dtk). Tanpa order." },
                    style = MaterialTheme.typography.labelSmall, color = Muted)
            }
        }
    }
    if (x.optString("platform") == "Binance" && x.has("terlihat") && !x.optBoolean("terlihat")) {
        Text("⚠️ Trader ini menyembunyikan posisi di Binance — buka/tutup tidak akan terdeteksi.",
            style = MaterialTheme.typography.labelSmall, color = SellColor)
    }
}

/** 👁 Bagian "Diikuti": trader yang di-follow, posisi terbuka mereka, dan kejadian BUKA/TUTUP terbaru. */
@Composable
fun CopyFollowSection(onOpen: (JSONObject) -> Unit) {
    val context = androidx.compose.ui.platform.LocalContext.current
    LaunchedEffect(Unit) {
        CopyFollow.init(context)
        while (true) {                                    // selama tab terbuka: segarkan tiap 15 detik
            CopyFollow.refresh(context)
            delay(15_000L)
        }
    }
    if (CopyFollow.keys.isEmpty() && CopyFollow.log.isEmpty()) return
    val st = CopyFollow.status
    val rows = st?.optJSONArray("list")?.let { a -> (0 until a.length()).mapNotNull { a.optJSONObject(it) } }.orEmpty()
    SectionTitle("👁 Trader diikuti", trailing = "${CopyFollow.keys.size}")
    AppCard {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(CopyFollow.error.ifBlank { st?.optString("pantau") ?: "Memuat…" }, Modifier.weight(1f),
                style = MaterialTheme.typography.labelSmall,
                color = if (CopyFollow.error.isNotBlank() || (st?.optString("pantau") ?: "").startsWith("⚠️")) SellColor else Muted)
            Text(if (CopyFollow.instant) "⚡ Instan ON" else "⚡ Instan OFF",
                Modifier.clickable { CopyFollow.setInstant(context, !CopyFollow.instant) },
                style = MaterialTheme.typography.labelMedium, fontWeight = FontWeight.Bold,
                color = if (CopyFollow.instant) BuyColor else Muted)
        }
        rows.forEach { t ->
            Column(Modifier.fillMaxWidth().clickable { onOpen(t) }.padding(vertical = 4.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(t.optString("name").ifBlank { t.optString("id").take(12) }, Modifier.weight(1f),
                        fontWeight = FontWeight.Bold, maxLines = 1, overflow = TextOverflow.Ellipsis)
                    Text(t.optString("platform"), style = MaterialTheme.typography.labelSmall, color = Muted)
                }
                val pos = t.optJSONArray("posisi")?.let { a -> (0 until a.length()).mapNotNull { a.optJSONObject(it) } }.orEmpty()
                if (pos.isEmpty()) {
                    Text(t.optString("status").let { if (it == "Dipantau") "Tidak ada posisi terbuka" else it },
                        style = MaterialTheme.typography.labelSmall, color = Muted)
                }
                pos.take(6).forEach { p ->
                    val u = p.numOrNull("untung")
                    val arah = p.optString("arah")
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                        if (arah == "BUY" || arah == "SELL") Pill(arah, if (arah == "BUY") BuyColor else SellColor, solid = true)
                        Text("${p.optString("symbol")} @ ${pxText(p.numOrNull("entry"))}" +
                            (p.numOrNull("tp")?.let { " • TP ${pxText(it)}" } ?: "") +
                            (p.numOrNull("sl")?.let { " • SL ${pxText(it)}" } ?: ""),
                            Modifier.weight(1f), style = MaterialTheme.typography.labelSmall, maxLines = 1,
                            overflow = TextOverflow.Ellipsis)
                        u?.let {
                            Text("${signed(it, 1)}%", style = MaterialTheme.typography.labelSmall, fontWeight = FontWeight.Bold,
                                color = if (it >= 0) BuyColor else SellColor)
                        }
                    }
                }
                if (pos.size > 6) Text("+${pos.size - 6} posisi lain (ketuk)", style = MaterialTheme.typography.labelSmall, color = Muted)
            }
        }
        if (CopyFollow.log.isNotEmpty()) {
            Text("Kejadian terbaru", fontWeight = FontWeight.Bold, style = MaterialTheme.typography.bodySmall)
            CopyFollow.log.take(8).forEach { e ->
                val (a, b) = copyEventText(e)
                Column(Modifier.fillMaxWidth().padding(vertical = 1.dp)) {
                    Text(a, style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.Bold, maxLines = 1,
                        overflow = TextOverflow.Ellipsis)
                    Text("$b • ${localTime(e.optString("time"))}", style = MaterialTheme.typography.labelSmall, color = Muted,
                        maxLines = 2, overflow = TextOverflow.Ellipsis)
                }
            }
        }
    }
}
