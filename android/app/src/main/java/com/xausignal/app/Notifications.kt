package com.xausignal.app

import android.Manifest
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat

object Notifications {
    const val FOREGROUND_ID = 1
    private const val CH_SIGNAL = "signals"
    private const val CH_SERVICE = "service"

    fun createChannels(context: Context) {
        val nm = context.getSystemService(NotificationManager::class.java)
        nm.createNotificationChannel(
            NotificationChannel(CH_SIGNAL, "Sinyal trading", NotificationManager.IMPORTANCE_HIGH).apply {
                description = "Sinyal BUY/SELL dan TUTUP posisi"
                enableVibration(true)
            }
        )
        nm.createNotificationChannel(
            NotificationChannel(CH_SERVICE, "Koneksi ke bot", NotificationManager.IMPORTANCE_MIN)
        )
    }

    private fun openApp(context: Context): PendingIntent {
        val intent = Intent(context, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP)
        return PendingIntent.getActivity(
            context, 0, intent, PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )
    }

    fun foreground(context: Context, text: String): Notification =
        NotificationCompat.Builder(context, CH_SERVICE)
            .setSmallIcon(R.drawable.ic_stat)
            .setContentTitle("XAU Signal aktif")
            .setContentText(text)
            .setContentIntent(openApp(context))
            .setOngoing(true)
            .build()

    fun signal(context: Context, event: SignalEvent) {
        val title = "${if (event.dir == "BUY") "🟢" else "🔴"} ${event.dir} XAUUSD ${event.str("set")} @ ${fmt(event.num("entry"))}"
        val text = "SL ${fmt(event.num("sl"))} • TP1 ${fmt(event.num("tp1"))} • lot ${event.str("lot").ifBlank { "-" }}\n" +
            "TP1 kena -> SL sisa ke entry (SL+). Tunggu sinyal TUTUP."
        post(context, event.id.hashCode(), title, text)
    }

    fun info(context: Context, event: SignalEvent) {
        val text = event.str("text")
        val title = text.lineSequence().firstOrNull() ?: "XAU Signal"
        post(context, (event.id + "info").hashCode(), title, text)
    }

    fun close(context: Context, event: SignalEvent) {
        val r = event.num("r")
        val title = "🏁 TUTUP ${event.dir} XAUUSD @ ${fmt(event.num("price"))}"
        val text = "Hasil ${fmt(event.num("points"))} poin (${fmt(r)}R) • ${event.str("reason")}"
        post(context, event.id.hashCode() + 1, title, text)
    }

    private fun post(context: Context, id: Int, title: String, text: String) {
        if (Build.VERSION.SDK_INT >= 33 &&
            context.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED
        ) return
        val n = NotificationCompat.Builder(context, CH_SIGNAL)
            .setSmallIcon(R.drawable.ic_stat)
            .setContentTitle(title)
            .setContentText(text)
            .setSubText(BRAND)
            .setStyle(NotificationCompat.BigTextStyle().bigText(text))
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setAutoCancel(true)
            .setContentIntent(openApp(context))
            .build()
        try {
            NotificationManagerCompat.from(context).notify(id, n)
        } catch (e: SecurityException) {
            // izin notifikasi dicabut pengguna
        }
    }
}
