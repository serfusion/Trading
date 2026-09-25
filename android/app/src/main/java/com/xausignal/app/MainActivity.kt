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
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat

private val BuyColor = Color(0xFF1FAA59)
private val SellColor = Color(0xFFE5484D)
private val Gold = Color(0xFFD4A017)

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

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AppScreen(onSettingsSaved: () -> Unit) {
    val events by SignalRepository.events.collectAsState()
    val heartbeat by SignalRepository.heartbeat.collectAsState()
    val connection by SignalRepository.connection.collectAsState()
    var showSettings by remember { mutableStateOf(SignalRepository.topic().isBlank()) }

    val permission = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) {}
    LaunchedEffect(Unit) {
        if (Build.VERSION.SDK_INT >= 33) permission.launch(Manifest.permission.POST_NOTIFICATIONS)
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("XAU Signal", fontWeight = FontWeight.Bold) },
                actions = {
                    IconButton(onClick = { showSettings = true }) {
                        Icon(Icons.Filled.Settings, contentDescription = "Pengaturan")
                    }
                }
            )
        }
    ) { padding ->
        val history = events.filter { it.type == "signal" || it.type == "close" || it.type == "info" }
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(horizontal = 12.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            item { StatusCard(heartbeat, connection) }
            item { OpenSignalCard(SignalRepository.openSignal(events), heartbeat) }
            item { StatsCard(SignalRepository.stats(events)) }
            item {
                Text(
                    "Riwayat sinyal",
                    style = MaterialTheme.typography.titleMedium,
                    modifier = Modifier.padding(top = 8.dp)
                )
            }
            if (history.isEmpty()) {
                item { Text("Belum ada sinyal. Pastikan bot di PC berjalan dan topik sudah benar.") }
            }
            items(history, key = { it.msgId }) { EventRow(it) }
            item { Spacer(Modifier.padding(12.dp)) }
        }
    }

    if (showSettings) {
        SettingsDialog(
            onDismiss = { showSettings = false },
            onSave = { server, topic ->
                SignalRepository.saveSettings(server, topic)
                showSettings = false
                onSettingsSaved()
            }
        )
    }
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
            val currency = heartbeat.str("currency")
            Text("Saldo ${fmt(heartbeat.num("balance"))} $currency • Equity ${fmt(heartbeat.num("equity"))} $currency")
            Text("Mode: ${heartbeat.str("mode")} • Sesi: ${heartbeat.str("session")} • Spread ${fmt(heartbeat.num("spread"))}")
            val block = heartbeat.str("block")
            if (block.isNotBlank()) Text("Blokir entry: $block", color = SellColor)
            Text("Berita: ${heartbeat.str("news")}", style = MaterialTheme.typography.bodySmall)
            Text("Update ${heartbeat.timeText()}", style = MaterialTheme.typography.bodySmall)
        }
    }
}

@Composable
fun OpenSignalCard(signal: SignalEvent?, heartbeat: SignalEvent?) {
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
            Text("Posisi sinyal aktif", style = MaterialTheme.typography.titleSmall)
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
            Text("SL ${fmt(signal.num("sl"))} • TP: tunggu sinyal TUTUP")
            Text("Lot saran ${signal.str("lot").ifBlank { "-" }} • ${signal.timeText()}")
            if (floating != null) {
                Text(
                    "Berjalan: ${fmt(floating)} poin",
                    color = if (floating >= 0) BuyColor else SellColor,
                    fontWeight = FontWeight.Bold
                )
            }
            val warning = signal.str("warning")
            if (warning.isNotBlank()) Text(warning, color = SellColor)
        }
    }
}

@Composable
fun StatsCard(stats: Stats) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Row(Modifier.padding(14.dp), horizontalArrangement = Arrangement.SpaceBetween) {
            StatItem("Selesai", stats.closed.toString())
            Spacer(Modifier.width(16.dp))
            StatItem(
                "Benar",
                if (stats.closed == 0) "-" else "${stats.wins} (${stats.wins * 100 / stats.closed}%)"
            )
            Spacer(Modifier.width(16.dp))
            StatItem("Total", "${fmt(stats.totalR)}R")
        }
    }
}

@Composable
fun StatItem(label: String, value: String) {
    Column {
        Text(label, style = MaterialTheme.typography.bodySmall)
        Text(value, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
    }
}

@Composable
fun EventRow(event: SignalEvent) {
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
                        Text("${event.dir} @ ${fmt(event.num("entry"))}  SL ${fmt(event.num("sl"))}", fontWeight = FontWeight.Bold)
                        val status = when (event.status) {
                            "skipped" -> "Dilewati: ${event.str("note")}"
                            "opened" -> "Order terbuka otomatis"
                            "failed" -> "Order gagal: ${event.str("note")}"
                            else -> "Sinyal • lot ${event.str("lot").ifBlank { "-" }}"
                        }
                        Text(status, style = MaterialTheme.typography.bodySmall)
                        Text(event.str("reason"), style = MaterialTheme.typography.bodySmall)
                    }
                    "close" -> {
                        val r = event.num("r")
                        val result = if (r == null) "" else if (r > 0) "BENAR" else "SALAH"
                        Text(
                            "${event.dir} ditutup @ ${fmt(event.num("price"))}  $result",
                            fontWeight = FontWeight.Bold,
                            color = if ((r ?: 0.0) > 0) BuyColor else SellColor
                        )
                        Text("${fmt(event.num("points"))} poin (${fmt(r)}R) • ${event.str("reason")}",
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
fun SettingsDialog(onDismiss: () -> Unit, onSave: (String, String) -> Unit) {
    var server by remember { mutableStateOf(SignalRepository.server()) }
    var topic by remember { mutableStateOf(SignalRepository.topic()) }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Pengaturan") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text(
                    "Jalankan \"python -m xau_bot app\" di PC untuk melihat server & topik.",
                    style = MaterialTheme.typography.bodySmall
                )
                OutlinedTextField(value = server, onValueChange = { server = it }, label = { Text("Server") },
                    singleLine = true)
                OutlinedTextField(value = topic, onValueChange = { topic = it }, label = { Text("Topik") },
                    singleLine = true)
            }
        },
        confirmButton = {
            TextButton(onClick = { onSave(server.ifBlank { SignalRepository.DEFAULT_SERVER }, topic) }) {
                Text("Simpan")
            }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Batal") } }
    )
}
