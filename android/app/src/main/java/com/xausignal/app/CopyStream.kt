package com.xausignal.app

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat
import androidx.core.app.ServiceCompat
import okhttp3.Call
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONObject
import java.io.IOException
import java.util.concurrent.TimeUnit

/**
 * ⚡ Notifikasi instan copy trader yang di-follow (aplikasi 4.16). Layanan latar mendengarkan topik ntfy
 * `<topik>-copy` terus-menerus (satu koneksi HTTP, ntfy mengirim keepalive tiap ±45 detik) → notifikasi BUKA/TUTUP
 * tiba ±detik setelah cloud mendeteksinya (cloud/api/_ikuti.py, cek tiap ±15 detik). Android mewajibkan notifikasi
 * kecil yang selalu tampil selama layanan berjalan; layanan hanya hidup bila ada trader di-follow dan ⚡ Instan ON.
 * Bila layanan mati / dimatikan, poll cadangan (SignalPoller, tiap 10 menit) tetap mengambil kejadian yang terlewat.
 */
object CopyStreamControl {
    fun shouldRun(context: Context): Boolean {
        SignalRepository.init(context)
        CopyFollow.init(context)
        return CopyFollow.instant && CopyFollow.keys.isNotEmpty() && SignalRepository.topic().isNotBlank()
    }

    fun sync(context: Context) {
        val app = context.applicationContext
        val intent = Intent(app, CopyStreamService::class.java)
        try {
            if (shouldRun(app)) {
                if (Build.VERSION.SDK_INT >= 26) app.startForegroundService(intent) else app.startService(intent)
            } else {
                app.stopService(intent)
            }
        } catch (e: Exception) {
            // Android 12+: layanan latar tidak boleh dimulai dari belakang → dicoba lagi saat aplikasi dibuka / alarm
        }
    }
}

/** Proses satu pesan ntfy topik -copy: simpan ke log + notifikasi. Dipakai layanan ⚡ dan poll cadangan. */
object CopyEvents {
    fun handle(context: Context, msgId: String, message: String) {
        CopyFollow.init(context)
        CopyFollow.setLastId(msgId)
        if (!CopyFollow.firstTime(msgId)) return
        val obj = try { JSONObject(message) } catch (e: Exception) { return }
        val arr = obj.optJSONArray("events") ?: return
        val events = (0 until arr.length()).mapNotNull { arr.optJSONObject(it) }
        CopyFollow.addLog(events)
        if (ageMs(obj.optString("time")) > STALE_MS) return     // kejadian lama (HP mati/offline): cukup masuk log
        events.forEach { e ->
            if ("${e.optString("platform")}|${e.optString("trader")}" in CopyFollow.keys) Notifications.copy(context, e)
        }
    }

    private const val STALE_MS = 15 * 60_000L

    private fun ageMs(iso: String): Long = try {
        val f = java.text.SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", java.util.Locale.US)
            .apply { timeZone = java.util.TimeZone.getTimeZone("UTC") }
        System.currentTimeMillis() - (f.parse(iso)?.time ?: 0L)
    } catch (e: Exception) {
        0L
    }

    private val client = OkHttpClient.Builder().connectTimeout(15, TimeUnit.SECONDS).readTimeout(20, TimeUnit.SECONDS).build()

    /** Poll cadangan (alarm 10 menit / aplikasi dibuka): ambil kejadian yang terlewat saat layanan ⚡ tidak berjalan. */
    fun poll(context: Context) {
        SignalRepository.init(context)
        CopyFollow.init(context)
        val topic = SignalRepository.topic()
        if (topic.isBlank() || (CopyFollow.keys.isEmpty() && CopyFollow.lastId() == null)) return
        val url = "${SignalRepository.server()}/$topic-copy/json?poll=1&since=${CopyFollow.lastId() ?: "1h"}"
        try {
            client.newCall(Request.Builder().url(url).build()).execute().use { res ->
                if (!res.isSuccessful) return
                res.body?.string().orEmpty().lineSequence().forEach { line -> parseLine(context, line) }
            }
        } catch (e: Exception) {
            // jaringan: dicoba lagi di poll berikutnya
        }
    }

    fun parseLine(context: Context, line: String) {
        if (line.isBlank()) return
        val o = try { JSONObject(line) } catch (e: Exception) { return }
        if (o.optString("event") == "message") handle(context, o.optString("id"), o.optString("message"))
    }
}

class CopyStreamService : Service() {
    @Volatile private var running = false
    @Volatile private var call: Call? = null
    private var worker: Thread? = null
    private val client = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(100, TimeUnit.SECONDS)          // ntfy keepalive tiap ±45 dtk; lebih lama = koneksi putus → sambung ulang
        .pingInterval(60, TimeUnit.SECONDS)
        .build()

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        startAsForeground()
        if (!CopyStreamControl.shouldRun(this)) {
            stopSelf()
            return START_NOT_STICKY
        }
        if (worker?.isAlive != true) {
            running = true
            worker = Thread { loop() }.apply { isDaemon = true; start() }
        }
        return START_STICKY
    }

    override fun onDestroy() {
        running = false
        call?.cancel()
        worker?.interrupt()
        super.onDestroy()
    }

    private fun startAsForeground() {
        val nm = getSystemService(NotificationManager::class.java)
        nm.createNotificationChannel(NotificationChannel(CH, "⚡ Pemantau copy trader (diam)", NotificationManager.IMPORTANCE_MIN))
        val open = PendingIntent.getActivity(this, 0, Intent(this, MainActivity::class.java)
            .addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP), PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
        val n: Notification = NotificationCompat.Builder(this, CH)
            .setSmallIcon(R.drawable.ic_stat)
            .setContentTitle("👁 Mengikuti ${CopyFollow.keys.size} trader")
            .setContentText("Notifikasi instan saat trader buka/tutup posisi")
            .setPriority(NotificationCompat.PRIORITY_MIN)
            .setOngoing(true)
            .setContentIntent(open)
            .build()
        val type = if (Build.VERSION.SDK_INT >= 34) ServiceInfo.FOREGROUND_SERVICE_TYPE_REMOTE_MESSAGING else 0
        ServiceCompat.startForeground(this, ID, n, type)
    }

    private fun loop() {
        var backoff = 5_000L
        while (running) {
            if (!CopyStreamControl.shouldRun(this)) {
                stopSelf()
                return
            }
            val topic = SignalRepository.topic()
            val since = CopyFollow.lastId() ?: "1m"
            val req = Request.Builder().url("${SignalRepository.server()}/$topic-copy/json?since=$since").build()
            try {
                val c = client.newCall(req)
                call = c
                c.execute().use { res ->
                    if (!res.isSuccessful) throw IOException("HTTP ${res.code}")
                    backoff = 5_000L
                    val src = res.body?.source() ?: throw IOException("tanpa isi")
                    while (running) {
                        val line = src.readUtf8Line() ?: break
                        CopyEvents.parseLine(this, line)
                    }
                }
            } catch (e: Exception) {
                if (!running) return
                try {
                    Thread.sleep(backoff)
                } catch (ie: InterruptedException) {
                    return
                }
                backoff = (backoff * 2).coerceAtMost(60_000L)
            }
        }
    }

    companion object {
        private const val CH = "copy_stream"
        private const val ID = 7716
    }
}
