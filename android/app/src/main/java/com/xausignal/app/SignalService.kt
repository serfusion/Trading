package com.xausignal.app

import android.app.Service
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import okhttp3.Call
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONObject
import java.io.IOException
import java.util.concurrent.TimeUnit

/**
 * Service latar depan yang terus membaca aliran JSON ntfy: <server>/<topik>-data/json.
 * Bot Python mengirim sinyal ke topik tersebut (lihat xau_bot/publish.py).
 */
class SignalService : Service() {
    private val client = OkHttpClient.Builder()
        .connectTimeout(20, TimeUnit.SECONDS)
        .readTimeout(120, TimeUnit.SECONDS) // ntfy mengirim keepalive tiap ~45 detik
        .build()

    @Volatile
    private var running = false
    private var worker: Thread? = null

    @Volatile
    private var call: Call? = null

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        SignalRepository.init(this)
        Notifications.createChannels(this)
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val notification = Notifications.foreground(this, "Menunggu sinyal XAUUSD...")
        if (Build.VERSION.SDK_INT >= 29) {
            startForeground(Notifications.FOREGROUND_ID, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC)
        } else {
            startForeground(Notifications.FOREGROUND_ID, notification)
        }
        if (!running) {
            running = true
            worker = Thread({ loop() }, "xau-signal-stream").also { it.start() }
        }
        return START_STICKY
    }

    override fun onDestroy() {
        running = false
        call?.cancel()   // putuskan stream lama segera (mis. topik diganti), jangan tunggu timeout baca
        worker?.interrupt()
        SignalRepository.setConnection("Berhenti")
        super.onDestroy()
    }

    private fun loop() {
        var backoff = 2_000L
        while (running) {
            val topic = SignalRepository.topic()
            if (topic.isBlank()) {
                SignalRepository.setConnection("Isi topik di Pengaturan")
                sleepQuietly(5_000)
                continue
            }
            val since = SignalRepository.lastMessageId() ?: "12h"
            val url = "${SignalRepository.server()}/$topic-data/json?since=$since"
            try {
                val request = Request.Builder().url(url).build()
                val current = client.newCall(request).also { call = it }
                if (!running) break
                current.execute().use { response ->
                    if (!response.isSuccessful) throw IOException("HTTP ${response.code}")
                    SignalRepository.setConnection("Terhubung")
                    backoff = 2_000L
                    val source = response.body?.source() ?: throw IOException("respon kosong")
                    while (running) {
                        val line = source.readUtf8Line() ?: break
                        if (running) handle(line)
                    }
                }
            } catch (e: Exception) {
                if (!running) break
                SignalRepository.setConnection("Terputus, mencoba lagi (${e.message ?: e.javaClass.simpleName})")
                sleepQuietly(backoff)
                backoff = (backoff * 2).coerceAtMost(60_000L)
            }
        }
    }

    private fun handle(line: String) {
        if (line.isBlank()) return
        val obj = try {
            JSONObject(line)
        } catch (e: Exception) {
            return
        }
        if (obj.optString("event") != "message") return
        val payload = try {
            JSONObject(obj.optString("message"))
        } catch (e: Exception) {
            return
        }
        val event = SignalRepository.add(obj.optString("id"), payload) ?: return
        when (event.type) {
            "signal" -> if (event.status == "signal" || event.status == "opened") Notifications.signal(this, event)
            "close" -> Notifications.close(this, event)
            "info" -> {
                val text = event.str("text")
                if (listOf("TP1", "Auto order", "Tutup semua", "LIVE").any { text.contains(it) }) {
                    Notifications.info(this, event)
                }
            }
        }
    }

    private fun sleepQuietly(ms: Long) {
        try {
            Thread.sleep(ms)
        } catch (e: InterruptedException) {
            // service dihentikan
        }
    }
}
