package com.xausignal.app

import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.time.Duration
import java.time.Instant
import java.time.OffsetDateTime

/**
 * 📊 Status tren & hitung mundur per pair (tab Sinyal, aplikasi 3.24; permintaan pengguna 3 Okt 2026).
 * Menyesuaikan sendiri: tanpa berita → arah tren D1/H4 + hitung mundur cek sinyal (tutup candle H1) + level breakout;
 * menjelang berita → hitung mundur rilis; setelah rilis → hitung mundur/hasil "lonjakan memudar" (cloud _pudar.py).
 * Hanya keterangan — bukan sinyal entry. Data: heartbeat cloud ("status") + GET /api/chat (persiapan).
 */
@Composable
fun StatusCards(prices: Map<String, SignalEvent>, follow: Set<String>) {
    var now by remember { mutableLongStateOf(System.currentTimeMillis()) }
    var prep by remember { mutableStateOf<JSONObject?>(null) }
    LaunchedEffect(Unit) {                     // detik berjalan untuk hitung mundur
        while (true) {
            now = System.currentTimeMillis()
            delay(1_000L)
        }
    }
    LaunchedEffect(Unit) {                     // berita & lonjakan: muat ulang tiap 60 detik (cache di cloud)
        while (true) {
            prep = withContext(Dispatchers.IO) { ChatClient.news().third } ?: prep
            delay(60_000L)
        }
    }
    for ((grp, sym) in listOf("XAU" to "XAU/USD", "BTC" to "BTC/USD", "BTC" to "ETH/USD")) {
        if (grp !in follow) continue
        val hb = prices.values.firstOrNull { it.symbol() == sym } ?: continue
        val st = hb.json.optJSONObject("status") ?: continue
        StatusCard(sym, grp == "BTC", hb, st, prep, now)
    }
}

private fun instantOf(iso: String): Instant? = try {
    OffsetDateTime.parse(iso).toInstant()
} catch (e: Exception) {
    null
}

private fun clock(ms: Long): String {
    val s = (ms / 1000).coerceAtLeast(0)
    val h = s / 3600
    val m = (s % 3600) / 60
    val sec = s % 60
    return if (h > 0) "%d j %02d m %02d d".format(h, m, sec) else "%02d:%02d".format(m, sec)
}

private fun px(x: Double, btc: Boolean): String =
    if (btc) "%,.0f".format(x).replace(',', '.') else "%,.2f".format(x).replace(',', '#').replace('.', ',').replace('#', '.')

@Composable
private fun StatusCard(sym: String, btc: Boolean, hb: SignalEvent, st: JSONObject, prep: JSONObject?, now: Long) {
    val d1 = st.optString("d1")
    val h4 = st.optString("h4")
    val (arah, warna) = when {
        d1 == "BUY" && h4 == "BUY" -> "🐂 BULLISH" to BuyColor
        d1 == "SELL" && h4 == "SELL" -> "🐻 BEARISH" to SellColor
        else -> "⚖️ CAMPURAN" to Muted
    }
    val price = hb.num("price") ?: st.optDouble("last_close")
    val levels = st.optJSONArray("levels")
    var buyLvl = Double.MAX_VALUE
    var sellLvl = -Double.MAX_VALUE
    var running = ""
    if (levels != null) for (i in 0 until levels.length()) {
        val l = levels.getJSONObject(i)
        buyLvl = minOf(buyLvl, l.optDouble("buy"))
        sellLvl = maxOf(sellLvl, l.optDouble("sell"))
        if (!l.isNull("open")) running = "${l.optString("open")} berjalan"
    }
    AppCard {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text("📊 $sym", fontWeight = FontWeight.Bold, style = MaterialTheme.typography.titleSmall)
            Spacer(Modifier.weight(1f))
            Text(arah, fontWeight = FontWeight.ExtraBold, color = warna, style = MaterialTheme.typography.titleLarge)
        }
        Text("D1 ${if (d1 == "BUY") "naik" else if (d1 == "SELL") "turun" else "-"} • H4 " +
            if (h4 == "BUY") "naik" else "turun", style = MaterialTheme.typography.labelSmall, color = Muted)
        // ⏱ hitung mundur cek sinyal (tutup candle H1)
        instantOf(st.optString("next_check"))?.let { t ->
            val left = Duration.between(Instant.ofEpochMilli(now), t).toMillis()
            Text(if (left > 0) "⏱ Cek sinyal: ${clock(left)}" else "⏱ Cloud sedang mengecek…",
                style = MaterialTheme.typography.bodySmall, modifier = Modifier.padding(top = 4.dp))
        }
        if (buyLvl < Double.MAX_VALUE && sellLvl > -Double.MAX_VALUE) {
            val toBuy = buyLvl - price
            val toSell = price - sellLvl
            Text("BUY > ${px(buyLvl, btc)} (${if (btc) "+%,.0f".format(toBuy) else "+$%.2f".format(toBuy)})" +
                " • SELL < ${px(sellLvl, btc)} (${if (btc) "−%,.0f".format(toSell) else "−$%.2f".format(toSell)})" +
                if (running.isNotBlank()) " • $running" else "",
                style = MaterialTheme.typography.labelSmall, color = Muted)
        }
        NewsLine(prep, btc, now)
    }
}

/** Baris berita: hitung mundur ke rilis berikutnya (≤ 24 jam) atau status lonjakan setelah rilis (≤ 6 jam). */
@Composable
private fun NewsLine(prep: JSONObject?, btc: Boolean, now: Long) {
    val list = prep?.optJSONArray("berita") ?: return
    val nowI = Instant.ofEpochMilli(now)
    var after: JSONObject? = null
    var next: Pair<String, Instant>? = null
    for (i in 0 until list.length()) {
        val b = list.getJSONObject(i)
        val t = instantOf(b.optString("time")) ?: continue
        val p = b.optJSONObject(if (btc) "pudar_btc" else "pudar")
        if (p != null && Duration.between(t, nowI).toHours() < 6) after = p
        if (t.isAfter(nowI) && (next == null || t.isBefore(next.second))) next = b.optString("title") to t
    }
    after?.let { p ->
        val teks = p.optString("teks")
        Text("${p.optString("label")}: $teks", fontWeight = FontWeight.Bold, style = MaterialTheme.typography.bodySmall,
            color = if (teks.contains("🔴")) SellColor else if (teks.contains("🟢")) BuyColor else Gold,
            modifier = Modifier.padding(top = 4.dp))
    }
    next?.let { (title, t) ->
        val left = Duration.between(nowI, t).toMillis()
        if (left in 1..24 * 3600_000L) Text("📰 $title dalam ${clock(left)}",
            style = MaterialTheme.typography.bodySmall, color = Gold, modifier = Modifier.padding(top = 4.dp))
    }
    if (after == null && next == null) Text("📰 Tidak ada berita penting pekan ini",
        style = MaterialTheme.typography.labelSmall, color = Muted, modifier = Modifier.padding(top = 4.dp))
}
