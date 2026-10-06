package com.xausignal.app

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.ui.ImageComposeScene
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.Density
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.flow.MutableStateFlow
import org.jetbrains.skia.EncodedImageFormat
import org.json.JSONObject
import java.io.File
import java.time.Instant
import java.time.temporal.ChronoUnit

object PreviewData {
    fun prep(): JSONObject = JSONObject().put("berita", org.json.JSONArray()
        .put(JSONObject().put("title", "Core CPI m/m (USD)").put("time", Instant.now().plus(3, ChronoUnit.HOURS).plusSeconds(1234).toString()))
        .put(JSONObject().put("title", "Unemployment Claims").put("time", Instant.now().minus(40, ChronoUnit.MINUTES).toString())
            .put("pudar", JSONObject().put("label", "📉 Sisa lonjakan").put("teks", "28% → 🔴 cenderung balik lewat harga rilis"))))
}

fun hb(sym: String, price: Double, d1: String, h4: String, buy: Double, sell: Double, open: Boolean) = SignalEvent("m$sym", "price",
    JSONObject().put("symbol", sym).put("price", price).put("status", JSONObject().put("d1", d1).put("h4", h4)
        .put("next_check", Instant.now().plusSeconds(600).toString())
        .put("levels", org.json.JSONArray().put(JSONObject().put("buy", buy).put("sell", sell).put("open", if (open) "BUY" else JSONObject.NULL)))))

fun main(args: Array<String>) {
    System.setProperty("preview", "1")
    val dark = args.getOrNull(0) != "light"
    UiPrefs.theme = if (dark) 1 else 2
    val prices = mapOf(
        "XAU/USD" to hb("XAU/USD", 3951.25, "BUY", "BUY", 3962.40, 3930.10, false),
        "BTC/USD" to hb("BTC/USD", 123456.0, "SELL", "SELL", 125300.0, 121900.0, true),
        "ETH/USD" to hb("ETH/USD", 4512.0, "BUY", "SELL", 4590.0, 4420.0, false))
    @Suppress("UNCHECKED_CAST")
    val spot = SignalRepository::class.java.getDeclaredField("_spot").apply { isAccessible = true }.get(SignalRepository) as MutableStateFlow<JSONObject?>
    val dl = Instant.now().plus(8, ChronoUnit.DAYS).toString()
    spot.value = JSONObject("""{"type":"spot_status","open":[{"id":"SPOT-SOL-1","coin":"SOL","entry":200.0,"tp":206.0,
      "p":95.2,"time":"${Instant.now()}","deadline":"$dl","alasan":"model","price":176.0}],"closed":[],
      "scan_at":"${Instant.now()}","every_min":10,"coins":100,"scanned":100,"found":0,"btc_up":true,"btc_filter":true,
      "tp_pct":3,"days":10,"ambang":93,"max_open":20,
      "teruji":{"baru":{"n":3580,"wr":90.3,"avg":0.77,"kalah":-17.2,"terburuk":-48.2},
      "jatuh":{"10":{"porsi":27.3,"tetap_tp":65.6,"akhir":-4.3},"20":{"porsi":11.0,"tetap_tp":35.0,"akhir":-12.4}}}}""")
    val w = 412; val h = 900
    val scene = ImageComposeScene(w * 2, h * 2, Density(2f)) {
        XauTheme {
            Column(Modifier.fillMaxSize().background(MaterialTheme.colorScheme.background).padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp)) {
                StatusCards(prices, setOf("XAU", "BTC", "SPOT"))
                SpotSection(emptyList())
            }
        }
    }
    var t = 0L
    repeat(30) { scene.render(t); t += 100_000_000L; Thread.sleep(60) }
    val img = scene.render(t)
    File(args.getOrNull(1) ?: "preview.png").writeBytes(img.encodeToData(EncodedImageFormat.PNG)!!.bytes)
    scene.close()
    System.exit(0)
}
