package com.xausignal.app

import androidx.compose.ui.text.style.TextOverflow

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
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.time.Duration
import java.time.Instant
import java.time.OffsetDateTime
import java.util.Locale

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
    // ⚡ 4.40 (14 Okt: tile XAU 4.166 padahal MT5 4.108): harga XAU ikut harga LIVE emas token tiap 5 dtk saat layar terbuka
    var xauLive by remember { mutableStateOf<Pair<Double, Long>?>(null) }
    LaunchedEffect(Unit) {
        while (true) {
            withContext(Dispatchers.IO) { LiveGold.harga() }?.let { xauLive = it.first to System.currentTimeMillis() }
            delay(5_000L)
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
                maxLines = 1, softWrap = false, modifier = Modifier.padding(start = 4.dp, end = 8.dp))
            val (label, ms) = headerCountdown(prep, now)
            Text("$label ${clockShort(ms)}", style = MaterialTheme.typography.labelMedium, color = Gold,
                fontWeight = FontWeight.Bold, maxLines = 1, overflow = TextOverflow.Ellipsis,
                textAlign = TextAlign.End, modifier = Modifier.weight(1f))
        }
        if (assets.isEmpty()) Text("Menunggu data cloud", style = MaterialTheme.typography.labelMedium, color = Muted)
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            assets.forEach { (sym, hb) ->
                val lv = xauLive?.takeIf { sym.startsWith("XAU") && now - it.second < 30_000L }?.first
                MiniTile(sym, hb, open == sym, Modifier.weight(1f), lv) { open = if (open == sym) null else sym }
            }
        }
        StripPra(prep)                           // ⏱️ XAU: arah 1–10 dtk setelah berita berikutnya (4.27)
        StripLangsung(prep, now)                 // ⏱️ 4.36: per detik T−15 mnt s/d +10 mnt, persen tiap detik, 💥 lentur
        StripAllin(prep, prices.values.firstOrNull { it.symbol() == "XAU/USD" }?.num("price"))   // 💥 4.35 (CPI)
        assets.firstOrNull { it.first == open }?.let { (sym, hb) -> TileDetail(sym, hb) }
        StripPudar(prep, now)                    // 📉/📈 lonjakan memudar ≤ 6 jam setelah rilis (hilang sejak 4.5)
        // 4.31: baris 🎯 "peluang emas naik 1 jam" DIHAPUS dari sini — bertentangan dengan arah 1–10 dtk; satu arah saja
        assets.firstOrNull { it.first.startsWith("XAU") }?.second?.warText()?.let {
            Text(it, style = MaterialTheme.typography.labelSmall, color = SellColor, fontWeight = FontWeight.Bold)
        }
        // ⏸️ jeda pra-berita: baris disembunyikan sejak 4.34 (permintaan pengguna 13 Okt: diganti persen berita per detik);
        // aturan jeda di cloud tetap berjalan (teruji menaikkan WR XAU)
    }
}

/**
 * ⏱️ Baris langsung di bawah kotak XAU (4.34/4.36, pengguna 13 Okt 2026: "persentase news berubah setiap detik sebelum &
 * sesudah rilis hingga menit XX"). Angka dari cloud (pra_satu.per_detik = uji tutup kertas, menit_pct = arah detik 2
 * bertahan s/d 5 mnt). Tidak mengarang: tanpa arah → "≈ 50:50". Rilis yang baru lewat diingat 10 menit.
 */
@Composable
private fun StripLangsung(prep: JSONObject?, now: Long) {
    var simpan by remember { mutableStateOf<JSONObject?>(null) }
    val baru = prep?.optJSONObject("pra_satu")
    val tBaru = baru?.let { instantOf(it.optString("time"))?.toEpochMilli() }
    val tLama = simpan?.let { instantOf(it.optString("time"))?.toEpochMilli() }
    // rilis yang baru lewat (≤ 10 mnt) tetap dipakai walau cloud sudah pindah ke berita berikutnya
    val r = if (tLama != null && now - tLama in 0..600_000L && tBaru != tLama) simpan else baru
    LaunchedEffect(tBaru) { if (baru != null && (tLama == null || now - tLama !in 0..600_000L)) simpan = baru }
    val t0 = r?.let { instantOf(it.optString("time"))?.toEpochMilli() } ?: return
    val det = (now - t0) / 1000.0
    // 4.36 (pengguna 13 Okt: "per detik dan berubah persentase, saya buka sebelum hingga sesudah news"): tampil sejak T−15 mnt
    // (awal HMR Exness) s/d +10 mnt; persen = kurva uji SETIAP detik 1–10 lalu 15 dtk…5 mnt (cloud per_detik)
    if (det < -900 || det > 600) return
    // ⚡ 4.39 (pengguna 14 Okt "apk gagal predict di detik awal"): harga emas LIVE tiap ±0,5 dtk dari T−15 dtk s/d +2 mnt
    // (LiveGold: XAUT OKX/KuCoin/Bitget/Gate). Setelah rilis baris ini memakai gerak harga SUNGGUHAN, bukan tebakan.
    var live by remember(t0) { mutableStateOf<List<Pair<Long, Double>>>(emptyList()) }
    var liveSrc by remember(t0) { mutableStateOf("") }
    val jendela = det >= -15 && det <= 120
    LaunchedEffect(t0, jendela) {
        while (jendela) {
            val hp = withContext(Dispatchers.IO) { LiveGold.harga() }
            if (hp != null) {
                live = (live + (System.currentTimeMillis() to hp.first)).takeLast(400)
                liveSrc = hp.second
            }
            if (System.currentTimeMillis() - t0 > 120_000L) break
            delay(500L)
        }
    }
    val dasar = live.lastOrNull { it.first <= t0 - 300 }?.second           // harga ±1 dtk sebelum rilis
    val kini = live.lastOrNull()?.takeIf { it.first > t0 }
    val gerak = if (dasar != null && kini != null) kini.second - dasar else null
    val liveArah = gerak?.let { if (it >= 0.5) "naik" else if (it <= -0.5) "turun" else null }
    val arah = r.optString("arah").ifBlank { null }
    val nama = r.optString("nama").ifBlank { "Berita" }
    val pd = r.optJSONObject("per_detik")
    fun p(h: Int): Int? = pd?.optInt(h.toString(), -1)?.takeIf { it > 0 }
    /** Persen untuk detik ke-s: kunci terdekat ≤ s (1…10, 15, 20, 30, 45, 60, 90, 120, 180, 240, 300). */
    fun pAt(s: Int): Int? = pd?.keys()?.asSequence()?.mapNotNull { it.toIntOrNull() }?.filter { it <= s }?.maxOrNull()
        ?.let { p(it) }
    val ar = if (arah == "naik") "▲ NAIK" else "▼ TURUN"
    fun mmss(x: Double): String = "${(x / 60).toInt()}:${"%02d".format(x.toInt() % 60)}"
    fun pct(x: Int?): String = x?.let { if (it < 50) "$it% ⚠️" else "$it%" } ?: "–"
    val dtk = kotlin.math.ceil(det.coerceAtLeast(0.01)).toInt()
    fun usd(g: Double): String = (if (g < 0) "−" else "+") + "\$" + "%.2f".format(Locale.US, kotlin.math.abs(g)).replace('.', ',')
    val liveTeks = gerak?.let { g ->
        if (liveArah == null) "⚡ $nama detik $dtk • LIVE emas ${usd(g)} • belum jelas (< \$0,50), tunggu"
        else {
            val la = if (liveArah == "naik") "▲ NAIK" else "▼ TURUN"
            val tahan = r.optJSONObject("lanjut")?.optInt("2", 0)?.takeIf { it > 0 }
            val beda = arah != null && arah != liveArah
            "⚡ $nama detik $dtk • LIVE emas $la ${usd(g)}" +
                (tahan?.let { " • bertahan s/d detik 10: $it%" } ?: "") +
                (if (beda) " • ⚠️ tebakan sebelum rilis SALAH" else "") + abaLive(r, det, liveArah)
        }
    }
    val teks = when {
        det >= 0 && det <= 120 && liveTeks != null -> liveTeks
        arah == null -> if (det < 0) "⏱️ $nama T−${mmss(-det)} • arah ≈ 50:50 (tanpa petunjuk teruji)"
                        else "🔴 $nama rilis +${mmss(det)} • ≈ 50:50"
        det < 0 -> "⏱️ $nama T−${if (det < -60) mmss(-det) else "${-det.toInt()} dtk"} • emas $ar • detik 1 " +
            "${p(1) ?: "–"}% • detik 2 ${p(2) ?: "–"}%" + aba(r, det)
        det < 60 -> "🔴 $nama detik $dtk • emas $ar ${pct(pAt(dtk) ?: r.optInt("persen"))}" + aba(r, det)
        det < 300 -> "🔴 $nama menit ${mmss(det)} • emas $ar ${pct(pAt(dtk))}" +
            (r.optInt("menit_pct", 0).takeIf { it > 0 }?.let { " • ikuti arah detik 2 ($it%)" } ?: "")
        else -> "$nama +${(det / 60).toInt()} mnt • di luar jangka uji (5 mnt)"
    }
    Text(arahBerwarna(teks), style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.ExtraBold, maxLines = 3)
    if (jendela) {
        val info = when {
            live.isEmpty() -> "⚡ LIVE: menghubungi bursa emas token…"
            det < 0 -> "⚡ LIVE siap: ${liveSrc} ${"%.1f".format(Locale.US, live.last().second)} • setelah rilis arah = gerak harga"
            dasar == null -> "⚡ LIVE: buka aplikasi sebelum rilis supaya harga dasar tercatat"
            else -> "⚡ sumber ${liveSrc} (≈ spot, bisa ±1 dtk lebih cepat dari MT5)"
        }
        Text(info, style = MaterialTheme.typography.labelSmall, color = Muted, maxLines = 2)
    }
}

/** 💥 + ⚡: posisi modal kecil berlawanan dengan arah LIVE → tutup segera; searah → aba-aba biasa. */
private fun abaLive(r: JSONObject, det: Double, liveArah: String): String {
    val a = r.optJSONObject("allin")?.takeIf { it.optBoolean("kuat") } ?: return ""
    val posisi = a.optString("arah").uppercase(Locale.US)
    val lawan = (posisi.contains("BUY") && liveArah == "turun") || (posisi.contains("SELL") && liveArah == "naik")
    return if (lawan) " • 💥 BERLAWANAN → TUTUP SEKARANG" else aba(r, det)
}

/**
 * 💥 aba-aba modal kecil (hanya tebakan CPI kuat). 4.36 "lentur" (pilihan pengguna 13 Okt, research/cpi_allin2.py bank):
 * T−5…0 MASUK, detik 0–2 tahan, detik 2 rugi → TUTUP / untung → tahan s/d detik 10, detik 10–13 TUTUP. Cloud lama (tanpa
 * allin.keluar) = tutup detik 2–5 seperti 4.35.
 */
private fun aba(r: JSONObject, det: Double): String {
    val a = r.optJSONObject("allin")?.takeIf { it.optBoolean("kuat") } ?: return ""
    val lentur = a.optString("keluar") == "lentur"
    return when {
        det >= -900 && det < -5 -> " • 💥 siapkan ${a.optString("arah")}"
        det >= -5 && det < 0 -> " • 💥 MASUK ${a.optString("arah")}"
        det >= 0 && det < 2 -> " • 💥 tahan s/d detik 2"
        !lentur && det >= 2 && det < 5 -> " • 💥 TUTUP SEKARANG"
        lentur && det >= 2 && det < 3 -> " • 💥 rugi → TUTUP • untung → tahan s/d detik 10"
        lentur && det >= 3 && det < 10 -> " • 💥 untung? tahan ${10 - det.toInt()} dtk lagi • rugi → TUTUP"
        lentur && det >= 10 && det < 13 -> " • 💥 TUTUP SEKARANG (detik 10)"
        else -> ""
    }
}

/**
 * 💥 Modal kecil + lot maksimal (4.35, permintaan pengguna 13 Okt 2026: masuk 1 dtk sebelum rilis, modal kecil siap hilang).
 * Cloud pra_satu.allin hanya untuk CPI (research/cpi_allin2.py): tebakan kuat → arah + tutup detik 2; ⚠️ lemah → JANGAN.
 * Lot maks dihitung untuk modal KECIL contoh (bukan modal utama di ⚙️): lot = saldo × leverage ÷ (harga × 100)
 * (Cent: 0,01 lot = 1 oz → saldo USC; akun USD: saldo USD). Ketuk = bukti. Info saja, tanpa order.
 * 4.37 (pengguna 13 Okt: "detik pertama bisa spike berlawanan lalu habis padahal prediksi benar"): tabel leverage dari
 * research/cpi_spike.py (allin.lev_tabel/saran_lev): lot untuk 1 peluru 10.000 USC, emas boleh melawan berapa dolar sebelum
 * modal habis (= harga ÷ leverage), hasil uji 2022–2026. ⭐ = leverage terbesar yang tidak pernah habis saat arah benar.
 */
@Composable
private fun StripAllin(prep: JSONObject?, xau: Double?) {
    val a = prep?.optJSONObject("pra_satu")?.optJSONObject("allin") ?: return
    var buka by remember(a.optString("teks")) { mutableStateOf(false) }
    val kuat = a.optBoolean("kuat")
    val tabel = a.optJSONArray("lev_tabel")
    val saran = a.optInt("saran_lev", 0)
    Column(Modifier.fillMaxWidth().clickable { buka = !buka }) {
        Text(arahBerwarna(a.optString("teks")), style = MaterialTheme.typography.labelMedium,
            fontWeight = FontWeight.ExtraBold, color = if (kuat) Gold else Muted, maxLines = 2)
        if (kuat && xau != null && xau > 0) {
            val m = SignalRepository.money()
            fun lot(saldo: Double, lev: Int) = Math.floor(saldo * lev / (xau * 100.0) * 100.0 + 1e-9) / 100.0
            fun dolar(x: Double) = "$" + fmt(x).replace(',', ' ').replace('.', ',').replace(' ', '.')
            val saldoTxt: (Double) -> String = { "${"%,.0f".format(Locale.US, it).replace(',', '.')} ${m.currency}" }
            if (tabel != null && tabel.length() > 0 && saran > 0) {
                val saldo = if (m.cent) 10_000.0 else 100.0
                val levs = (0 until tabel.length()).map { tabel.getJSONObject(it).optInt("lev") }.filter { it >= 200 }
                Text("1 peluru ${saldoTxt(saldo)}: " + levs.joinToString(" • ") {
                    "1:$it ${lotText(lot(saldo, it))}${if (it == saran) " ⭐" else ""}"
                } + " lot", style = MaterialTheme.typography.labelMedium, fontWeight = FontWeight.Bold, color = Gold,
                    maxLines = 2)
                Text("⭐ 1:$saran: habis bila emas melawan ${dolar(xau / saran)} • lonjakan detik 1 saat arah benar " +
                    "sejak 2022 tidak pernah sejauh itu • ketuk = tabel", style = MaterialTheme.typography.labelSmall,
                    color = Muted, maxLines = 2)
                if (buka) {
                    for (i in 0 until tabel.length()) {
                        val t = tabel.getJSONObject(i)
                        val lev = t.optInt("lev")
                        val hb = t.optInt("habis_benar")
                        Text("${if (lev == saran) "⭐ " else ""}1:$lev • ${lotText(lot(saldo, lev))} lot • habis bila melawan " +
                            "${dolar(xau / lev)} • untung ${t.optInt("untung")}% rilis • rata ${"%+.0f".format(t.optDouble("rata"))}" +
                            "/$100 • habis ${t.optInt("habis")}/${t.optInt("n")}" +
                            (if (hb > 0) " ($hb× padahal arah benar)" else ""),
                            style = MaterialTheme.typography.labelSmall,
                            color = if (lev == saran) Gold else if (hb > 0) SellColor else Muted)
                    }
                    a.optJSONObject("bertahap")?.let { b ->
                        Text("Pilihan BERTAHAP: 1:200 saat T−1 dtk → detik 2 untung, tambah lot sampai total 1:1000 → rata " +
                            "${"%+.0f".format(b.optDouble("rata"))}/$100, habis ${b.optInt("habis")}× • satu-satunya yang juga " +
                            "positif sebelum 2021 (${"%+.1f".format(b.optDouble("lama_rata")).replace('.', ',')})",
                            style = MaterialTheme.typography.labelSmall, color = Muted)
                    }
                    Text("Sebelum Okt 2021 semua leverage rata-rata RUGI • pakai ±95% lot (spread & margin) • order ditolak " +
                        "(Exness HMR membatasi leverage saat berita) → pakai baris leverage yang lebih kecil",
                        style = MaterialTheme.typography.labelSmall, color = Muted)
                }
            } else {
                val lev = a.optInt("lev", 200)
                val contoh = if (m.cent) listOf(5_000.0, 10_000.0) else listOf(50.0, 100.0)
                val teks = contoh.joinToString(" • ") { "${saldoTxt(it)} ≈ ${lotText(lot(it, lev))} lot" }
                Text("Lot maks 1:$lev: $teks • rugi maks = seluruh saldo", style = MaterialTheme.typography.labelSmall,
                    color = Muted, maxLines = 2)
            }
        }
        if (buka) Text(a.optString("bukti"), style = MaterialTheme.typography.labelSmall, color = Muted)
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
private fun MiniTile(sym: String, hb: SignalEvent, selected: Boolean, modifier: Modifier, live: Double? = null,
                     onClick: () -> Unit) {
    val (arrow, color) = trendOf(hb)
    val btc = !sym.startsWith("XAU")
    val price = live ?: hb.num("price")
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
        Text(sym.substringBefore("/") + if (live != null) " ⚡" else "", style = MaterialTheme.typography.labelSmall, color = Muted)
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
        // 4.22: tampilkan prediksi ("CPI: emas naik 54%"), bukan sekadar nama berita
        val label = prediksiTeks(b, pendek = true)?.let { "🎯 $it" } ?: "📰 ${b.optString("title").take(18)}"
        if (t.isAfter(nowI) && (best == null || t.isBefore(best.second))) best = label to t
    }
    best?.let { (label, t) ->
        val left = Duration.between(nowI, t).toMillis()
        if (left <= 24 * 3600_000L) return label to left
    }
    val day = nowI.truncatedTo(java.time.temporal.ChronoUnit.DAYS)
    val sesi = listOf("🌏 Asia" to 0L, "🇪🇺 Eropa" to 7L, "🇺🇸 Amerika" to 13L)
    for (d in 0..1) for ((name, h) in sesi) {
        val t = day.plus(Duration.ofDays(d.toLong())).plus(Duration.ofHours(h))
        if (t.isAfter(nowI)) return name to Duration.between(nowI, t).toMillis()
    }
    return "" to 0L
}

/** 📉/📈 status "lonjakan memudar" XAU & BTC (cloud _pudar.py) ≤ 6 jam setelah rilis; tanpa teks bila tidak ada. */
@Composable
private fun StripPudar(prep: JSONObject?, now: Long) {
    val list = prep?.optJSONArray("berita") ?: return
    val nowI = Instant.ofEpochMilli(now)
    for (key in listOf("pudar", "pudar_btc")) {
        var p: JSONObject? = null
        for (i in 0 until list.length()) {
            val b = list.getJSONObject(i)
            val t = instantOf(b.optString("time")) ?: continue
            val x = b.optJSONObject(key) ?: continue
            if (!t.isAfter(nowI) && Duration.between(t, nowI).toHours() < 6) p = x
        }
        p?.let {
            val teks = it.optString("teks")
            Text("${if (key == "pudar") "XAU" else "BTC"} ${it.optString("label")}: $teks", maxLines = 2,
                style = MaterialTheme.typography.labelMedium, fontWeight = FontWeight.Bold,
                color = if (teks.contains("🔴")) SellColor else if (teks.contains("🟢")) BuyColor else Gold)
        }
    }
}

/**
 * ⏱️ KHUSUS XAU (10 Okt 2026): entry 1 detik SEBELUM berita berikutnya → arah emas 1–10 detik setelah rilis (naik/turun
 * saja, bukan untung/rugi). Arah dari petunjuk teruji; persen = seberapa sering harga XAU bergerak searah di detik
 * 1/2/3/5/10 (cloud _pra_aset.py ← research/pra_xau_arah.py, tick Exness 2015–2026). Ketuk = bukti.
 */
/** "4 hari lagi" / "5 jam lagi" / "12 mnt lagi" dihitung di HP (teks cloud bisa sudah lama). */
private fun sisaTeks(t: Instant?): String {
    if (t == null) return ""
    val s = java.time.Duration.between(Instant.now(), t).seconds
    return when {
        s <= 0 -> "sedang rilis"
        s >= 86400 -> "${s / 86400} hari lagi"
        s >= 3600 -> "${s / 3600} jam lagi"
        else -> "${maxOf(1L, s / 60)} mnt lagi"
    }
}

/**
 * 🎯 Berita mendatang di bawah XAU (aplikasi 4.30, permintaan pengguna): satu baris per berita
 * "CPI • peluang emas turun 66% ⚠️ • 4 hari lagi" (arah emas 1–10 dtk setelah rilis; cloud _pra_aset.daftar).
 * Persen = seberapa sering tebakan itu benar di data 2010–2026; tanpa petunjuk teruji → "≈ 50:50". Ketuk = bukti.
 */
@Composable
private fun StripDaftar(prep: JSONObject, daftar: org.json.JSONArray) {
    val pra = prep.optJSONObject("pra")
    var buka by remember(daftar.toString()) { mutableStateOf(-1) }
    Column(Modifier.fillMaxWidth()) {
        Text("🎯 Berita mendatang • arah emas 1–10 dtk setelah rilis", maxLines = 1,
            style = MaterialTheme.typography.labelSmall, color = Muted, fontWeight = FontWeight.Bold)
        for (i in 0 until daftar.length()) {
            val r = daftar.optJSONObject(i) ?: continue
            val st = r.optString("status")
            val naik = r.optString("arah") == "naik"
            val warna = when (st) {
                "acak" -> Muted
                "teruji", "tren searah" -> if (naik) BuyColor else SellColor
                else -> Gold
            }
            val teks = r.optString("teks").substringBeforeLast(" • ") + " • " +
                sisaTeks(instantOf(r.optString("time")))
            Column(Modifier.fillMaxWidth().clickable { buka = if (buka == i) -1 else i }) {
                Text(teks, style = if (i == 0) MaterialTheme.typography.labelMedium else MaterialTheme.typography.labelSmall,
                    color = warna, fontWeight = if (i == 0) FontWeight.ExtraBold else FontWeight.Bold, maxLines = 2)
                val tr = r.optJSONObject("tren")
                if (tr != null) {
                    Text(tr.optString("teks"), style = MaterialTheme.typography.labelSmall, color = Muted, maxLines = 2)
                    if (buka == i) Text(tr.optString("bukti"), style = MaterialTheme.typography.labelSmall, color = Muted)
                } else if (i == 0) {
                    val nanti = pra?.optString("tren_nanti").orEmpty()
                    if (nanti.isNotBlank()) Text(nanti, style = MaterialTheme.typography.labelSmall, color = Muted, maxLines = 1)
                }
                if (buka == i) Text(r.optString("bukti"), style = MaterialTheme.typography.labelSmall, color = Muted)
            }
        }
        // 📌 kepastian setelah detik 2 (4.28) tetap tampil sekali di bawah daftar
        pra?.optString("kepastian")?.ifBlank { null }?.let {
            Text(it, style = MaterialTheme.typography.labelSmall, color = Gold, fontWeight = FontWeight.Bold, maxLines = 2)
        }
    }
}

/** 4.33: hanya bagian arah + persen yang berwarna ("▼ TURUN 56%" merah, "▲ NAIK 56%" hijau); sisanya warna biasa. */
@Composable
internal fun arahBerwarna(teks: String): AnnotatedString {
    val hijau = BuyColor                                  // warna tema = @Composable → dibaca di luar builder
    val merah = SellColor
    return buildAnnotatedString {
        val m = Regex("(▲ NAIK|▼ TURUN|naik|turun|NAIK|TURUN) \\d+%").find(teks)
        if (m == null) {
            append(teks)
        } else {
            append(teks.substring(0, m.range.first))
            val naik = m.value.contains("NAIK") || m.value.startsWith("naik")
            withStyle(SpanStyle(color = if (naik) hijau else merah, fontWeight = FontWeight.Bold)) { append(m.value) }
            append(teks.substring(m.range.last + 1))
        }
    }
}

/**
 * 🎯 SATU baris berita berikutnya (aplikasi 4.31, permintaan pengguna "cukup news berikutnya naik atau turun"):
 * "CPI ▼ TURUN 56% ⚠️ • 4 hari lagi" (arah emas 1–10 dtk setelah rilis, cloud _pra_aset.satu). Ketuk = dasar angka.
 */
@Composable
private fun StripSatu(r: JSONObject) {
    var buka by remember(r.optString("time") + r.optString("teks")) { mutableStateOf(false) }
    val teks = r.optString("teks").substringBeforeLast(" • ") + " • " + sisaTeks(instantOf(r.optString("time")))
    Column(Modifier.fillMaxWidth().clickable { buka = !buka }) {
        // 4.33: ukuran biasa (keluhan "terlalu besar"); hanya arah + persen berwarna
        // 4.38: tanda ▾/▴ supaya jelas bisa diketuk; detail = poin "• …" dari cloud (tutup kertas, konsensus, orang, dll)
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(arahBerwarna(teks), Modifier.weight(1f), style = MaterialTheme.typography.labelMedium, maxLines = 2)
            Text(if (buka) "▴" else "▾", color = Muted, style = MaterialTheme.typography.labelMedium)
        }
        if (buka) Text(r.optString("bukti"), style = MaterialTheme.typography.labelSmall, color = Muted)
    }
}

@Composable
private fun StripPra(prep: JSONObject?) {
    val satu = prep?.optJSONObject("pra_satu")
    if (satu != null) {
        StripSatu(satu)
        return
    }
    val daftar = prep?.optJSONArray("pra_daftar")
    if (prep != null && daftar != null && daftar.length() > 0) {
        StripDaftar(prep, daftar)
        return
    }
    val pra = prep?.optJSONObject("pra") ?: return
    var open by remember(pra.optString("time")) { mutableStateOf(false) }
    val st = pra.optString("status")
    val warna = when {
        st == "acak" -> Muted
        st == "teruji" -> if (pra.optString("arah") == "naik") BuyColor else SellColor
        else -> Gold
    }
    Column(Modifier.fillMaxWidth().clickable { open = !open }) {
        Text(pra.optString("judul"), maxLines = 1, style = MaterialTheme.typography.labelSmall, color = Muted,
            fontWeight = FontWeight.Bold)
        Text(pra.optString("teks"), style = MaterialTheme.typography.labelMedium, color = warna,
            fontWeight = FontWeight.ExtraBold, maxLines = 2)
        Text(pra.optString("kecil"), style = MaterialTheme.typography.labelSmall, color = Muted, maxLines = 2)
        // ➕ tren emas 4 jam (aplikasi 4.29): searah petunjuk berita → % gabungan; berlawanan → ≈ lempar koin
        pra.optJSONObject("tren")?.let { tr ->
            val hub = tr.optString("hubungan")
            val wTren = when (hub) {
                "sepakat" -> if (tr.optString("arah") == "naik") BuyColor else SellColor
                "berlawanan" -> Gold
                else -> Muted
            }
            Text(tr.optString("teks"), style = MaterialTheme.typography.labelSmall, color = wTren,
                fontWeight = FontWeight.Bold, maxLines = 2)
            Text(tr.optString("putusan"), style = MaterialTheme.typography.labelSmall, color = wTren, maxLines = 2)
            if (open) Text(tr.optString("bukti"), style = MaterialTheme.typography.labelSmall, color = Muted)
        } ?: pra.optString("tren_nanti").ifBlank { null }?.let {
            Text(it, style = MaterialTheme.typography.labelSmall, color = Muted, maxLines = 1)
        }
        // 📌 kepastian setelah detik 2 (aplikasi 4.28): arah yang sudah terlihat ≥ $0,50 hampir selalu bertahan s/d detik 10
        pra.optString("kepastian").ifBlank { null }?.let {
            Text(it, style = MaterialTheme.typography.labelSmall, color = Gold, fontWeight = FontWeight.Bold,
                maxLines = if (open) 4 else 2)
        }
        if (open) {
            pra.optString("bukti").ifBlank { null }?.let {
                Text(it, style = MaterialTheme.typography.labelSmall, color = Muted)
            }
            Text(pra.optString("catatan"), style = MaterialTheme.typography.labelSmall, color = Muted)
        }
    }
}

/** 🎯 Berita besar berikutnya (pekan ini atau 📅 mendatang): "NFP: peluang emas naik 1 jam X%" (4.17). */
@Composable
private fun StripPrediksi(prep: JSONObject?) {
    val now = Instant.now()
    val cand = mutableListOf<JSONObject>()
    prep?.optJSONArray("berita")?.let { l ->
        for (i in 0 until l.length()) l.getJSONObject(i).takeIf { instantOf(it.optString("time"))?.isAfter(now) == true }?.let(cand::add)
    }
    prep?.optJSONArray("mendatang")?.let { l -> for (i in 0 until l.length()) cand.add(l.getJSONObject(i)) }
    val utama = listOf("Non-Farm", "CPI", "Federal Funds", "JOLTS")
    val b = cand.filter { c -> utama.any { c.optString("title").contains(it) } }
        .minByOrNull { instantOf(it.optString("time")) ?: Instant.MAX } ?: return
    // 4.18: cukup "NFP: peluang emas naik 1 jam 61%"; ketuk = show/hide detail (dasar angka, 🔄 titik balik NFP, 🏦 Fed)
    val p = b.optJSONObject("prediksi")
    val teks = p?.optString("teks")?.ifBlank { null } ?: b.optJSONObject("prarilis")?.optString("teks")?.ifBlank { null }
    val dalam = b.optString("dalam").ifBlank { b.optString("when") }
    var open by remember(b.optString("title") + b.optString("time")) { mutableStateOf(false) }
    Column(Modifier.fillMaxWidth().clickable { open = !open }) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(teks?.let { "🎯 $it" } ?: "🎯 ${b.optString("title").replace("Non-Farm Employment Change", "NFP")} (prediksi memuat…)", Modifier.weight(1f),
                maxLines = 2, style = MaterialTheme.typography.labelMedium, color = Gold, fontWeight = FontWeight.Bold)
            Text(if (open) "▴" else "▾", color = Muted, style = MaterialTheme.typography.labelMedium)
        }
        Text(dalam, maxLines = 1, style = MaterialTheme.typography.labelSmall, color = Muted)
        val det = p?.optJSONArray("detail")
        if (open && det != null) for (k in 0 until det.length()) {
            val d = det.optJSONObject(k) ?: continue
            Text("${d.optString("judul")}: ${d.optString("teks")}", style = MaterialTheme.typography.labelSmall,
                fontWeight = FontWeight.Bold)
            d.optString("catatan").ifBlank { null }?.let {
                Text(it, style = MaterialTheme.typography.labelSmall, color = Muted)
            }
        }
    }
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
