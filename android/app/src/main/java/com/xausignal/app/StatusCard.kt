package com.xausignal.app

import androidx.compose.foundation.background
import androidx.compose.ui.unit.sp
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.clickable
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.IntrinsicSize
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.height
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
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.time.DayOfWeek
import java.time.Duration
import java.time.Instant
import java.time.LocalTime
import java.time.OffsetDateTime
import java.time.ZoneId
import java.time.ZonedDateTime

/**
 * 📊 Status tren XAU • BTC • ETH dalam SATU baris (aplikasi 4.2, permintaan pengguna 5 Okt 2026: "jadikan 3 satu baris,
 * jangan terlalu banyak makan tempat") + ⏱ hitung mundur yang berguna (menggantikan hitung mundur "cek" candle H1):
 * berita USD penting berikutnya (≤ 24 jam) atau sesi pasar berikutnya (London / New York buka, pasar emas tutup/buka
 * pekan). Setelah rilis: status "lonjakan memudar" (cloud _pudar.py). Hanya keterangan — bukan sinyal entry.
 * Data: heartbeat cloud ("status") + GET /api/chat (persiapan).
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
    val pairs = listOf("XAU" to "XAU/USD", "BTC" to "BTC/USD", "BTC" to "ETH/USD").mapNotNull { (grp, sym) ->
        if (grp !in follow) return@mapNotNull null
        val hb = prices.values.firstOrNull { it.symbol() == sym } ?: return@mapNotNull null
        hb.json.optJSONObject("status")?.let { Triple(sym, hb, it) }
    }
    if (pairs.isEmpty() && "XAU" !in follow && "BTC" !in follow) return
    AppCard {
        if (pairs.isNotEmpty()) {
            Row(Modifier.height(IntrinsicSize.Min), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                pairs.forEach { (sym, hb, st) -> TrendTile(sym, sym != "XAU/USD", hb, st, now) }
                repeat(3 - pairs.size) { Spacer(Modifier.weight(1f)) }
            }
        }
        CountdownRow(prep, now, xau = "XAU" in follow, btc = "BTC" in follow)
    }
}

/**
 * Pasar ringkas (aplikasi 4.5, permintaan pengguna 6 Okt 2026 "1 baris XAU, BTC, ETH, elegan, jangan banyak tulisan"):
 * satu kartu — header LIVE + hitung mundur cek sinyal, satu baris 3 kotak (koin, harga, warna tren D1+H4). Ketuk kotak
 * untuk melihat level BUY/SELL berikutnya. Berita ≤ 24 jam: satu baris. Hanya keterangan, bukan sinyal entry.
 */
@Composable
fun MarketStrip(prices: Map<String, SignalEvent>, connection: String, follow: Set<String>) {
    var now by remember { mutableLongStateOf(System.currentTimeMillis()) }
    var prep by remember { mutableStateOf<JSONObject?>(null) }
    var open by remember { mutableStateOf<String?>(null) }
    LaunchedEffect(Unit) {
        while (true) {
            now = System.currentTimeMillis()
            delay(1_000L)
        }
    }
    LaunchedEffect(Unit) {
        while (true) {
            prep = withContext(Dispatchers.IO) { ChatClient.news().third } ?: prep
            delay(60_000L)
        }
    }
    val online = connection == "Terhubung"
    val assets = listOf("XAU" to "XAU/USD", "BTC" to "BTC/USD", "BTC" to "ETH/USD")
        .filter { (g, _) -> g in follow }
        .mapNotNull { (_, sym) -> prices.values.firstOrNull { it.symbol() == sym }?.let { sym to it } }
    HeroCard {
        Row(verticalAlignment = Alignment.CenterVertically) {
            PulseDot(if (online) BuyColor else SellColor, 7.dp)
            Text(if (online) "LIVE" else connection, style = MaterialTheme.typography.labelMedium,
                fontWeight = FontWeight.ExtraBold, color = if (online) BuyColor else SellColor,
                modifier = Modifier.padding(start = 4.dp).weight(1f))
            val (label, ms) = headerCountdown(prep, now)
            Text("$label ${clockShort(ms)}", style = MaterialTheme.typography.labelMedium, color = Gold,
                fontWeight = FontWeight.Bold, maxLines = 1)
        }
        if (assets.isEmpty()) Text("Menunggu data cloud", style = MaterialTheme.typography.labelMedium, color = Muted)
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            assets.forEach { (sym, hb) ->
                MiniTile(sym, hb, open == sym, Modifier.weight(1f)) { open = if (open == sym) null else sym }
            }
        }
        assets.firstOrNull { it.first == open }?.let { (sym, hb) -> TileDetail(sym, hb) }
        assets.firstOrNull { it.first.startsWith("XAU") }?.second?.warText()?.let {
            Text(it, style = MaterialTheme.typography.labelSmall, color = SellColor, fontWeight = FontWeight.Bold)
        }
    }
}

@Composable
private fun trendOf(hb: SignalEvent): Pair<String, Color> {
    val st = hb.json.optJSONObject("status")
    val d1 = st?.optString("d1") ?: ""
    val h4 = st?.optString("h4") ?: ""
    return when {
        d1 == "BUY" && h4 == "BUY" -> "▲" to BuyColor
        d1 == "SELL" && h4 == "SELL" -> "▼" to SellColor
        else -> "◆" to Muted
    }
}

@Composable
private fun MiniTile(sym: String, hb: SignalEvent, selected: Boolean, modifier: Modifier, onClick: () -> Unit) {
    val (arrow, color) = trendOf(hb)
    val btc = !sym.startsWith("XAU")
    val price = hb.num("price")
    Column(
        modifier.clip(TileShape)
            .background(if (selected) color.copy(alpha = 0.16f) else CardHigh.copy(alpha = 0.85f))
            .border(1.dp, if (selected) color.copy(alpha = 0.6f) else LineColor, TileShape)
            .clickable(onClick = onClick).padding(vertical = 10.dp, horizontal = 6.dp),
        horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(4.dp)
    ) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(4.dp)) {
            AssetCoin(sym, 22.dp)
            Text(arrow, color = color, fontWeight = FontWeight.Black, fontSize = 12.sp)
        }
        Text(if (price == null) "–" else px(price, btc), fontWeight = FontWeight.ExtraBold, maxLines = 1,
            style = MaterialTheme.typography.titleSmall, textAlign = TextAlign.Center)
        Text(sym.substringBefore("/"), style = MaterialTheme.typography.labelSmall, color = Muted)
    }
}

@Composable
private fun TileDetail(sym: String, hb: SignalEvent) {
    val st = hb.json.optJSONObject("status") ?: return
    val btc = !sym.startsWith("XAU")
    val price = hb.num("price") ?: st.optDouble("last_close")
    val levels = st.optJSONArray("levels") ?: return
    var buyLvl = Double.MAX_VALUE
    var sellLvl = -Double.MAX_VALUE
    for (i in 0 until levels.length()) {
        val l = levels.getJSONObject(i)
        buyLvl = minOf(buyLvl, l.optDouble("buy"))
        sellLvl = maxOf(sellLvl, l.optDouble("sell"))
    }
    if (buyLvl == Double.MAX_VALUE || sellLvl == -Double.MAX_VALUE) return
    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        Box(Modifier.weight(1f)) {
            LevelChip("BUY >", px(buyLvl, btc), if (btc) "+%,.0f".format(buyLvl - price) else "+$%.2f".format(buyLvl - price), BuyColor)
        }
        Box(Modifier.weight(1f)) {
            LevelChip("SELL <", px(sellLvl, btc), if (btc) "−%,.0f".format(price - sellLvl) else "−$%.2f".format(price - sellLvl), SellColor)
        }
    }
}

/** Hitung mundur header: berita USD berikutnya ≤ 24 jam, selain itu pembukaan sesi berikutnya (WIB: Asia 07:00,
 *  Eropa 14:00, Amerika 20:00 = 00:00 / 07:00 / 13:00 UTC). */
private fun headerCountdown(prep: JSONObject?, now: Long): Pair<String, Long> {
    val nowI = Instant.ofEpochMilli(now)
    val list = prep?.optJSONArray("berita")
    var best: Pair<String, Instant>? = null
    if (list != null) for (i in 0 until list.length()) {
        val b = list.getJSONObject(i)
        val t = instantOf(b.optString("time")) ?: continue
        if (t.isAfter(nowI) && (best == null || t.isBefore(best.second))) best = b.optString("title") to t
    }
    best?.let { (title, t) ->
        val left = Duration.between(nowI, t).toMillis()
        if (left <= 24 * 3600_000L) return "📰 ${title.take(18)}" to left
    }
    val day = nowI.truncatedTo(java.time.temporal.ChronoUnit.DAYS)
    val sesi = listOf("🌏 Asia" to 0L, "🇪🇺 Eropa" to 7L, "🇺🇸 Amerika" to 13L)
    for (d in 0..1) for ((name, h) in sesi) {
        val t = day.plus(Duration.ofDays(d.toLong())).plus(Duration.ofHours(h))
        if (t.isAfter(nowI)) return name to Duration.between(nowI, t).toMillis()
    }
    return "" to 0L
}

/** Satu baris: berita berikutnya ≤ 24 jam (atau status lonjakan setelah rilis), tanpa teks bila tidak ada. */
@Composable
private fun StripNews(prep: JSONObject?, now: Long) {
    val list = prep?.optJSONArray("berita") ?: return
    val nowI = Instant.ofEpochMilli(now)
    var next: Pair<String, Instant>? = null
    for (i in 0 until list.length()) {
        val b = list.getJSONObject(i)
        val t = instantOf(b.optString("time")) ?: continue
        if (t.isAfter(nowI) && (next == null || t.isBefore(next.second))) next = b.optString("title") to t
    }
    next?.let { (title, t) ->
        val left = Duration.between(nowI, t).toMillis()
        if (left in 1..24 * 3600_000L) Text("📰 $title • ${clockShort(left)}", maxLines = 1,
            style = MaterialTheme.typography.labelMedium, color = Gold, fontWeight = FontWeight.Bold)
    }
}

private fun instantOf(iso: String): Instant? = try {
    OffsetDateTime.parse(iso).toInstant()
} catch (e: Exception) {
    null
}

/** Isi lingkaran: "3:20" + "jam" (≥ 1 jam) atau "42:10" + "menit" (< 1 jam). */
private fun clockShort(ms: Long): Pair<String, String> {
    val s = (ms / 1000).coerceAtLeast(0)
    val h = s / 3600
    return if (h > 0) "%d:%02d".format(h, (s % 3600) / 60) to "jam" else "%02d:%02d".format(s / 60, s % 60) to "menit"
}

/** "2 j 13 m" tanpa detik (baris sesi). */
private fun clockHm(ms: Long): String {
    val m = (ms / 60_000).coerceAtLeast(0)
    return if (m >= 60) "${m / 60} j %02d m".format(m % 60) else "$m m"
}

private fun px(x: Double, btc: Boolean): String =
    if (btc) "%,.0f".format(x).replace(',', '.') else "%,.2f".format(x).replace(',', '#').replace('.', ',').replace('#', '.')

/** Satu pair dalam kotak sepertiga lebar: koin, arah tren D1+H4, level breakout BUY/SELL (tanpa hitung mundur cek). */
@Composable
private fun RowScope.TrendTile(sym: String, btc: Boolean, hb: SignalEvent, st: JSONObject, now: Long) {
    val d1 = st.optString("d1")
    val h4 = st.optString("h4")
    val (arah, warna) = when {
        d1 == "BUY" && h4 == "BUY" -> "▲ NAIK" to BuyColor
        d1 == "SELL" && h4 == "SELL" -> "▼ TURUN" to SellColor
        else -> "◆ CAMPUR" to Muted
    }
    val price = hb.num("price") ?: st.optDouble("last_close")
    val levels = st.optJSONArray("levels")
    var buyLvl = Double.MAX_VALUE
    var sellLvl = -Double.MAX_VALUE
    var running = false
    if (levels != null) for (i in 0 until levels.length()) {
        val l = levels.getJSONObject(i)
        buyLvl = minOf(buyLvl, l.optDouble("buy"))
        sellLvl = maxOf(sellLvl, l.optDouble("sell"))
        if (!l.isNull("open")) running = true
    }
    // lewat > 20 menit tanpa candle baru = pasar tutup (XAU akhir pekan / libur)
    val paused = instantOf(st.optString("next_check"))
        ?.let { Duration.between(Instant.ofEpochMilli(now), it).toMillis() <= -20 * 60_000L } ?: false
    val shape = TileShape
    Column(
        Modifier.weight(1f).fillMaxHeight().clip(shape).background(warna.copy(alpha = 0.10f).let { if (warna == Muted) CardHigh else it })
            .border(1.dp, warna.copy(alpha = 0.35f), shape).padding(horizontal = 8.dp, vertical = 8.dp),
        verticalArrangement = Arrangement.spacedBy(2.dp)
    ) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(5.dp)) {
            AssetCoin(sym, 22.dp)
            Text(sym.substringBefore("/"), fontWeight = FontWeight.ExtraBold, style = MaterialTheme.typography.titleSmall,
                maxLines = 1)
        }
        Text(arah, color = warna, fontWeight = FontWeight.ExtraBold, style = MaterialTheme.typography.labelMedium,
            maxLines = 1)
        if (buyLvl < Double.MAX_VALUE && sellLvl > -Double.MAX_VALUE && !price.isNaN()) {
            LevelLine("▲", px(buyLvl, btc), BuyColor)
            LevelLine("▼", px(sellLvl, btc), SellColor)
        }
        when {
            paused -> Text("⏸ tutup", style = MaterialTheme.typography.labelSmall, color = Muted, maxLines = 1)
            running -> Text("🔁 jalan", style = MaterialTheme.typography.labelSmall, color = Gold, maxLines = 1)
        }
    }
}

/** "▲ 3.950,00" = BUY bila candle H1 tutup di atas level ini; "▼" = SELL di bawah level. */
@Composable
private fun LevelLine(icon: String, level: String, color: Color) {
    Text("$icon $level", color = color, fontWeight = FontWeight.Bold, style = MaterialTheme.typography.labelSmall,
        maxLines = 1, overflow = TextOverflow.Ellipsis)
}

/** Peristiwa berikutnya untuk hitung mundur. [window] = lebar lingkaran penuh. */
private data class Upcoming(val icon: String, val title: String, val at: Instant, val window: Duration)

private val WIB: ZoneId = ZoneId.of("Asia/Jakarta")
private val NY: ZoneId = ZoneId.of("America/New_York")
private val LONDON: ZoneId = ZoneId.of("Europe/London")

private fun wibText(t: Instant): String {
    val z = t.atZone(WIB)
    return "%02d:%02d WIB".format(z.hour, z.minute)
}

/** Kejadian [time] waktu lokal [zone] berikutnya pada hari kerja (Senin–Jumat). */
private fun nextWeekday(now: ZonedDateTime, zone: ZoneId, time: LocalTime): Instant {
    var d = now.withZoneSameInstant(zone).toLocalDate()
    while (true) {
        val t = d.atTime(time).atZone(zone)
        if (t.dayOfWeek != DayOfWeek.SATURDAY && t.dayOfWeek != DayOfWeek.SUNDAY && t.toInstant().isAfter(now.toInstant()))
            return t.toInstant()
        d = d.plusDays(1)
    }
}

/** Hari & jam New York berikutnya ([dow] [time]). */
private fun nextNy(now: ZonedDateTime, dow: DayOfWeek, time: LocalTime): Instant {
    var d = now.withZoneSameInstant(NY).toLocalDate()
    while (true) {
        val t = d.atTime(time).atZone(NY)
        if (t.dayOfWeek == dow && t.toInstant().isAfter(now.toInstant())) return t.toInstant()
        d = d.plusDays(1)
    }
}

/**
 * Sesi pasar berikutnya (jam WIB menyesuaikan musim panas London/New York sendiri):
 * London buka 08:00 London, New York buka 08:00 New York (data AS 08:30), emas tutup pekan Jumat 17:00 New York,
 * emas buka pekan Minggu 18:00 New York. Saat akhir pekan hanya "emas buka".
 */
private fun nextSession(nowMs: Long): Upcoming {
    val now = Instant.ofEpochMilli(nowMs).atZone(NY)
    val open = nextNy(now, DayOfWeek.SUNDAY, LocalTime.of(18, 0))
    val close = nextNy(now, DayOfWeek.FRIDAY, LocalTime.of(17, 0))
    if (open.isBefore(close)) return Upcoming("🔔", "Emas buka", open, Duration.ofHours(49))
    val list = listOf(
        Upcoming("🇬🇧", "London buka", nextWeekday(now, LONDON, LocalTime.of(8, 0)), Duration.ofHours(24)),
        Upcoming("🇺🇸", "New York buka", nextWeekday(now, NY, LocalTime.of(8, 0)), Duration.ofHours(24)),
        Upcoming("🔕", "Emas tutup", close, Duration.ofHours(24)),
    )
    return list.minBy { it.at }
}

/** Berita USD penting berikutnya (≤ 24 jam) dari kartu 🎯 Persiapan berita. */
private fun nextNews(prep: JSONObject?, nowMs: Long): Upcoming? {
    val list = prep?.optJSONArray("berita") ?: return null
    val nowI = Instant.ofEpochMilli(nowMs)
    var best: Upcoming? = null
    for (i in 0 until list.length()) {
        val b = list.getJSONObject(i)
        val t = instantOf(b.optString("time")) ?: continue
        if (t.isAfter(nowI) && Duration.between(nowI, t) <= Duration.ofHours(24) && (best == null || t.isBefore(best.at)))
            best = Upcoming("📰", b.optString("title"), t, Duration.ofHours(24))
    }
    return best
}

/**
 * ⏱ Lingkaran = peristiwa terdekat yang bisa menggerakkan harga (berita penting dulu, lalu sesi pasar);
 * baris kanan = keduanya + status "lonjakan memudar" setelah rilis (≤ 6 jam).
 */
@Composable
private fun CountdownRow(prep: JSONObject?, now: Long, xau: Boolean, btc: Boolean) {
    val news = nextNews(prep, now)
    val session = nextSession(now)
    val main = news ?: session
    val left = Duration.between(Instant.ofEpochMilli(now), main.at).toMillis()
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        Ring(1f - left.toFloat() / main.window.toMillis(), if (main === news) Gold else BuyColor, size = 58.dp,
            stroke = 5.dp) {
            val (num, unit) = clockShort(left)
            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                Text(num, fontWeight = FontWeight.ExtraBold, style = MaterialTheme.typography.labelLarge, maxLines = 1)
                Text(unit, style = MaterialTheme.typography.labelSmall, color = Muted, maxLines = 1)
            }
        }
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(3.dp)) {
            if (news != null) {
                Text("📰 ${news.title}", fontWeight = FontWeight.Bold, style = MaterialTheme.typography.labelMedium,
                    color = Gold, maxLines = 1, overflow = TextOverflow.Ellipsis)
                Text(wibText(news.at), style = MaterialTheme.typography.labelSmall, color = Muted, maxLines = 1)
            }
            Text("${session.icon} ${session.title} ${wibText(session.at)}" +
                (if (main === session) "" else " • " +
                    clockHm(Duration.between(Instant.ofEpochMilli(now), session.at).toMillis())),
                style = MaterialTheme.typography.labelSmall,
                fontWeight = if (main === session) FontWeight.Bold else FontWeight.Normal,
                color = if (main === session) MaterialTheme.colorScheme.onSurface else Muted,
                maxLines = 1, overflow = TextOverflow.Ellipsis)
            AfterNews(prep, now, xau, btc)
        }
    }
}

/** Status lonjakan setelah rilis (≤ 6 jam) untuk XAU dan/atau BTC (cloud _pudar.py). */
@Composable
private fun AfterNews(prep: JSONObject?, now: Long, xau: Boolean, btc: Boolean) {
    val list = prep?.optJSONArray("berita") ?: return
    val nowI = Instant.ofEpochMilli(now)
    for ((key, on) in listOf("pudar" to xau, "pudar_btc" to btc)) {
        if (!on) continue
        var after: JSONObject? = null
        for (i in 0 until list.length()) {
            val b = list.getJSONObject(i)
            val t = instantOf(b.optString("time")) ?: continue
            val p = b.optJSONObject(key)
            if (p != null && !t.isAfter(nowI) && Duration.between(t, nowI).toHours() < 6) after = p
        }
        after?.let { p ->
            val teks = p.optString("teks")
            Text("${if (key == "pudar") "XAU" else "BTC"}: $teks", fontWeight = FontWeight.Bold,
                style = MaterialTheme.typography.labelSmall, overflow = TextOverflow.Ellipsis,
                color = if (teks.contains("🔴")) SellColor else if (teks.contains("🟢")) BuyColor else Gold, maxLines = 1)
        }
    }
}
