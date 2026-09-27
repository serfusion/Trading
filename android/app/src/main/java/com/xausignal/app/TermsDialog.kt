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
private const val STAR_RISK = 0.015     // ⭐: rugi maks ±1,5% modal per sinyal
private const val NORMAL_RISK = 0.0075  // biasa: ±0,75%

/** Lot per posisi (akun Cent) supaya rugi saat SL ≈ persen risiko dari modal. */
fun suggestedLot(modalIdr: Double, idrRate: Double, risk: Double): Double {
    val usc = modalIdr / idrRate * 100.0
    val lossPer001 = LEGS * SL_POINTS            // USC per 0.01 lot untuk 5 posisi
    return (Math.floor(usc * risk / lossPer001) / 100.0).coerceAtLeast(0.01)
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
                Text("• Lot akun Cent, 5 posisi/sinyal, contoh SL \$45:", fontWeight = FontWeight.Bold)
                TableRow("Modal", "Biasa", "⭐", header = true)
                LineDivider()
                for (jt in 5..100 step 5) {
                    val modal = jt * 1_000_000.0
                    TableRow(
                        "Rp$jt jt",
                        lotText(suggestedLot(modal, rate, NORMAL_RISK)),
                        lotText(suggestedLot(modal, rate, STAR_RISK))
                    )
                }
                Text(
                    "Risiko ±0,75% (biasa) & ±1,5% (⭐) modal per sinyal. SL lebih lebar → kecilkan lot.",
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
