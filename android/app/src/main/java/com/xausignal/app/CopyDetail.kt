package com.xausignal.app

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONArray
import org.json.JSONObject
import java.net.URLEncoder
import java.util.concurrent.TimeUnit
import kotlin.math.abs

/**
 * 👥 Detail copy trader (aplikasi 4.13). Semua dirangkum CLOUD (`cloud/api/_copyposisi.py`, GET /api/chat?copyposisi=
 * <situs>|<id>) — HP hanya menampilkan: posisi terbuka (entry, harga sekarang, TP, SL, leverage, untung) dan 10 trade
 * terakhir (entry → tutup, gerak harga, TP/SL bila dibuka situsnya) + satu kalimat ringkasan. Info saja, tanpa order.
 */
object CopyDetail {
    private val client = OkHttpClient.Builder().connectTimeout(15, TimeUnit.SECONDS).readTimeout(55, TimeUnit.SECONDS).build()

    suspend fun fetch(x: JSONObject): JSONObject = withContext(Dispatchers.IO) {
        val base = SignalRepository.cloudUrl()
        if (base.isBlank()) return@withContext JSONObject().put("catatan", "Alamat cloud belum diisi.")
        val key = URLEncoder.encode("${x.optString("platform")}|${x.optString("id")}", "UTF-8")
        try {
            client.newCall(Request.Builder().url("$base/api/chat?copyposisi=$key").get()
                .header("X-Chat-Key", SignalRepository.topic()).build()).execute().use { res ->
                val j = JSONObject(res.body?.string().orEmpty())
                if (!j.has("posisi") && !j.has("catatan")) j.put("catatan", "Cloud belum versi terbaru (HTTP ${res.code}).")
                j
            }
        } catch (e: Exception) {
            JSONObject().put("catatan", "Gagal memuat: ${(e.message ?: e.javaClass.simpleName).take(60)}")
        }
    }
}

private fun num(o: JSONObject, k: String): Double? = if (o.isNull(k)) null else o.optDouble(k).takeIf { !it.isNaN() }

private fun px(v: Double?): String = when {
    v == null -> "-"
    abs(v) >= 1000 -> fmt(v, 1)
    abs(v) >= 1 -> fmt(v, 3)
    else -> fmt(v, 6)
}

private fun arr(j: JSONObject?, k: String): List<JSONObject> {
    val a = j?.optJSONArray(k) ?: JSONArray()
    return (0 until a.length()).mapNotNull { a.optJSONObject(it) }
}

/** Jendela detail copy trader: angka utama, ringkasan, posisi terbuka, trade terakhir. */
@Composable
fun CopyDetailDialog(x: JSONObject, onDismiss: () -> Unit) {
    val uri = LocalUriHandler.current
    var data by remember(x) { mutableStateOf<JSONObject?>(null) }
    LaunchedEffect(x) { data = CopyDetail.fetch(x) }
    val platform = x.optString("platform").let { if (it.startsWith("MQL5")) "MQL5" else it }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = {
            Column {
                Text(x.optString("name"), fontWeight = FontWeight.ExtraBold, maxLines = 1)
                Text("$platform • ${x.optInt("pengikut")} pengikut", style = MaterialTheme.typography.labelSmall, color = Muted)
            }
        },
        text = {
            Column(Modifier.heightIn(max = 520.dp).verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(8.dp)) {
                val paruh = x.optJSONArray("paruh")
                TileGrid(listOf(
                    TileData("Profit ${x.optString("periode", "1 th")}", "${signed(x.optDouble("roi"), 0)}%", BuyColor),
                    TileData("DD maks", "${x.optDouble("mdd").toInt()}%", SellColor),
                    TileData("WR", "${x.optDouble("wr").toInt()}%", Gold, if (x.optBoolean("wr_curiga")) "⚠️ hampir 100%" else null),
                    TileData("Paruh 1 / 2", paruh?.let { "${signed(it.optDouble(0), 0)}/${signed(it.optDouble(1), 0)}%" } ?: "-", Muted),
                ))
                val r = data
                if (r == null) {
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        CircularProgressIndicator(Modifier.padding(4.dp), strokeWidth = 2.dp)
                        Text("Cloud merangkum data $platform…", style = MaterialTheme.typography.labelSmall, color = Muted)
                    }
                } else {
                    r.optString("ringkas").takeIf { it.isNotBlank() }?.let {
                        Text(it, style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.Bold)
                    }
                    val pos = arr(r, "posisi")
                    Text("Posisi terbuka (${pos.size})", fontWeight = FontWeight.Bold, style = MaterialTheme.typography.bodyMedium)
                    pos.forEach { PosRow(it) }
                    val hist = arr(r, "riwayat")
                    if (hist.isNotEmpty()) {
                        Text("Trade terakhir", fontWeight = FontWeight.Bold, style = MaterialTheme.typography.bodyMedium)
                        hist.forEach { TradeRow(it) }
                    }
                    r.optString("catatan").takeIf { it.isNotBlank() }?.let {
                        Text(it, style = MaterialTheme.typography.labelSmall, color = Muted)
                    }
                }
            }
        },
        confirmButton = {
            TextButton(onClick = { x.optString("url").takeIf { it.startsWith("https://") }?.let { runCatching { uri.openUri(it) } } }) {
                Text("Salin di $platform")
            }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Tutup") } },
    )
}

@Composable
private fun SidePills(p: JSONObject) {
    val arah = p.optString("arah")
    if (arah == "BUY" || arah == "SELL") Pill(arah, if (arah == "BUY") BuyColor else SellColor, solid = true)
    if (!p.isNull("lev")) Pill("${p.optInt("lev")}x", Muted)
}

@Composable
private fun PosRow(p: JSONObject) {
    val arah = p.optString("arah")
    AppCard(accent = when (arah) { "BUY" -> BuyColor; "SELL" -> SellColor; else -> null }) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(p.optString("symbol"), Modifier.weight(1f), fontWeight = FontWeight.ExtraBold, maxLines = 1)
            SidePills(p)
        }
        val u = num(p, "untung")
        Row(Modifier.fillMaxWidth()) {
            KV("Entry", px(num(p, "entry")), Modifier.weight(1f))
            KV("Sekarang", px(num(p, "now")), Modifier.weight(1f))
            KV("Untung", u?.let { "${signed(it, 1)}%" } ?: "-", Modifier.weight(1f), if ((u ?: 0.0) >= 0) BuyColor else SellColor)
        }
        Row(Modifier.fillMaxWidth()) {
            KV("TP", px(num(p, "tp")), Modifier.weight(1f), BuyColor)
            KV("SL", px(num(p, "sl")), Modifier.weight(1f), SellColor)
            KV("", "", Modifier.weight(1f))
        }
    }
}

@Composable
private fun TradeRow(t: JSONObject) {
    val g = num(t, "gerak")
    Column(Modifier.fillMaxWidth().padding(vertical = 2.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            Text(t.optString("symbol"), Modifier.weight(1f), fontWeight = FontWeight.Bold,
                style = MaterialTheme.typography.bodySmall, maxLines = 1)
            SidePills(t)
            Text(g?.let { "${signed(it, 2)}%" } ?: "-", fontWeight = FontWeight.ExtraBold,
                color = if ((g ?: 0.0) >= 0) BuyColor else SellColor, style = MaterialTheme.typography.bodySmall)
        }
        val extra = buildList {
            num(t, "tp")?.let { add("TP ${px(it)}") }
            num(t, "sl")?.let { add("SL ${px(it)}") }
            t.optString("waktu").takeIf { it.length >= 10 && it != "null" }?.let { add(it.take(10)) }
        }.joinToString(" • ")
        Text("Entry ${px(num(t, "entry"))} → tutup ${px(num(t, "tutup"))}" + if (extra.isNotEmpty()) " • $extra" else "",
            style = MaterialTheme.typography.labelSmall, color = Muted)
    }
}

@Composable
private fun KV(label: String, value: String, modifier: Modifier, color: Color = Color.Unspecified) {
    Column(modifier) {
        if (label.isNotEmpty()) Text(label, style = MaterialTheme.typography.labelSmall, color = Muted)
        Text(value, style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.Bold, color = color)
    }
}
