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
                Text("• ★ kuning = win rate historis (★★★ ≥75%, ★★ ≥60%, ★ ≥48%).", color = Gold)
                Text("• 💸 = profit rata-rata historis per sinyal (💸💸💸 ≥+0,25R, 💸💸 ≥+0,12R, 💸 ≥+0,05R).")
                Text("• Angka WR & profit dari data 2007–2026, bukan jaminan hasil ke depan.")
                Text("• Lot akun Cent, 5 posisi/sinyal, contoh SL \$45:", fontWeight = FontWeight.Bold)
                TableRow("Modal", "Lainnya", "💸", header = true)
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
                    "Rugi maks per sinyal ±0,5% modal (💸) & ±0,25% (lainnya). * = lot minimum, risiko sedikit " +
                        "di atas 0,5%. lewati = modal terlalu kecil untuk sinyal biasa. SL lebih lebar → kecilkan lot.",
                    style = MaterialTheme.typography.bodySmall, color = Muted
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
