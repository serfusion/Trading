package com.xausignal.app

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import org.json.JSONArray
import org.json.JSONObject
import java.time.Duration
import java.time.Instant
import java.time.OffsetDateTime
import java.util.Locale

/** 20 koin besar yang dipindai 💎 (sama dengan cloud/api/spot_model.json "coins"). */
val SPOT_COINS = listOf("BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "DOGE", "TRX", "LINK", "AVAX", "DOT", "LTC", "BCH",
    "XLM", "ATOM", "ETC", "UNI", "NEAR", "AAVE", "FIL")

/** Harga spot: 2 desimal ≥ 100, 4 desimal ≥ 1, selain itu 6 desimal. */
fun spotPx(v: Double?): String = when {
    v == null -> "-"
    v >= 100 -> fmt(v, 2)
    v >= 1 -> fmt(v, 4)
    else -> fmt(v, 6)
}

fun spotPct(v: Double): String = String.format(Locale.US, "%+.1f%%", v).replace('.', ',')

private fun instantOf(iso: String): Instant? = try {
    OffsetDateTime.parse(iso).toInstant()
} catch (e: Exception) {
    null
}

private fun objects(arr: JSONArray?): List<JSONObject> =
    if (arr == null) emptyList() else (0 until arr.length()).mapNotNull { arr.optJSONObject(it) }

/** Statistik BARU (Okt 2021–2026) untuk label "kilat"/"biasa" dari spot_status "tier", atau null. */
private fun tierBaru(st: JSONObject?, tier: String): JSONObject? =
    st?.optJSONObject("tier")?.optJSONObject(tier)?.optJSONObject("baru")

private fun pctBulat(v: Double): String = fmt(v, 0) + "%"

/**
 * 💎 Spot Binance (aplikasi 4.1, permintaan pengguna 4 Okt 2026): koin dengan peluang tinggi naik lagi +3% dalam 10 hari
 * (cloud/api/_spot.py, research/spot_peluang.py). Kartu BELI (harga beli, limit jual TP, harga sekarang, batas waktu)
 * dan CLOSE terakhir. Data: spot_status cloud; cadangan: pesan spot_signal / spot_close di HP. Info saja, tanpa order.
 *
 * Aplikasi 4.24 (9 Okt 2026): angka "teruji" = versi JUJUR (cloud/api/spot_teruji.json, research/spot_apk.py: koin volume
 * terbesar saat itu termasuk delisting) + label ⚡ Dip ringan (tier "kilat": harga masih ≤ 15% di bawah puncak 20 hari).
 * Cincin = untung% teruji label itu (bukan "peluang": skor model tidak terkalibrasi sejak 2021).
 */
@Composable
fun SpotSection(events: List<SignalEvent>) {
    val status by SignalRepository.spot.collectAsState()
    val st = status
    val open: List<JSONObject>
    val closed: List<JSONObject>
    if (st != null) {
        open = objects(st.optJSONArray("open"))
        closed = objects(st.optJSONArray("closed"))
    } else {                                       // cloud lama / ringkasan belum datang: dari pesan sinyal
        val done = events.filter { it.type == "spot_close" }.map { it.id }.toSet()
        open = events.filter { it.type == "spot_signal" && it.id !in done }.map { it.json }
        closed = events.filter { it.type == "spot_close" }.map { it.json }
    }
    if (st == null && open.isEmpty() && closed.isEmpty()) return
    // daftar koin yang dipindai cloud (spot_model.json); cadangan = 20 koin bawaan
    val coins = st?.optJSONArray("coins")?.let { arr -> (0 until arr.length()).map { arr.optString(it) } }
        ?.filter { it.isNotBlank() }?.ifEmpty { null } ?: SPOT_COINS
    SectionTitle("💎 Spot Binance", trailing = if (open.isEmpty()) null else "${open.size} aktif")
    if (open.isEmpty()) {
        AppCard {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(14.dp)) {
                Box(
                    Modifier.size(48.dp).background(Gold.copy(alpha = 0.14f), CircleShape)
                        .border(1.dp, Gold.copy(alpha = 0.4f), CircleShape),
                    contentAlignment = Alignment.Center
                ) { Text("💎", style = MaterialTheme.typography.titleLarge) }
                Column {
                    Text("Belum ada koin berpeluang tinggi", fontWeight = FontWeight.ExtraBold)
                    Text("Dipindai tiap hari 07:05 WIB • ${coins.size} koin" +
                        (st?.optString("scan_day")?.takeIf { it.isNotBlank() }?.let { " • terakhir $it" } ?: ""),
                        style = MaterialTheme.typography.labelMedium, color = Muted)
                }
            }
            Text("${coins.size} koin dipantau: ${coins.joinToString(" • ")}",
                style = MaterialTheme.typography.labelSmall, color = Muted)
        }
    }
    open.forEach { SpotOpenCard(it, st) }
    if (closed.isNotEmpty()) SpotClosedCard(closed.take(5))
    st?.optJSONObject("teruji")?.optJSONObject("baru")?.let { b ->
        val k = tierBaru(st, "kilat")
        val bi = tierBaru(st, "biasa")
        val dasar = st.optJSONObject("teruji")?.optDouble("dasar_baru")?.takeIf { !it.isNaN() }
        Text(
            if (k != null && bi != null)
                "Teruji Okt 2021–2026 (20 koin volume terbesar saat itu, termasuk delisting): ⚡ untung di " +
                    "${pctBulat(k.optDouble("wr"))} sinyal, rata ${spotPct(k.optDouble("avg"))} • biasa " +
                    "${pctBulat(bi.optDouble("wr"))}, ${spotPct(bi.optDouble("avg"))} • rugi terburuk " +
                    spotPct(b.optDouble("terburuk")) + (dasar?.let { " • acak ${pctBulat(it)}" } ?: "")
            else
                "Teruji Okt 2021–2026: untung di ${pctBulat(b.optDouble("wr"))} sinyal (target " +
                    "+${fmt(st.optDouble("tp_pct", 3.0), 0)}%) • rata ${spotPct(b.optDouble("avg"))} • rugi rata " +
                    "${spotPct(b.optDouble("kalah"))} • terburuk ${spotPct(b.optDouble("terburuk"))}",
            style = MaterialTheme.typography.labelSmall, color = Muted
        )
    }
}

@Composable
private fun SpotOpenCard(o: JSONObject, st: JSONObject?) {
    val coin = o.optString("coin")
    val entry = o.optDouble("entry")
    val tp = o.optDouble("tp")
    val price = o.optDouble("price").takeIf { !it.isNaN() }
    val p = o.optDouble("p")
    val tpPct = st?.optDouble("tp_pct", 3.0) ?: 3.0
    val days = st?.optInt("days", 10) ?: 10
    val chg = price?.let { (it / entry - 1) * 100 }
    val left = instantOf(o.optString("deadline"))?.let { Duration.between(Instant.now(), it) }
    val tier = o.optString("tier")
    val kilat = tier == "kilat"
    val tierWr = tier.takeIf { it.isNotBlank() }?.let { tierBaru(st, it)?.optDouble("wr") }?.takeIf { !it.isNaN() }
    AppCard(accent = BuyColor) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            AssetCoin(coin, 38.dp)
            Column(Modifier.weight(1f)) {
                Text("$coin/USDT", fontWeight = FontWeight.ExtraBold, style = MaterialTheme.typography.titleMedium)
                Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    Pill("BELI SPOT", BuyColor, solid = true)
                    if (kilat) Pill(o.optString("tier_nama").ifBlank { "⚡ Dip ringan" }, Gold)
                }
            }
            if (tierWr != null) {
                Ring((tierWr / 100).toFloat(), Gold, size = 60.dp, stroke = 6.dp) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Text(pctBulat(tierWr), fontWeight = FontWeight.ExtraBold,
                            style = MaterialTheme.typography.titleSmall)
                        Text("teruji", style = MaterialTheme.typography.labelSmall, color = Muted)
                    }
                }
            } else {
                Ring((p / 100).toFloat(), Gold, size = 60.dp, stroke = 6.dp) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Text("${fmt(p, 0)}", fontWeight = FontWeight.ExtraBold, style = MaterialTheme.typography.titleSmall)
                        Text("skor", style = MaterialTheme.typography.labelSmall, color = Muted)
                    }
                }
            }
        }
        Text("Target +${fmt(tpPct, 0)}% dalam $days hari" +
            (o.optString("alasan").takeIf { it.isNotBlank() }?.let { " • $it" } ?: "") +
            (if (tierWr != null && !p.isNaN()) " • skor model ${fmt(p, 0)}" else "") +
            (if (kilat) " • masih ${spotPct(o.optDouble("dd20"))} dari puncak 20 hari" else ""),
            style = MaterialTheme.typography.labelMedium, color = Muted)
        TileGrid(listOf(
            TileData("Beli", spotPx(entry), Gold, "± harga sinyal"),
            TileData("Jual • TP +${fmt(tpPct, 0)}%", spotPx(tp), BuyColor, "pasang limit jual"),
            TileData("Harga sekarang", spotPx(price), if ((chg ?: 0.0) >= 0) BuyColor else SellColor,
                chg?.let { spotPct(it) }),
            TileData("Batas waktu", formatTime(o.optString("deadline")).removeSuffix(" WIB"), Muted,
                left?.let { if (it.isNegative) "lewat → jual" else "sisa ${it.toDays()} h ${it.toHours() % 24} j" }),
        ))
        if (price != null && tp > entry) {
            val prog = ((price - entry) / (tp - entry)).coerceIn(0.0, 1.0).toFloat()
            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Box(Modifier.fillMaxWidth().height(8.dp).clip(RoundedCornerShape(4.dp)).background(CardHigh)) {
                    if (prog > 0f) Box(Modifier.fillMaxWidth(prog).height(8.dp)
                        .background(Brush.horizontalGradient(listOf(Gold, BuyColor))))
                }
                Text("Menuju TP: ${fmt(prog * 100.0, 0)}%", style = MaterialTheme.typography.labelSmall, color = Muted)
            }
        }
        val b = st?.optJSONObject("teruji")?.optJSONObject("baru")
        NoteBox("Maks ${100 / maxOf(st?.optInt("max_open", 10) ?: 10, 1)}% modal spot per koin. Tanpa SL: sesekali " +
            "rugi besar" + (b?.let { " (rata ${spotPct(it.optDouble("kalah"))}, terburuk ${spotPct(it.optDouble("terburuk"))}" +
            " — koin bisa ambruk/delisting)" } ?: "") + ".", Gold)
    }
}

@Composable
private fun SpotClosedCard(list: List<JSONObject>) {
    AppCard {
        CardTitle("Close spot terakhir")
        list.forEach { c ->
            val r = c.optDouble("r")
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                AssetCoin(c.optString("coin"), 28.dp)
                Column(Modifier.weight(1f)) {
                    Text((if (c.optString("tier") == "kilat") "⚡ " else "") + "${c.optString("coin")}/USDT",
                        fontWeight = FontWeight.Bold, style = MaterialTheme.typography.bodyMedium)
                    Text("${c.optString("reason")} • ${formatTime(c.optString("time"))}",
                        style = MaterialTheme.typography.labelSmall, color = Muted, maxLines = 1)
                }
                Spacer(Modifier.size(4.dp))
                Pill(spotPct(r), if (r > 0) BuyColor else SellColor, solid = true)
            }
        }
    }
}
