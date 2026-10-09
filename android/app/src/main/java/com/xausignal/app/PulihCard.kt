package com.xausignal.app

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import org.json.JSONObject
import java.util.Locale

/** Koin keranjang 🔗 dengan harga beli (urutan dari cloud). */
fun pulihKoin(s: SignalEvent): List<Pair<String, Double>> {
    val o: JSONObject = s.json.optJSONObject("koin") ?: return emptyList()
    return o.keys().asSequence().map { it to o.optDouble(it) }.filter { !it.second.isNaN() }.toList()
}

/** Harga untuk teks salin: titik desimal, tanpa pemisah ribuan. */
private fun rawSpot(v: Double): String = when {
    v >= 100 -> String.format(Locale.US, "%.2f", v)
    v >= 1 -> String.format(Locale.US, "%.4f", v)
    else -> String.format(Locale.US, "%.6f", v)
}

/**
 * 🔗 Emas pulih → kripto ikut naik (aplikasi 4.25, izin pengguna 9 Okt 2026; cloud/api/_pulih.py, docs/XAU_KRIPTO.md):
 * emas jatuh ≥ 5 ATR lalu memantul saat emas & BTC sedang searah → beli keranjang koin spot, jual setelah 48 jam.
 * Info saja, tanpa order otomatis. Ikut pilihan pair "SPOT".
 */
@Composable
fun PulihSection(events: List<SignalEvent>) {
    val ended = events.filter { it.type == "pulih_close" }.map { it.id }.toSet()
    val open = events.filter { it.type == "pulih_signal" && it.id !in ended }.take(1)
    val closes = events.filter { it.type == "pulih_close" }.take(3)
    if (open.isEmpty() && closes.isEmpty()) return
    SectionTitle("🔗 Emas pulih → kripto", trailing = if (open.isEmpty()) null else "aktif")
    open.forEach { s ->
        val koin = pulihKoin(s)
        AppCard(accent = BuyColor) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                AssetCoin("BTC", 38.dp)
                Column(Modifier.weight(1f)) {
                    Text("Beli keranjang ${koin.size} koin", fontWeight = FontWeight.ExtraBold,
                        style = MaterialTheme.typography.titleMedium)
                    Text("Emas jatuh lalu memantul • emas & BTC searah (korelasi ${fmt(s.num("korelasi"), 2).replace('.', ',')})",
                        style = MaterialTheme.typography.labelMedium, color = Muted)
                }
                Pill("BUY", BuyColor, solid = true)
            }
            TileGrid(listOf(
                TileData("Emas jatuh", "${fmt(s.num("xau_top"), 2)} → ${fmt(s.num("xau_bot"), 2)}", Gold,
                    "${fmt(s.num("atr_x"), 1).replace('.', ',')} ATR"),
                TileData("Jual semua", formatTime(s.str("deadline")), Muted, "tahan ${s.num("hold_h")?.toInt() ?: 48} jam"),
            ))
            if (koin.isNotEmpty()) {
                OrderLine(koin.map { it.first to spotPx(it.second) },
                    koin.joinToString(" / ") { "${it.first} ${rawSpot(it.second)}" },
                    "Harga beli saat sinyal. Spot saja, bagi rata (mis. 10% modal ÷ ${koin.size} koin), tanpa leverage. " +
                        "Jual semua di jam di atas.")
            }
            s.json.optJSONObject("teruji")?.let { t ->
                val l = t.optJSONArray("lama")
                val b = t.optJSONArray("baru")
                val d = t.optJSONArray("dasar_baru")
                if (l != null && b != null) {
                    Text("Teruji: naik ${l.optInt(1)}% sebelum Okt 2021 • ${b.optInt(1)}% sejak itu • rata " +
                        "${spotPct(b.optDouble(2))} per 48 jam" + (d?.let { " (beli acak ${spotPct(it.optDouble(1))})" } ?: "") +
                        " • terburuk ${fmt(t.optDouble("terburuk"), 0)}% • belum pasti",
                        style = MaterialTheme.typography.labelSmall, color = Muted)
                }
            }
        }
    }
    if (closes.isNotEmpty()) {
        AppCard {
            CardTitle("Keranjang selesai")
            closes.forEach { c ->
                val r = c.num("r_pct") ?: 0.0
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    AssetCoin("BTC", 28.dp)
                    Column(Modifier.weight(1f)) {
                        Text("Keranjang ${c.num("n")?.toInt() ?: 0} koin", fontWeight = FontWeight.Bold,
                            style = MaterialTheme.typography.bodyMedium)
                        Text("${c.num("naik")?.toInt() ?: 0} koin naik • ${c.timeText()}",
                            style = MaterialTheme.typography.labelSmall, color = Muted)
                    }
                    Pill(spotPct(r), if (r > 0) BuyColor else SellColor, solid = true)
                }
            }
        }
    }
}
