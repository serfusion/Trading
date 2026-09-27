package com.xausignal.app

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
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject

private enum class Confirm { AUTO_ON, CLOSE_ALL }

/** Batas lot di aplikasi; batas sebenarnya dicek server (MAX_LEG_LOT, default 0.10). */
private const val APP_MAX_LOT = 1.0

/** Tab Auto: remote control auto order di cloud. HP hanya mengirim perintah; eksekusi di server. */
@Composable
fun AutoTab(money: MoneySettings) {
    val scope = rememberCoroutineScope()
    var url by remember { mutableStateOf(SignalRepository.cloudUrl()) }
    var key by remember { mutableStateOf(SignalRepository.controlKey()) }
    var editing by remember {
        mutableStateOf(SignalRepository.cloudUrl().isBlank() || SignalRepository.controlKey().isBlank())
    }
    var status by remember { mutableStateOf<AutoStatus?>(null) }
    var busy by remember { mutableStateOf(false) }
    var message by remember { mutableStateOf("") }
    var lot by remember { mutableStateOf("") }
    var legs by remember { mutableIntStateOf(0) }
    var confirm by remember { mutableStateOf<Confirm?>(null) }

    suspend fun load(changes: JSONObject?) {
        busy = true
        try {
            val s = withContext(Dispatchers.IO) {
                if (changes == null) AutoControl.status() else AutoControl.update(changes)
            }
            status = s
            if (changes != null || lot.isBlank()) lot = lotText(s.legLot)
            if (changes != null || legs == 0) legs = s.legs.coerceIn(1, 10)
            message = if (changes == null) "" else "✅ Tersimpan di cloud"
        } catch (e: Exception) {
            message = "❌ ${e.message ?: e.javaClass.simpleName}"
        } finally {
            busy = false
        }
    }

    fun send(changes: JSONObject?) {
        scope.launch { load(changes) }
    }

    LaunchedEffect(editing) {
        while (!editing) {
            load(null)
            delay(30_000)
        }
    }

    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(horizontal = 16.dp, vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        item {
            AppCard(accent = Gold) {
                Text("Auto order 24 jam (cloud)", style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold)
                Text(
                    "Order dibuka oleh server (Vercel + MetaApi) langsung ke akun MT5 Exness kamu. " +
                        "HP boleh mati / offline; aplikasi ini hanya remote control.",
                    style = MaterialTheme.typography.bodyMedium, color = Muted
                )
            }
        }
        item {
            AppCard {
                CardTitle("Koneksi cloud")
                if (editing) {
                    OutlinedTextField(
                        value = url, onValueChange = { url = it }, singleLine = true,
                        label = { Text("URL cloud") },
                        placeholder = { Text("https://superfal-dev.com") },
                        modifier = Modifier.fillMaxWidth()
                    )
                    OutlinedTextField(
                        value = key, onValueChange = { key = it }, singleLine = true,
                        label = { Text("CONTROL_KEY (dari Vercel)") },
                        visualTransformation = PasswordVisualTransformation(),
                        modifier = Modifier.fillMaxWidth()
                    )
                    Button(
                        onClick = {
                            SignalRepository.saveCloud(url, key)
                            url = SignalRepository.cloudUrl()
                            status = null
                            editing = false
                        },
                        shape = RoundedCornerShape(12.dp),
                        modifier = Modifier.fillMaxWidth()
                    ) { Text("Simpan & hubungkan", fontWeight = FontWeight.Bold) }
                } else {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        StatusDot(if (status != null) BuyColor else Muted)
                        Text(
                            SignalRepository.cloudUrl(), style = MaterialTheme.typography.bodyMedium,
                            modifier = Modifier.padding(start = 8.dp).weight(1f), maxLines = 1
                        )
                    }
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        OutlinedButton(onClick = { send(null) }, enabled = !busy, shape = RoundedCornerShape(12.dp)) {
                            Text("Refresh")
                        }
                        TextButton(onClick = { editing = true }) { Text("Ubah koneksi") }
                    }
                }
                if (busy) LinearProgressIndicator(modifier = Modifier.fillMaxWidth())
                if (message.isNotBlank()) {
                    NoteBox(message, if (message.startsWith("❌")) SellColor else BuyColor)
                }
            }
        }
        val s = status
        if (s != null && !editing) {
            item { AccountCard(s, money) }
            if (s.executor) {
                item {
                    AppCard {
                        CardTitle("Kontrol")
                        SwitchRow(
                            "Auto order",
                            if (s.auto) "ON — sinyal baru langsung dieksekusi" else "OFF — hanya sinyal (default)",
                            s.auto, !busy
                        ) { on ->
                            if (on) confirm = Confirm.AUTO_ON else send(JSONObject().put("auto", false))
                        }
                        LineDivider()
                        SwitchRow(
                            "Jeda", "Tidak membuka order baru; posisi terbuka tetap dikelola",
                            s.paused, !busy
                        ) { on -> send(JSONObject().put("paused", on)) }
                    }
                }
                item {
                    val lotValue = parseLot(lot, APP_MAX_LOT)
                    val currency = s.currency.ifBlank { money.currency }
                    AppCard {
                        CardTitle("Ukuran order per sinyal")
                        LotInput(lot, { lot = it }, "Lot per posisi", APP_MAX_LOT, enabled = !busy)
                        CountInput(legs, { legs = it }, "Jumlah posisi", 1, 10, enabled = !busy)
                        if (lotValue != null) {
                            // SL median ±$50 per 0,01 lot (docs/BACKTEST.md 4.3) -> 50 unit mata uang akun
                            val risk = 50.0 * legs * Math.round(lotValue * 100.0)
                            MetricRow {
                                Metric("Total lot", lotText(lotValue * legs))
                                Metric("Rugi maks ±", "${fmt(risk, 0)} $currency", SellColor)
                            }
                            Text(
                                "Perkiraan bila SL ±\$50 kena (median 2025–26). Contoh akun Cent Rp5–10 jt: " +
                                    "0.01 × 5 posisi.",
                                style = MaterialTheme.typography.bodySmall, color = Muted
                            )
                        }
                        Button(
                            enabled = !busy && lotValue != null,
                            onClick = {
                                lotValue?.let { send(JSONObject().put("leg_lot", it).put("legs", legs)) }
                            },
                            shape = RoundedCornerShape(12.dp),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text(
                                if (lotValue == null) "Lot tidak valid"
                                else "Simpan: $legs × ${lotText(lotValue)} lot",
                                fontWeight = FontWeight.Bold
                            )
                        }
                        Button(
                            enabled = !busy,
                            onClick = { confirm = Confirm.CLOSE_ALL },
                            colors = ButtonDefaults.buttonColors(containerColor = SellColor, contentColor = Color.White),
                            shape = RoundedCornerShape(12.dp),
                            modifier = Modifier.fillMaxWidth()
                        ) { Text("TUTUP SEMUA posisi bot", fontWeight = FontWeight.Bold) }
                    }
                }
            }
            item { SectionTitle("Posisi bot terbuka", trailing = "${s.positions.size}") }
            if (s.positions.isEmpty()) {
                item {
                    AppCard {
                        Text("Tidak ada posisi terbuka.", color = Muted)
                    }
                }
            }
            items(s.positions, key = { "live-" + it.id }) { PositionRow(it, s.currency) }
        }
        item {
            NoteBox(
                "Uji dulu di akun DEMO Exness. Auto OFF / Jeda: tidak membuka order baru, tetapi posisi " +
                    "yang sudah terbuka tetap dikelola (TP1, SL+, TUTUP). TUTUP SEMUA hanya menutup posisi " +
                    "milik bot (magic 250936–250945), posisi manual tidak disentuh, lalu auto dijeda. " +
                    "Hasil trading tidak dijamin.",
                SellColor
            )
        }
        item { Footer() }
    }

    when (confirm) {
        Confirm.AUTO_ON -> AlertDialog(
            onDismissRequest = { confirm = null },
            title = { Text("Nyalakan auto order?") },
            text = {
                Text(
                    "Server akan membuka order SUNGGUHAN di akun MT5 kamu setiap ada sinyal baru " +
                        "(${status?.legs ?: 5} posisi × ${lotText(status?.legLot ?: 0.01)} lot, SL wajib " +
                        "terpasang). Pastikan sudah diuji di akun demo."
                )
            },
            confirmButton = {
                TextButton(onClick = {
                    confirm = null
                    send(JSONObject().put("auto", true).put("paused", false))
                }) { Text("Ya, nyalakan") }
            },
            dismissButton = { TextButton(onClick = { confirm = null }) { Text("Batal") } }
        )
        Confirm.CLOSE_ALL -> AlertDialog(
            onDismissRequest = { confirm = null },
            title = { Text("Tutup semua posisi bot?") },
            text = { Text("Semua posisi milik bot ditutup di harga pasar sekarang dan auto order dijeda.") },
            confirmButton = {
                TextButton(onClick = {
                    confirm = null
                    send(JSONObject().put("close_all", true))
                }) { Text("Tutup semua", color = SellColor) }
            },
            dismissButton = { TextButton(onClick = { confirm = null }) { Text("Batal") } }
        )
        null -> Unit
    }
}

@Composable
private fun AccountCard(s: AutoStatus, money: MoneySettings) {
    if (!s.executor) {
        AppCard(accent = SellColor) {
            Text("MetaApi belum dipasang", fontWeight = FontWeight.Bold, color = SellColor)
            Text(
                "Isi METAAPI_TOKEN dan METAAPI_ACCOUNT_ID di Vercel (lihat docs/CLOUD.md), lalu Redeploy. " +
                    "Sampai itu, cloud hanya mengirim sinyal.",
                style = MaterialTheme.typography.bodyMedium, color = Muted
            )
        }
        return
    }
    val (mode, color) = when {
        s.auto && !s.paused -> "AUTO ON" to BuyColor
        s.auto -> "AUTO DIJEDA" to Gold
        else -> "AUTO OFF • sinyal saja" to Muted
    }
    val currency = s.currency.ifBlank { money.currency }
    val floating = s.positions.sumOf { it.profit ?: 0.0 }
    AppCard(accent = color) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            CardTitle("Akun MT5", Modifier.weight(1f))
            Pill(mode, color, solid = s.auto && !s.paused)
        }
        MetricRow {
            Metric("Saldo $currency", fmt(s.balance))
            Metric("Equity $currency", fmt(s.equity))
        }
        MetricRow {
            Metric("Per sinyal", "${s.legs} × ${lotText(s.legLot)} lot")
            Metric("Floating", signed(floating), if (floating >= 0) BuyColor else SellColor)
        }
        if (s.error.isNotBlank()) NoteBox(s.error, SellColor)
    }
}

@Composable
private fun SwitchRow(title: String, subtitle: String, checked: Boolean, enabled: Boolean, onChange: (Boolean) -> Unit) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Column(Modifier.weight(1f).padding(end = 8.dp)) {
            Text(title, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.Bold)
            Text(subtitle, style = MaterialTheme.typography.bodySmall, color = Muted)
        }
        Switch(checked = checked, onCheckedChange = onChange, enabled = enabled)
    }
}

@Composable
private fun PositionRow(p: LivePosition, currency: String) {
    val profit = p.profit ?: 0.0
    val color = dirColor(p.dir)
    AppCard {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Pill(p.dir, color, solid = true)
            Text(
                "${lotText(p.volume)} lot @ ${fmt(p.open)}", fontWeight = FontWeight.Bold,
                modifier = Modifier.weight(1f)
            )
            Text(
                "${signed(profit)} $currency", fontWeight = FontWeight.Bold,
                color = if (profit >= 0) BuyColor else SellColor, textAlign = TextAlign.End
            )
        }
        MetricRow {
            Metric("SL", fmt(p.sl), SellColor)
            Metric("TP", if (p.tp == null || p.tp == 0.0) "-" else fmt(p.tp), BuyColor)
        }
        Text("Tiket #${p.id}", style = MaterialTheme.typography.labelSmall, color = Muted)
    }
}
