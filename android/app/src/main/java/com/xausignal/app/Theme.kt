package com.xausignal.app

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.ReadOnlyComposable
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.compositeOver
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import java.util.Locale

const val BRAND = "Superfal-Dev"
const val TAGLINE = "Sinyal & auto order XAUUSD"

/** Warna khusus trading; versi gelap & terang supaya teks tetap kontras. */
data class TradeColors(
    val buy: Color,
    val sell: Color,
    val gold: Color,
    val muted: Color,
    val card: Color,
    val cardHigh: Color,
    val line: Color,
)

private val DarkTrade = TradeColors(
    buy = Color(0xFF3DD68C), sell = Color(0xFFFF6B6B), gold = Color(0xFFE8B930),
    muted = Color(0xFF9AA4B2), card = Color(0xFF171C24), cardHigh = Color(0xFF1F2530), line = Color(0xFF2A313D),
)
private val LightTrade = TradeColors(
    buy = Color(0xFF12803F), sell = Color(0xFFC62828), gold = Color(0xFF8A6500),
    muted = Color(0xFF5B6472), card = Color(0xFFFFFFFF), cardHigh = Color(0xFFF3EFE4), line = Color(0xFFE2DCCB),
)

private val LocalTrade = staticCompositionLocalOf { DarkTrade }

val BuyColor: Color @Composable @ReadOnlyComposable get() = LocalTrade.current.buy
val SellColor: Color @Composable @ReadOnlyComposable get() = LocalTrade.current.sell
val Gold: Color @Composable @ReadOnlyComposable get() = LocalTrade.current.gold
val Muted: Color @Composable @ReadOnlyComposable get() = LocalTrade.current.muted
val CardColor: Color @Composable @ReadOnlyComposable get() = LocalTrade.current.card
val CardHigh: Color @Composable @ReadOnlyComposable get() = LocalTrade.current.cardHigh
val LineColor: Color @Composable @ReadOnlyComposable get() = LocalTrade.current.line

@Composable
fun dirColor(dir: String?): Color = when (dir) {
    "BUY" -> BuyColor
    "SELL" -> SellColor
    else -> Muted
}

@Composable
fun XauTheme(content: @Composable () -> Unit) {
    val dark = isSystemInDarkTheme()
    val trade = if (dark) DarkTrade else LightTrade
    val scheme = if (dark) {
        darkColorScheme(
            primary = trade.gold, onPrimary = Color(0xFF1B1400),
            primaryContainer = Color(0xFF3A2F0B), onPrimaryContainer = Color(0xFFF5D77A),
            secondary = trade.gold, onSecondary = Color(0xFF1B1400),
            secondaryContainer = Color(0xFF2E2710), onSecondaryContainer = Color(0xFFF5D77A),
            background = Color(0xFF0E1116), onBackground = Color(0xFFE8EAED),
            surface = Color(0xFF0E1116), onSurface = Color(0xFFE8EAED),
            surfaceVariant = trade.cardHigh, onSurfaceVariant = trade.muted, surfaceTint = trade.cardHigh,
            surfaceContainerLowest = Color(0xFF0A0D11), surfaceContainerLow = Color(0xFF13171D),
            surfaceContainer = trade.card, surfaceContainerHigh = trade.cardHigh,
            surfaceContainerHighest = Color(0xFF262D39),
            outline = trade.line, outlineVariant = trade.line, error = trade.sell,
        )
    } else {
        lightColorScheme(
            primary = trade.gold, onPrimary = Color.White,
            primaryContainer = Color(0xFFF3E3B0), onPrimaryContainer = Color(0xFF2A1F00),
            secondary = trade.gold, onSecondary = Color.White,
            secondaryContainer = Color(0xFFF1E6C4), onSecondaryContainer = Color(0xFF2A1F00),
            background = Color(0xFFF7F5EF), onBackground = Color(0xFF1A1C20),
            surface = Color(0xFFF7F5EF), onSurface = Color(0xFF1A1C20),
            surfaceVariant = trade.cardHigh, onSurfaceVariant = trade.muted, surfaceTint = trade.line,
            surfaceContainerLowest = Color.White, surfaceContainerLow = Color(0xFFFBF9F4),
            surfaceContainer = Color(0xFFF5F2EA), surfaceContainerHigh = Color(0xFFEFEBE1),
            surfaceContainerHighest = Color(0xFFE9E4D8),
            outline = trade.line, outlineVariant = trade.line, error = trade.sell,
        )
    }
    CompositionLocalProvider(LocalTrade provides trade) {
        MaterialTheme(colorScheme = scheme, content = content)
    }
}

// ------------------------------------------------------------------ angka

/** Lot selalu kelipatan 0,01 (0.01, 0.02, ...). Membuang sisa float seperti 0.009999999776. */
fun roundLot(value: Double): Double = Math.round(value * 100.0) / 100.0

fun lotText(value: Double?): String =
    if (value == null) "-" else String.format(Locale.US, "%.2f", roundLot(value))

/** Baca lot dari teks pengguna ("0,02" / "0.02"). Null bila bukan kelipatan 0,01 atau di luar batas. */
fun parseLot(text: String, max: Double = 100.0): Double? {
    val v = text.trim().replace(",", ".").toDoubleOrNull() ?: return null
    val cents = v * 100.0
    if (Math.abs(cents - Math.round(cents)) > 1e-6) return null
    val lot = roundLot(v)
    return if (lot < 0.01 || lot > max) null else lot
}

fun signed(value: Double, digits: Int = 2): String = (if (value > 0) "+" else "") + fmt(value, digits)

// ------------------------------------------------------------------ komponen

/** Kartu standar aplikasi: sudut membulat, garis tipis, padding lega. */
@Composable
fun AppCard(
    modifier: Modifier = Modifier,
    accent: Color? = null,
    content: @Composable ColumnScope.() -> Unit,
) {
    Card(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(
            containerColor = if (accent != null) accent.copy(alpha = 0.12f).compositeOver(CardColor) else CardColor,
            contentColor = MaterialTheme.colorScheme.onSurface,
        ),
        border = BorderStroke(1.dp, accent?.copy(alpha = 0.45f) ?: LineColor),
    ) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp), content = content)
    }
}

@Composable
fun SectionTitle(text: String, modifier: Modifier = Modifier, trailing: String? = null) {
    Row(
        modifier.fillMaxWidth().padding(top = 12.dp, bottom = 2.dp, start = 4.dp, end = 4.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(Modifier.size(width = 4.dp, height = 18.dp).background(Gold, RoundedCornerShape(2.dp)))
        Text(
            text, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold,
            modifier = Modifier.padding(start = 8.dp).weight(1f)
        )
        if (trailing != null) Text(trailing, style = MaterialTheme.typography.labelMedium, color = Muted)
    }
}

@Composable
fun CardTitle(text: String, modifier: Modifier = Modifier) {
    Text(
        text.uppercase(Locale("id")),
        style = MaterialTheme.typography.labelMedium,
        fontWeight = FontWeight.Bold,
        color = Muted,
        letterSpacing = 1.sp,
        modifier = modifier,
    )
}

/** Label kecil berwarna (BUY, SELL, TUTUP, AUTO ON, ...). */
@Composable
fun Pill(text: String, color: Color, solid: Boolean = false, modifier: Modifier = Modifier) {
    Text(
        text,
        color = if (solid) Color.White else color,
        fontWeight = FontWeight.Bold,
        style = MaterialTheme.typography.labelMedium,
        maxLines = 1,
        modifier = modifier
            .background(if (solid) color else color.copy(alpha = 0.16f), RoundedCornerShape(50))
            .padding(horizontal = 10.dp, vertical = 4.dp)
    )
}

@Composable
fun StatusDot(color: Color) {
    Box(Modifier.size(10.dp).background(color, CircleShape))
}

/**
 * Kotak angka: label kecil di atas, nilai besar di bawah. Dipakai berjajar dalam Row.
 * [compact] = huruf lebih kecil untuk 3–4 kotak sebaris (mis. harga 4,123.45).
 */
@Composable
fun RowScope.Metric(label: String, value: String, color: Color = Color.Unspecified, compact: Boolean = false) {
    Column(
        Modifier
            .weight(1f)
            .background(CardHigh, RoundedCornerShape(12.dp))
            .padding(horizontal = if (compact) 8.dp else 10.dp, vertical = 8.dp)
    ) {
        Text(label, style = MaterialTheme.typography.labelSmall, color = Muted, maxLines = 1)
        Text(
            value,
            style = if (compact) MaterialTheme.typography.titleSmall else MaterialTheme.typography.titleMedium,
            fontWeight = FontWeight.Bold, color = color, maxLines = 1
        )
    }
}

@Composable
fun MetricRow(content: @Composable RowScope.() -> Unit) {
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp), content = content)
}

/** Baris "label ........ nilai". */
@Composable
fun KeyValue(label: String, value: String, color: Color = Color.Unspecified, bold: Boolean = false) {
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        Text(label, style = MaterialTheme.typography.bodyMedium, color = Muted, modifier = Modifier.weight(1f))
        Text(
            value, style = MaterialTheme.typography.bodyMedium, color = color,
            fontWeight = if (bold) FontWeight.Bold else FontWeight.Medium, textAlign = TextAlign.End
        )
    }
}

@Composable
fun LineDivider() {
    Box(Modifier.fillMaxWidth().height(1.dp).background(LineColor))
}

/** Bar menang/kalah: hijau = porsi menang, merah = porsi kalah. */
@Composable
fun WinBar(wins: Int, losses: Int) {
    val total = wins + losses
    Row(
        Modifier
            .fillMaxWidth()
            .height(8.dp)
            .background(CardHigh, RoundedCornerShape(4.dp))
    ) {
        if (total == 0) return@Row
        if (wins > 0) Box(Modifier.weight(wins.toFloat()).height(8.dp).background(BuyColor, RoundedCornerShape(4.dp)))
        if (losses > 0) {
            Box(Modifier.weight(losses.toFloat()).height(8.dp).background(SellColor, RoundedCornerShape(4.dp)))
        }
    }
}

/** Kotak catatan/peringatan dengan garis kiri berwarna. */
@Composable
fun NoteBox(text: String, color: Color = Gold) {
    Row(
        Modifier
            .fillMaxWidth()
            .background(color.copy(alpha = 0.10f), RoundedCornerShape(12.dp))
            .padding(12.dp)
    ) {
        Box(Modifier.width(3.dp).height(18.dp).background(color, RoundedCornerShape(2.dp)))
        Text(
            text, style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurface, modifier = Modifier.padding(start = 10.dp)
        )
    }
}

@Composable
fun Footer() {
    Column(
        Modifier.fillMaxWidth().padding(vertical = 20.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Text(BRAND, style = MaterialTheme.typography.labelLarge, color = Gold, fontWeight = FontWeight.Bold)
        Text(
            "Bukan saran investasi • hasil tidak dijamin",
            style = MaterialTheme.typography.labelSmall, color = Muted
        )
    }
}

/**
 * Input lot yang selalu pas 0.01, 0.02, ...: tombol −/+ (langkah 0,01), kotak teks, dan pilihan cepat.
 * [text] disimpan sebagai teks supaya pengguna bisa mengetik bebas; validasi dengan [parseLot].
 */
@Composable
fun LotInput(
    text: String,
    onChange: (String) -> Unit,
    label: String,
    max: Double,
    presets: List<Double> = listOf(0.01, 0.02, 0.03, 0.05, 0.10),
    enabled: Boolean = true,
) {
    val current = parseLot(text, max)
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            StepButton("−", enabled && (current ?: 0.0) > 0.01) {
                onChange(lotText(((current ?: 0.02) - 0.01).coerceIn(0.01, max)))
            }
            OutlinedTextField(
                value = text,
                onValueChange = { onChange(it.replace(",", ".")) },
                singleLine = true,
                enabled = enabled,
                label = { Text(label) },
                isError = current == null,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                textStyle = MaterialTheme.typography.titleMedium.copy(
                    fontWeight = FontWeight.Bold, textAlign = TextAlign.Center
                ),
                modifier = Modifier.weight(1f)
            )
            StepButton("+", enabled && (current ?: 0.0) < max) {
                onChange(lotText(((current ?: 0.0) + 0.01).coerceIn(0.01, max)))
            }
        }
        if (current == null) {
            Text("Isi 0.01 – ${lotText(max)}, kelipatan 0.01", style = MaterialTheme.typography.bodySmall,
                color = SellColor)
        }
        Row(
            Modifier.horizontalScroll(rememberScrollState()),
            horizontalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            presets.filter { it <= max + 1e-9 }.forEach { p ->
                val selected = current != null && Math.abs(current - p) < 1e-9
                Text(
                    lotText(p),
                    style = MaterialTheme.typography.labelLarge,
                    fontWeight = FontWeight.Bold,
                    color = if (selected) MaterialTheme.colorScheme.onPrimary else MaterialTheme.colorScheme.onSurface,
                    modifier = Modifier
                        .background(if (selected) Gold else CardHigh, RoundedCornerShape(50))
                        .border(1.dp, if (selected) Gold else LineColor, RoundedCornerShape(50))
                        .clickable(enabled = enabled) { onChange(lotText(p)) }
                        .padding(horizontal = 12.dp, vertical = 6.dp)
                )
            }
        }
    }
}

/** Input angka bulat dengan tombol −/+ (mis. jumlah posisi 1–10). */
@Composable
fun CountInput(value: Int, onChange: (Int) -> Unit, label: String, min: Int, max: Int, enabled: Boolean = true) {
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(label, style = MaterialTheme.typography.bodyMedium, modifier = Modifier.weight(1f))
        StepButton("−", enabled && value > min) { onChange(value - 1) }
        Text(
            "$value", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold,
            textAlign = TextAlign.Center, modifier = Modifier.width(40.dp)
        )
        StepButton("+", enabled && value < max) { onChange(value + 1) }
    }
}

@Composable
private fun StepButton(symbol: String, enabled: Boolean, onClick: () -> Unit) {
    FilledTonalButton(
        onClick = onClick,
        enabled = enabled,
        shape = RoundedCornerShape(12.dp),
        contentPadding = PaddingValues(0.dp),
        modifier = Modifier.size(48.dp).border(1.dp, LineColor, RoundedCornerShape(12.dp))
    ) {
        Text(symbol, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
    }
}
