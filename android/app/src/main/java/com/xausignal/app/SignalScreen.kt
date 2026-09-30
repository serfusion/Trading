package com.xausignal.app

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import java.time.DayOfWeek
import java.time.LocalDate
import java.time.ZoneId
import java.time.ZonedDateTime
import java.time.temporal.TemporalAdjusters

private const val HISTORY_PAGE = 4

/** Tab Sinyal: harga semua pair, sinyal aktif, ringkasan, riwayat. */
@Composable
fun SignalsTab(allEvents: List<SignalEvent>, prices: Map<String, SignalEvent>, connection: String, money: MoneySettings,
               follow: Set<String> = SignalRepository.followed()) {
    // hanya pair yang diikuti (Pengaturan → Pair yang saya ikuti)
    // dihitung ulang hanya saat pesan / pair diikuti / harga berubah (bukan per kartu)
    val events = remember(allEvents, follow) { allEvents.filter { it.pairGroup() in follow } }
    val signalIds = remember(events) { events.filter { it.type == "signal" }.map { it.id }.toSet() }
    val primary = remember(events, prices) { SignalRepository.primaryOf(events, prices) }
    val twins = SignalRepository.twinCounts(events)
    // riwayat: sinyal kembar cukup 1 kartu (set utama = harga TUTUP yang dipakai)
    val history = remember(events, primary) {
        events.filter {
            (primary[it.id] ?: it.id) == it.id && (it.type == "signal" || (it.type == "close" && it.id !in signalIds))
        }
    }
    // posisi yang masih terbuka di cloud tetapi data sinyalnya tidak ada di HP (mis. aplikasi di-install ulang)
    val orphans = prices.values.flatMap { SignalRepository.cloudOpen(it) }
        .filter { x ->
            val grp = if (x.symbol.startsWith("XAU")) "XAU" else if (x.symbol.startsWith("BTC")) "BTC" else "GAP"
            x.id !in signalIds && grp in follow
        }
        .groupBy { SignalRepository.twinKey(it.id) }.values.toList()
    val missed = events.filter { it.type == "signal" && it.closedByHeartbeat(prices[it.symbol()]) }.map { it.id }.toSet()
    var shown by rememberSaveable { mutableIntStateOf(HISTORY_PAGE) }
    var showLog by rememberSaveable { mutableStateOf(false) }
    // log notifikasi: sinyal baru, TP1 + SL+, TUTUP, info auto order (terbaru di atas)
    val log = remember(events) {
        events.filter { it.type == "signal" || it.type == "close" || (it.type == "info" && it.str("kind") != "be07") }
    }
    // Sinyal kembar (beberapa set di candle sama: simbol, arah, entry sama) digabung jadi 1 kartu ×N.
    val open = SignalRepository.openSignals(events, prices)
        .groupBy { Triple(it.symbol(), it.dir, it.price("entry")) }.values.toList()
    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(horizontal = 16.dp, vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        item { TickerCard(prices, connection) }
        val active = open.size + orphans.size
        item { SectionTitle("Aktif", trailing = if (active == 0) null else "$active") }
        items(orphans, key = { "cloud-" + it.first().id }) { g -> CloudOpenCard(g, prices[g.first().symbol]) }
        if (active == 0) {
            item {
                AppCard {
                    Text("⏳ WAIT — belum ada sinyal 💰", fontWeight = FontWeight.Bold)
                    Text("Jangan entry manual. Cloud mengecek pasar tiap 10 menit; cek berikutnya ${nextCheckText()}.",
                        style = MaterialTheme.typography.labelSmall, color = Muted)
                }
            }
        } else {
            items(open, key = { "open-" + it.first().msgId }) { g ->
                val s = g.first()
                OpenSignalCard(s, prices[s.symbol()], g.any { SignalRepository.slPlusActive(events, it.id) }, money, g.size,
                    g.map { it.id })
            }
        }
        item { TodayCard(events, money) }
        item {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                SectionTitle("Riwayat", Modifier.weight(1f))
                FilterChip(selected = !showLog, onClick = { showLog = false; shown = HISTORY_PAGE },
                    label = { Text("Hasil (${history.size})") })
                FilterChip(selected = showLog, onClick = { showLog = true; shown = HISTORY_PAGE },
                    label = { Text("Notifikasi (${log.size})") })
            }
        }
        // hanya 4 kartu terbaru; "Load more" menampilkan 4 kartu lebih lama berikutnya
        if (showLog) {
            items(log.take(shown), key = { "log-" + it.msgId }) { LogRow(it, primary) }
        } else {
            items(history.take(shown), key = { it.msgId }) {
                if (it.type == "signal") SignalResultCard(it, events, money, it.id in missed, twins[it.id] ?: 1)
                else CloseRow(it, money, events)
            }
        }
        val total = if (showLog) log.size else history.size
        if (total > shown) {
            item {
                OutlinedButton(onClick = { shown += HISTORY_PAGE }, modifier = Modifier.fillMaxWidth()) {
                    Text("Load more (${total - shown} lagi)")
                }
            }
        }
        item { Footer() }
    }
}

/** Satu baris log notifikasi: jenis, pair, keterangan singkat, waktu. */
@Composable
fun LogRow(e: SignalEvent, primary: Map<String, String>) {
    val sym = e.symbol()
    val (icon, title, detail, color) = when (e.type) {
        "signal" -> listOf(if (e.dir == "BUY") "🟢" else "🔴", "Sinyal ${e.dir} $sym",
            "Entry ${e.price("entry")} • SL ${e.price("sl")} • ${if (e.isGap()) "TP" else "TP1"} ${e.price("tp1")}",
            "dir")
        "close" -> {
            val main = (primary[e.id] ?: e.id) == e.id
            if (e.isVoid()) listOf("⚠️", "BATAL ${e.dir} $sym", "Sinyal dari data saat pasar tutup", "muted")
            else if (main) listOf("🏁", "TUTUP ${e.dir} $sym • ${if (e.json.optBoolean("tp1_hit")) "PROFIT" else "MINUS"}",
                "Harga ${e.price("price")} • ${e.str("reason")}", if (e.json.optBoolean("tp1_hit")) "buy" else "sell")
            else listOf("•", "Set ${e.str("set")} selesai ($sym)", "Bukan TUTUP utama — posisi Anda tetap jalan", "muted")
        }
        else -> if (e.str("kind") == "tp1") listOf("🎯", "TP1 kena $sym",
            "Tutup 1 posisi, SL sisa ke ${if (e.num("sl_plus") != null) e.price("sl_plus") else "entry"}", "gold")
        else listOf("ℹ️", "Info", e.str("text"), "muted")
    }
    AppCard {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            Text(icon, style = MaterialTheme.typography.titleMedium)
            Column(Modifier.weight(1f)) {
                Text(title, fontWeight = FontWeight.Bold, color = when (color) {
                    "dir" -> dirColor(e.dir); "buy" -> BuyColor; "sell" -> SellColor; "gold" -> Gold; else -> Muted
                })
                Text(detail, style = MaterialTheme.typography.labelSmall, color = Muted, maxLines = 2)
            }
            Text(e.timeText(), style = MaterialTheme.typography.labelSmall, color = Muted)
        }
    }
}

/** Harga terakhir tiap pair dalam satu kartu ringkas. */
@Composable
fun TickerCard(prices: Map<String, SignalEvent>, connection: String) {
    val online = connection == "Terhubung"
    val list = prices.entries.sortedBy { (k, _) -> if (k.startsWith("XAU")) "0" else if (k.startsWith("BTC")) "1" else k }
    AppCard {
        Row(verticalAlignment = Alignment.CenterVertically) {
            StatusDot(if (online) BuyColor else SellColor)
            Text(
                if (online) "Live" else connection, style = MaterialTheme.typography.labelMedium,
                color = if (online) Muted else SellColor, modifier = Modifier.padding(start = 8.dp).weight(1f)
            )
            list.maxByOrNull { it.value.str("time") }?.let {
                Text(it.value.timeText(), style = MaterialTheme.typography.labelSmall, color = Muted)
            }
        }
        if (list.isEmpty()) Text("-", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
        list.forEach { (sym, hb) ->
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(sym, color = Muted, modifier = Modifier.weight(1f))
                Text(
                    priceText(sym, hb.num("price")), style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.Bold
                )
            }
        }
        // ⚠️ mode perang (minyak melonjak) dari heartbeat XAU: label saja, sinyal XAU tetap dikirim
        list.firstOrNull { it.key.startsWith("XAU") }?.value?.warText()?.let {
            Text(it, style = MaterialTheme.typography.labelMedium, color = SellColor, fontWeight = FontWeight.Bold)
        }
    }
}

/** Simbol + arah + waktu, lalu 💰 (profit) ★ (win rate) dan chip WR / R historis. */
@Composable
private fun SignalHeader(signal: SignalEvent, count: Int = 1) {
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(signal.symbol(), style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
        Pill(signal.dir, dirColor(signal.dir), solid = true)
        if (count > 1) Pill("×$count", Gold)
        tierLabel(signal.tier()).takeIf { it.isNotEmpty() && signal.type == "signal" }?.let {
            Pill(it, if (signal.isZap()) Gold else Muted, solid = signal.isZap())
        }
        Spacer(Modifier.weight(1f))
        Text(signal.timeText(), style = MaterialTheme.typography.labelSmall, color = Muted)
    }
    signal.warText()?.let { Text(it, style = MaterialTheme.typography.labelSmall, color = SellColor) }
    val m = signal.moneyBadge()
    val st = signal.stars()
    if (signal.type == "signal" && !signal.json.has("money") && !signal.isGap()) {
        // dikirim cloud versi lama (sebelum 28 Sep 10:02 WIB): semua sinyal dikirim, ★ = searah tren H4/EMA, belum ada 💰
        Text("Sinyal format lama (sebelum ada 💰): ★ = searah tren H4, bukan win rate. Belum tentu termasuk sinyal 💰.",
            style = MaterialTheme.typography.labelSmall, color = Muted)
    }
    if (m > 0 || st > 0 || signal.json.has("wr")) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            if (signal.isZap()) Text("⚡", fontWeight = FontWeight.Bold)
            if (m > 0) Text("💰".repeat(m))
            if (st > 0) Text("★".repeat(st), color = Gold, fontWeight = FontWeight.Bold)
            Spacer(Modifier.weight(1f))
            if (signal.json.has("wr")) {
                // ⚡ dengan SL+ 0,7R (otomatis): pakai statistik skema itu (WR lebih tinggi)
                val s07 = signal.json.has("wr07") && SignalRepository.money().use07(signal.id, signal.tier())
                val avg = signal.json.optDouble(if (s07) "avg_r07" else "avg_r")
                Pill("${signed(avg)}R", if (avg > 0) BuyColor else SellColor)
                Pill("WR ${fmt(signal.json.optDouble(if (s07) "wr07" else "wr"), 0)}%", Gold)
            }
        }
    }
}

@Composable
fun OpenSignalCard(signal: SignalEvent, hb: SignalEvent?, slPlus: Boolean, money: MoneySettings, count: Int = 1,
                   ids: List<String> = listOf(signal.id)) {
    val entry = signal.num("entry")
    val price = hb?.num("price")
    val sign = if (signal.dir == "BUY") 1 else -1
    val floating = if (entry != null && price != null) (price - entry) * sign else null
    // posisi yang masih terbuka: 5 sebelum TP1, 4 sesudahnya (posisi #1 sudah TP); gap = 1 posisi
    val legsOpen = if (!signal.isGap() && slPlus) signal.legs() - 1 else signal.legs()
    val cents = Math.round(signal.entryLot(money) * 100.0).toDouble()
    val pv = signal.num("point_value") ?: 1.0
    val floatMoney = floating?.let { it * legsOpen * cents * pv }
    AppCard(accent = dirColor(signal.dir)) {
        SignalHeader(signal, count)
        Row(verticalAlignment = Alignment.Bottom) {
            Text(
                signal.price("entry"), style = MaterialTheme.typography.headlineMedium,
                fontWeight = FontWeight.Bold, modifier = Modifier.weight(1f)
            )
            if (floating != null && floatMoney != null) {
                val digits = if (signal.symbol().contains("JPY")) 3 else if ((entry ?: 0.0) < 20) 5 else 2
                Column(horizontalAlignment = Alignment.End) {
                    Text(
                        moneyMain(floatMoney, money), style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold, color = if (floating >= 0) BuyColor else SellColor
                    )
                    Text(
                        "${idrLine(floatMoney, money)} • ${signed(floating, digits)} poin × $legsOpen posisi",
                        style = MaterialTheme.typography.labelSmall, color = Muted
                    )
                }
            }
        }
        MetricRow {
            Metric("SL", signal.price("sl"), SellColor, compact = true)
            Metric(if (signal.isGap()) "TP" else "TP1", signal.price("tp1"), BuyColor, compact = true)
        }
        LineDivider()
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text("Entry", color = Muted, modifier = Modifier.weight(1f))
            Text(legsLot(signal, money), style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold, color = Gold)
        }
        Text(lossLine(signal, money) + if (count > 1) " • $count set sama, entry 1× saja" else "",
            style = MaterialTheme.typography.labelSmall, color = Muted)
        if (slPlus) Text("🛡️ SL+ aktif", color = BuyColor, fontWeight = FontWeight.Bold)
        val sl = signal.num("sl")
        if (floating != null && slPlus && !signal.isGap() && floating < 0) {
            NoteBox(
                "⚠️ Harga sudah melewati SL+ (≈ entry). Bila SL 4 posisi sudah digeser ke SL+, posisi itu sudah " +
                    "tertutup ≈ impas. Bila di MT5 masih terbuka dan minus, SL belum digeser: tutup atau pasang SL sekarang.",
                SellColor
            )
        } else if (price != null && sl != null && !slPlus && (price - sl) * sign <= 0) {
            NoteBox(
                "⚠️ Harga sudah melewati SL. Posisi seharusnya tertutup di SL; bila di MT5 masih terbuka, SL belum " +
                    "terpasang — tutup sekarang. Konfirmasi TUTUP dari cloud menyusul (cek tiap 10 menit).",
                SellColor
            )
        }
        val exits = exitLevels(hb, ids)
        if (exits.isNotEmpty()) {
            val buy = signal.dir == "BUY"
            LineDivider()
            Text("🚪 HARGA TUTUP — 4 posisi running", style = MaterialTheme.typography.titleSmall,
                fontWeight = FontWeight.ExtraBold, color = Gold)
            if (count > 1) {
                Text("$count set sama, entry 1× → cukup 1 harga TUTUP ini (set paling lambat; di data paling untung).",
                    style = MaterialTheme.typography.labelSmall, color = Muted)
            }
            exits.forEach { x ->
                val gap = price?.let { (it - x.level) * sign }
                Row(verticalAlignment = Alignment.Bottom) {
                    Column(Modifier.weight(1f)) {
                        Text("tutup bila close H1 ${if (buy) "di bawah" else "di atas"}",
                            style = MaterialTheme.typography.labelSmall, color = Muted)
                        Text(priceText(signal.symbol(), x.level), style = MaterialTheme.typography.headlineSmall,
                            fontWeight = FontWeight.ExtraBold)
                    }
                    Column(horizontalAlignment = Alignment.End) {
                        Text(x.set, style = MaterialTheme.typography.labelMedium, fontWeight = FontWeight.Bold)
                        Text(
                            "${if (buy) "low" else "high"} ${x.bars} candle" +
                                (gap?.let { " • jarak ${fmt(it, 2)}" } ?: ""),
                            style = MaterialTheme.typography.labelSmall, color = Muted
                        )
                    }
                }
            }
            // Bila harga berbalik sekarang, posisi keluar di yang lebih dulu kena: SL/SL+ (langsung) atau TUTUP
            // (dicek saat candle H1 tutup) -> hasil minimal yang sudah "terkunci".
            if (entry != null && !signal.isGap()) {
                val stop = if (slPlus) entry + sign * 0.10 else signal.num("sl")
                if (stop != null) {
                    val near = if (buy) exits.maxOf { it.level } else exits.minOf { it.level }
                    val exit = if (buy) maxOf(stop, near) else minOf(stop, near)
                    val by = if (exit == stop) (if (slPlus) "SL+" else "SL") else "TUTUP"
                    val result = (exit - entry) * sign * legsOpen * cents * pv
                    Text(
                        (if (result > 0 && by == "TUTUP") "🔒 Profit terkunci ≈ " else "Bila harga berbalik sekarang: ") +
                            "${moneyMain(result, money)} (${idrLine(result, money)}) di $by " +
                            priceText(signal.symbol(), exit),
                        style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.Bold,
                        color = if (result >= 0) BuyColor else SellColor
                    )
                }
            }
            Text(
                "Harga TUTUP berubah tiap jam, umumnya mengikuti harga ke arah profit (seperti trailing stop); " +
                    "bisa bergeser menjauh bila ada ekor candle melewatinya tanpa close. Dicek saat candle H1 tutup, " +
                    "jadi hasil bisa sedikit lebih jelek dari angkanya. " +
                    "Update ${hb?.timeText() ?: "-"}.",
                style = MaterialTheme.typography.labelSmall, color = Muted
            )
        }
    }
}

/**
 * Sinyal yang menurut heartbeat cloud masih berjalan, tetapi data sinyalnya tidak ada di HP (mis. aplikasi baru
 * di-install ulang dan pesan lama sudah lewat 12 jam di ntfy). Menampilkan satu harga TUTUP (set paling lambat).
 */
@Composable
fun CloudOpenCard(group: List<CloudOpen>, hb: SignalEvent?) {
    val main = group.maxByOrNull { it.bars } ?: return
    val buy = main.dir == "BUY"
    val price = hb?.num("price")
    AppCard(accent = dirColor(main.dir)) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(main.symbol, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            Pill(main.dir, dirColor(main.dir), solid = true)
            if (group.size > 1) Pill("×${group.size}", Gold)
        }
        Text(
            "Sinyal ini masih berjalan di cloud, tetapi data entry-nya tidak ada di HP (mis. aplikasi di-install ulang). " +
                "Kalau posisi Anda sudah ditutup, abaikan kartu ini.",
            style = MaterialTheme.typography.labelSmall, color = Muted
        )
        LineDivider()
        Text("🚪 HARGA TUTUP", style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.ExtraBold, color = Gold)
        Row(verticalAlignment = Alignment.Bottom) {
            Column(Modifier.weight(1f)) {
                Text("tutup bila close H1 ${if (buy) "di bawah" else "di atas"}",
                    style = MaterialTheme.typography.labelSmall, color = Muted)
                Text(priceText(main.symbol, main.level), style = MaterialTheme.typography.headlineSmall,
                    fontWeight = FontWeight.ExtraBold)
            }
            Column(horizontalAlignment = Alignment.End) {
                Text(main.set, style = MaterialTheme.typography.labelMedium, fontWeight = FontWeight.Bold)
                Text(
                    "${if (buy) "low" else "high"} ${main.bars} candle" +
                        (price?.let { " • jarak ${fmt((it - main.level) * (if (buy) 1 else -1), 2)}" } ?: ""),
                    style = MaterialTheme.typography.labelSmall, color = Muted
                )
            }
        }
    }
}

/** Jam cek cloud berikutnya (menit :02, :12, … :52), WIB. */
fun nextCheckText(): String {
    val now = ZonedDateTime.now(ZoneId.of("Asia/Jakarta"))
    val m = now.minute
    val next = ((m - 2).floorDiv(10) + 1) * 10 + 2
    val t = now.withSecond(0).withNano(0).withMinute(0).plusMinutes(next.toLong())
    return String.format(java.util.Locale.US, "%02d:%02d WIB", t.hour, t.minute)
}

/** Level TUTUP (channel keluar) untuk candle H1 yang sedang berjalan, dari heartbeat cloud (`exits`). */
data class ExitLevel(val set: String, val level: Double, val bars: Int)

fun exitLevels(hb: SignalEvent?, ids: Collection<String>): List<ExitLevel> {
    val arr = hb?.json?.optJSONArray("exits") ?: return emptyList()
    return (0 until arr.length()).mapNotNull { i ->
        val o = arr.optJSONObject(i) ?: return@mapNotNull null
        if (o.optString("id") in ids) ExitLevel(o.optString("set"), o.optDouble("level"), o.optInt("bars")) else null
    }.maxByOrNull { it.bars }?.let { listOf(it) } ?: emptyList()   // satu harga: set paling lambat (lihat primaryOf)
}

fun weekKey(t: ZonedDateTime): String =
    t.toLocalDate().with(TemporalAdjusters.previousOrSame(DayOfWeek.MONDAY)).toString()

@Composable
fun TodayCard(events: List<SignalEvent>, money: MoneySettings) {
    val today = LocalDate.now(ZoneId.of("Asia/Jakarta"))
    val dayKey: (ZonedDateTime) -> String = { it.toLocalDate().toString() }
    // dihitung ulang hanya saat pesan / pengaturan / tanggal berubah, bukan setiap harga bergerak
    val day = remember(events, money, today) {
        SignalRepository.periodStats(events, money, dayKey).firstOrNull { it.label == today.toString() }
    }
    // rincian per pair supaya jelas dari mana untung/rugi hari ini (XAU, BTC, forex gap)
    val perPair = remember(events, money, today) {
        events.filter { it.type == "close" }.map { it.symbol() }.distinct().sorted().mapNotNull { sym ->
            SignalRepository.periodStats(events, money, dayKey, symbol = sym)
                .firstOrNull { it.label == today.toString() }?.let { sym to it }
        }
    }
    val week = remember(events, money, today) {
        SignalRepository.periodStats(events, money, ::weekKey)
            .firstOrNull { it.label == today.with(TemporalAdjusters.previousOrSame(DayOfWeek.MONDAY)).toString() }
    }
    val month = remember(events, money, today) {
        SignalRepository.periodStats(events, money, { it.toLocalDate().toString().substring(0, 7) })
            .firstOrNull { it.label == today.toString().substring(0, 7) }
    }
    AppCard {
        SummaryLine("Hari ini", day, money)
        if (perPair.size > 1 || perPair.any { !it.first.startsWith("XAU") }) {
            perPair.forEach { (sym, s) ->
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text("• $sym  ${s.wins} Profit • ${s.losses} Minus", style = MaterialTheme.typography.labelSmall,
                        color = Muted, modifier = Modifier.weight(1f))
                    Text(moneyMain(s.net, money), style = MaterialTheme.typography.labelSmall,
                        fontWeight = FontWeight.Bold, color = if (s.net >= 0) BuyColor else SellColor)
                }
            }
        }
        LineDivider()
        SummaryLine("Minggu ini", week, money)
        LineDivider()
        SummaryLine("Bulan ini", month, money)
    }
}

@Composable
fun SummaryLine(label: String, s: PeriodStats?, money: MoneySettings) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Column(Modifier.weight(1f)) {
            Text(label, fontWeight = FontWeight.Medium)
            if (s != null) {
                Text("${s.wins} Profit • ${s.losses} Minus", style = MaterialTheme.typography.labelSmall, color = Muted)
            }
        }
        if (s == null) {
            Text("-", color = Muted)
        } else {
            Column(horizontalAlignment = Alignment.End) {
                Text(moneyMain(s.net, money), fontWeight = FontWeight.Bold,
                    color = if (s.net >= 0) BuyColor else SellColor)
                Text(idrLine(s.net, money), style = MaterialTheme.typography.labelSmall, color = Muted)
            }
        }
    }
}

/** "5 posisi × 0.02 lot": yang dimasukkan di MT5. Sinyal kembar ×N tetap entry 1×. */
fun legsLot(signal: SignalEvent, money: MoneySettings): String =
    "${signal.legs()} posisi × ${lotText(signal.entryLot(money))} lot"

/** "Rugi maks di SL −450 USC (≈ −Rp74.250, 0,45% modal)". */
fun lossLine(signal: SignalEvent, money: MoneySettings): String {
    val loss = signal.maxLoss(money) ?: return "Pasang SL sesuai sinyal"
    val idr = idrText(SignalRepository.toIdr(loss, money))
    val pct = if (money.modalIdr > 0) ", ${fmt(loss / money.balance * 100.0, 2).replace('.', ',')}% modal" else ""
    return "Rugi maks di SL −${fmt(loss, 0)} ${money.currency} (≈ −$idr$pct)"
}

/** Riwayat satu sinyal: entry → tutup → PROFIT (TP1 kena) / MINUS + uang. */
@Composable
fun SignalResultCard(signal: SignalEvent, events: List<SignalEvent>, money: MoneySettings, missed: Boolean = false,
                     count: Int = 1) {
    if (signal.isVoid()) {
        AppCard {
            SignalHeader(signal)
            Pill("BATAL", Muted, solid = true)
        }
        return
    }
    val tp1 = SignalRepository.tp1Event(events, signal.id)
    val close = SignalRepository.closeEvent(events, signal.id)
    // kartu ini = set utama (harga TUTUP yang dipakai); sinyal kembar entry 1× -> hasil tidak dibagi
    val amount = close?.let { SignalRepository.amount(it, money) }
    val win = close != null && SignalRepository.isWin(close, events)   // menang = TP1 kena
    val result = if (close == null) Gold else if (win) BuyColor else SellColor
    AppCard(accent = result) {
        SignalHeader(signal, count)
        MetricRow {
            Metric("Entry", signal.price("entry"), compact = true)
            Metric("Tutup", close?.price("price") ?: "-", compact = true)
            Metric("Waktu tutup", close?.timeText()?.removeSuffix(" WIB") ?: "-", compact = true)
        }
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Pill(
                if (close == null && missed) "SELESAI" else if (close == null) "BERJALAN" else if (win) "PROFIT" else "MINUS",
                if (close == null && missed) Muted else result, solid = true
            )
            if (close == null && missed) {
                Text("pesan TUTUP terlewat (HP offline)", style = MaterialTheme.typography.labelSmall, color = Muted)
            }
            if (tp1 != null && !signal.isGap()) Pill("TP1 ✓", BuyColor)
            Spacer(Modifier.weight(1f))
            if (amount != null) {
                Column(horizontalAlignment = Alignment.End) {
                    Text(moneyMain(amount, money), fontWeight = FontWeight.Bold, color = result,
                        style = MaterialTheme.typography.titleMedium)
                    Text(idrLine(amount, money), style = MaterialTheme.typography.labelSmall, color = Muted)
                }
            }
        }
    }
}

@Composable
fun CloseRow(event: SignalEvent, money: MoneySettings, events: List<SignalEvent> = emptyList()) {
    if (event.isVoid()) {
        AppCard {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Pill("BATAL ${event.dir}".trim(), Muted, solid = true)
                Text(event.timeText(), style = MaterialTheme.typography.labelSmall, color = Muted)
            }
        }
        return
    }
    val amount = SignalRepository.amount(event, money)
    val win = SignalRepository.isWin(event, events)       // menang = TP1 kena, kalah = SL / TUTUP sebelum TP1
    val result = if (win) BuyColor else SellColor
    AppCard(accent = result) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(event.symbol(), fontWeight = FontWeight.Bold)
            Pill(if (win) "PROFIT" else "MINUS", result, solid = true)
            Text(
                event.timeText(), style = MaterialTheme.typography.labelSmall, color = Muted,
                modifier = Modifier.weight(1f), textAlign = TextAlign.End
            )
        }
        if (amount != null) {
            Text(moneyMain(amount, money), fontWeight = FontWeight.Bold, color = result,
                modifier = Modifier.fillMaxWidth(), textAlign = TextAlign.End)
        }
    }
}
