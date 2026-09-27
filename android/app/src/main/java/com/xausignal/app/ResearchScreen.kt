package com.xausignal.app

import androidx.compose.foundation.background
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp

/** Tab Riset: perbandingan semua metode (SMC/ICT, scalping, trend) dari backtest data asli. */
@Composable
fun ResearchTab() {
    val context = LocalContext.current
    val report = remember {
        try {
            Strategies.load(context)
        } catch (e: Exception) {
            null
        }
    }
    var filter by remember { mutableStateOf(StrategyFilter.ALL) }
    var sort by remember { mutableStateOf(StrategySort.PROFIT) }

    if (report == null) {
        Text("Data riset tidak bisa dibaca.", modifier = Modifier.padding(16.dp), color = SellColor)
        return
    }
    val shown = Strategies.select(report.items, filter, sort)

    LazyColumn(
        modifier = Modifier.fillMaxSize().padding(horizontal = 12.dp).testTag("research_list"),
        verticalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        item { Spacer(Modifier.padding(2.dp)) }
        item { ResearchSummaryCard(report) }
        item { SchemeCard(report) }
        item {
            Row(
                Modifier.horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(6.dp)
            ) {
                StrategyFilter.entries.forEach { f ->
                    FilterChip(
                        selected = filter == f, onClick = { filter = f }, label = { Text(f.label) },
                        modifier = Modifier.testTag("filter_${f.name}")
                    )
                }
            }
        }
        item {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                Text("Urutkan:", style = MaterialTheme.typography.bodySmall)
                StrategySort.entries.forEach { s ->
                    FilterChip(
                        selected = sort == s, onClick = { sort = s }, label = { Text(s.label) },
                        modifier = Modifier.testTag("sort_${s.name}")
                    )
                }
            }
        }
        item {
            Text(
                "${shown.size} strategi • R = kelipatan risiko (SL). +0,10R per trade = rata-rata untung 10% dari risiko.",
                style = MaterialTheme.typography.bodySmall,
                modifier = Modifier.testTag("research_count")
            )
        }
        if (shown.isEmpty()) item { Text("Tidak ada strategi untuk filter ini.") }
        items(shown, key = { "${it.title}|${it.scheme}" }) { StrategyCard(it) }
        item {
            Text(
                "Sumber: ${report.rule}. Data XAUUSD asli ±350 ribu candle, spread dihitung, SL dicek lebih dulu. " +
                    "Hasil masa lalu tidak menjamin masa depan. Dibuat ${report.generated}.",
                style = MaterialTheme.typography.bodySmall
            )
        }
        item { Footer() }
    }
}

@Composable
private fun ResearchSummaryCard(report: StrategyReport) {
    val passed = report.items.filter { it.pass }
    val topWin = report.highestWinRate()
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = Gold.copy(alpha = 0.15f))
    ) {
        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text("🔬 Perbandingan semua metode", fontWeight = FontWeight.Bold)
            Text(
                "${report.combos} kombinasi SMC/ICT & scalping (model × filter × TP/BE/parsial) diuji di " +
                    "2012–17, 2018–22, 2025–26: ${report.combosPass} yang untung di ketiga periode.",
                style = MaterialTheme.typography.bodySmall
            )
            Text(
                "Lolos: ${passed.joinToString { it.title }.ifBlank { "-" }}",
                color = BuyColor, fontWeight = FontWeight.Bold,
                style = MaterialTheme.typography.bodySmall
            )
            if (topWin != null) {
                Text(
                    "Win rate tertinggi: ${topWin.title} [${topWin.scheme}] ${fmt(topWin.meanWin, 1)}% " +
                        "tetapi rata-rata ${signed(topWin.meanR)}R per trade → " +
                        if (topWin.meanR > 0) "untung." else "tetap rugi.",
                    style = MaterialTheme.typography.bodySmall
                )
            }
        }
    }
}

@Composable
private fun SchemeCard(report: StrategyReport) {
    if (report.schemes.isEmpty()) return
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(2.dp)) {
            Text("Win rate vs profit (rata-rata semua model SMC & scalping)", fontWeight = FontWeight.Bold)
            Text(
                "TP kecil = win rate naik, tetapi rugi per kalah tetap 1R. Supaya impas, win rate harus di atas " +
                    "batas impas (belum termasuk spread).",
                style = MaterialTheme.typography.bodySmall
            )
            report.schemes.forEach { s ->
                val be = s.breakevenWin?.let { " • impas ≥ ${fmt(it, 0)}%" } ?: ""
                Text(
                    "${s.scheme}: win ${fmt(s.winRate, 1)}% • ${signed(s.avgR)}R$be",
                    style = MaterialTheme.typography.bodySmall,
                    color = if (s.avgR > 0) BuyColor else MaterialTheme.colorScheme.onSurface
                )
            }
        }
    }
}

@Composable
private fun StrategyCard(s: StrategyResult) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(2.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    if (s.pass) "LOLOS" else "RUGI",
                    color = Color.White,
                    fontWeight = FontWeight.Bold,
                    style = MaterialTheme.typography.labelSmall,
                    modifier = Modifier
                        .background(if (s.pass) BuyColor else SellColor, RoundedCornerShape(6.dp))
                        .padding(horizontal = 6.dp, vertical = 2.dp)
                )
                Spacer(Modifier.padding(horizontal = 4.dp))
                Text(s.title, fontWeight = FontWeight.Bold, modifier = Modifier.weight(1f))
            }
            Text("${s.kind} • ${s.timeframe} • ${s.scheme}", style = MaterialTheme.typography.bodySmall)
            Text(
                "Rata-rata: win ${fmt(s.meanWin, 1)}% • ${signed(s.meanR)}R per trade",
                fontWeight = FontWeight.Bold,
                color = if (s.meanR > 0) BuyColor else SellColor,
                style = MaterialTheme.typography.bodyMedium
            )
            s.periods.forEach { p ->
                Text(
                    "${p.period}: ${p.trades} trade • win ${fmt(p.winRate, 1)}% • ${signed(p.avgR)}R • " +
                        "total ${signed(p.totalR, 1)}R • PF ${fmt(p.profitFactor)}",
                    style = MaterialTheme.typography.bodySmall,
                    color = if (p.avgR > 0) BuyColor else MaterialTheme.colorScheme.onSurface
                )
            }
            if (s.note.isNotBlank()) Text(s.note, style = MaterialTheme.typography.labelSmall)
        }
    }
}

fun signed(value: Double, digits: Int = 2): String = (if (value > 0) "+" else "") + fmt(value, digits)
