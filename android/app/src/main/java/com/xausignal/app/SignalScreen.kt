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

/** Tab Sinyal: harga, sinyal aktif, ringkasan, riwayat. */
@Composable
fun SignalsTab(events: List<SignalEvent>, heartbeat: SignalEvent?, connection: String, money: MoneySettings) {
    val history = events.filter {
        it.type == "signal" || it.type == "close" || (it.type == "info" && it.str("text").contains("TP1"))
    }
    val open = SignalRepository.openSignals(events)
    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(horizontal = 16.dp, vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        item { MarketCard(heartbeat, connection) }
        item { SectionTitle("Sinyal aktif") }
        if (open.isEmpty()) {
            item { AppCard { Text("Belum ada sinyal", color = Muted) } }
        } else {
            items(open, key = { "open-" + it.msgId }) {
                OpenSignalCard(it, heartbeat, SignalRepository.slPlusActive(events, it.id))
            }
        }
        item { TodayCard(events, money) }
        if (history.isNotEmpty()) item { SectionTitle("Riwayat") }
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
                if (online) "XAU/USD" else connection, style = MaterialTheme.typography.labelLarge,
                color = if (online) Muted else SellColor,
                modifier = Modifier.padding(start = 8.dp).weight(1f), maxLines = 1
            )
            if (heartbeat != null) {
                Text(heartbeat.timeText(), style = MaterialTheme.typography.labelMedium, color = Muted)
            }
        }
        Text(
            fmt(heartbeat?.num("price")),
            style = MaterialTheme.typography.displaySmall,
            fontWeight = FontWeight.Bold,
        )
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
        SignalHeader(signal)
        Row(verticalAlignment = Alignment.Bottom) {
            Column(Modifier.weight(1f)) {
                Text("Entry", style = MaterialTheme.typography.labelMedium, color = Muted)
                Text(fmt(entry), style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
            }
            if (floating != null) {
                Text(
                    "${signed(floating)} poin",
                    style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold,
                    color = if (floating >= 0) BuyColor else SellColor
                )
            }
        }
        MetricRow {
            Metric("SL", fmt(signal.num("sl")), SellColor, compact = true)
            Metric("TP1", fmt(signal.num("tp1")), BuyColor, compact = true)
            Metric("Lot", signal.str("lot").ifBlank { "-" }, compact = true)
        }
        if (slPlus) Text("🛡️ SL+ aktif", color = BuyColor, fontWeight = FontWeight.Bold)
    }
}

/** Baris atas kartu sinyal: arah, ⭐, waktu. */
@Composable
private fun SignalHeader(signal: SignalEvent) {
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        Pill(signal.dir, dirColor(signal.dir), solid = true)
        if (signal.json.optBoolean("star", false)) Pill("⭐", Gold)
        Text(
            signal.timeText(), style = MaterialTheme.typography.labelMedium, color = Muted,
            modifier = Modifier.weight(1f), textAlign = TextAlign.End
        )
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
            CardTitle("Ringkasan", Modifier.weight(1f))
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
                if (s == null) "-" else "${s.wins} menang • ${s.losses} kalah",
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
        "signal" -> AppCard {
            SignalHeader(event)
            MetricRow {
                Metric("Entry", fmt(event.num("entry")), compact = true)
                Metric("SL", fmt(event.num("sl")), SellColor, compact = true)
                Metric("TP1", fmt(event.num("tp1")), BuyColor, compact = true)
            }
        }
        "close" -> CloseRow(event, money)
        else -> AppCard {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Pill("TP1", BuyColor)
                Text("SL+ ke entry", style = MaterialTheme.typography.bodyMedium, modifier = Modifier.weight(1f))
                Text(event.timeText(), style = MaterialTheme.typography.labelMedium, color = Muted)
            }
        }
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
            Text(
                "@ ${fmt(event.num("price"))}", style = MaterialTheme.typography.bodyMedium, color = Muted,
                modifier = Modifier.weight(1f)
            )
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
    }
}
