package com.xausignal.app

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp

/**
 * 🎨 Tampilan (aplikasi 4.0, permintaan pengguna 4 Okt 2026): bentuk kartu (kotak / bulat / kapsul), susunan angka
 * (grid / daftar), win rate (lingkaran / bar), warna aksen, dan tema. Berlaku langsung, contoh di bawah ikut berubah.
 */
@Composable
fun AppearanceDialog(onDismiss: () -> Unit) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("🎨 Tampilan", fontWeight = FontWeight.ExtraBold) },
        text = { AppearanceContent() },
        confirmButton = { TextButton(onClick = onDismiss) { Text("Selesai", fontWeight = FontWeight.Bold) } },
    )
}

/** Isi pilihan 🎨 Tampilan (juga dipakai pratinjau). */
@Composable
fun AppearanceContent() {
    Column(Modifier.verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        CardTitle("Bentuk kartu")
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            listOf("Kotak" to 0, "Bulat" to 1, "Kapsul" to 2).forEach { (name, v) ->
                ShapeOption(name, v, Modifier.weight(1f))
            }
        }
        CardTitle("Susunan angka sinyal")
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Choice("▦ Grid", UiPrefs.grid, Modifier.weight(1f)) { UiPrefs.grid = true; UiPrefs.save() }
            Choice("☰ Daftar", !UiPrefs.grid, Modifier.weight(1f)) { UiPrefs.grid = false; UiPrefs.save() }
        }
        CardTitle("Win rate")
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Choice("◯ Lingkaran", UiPrefs.ring, Modifier.weight(1f)) { UiPrefs.ring = true; UiPrefs.save() }
            Choice("▬ Bar", !UiPrefs.ring, Modifier.weight(1f)) { UiPrefs.ring = false; UiPrefs.save() }
        }
        CardTitle("Warna aksen")
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            ACCENTS.forEachIndexed { i, a ->
                val on = UiPrefs.accent == i
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Box(
                        Modifier
                            .size(40.dp)
                            .border(2.dp, if (on) MaterialTheme.colorScheme.onSurface else LineColor, CircleShape)
                            .padding(4.dp)
                            .background(Brush.linearGradient(listOf(a.dark, a.dark2)), CircleShape)
                            .clickable { UiPrefs.accent = i; UiPrefs.save() },
                        contentAlignment = Alignment.Center
                    ) {
                        if (on) Text("✓", color = onColor(a.dark), fontWeight = FontWeight.Black)
                    }
                    Text(a.name, style = MaterialTheme.typography.labelSmall, color = if (on) Gold else Muted)
                }
            }
        }
        CardTitle("Tema")
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            listOf("🌙 Gelap" to 1, "☀️ Terang" to 2, "📱 Ikut HP" to 0).forEach { (name, v) ->
                Choice(name, UiPrefs.theme == v, Modifier.weight(1f)) { UiPrefs.theme = v; UiPrefs.save() }
            }
        }
        Spacer(Modifier.height(4.dp))
        CardTitle("Contoh")
        PreviewCard()
    }
}

@Composable
private fun ShapeOption(name: String, value: Int, modifier: Modifier) {
    val on = UiPrefs.shape == value
    val r = when (value) {
        0 -> 4.dp
        2 -> 18.dp
        else -> 11.dp
    }
    Column(
        modifier
            .border(2.dp, if (on) Gold else LineColor, RoundedCornerShape(r + 4.dp))
            .clickable { UiPrefs.shape = value; UiPrefs.save() }
            .padding(10.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(6.dp)
    ) {
        Box(
            Modifier
                .fillMaxWidth()
                .height(30.dp)
                .background(Brush.linearGradient(listOf(Gold.copy(alpha = if (on) 0.9f else 0.35f), Gold2.copy(alpha = 0.3f))),
                    RoundedCornerShape(r))
        )
        Text(name, style = MaterialTheme.typography.labelMedium, fontWeight = if (on) FontWeight.Bold else FontWeight.Medium,
            color = if (on) Gold else Muted)
    }
}

/** Kartu contoh: ikut berubah saat pilihan diganti. */
@Composable
private fun PreviewCard() {
    AppCard(accent = BuyColor) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            AssetCoin("XAU/USD", 34.dp)
            Text("XAU/USD", fontWeight = FontWeight.ExtraBold, modifier = Modifier.weight(1f))
            Pill("BUY", BuyColor, solid = true)
        }
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            WinGauge(63, 37, 52.dp)
            Column(Modifier.weight(1f)) {
                TileGrid(listOf(
                    TileData("Entry", "3,912.40", Gold),
                    TileData("TP1", "3,925.10", BuyColor),
                ))
            }
        }
    }
}
