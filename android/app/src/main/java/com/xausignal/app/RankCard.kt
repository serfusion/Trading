package com.xausignal.app

import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp

/**
 * 🏆 Info sinyal (aplikasi 3.27, permintaan pengguna 3 Okt 2026): urutan kategori 💰 terbaik → terlemah dari hasil
 * teruji (replay kode cloud, spread asli Exness, sejak Okt 2021; cloud/api/riwayat.json "kat"), lalu saran entry:
 * modal, rugi maks per sinyal, dan lot per posisi untuk SL tipikal setahun terakhir ("risk_med").
 */
@Composable
fun RankCard(money: MoneySettings) {
    val d = Verified.data ?: return
    data class Row3(val asset: String, val cat: String, val n: Int, val wr: Double, val avg: Double, val ini: Double?)
    val rows = mutableListOf<Row3>()
    for (a in listOf("XAU", "BTC")) {
        val kat = d.optJSONObject(a)?.optJSONObject("kat") ?: continue
        for (c in kat.keys()) {
            val k = kat.optJSONObject(c) ?: continue
            val b = k.optJSONObject("baru") ?: continue
            if (b.optInt("n") == 0) continue
            val ini = k.optJSONObject("tahun_ini")?.takeIf { it.optInt("n") > 0 }?.optDouble("avg")
            rows += Row3(a, c, b.optInt("n"), b.optDouble("wr"), b.optDouble("avg"), ini)
        }
    }
    if (rows.isEmpty()) return
    AppCard {
        Text("🏆 Urutan sinyal terbaik (teruji sejak 2021)", fontWeight = FontWeight.Bold)
        rows.sortedByDescending { it.avg }.forEachIndexed { i, r ->
            val weak = r.avg < 0.1
            Row(Modifier.padding(top = 2.dp)) {
                Text("${i + 1}. ${r.asset} ${r.cat}", Modifier.weight(1.4f), fontWeight = FontWeight.Medium,
                    style = MaterialTheme.typography.bodySmall)
                Text("WR ${fmt(r.wr, 0)}%", Modifier.weight(0.8f), style = MaterialTheme.typography.labelSmall)
                Text("${signed(r.avg)}R".replace('.', ','), Modifier.weight(0.8f), fontWeight = FontWeight.Bold,
                    color = if (weak) SellColor else BuyColor, style = MaterialTheme.typography.labelSmall)
                Text(if (weak) "lemah" else r.ini?.let { "2026 ${signed(it)}R".replace('.', ',') } ?: "",
                    Modifier.weight(1f), color = Muted, style = MaterialTheme.typography.labelSmall)
            }
        }
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
