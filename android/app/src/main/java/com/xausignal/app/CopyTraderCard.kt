package com.xausignal.app

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject

/** cloud/api/copytrader.json lewat GET /api/chat?copytrader=1, dimuat sekali per sesi aplikasi. */
object CopyTraders {
    var data by mutableStateOf<JSONObject?>(null)
    var tried by mutableStateOf(false)
    suspend fun load() {
        if (data != null) return
        data = withContext(Dispatchers.IO) { ChatClient.copytrader() }
        tried = true
    }
}

/**
 * 👥 Copy trader teruji (aplikasi 4.7, permintaan pengguna 6 Okt 2026; research/copy_pilih.py, docs/COPY_TRADE.md).
 * Penyedia Binance Copy Trading & MQL5 Signals yang lolos saringan (umur ≥ 12 bln, untung di 2 paruh tahun, DD ≤ 20%,
 * WR ≥ 60–65%, pengikut nyata, tanpa grid), diperbarui mingguan oleh GitHub Actions. Ketuk = buka halaman langganan.
 * Info saja — aplikasi tidak menyalin order.
 */
@Composable
fun CopyTraderSection() {
    LaunchedEffect(Unit) { CopyTraders.load() }
    val d = CopyTraders.data ?: return              // cloud lama / gagal → kartu tidak tampil
    val bin = d.optJSONArray("binance")
    val mq = d.optJSONArray("mql5")
    val all = buildList {
        for (i in 0 until (bin?.length() ?: 0)) bin?.optJSONObject(i)?.let { add(it) }
        for (i in 0 until (mq?.length() ?: 0)) mq?.optJSONObject(i)?.let { add(it) }
    }
    if (all.isEmpty()) return
    var open by rememberSaveable { mutableStateOf(false) }
    // ringkas: 2 Binance teratas + 1 MQL5 teratas; buka = semua + bukti uji
    val shown = if (open) all else all.filter { it.optString("platform") == "Binance" }.take(2) +
        all.filter { it.optString("platform").startsWith("MQL5") }.take(1)
    val n = d.optJSONObject("n")
    SectionTitle("👥 Copy trader teruji", trailing = "${(n?.optInt("binance") ?: 0) + (n?.optInt("mql5") ?: 0)} lolos")
    AppCard {
        Text("Profit 1 tahun • DD maks • WR", Modifier.fillMaxWidth(), textAlign = TextAlign.End,
            style = MaterialTheme.typography.labelSmall, color = Muted)
        shown.forEach { CopyRow(it) }
        Row(
            Modifier.fillMaxWidth().clickable { open = !open }.padding(top = 2.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                "Diperbarui ${d.optString("dibuat")} • ketuk nama = buka halaman salin",
                Modifier.weight(1f), style = MaterialTheme.typography.labelSmall, color = Muted
            )
            Text(if (open) "Tutup ▴" else "Semua & bukti ▾", style = MaterialTheme.typography.labelMedium,
                fontWeight = FontWeight.Bold, color = Gold)
        }
        if (open) {
            val uji = d.optJSONObject("uji")
            Text("Saringan: ${d.optString("aturan")}", style = MaterialTheme.typography.labelSmall, color = Muted)
            uji?.optString("binance")?.takeIf { it.isNotBlank() }?.let {
                Text("Uji Binance: $it", style = MaterialTheme.typography.labelSmall, color = Muted)
            }
            uji?.optString("mql5")?.takeIf { it.isNotBlank() }?.let {
                Text("Uji MQL5: $it", style = MaterialTheme.typography.labelSmall, color = Muted)
            }
            val basi = d.optJSONArray("basi")
            if (basi != null && basi.length() > 0) {
                Text("Daftar ${(0 until basi.length()).joinToString { basi.optString(it) }} dari minggu lalu (unduh gagal).",
                    style = MaterialTheme.typography.labelSmall, color = SellColor)
            }
            if (all.any { it.optBoolean("wr_curiga") }) {
                Text("⚠️ WR ≈ 100% biasanya karena posisi rugi ditahan (floating), bukan keahlian — cek posisi terbuka " +
                    "sebelum menyalin.", style = MaterialTheme.typography.labelSmall, color = SellColor)
            }
            NoteBox(d.optString("kesimpulan").ifBlank { "Hasil lalu tidak menjamin hasil depan. Mulai modal kecil." })
        }
    }
}

@Composable
private fun CopyRow(x: JSONObject) {
    val uri = LocalUriHandler.current
    val platform = x.optString("platform")
    val binance = platform == "Binance"
    val badge = if (binance) Color(0xFFF0B90B) else Color(0xFF2E7BE6)
    val roi = x.optDouble("roi")
    val wrWarn = x.optBoolean("wr_curiga")
    Row(
        Modifier.fillMaxWidth().clickable { x.optString("url").takeIf { it.startsWith("https://") }?.let { runCatching { uri.openUri(it) } } },
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        Box(
            Modifier.size(34.dp).background(badge.copy(alpha = 0.16f), CircleShape)
                .border(1.dp, badge.copy(alpha = 0.55f), CircleShape),
            contentAlignment = Alignment.Center
        ) {
            Text(if (binance) "B" else platform.removePrefix("MQL5 ").take(3), color = badge, fontWeight = FontWeight.ExtraBold,
                style = MaterialTheme.typography.labelMedium)
        }
        Column(Modifier.weight(1f)) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                Text(x.optString("name"), Modifier.weight(1f, fill = false), fontWeight = FontWeight.Bold,
                    style = MaterialTheme.typography.bodyMedium, maxLines = 1, overflow = TextOverflow.Ellipsis)
                if (x.optBoolean("penuh")) Pill("PENUH", Muted)
            }
            val harga = x.optDouble("harga", 0.0)
            val sub = buildList {
                add(x.optString("aset"))
                add("${x.optInt("pengikut")} ${if (binance) "pengikut" else "pelanggan"}")
                if (!binance) add(if (harga > 0) "$${harga.toInt()}/bln" else "gratis")
            }.joinToString(" • ")
            Text(sub, style = MaterialTheme.typography.labelSmall, color = Muted, maxLines = 1, overflow = TextOverflow.Ellipsis)
        }
        Column(horizontalAlignment = Alignment.End) {
            Text("${signed(roi, 0)}%", fontWeight = FontWeight.ExtraBold, color = if (roi >= 0) BuyColor else SellColor,
                style = MaterialTheme.typography.titleSmall, textAlign = TextAlign.End)
            Text("DD ${x.optDouble("mdd").toInt()}% • WR ${x.optDouble("wr").toInt()}%${if (wrWarn) "⚠️" else ""}",
                style = MaterialTheme.typography.labelSmall, color = if (wrWarn) SellColor else Muted)
        }
    }
}
