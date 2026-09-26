package com.xausignal.app

import android.Manifest
import android.content.Intent
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Tab
import androidx.compose.material3.TabRow
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import java.time.DayOfWeek
import java.time.LocalDate
import java.time.format.DateTimeFormatter
import java.time.temporal.TemporalAdjusters
import java.util.Locale

private val BuyColor = Color(0xFF1FAA59)
private val SellColor = Color(0xFFE5484D)
private val Gold = Color(0xFFD4A017)
const val BRAND = "by: Superfal-Dev"

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        SignalRepository.init(this)
        startSignalService()
        setContent {
            XauTheme {
                AppScreen(onSettingsSaved = { restartSignalService() })
            }
        }
    }

    private fun startSignalService() {
        ContextCompat.startForegroundService(this, Intent(this, SignalService::class.java))
    }

    private fun restartSignalService() {
        stopService(Intent(this, SignalService::class.java))
        startSignalService()
    }
}

@Composable
fun XauTheme(content: @Composable () -> Unit) {
    val scheme = if (isSystemInDarkTheme()) {
        darkColorScheme(primary = Gold, secondary = Gold)
    } else {
        lightColorScheme(primary = Color(0xFF9A7200), secondary = Color(0xFF9A7200))
    }
    MaterialTheme(colorScheme = scheme, content = content)
}

fun idrText(value: Double): String = "Rp" + String.format(Locale("id", "ID"), "%,.0f", value)

fun moneyText(value: Double, m: MoneySettings): String {
    val sign = if (value > 0) "+" else ""
    return "$sign${fmt(value)} ${m.currency} (${if (value > 0) "+" else ""}${idrText(SignalRepository.toIdr(value, m))})"
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AppScreen(onSettingsSaved: () -> Unit) {
    val events by SignalRepository.events.collectAsState()
    val heartbeat by SignalRepository.heartbeat.collectAsState()
    val connection by SignalRepository.connection.collectAsState()
    val moneyVersion by SignalRepository.moneyVersion.collectAsState()
    var showSettings by remember { mutableStateOf(SignalRepository.topic().isBlank()) }
    var tab by remember { mutableIntStateOf(0) }
    val money = remember(moneyVersion) { SignalRepository.money() }

    val permission = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) {}
    LaunchedEffect(Unit) {
        if (Build.VERSION.SDK_INT >= 33) permission.launch(Manifest.permission.POST_NOTIFICATIONS)
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text("XAU Signal", fontWeight = FontWeight.Bold)
                        Text(BRAND, style = MaterialTheme.typography.labelSmall, color = Gold)
                    }
                },
                actions = {
                    IconButton(onClick = { showSettings = true }) {
                        Icon(Icons.Filled.Settings, contentDescription = "Pengaturan")
                    }
                }
            )
        }
    ) { padding ->
        Column(Modifier.fillMaxSize().padding(padding)) {
            TabRow(selectedTabIndex = tab) {
                Tab(selected = tab == 0, onClick = { tab = 0 }, text = { Text("Sinyal") })
                Tab(selected = tab == 1, onClick = { tab = 1 }, text = { Text("Statistik") })
            }
            if (tab == 0) SignalsTab(events, heartbeat, connection, money) else StatsTab(events, money)
        }
    }

    if (showSettings) {
        SettingsDialog(
            onDismiss = { showSettings = false },
            onSave = { server, topic, m ->
                SignalRepository.saveSettings(server, topic)
                SignalRepository.saveMoney(m)
                showSettings = false
                onSettingsSaved()
            }
        )
    }
}

@Composable
fun SignalsTab(events: List<SignalEvent>, heartbeat: SignalEvent?, connection: String, money: MoneySettings) {
    val history = events.filter { it.type == "signal" || it.type == "close" || it.type == "info" }
    val open = SignalRepository.openSignals(events)
    LazyColumn(
        modifier = Modifier.fillMaxSize().padding(horizontal = 12.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        item { Spacer(Modifier.padding(2.dp)) }
        item { StatusCard(heartbeat, connection) }
        if (open.isEmpty()) {
            item { OpenSignalCard(null, heartbeat, false) }
        } else {
            items(open, key = { "open-" + it.msgId }) {
                OpenSignalCard(it, heartbeat, SignalRepository.slPlusActive(events, it.id))
            }
        }
        item { TodayCard(events, money) }
        item {
            Text("Riwayat sinyal", style = MaterialTheme.typography.titleMedium,
                modifier = Modifier.padding(top = 8.dp))
        }
        if (history.isEmpty()) {
            item { Text("Belum ada sinyal. Pastikan bot/cloud berjalan dan topik sudah benar.") }
        }
        items(history, key = { it.msgId }) { EventRow(it, money) }
        item { Footer() }
    }
}

@Composable
fun Footer() {
    Text(
        "XAU Signal $BRAND",
        style = MaterialTheme.typography.labelSmall,
        color = Gold,
        modifier = Modifier.fillMaxWidth().padding(vertical = 16.dp)
    )
}

@Composable
fun StatusCard(heartbeat: SignalEvent?, connection: String) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(14.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text("● ", color = if (connection == "Terhubung") BuyColor else SellColor)
                Text(connection, style = MaterialTheme.typography.bodyMedium)
            }
            if (heartbeat == null) {
                Text("Menunggu data dari bot...", style = MaterialTheme.typography.bodySmall)
                return@Column
            }
            Text(
                "${heartbeat.str("symbol")}  ${fmt(heartbeat.num("price"))}",
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold
            )
            heartbeat.num("balance")?.let {
                val currency = heartbeat.str("currency")
                Text("Saldo ${fmt(it)} $currency • Equity ${fmt(heartbeat.num("equity"))} $currency")
            }
            Text("Mode: ${heartbeat.str("mode")} • Spread ${fmt(heartbeat.num("spread"))}")
            val block = heartbeat.str("block")
            if (block.isNotBlank()) Text("Blokir entry: $block", color = SellColor)
            Text("Update ${heartbeat.timeText()}", style = MaterialTheme.typography.bodySmall)
        }
    }
}

@Composable
fun OpenSignalCard(signal: SignalEvent?, heartbeat: SignalEvent?, slPlus: Boolean) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = when (signal?.dir) {
                "BUY" -> BuyColor.copy(alpha = 0.18f)
                "SELL" -> SellColor.copy(alpha = 0.18f)
                else -> MaterialTheme.colorScheme.surfaceVariant
            }
        )
    ) {
        Column(Modifier.padding(14.dp)) {
            Text("Posisi sinyal aktif ${signal?.str("set") ?: ""}", style = MaterialTheme.typography.titleSmall)
            if (signal == null) {
                Text("Tidak ada. Tunggu sinyal BUY/SELL berikutnya.")
                return@Column
            }
            val entry = signal.num("entry")
            val price = heartbeat?.num("price")
            val sign = if (signal.dir == "BUY") 1 else -1
            val floating = if (entry != null && price != null) (price - entry) * sign else null
            Text(
                "${signal.dir} @ ${fmt(entry)}",
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold,
                color = if (signal.dir == "BUY") BuyColor else SellColor
            )
            Text("SL ${fmt(signal.num("sl"))} • TP1 ${fmt(signal.num("tp1"))} (posisi #1)")
            Text("Lot ${signal.str("lot").ifBlank { "-" }} • ${signal.timeText()}")
            Text(
                if (slPlus) "🛡️ SL+ aktif: SL posisi sisa di entry" else "Tunggu TP1 lalu pindahkan SL ke entry",
                color = if (slPlus) BuyColor else MaterialTheme.colorScheme.onSurface
            )
            if (floating != null) {
                Text(
                    "Berjalan: ${fmt(floating)} poin",
                    color = if (floating >= 0) BuyColor else SellColor,
                    fontWeight = FontWeight.Bold
                )
            }
            val warning = signal.str("warning")
            if (warning.isNotBlank()) Text(warning, style = MaterialTheme.typography.bodySmall)
        }
    }
}

private fun weekKey(t: java.time.ZonedDateTime): String =
    t.toLocalDate().with(TemporalAdjusters.previousOrSame(DayOfWeek.MONDAY)).toString()

@Composable
fun TodayCard(events: List<SignalEvent>, money: MoneySettings) {
    val today = LocalDate.now(java.time.ZoneId.of("Asia/Jakarta"))
    val day = SignalRepository.periodStats(events, money, { it.toLocalDate().toString() })
        .firstOrNull { it.label == today.toString() }
    val week = SignalRepository.periodStats(events, money, ::weekKey)
        .firstOrNull { it.label == today.with(TemporalAdjusters.previousOrSame(DayOfWeek.MONDAY)).toString() }
    val month = SignalRepository.periodStats(events, money, { it.toLocalDate().toString().substring(0, 7) })
        .firstOrNull { it.label == today.toString().substring(0, 7) }
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text("Ringkasan (akun ${money.currency}, ${money.legLot} lot/posisi)", style = MaterialTheme.typography.titleSmall)
            SummaryLine("Hari ini", day, money)
            SummaryLine("Minggu ini", week, money)
            SummaryLine("Bulan ini", month, money)
        }
    }
}

@Composable
fun SummaryLine(label: String, s: PeriodStats?, money: MoneySettings) {
    if (s == null) {
        Text("$label: belum ada sinyal selesai", style = MaterialTheme.typography.bodySmall)
        return
    }
    Text(
        "$label: ${s.wins} menang / ${s.losses} kalah • ${moneyText(s.net, money)}",
        color = if (s.net >= 0) BuyColor else SellColor,
        style = MaterialTheme.typography.bodyMedium
    )
}

@Composable
fun StatsTab(events: List<SignalEvent>, money: MoneySettings) {
    var period by remember { mutableIntStateOf(0) }
    val idFmt = DateTimeFormatter.ofPattern("dd MMM yyyy", Locale("id"))
    val stats = when (period) {
        0 -> SignalRepository.periodStats(events, money, { it.toLocalDate().toString() },
            { LocalDate.parse(it).format(idFmt) })
        1 -> SignalRepository.periodStats(events, money, ::weekKey,
            { "Minggu " + LocalDate.parse(it).format(idFmt) })
        else -> SignalRepository.periodStats(events, money, { it.toLocalDate().toString().substring(0, 7) },
            { LocalDate.parse("$it-01").format(DateTimeFormatter.ofPattern("MMMM yyyy", Locale("id"))) })
    }
    val all = stats.fold(PeriodStats("Total", 0, 0, 0.0, 0.0)) { acc, s ->
        PeriodStats("Total", acc.wins + s.wins, acc.losses + s.losses, acc.profit + s.profit, acc.loss + s.loss)
    }
    LazyColumn(
        modifier = Modifier.fillMaxSize().padding(horizontal = 12.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        item {
            Row(Modifier.padding(top = 8.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                listOf("Harian", "Mingguan", "Bulanan").forEachIndexed { i, name ->
                    FilterChip(selected = period == i, onClick = { period = i }, label = { Text(name) })
                }
            }
        }
        item { StatCard(all, money, highlight = true) }
        if (stats.isEmpty()) {
            item { Text("Belum ada sinyal TUTUP. Statistik muncul setelah posisi selesai.") }
        }
        items(stats, key = { it.label }) { StatCard(it, money) }
        item {
            Text(
                "Hitungan: hasil R x jarak SL x jumlah posisi x (lot/0,01). Akun ${money.currency}; " +
                    "kurs Rp${fmt(money.idrRate, 0)} per USD. Ubah di Pengaturan.",
                style = MaterialTheme.typography.bodySmall
            )
        }
        item { Footer() }
    }
}

@Composable
fun StatCard(s: PeriodStats, money: MoneySettings, highlight: Boolean = false) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = if (highlight) Gold.copy(alpha = 0.15f) else MaterialTheme.colorScheme.surfaceVariant
        )
    ) {
        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(2.dp)) {
            Text(s.label, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.Bold)
            val rate = if (s.total > 0) s.wins * 100 / s.total else 0
            Text("Sinyal: ${s.total} • Menang ${s.wins} • Kalah ${s.losses} • Win rate $rate%")
            Text("Profit: ${moneyText(s.profit, money)}", color = BuyColor)
            Text("Rugi: ${moneyText(s.loss, money)}", color = SellColor)
            Text(
                "Bersih: ${moneyText(s.net, money)}",
                fontWeight = FontWeight.Bold,
                color = if (s.net >= 0) BuyColor else SellColor
            )
        }
    }
}

@Composable
fun EventRow(event: SignalEvent, money: MoneySettings) {
    val color = when (event.dir) {
        "BUY" -> BuyColor
        "SELL" -> SellColor
        else -> MaterialTheme.colorScheme.onSurface
    }
    Card(modifier = Modifier.fillMaxWidth()) {
        Row(Modifier.padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
            val badge = when (event.type) {
                "close" -> "TUTUP"
                "signal" -> event.dir
                else -> "INFO"
            }
            Text(
                badge,
                color = Color.White,
                fontWeight = FontWeight.Bold,
                modifier = Modifier
                    .background(if (event.type == "info") Color.Gray else color, RoundedCornerShape(6.dp))
                    .padding(horizontal = 8.dp, vertical = 4.dp)
            )
            Spacer(Modifier.width(10.dp))
            Column(Modifier.fillMaxWidth()) {
                when (event.type) {
                    "signal" -> {
                        Text(
                            "${event.dir} ${event.str("set")} @ ${fmt(event.num("entry"))}  SL ${fmt(event.num("sl"))}",
                            fontWeight = FontWeight.Bold
                        )
                        Text("TP1 ${fmt(event.num("tp1"))} • lot ${event.str("lot").ifBlank { "-" }}",
                            style = MaterialTheme.typography.bodySmall)
                        val status = when (event.status) {
                            "skipped" -> "Dilewati: ${event.str("note")}"
                            "opened" -> "Order terbuka otomatis"
                            "failed" -> "Order gagal: ${event.str("note")}"
                            else -> "Sinyal"
                        }
                        Text(status, style = MaterialTheme.typography.bodySmall)
                        Text(event.str("reason"), style = MaterialTheme.typography.bodySmall)
                    }
                    "close" -> {
                        val amount = SignalRepository.amount(event, money)
                        val win = (amount ?: event.num("r") ?: 0.0) > 0
                        Text(
                            "${event.dir} ${event.str("set")} ditutup @ ${fmt(event.num("price"))}  " +
                                if (win) "MENANG" else "KALAH",
                            fontWeight = FontWeight.Bold,
                            color = if (win) BuyColor else SellColor
                        )
                        if (amount != null) Text(moneyText(amount, money), color = if (win) BuyColor else SellColor)
                        Text("${fmt(event.num("points"))} poin (${fmt(event.num("r"))}R) • ${event.str("reason")}",
                            style = MaterialTheme.typography.bodySmall)
                    }
                    else -> Text(event.str("text"))
                }
                Text(event.timeText(), style = MaterialTheme.typography.labelSmall)
            }
        }
    }
}

@Composable
fun SettingsDialog(onDismiss: () -> Unit, onSave: (String, String, MoneySettings) -> Unit) {
    val current = SignalRepository.money()
    var server by remember { mutableStateOf(SignalRepository.server()) }
    var topic by remember { mutableStateOf(SignalRepository.topic()) }
    var cent by remember { mutableStateOf(current.cent) }
    var lot by remember { mutableStateOf(current.legLot.toString()) }
    var rate by remember { mutableStateOf(fmt(current.idrRate, 0).replace(",", "")) }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Pengaturan") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(value = server, onValueChange = { server = it }, label = { Text("Server") },
                    singleLine = true)
                OutlinedTextField(value = topic, onValueChange = { topic = it }, label = { Text("Topik") },
                    singleLine = true)
                Text("Akun trading", style = MaterialTheme.typography.labelMedium)
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    FilterChip(selected = cent, onClick = { cent = true }, label = { Text("Cent (USC)") })
                    FilterChip(selected = !cent, onClick = { cent = false }, label = { Text("USD") })
                }
                OutlinedTextField(value = lot, onValueChange = { lot = it }, label = { Text("Lot per posisi") },
                    singleLine = true)
                OutlinedTextField(value = rate, onValueChange = { rate = it }, label = { Text("Kurs 1 USD (Rp)") },
                    singleLine = true)
                Text(BRAND, style = MaterialTheme.typography.labelSmall, color = Gold)
            }
        },
        confirmButton = {
            TextButton(onClick = {
                val m = MoneySettings(
                    cent = cent,
                    legLot = lot.replace(",", ".").toDoubleOrNull() ?: 0.01,
                    idrRate = rate.replace(".", "").replace(",", "").toDoubleOrNull() ?: 16500.0,
                )
                onSave(server.ifBlank { SignalRepository.DEFAULT_SERVER }, topic, m)
            }) { Text("Simpan") }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Batal") } }
    )
}
