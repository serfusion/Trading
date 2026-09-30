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
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.DateRange
import androidx.compose.material.icons.automirrored.filled.List
import androidx.compose.material.icons.filled.Info
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
import androidx.compose.ui.input.nestedscroll.nestedScroll
import androidx.compose.material3.pulltorefresh.PullToRefreshContainer
import androidx.compose.material3.pulltorefresh.rememberPullToRefreshState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.ui.text.input.KeyboardType
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
        askUnrestrictedBattery()
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

    /** Minta dikecualikan dari penghemat baterai supaya alarm cek sinyal tidak ditunda/dimatikan HP. */
    private fun askUnrestrictedBattery() {
        val pm = getSystemService(android.os.PowerManager::class.java) ?: return
        if (pm.isIgnoringBatteryOptimizations(packageName)) return
        try {
            startActivity(
                android.content.Intent(android.provider.Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS)
                    .setData(android.net.Uri.parse("package:$packageName"))
            )
        } catch (e: Exception) {
            // beberapa HP tidak punya layar ini
        }
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
    TabItem("News", Icons.AutoMirrored.Filled.List),
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AppScreen(onSettingsSaved: () -> Unit) {
    val events by SignalRepository.events.collectAsState()
    val prices by SignalRepository.prices.collectAsState()
    val connection by SignalRepository.connection.collectAsState()
    val moneyVersion by SignalRepository.moneyVersion.collectAsState()
    var showSettings by remember { mutableStateOf(SignalRepository.topic().isBlank()) }
    var showTerms by remember { mutableStateOf(!SignalRepository.termsAccepted()) }
    var tab by remember { mutableIntStateOf(0) }
    val money = remember(moneyVersion) { SignalRepository.money() }
    val follow = remember(moneyVersion) { SignalRepository.followed() }

    val permission = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) {}
    val context = LocalContext.current
    val lifecycle = LocalLifecycleOwner.current.lifecycle
    LaunchedEffect(Unit) {
        if (Build.VERSION.SDK_INT >= 33) permission.launch(Manifest.permission.POST_NOTIFICATIONS)
    }
    LaunchedEffect(Unit) {
        while (true) {   // selama aplikasi terbuka: ambil data tepat setelah cek cloud (tiap 10 menit, bukan tiap menit)
            val now = System.currentTimeMillis()
            delay(PollScheduler.nextSlot(now + 1_000L) - now)
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
                        Image(
                            painterResource(R.drawable.logo),
                            contentDescription = null,
                            modifier = Modifier.size(40.dp)
                        )
                        Column(Modifier.padding(start = 12.dp)) {
                            Text(APP_NAME, fontWeight = FontWeight.Bold, color = Gold,
                                style = MaterialTheme.typography.titleMedium, maxLines = 1)
                            Text(BRAND, style = MaterialTheme.typography.labelSmall, color = Muted)
                        }
                    }
                },
                actions = {
                    IconButton(onClick = { showTerms = true }) {
                        Icon(Icons.Filled.Info, contentDescription = "Syarat & Ketentuan")
                    }
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
            // Tarik ke bawah: ambil pesan & harga terbaru dari server sekarang juga.
            val pull = rememberPullToRefreshState()
            if (pull.isRefreshing) {
                LaunchedEffect(true) {
                    try {
                        withContext(Dispatchers.IO) { SignalPoller.poll(context.applicationContext) }
                    } finally {
                        pull.endRefresh()
                    }
                }
            }
            val pullable = if (tab != 2) Modifier.nestedScroll(pull.nestedScrollConnection) else Modifier
            Box(Modifier.fillMaxSize().then(pullable)) {
                when (tab) {
                    0 -> SignalsTab(events, prices, connection, money, follow)
                    1 -> StatsTab(events, money)
                    else -> NewsTab()
                }
                // Indikator hanya digambar saat ditarik / refresh: di Material3 1.2 lingkaran (bayangan) indikator
                // tetap terlihat sebagai bulatan hitam di tengah atas walau tidak sedang ditarik.
                if (tab != 2 && (pull.isRefreshing || pull.progress > 0f)) {
                    PullToRefreshContainer(state = pull, modifier = Modifier.align(Alignment.TopCenter))
                }
            }
        }
    }

    if (showTerms) {
        TermsDialog(money.idrRate) {
            SignalRepository.acceptTerms()
            showTerms = false
        }
    } else if (showSettings) {
        SettingsDialog(
            onDismiss = { showSettings = false },
            onSave = { server, topic, cloud, m ->
                SignalRepository.saveSettings(server, topic)
                SignalRepository.saveCloudUrl(cloud)
                SignalRepository.saveMoney(m)
                showSettings = false
                onSettingsSaved()
            }
        )
    }
}

@Composable
fun SettingsDialog(onDismiss: () -> Unit, onSave: (String, String, String, MoneySettings) -> Unit) {
    val current = SignalRepository.money()
    var server by remember { mutableStateOf(SignalRepository.server()) }
    var topic by remember { mutableStateOf(SignalRepository.topic()) }
    var cloud by remember { mutableStateOf(SignalRepository.cloudUrl()) }
    var cent by remember { mutableStateOf(current.cent) }
    var lot by remember { mutableStateOf(lotText(current.legLot)) }
    var starLot by remember { mutableStateOf(lotText(current.starLot)) }
    var rate by remember { mutableStateOf(fmt(current.idrRate, 0).replace(",", "")) }
    val lotValue = parseLot(lot)
    val starValue = parseLot(starLot)
    var modal by remember {
        mutableStateOf(if (current.baseModalIdr > 0) fmt(current.baseModalIdr, 0).replace(",", ".") else "")
    }
    var riskPct by remember { mutableStateOf(current.riskPct) }
    var zapRisk by remember { mutableStateOf(current.zapRiskPct) }
    var slAuto by remember { mutableStateOf(current.slAuto) }
    var autoModal by remember { mutableStateOf(current.autoModal) }
    var follow by remember { mutableStateOf(SignalRepository.followed()) }
    val modalValue = modal.replace(".", "").replace(",", "").trim().toDoubleOrNull() ?: 0.0
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
                Text(
                    "Notifikasi instan: di aplikasi ntfy langganan topik yang sama persis " +
                        "(${topic.ifBlank { "…" }}), tanpa \"-data\". Aplikasi ini sendiri mengecek tiap 10 menit.",
                    style = MaterialTheme.typography.bodySmall, color = Muted
                )
                OutlinedTextField(value = cloud, onValueChange = { cloud = it },
                    label = { Text("Alamat cloud (untuk Tanya)") },
                    placeholder = { Text("https://nama-proyek.vercel.app") },
                    singleLine = true, modifier = Modifier.fillMaxWidth())
                CardTitle("Akun")
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    FilterChip(selected = cent, onClick = { cent = true }, label = { Text("Cent (USC)") })
                    FilterChip(selected = !cent, onClick = { cent = false }, label = { Text("USD") })
                }
                Text(
                    "Harus sama dengan akun MT5: Cent = saldo tertulis USC dan simbol berakhiran c (XAUUSDc). " +
                        "Akun USD tetapi dipilih Cent → lot 100× terlalu besar!",
                    style = MaterialTheme.typography.bodySmall, color = SellColor
                )
                CardTitle("Pair yang saya ikuti")
                Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    listOf("XAU" to "XAU/USD", "BTC" to "BTC/USD", "GAP" to "Forex gap").forEach { (k, label) ->
                        FilterChip(
                            selected = k in follow,
                            onClick = { follow = if (k !in follow) follow + k else if (follow.size > 1) follow - k else follow },
                            label = { Text(label) }
                        )
                    }
                }
                Text(
                    "Sinyal, notifikasi, dan ringkasan \"Hari ini\" hanya untuk pair yang dipilih. Forex gap = USD/JPY, " +
                        "EUR/JPY, AUD/JPY, AUD/USD, EUR/CHF (hanya saat buka pekan, Senin pagi WIB).",
                    style = MaterialTheme.typography.bodySmall, color = Muted
                )
                OutlinedTextField(
                    value = modal, onValueChange = { modal = it.filter { c -> c.isDigit() || c == '.' } },
                    label = { Text("Modal (Rp)") }, placeholder = { Text("mis. 10.000.000") },
                    singleLine = true, modifier = Modifier.fillMaxWidth(),
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number)
                )
                if (modalValue > 0) {
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        FilterChip(selected = autoModal, onClick = { autoModal = !autoModal },
                            label = { Text("Modal otomatis") })
                    }
                    Text(
                        if (autoModal) "Modal = modal di atas + profit/rugi sinyal yang TUTUP sejak disimpan" +
                            (if (current.autoModal) " (sekarang ≈ ${idrText(current.modalIdr)})." else ".")
                        else "Nyalakan supaya lot ikut naik/turun sesuai profit/rugi tanpa mengetik ulang modal.",
                        style = MaterialTheme.typography.bodySmall, color = Muted
                    )
                    CardTitle("Rugi maks sinyal ⚡ kesempatan emas")
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        FilterChip(selected = zapRisk == 0.5, onClick = { zapRisk = 0.5 }, label = { Text("0,5%") })
                        FilterChip(selected = zapRisk == 1.0, onClick = { zapRisk = 1.0 }, label = { Text("1%") })
                    }
                    CardTitle("Rugi maks sinyal 🥈/🥉")
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        FilterChip(selected = riskPct == 0.25, onClick = { riskPct = 0.25 }, label = { Text("0,25%") })
                        FilterChip(selected = riskPct == 0.5, onClick = { riskPct = 0.5 }, label = { Text("0,5%") })
                    }
                    Text(
                        "Sinyal \"Biasa\" memakai setengahnya. Lot dihitung otomatis dari jarak SL tiap sinyal " +
                            "(dibulatkan ke bawah, min 0.01). Risiko > 1% per sinyal tidak disarankan: ⚡ pun bisa " +
                            "kalah 8× beruntun.",
                        style = MaterialTheme.typography.bodySmall, color = Muted
                    )
                } else {
                    LotInput(lot, { lot = it; starLot = it }, "Lot per posisi", 100.0)
                    Text("Isi modal supaya lot dihitung otomatis.", style = MaterialTheme.typography.bodySmall,
                        color = Muted)
                }
                CardTitle("Skema")
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    FilterChip(selected = slAuto, onClick = { slAuto = true }, label = { Text("SL+ otomatis") })
                    FilterChip(selected = !slAuto, onClick = { slAuto = false }, label = { Text("SL+ setelah TP1") })
                }
                Text(
                    "1 posisi TP1 (1R), 4 posisi running sampai sinyal TUTUP. " +
                        (if (slAuto) "Otomatis: ⚡ & BTC → SL semua posisi ke entry saat profit 0,7R (WR lebih " +
                            "tinggi, profit setara); XAU lainnya → SL+ setelah TP1 kena (profit XAU lebih besar)."
                        else "TP1 kena → SL 4 posisi ke entry (SL+)."),
                    style = MaterialTheme.typography.bodySmall, color = Muted
                )
                OutlinedTextField(value = rate, onValueChange = { rate = it }, label = { Text("Kurs 1 USD (Rp)") },
                    singleLine = true, modifier = Modifier.fillMaxWidth())
            }
        },
        confirmButton = {
            TextButton(
                enabled = modalValue > 0 || (lotValue != null && starValue != null),
                onClick = {
                    val m = MoneySettings(
                        cent = cent,
                        legLot = lotValue ?: 0.01,
                        idrRate = rate.replace(".", "").replace(",", "").toDoubleOrNull() ?: 17500.0,
                        starLot = starValue ?: 0.01,
                        tpLegs = 1,
                        be07 = false,
                        modalIdr = modalValue,
                        riskPct = riskPct,
                        zapRiskPct = zapRisk,
                        slAuto = slAuto,
                        autoModal = autoModal,
                    )
                    SignalRepository.saveFollowed(follow)
                    onSave(server.ifBlank { SignalRepository.DEFAULT_SERVER }, topic, cloud, m)
                }
            ) { Text("Simpan", fontWeight = FontWeight.Bold) }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Batal") } }
    )
}
