package com.xausignal.app

import androidx.compose.foundation.background
import androidx.compose.foundation.border
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
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
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
        d1 == "BUY" && h4 == "BUY" -> "BULLISH" to BuyColor
        d1 == "SELL" && h4 == "SELL" -> "BEARISH" to SellColor
        else -> "CAMPURAN" to Muted
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
    AppCard(accent = if (warna == Muted) null else warna) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            AssetCoin(sym, 36.dp)
            Column(Modifier.weight(1f)) {
                Text(sym, fontWeight = FontWeight.ExtraBold, style = MaterialTheme.typography.titleMedium)
                Text("D1 ${if (d1 == "BUY") "naik" else if (d1 == "SELL") "turun" else "-"} • H4 " +
                    if (h4 == "BUY") "naik" else "turun", style = MaterialTheme.typography.labelSmall, color = Muted)
            }
            Pill(arah, warna, solid = warna != Muted)
        }
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(14.dp)) {
            // ⏱ hitung mundur cek sinyal (tutup candle H1) dalam lingkaran
            val left = instantOf(st.optString("next_check"))?.let { Duration.between(Instant.ofEpochMilli(now), it).toMillis() }
            // lewat > 20 menit tanpa candle baru = pasar tutup (XAU akhir pekan / libur), bukan sedang dicek
            val paused = left != null && left <= -20 * 60_000L
            Ring(if (left != null && left > 0) 1f - left / 3_600_000f else 1f, if (paused) Muted else Gold, size = 74.dp,
                stroke = 6.dp) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Text(when {
                        left == null -> "–"
                        left > 0 -> clockShort(left)
                        paused -> "⏸"
                        else -> "…"
                    }, fontWeight = FontWeight.ExtraBold, style = MaterialTheme.typography.titleSmall, maxLines = 1)
                    Text(if (paused) "tutup" else "cek", style = MaterialTheme.typography.labelSmall, color = Muted)
                }
            }
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Text(when {
                    left == null -> "Menunggu data cloud"
                    left > 0 -> "Cek sinyal ${clock(left)}"
                    !paused -> "Cloud sedang mengecek…"
                    else -> "Pasar tutup — cek lagi saat buka"
                }, style = MaterialTheme.typography.labelMedium, fontWeight = FontWeight.Bold)
                if (buyLvl < Double.MAX_VALUE && sellLvl > -Double.MAX_VALUE) {
                    val toBuy = buyLvl - price
                    val toSell = price - sellLvl
                    LevelChip("BUY >", px(buyLvl, btc), if (btc) "+%,.0f".format(toBuy) else "+$%.2f".format(toBuy), BuyColor)
                    LevelChip("SELL <", px(sellLvl, btc), if (btc) "−%,.0f".format(toSell) else "−$%.2f".format(toSell),
                        SellColor)
                }
                if (running.isNotBlank()) Text("🔁 $running", style = MaterialTheme.typography.labelSmall, color = Gold)
            }
        }
        NewsLine(prep, btc, now)
    }
}

/** "BUY > 3.950,00  +$4,20" dalam kapsul berwarna. */
@Composable
private fun LevelChip(label: String, level: String, dist: String, color: Color) {
    Row(
        Modifier.fillMaxWidth().clip(TileShape).background(color.copy(alpha = 0.12f))
            .border(1.dp, color.copy(alpha = 0.3f), TileShape).padding(horizontal = 10.dp, vertical = 6.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(label, style = MaterialTheme.typography.labelSmall, fontWeight = FontWeight.ExtraBold, color = color)
        Text(level, style = MaterialTheme.typography.labelLarge, fontWeight = FontWeight.ExtraBold,
            modifier = Modifier.padding(start = 6.dp).weight(1f), maxLines = 1)
        Text(dist, style = MaterialTheme.typography.labelSmall, color = Muted, maxLines = 1)
    }
}

/** "42:10" / "1:05:00" untuk isi lingkaran. */
private fun clockShort(ms: Long): String {
    val s = (ms / 1000).coerceAtLeast(0)
    val h = s / 3600
    return if (h > 0) "%d:%02d:%02d".format(h, (s % 3600) / 60, s % 60) else "%02d:%02d".format(s / 60, s % 60)
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
