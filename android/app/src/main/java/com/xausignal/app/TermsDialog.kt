package com.xausignal.app

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp

private const val SL_POINTS = 45.0      // contoh jarak SL (3 × ATR H1) dalam $
private const val LEGS = 5
private const val STAR_RISK = 0.005     // ⭐: rugi maks ±0,5% modal per sinyal (research/risk_compare.py)
private const val NORMAL_RISK = 0.0025  // biasa: setengahnya

/** Lot per posisi (akun Cent) supaya rugi saat SL ≤ persen risiko dari modal; 0 = di bawah lot minimum. */
fun suggestedLot(modalIdr: Double, idrRate: Double, risk: Double): Double {
    val usc = modalIdr / idrRate * 100.0
    val lossPer001 = LEGS * SL_POINTS            // USC per 0.01 lot untuk 5 posisi
    return Math.floor(usc * risk / lossPer001 + 1e-9) / 100.0
}

private fun lotCell(lot: Double, star: Boolean): String = when {
    lot >= 0.01 -> lotText(lot)
    star -> "0.01*"
    else -> "lewati"
}

@Composable
fun TermsDialog(rate: Double, onDismiss: () -> Unit) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Syarat & Ketentuan", fontWeight = FontWeight.Bold) },
        text = {
            Column(Modifier.verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Text("• Bukan saran investasi. Hasil tidak dijamin, bisa rugi.")
                Text("• Selalu pasang SL sesuai sinyal. Jangan tambah posisi saat minus.")
                Text("• 💰 profit historis: 💰💰💰 ≥+0,25R • 💰💰 ≥+0,12R • 💰 ≥+0,05R")
                Text("• ★ win rate historis: ★★★ ≥75% • ★★ ≥60% • ★ ≥48%", color = Gold)
                Text("• Hanya sinyal 💰 yang dikirim. Data 2007–2026, bukan jaminan.")
                Text("• ⚡ kesempatan emas (XAU konf+⭐ saat volatilitas rendah, BTC ⭐): dengan SL+ 0,7R " +
                    "WR ±63%, +0,75R/sinyal, untung 13/14 th (XAU) & 11/11 th (BTC). Tetap bisa kalah beruntun.",
                    color = Gold)
                Text("• Peringkat: ⚡ Emas > 🥈 > 🥉 > Biasa (lot ikut peringkat bila Modal diisi).")
                Text("• Prediksi berita (urutan terbaik → biasa):", fontWeight = FontWeight.Bold)
                Text("  ⚡ Sangat kuat: peluang ≥ 60% & teruji ≥ 60% di dua periode (NFP setelah rilis lalu di atas " +
                    "perkiraan: emas naik 1 jam 72% s.d. 2021 / 61% sejak Okt 2021)", color = Gold)
                Text("  🥈 Kuat: model sebelum rilis NFP/JOLTS/Fed (benar 60–65% saat diuji), peluang ≥ 60%")
                Text("  🥉 Lemah: model, peluang 55–59%")
                Text("  Biasa: dasar historis 50–57% (≈ lempar koin)")
                Text("• ⚠️ Mode perang = minyak naik ≥10% dalam 10 hari: sinyal emas historis lemah, pakai lot kecil.",
                    color = SellColor)
                Text("• ⏸️ Jeda pra-berita: sinyal XAU baru tidak dikirim ≤ 60 jam sebelum NFP/CPI/Fed (teruji 2012–2026: " +
                    "sejak Okt 2021 WR 62→65%, PF 1,56→1,96; s.d. 2021 PF 1,35→1,62; 11/14 tahun membaik). " +
                    "Posisi terbuka tetap dikelola.",
                    color = Gold)
                Text("• Lot akun Cent, 5 posisi/sinyal, contoh SL \$45:", fontWeight = FontWeight.Bold)
                TableRow("Modal (XAU)", "Risiko 0,25%", "Risiko 0,5%", header = true)
                LineDivider()
                for (jt in 5..100 step 5) {
                    val modal = jt * 1_000_000.0
                    TableRow(
                        "Rp$jt jt",
                        lotCell(suggestedLot(modal, rate, NORMAL_RISK), false),
                        lotCell(suggestedLot(modal, rate, STAR_RISK), true)
                    )
                }
                Text(
                    "Lot per posisi, akun Cent, 5 posisi, SL \$45. * = lot minimum. lewati = modal terlalu kecil.",
                    style = MaterialTheme.typography.bodySmall, color = Muted
                )
                Text(
                    "Tabel ini hanya CONTOH (SL \$45). Lot yang dipakai = lot di kartu sinyal: dihitung dari jarak SL " +
                        "sinyal itu. SL lebih jauh → lot lebih kecil, rugi Rupiah tetap ±0,25% / 0,5% modal. " +
                        "Mis. Rp50 jt, 0,5%: SL \$45 → 0.06 lot, SL \$55 → 0.05 lot.",
                    style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.Bold
                )
            }
        },
        confirmButton = { TextButton(onClick = onDismiss) { Text("Saya mengerti", fontWeight = FontWeight.Bold) } }
    )
}

@Composable
private fun TableRow(a: String, b: String, c: String, header: Boolean = false) {
    val w = if (header) FontWeight.Bold else FontWeight.Normal
    androidx.compose.foundation.layout.Row {
        Text(a, fontWeight = w, modifier = Modifier.weight(1.2f))
        Text(b, fontWeight = w, modifier = Modifier.weight(1f))
        Text(c, fontWeight = w, color = Gold, modifier = Modifier.weight(1f))
    }
}
