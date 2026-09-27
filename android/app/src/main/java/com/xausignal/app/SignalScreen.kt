package com.xausignal.app

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
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

/** Tab Sinyal: harga & koneksi, sinyal aktif, ringkasan hari/minggu/bulan, riwayat. */
@Composable
fun SignalsTab(events: List<SignalEvent>, heartbeat: SignalEvent?, connection: String, money: MoneySettings) {
    val history = events.filter { it.type == "signal" || it.type == "close" || it.type == "info" }
    val open = SignalRepository.openSignals(events)
    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(horizontal = 16.dp, vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        item { MarketCard(heartbeat, connection) }
        item { SectionTitle("Sinyal aktif", trailing = if (open.isEmpty()) null else "${open.size} set") }
        if (open.isEmpty()) {
            item {
                AppCard {
                    Text("Belum ada posisi sinyal", fontWeight = FontWeight.Bold)
                    Text(
                        "Tunggu sinyal BUY/SELL berikutnya. Notifikasi akan berbunyi saat sinyal masuk.",
                        style = MaterialTheme.typography.bodyMedium, color = Muted
                    )
                }
            }
        } else {
            items(open, key = { "open-" + it.msgId }) {
                OpenSignalCard(it, heartbeat, SignalRepository.slPlusActive(events, it.id))
            }
        }
        item { TodayCard(events, money) }
        item { SectionTitle("Riwayat sinyal", trailing = if (history.isEmpty()) null else "${history.size}") }
        if (history.isEmpty()) {
            item {
                NoteBox("Belum ada sinyal. Pastikan bot/cloud berjalan dan topik di Pengaturan sudah benar.")
            }
        }
        items(history, key = { it.msgId }) { EventRow(it, money) }
        item { Footer() }
    }
}

@Composable
fun MarketCard(heartbeat: SignalEvent?, connection: String) {
    val online = connection == "Terhubung"
    AppCard {
        Row(verticalAlignment = Alignment.CenterVertically) {
            StatusDot(if (online) BuyColor else SellColor)
            Text(
                connection, style = MaterialTheme.typography.labelLarge,
                color = if (online) BuyColor else SellColor,
                modifier = Modifier.padding(start = 8.dp).weight(1f), maxLines = 2
            )
            if (heartbeat != null) {
                Text(heartbeat.timeText(), style = MaterialTheme.typography.labelMedium, color = Muted)
            }
        }
        if (heartbeat == null) {
            Text("Menunggu data dari bot...", style = MaterialTheme.typography.bodyMedium, color = Muted)
            return@AppCard
        }
        Column {
            Text(heartbeat.str("symbol").ifBlank { "XAUUSD" }, style = MaterialTheme.typography.labelLarge, color = Muted)
            Text(
                fmt(heartbeat.num("price")),
                style = MaterialTheme.typography.displaySmall,
                fontWeight = FontWeight.Bold,
            )
        }
        val currency = heartbeat.str("currency")
        heartbeat.num("balance")?.let { balance ->
            MetricRow {
                Metric("Saldo $currency", fmt(balance))
                Metric("Equity $currency", fmt(heartbeat.num("equity")))
            }
        }
        KeyValue("Mode", heartbeat.str("mode").ifBlank { "-" }, Gold, bold = true)
        heartbeat.num("spread")?.let { KeyValue("Spread", fmt(it)) }
        val trend = heartbeat.str("trend")
        if (trend.isNotBlank()) Text(trend, style = MaterialTheme.typography.bodySmall, color = Muted)
        val block = heartbeat.str("block")
        if (block.isNotBlank()) NoteBox("Entry diblokir: $block", SellColor)
    }
}

@Composable
fun OpenSignalCard(signal: SignalEvent, heartbeat: SignalEvent?, slPlus: Boolean) {
    val color = dirColor(signal.dir)
    val entry = signal.num("entry")
    val price = heartbeat?.num("price")
    val sign = if (signal.dir == "BUY") 1 else -1
    val floating = if (entry != null && price != null) (price - entry) * sign else null
    AppCard(accent = color) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Pill(signal.dir, color, solid = true)
            val set = signal.str("set")
            if (set.isNotBlank()) Pill("Set $set", Muted)
            Text(
                signal.timeText(), style = MaterialTheme.typography.labelMedium, color = Muted,
                modifier = Modifier.weight(1f), textAlign = TextAlign.End
            )
        }
        Row(verticalAlignment = Alignment.Bottom) {
            Column(Modifier.weight(1f)) {
                Text("Entry", style = MaterialTheme.typography.labelMedium, color = Muted)
                Text(fmt(entry), style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
            }
            if (floating != null) {
                Column(horizontalAlignment = Alignment.End) {
                    Text("Berjalan", style = MaterialTheme.typography.labelMedium, color = Muted)
                    Text(
                        "${signed(floating)} poin",
                        style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold,
                        color = if (floating >= 0) BuyColor else SellColor
                    )
                }
            }
        }
        MetricRow {
            Metric("Stop loss", fmt(signal.num("sl")), SellColor)
            Metric("TP1 (posisi #1)", fmt(signal.num("tp1")), BuyColor)
        }
        KeyValue("Lot", signal.str("lot").ifBlank { "-" }, bold = true)
        NoteBox(
            if (slPlus) "SL+ aktif: SL posisi sisa sudah di entry (aman impas)."
            else "Tunggu TP1, lalu SL posisi sisa dipindah ke entry (SL+).",
            if (slPlus) BuyColor else Gold
        )
        val warning = signal.str("warning")
        if (warning.isNotBlank()) NoteBox(warning, SellColor)
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
        Row(verticalAlignment = Alignment.CenterVertically) {
            CardTitle("Ringkasan hasil", Modifier.weight(1f))
            Pill("${money.currency} • ${lotText(money.legLot)} lot", Gold)
        }
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
            Text(label, style = MaterialTheme.typography.bodyLarge, fontWeight = FontWeight.Medium)
            Text(
                if (s == null) "Belum ada sinyal selesai" else "${s.wins} menang • ${s.losses} kalah",
                style = MaterialTheme.typography.bodySmall, color = Muted
            )
        }
        if (s != null) {
            Column(horizontalAlignment = Alignment.End) {
                Text(
                    moneyMain(s.net, money), fontWeight = FontWeight.Bold,
                    color = if (s.net >= 0) BuyColor else SellColor
                )
                Text(idrLine(s.net, money), style = MaterialTheme.typography.bodySmall, color = Muted)
            }
        }
    }
}

@Composable
fun EventRow(event: SignalEvent, money: MoneySettings) {
    when (event.type) {
        "signal" -> SignalRow(event)
        "close" -> CloseRow(event, money)
        else -> AppCard {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Pill("INFO", Muted)
                Text(
                    event.timeText(), style = MaterialTheme.typography.labelMedium, color = Muted,
                    modifier = Modifier.weight(1f), textAlign = TextAlign.End
                )
            }
            Text(event.str("text"), style = MaterialTheme.typography.bodyMedium)
        }
    }
}

@Composable
private fun SignalRow(event: SignalEvent) {
    val color = dirColor(event.dir)
    AppCard {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Pill(event.dir, color, solid = true)
            val (statusText, statusColor) = when (event.status) {
                "skipped" -> "Dilewati" to Muted
                "opened" -> "Order terbuka" to BuyColor
                "failed" -> "Order gagal" to SellColor
                else -> "Sinyal" to Gold
            }
            Pill(statusText, statusColor)
            Text(
                event.timeText(), style = MaterialTheme.typography.labelMedium, color = Muted,
                modifier = Modifier.weight(1f), textAlign = TextAlign.End
            )
        }
        MetricRow {
            Metric("Entry", fmt(event.num("entry")), compact = true)
            Metric("SL", fmt(event.num("sl")), SellColor, compact = true)
            Metric("TP1", fmt(event.num("tp1")), BuyColor, compact = true)
        }
        val set = event.str("set")
        if (set.isNotBlank()) KeyValue("Set", set)
        KeyValue("Lot", event.str("lot").ifBlank { "-" })
        val note = event.str("note")
        if ((event.status == "skipped" || event.status == "failed") && note.isNotBlank()) {
            Text(note, style = MaterialTheme.typography.bodySmall, color = SellColor)
        }
        val reason = event.str("reason")
        if (reason.isNotBlank()) Text(reason, style = MaterialTheme.typography.bodySmall, color = Muted)
    }
}

@Composable
private fun CloseRow(event: SignalEvent, money: MoneySettings) {
    val amount = SignalRepository.amount(event, money)
    val win = (amount ?: event.num("r") ?: 0.0) > 0
    val result = if (win) BuyColor else SellColor
    AppCard(accent = result) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Pill("TUTUP ${event.dir}".trim(), dirColor(event.dir), solid = true)
            Pill(if (win) "MENANG" else "KALAH", result)
            Text(
                event.timeText(), style = MaterialTheme.typography.labelMedium, color = Muted,
                modifier = Modifier.weight(1f), textAlign = TextAlign.End
            )
        }
        Row(verticalAlignment = Alignment.Bottom) {
            Column(Modifier.weight(1f)) {
                Text("Ditutup @ ${fmt(event.num("price"))}", style = MaterialTheme.typography.bodyMedium)
                Text(
                    "${signed(event.num("points") ?: 0.0)} poin • ${signed(event.num("r") ?: 0.0)}R",
                    style = MaterialTheme.typography.bodySmall, color = Muted
                )
            }
            if (amount != null) {
                Column(horizontalAlignment = Alignment.End) {
                    Text(
                        moneyMain(amount, money), style = MaterialTheme.typography.titleLarge,
                        fontWeight = FontWeight.Bold, color = result
                    )
                    Text(idrLine(amount, money), style = MaterialTheme.typography.bodySmall, color = Muted)
                }
            }
        }
        val reason = event.str("reason")
        if (reason.isNotBlank()) Text(reason, style = MaterialTheme.typography.bodySmall, color = Muted)
    }
}
