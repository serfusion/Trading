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

/**
 * 🌊 Ikut arus (aplikasi 4.3, izin pengguna 6 Okt 2026; cloud/api/_arus.py, docs/PISAU.md): setelah XAU/BTC/ETH
 * melonjak/jatuh cepat, ikuti arahnya. Hanya varian WR ≥ 62% di dua periode. Info saja, tanpa order otomatis.
 */
@Composable
fun ArusSection(events: List<SignalEvent>) {
    val ended = events.filter { it.type == "arus_close" || it.type == "arus_cancel" }.map { it.id }.toSet()
    val open = events.filter { it.type == "arus_signal" && it.id !in ended }
    val closes = events.filter { it.type == "arus_close" }.take(3)
    if (open.isEmpty() && closes.isEmpty()) return
    SectionTitle("🌊 Ikut arus", trailing = if (open.isEmpty()) null else "${open.size} aktif")
    open.forEach { s ->
        val fill = events.firstOrNull { it.type == "arus_fill" && it.id == s.id }
        val buy = s.dir == "BUY"
        val stop = s.str("order") == "stop"
        AppCard(accent = if (buy) BuyColor else SellColor) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                AssetCoin(s.symbol(), 38.dp)
                Column(Modifier.weight(1f)) {
                    Text(s.symbol(), fontWeight = FontWeight.ExtraBold, style = MaterialTheme.typography.titleMedium)
                    Text(if (stop && fill == null) "${s.dir} STOP — tunggu tersentuh" else "${s.dir} berjalan",
                        style = MaterialTheme.typography.labelMedium, color = Muted)
                }
                Pill(s.dir, if (buy) BuyColor else SellColor, solid = true)
            }
            val e = fill ?: s
            TileGrid(listOf(
                TileData(if (stop && fill == null) "Pasang stop" else "Entry", e.price("entry"), Gold, null),
                TileData("SL", e.price("sl"), SellColor, null),
                TileData("TP", e.price("tp"), BuyColor, null),
                TileData("Tutup paling lambat", "${s.num("hold_h")?.toInt() ?: 0} jam", Muted,
                    if (stop && fill == null) "stop berlaku 6 jam" else null),
            ))
            s.json.optJSONObject("teruji")?.let { t ->
                val l = t.optJSONArray("lama")
                val b = t.optJSONArray("baru")
                if (l != null && b != null) {
                    Text("Teruji: WR ${l.optInt(1)}% sebelum Okt 2021 • ${b.optInt(1)}% sejak itu • " +
                        "${signed(b.optDouble(2))}R/sinyal • ${t.optString("tahun")}",
                        style = MaterialTheme.typography.labelSmall, color = Muted)
                }
            }
        }
    }
    if (closes.isNotEmpty()) {
        AppCard {
            CardTitle("Tutup terakhir")
            closes.forEach { c ->
                val r = c.num("r") ?: 0.0
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    AssetCoin(c.symbol(), 28.dp)
                    Column(Modifier.weight(1f)) {
                        Text("${c.dir} ${c.symbol()}", fontWeight = FontWeight.Bold, style = MaterialTheme.typography.bodyMedium)
                        Text("${c.str("reason")} • ${c.timeText()}", style = MaterialTheme.typography.labelSmall, color = Muted)
                    }
                    Pill("${signed(r)}R".replace('.', ','), if (r > 0) BuyColor else SellColor, solid = true)
                }
            }
        }
    }
}
