package com.xausignal.app

import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.TimeUnit

/**
 * ⚡ Harga emas LIVE per detik saat rilis berita (aplikasi 4.39, 14 Okt 2026 — pengguna: "apk gagal predict di detik awal").
 * Tebakan SEBELUM rilis tidak bisa hampir selalu benar (research/aturan_pra.py: ±40 rb aturan → 53% di tahun berikutnya),
 * jadi setelah rilis aplikasi membaca harga emas token (XAUT/PAXG ≈ spot) langsung dari bursa publik tiap ±0,5 dtk.
 * Uji 2026 (13 rilis): XAUT OKX bergerak ±1 dtk lebih cepat dari feed Exness; gerak OKX ≥ $1 di detik 1 searah Exness detik 2
 * pada 10/11 rilis. CPI 14 Okt: OKX −$13 di detik 1 (4.153,0 → 4.139,9), −$27 di detik 2.
 * HP langsung ke bursa (tanpa cloud, tanpa kunci). Sumber pertama yang menjawab dipakai; gagal → sumber berikutnya.
 * Info saja, tanpa order.
 */
object LiveGold {
    private val http = OkHttpClient.Builder()
        .connectTimeout(2, TimeUnit.SECONDS).readTimeout(2, TimeUnit.SECONDS).callTimeout(3, TimeUnit.SECONDS).build()

    private class Src(val nama: String, val url: String, val parse: (String) -> Double?)

    private fun mid(bid: String?, ask: String?, last: String?): Double? {
        val b = bid?.toDoubleOrNull()
        val a = ask?.toDoubleOrNull()
        return if (b != null && a != null && b > 0 && a > 0) (a + b) / 2 else last?.toDoubleOrNull()
    }

    private val sumber = listOf(
        Src("OKX XAUT", "https://www.okx.com/api/v5/market/ticker?instId=XAUT-USDT") { s ->
            JSONObject(s).optJSONArray("data")?.optJSONObject(0)?.let { mid(it.optString("bidPx"), it.optString("askPx"), it.optString("last")) }
        },
        Src("KuCoin XAUT", "https://api.kucoin.com/api/v1/market/orderbook/level1?symbol=XAUT-USDT") { s ->
            JSONObject(s).optJSONObject("data")?.let { mid(it.optString("bestBid"), it.optString("bestAsk"), it.optString("price")) }
        },
        Src("Bitget XAUT", "https://api.bitget.com/api/v2/spot/market/tickers?symbol=XAUTUSDT") { s ->
            JSONObject(s).optJSONArray("data")?.optJSONObject(0)?.let { mid(it.optString("bidPr"), it.optString("askPr"), it.optString("lastPr")) }
        },
        Src("Gate XAUT", "https://api.gateio.ws/api/v4/spot/tickers?currency_pair=XAUT_USDT") { s ->
            JSONArray(s).optJSONObject(0)?.let { mid(it.optString("highest_bid"), it.optString("lowest_ask"), it.optString("last")) }
        },
    )

    @Volatile private var aktif = 0

    /** (harga, nama sumber) atau null bila semua sumber gagal. Dipanggil dari Dispatchers.IO. */
    fun harga(): Pair<Double, String>? {
        for (k in sumber.indices) {
            val i = (aktif + k) % sumber.size
            val s = sumber[i]
            val p = try {
                http.newCall(Request.Builder().url(s.url).header("User-Agent", "Mozilla/5.0").build()).execute().use { r ->
                    if (r.isSuccessful) r.body?.string()?.let(s.parse) else null
                }
            } catch (e: Exception) {
                null
            }
            if (p != null && p > 0) {
                aktif = i
                return p to s.nama
            }
        }
        return null
    }
}
