package com.xausignal.app

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
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
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject

private enum class Confirm { AUTO_ON, CLOSE_ALL }

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
    var legs by remember { mutableStateOf("") }
    var confirm by remember { mutableStateOf<Confirm?>(null) }

    suspend fun load(changes: JSONObject?) {
        busy = true
        try {
            val s = withContext(Dispatchers.IO) {
                if (changes == null) AutoControl.status() else AutoControl.update(changes)
            }
            status = s
            if (changes != null || lot.isBlank()) lot = s.legLot.toString()
            if (changes != null || legs.isBlank()) legs = s.legs.toString()
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
        modifier = Modifier.fillMaxSize().padding(horizontal = 12.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        item { Spacer(Modifier.padding(2.dp)) }
        item {
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = Gold.copy(alpha = 0.15f))
            ) {
                Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text("🤖 Auto order 24 jam (cloud)", fontWeight = FontWeight.Bold)
                    Text(
                        "Order dibuka oleh server (Vercel + MetaApi) langsung ke akun MT5 Exness kamu. " +
                            "HP boleh mati / offline; aplikasi ini hanya remote control.",
                        style = MaterialTheme.typography.bodySmall
                    )
                }
            }
        }
        item {
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("Koneksi cloud", style = MaterialTheme.typography.titleSmall)
                    if (editing) {
                        OutlinedTextField(
                            value = url, onValueChange = { url = it }, singleLine = true,
                            label = { Text("URL cloud, mis. https://superfal-dev.com") },
                            modifier = Modifier.fillMaxWidth()
                        )
                        OutlinedTextField(
                            value = key, onValueChange = { key = it }, singleLine = true,
                            label = { Text("CONTROL_KEY (dari Vercel)") },
                            visualTransformation = PasswordVisualTransformation(),
                            modifier = Modifier.fillMaxWidth()
                        )
                        Button(onClick = {
                            SignalRepository.saveCloud(url, key)
                            url = SignalRepository.cloudUrl()
                            status = null
                            editing = false
                        }) { Text("Simpan & hubungkan") }
                    } else {
                        Text(SignalRepository.cloudUrl(), style = MaterialTheme.typography.bodyMedium)
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            OutlinedButton(onClick = { send(null) }, enabled = !busy) { Text("Refresh") }
                            TextButton(onClick = { editing = true }) { Text("Ubah") }
                        }
                    }
                    if (busy) LinearProgressIndicator(modifier = Modifier.fillMaxWidth())
                    if (message.isNotBlank()) {
                        Text(message, color = if (message.startsWith("❌")) SellColor else BuyColor)
                    }
                }
            }
        }
        val s = status
        if (s != null && !editing) {
            item { AccountCard(s) }
            if (s.executor) {
                item {
                    Card(modifier = Modifier.fillMaxWidth()) {
                        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            SwitchRow(
                                "Auto order", if (s.auto) "ON — sinyal baru langsung dieksekusi" else
                                    "OFF — hanya sinyal (default)",
                                s.auto, !busy
                            ) { on ->
                                if (on) confirm = Confirm.AUTO_ON else send(JSONObject().put("auto", false))
                            }
                            SwitchRow(
                                "Jeda", "Tidak membuka order baru; posisi terbuka tetap dikelola",
                                s.paused, !busy
                            ) { on -> send(JSONObject().put("paused", on)) }
                            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                OutlinedTextField(
                                    value = lot, onValueChange = { lot = it }, singleLine = true,
                                    label = { Text("Lot/posisi") },
                                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                                    modifier = Modifier.weight(1f)
                                )
                                OutlinedTextField(
                                    value = legs, onValueChange = { legs = it }, singleLine = true,
                                    label = { Text("Jumlah posisi") },
                                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                                    modifier = Modifier.weight(1f)
                                )
                            }
                            Button(enabled = !busy, onClick = {
                                val l = lot.replace(",", ".").toDoubleOrNull()
                                val n = legs.toIntOrNull()
                                if (l == null || n == null) {
                                    message = "❌ Lot / jumlah posisi tidak valid"
                                } else {
                                    send(JSONObject().put("leg_lot", l).put("legs", n))
                                }
                            }) { Text("Simpan lot") }
                            Text(
                                "Contoh akun Cent Rp5–10 jt: 0.01 x 5. SL ±\$50 -> rugi maks ±250 " +
                                    "${s.currency.ifBlank { money.currency }} per sinyal.",
                                style = MaterialTheme.typography.bodySmall
                            )
                            Button(
                                enabled = !busy,
                                onClick = { confirm = Confirm.CLOSE_ALL },
                                colors = ButtonDefaults.buttonColors(containerColor = SellColor),
                                modifier = Modifier.fillMaxWidth()
                            ) { Text("TUTUP SEMUA posisi bot", color = Color.White) }
                        }
                    }
                }
            }
            item {
                Text(
                    "Posisi bot terbuka (${s.positions.size})",
                    style = MaterialTheme.typography.titleMedium,
                    modifier = Modifier.padding(top = 8.dp)
                )
            }
            if (s.positions.isEmpty()) item { Text("Tidak ada posisi terbuka.") }
            items(s.positions, key = { "live-" + it.id }) { PositionRow(it, s.currency) }
        }
        item {
            Text(
                "⚠️ Uji dulu di akun DEMO Exness. Auto OFF / Jeda: tidak membuka order baru, tetapi posisi " +
                    "yang sudah terbuka tetap dikelola (TP1, SL+, TUTUP). TUTUP SEMUA hanya menutup posisi " +
                    "milik bot (magic 250936–250945), posisi manual tidak disentuh, lalu auto dijeda. " +
                    "Hasil trading tidak dijamin.",
                style = MaterialTheme.typography.bodySmall
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
                        "(${legs.ifBlank { "5" }} posisi x ${lot.ifBlank { "0.01" }} lot, SL wajib terpasang). " +
                        "Pastikan sudah diuji di akun demo."
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
private fun AccountCard(s: AutoStatus) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(2.dp)) {
            if (!s.executor) {
                Text("MetaApi belum dipasang", fontWeight = FontWeight.Bold, color = SellColor)
                Text(
                    "Isi METAAPI_TOKEN dan METAAPI_ACCOUNT_ID di Vercel (lihat docs/CLOUD.md), lalu Redeploy. " +
                        "Sampai itu, cloud hanya mengirim sinyal.",
                    style = MaterialTheme.typography.bodySmall
                )
                return@Column
            }
            val mode = when {
                s.auto && !s.paused -> "AUTO ON"
                s.auto -> "AUTO DIJEDA"
                else -> "AUTO OFF (sinyal saja)"
            }
            Text(mode, fontWeight = FontWeight.Bold, color = if (s.auto && !s.paused) BuyColor else Gold)
            Text("Saldo ${fmt(s.balance)} ${s.currency} • Equity ${fmt(s.equity)} ${s.currency}")
            Text("${s.legs} posisi x ${s.legLot} lot per sinyal")
            if (s.error.isNotBlank()) Text(s.error, color = SellColor, style = MaterialTheme.typography.bodySmall)
        }
    }
}

@Composable
private fun SwitchRow(title: String, subtitle: String, checked: Boolean, enabled: Boolean, onChange: (Boolean) -> Unit) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Column(Modifier.weight(1f)) {
            Text(title, fontWeight = FontWeight.Bold)
            Text(subtitle, style = MaterialTheme.typography.bodySmall)
        }
        Switch(checked = checked, onCheckedChange = onChange, enabled = enabled)
    }
}

@Composable
private fun PositionRow(p: LivePosition, currency: String) {
    val profit = p.profit ?: 0.0
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(12.dp)) {
            Text(
                "${p.dir} ${fmt(p.volume)} lot @ ${fmt(p.open)}",
                fontWeight = FontWeight.Bold,
                color = if (p.dir == "BUY") BuyColor else SellColor
            )
            Text("SL ${fmt(p.sl)} • TP ${if (p.tp == null || p.tp == 0.0) "-" else fmt(p.tp)} • #${p.id}",
                style = MaterialTheme.typography.bodySmall)
            Text(
                "P/L ${if (profit > 0) "+" else ""}${fmt(profit)} $currency",
                color = if (profit >= 0) BuyColor else SellColor
            )
        }
    }
}
