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
    var fromCloud by mutableStateOf(false)
    var reason by mutableStateOf("")
    var retry by mutableStateOf(0)
    suspend fun load(context: android.content.Context) {
        if (fromCloud) return
        val (d, why) = withContext(Dispatchers.IO) { ChatClient.copytrader() }
        if (d != null) {
            data = d; fromCloud = true; reason = ""
            return
        }
        reason = why
        if (data == null) {                         // cadangan: salinan yang dibundel di APK (assets/copytrader.json)
            data = withContext(Dispatchers.IO) {
                runCatching { JSONObject(context.assets.open("copytrader.json").bufferedReader().use { it.readText() }) }
                    .getOrNull()
            }
        }
    }
}

/**
 * 👥 Copy trader terbaik (aplikasi 4.7–4.9; research/copy_pilih.py, docs/COPY_TRADE.md): gabungan OKX, Bitget,
 * Hyperliquid, eToro, Binance, MQL5 yang lolos saringan teruji (untung di 2 paruh, DD ≤ 20%, WR ≥ 60%, pengikut nyata),
 * diperbarui mingguan oleh GitHub Actions. Ketuk = buka halaman salin. Info saja — aplikasi tidak menyalin order.
 */
@Composable
fun CopyTraderSection() {
    val context = androidx.compose.ui.platform.LocalContext.current
    LaunchedEffect(CopyTraders.retry) { CopyTraders.load(context) }
    val d = CopyTraders.data
    if (d == null) {                                // belum termuat / cloud gagal → tetap tampil + coba lagi
        SectionTitle("👥 Copy trader terbaik")
        AppCard {
            Row(Modifier.fillMaxWidth().clickable { CopyTraders.retry++ }, verticalAlignment = Alignment.CenterVertically) {
                Text(if (CopyTraders.reason.isBlank()) "Memuat…" else "Gagal: ${CopyTraders.reason} • ketuk untuk coba lagi",
                    Modifier.weight(1f), style = MaterialTheme.typography.labelSmall, color = Muted)
            }
        }
        return
    }
    val gab = d.optJSONArray("gabungan")
    val all = if (gab != null) (0 until gab.length()).mapNotNull { gab.optJSONObject(it) }
    else listOf("etoro", "binance", "mql5").flatMap { k ->       // cloud sebelum 4.9
        val a = d.optJSONArray(k)
        (0 until (a?.length() ?: 0)).mapNotNull { a?.optJSONObject(it) }
    }
    if (all.isEmpty()) return
    var open by rememberSaveable { mutableStateOf(false) }
    SectionTitle("👥 Copy trader terbaik", trailing = "${all.size}")
    AppCard {
        (if (open) all else all.take(5)).forEach { CopyRow(it) }
        Row(
            Modifier.fillMaxWidth().clickable { open = !open }.padding(top = 2.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text("Diperbarui ${d.optString("dibuat")}" + if (CopyTraders.fromCloud) "" else " (offline)",
                Modifier.weight(1f).clickable { if (!CopyTraders.fromCloud) CopyTraders.retry++ },
                style = MaterialTheme.typography.labelSmall, color = Muted)
            Text(if (open) "Tutup ▴" else "Semua ▾", style = MaterialTheme.typography.labelMedium,
                fontWeight = FontWeight.Bold, color = Gold)
        }
        if (open) {
            if (!CopyTraders.fromCloud && CopyTraders.reason.isNotBlank()) {
                Text("Cloud: ${CopyTraders.reason} — memakai data bawaan APK", style = MaterialTheme.typography.labelSmall,
                    color = SellColor)
            }
            val invalid = d.optJSONArray("invalid")
            if (invalid != null && invalid.length() > 0) {
                Text("Invalid: ${(0 until invalid.length()).joinToString { invalid.optString(it) }} (data minggu lalu)",
                    style = MaterialTheme.typography.labelSmall, color = SellColor)
            }
            Text(d.optString("singkat").ifBlank { d.optString("kesimpulan") },
                style = MaterialTheme.typography.labelSmall, color = Muted)
        }
    }
}

private data class Badge(val text: String, val color: Color)

private fun badgeOf(platform: String): Badge = when (platform) {
    "Binance" -> Badge("B", Color(0xFFF0B90B))
    "eToro" -> Badge("e", Color(0xFF13C636))
    "OKX" -> Badge("O", Color(0xFFB0B7C3))
    "Bitget" -> Badge("Bg", Color(0xFF00C2CC))
    "Hyperliquid" -> Badge("H", Color(0xFF50D2C1))
    else -> Badge(platform.removePrefix("MQL5 ").take(3), Color(0xFF2E7BE6))
}

@Composable
private fun CopyRow(x: JSONObject) {
    val uri = LocalUriHandler.current
    val platform = x.optString("platform")
    val b = badgeOf(platform)
    val roi = x.optDouble("roi")
    val wrWarn = x.optBoolean("wr_curiga")
    Row(
        Modifier.fillMaxWidth().clickable {
            x.optString("url").takeIf { it.startsWith("https://") }?.let { runCatching { uri.openUri(it) } }
        },
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        Box(
            Modifier.size(34.dp).background(b.color.copy(alpha = 0.16f), CircleShape)
                .border(1.dp, b.color.copy(alpha = 0.55f), CircleShape),
            contentAlignment = Alignment.Center
        ) {
            Text(b.text, color = b.color, fontWeight = FontWeight.ExtraBold, style = MaterialTheme.typography.labelMedium)
        }
        Column(Modifier.weight(1f)) {
            Text(x.optString("name"), fontWeight = FontWeight.Bold, style = MaterialTheme.typography.bodyMedium,
                maxLines = 1, overflow = TextOverflow.Ellipsis)
            Text("${if (platform.startsWith("MQL5")) "MQL5" else platform} • ${x.optInt("pengikut")} pengikut" +
                if (x.optBoolean("penuh")) " • penuh" else "",
                style = MaterialTheme.typography.labelSmall, color = Muted, maxLines = 1, overflow = TextOverflow.Ellipsis)
        }
        Column(horizontalAlignment = Alignment.End) {
            Text("${signed(roi, 0)}%", fontWeight = FontWeight.ExtraBold, color = if (roi >= 0) BuyColor else SellColor,
                style = MaterialTheme.typography.titleSmall, textAlign = TextAlign.End)
            Text("${x.optString("periode", "1 th")} • DD ${x.optDouble("mdd").toInt()}% • WR ${x.optDouble("wr").toInt()}%" +
                if (wrWarn) "⚠️" else "",
                style = MaterialTheme.typography.labelSmall, color = if (wrWarn) SellColor else Muted)
        }
    }
}
