package com.xausignal.app

import android.app.AlarmManager
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONObject
import java.io.IOException
import java.util.concurrent.TimeUnit

/**
 * Ambil pesan baru dari ntfy (mode poll, tanpa koneksi terus-menerus): <server>/<topik>-data/json?poll=1.
 * Dipanggil oleh alarm latar belakang (tanpa notifikasi yang selalu tampil) dan saat aplikasi dibuka.
 */
object SignalPoller {
    private val client = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(20, TimeUnit.SECONDS)
        .build()

    /** Return jumlah pesan baru. Muat pertama (belum ada riwayat) tidak membunyikan notifikasi. */
    @Synchronized
    fun poll(context: Context): Int {
        SignalRepository.init(context)
        Notifications.createChannels(context)
        val topic = SignalRepository.topic()
        if (topic.isBlank()) {
            SignalRepository.setConnection("Isi topik di Pengaturan")
            return 0
        }
        val last = SignalRepository.lastMessageId()
        val url = "${SignalRepository.server()}/$topic-data/json?poll=1&since=${last ?: "12h"}"
        return try {
            client.newCall(Request.Builder().url(url).build()).execute().use { res ->
                if (!res.isSuccessful) throw IOException("HTTP ${res.code}")
                var added = 0
                val seen = HashSet<String>()           // sinyal kembar (set berbeda, entry sama) = 1 notifikasi
                res.body?.string().orEmpty().lineSequence().forEach { line ->
                    val event = parse(line) ?: return@forEach
                    added++
                    val twin = "${event.type}|${event.symbol()}|${event.dir}|${event.price("entry")}"
                    if (last != null && (event.type != "signal" || seen.add(twin))) notify(context, event)
                }
                SignalRepository.setConnection("Terhubung")
                added
            }
        } catch (e: Exception) {
            SignalRepository.setConnection("Offline")
            0
        }
    }

    private fun parse(line: String): SignalEvent? {
        if (line.isBlank()) return null
        return try {
            val obj = JSONObject(line)
            if (obj.optString("event") != "message") return null
            SignalRepository.add(obj.optString("id"), JSONObject(obj.optString("message")))
        } catch (e: Exception) {
            null
        }
    }

    private fun notify(context: Context, event: SignalEvent) {
        when (event.type) {
            "signal" -> if ((event.status == "signal" || event.status == "opened") && !event.isVoid()) {
                Notifications.signal(context, event)
            }
            "close" -> Notifications.close(context, event)
            "info" -> when {
                event.str("kind") == "be07" -> if (SignalRepository.money().be07) Notifications.be07(context, event)
                event.str("text").contains("TP1") -> Notifications.info(context, event)
            }
        }
    }
}

/** Alarm latar belakang: cek sinyal beberapa menit setelah cloud memeriksa pasar (:02 & :32 UTC). */
object PollScheduler {
    private const val SLOT = 10 * 60_000L
    private const val OFFSET = 5 * 60_000L   // :05, :15, ... :55 (3 menit setelah cek cloud :02, :12, ...)

    fun nextSlot(now: Long): Long = ((now - OFFSET) / SLOT + 1) * SLOT + OFFSET

    fun schedule(context: Context) {
        val am = context.getSystemService(AlarmManager::class.java) ?: return
        val intent = Intent(context, PollReceiver::class.java).setAction(PollReceiver.ACTION)
        val pi = PendingIntent.getBroadcast(
            context, 0, intent, PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )
        // Tetap berjalan saat HP tidur (Doze), tanpa izin alarm tepat waktu.
        am.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, nextSlot(System.currentTimeMillis()), pi)
    }
}

class PollReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val app = context.applicationContext
        val pending = goAsync()
        Thread {
            try {
                SignalPoller.poll(app)
            } finally {
                PollScheduler.schedule(app)
                pending.finish()
            }
        }.start()
    }

    companion object {
        const val ACTION = "com.xausignal.app.POLL"
    }
}
