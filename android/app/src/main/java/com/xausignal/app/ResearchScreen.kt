package com.xausignal.app

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp

/**
 * Tab Riset: ringkasan hasil uji di repo (docs/BACKTEST.md, docs/RISET_GITHUB.md, docs/AUDIT_63_REPO.md).
 * Isinya statis dan ikut diperbarui bersama APK; angka harus sama dengan dokumen tersebut.
 */
@Composable
fun ResearchTab() {
    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(horizontal = 16.dp, vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        item {
            AppCard(accent = Gold) {
                Text("Hasil riset bot ini", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                Text(
                    "Diuji di ±630 ribu candle XAUUSD asli 2012–2026: spread dihitung, entry di candle berikutnya, " +
                        "SL dicek lebih dulu, tanpa melihat data masa depan. Swap & komisi belum dihitung.",
                    style = MaterialTheme.typography.bodyMedium, color = Muted
                )
                NoteBox("Tidak ada strategi yang tidak pernah rugi. Hasil masa lalu tidak menjamin masa depan.", SellColor)
            }
        }

        item { SectionTitle("Strategi yang dipakai") }
        item {
            AppCard {
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Pill("LOLOS", BuyColor, solid = true)
                    Text("Trend-following Donchian H1", fontWeight = FontWeight.Bold,
                        style = MaterialTheme.typography.titleMedium, modifier = Modifier.weight(1f))
                }
                Bullet("3 set channel: 40/15, 55/20, 80/30 (masuk saat harga menembus high/low N bar).")
                Bullet("SL 3 × ATR(20). Posisi #1 ambil TP1 = 1R, lalu SL posisi sisa pindah ke entry (SL+).")
                Bullet("Keluar (TUTUP) saat harga menembus channel exit berlawanan.")
                MetricRow {
                    Metric("Win rate", "33–41%", Gold)
                    Metric("Periode positif (R)", "4 dari 4", BuyColor)
                }
                Text(
                    "Lebih sering kalah kecil; profit datang dari sedikit trend besar. 89% dari 76 variasi " +
                        "parameternya positif di keempat periode.",
                    style = MaterialTheme.typography.bodySmall, color = Muted
                )
            }
        }

        item { SectionTitle("Hasil per periode", trailing = "saldo awal \$10.000") }
        item {
            AppCard {
                TableRow("Periode", "Skema F 0,5%\n(default)", "Skema A 0,25%\n(usulan)", header = true)
                LineDivider()
                TableRow("2012–17", "+28,6%\nDD −13,9%", "+24,0%\nDD −12,4%")
                TableRow("2018–22", "+16,3%\nDD −16,4%", "+24,9%\nDD −11,0%")
                TableRow("2022–25", "−14,9%\nDD −28,9%", "+3,7%\nDD −14,4%")
                TableRow("2025–26", "+41,0%\nDD −9,9%", "lot min.\nterlewati")
                Text(
                    "Risiko per set sinyal, engine bot yang sama dengan live. DD = penurunan terdalam dari puncak " +
                        "saldo. Skema A (tanpa TP1, tahan sampai TUTUP) adalah usulan riset dan belum aktif di bot.",
                    style = MaterialTheme.typography.bodySmall, color = Muted
                )
            }
        }

        item { SectionTitle("Ujian sinyal", trailing = "masa depan ditutup") }
        item {
            AppCard {
                Text(
                    "Bot mode SINYAL dijalankan candle demi candle; jawaban baru dibuka saat sinyal TUTUP.",
                    style = MaterialTheme.typography.bodyMedium, color = Muted
                )
                ExamRow("M15 2012–2022", "786 sinyal", "36,5% benar", "+84,9R")
                LineDivider()
                ExamRow("M15 2025–Sep 2026", "106 sinyal", "40,6% benar", "+35,7R")
                MetricRow {
                    Metric("Rata-rata benar", "+1,72R", BuyColor)
                    Metric("Rata-rata salah", "−0,82R", SellColor)
                }
            }
        }

        item { SectionTitle("Tidak lolos uji") }
        item {
            AppCard {
                FailRow("Menebak arah candle berikutnya", "47,9–52,1% ≈ lempar koin")
                FailRow("SMC (sweep → MSS → FVG/OB)", "−0,16R s/d −0,26R per trade")
                FailRow("Scalping M5/M15", "0 dari 18 varian positif")
                FailRow("Scalping berita (NFP, CPI, FOMC, ...)", "tidak ada yang konsisten positif")
                FailRow("Machine learning walk-forward", "akurasi arah 51,3%")
                FailRow("Grid / martingale", "akun \$1.000 habis 44× dalam 14 tahun")
            }
        }

        item { SectionTitle("Audit 63 repo GitHub") }
        item {
            AppCard {
                Bullet("Tidak ditemukan keylogger, pencuri password/wallet, atau unduh-lalu-jalankan yang aktif.")
                Bullet("1 repo kodenya tersandi (PyArmor + DLL) — jangan dijalankan.", SellColor)
                Bullet("4 repo mengirim saldo & profit pemakai ke Telegram penulisnya.", SellColor)
                Bullet("Strategi win-rate tinggi (62–96%) semuanya rugi setelah spread.")
                Bullet("Tidak ada script yang lebih baik dari resep bot ini, jadi tidak ada yang digabungkan.")
            }
        }

        item { SectionTitle("Pembanding & kebijakan risiko") }
        item {
            AppCard {
                KeyValue("Menabung emas \$10/bulan (2012–2026)", "+156%", BuyColor, bold = true)
                Text(
                    "Setor \$1.730 menjadi \$4.427, tanpa kemungkinan akun habis. Membeli emas tanpa leverage " +
                        "(+178%) mengalahkan semua setelan bot di 2012–2026.",
                    style = MaterialTheme.typography.bodySmall, color = Muted
                )
                LineDivider()
                KeyValue("Risiko disarankan", "0,25–0,5% per set", Gold, bold = true)
                KeyValue("Risiko 2% per trade", "98% peluang DD > 50%", SellColor, bold = true)
                KeyValue("Martingale", "bangkrut di 100% simulasi", SellColor, bold = true)
            }
        }
        item {
            NoteBox(
                "Sumber lengkap di repo: docs/BACKTEST.md, docs/RISET_GITHUB.md, docs/AUDIT_63_REPO.md. " +
                    "Selalu uji di akun demo sebelum memakai uang sungguhan.",
                Muted
            )
        }
        item { Footer() }
    }
}

@Composable
private fun Bullet(text: String, color: Color = Gold) {
    Row {
        Text("•", color = color, fontWeight = FontWeight.Bold, modifier = Modifier.padding(end = 8.dp))
        Text(text, style = MaterialTheme.typography.bodyMedium)
    }
}

@Composable
private fun TableRow(label: String, a: String, b: String, header: Boolean = false) {
    val buy = BuyColor
    val sell = SellColor
    val muted = Muted
    val cellColor = { v: String ->
        when {
            header -> muted
            v.startsWith("+") -> buy
            v.startsWith("−") -> sell
            else -> muted
        }
    }
    Row(verticalAlignment = Alignment.CenterVertically) {
        Text(
            label, modifier = Modifier.weight(1f),
            style = if (header) MaterialTheme.typography.labelMedium else MaterialTheme.typography.bodyMedium,
            fontWeight = if (header) FontWeight.Bold else FontWeight.Medium,
            color = if (header) Muted else Color.Unspecified
        )
        listOf(a, b).forEach { v ->
            Text(
                v, modifier = Modifier.weight(1.2f), textAlign = TextAlign.End,
                style = if (header) MaterialTheme.typography.labelMedium else MaterialTheme.typography.bodyMedium,
                fontWeight = FontWeight.Bold, color = cellColor(v)
            )
        }
    }
}

@Composable
private fun ExamRow(data: String, count: String, correct: String, total: String) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Column(Modifier.weight(1f)) {
            Text(data, fontWeight = FontWeight.Bold)
            Text("$count • $correct", style = MaterialTheme.typography.bodySmall, color = Muted)
        }
        Text(total, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold, color = BuyColor)
    }
}

@Composable
private fun FailRow(name: String, result: String) {
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
        Pill("GAGAL", SellColor)
        Column(Modifier.weight(1f)) {
            Text(name, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Medium)
            Text(result, style = MaterialTheme.typography.bodySmall, color = Muted)
        }
    }
}
