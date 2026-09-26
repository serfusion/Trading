package com.xausignal.app

import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.io.IOException
import java.util.concurrent.TimeUnit

data class LivePosition(
    val id: String,
    val dir: String,
    val volume: Double?,
    val open: Double?,
    val sl: Double?,
    val tp: Double?,
    val profit: Double?,
)

data class AutoStatus(
    val auto: Boolean,
    val paused: Boolean,
    val legLot: Double,
    val legs: Int,
    val executor: Boolean,
    val balance: Double?,
    val equity: Double?,
    val currency: String,
    val positions: List<LivePosition>,
    val error: String,
)

/**
 * Remote control auto order. Order dieksekusi di cloud (Vercel -> MetaApi -> akun MT5 Exness),
 * jadi tetap jalan 24 jam walau HP mati. Endpoint: <cloud>/api/control, header X-Control-Key.
 * Semua fungsi di sini blocking -> panggil dari Dispatchers.IO.
 */
object AutoControl {
    private val JSON_TYPE = "application/json; charset=utf-8".toMediaType()
    private val client = OkHttpClient.Builder()
        .connectTimeout(20, TimeUnit.SECONDS)
        .readTimeout(60, TimeUnit.SECONDS)
        .build()

    fun status(): AutoStatus = call(null)

    fun update(changes: JSONObject): AutoStatus = call(changes)

    private fun call(body: JSONObject?): AutoStatus {
        val base = SignalRepository.cloudUrl()
        if (base.isBlank()) throw IOException("Isi URL cloud dulu")
        val builder = Request.Builder()
            .url("$base/api/control")
            .header("X-Control-Key", SignalRepository.controlKey())
        if (body != null) builder.post(body.toString().toRequestBody(JSON_TYPE))
        client.newCall(builder.build()).execute().use { res ->
            val text = res.body?.string().orEmpty()
            val json = try {
                JSONObject(text)
            } catch (e: Exception) {
                throw IOException("HTTP ${res.code} (cek URL cloud): ${text.take(80)}")
            }
            if (!res.isSuccessful || !json.optBoolean("ok", false)) {
                throw IOException(json.optString("error").ifBlank { "HTTP ${res.code}" })
            }
            return parse(json)
        }
    }

    private fun JSONObject.dbl(key: String): Double? =
        if (has(key) && !isNull(key)) optDouble(key).takeIf { !it.isNaN() } else null

    fun parse(j: JSONObject): AutoStatus {
        val c = j.optJSONObject("control") ?: JSONObject()
        val acc = j.optJSONObject("account")
        val arr = j.optJSONArray("positions")
        val positions = ArrayList<LivePosition>()
        if (arr != null) {
            for (i in 0 until arr.length()) {
                val p = arr.getJSONObject(i)
                positions.add(
                    LivePosition(
                        p.optString("id"), p.optString("dir"), p.dbl("volume"), p.dbl("open"),
                        p.dbl("sl"), p.dbl("tp"), p.dbl("profit")
                    )
                )
            }
        }
        return AutoStatus(
            auto = c.optBoolean("auto", false),
            paused = c.optBoolean("paused", false),
            legLot = c.dbl("leg_lot") ?: 0.01,
            legs = c.optInt("legs", 5),
            executor = j.optBoolean("executor", false),
            balance = acc?.dbl("balance"),
            equity = acc?.dbl("equity"),
            currency = acc?.optString("currency").orEmpty(),
            positions = positions,
            error = j.optString("error"),
        )
    }
}
