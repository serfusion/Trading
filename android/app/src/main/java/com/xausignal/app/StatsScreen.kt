package com.xausignal.app

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import java.time.LocalDate
import java.time.format.DateTimeFormatter
import java.util.Locale

/** Tab Statistik: menang/kalah & profit/rugi per hari, minggu, bulan (mata uang akun + Rupiah). */
@Composable
fun StatsTab(events: List<SignalEvent>, money: MoneySettings) {
    var period by remember { mutableIntStateOf(0) }
    var kind by remember { mutableIntStateOf(0) }
    val symbols = remember(events) {
        listOf("Semua") + events.filter { it.type == "close" }.map { it.symbol() }.distinct().sorted()
    }
    val symbol: String? = symbols.getOrNull(kind)?.takeIf { kind > 0 }
    val star: Boolean? = null
    val idFmt = DateTimeFormatter.ofPattern("dd MMM yyyy", Locale("id"))
    val stats = remember(events, money, period, symbol) { when (period) {
        0 -> SignalRepository.periodStats(events, money, { it.toLocalDate().toString() },
            { LocalDate.parse(it).format(idFmt) }, star, symbol)
        1 -> SignalRepository.periodStats(events, money, ::weekKey,
            { "Minggu " + LocalDate.parse(it).format(idFmt) }, star, symbol)
        else -> SignalRepository.periodStats(events, money, { it.toLocalDate().toString().substring(0, 7) },
            { LocalDate.parse("$it-01").format(DateTimeFormatter.ofPattern("MMMM yyyy", Locale("id"))) }, star, symbol)
    } }
    val all = stats.fold(PeriodStats("Total", 0, 0, 0.0, 0.0)) { acc, s ->
        PeriodStats("Total", acc.wins + s.wins, acc.losses + s.losses, acc.profit + s.profit, acc.loss + s.loss)
    }
    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(horizontal = 16.dp, vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        if (symbols.size > 2) item { SymbolChips(symbols, kind) { kind = it } }
        item { Selector(listOf("Harian", "Mingguan", "Bulanan"), period) { period = it } }
        item { TotalCard(all, money) }
        item {
            SectionTitle(
                listOf("Per hari", "Per minggu", "Per bulan")[period],
                trailing = if (stats.isEmpty()) null else "${stats.size} periode"
            )
        }
        if (stats.isEmpty()) {
            item { AppCard { Text("Belum ada sinyal selesai", color = Muted) } }
        }
        items(stats, key = { it.label }) { PeriodCard(it, money) }
        item { Footer() }
    }
}

/** Pilihan pair yang bisa digeser ke samping. */
@Composable
private fun SymbolChips(options: List<String>, selected: Int, onSelect: (Int) -> Unit) {
    Row(
        Modifier.horizontalScroll(androidx.compose.foundation.rememberScrollState()),
        horizontalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        options.forEachIndexed { i, name ->
            androidx.compose.material3.FilterChip(
                selected = selected == i, onClick = { onSelect(i) },
                label = { Text(name.replace("/", ""), fontWeight = FontWeight.Medium) }
            )
        }
    }
}

/** Pemilih periode bergaya segmented control. */
@Composable
private fun Selector(options: List<String>, selected: Int, onSelect: (Int) -> Unit) {
    Row(
        Modifier
            .fillMaxWidth()
            .background(CardColor, RoundedCornerShape(14.dp))
            .padding(4.dp)
    ) {
        options.forEachIndexed { i, name ->
            val on = selected == i
            Text(
                name,
                textAlign = TextAlign.Center,
                fontWeight = if (on) FontWeight.Bold else FontWeight.Medium,
                color = if (on) MaterialTheme.colorScheme.onPrimary else Muted,
                modifier = Modifier
                    .weight(1f)
                    .background(if (on) Gold else CardColor, RoundedCornerShape(10.dp))
                    .clickable { onSelect(i) }
                    .padding(vertical = 10.dp)
            )
        }
    }
}

@Composable
private fun TotalCard(s: PeriodStats, money: MoneySettings) {
    val rate = if (s.total > 0) s.wins * 100 / s.total else 0
    AppCard(accent = Gold) {
        CardTitle("Total")
        Column {
            Text("Hasil bersih", style = MaterialTheme.typography.labelMedium, color = Muted)
            Text(
                moneyMain(s.net, money),
                style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold,
                color = if (s.net >= 0) BuyColor else SellColor
            )
            Text(idrLine(s.net, money), style = MaterialTheme.typography.bodyMedium, color = Muted)
        }
        WinBar(s.wins, s.losses)
        MetricRow {
            Metric("Sinyal", "${s.total}", compact = true)
            Metric("Profit", "${s.wins}", BuyColor, compact = true)
            Metric("Minus", "${s.losses}", SellColor, compact = true)
            Metric("Win rate", "$rate%", Gold, compact = true)
        }
        KeyValue("Total profit", moneyMain(s.profit, money), BuyColor, bold = true)
        KeyValue("Total minus", moneyMain(s.loss, money), SellColor, bold = true)
    }
}

@Composable
private fun PeriodCard(s: PeriodStats, money: MoneySettings) {
    val rate = if (s.total > 0) s.wins * 100 / s.total else 0
    AppCard {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text(s.label, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                Text(
                    "${s.total} sinyal • ${s.wins} profit • ${s.losses} minus • WR $rate%",
                    style = MaterialTheme.typography.bodySmall, color = Muted
                )
            }
            Column(horizontalAlignment = Alignment.End) {
                Text(
                    moneyMain(s.net, money), fontWeight = FontWeight.Bold,
                    style = MaterialTheme.typography.titleMedium,
                    color = if (s.net >= 0) BuyColor else SellColor
                )
                Text(idrLine(s.net, money), style = MaterialTheme.typography.bodySmall, color = Muted)
            }
        }
        WinBar(s.wins, s.losses)
        MetricRow {
            Metric("Total profit", moneyMain(s.profit, money), BuyColor)
            Metric("Total minus", moneyMain(s.loss, money), SellColor)
        }
    }
}
