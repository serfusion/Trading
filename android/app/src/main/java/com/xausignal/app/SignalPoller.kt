package com.xausignal.app

import android.app.AlarmManager
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.Build
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
                val pending = mutableListOf<SignalEvent>()
                res.body?.string().orEmpty().lineSequence().forEach { line ->
                    val event = parse(line) ?: return@forEach
                    added++
                    val twin = "${event.type}|${event.symbol()}|${event.dir}|${event.price("entry")}"
                    if (last != null && (event.type != "signal" || seen.add(twin))) pending += event
                }
                // notifikasi setelah SEMUA pesan terbaca: heartbeat (posisi terbuka di cloud) datang sesudah TUTUP di
                // tick yang sama, dan dibutuhkan untuk tahu apakah TUTUP itu final (set utama sinyal kembar)
                pending.forEach { notify(context, it) }
                SignalRepository.setConnection("Terhubung")
                added
            }
        } catch (e: Exception) {
            SignalRepository.setConnection("Offline")
            0
        } finally {
            SignalRepository.flush()
            try {
                CopyEvents.poll(context)               // 👁 cadangan kejadian copy trader (bila layanan ⚡ mati)
            } catch (e: Exception) {
                // opsional
            }
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
        if (event.pairGroup() !in SignalRepository.followed()) return   // pair yang tidak diikuti: tanpa notifikasi
        when (event.type) {
            "signal" -> if ((event.status == "signal" || event.status == "opened") && !event.isVoid()) {
                Notifications.signal(context, event)
            }
            "close" -> Notifications.close(context, event)
            "spot_signal" -> Notifications.spotSignal(context, event)
            "arus_signal", "arus_fill", "arus_close", "arus_cancel" -> Notifications.arus(context, event)
            "pulih_signal", "pulih_close" -> Notifications.pulih(context, event)
            "spot_close" -> Notifications.spotClose(context, event)
            "spot_warn" -> Notifications.spotWarn(context, event)
            "info" -> when {
                event.str("kind") == "be07" ->
                    if (SignalRepository.money().use07(event.id, SignalRepository.signalTier(event.id))) {
                        Notifications.be07(context, event)
                    }
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
        // Tetap berjalan saat HP tidur (Doze). Alarm tepat waktu (tidak ditunda sistem sampai belasan menit) bila
        // diizinkan: Android 12 ke atas memakai izin alarm tepat (USE_EXACT_ALARM / SCHEDULE_EXACT_ALARM).
        val at = nextSlot(System.currentTimeMillis() + 60_000L)   // min 1 menit ke depan: alarm tak pernah berulang
        val exact = if (Build.VERSION.SDK_INT >= 31) am.canScheduleExactAlarms() else true
        try {
            if (exact) am.setExactAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, at, pi)
            else am.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, at, pi)
        } catch (e: SecurityException) {
            am.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, at, pi)
        }
    }
}

class PollReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val app = context.applicationContext
        val pending = goAsync()
        Thread {
            try {
                SignalPoller.poll(app)
                try {
                    NewsAlarm.refreshIfStale(app)          // kalender berita untuk pengingat ⏱️ (tiap 6 jam)
                } catch (e: Exception) {
                    // pengingat berita opsional
                }
            } finally {
                CopyStreamControl.sync(app)                // ⚡ hidupkan lagi pemantau copy trader bila dimatikan sistem
                PollScheduler.schedule(app)
                NewsAlarm.schedule(app)
                pending.finish()
            }
        }.start()
    }

    companion object {
        const val ACTION = "com.xausignal.app.POLL"
    }
}
