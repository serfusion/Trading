package com.xausignal.app

import android.content.Context
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.LocalContentColor
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.ReadOnlyComposable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Shape
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.compositeOver
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.luminance
import androidx.compose.ui.layout.Layout
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import java.util.Locale

const val APP_NAME = "Dividend Indicator"
const val BRAND = "Superfal-Dev"

// ------------------------------------------------------------------ tampilan yang bisa diatur (aplikasi 4.0)

/** Warna aksen pilihan pengguna: (gelap, gelap-2) untuk tema gelap, (terang, terang-2) untuk tema terang. */
data class Accent(val name: String, val dark: Color, val dark2: Color, val light: Color, val light2: Color)

val ACCENTS = listOf(
    Accent("Emas", Color(0xFFF7CB5A), Color(0xFFE0962B), Color(0xFF9A6A00), Color(0xFFC4891A)),
    Accent("Safir", Color(0xFF7AB0FF), Color(0xFF3D6EF2), Color(0xFF1D4ED8), Color(0xFF3B82F6)),
    Accent("Ametis", Color(0xFFBDA4FF), Color(0xFF8B5CF6), Color(0xFF6D28D9), Color(0xFF8B5CF6)),
    Accent("Toska", Color(0xFF5BE7E0), Color(0xFF12AEBF), Color(0xFF0E7490), Color(0xFF0891B2)),
)

/**
 * 🎨 Pengaturan tampilan (permintaan pengguna 4 Okt 2026: "bisa disesuaikan kotak, grid, circle"): bentuk kartu,
 * susunan angka grid/daftar, win rate lingkaran/bar, warna aksen, tema. Disimpan di HP, berlaku langsung.
 */
object UiPrefs {
    private const val FILE = "tampilan"
    private var ctx: Context? = null
    var shape by mutableIntStateOf(1)        // 0 kotak, 1 bulat, 2 kapsul
    var grid by mutableStateOf(true)         // angka sinyal: grid / daftar
    var ring by mutableStateOf(true)         // win rate: lingkaran / bar
    var accent by mutableIntStateOf(0)
    var theme by mutableIntStateOf(1)        // 0 ikut HP, 1 gelap, 2 terang

    fun init(context: Context) {
        ctx = context.applicationContext
        val p = context.getSharedPreferences(FILE, Context.MODE_PRIVATE)
        shape = p.getInt("shape", 1)
        grid = p.getBoolean("grid", true)
        ring = p.getBoolean("ring", true)
        accent = p.getInt("accent", 0).coerceIn(0, ACCENTS.size - 1)
        theme = p.getInt("theme", 1)
    }

    fun save() {
        ctx?.getSharedPreferences(FILE, Context.MODE_PRIVATE)?.edit()
            ?.putInt("shape", shape)?.putBoolean("grid", grid)?.putBoolean("ring", ring)
            ?.putInt("accent", accent)?.putInt("theme", theme)?.apply()
    }

    fun radius(): Dp = when (shape) {
        0 -> 6.dp
        2 -> 28.dp
        else -> 20.dp
    }
}

val CardShape: Shape @Composable get() = RoundedCornerShape(UiPrefs.radius())
val TileShape: Shape @Composable get() = RoundedCornerShape(UiPrefs.radius() * 0.7f)

/** Warna khusus trading; versi gelap & terang supaya teks tetap kontras. */
data class TradeColors(
    val buy: Color,
    val sell: Color,
    val gold: Color,
    val gold2: Color,
    val muted: Color,
    val card: Color,
    val cardTop: Color,
    val cardHigh: Color,
    val line: Color,
    val bgTop: Color,
    val bgBottom: Color,
    val dark: Boolean,
)

private val DarkTrade = TradeColors(
    buy = Color(0xFF34E39A), sell = Color(0xFFFF6B7A), gold = ACCENTS[0].dark, gold2 = ACCENTS[0].dark2,
    muted = Color(0xFF8D97A8), card = Color(0xFF111723), cardTop = Color(0xFF182133), cardHigh = Color(0xFF1C2638),
    line = Color(0xFF263247), bgTop = Color(0xFF0D1322), bgBottom = Color(0xFF070A11), dark = true,
)
private val LightTrade = TradeColors(
    buy = Color(0xFF0E8A4A), sell = Color(0xFFD12C3F), gold = ACCENTS[0].light, gold2 = ACCENTS[0].light2,
    muted = Color(0xFF5E6878), card = Color(0xFFFFFFFF), cardTop = Color(0xFFFFFFFF), cardHigh = Color(0xFFF4F1EA),
    line = Color(0xFFE6E0D3), bgTop = Color(0xFFFBF8F1), bgBottom = Color(0xFFF1EDE4), dark = false,
)

private val LocalTrade = staticCompositionLocalOf { DarkTrade }

val BuyColor: Color @Composable @ReadOnlyComposable get() = LocalTrade.current.buy
val SellColor: Color @Composable @ReadOnlyComposable get() = LocalTrade.current.sell
val Gold: Color @Composable @ReadOnlyComposable get() = LocalTrade.current.gold
val Gold2: Color @Composable @ReadOnlyComposable get() = LocalTrade.current.gold2
val Muted: Color @Composable @ReadOnlyComposable get() = LocalTrade.current.muted
val CardColor: Color @Composable @ReadOnlyComposable get() = LocalTrade.current.card
val CardHigh: Color @Composable @ReadOnlyComposable get() = LocalTrade.current.cardHigh
val LineColor: Color @Composable @ReadOnlyComposable get() = LocalTrade.current.line
val IsDark: Boolean @Composable @ReadOnlyComposable get() = LocalTrade.current.dark

/** Teks di atas warna penuh: gelap untuk warna terang (emas), putih untuk warna gelap. */
fun onColor(c: Color): Color = if (c.luminance() > 0.45f) Color(0xFF16110A) else Color.White

@Composable
fun dirColor(dir: String?): Color = when (dir) {
    "BUY" -> BuyColor
    "SELL" -> SellColor
    else -> Muted
}

private val BaseType = Typography()
private val AppType = BaseType.copy(
    headlineLarge = BaseType.headlineLarge.copy(fontWeight = FontWeight.ExtraBold, letterSpacing = (-0.5).sp,
        fontFeatureSettings = "tnum"),
    headlineMedium = BaseType.headlineMedium.copy(fontWeight = FontWeight.ExtraBold, letterSpacing = (-0.5).sp,
        fontFeatureSettings = "tnum"),
    headlineSmall = BaseType.headlineSmall.copy(fontWeight = FontWeight.ExtraBold, letterSpacing = (-0.3).sp,
        fontFeatureSettings = "tnum"),
    titleLarge = BaseType.titleLarge.copy(fontWeight = FontWeight.Bold, letterSpacing = (-0.2).sp,
        fontFeatureSettings = "tnum"),
    titleMedium = BaseType.titleMedium.copy(fontFeatureSettings = "tnum"),
    titleSmall = BaseType.titleSmall.copy(fontFeatureSettings = "tnum"),
    labelSmall = BaseType.labelSmall.copy(letterSpacing = 0.2.sp),
)

@Composable
fun XauTheme(content: @Composable () -> Unit) {
    val dark = when (UiPrefs.theme) {
        1 -> true
        2 -> false
        else -> isSystemInDarkTheme()
    }
    val acc = ACCENTS[UiPrefs.accent.coerceIn(0, ACCENTS.size - 1)]
    val trade = if (dark) DarkTrade.copy(gold = acc.dark, gold2 = acc.dark2)
    else LightTrade.copy(gold = acc.light, gold2 = acc.light2)
    val scheme = if (dark) {
        darkColorScheme(
            primary = trade.gold, onPrimary = onColor(trade.gold),
            primaryContainer = trade.gold.copy(alpha = 0.22f).compositeOver(trade.card), onPrimaryContainer = trade.gold,
            secondary = trade.gold, onSecondary = onColor(trade.gold),
            secondaryContainer = trade.gold.copy(alpha = 0.16f).compositeOver(trade.card),
            onSecondaryContainer = trade.gold,
            background = trade.bgBottom, onBackground = Color(0xFFEAEEF5),
            surface = trade.bgBottom, onSurface = Color(0xFFEAEEF5),
            surfaceVariant = trade.cardHigh, onSurfaceVariant = trade.muted, surfaceTint = trade.cardHigh,
            surfaceContainerLowest = Color(0xFF05070C), surfaceContainerLow = trade.card,
            surfaceContainer = trade.card, surfaceContainerHigh = trade.cardTop,
            surfaceContainerHighest = trade.cardHigh,
            outline = trade.line, outlineVariant = trade.line, error = trade.sell,
        )
    } else {
        lightColorScheme(
            primary = trade.gold, onPrimary = onColor(trade.gold),
            primaryContainer = trade.gold.copy(alpha = 0.18f).compositeOver(Color.White),
            onPrimaryContainer = Color(0xFF221A05),
            secondary = trade.gold, onSecondary = onColor(trade.gold),
            secondaryContainer = trade.gold.copy(alpha = 0.14f).compositeOver(Color.White),
            onSecondaryContainer = Color(0xFF221A05),
            background = trade.bgBottom, onBackground = Color(0xFF181B22),
            surface = trade.bgTop, onSurface = Color(0xFF181B22),
            surfaceVariant = trade.cardHigh, onSurfaceVariant = trade.muted, surfaceTint = trade.line,
            surfaceContainerLowest = Color.White, surfaceContainerLow = Color(0xFFFCFAF6),
            surfaceContainer = Color.White, surfaceContainerHigh = Color.White,
            surfaceContainerHighest = trade.cardHigh,
            outline = trade.line, outlineVariant = trade.line, error = trade.sell,
        )
    }
    CompositionLocalProvider(LocalTrade provides trade) {
        MaterialTheme(colorScheme = scheme, typography = AppType, content = content)
    }
}

/** Latar aplikasi: gradien gelap + cahaya aksen lembut di pojok kanan atas. */
@Composable
fun AppBackground(content: @Composable BoxScope.() -> Unit) {
    val t = LocalTrade.current
    val glow = t.gold.copy(alpha = if (t.dark) 0.16f else 0.12f)
    val glow2 = t.buy.copy(alpha = if (t.dark) 0.06f else 0.04f)
    Box(
        Modifier
            .fillMaxSize()
            .background(Brush.verticalGradient(listOf(t.bgTop, t.bgBottom)))
            .drawBehind {
                val r = size.width * 0.95f
                drawCircle(Brush.radialGradient(listOf(glow, Color.Transparent), Offset(size.width * 0.9f, 0f), r),
                    r, Offset(size.width * 0.9f, 0f))
                val r2 = size.width * 0.8f
                drawCircle(Brush.radialGradient(listOf(glow2, Color.Transparent), Offset(0f, size.height * 0.75f), r2),
                    r2, Offset(0f, size.height * 0.75f))
            },
        content = content
    )
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

/**
 * Kartu standar aplikasi: gradien halus, garis tepi bergradien, sudut sesuai 🎨 Tampilan.
 * [accent] = kartu berwarna (arah BUY/SELL, hasil) dengan cahaya lembut.
 */
@Composable
fun AppCard(
    modifier: Modifier = Modifier,
    accent: Color? = null,
    content: @Composable ColumnScope.() -> Unit,
) {
    val t = LocalTrade.current
    val shape = CardShape
    val fill = if (accent != null) {
        Brush.linearGradient(listOf(accent.copy(alpha = if (t.dark) 0.20f else 0.10f).compositeOver(t.cardTop), t.card))
    } else Brush.verticalGradient(listOf(t.cardTop, t.card))
    val edge = if (accent != null) Brush.linearGradient(listOf(accent.copy(alpha = 0.9f), accent.copy(alpha = 0.15f), t.line))
    else Brush.verticalGradient(listOf(t.line.copy(alpha = 1f), t.line.copy(alpha = 0.4f)))
    val glow = when {
        accent != null -> Modifier.shadow(12.dp, shape, ambientColor = accent.copy(alpha = 0.5f), spotColor = accent)
        !t.dark -> Modifier.shadow(4.dp, shape, ambientColor = Color(0x22000000), spotColor = Color(0x22000000))
        else -> Modifier
    }
    CompositionLocalProvider(LocalContentColor provides MaterialTheme.colorScheme.onSurface) {
        Column(
            modifier
                .fillMaxWidth()
                .then(glow)
                .clip(shape)
                .background(fill)
                .border(1.dp, edge, shape)
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
            content = content
        )
    }
}

/** Kartu utama (harga, total): gradien aksen kuat + lingkaran dekoratif. */
@Composable
fun HeroCard(modifier: Modifier = Modifier, color: Color = Gold, content: @Composable ColumnScope.() -> Unit) {
    val t = LocalTrade.current
    val shape = CardShape
    CompositionLocalProvider(LocalContentColor provides MaterialTheme.colorScheme.onSurface) {
        Column(
            modifier
                .fillMaxWidth()
                .shadow(16.dp, shape, ambientColor = color.copy(alpha = 0.45f), spotColor = color)
                .clip(shape)
                .background(Brush.linearGradient(listOf(
                    color.copy(alpha = if (t.dark) 0.30f else 0.18f).compositeOver(t.cardTop), t.card, t.card)))
                .drawBehind {
                    drawCircle(color.copy(alpha = 0.10f), size.height * 0.9f, Offset(size.width * 1.02f, -size.height * 0.1f))
                    drawCircle(color.copy(alpha = 0.07f), size.height * 0.55f, Offset(size.width * 0.78f, size.height * 1.05f))
                }
                .border(1.dp, Brush.linearGradient(listOf(color.copy(alpha = 0.9f), t.line, color.copy(alpha = 0.35f))), shape)
                .padding(18.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
            content = content
        )
    }
}

@Composable
fun SectionTitle(text: String, modifier: Modifier = Modifier, trailing: String? = null) {
    Row(
        modifier.fillMaxWidth().padding(top = 14.dp, bottom = 2.dp, start = 4.dp, end = 4.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(Modifier.size(8.dp).background(Brush.linearGradient(listOf(Gold, Gold2)), CircleShape))
        Text(
            text, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.ExtraBold,
            modifier = Modifier.padding(start = 10.dp).weight(1f)
        )
        if (trailing != null) {
            Text(
                trailing, style = MaterialTheme.typography.labelMedium, fontWeight = FontWeight.Bold, color = Gold,
                modifier = Modifier.background(Gold.copy(alpha = 0.14f), RoundedCornerShape(50))
                    .padding(horizontal = 10.dp, vertical = 3.dp)
            )
        }
    }
}

@Composable
fun CardTitle(text: String, modifier: Modifier = Modifier) {
    Text(
        text.uppercase(Locale("id")),
        style = MaterialTheme.typography.labelMedium,
        fontWeight = FontWeight.Bold,
        color = Muted,
        letterSpacing = 1.2.sp,
        modifier = modifier,
    )
}

/** Label kecil berwarna (BUY, SELL, TUTUP, AUTO ON, ...). [solid] = gradien penuh. */
@Composable
fun Pill(text: String, color: Color, solid: Boolean = false, modifier: Modifier = Modifier) {
    Text(
        text,
        color = if (solid) onColor(color) else color,
        fontWeight = FontWeight.ExtraBold,
        style = MaterialTheme.typography.labelMedium,
        letterSpacing = 0.6.sp,
        maxLines = 1,
        modifier = modifier
            .background(
                if (solid) Brush.horizontalGradient(listOf(color, color.copy(alpha = 0.78f).compositeOver(Color.Black)))
                else Brush.horizontalGradient(listOf(color.copy(alpha = 0.18f), color.copy(alpha = 0.10f))),
                RoundedCornerShape(50)
            )
            .border(1.dp, color.copy(alpha = if (solid) 0f else 0.35f), RoundedCornerShape(50))
            .padding(horizontal = 10.dp, vertical = 4.dp)
    )
}

@Composable
fun StatusDot(color: Color) {
    Box(Modifier.size(10.dp).background(color, CircleShape))
}

/** Titik "live" berdenyut. */
@Composable
fun PulseDot(color: Color, size: Dp = 10.dp) {
    val tr = rememberInfiniteTransition(label = "pulse")
    val a by tr.animateFloat(0.25f, 1f, infiniteRepeatable(tween(900), RepeatMode.Reverse), label = "a")
    Box(Modifier.size(size * 2), contentAlignment = Alignment.Center) {
        Box(Modifier.size(size * 2).background(color.copy(alpha = 0.22f * a), CircleShape))
        Box(Modifier.size(size).background(color, CircleShape))
    }
}

private val FIAT = setOf("USD", "EUR", "GBP", "JPY", "AUD", "CHF", "CAD", "NZD")

/** Koin bulat bergradien per aset: Au (emas), ₿, Ξ, FX (forex), atau 3 huruf koin spot (SOL, ADA, ...). */
@Composable
fun AssetCoin(symbol: String, size: Dp = 40.dp) {
    val s = symbol.uppercase(Locale.US)
    val (glyph, c1, c2) = when {
        s.startsWith("XAU") -> Triple("Au", Color(0xFFFFE6A0), Color(0xFFC88A16))
        s.startsWith("BTC") -> Triple("₿", Color(0xFFFFC46B), Color(0xFFE8710F))
        s.startsWith("ETH") -> Triple("Ξ", Color(0xFFC9BCFF), Color(0xFF6552D8))
        s.substringBefore("/") in FIAT -> Triple("FX", Color(0xFF9AD0FF), Color(0xFF2E6BDB))
        else -> Triple(s.substringBefore("/").take(3), Color(0xFF8CF0D6), Color(0xFF15A39A))   // koin spot lain
    }
    Box(
        Modifier
            .size(size)
            .shadow(6.dp, CircleShape, ambientColor = c2, spotColor = c2)
            .background(Brush.linearGradient(listOf(c1, c2)), CircleShape)
            .border(1.5.dp, Brush.linearGradient(listOf(Color.White.copy(alpha = 0.7f), Color.White.copy(alpha = 0.05f))),
                CircleShape),
        contentAlignment = Alignment.Center
    ) {
        Text(glyph, color = Color(0xFF1B1204), fontWeight = FontWeight.Black,
            fontSize = (size.value * (if (glyph.length > 2) 0.3f else 0.4f)).sp, maxLines = 1)
    }
}

/**
 * Cincin progres (win rate, hitung mundur). [value] 0..1. Isi tengah bebas ([content]).
 * Bila 🎨 Tampilan memilih "Bar", pakai [WinGauge] yang menampilkan bar.
 */
@Composable
fun Ring(
    value: Float,
    color: Color,
    modifier: Modifier = Modifier,
    size: Dp = 64.dp,
    stroke: Dp = 6.dp,
    content: @Composable BoxScope.() -> Unit = {},
) {
    val track = LineColor
    val v by animateFloatAsState(value.coerceIn(0f, 1f), tween(700), label = "ring")
    Box(modifier.size(size), contentAlignment = Alignment.Center) {
        Canvas(Modifier.fillMaxSize()) {
            val s = stroke.toPx()
            val d = Size(this.size.width - s, this.size.height - s)
            val tl = Offset(s / 2f, s / 2f)
            drawArc(track, -90f, 360f, false, tl, d, style = Stroke(s))
            if (v > 0f) drawArc(color, -90f, 360f * v, false, tl, d, style = Stroke(s, cap = StrokeCap.Round))
        }
        content()
    }
}

/** Win rate: lingkaran berisi persen, atau bar hijau/merah (🎨 Tampilan). */
@Composable
fun WinGauge(wins: Int, losses: Int, size: Dp = 56.dp, color: Color? = null) {
    val total = wins + losses
    val rate = if (total > 0) wins.toFloat() / total else 0f
    if (UiPrefs.ring) {
        Ring(rate, color ?: if (rate >= 0.5f) BuyColor else SellColor, size = size, stroke = (size.value / 9f).dp) {
            Text(if (total > 0) "${Math.round(rate * 100)}%" else "–", fontWeight = FontWeight.ExtraBold,
                fontSize = (size.value * 0.24f).sp, maxLines = 1)
        }
    } else {
        Column(Modifier.width(size), horizontalAlignment = Alignment.CenterHorizontally) {
            Text(if (total > 0) "${Math.round(rate * 100)}%" else "–", fontWeight = FontWeight.ExtraBold,
                fontSize = (size.value * 0.26f).sp, maxLines = 1)
            WinBar(wins, losses)
        }
    }
}

/**
 * Kotak angka: label kecil di atas, nilai besar di bawah. Dipakai berjajar dalam Row.
 * [compact] = huruf lebih kecil untuk 3–4 kotak sebaris (mis. harga 4,123.45).
 */
@Composable
fun RowScope.Metric(label: String, value: String, color: Color = Color.Unspecified, compact: Boolean = false) {
    val shape = TileShape
    Column(
        Modifier
            .weight(1f)
            .clip(shape)
            .background(CardHigh)
            .border(1.dp, if (color != Color.Unspecified) color.copy(alpha = 0.30f) else LineColor, shape)
            .padding(horizontal = if (compact) 8.dp else 12.dp, vertical = 9.dp)
    ) {
        Text(label, style = MaterialTheme.typography.labelSmall, color = Muted, maxLines = 1)
        Text(
            value,
            style = if (compact) MaterialTheme.typography.titleSmall else MaterialTheme.typography.titleMedium,
            fontWeight = FontWeight.ExtraBold, color = color, maxLines = 1
        )
    }
}

@Composable
fun MetricRow(content: @Composable RowScope.() -> Unit) {
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp), content = content)
}

/** Satu kotak angka besar untuk [TileGrid]. [wide] = satu baris penuh. */
data class TileData(val label: String, val value: String, val color: Color, val sub: String? = null,
                    val wide: Boolean = false, val done: Boolean = false)

/** Angka besar dalam grid 2 kolom, atau daftar label—nilai (🎨 Tampilan → Susunan angka). */
@Composable
fun TileGrid(items: List<TileData>) {
    if (!UiPrefs.grid) {
        Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
            items.forEach { d ->
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(Modifier.size(8.dp).background(d.color, CircleShape))
                    Text(d.label + (d.sub?.let { " • $it" } ?: ""), color = Muted,
                        style = MaterialTheme.typography.labelMedium,
                        modifier = Modifier.padding(start = 8.dp).weight(1f))
                    Text(d.value, color = d.color, fontWeight = FontWeight.ExtraBold,
                        style = MaterialTheme.typography.titleLarge)
                }
            }
        }
        return
    }
    val rows = mutableListOf<List<TileData>>()
    var pending = mutableListOf<TileData>()
    for (d in items) {
        if (d.wide) {
            if (pending.isNotEmpty()) rows += pending.toList()
            pending = mutableListOf()
            rows += listOf(d)
        } else {
            pending += d
            if (pending.size == 2) {
                rows += pending.toList()
                pending = mutableListOf()
            }
        }
    }
    if (pending.isNotEmpty()) rows += pending.toList()
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        rows.forEach { row ->
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                row.forEach { d -> Tile(d) }
                if (row.size == 1 && !row[0].wide) Box(Modifier.weight(1f))
            }
        }
    }
}

@Composable
private fun RowScope.Tile(d: TileData) {
    val shape = TileShape
    Column(
        Modifier
            .weight(1f)
            .clip(shape)
            .background(Brush.verticalGradient(listOf(d.color.copy(alpha = 0.13f).compositeOver(CardHigh), CardHigh)))
            .border(1.dp, d.color.copy(alpha = if (d.done) 0.9f else 0.32f), shape)
            .padding(horizontal = 12.dp, vertical = 10.dp)
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Box(Modifier.size(7.dp).background(d.color, CircleShape))
            Text(d.label, style = MaterialTheme.typography.labelMedium, fontWeight = FontWeight.Bold, color = Muted,
                maxLines = 1, modifier = Modifier.padding(start = 6.dp).weight(1f))
            if (d.done) Text("✓", color = d.color, fontWeight = FontWeight.Black)
        }
        Text(d.value, style = if (d.wide) MaterialTheme.typography.headlineSmall else MaterialTheme.typography.titleLarge,
            fontWeight = FontWeight.ExtraBold, color = d.color, maxLines = 1)
        d.sub?.let { Text(it, style = MaterialTheme.typography.labelSmall, color = Muted, maxLines = 1) }
    }
}

/**
 * Lintasan harga sinyal: SL ──── Entry ── TP1 ── TP2 ──── TP3 dengan titik harga sekarang (aplikasi 4.0).
 * Posisi = (x − SL) / (TP3 − SL), jadi berlaku untuk BUY dan SELL.
 */
@Composable
fun PriceTrack(sl: Double, entry: Double, tp1: Double, tp2: Double, tp3: Double, price: Double?) {
    val span = tp3 - sl
    if (span == 0.0) return
    fun f(x: Double) = ((x - sl) / span).toFloat().coerceIn(0f, 1f)
    val buy = BuyColor
    val sell = SellColor
    val gold = Gold
    val muted = Muted
    val line = LineColor
    val now = price?.let { f(it) }
    val nowColor = price?.let { if ((it - entry) * (tp3 - sl) >= 0) buy else sell } ?: muted
    val marks = listOf(f(sl), f(entry), f(tp1), f(tp2), f(tp3))
    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Canvas(Modifier.fillMaxWidth().height(22.dp)) {
            val y = size.height / 2f
            val w = size.width
            val h = 6.dp.toPx()
            drawLine(line, Offset(0f, y), Offset(w, y), h, StrokeCap.Round)
            drawLine(Brush.horizontalGradient(listOf(sell, sell.copy(alpha = 0.3f)), 0f, marks[1] * w),
                Offset(0f, y), Offset(marks[1] * w, y), h, StrokeCap.Round)
            drawLine(Brush.horizontalGradient(listOf(buy.copy(alpha = 0.3f), buy), marks[1] * w, w),
                Offset(marks[1] * w, y), Offset(w, y), h, StrokeCap.Round)
            marks.forEachIndexed { i, m ->
                val c = when (i) {
                    0 -> sell
                    1 -> gold
                    else -> buy
                }
                drawCircle(Color.White.copy(alpha = 0.9f), 5.dp.toPx(), Offset(m * w, y))
                drawCircle(c, 3.6.dp.toPx(), Offset(m * w, y))
            }
            if (now != null) {
                drawCircle(nowColor.copy(alpha = 0.25f), 11.dp.toPx(), Offset(now * w, y))
                drawCircle(Color.White, 7.dp.toPx(), Offset(now * w, y))
                drawCircle(nowColor, 5.dp.toPx(), Offset(now * w, y))
            }
        }
        FractionRow(marks) {
            listOf("SL", "Entry", "TP1", "TP2", "TP3").forEachIndexed { i, s ->
                Text(s, style = MaterialTheme.typography.labelSmall, fontWeight = FontWeight.Bold,
                    color = if (i == 0) sell else if (i == 1) gold else buy)
            }
        }
    }
}

/** Menaruh tiap anak di tengah posisi pecahan lebar (dijaga tidak keluar tepi). */
@Composable
private fun FractionRow(fractions: List<Float>, content: @Composable () -> Unit) {
    Layout(content, Modifier.fillMaxWidth()) { measurables, c ->
        val ps = measurables.map { it.measure(c.copy(minWidth = 0)) }
        val w = c.maxWidth
        val h = ps.maxOfOrNull { it.height } ?: 0
        layout(w, h) {
            ps.forEachIndexed { i, p ->
                val x = (fractions.getOrElse(i) { 0f } * w - p.width / 2f).toInt()
                    .coerceIn(0, (w - p.width).coerceAtLeast(0))
                p.placeRelative(x, 0)
            }
        }
    }
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
    Box(Modifier.fillMaxWidth().height(1.dp).background(
        Brush.horizontalGradient(listOf(Color.Transparent, LineColor, LineColor, Color.Transparent))))
}

/** Bar menang/kalah: hijau = porsi menang, merah = porsi kalah. */
@Composable
fun WinBar(wins: Int, losses: Int) {
    val total = wins + losses
    Row(
        Modifier
            .fillMaxWidth()
            .height(8.dp)
            .clip(RoundedCornerShape(4.dp))
            .background(CardHigh),
        horizontalArrangement = Arrangement.spacedBy(2.dp)
    ) {
        if (total == 0) return@Row
        if (wins > 0) {
            Box(Modifier.weight(wins.toFloat()).height(8.dp)
                .background(Brush.horizontalGradient(listOf(BuyColor.copy(alpha = 0.6f), BuyColor))))
        }
        if (losses > 0) {
            Box(Modifier.weight(losses.toFloat()).height(8.dp)
                .background(Brush.horizontalGradient(listOf(SellColor, SellColor.copy(alpha = 0.6f)))))
        }
    }
}

/** Kotak catatan/peringatan dengan garis kiri berwarna. */
@Composable
fun NoteBox(text: String, color: Color = Gold) {
    Row(
        Modifier
            .fillMaxWidth()
            .clip(TileShape)
            .background(color.copy(alpha = 0.11f))
            .border(1.dp, color.copy(alpha = 0.30f), TileShape)
            .padding(12.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(Modifier.width(3.dp).height(20.dp).background(color, RoundedCornerShape(2.dp)))
        Text(
            text, style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurface, modifier = Modifier.padding(start = 10.dp)
        )
    }
}

/** Pilihan bergaya tombol kapsul (dipakai di 🎨 Tampilan dan pemilih periode). */
@Composable
fun Choice(text: String, selected: Boolean, modifier: Modifier = Modifier, onClick: () -> Unit) {
    val shape = TileShape
    Text(
        text,
        textAlign = TextAlign.Center,
        fontWeight = if (selected) FontWeight.ExtraBold else FontWeight.Medium,
        color = if (selected) onColor(Gold) else MaterialTheme.colorScheme.onSurface,
        style = MaterialTheme.typography.labelLarge,
        maxLines = 1,
        modifier = modifier
            .clip(shape)
            .background(if (selected) Brush.horizontalGradient(listOf(Gold, Gold2))
                else Brush.horizontalGradient(listOf(CardHigh, CardHigh)))
            .border(1.dp, if (selected) Gold else LineColor, shape)
            .clickable(onClick = onClick)
            .padding(horizontal = 12.dp, vertical = 10.dp)
    )
}

@Composable
fun Footer() {
    Column(
        Modifier.fillMaxWidth().padding(vertical = 20.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Text(BRAND, style = MaterialTheme.typography.labelMedium, color = Gold, fontWeight = FontWeight.Bold,
            letterSpacing = 1.5.sp)
        Text("Bukan saran investasi", style = MaterialTheme.typography.labelSmall, color = Muted)
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
