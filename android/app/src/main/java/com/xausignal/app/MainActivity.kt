package com.xausignal.app

import android.Manifest
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.DateRange
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Tab
import androidx.compose.material3.TabRow
import androidx.compose.material3.TabRowDefaults.tabIndicatorOffset
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
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
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.lifecycle.Lifecycle
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.withContext
import java.util.Locale

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        SignalRepository.init(this)
        Notifications.createChannels(this)
        PollScheduler.schedule(applicationContext)
        setContent {
            XauTheme {
                AppScreen(onSettingsSaved = { refresh() })
            }
        }
    }

    override fun onResume() {
        super.onResume()
        refresh()
    }

    /** Muat harga & sinyal terbaru saat aplikasi dibuka. */
    private fun refresh() {
        val app = applicationContext
        Thread { SignalPoller.poll(app) }.start()
    }
}

fun idrText(value: Double): String = "Rp" + String.format(Locale("id", "ID"), "%,.0f", Math.abs(value))

/** Nilai dalam mata uang akun, mis. "+250.00 USC". */
fun moneyMain(value: Double, m: MoneySettings): String = "${signed(value)} ${m.currency}"

/** Nilai dalam Rupiah, mis. "≈ +Rp41.250". */
fun idrLine(value: Double, m: MoneySettings): String {
    val idr = SignalRepository.toIdr(value, m)
    val sign = if (idr > 0) "+" else if (idr < 0) "−" else ""
    return "≈ $sign${idrText(idr)}"
}

private data class TabItem(val title: String, val icon: ImageVector)

private val TABS = listOf(
    TabItem("Sinyal", Icons.Filled.Notifications),
    TabItem("Statistik", Icons.Filled.DateRange),
)

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
    val context = LocalContext.current
    val lifecycle = LocalLifecycleOwner.current.lifecycle
    LaunchedEffect(Unit) {
        if (Build.VERSION.SDK_INT >= 33) permission.launch(Manifest.permission.POST_NOTIFICATIONS)
    }
    LaunchedEffect(Unit) {
        while (true) {   // selama aplikasi terbuka: perbarui tiap menit
            delay(60_000)
            if (lifecycle.currentState.isAtLeast(Lifecycle.State.RESUMED)) {
                withContext(Dispatchers.IO) { SignalPoller.poll(context.applicationContext) }
            }
        }
    }

    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        topBar = {
            TopAppBar(
                colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.background),
                title = {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Box(
                            Modifier
                                .size(40.dp)
                                .background(Color(0xFF14181F), RoundedCornerShape(12.dp)),
                            contentAlignment = Alignment.Center
                        ) {
                            Image(
                                painterResource(R.drawable.ic_launcher_foreground),
                                contentDescription = null,
                                modifier = Modifier.size(40.dp)
                            )
                        }
                        Column(Modifier.padding(start = 12.dp)) {
                            Text(APP_NAME, fontWeight = FontWeight.Bold, color = Gold,
                                style = MaterialTheme.typography.titleMedium, maxLines = 1)
                            Text(BRAND, style = MaterialTheme.typography.labelSmall, color = Muted)
                        }
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
            TabRow(
                selectedTabIndex = tab,
                containerColor = MaterialTheme.colorScheme.background,
                contentColor = Gold,
                indicator = { positions ->
                    Box(
                        Modifier
                            .tabIndicatorOffset(positions[tab])
                            .padding(horizontal = 20.dp)
                            .height(3.dp)
                            .background(Gold, RoundedCornerShape(topStart = 3.dp, topEnd = 3.dp))
                    )
                },
                divider = { LineDivider() }
            ) {
                TABS.forEachIndexed { i, t ->
                    Tab(
                        selected = tab == i,
                        onClick = { tab = i },
                        selectedContentColor = Gold,
                        unselectedContentColor = Muted,
                        icon = { Icon(t.icon, contentDescription = null) },
                        text = {
                            Text(t.title, fontWeight = if (tab == i) FontWeight.Bold else FontWeight.Medium,
                                maxLines = 1)
                        }
                    )
                }
            }
            when (tab) {
                0 -> SignalsTab(events, heartbeat, connection, money)
                else -> StatsTab(events, money)
            }
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
fun SettingsDialog(onDismiss: () -> Unit, onSave: (String, String, MoneySettings) -> Unit) {
    val current = SignalRepository.money()
    var server by remember { mutableStateOf(SignalRepository.server()) }
    var topic by remember { mutableStateOf(SignalRepository.topic()) }
    var cent by remember { mutableStateOf(current.cent) }
    var lot by remember { mutableStateOf(lotText(current.legLot)) }
    var starLot by remember { mutableStateOf(lotText(current.starLot)) }
    var rate by remember { mutableStateOf(fmt(current.idrRate, 0).replace(",", "")) }
    val lotValue = parseLot(lot)
    val starValue = parseLot(starLot)
    AlertDialog(
        onDismissRequest = onDismiss,
        title = {
            Text("Pengaturan", fontWeight = FontWeight.Bold)
        },
        text = {
            Column(
                Modifier.verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                OutlinedTextField(value = server, onValueChange = { server = it }, label = { Text("Server") },
                    singleLine = true, modifier = Modifier.fillMaxWidth())
                OutlinedTextField(value = topic, onValueChange = { topic = it }, label = { Text("Topik") },
                    singleLine = true, modifier = Modifier.fillMaxWidth())
                CardTitle("Akun")
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    FilterChip(selected = cent, onClick = { cent = true }, label = { Text("Cent (USC)") })
                    FilterChip(selected = !cent, onClick = { cent = false }, label = { Text("USD") })
                }
                LotInput(lot, { lot = it }, "Lot sinyal biasa", 100.0)
                LotInput(starLot, { starLot = it }, "Lot sinyal ⭐", 100.0)
                OutlinedTextField(value = rate, onValueChange = { rate = it }, label = { Text("Kurs 1 USD (Rp)") },
                    singleLine = true, modifier = Modifier.fillMaxWidth())
            }
        },
        confirmButton = {
            TextButton(
                enabled = lotValue != null && starValue != null,
                onClick = {
                    val m = MoneySettings(
                        cent = cent,
                        legLot = lotValue ?: 0.01,
                        idrRate = rate.replace(".", "").replace(",", "").toDoubleOrNull() ?: 16500.0,
                        starLot = starValue ?: 0.01,
                    )
                    onSave(server.ifBlank { SignalRepository.DEFAULT_SERVER }, topic, m)
                }
            ) { Text("Simpan", fontWeight = FontWeight.Bold) }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Batal") } }
    )
}
