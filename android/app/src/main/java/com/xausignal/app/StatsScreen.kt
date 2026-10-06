package com.xausignal.app

import androidx.compose.foundation.background
import androidx.compose.foundation.border
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
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
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
        item { RiwayatCard() }          // 📜 riwayat sinyal 💰 per tahun (uji data, aplikasi 3.25)
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

/** Pemilih periode bergaya segmented control (sudut ikut 🎨 Tampilan). */
@Composable
private fun Selector(options: List<String>, selected: Int, onSelect: (Int) -> Unit) {
    Row(
        Modifier
            .fillMaxWidth()
            .clip(CardShape)
            .background(CardColor)
            .border(1.dp, LineColor, CardShape)
            .padding(5.dp),
        horizontalArrangement = Arrangement.spacedBy(5.dp)
    ) {
        options.forEachIndexed { i, name ->
            Choice(name, selected == i, Modifier.weight(1f)) { onSelect(i) }
        }
    }
}

@Composable
private fun TotalCard(s: PeriodStats, money: MoneySettings) {
    val rate = if (s.total > 0) s.wins * 100 / s.total else 0
    HeroCard(color = if (s.net >= 0) BuyColor else SellColor) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(16.dp)) {
            WinGauge(s.wins, s.losses, 92.dp)
            Column(Modifier.weight(1f)) {
                CardTitle("Hasil bersih")
                Text(
                    moneyMain(s.net, money),
                    style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.ExtraBold,
                    color = if (s.net >= 0) BuyColor else SellColor, maxLines = 1
                )
                Text(idrLine(s.net, money), style = MaterialTheme.typography.bodyMedium, color = Muted)
            }
        }
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
    AppCard {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            WinGauge(s.wins, s.losses, 50.dp)
            Column(Modifier.weight(1f)) {
                Text(s.label, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.ExtraBold)
                Text(
                    "${s.total} sinyal • ${s.wins} profit • ${s.losses} minus",
                    style = MaterialTheme.typography.labelSmall, color = Muted
                )
            }
            Column(horizontalAlignment = Alignment.End) {
                Text(
                    moneyMain(s.net, money), fontWeight = FontWeight.ExtraBold,
                    style = MaterialTheme.typography.titleSmall,
                    color = if (s.net >= 0) BuyColor else SellColor
                )
                Text(idrLine(s.net, money), style = MaterialTheme.typography.labelSmall, color = Muted)
            }
        }
        MetricRow {
            Metric("Total profit", moneyMain(s.profit, money), BuyColor, compact = true)
            Metric("Total minus", moneyMain(s.loss, money), SellColor, compact = true)
        }
    }
}


/** Angka teruji (cloud/api/riwayat.json lewat GET /api/chat?riwayat=1), dimuat sekali per sesi aplikasi. */
object Verified {
    var data by androidx.compose.runtime.mutableStateOf<org.json.JSONObject?>(null)
    suspend fun load() {
        if (data == null) data = kotlinx.coroutines.withContext(kotlinx.coroutines.Dispatchers.IO) { ChatClient.riwayat() }
    }
}

/**
 * 📜 Hasil teruji sinyal 💰 (aplikasi 3.26): replay kode cloud asli 2012–2026 dengan filter & spread asli Exness
 * (research/verifikasi.py). Ringkas: tahun ini, 365 hari, sejak Okt 2021, sebelum Okt 2021, per kategori.
 */
@Composable
private fun RiwayatCard() {
    androidx.compose.runtime.LaunchedEffect(Unit) { Verified.load() }
    AppCard {
        Text("📜 Hasil teruji sinyal 💰", fontWeight = FontWeight.Bold)
        val d = Verified.data
        if (d == null) {
            Text("Memuat… (butuh cloud terbaru)", color = Muted, style = MaterialTheme.typography.labelSmall)
            return@AppCard
        }
        Text("Kode cloud diuji ulang di data lama, spread asli Exness. +10R ≈ +5% modal (lot aplikasi).",
            style = MaterialTheme.typography.labelSmall, color = Muted)
        for (key in listOf("XAU", "BTC")) {
            val a = d.optJSONObject(key) ?: continue
            Text("$key/USD", fontWeight = FontWeight.Bold, style = MaterialTheme.typography.bodySmall,
                modifier = Modifier.padding(top = 8.dp))
            val year = a.optString("sampai").take(4)
            RiwayatRow(year, a.optJSONObject("tahun")?.optJSONObject(year))
            RiwayatRow("365 hari", a.optJSONObject("365h"))
            RiwayatRow("Sejak Okt 2021", a.optJSONObject("baru"))
            RiwayatRow("Sebelum 2021", a.optJSONObject("lama"))
            val kat = a.optJSONObject("kat") ?: continue
            val cats = kat.keys().asSequence().toList()
                .sortedByDescending { kat.optJSONObject(it)?.optJSONObject("baru")?.optInt("n") ?: 0 }
            for (c in cats) RiwayatRow("• $c", kat.optJSONObject(c)?.optJSONObject("baru"))
        }
    }
}

@Composable
private fun RiwayatRow(label: String, c: org.json.JSONObject?) {
    if (c == null || c.optInt("n") == 0) return
    val tot = c.optDouble("tot")
    Row(Modifier.fillMaxWidth()) {
        Text(label, Modifier.weight(1.3f), style = MaterialTheme.typography.labelSmall)
        Text("${c.optInt("n")}×", Modifier.weight(0.6f), style = MaterialTheme.typography.labelSmall, color = Muted)
        Text("WR %.0f%%".format(c.optDouble("wr")), Modifier.weight(0.8f), style = MaterialTheme.typography.labelSmall)
        Text("%+.2fR".format(c.optDouble("avg")).replace('.', ','), Modifier.weight(0.8f),
            style = MaterialTheme.typography.labelSmall, color = Muted)
        Text("%+.0fR".format(tot), Modifier.weight(0.7f), textAlign = TextAlign.End,
            fontWeight = FontWeight.Bold, color = if (tot >= 0) BuyColor else SellColor,
            style = MaterialTheme.typography.labelSmall)
    }
}
