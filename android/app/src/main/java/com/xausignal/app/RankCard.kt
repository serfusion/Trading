package com.xausignal.app

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp

/**
 * 🏆 Info sinyal (aplikasi 3.27, permintaan pengguna 3 Okt 2026): urutan kategori 💰 terbaik → terlemah dari hasil
 * teruji (replay kode cloud, spread asli Exness, sejak Okt 2021; cloud/api/riwayat.json "kat"), lalu saran entry:
 * modal, rugi maks per sinyal, dan lot per posisi untuk SL tipikal setahun terakhir ("risk_med").
 */
@Composable
fun RankCard(money: MoneySettings) {
    androidx.compose.runtime.LaunchedEffect(Unit) { Verified.load() }
    val d = Verified.data
    if (d == null) {
        Text("Memuat… (butuh alamat cloud & cloud terbaru)", color = Muted, style = MaterialTheme.typography.labelSmall)
        return
    }
    data class Row3(val asset: String, val cat: String, val n: Int, val wr: Double, val avg: Double, val ini: Double?,
                    val sent: Boolean)
    val rows = mutableListOf<Row3>()
    for (a in listOf("XAU", "BTC", "ETH")) {
        val obj = d.optJSONObject(a) ?: continue
        val live = obj.optJSONObject("kat")             // kategori yang dikirim: hasil replay live
        val all = obj.optJSONObject("kat_semua")        // semua kategori (termasuk tidak dikirim)
        val names = ((live?.keys()?.asSequence()?.toList() ?: emptyList()) +
            (all?.keys()?.asSequence()?.toList() ?: emptyList())).distinct()
        for (c in names) {
            // penanda "dikirim" dari cloud (BTC konf dimatikan 3 Okt 2026); data lama tanpa penanda: ada di replay live
            val flag = all?.optJSONObject(c)?.takeIf { it.has("dikirim") }?.optBoolean("dikirim")
                ?: live?.optJSONObject(c)?.takeIf { it.has("dikirim") }?.optBoolean("dikirim")
            val sent = flag ?: (live?.has(c) == true)
            val k = (if (sent) live?.optJSONObject(c) else null) ?: all?.optJSONObject(c) ?: live?.optJSONObject(c)
                ?: continue
            val b = k.optJSONObject("baru") ?: continue
            if (b.optInt("n") == 0) continue
            val ini = k.optJSONObject("tahun_ini")?.takeIf { it.optInt("n") > 0 }?.optDouble("avg")
            rows += Row3(a, c, b.optInt("n"), b.optDouble("wr"), b.optDouble("avg"), ini, sent)
        }
    }
    // lapisan 🔁 (lot ½) dan gap pekan forex (aplikasi 3.33): replay kode cloud, spread asli/akun Standard
    for (a in listOf("XAU", "BTC")) {
        val b = d.optJSONObject(a)?.optJSONObject("lapis")?.optJSONObject("baru") ?: continue
        if (b.optInt("n") > 0) rows += Row3(a, "lapisan 🔁 (lot ½)", b.optInt("n"), b.optDouble("wr"), b.optDouble("avg"),
            null, true)
    }
    d.optJSONObject("GAP")?.let { gap ->
        for (pair in gap.keys()) {
            val b = gap.optJSONObject(pair)?.optJSONObject("baru") ?: continue
            if (b.optInt("n") > 0) rows += Row3("Gap", "$pair (${b.optInt("n")}×)", b.optInt("n"), b.optDouble("wr"),
                b.optDouble("avg"), null, true)
        }
    }
    if (rows.isEmpty()) return
    fun bags(avg: Double) = if (avg >= 0.245) 3 else if (avg >= 0.12) 2 else if (avg >= 0.05) 1 else 0
    AppCard {
        Text("🏆 Urutan sinyal terbaik (teruji sejak Okt 2021)", fontWeight = FontWeight.Bold)
        rows.sortedByDescending { it.avg }.forEachIndexed { i, r ->
            val m = bags(r.avg)
            Row(Modifier.padding(top = 2.dp), verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                RankBadge(i + 1)
                Column(Modifier.weight(1f)) {
                    Text("${r.asset} ${r.cat}", fontWeight = FontWeight.Bold, style = MaterialTheme.typography.bodySmall)
                    Text((if (m > 0) "💰".repeat(m) + "  " else "") + "WR ${fmt(r.wr, 0)}% • " +
                        if (r.sent) "dikirim" else "tidak dikirim",
                        color = if (r.sent) Muted else Muted.copy(alpha = 0.6f), style = MaterialTheme.typography.labelSmall)
                }
                Text("${signed(r.avg)}R".replace('.', ','), fontWeight = FontWeight.ExtraBold,
                    color = if (r.avg < 0.05) SellColor else BuyColor, style = MaterialTheme.typography.labelLarge)
            }
        }
        Text("💰 = untung per sinyal (≥0,05R 💰, ≥0,12R 💰💰, ≥0,25R 💰💰💰). — = tidak menguntungkan. Gap: (n×) = " +
            "jumlah sinyal sejak 2021, masih sedikit.", color = Muted, style = MaterialTheme.typography.labelSmall)
        LineDivider()
        Text("💼 Saran entry", fontWeight = FontWeight.Bold)
        if (money.modalIdr <= 0) {
            Text("Isi modal di Pengaturan agar lot dihitung otomatis.", color = Muted,
                style = MaterialTheme.typography.labelSmall)
            return@AppCard
        }
        val risk = money.balance * money.riskPct / 100.0
        Text("Modal ${idrText(money.modalIdr)} (${fmt(money.balance, 0)} ${money.currency}) • rugi maks " +
            "${fmt(money.riskPct, 2).replace('.', ',')}% = ${fmt(risk, 0)} ${money.currency} per sinyal",
            style = MaterialTheme.typography.bodySmall)
        for ((a, pv) in listOf("XAU" to 1.0, "BTC" to 0.01)) {
            val sl = d.optJSONObject(a)?.optDouble("risk_med") ?: continue
            if (sl.isNaN() || sl <= 0) continue
            val lot = maxOf(0.01, Math.floor(risk / (sl * 5 * pv) + 1e-9) / 100.0)
            Text("$a: 5 posisi × ${lotText(lot)} lot (SL tipikal ${fmt(sl, 0)} poin)",
                style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.Bold, color = Gold)
        }
        Text("Lot pasti tampil di kartu sinyal (SL tiap sinyal berbeda). Lemah = jangan entry / lot kecil.",
            color = Muted, style = MaterialTheme.typography.labelSmall)
    }
}

/** Nomor urut dalam lingkaran: 1 emas, 2 perak, 3 perunggu. */
@Composable
private fun RankBadge(n: Int) {
    val (c1, c2) = when (n) {
        1 -> Color(0xFFFFE08A) to Color(0xFFD39A1E)
        2 -> Color(0xFFF1F4F8) to Color(0xFF9AA3AF)
        3 -> Color(0xFFF6C29A) to Color(0xFFB0662E)
        else -> CardHigh to CardHigh
    }
    Box(
        Modifier.size(28.dp).background(Brush.linearGradient(listOf(c1, c2)), CircleShape)
            .border(1.dp, if (n > 3) LineColor else Color.White.copy(alpha = 0.4f), CircleShape),
        contentAlignment = Alignment.Center
    ) {
        Text("$n", fontWeight = FontWeight.Black, style = MaterialTheme.typography.labelMedium,
            color = if (n > 3) Muted else Color(0xFF1B1204))
    }
}
