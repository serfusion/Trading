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
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.TimeUnit
import kotlin.math.abs

/** Satu posisi terbuka copy trader (aplikasi 4.12). Angka yang tidak dibuka situsnya = null → ditampilkan "-". */
data class CopyPos(
    val symbol: String, val buy: Boolean?, val entry: Double?, val now: Double?, val tp: Double?, val sl: Double?,
    val lev: String, val pnlPct: Double?,
)

/**
 * 👥 Posisi terbuka copy trader, dibaca LANGSUNG dari HP ke situsnya (tanpa cloud; endpoint publik tanpa kunci):
 * eToro (entry/TP/SL lengkap), Hyperliquid (entry + TP/SL dari order pemicu), OKX/Binance/Bitget (entry & leverage bila
 * trader tidak menyembunyikan posisi; TP/SL tidak dibuka situsnya), MQL5 (posisi hanya untuk pelanggan).
 */
object CopyDetail {
    private val client = OkHttpClient.Builder().connectTimeout(15, TimeUnit.SECONDS).readTimeout(20, TimeUnit.SECONDS).build()
    private const val UA = "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Mobile Safari/537.36"
    private val JSON = "application/json".toMediaType()

    private fun get(url: String): String = client.newCall(
        Request.Builder().url(url).header("User-Agent", UA).header("Accept", "application/json").build()
    ).execute().use { it.body?.string().orEmpty() }

    private fun post(url: String, body: String): String = client.newCall(
        Request.Builder().url(url).header("User-Agent", UA).post(body.toRequestBody(JSON)).build()
    ).execute().use { it.body?.string().orEmpty() }

    private fun d(o: JSONObject, k: String): Double? = o.optString(k).toDoubleOrNull()?.takeIf { it != 0.0 }

    /** (posisi, catatan). Catatan kosong = normal. */
    suspend fun fetch(x: JSONObject): Pair<List<CopyPos>, String> = withContext(Dispatchers.IO) {
        val id = x.optString("id")
        try {
            when (x.optString("platform")) {
                "eToro" -> etoro(id)
                "Hyperliquid" -> hyperliquid(id)
                "OKX" -> okx(id)
                "Bitget" -> bitget(id)
                "Binance" -> binance(id)
                else -> emptyList<CopyPos>() to "MQL5 hanya membuka posisi untuk pelanggan sinyal."
            }
        } catch (e: Exception) {
            emptyList<CopyPos>() to "Gagal memuat: ${(e.message ?: e.javaClass.simpleName).take(60)}"
        }
    }

    private fun etoro(cid: String): Pair<List<CopyPos>, String> {
        val pf = JSONObject(get("https://www.etoro.com/sapi/trade-data-real/live/public/portfolios?cid=$cid&format=json"))
        val agg = pf.optJSONArray("AggregatedPositions") ?: JSONArray()
        val rows = (0 until agg.length()).map { agg.getJSONObject(it) }.sortedByDescending { it.optDouble("Invested") }.take(6)
        if (rows.isEmpty()) return emptyList<CopyPos>() to "Tidak ada posisi terbuka."
        val ids = rows.joinToString(",") { it.optInt("InstrumentID").toString() }
        val names = HashMap<Int, String>()
        runCatching {
            val m = JSONObject(get("https://api.etorostatic.com/sapi/instrumentsmetadata/V1.1/instruments?InstrumentIds=$ids"))
                .optJSONArray("InstrumentDisplayDatas") ?: JSONArray()
            for (i in 0 until m.length()) m.getJSONObject(i).let { names[it.optInt("InstrumentID")] = it.optString("SymbolFull") }
        }
        val out = rows.map { a ->
            val iid = a.optInt("InstrumentID")
            val buy = a.optString("Direction") != "Sell"
            var entry: Double? = null
            var now: Double? = null
            var tp: Double? = null
            var sl: Double? = null
            var lev = "1x"
            runCatching {
                val p = JSONObject(get("https://www.etoro.com/sapi/trade-data-real/live/public/positions?cid=$cid&InstrumentID=$iid&format=json"))
                entry = d(p, "AverageOpen")
                val ps = p.optJSONArray("PublicPositions") ?: JSONArray()
                val last = (0 until ps.length()).map { ps.getJSONObject(it) }.maxByOrNull { it.optString("OpenDateTime") }
                if (last != null) {
                    now = d(last, "CurrentRate")
                    lev = "${last.optInt("Leverage", 1)}x"
                    val e = entry ?: d(last, "OpenRate") ?: 0.0
                    // eToro mengisi TP/SL "kosong" dengan nilai ekstrem (TP ±10× harga, SL 0,0001) → dianggap tidak ada
                    tp = d(last, "TakeProfitRate")?.takeIf { e > 0 && it / e in 0.2..3.0 }
                    sl = d(last, "StopLossRate")?.takeIf { e > 0 && it / e in 0.2..3.0 }
                }
            }
            CopyPos(names[iid] ?: "ID $iid", buy, entry, now, tp, sl, lev, a.optDouble("NetProfit"))
        }
        return out to "Persen untung = rata-rata posisi trader pada aset itu."
    }

    private fun hyperliquid(addr: String): Pair<List<CopyPos>, String> {
        val url = "https://api.hyperliquid.xyz/info"
        val st = JSONObject(post(url, """{"type":"clearinghouseState","user":"$addr"}"""))
        val orders = runCatching { JSONArray(post(url, """{"type":"frontendOpenOrders","user":"$addr"}""")) }.getOrNull() ?: JSONArray()
        val tp = HashMap<String, Double>()
        val sl = HashMap<String, Double>()
        for (i in 0 until orders.length()) {
            val o = orders.getJSONObject(i)
            val t = o.optString("orderType")
            val px = d(o, "triggerPx") ?: continue
            when {
                t.contains("Take Profit") -> tp[o.optString("coin")] = px
                t.contains("Stop") -> sl[o.optString("coin")] = px
            }
        }
        val ap = st.optJSONArray("assetPositions") ?: JSONArray()
        val out = (0 until ap.length()).map { ap.getJSONObject(it).getJSONObject("position") }
            .sortedByDescending { abs(it.optString("positionValue").toDoubleOrNull() ?: 0.0) }.take(10).map { p ->
                val coin = p.optString("coin")
                val szi = p.optString("szi").toDoubleOrNull() ?: 0.0
                val value = p.optString("positionValue").toDoubleOrNull()
                CopyPos(coin, szi > 0, d(p, "entryPx"), value?.let { if (szi != 0.0) abs(it / szi) else null },
                    tp[coin], sl[coin], "${p.optJSONObject("leverage")?.optInt("value") ?: 1}x",
                    p.optString("returnOnEquity").toDoubleOrNull()?.times(100))
            }
        return out to if (out.isEmpty()) "Tidak ada posisi terbuka." else ""
    }

    private fun okx(code: String): Pair<List<CopyPos>, String> {
        val j = JSONObject(get("https://www.okx.com/api/v5/copytrading/public-current-subpositions?instType=SWAP&uniqueCode=$code&limit=20"))
        val a = j.optJSONArray("data") ?: JSONArray()
        val rows = (0 until a.length()).map { a.getJSONObject(it) }
        val out = rows.take(10).map { p ->
            CopyPos(p.optString("instId").removeSuffix("-SWAP").ifBlank { "(disembunyikan)" },
                when (p.optString("posSide")) { "long" -> true; "short" -> false; else -> null },
                d(p, "openAvgPx"), d(p, "markPx"), null, null, "${p.optString("lever")}x",
                p.optString("uplRatio").toDoubleOrNull()?.times(100))
        }
        val hidden = rows.any { it.optString("instId").isBlank() }
        return out to when {
            out.isEmpty() -> "Tidak ada posisi terbuka."
            hidden -> "Trader menyembunyikan koin & harga; arah, leverage & untung tetap terlihat. TP/SL tidak dibuka OKX."
            else -> "TP/SL tidak dibuka OKX."
        }
    }

    private fun bitget(uid: String): Pair<List<CopyPos>, String> {
        val j = JSONObject(post("https://www.bitget.com/v1/trigger/trace/public/traderPosition",
            """{"languageType":0,"traderUid":"$uid"}"""))
        val a = j.optJSONArray("data") ?: JSONArray()
        val out = (0 until a.length()).map { a.getJSONObject(it) }.take(10).map { p ->
            CopyPos(p.optString("symbolDisplayName"), when (p.optInt("holdSide")) { 1 -> true; 2 -> false; else -> null },
                d(p, "openAvgPrice") ?: d(p, "avgPrice"), null, null, null, "${p.optInt("openLevel")}x", null)
        }
        return out to if (out.isEmpty()) "Tidak ada posisi terbuka (atau trader mengaktifkan perlindungan posisi)."
        else "Bitget hanya membuka entry & leverage."
    }

    private fun binance(id: String): Pair<List<CopyPos>, String> {
        val j = JSONObject(get("https://www.binance.com/bapi/futures/v1/friendly/future/copy-trade/lead-data/positions?portfolioId=$id"))
        val a = j.optJSONArray("data") ?: JSONArray()
        val out = (0 until a.length()).map { a.getJSONObject(it) }
            .filter { (it.optString("positionAmount").toDoubleOrNull() ?: 0.0) != 0.0 }.take(10).map { p ->
                val amt = p.optString("positionAmount").toDouble()
                val entry = d(p, "entryPrice")
                val lev = p.optInt("leverage", 1)
                val pnl = p.optString("unrealizedProfit").toDoubleOrNull()
                val margin = entry?.let { abs(amt) * it / lev }
                CopyPos(p.optString("symbol"), amt > 0, entry, d(p, "markPrice"), null, null, "${lev}x",
                    if (pnl != null && margin != null && margin > 0) pnl / margin * 100 else null)
            }
        return out to if (out.isEmpty()) "Tidak ada posisi terbuka atau trader menyembunyikan posisi." else "TP/SL tidak dibuka Binance."
    }
}

private fun px(v: Double?): String = when {
    v == null -> "-"
    abs(v) >= 1000 -> fmt(v, 1)
    abs(v) >= 1 -> fmt(v, 3)
    else -> fmt(v, 6)
}

/** Jendela detail copy trader: angka utama + posisi terbuka (entry, harga sekarang, TP, SL, leverage, untung). */
@Composable
fun CopyDetailDialog(x: JSONObject, onDismiss: () -> Unit) {
    val uri = LocalUriHandler.current
    var data by remember(x) { mutableStateOf<Pair<List<CopyPos>, String>?>(null) }
    LaunchedEffect(x) { data = CopyDetail.fetch(x) }
    val platform = x.optString("platform")
    AlertDialog(
        onDismissRequest = onDismiss,
        title = {
            Column {
                Text(x.optString("name"), fontWeight = FontWeight.ExtraBold, maxLines = 1)
                Text("$platform • ${x.optInt("pengikut")} pengikut", style = MaterialTheme.typography.labelSmall, color = Muted)
            }
        },
        text = {
            Column(Modifier.heightIn(max = 460.dp).verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(8.dp)) {
                TileGrid(listOf(
                    TileData("Profit ${x.optString("periode", "1 th")}", "${signed(x.optDouble("roi"), 0)}%", BuyColor, null),
                    TileData("DD maks", "${x.optDouble("mdd").toInt()}%", SellColor, null),
                    TileData("WR", "${x.optDouble("wr").toInt()}%", Gold, if (x.optBoolean("wr_curiga")) "⚠️ hampir 100%" else null),
                    TileData("2 paruh", x.optJSONArray("paruh")?.let { "${signed(it.optDouble(0), 0)} / ${signed(it.optDouble(1), 0)}%" } ?: "-",
                        Muted, null),
                ))
                Text("Posisi terbuka", fontWeight = FontWeight.Bold, style = MaterialTheme.typography.bodyMedium)
                val r = data
                if (r == null) {
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        CircularProgressIndicator(Modifier.padding(4.dp), strokeWidth = 2.dp)
                        Text("Memuat dari $platform…", style = MaterialTheme.typography.labelSmall, color = Muted)
                    }
                } else {
                    r.first.forEach { PosRow(it) }
                    if (r.second.isNotBlank()) Text(r.second, style = MaterialTheme.typography.labelSmall, color = Muted)
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
private fun PosRow(p: CopyPos) {
    AppCard(accent = when (p.buy) { true -> BuyColor; false -> SellColor; null -> null }) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(p.symbol, Modifier.weight(1f), fontWeight = FontWeight.ExtraBold, maxLines = 1)
            if (p.buy != null) Pill(if (p.buy) "BUY" else "SELL", if (p.buy) BuyColor else SellColor, solid = true)
            Pill(p.lev, Muted)
        }
        Row(Modifier.fillMaxWidth()) {
            KV("Entry", px(p.entry), Modifier.weight(1f))
            KV("Sekarang", px(p.now), Modifier.weight(1f))
            KV("Untung", p.pnlPct?.let { "${signed(it, 1)}%" } ?: "-", Modifier.weight(1f),
                if ((p.pnlPct ?: 0.0) >= 0) BuyColor else SellColor)
        }
        Row(Modifier.fillMaxWidth()) {
            KV("TP", px(p.tp), Modifier.weight(1f), BuyColor)
            KV("SL", px(p.sl), Modifier.weight(1f), SellColor)
            KV("", "", Modifier.weight(1f))
        }
    }
}

@Composable
private fun KV(label: String, value: String, modifier: Modifier, color: androidx.compose.ui.graphics.Color = androidx.compose.ui.graphics.Color.Unspecified) {
    Column(modifier) {
        if (label.isNotEmpty()) Text(label, style = MaterialTheme.typography.labelSmall, color = Muted)
        Text(value, style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.Bold, color = color)
    }
}
