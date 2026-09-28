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
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
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

/** Tab Sinyal: harga semua pair, sinyal aktif, ringkasan, riwayat. */
@Composable
fun SignalsTab(events: List<SignalEvent>, prices: Map<String, SignalEvent>, connection: String, money: MoneySettings) {
    val signalIds = events.filter { it.type == "signal" }.map { it.id }.toSet()
    val history = events.filter { it.type == "signal" || (it.type == "close" && it.id !in signalIds) }
    val open = SignalRepository.openSignals(events)
    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(horizontal = 16.dp, vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        item { TickerCard(prices, connection) }
        item { SectionTitle("Aktif", trailing = if (open.isEmpty()) null else "${open.size}") }
        if (open.isEmpty()) {
            item { AppCard { Text("Menunggu sinyal 💰", color = Muted) } }
        } else {
            items(open, key = { "open-" + it.msgId }) {
                OpenSignalCard(it, prices[it.symbol()], SignalRepository.slPlusActive(events, it.id), money)
            }
        }
        item { TodayCard(events, money) }
        if (history.isNotEmpty()) item { SectionTitle("Riwayat") }
        items(history, key = { it.msgId }) {
            if (it.type == "signal") SignalResultCard(it, events, money) else CloseRow(it, money)
        }
        item { Footer() }
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
    }
}

/** Simbol + arah + waktu, lalu 💰 (profit) ★ (win rate) dan chip WR / R historis. */
@Composable
private fun SignalHeader(signal: SignalEvent) {
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(signal.symbol(), style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
        Pill(signal.dir, dirColor(signal.dir), solid = true)
        Spacer(Modifier.weight(1f))
        Text(signal.timeText(), style = MaterialTheme.typography.labelSmall, color = Muted)
    }
    val m = signal.moneyBadge()
    val st = signal.stars()
    if (m > 0 || st > 0 || signal.json.has("wr")) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            if (m > 0) Text("💰".repeat(m))
            if (st > 0) Text("★".repeat(st), color = Gold, fontWeight = FontWeight.Bold)
            Spacer(Modifier.weight(1f))
            if (signal.json.has("wr")) {
                val avg = signal.json.optDouble("avg_r")
                Pill("${signed(avg)}R", if (avg > 0) BuyColor else SellColor)
                Pill("WR ${fmt(signal.json.optDouble("wr"), 0)}%", Gold)
            }
        }
    }
}

private fun SignalEvent.isGap(): Boolean = str("mode") == "gap"

@Composable
fun OpenSignalCard(signal: SignalEvent, hb: SignalEvent?, slPlus: Boolean, money: MoneySettings) {
    val entry = signal.num("entry")
    val price = hb?.num("price")
    val sign = if (signal.dir == "BUY") 1 else -1
    val floating = if (entry != null && price != null) (price - entry) * sign else null
    AppCard(accent = dirColor(signal.dir)) {
        SignalHeader(signal)
        Row(verticalAlignment = Alignment.Bottom) {
            Text(
                signal.price("entry"), style = MaterialTheme.typography.headlineMedium,
                fontWeight = FontWeight.Bold, modifier = Modifier.weight(1f)
            )
            if (floating != null) {
                Text(
                    (if (floating > 0) "+" else "") + priceText(signal.symbol(), floating),
                    style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold,
                    color = if (floating >= 0) BuyColor else SellColor
                )
            }
        }
        MetricRow {
            Metric("SL", signal.price("sl"), SellColor, compact = true)
            Metric(if (signal.isGap()) "TP" else "TP1", signal.price("tp1"), BuyColor, compact = true)
            Metric("Lot", legsLot(signal, money), Gold, compact = true)
        }
        if (slPlus) Text("🛡️ SL+ aktif", color = BuyColor, fontWeight = FontWeight.Bold)
    }
}

fun weekKey(t: ZonedDateTime): String =
    t.toLocalDate().with(TemporalAdjusters.previousOrSame(DayOfWeek.MONDAY)).toString()

@Composable
fun TodayCard(events: List<SignalEvent>, money: MoneySettings) {
    val today = LocalDate.now(ZoneId.of("Asia/Jakarta"))
    val day = SignalRepository.periodStats(events, money, { it.toLocalDate().toString() })
        .firstOrNull { it.label == today.toString() }
    val week = SignalRepository.periodStats(events, money, ::weekKey)
        .firstOrNull { it.label == today.with(TemporalAdjusters.previousOrSame(DayOfWeek.MONDAY)).toString() }
    val month = SignalRepository.periodStats(events, money, { it.toLocalDate().toString().substring(0, 7) })
        .firstOrNull { it.label == today.toString().substring(0, 7) }
    AppCard {
        SummaryLine("Hari ini", day, money)
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
                Text("${s.wins}W • ${s.losses}L", style = MaterialTheme.typography.labelSmall, color = Muted)
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

/** "5 × 0.02": jumlah posisi × lot pilihanmu. */
fun legsLot(signal: SignalEvent, money: MoneySettings): String =
    "${signal.num("legs")?.toInt() ?: 5} × ${lotText(money.lotFor(signal.isStar()))}"

/** Riwayat satu sinyal: entry → tutup → MENANG/KALAH + uang. */
@Composable
fun SignalResultCard(signal: SignalEvent, events: List<SignalEvent>, money: MoneySettings) {
    if (signal.isVoid()) {
        AppCard {
            SignalHeader(signal)
            Pill("BATAL", Muted, solid = true)
        }
        return
    }
    val tp1 = SignalRepository.tp1Event(events, signal.id)
    val close = SignalRepository.closeEvent(events, signal.id)
    val amount = close?.let { SignalRepository.amount(it, money) }
    val win = close != null && (amount ?: close.num("r") ?: 0.0) > 0
    val result = if (close == null) Gold else if (win) BuyColor else SellColor
    AppCard(accent = result) {
        SignalHeader(signal)
        MetricRow {
            Metric("Entry", signal.price("entry"), compact = true)
            Metric("Tutup", close?.price("price") ?: "-", compact = true)
            Metric("Waktu tutup", close?.timeText()?.removeSuffix(" WIB") ?: "-", compact = true)
        }
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Pill(if (close == null) "BERJALAN" else if (win) "MENANG" else "KALAH", result, solid = true)
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
fun CloseRow(event: SignalEvent, money: MoneySettings) {
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
    val win = (amount ?: event.num("r") ?: 0.0) > 0
    val result = if (win) BuyColor else SellColor
    AppCard(accent = result) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(event.symbol(), fontWeight = FontWeight.Bold)
            Pill(if (win) "MENANG" else "KALAH", result, solid = true)
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
