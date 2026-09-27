package com.xausignal.app

import android.Manifest
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
    private const val CH_SIGNAL = "signals"

    fun createChannels(context: Context) {
        val nm = context.getSystemService(NotificationManager::class.java)
        nm.createNotificationChannel(
            NotificationChannel(CH_SIGNAL, "Sinyal XAU/USD", NotificationManager.IMPORTANCE_HIGH).apply {
                enableVibration(true)
            }
        )
        nm.deleteNotificationChannel("service")   // notifikasi "menunggu sinyal" versi lama
    }

    private fun openApp(context: Context): PendingIntent {
        val intent = Intent(context, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP)
        return PendingIntent.getActivity(
            context, 0, intent, PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )
    }

    fun signal(context: Context, event: SignalEvent) {
        val star = if (event.isStar()) "⭐ " else ""
        val title = "$star${event.dir} XAU/USD @ ${fmt(event.num("entry"))}"
        val text = "SL ${fmt(event.num("sl"))} • TP1 ${fmt(event.num("tp1"))} • " +
            legsLot(event, SignalRepository.money())
        post(context, event.id.hashCode(), title, text)
    }

    fun info(context: Context, event: SignalEvent) {
        val title = event.str("text").lineSequence().firstOrNull() ?: APP_NAME
        post(context, (event.id + "info").hashCode(), title, "SL posisi sisa → entry (SL+)")
    }

    fun close(context: Context, event: SignalEvent) {
        val r = event.num("r") ?: 0.0
        val title = "TUTUP ${event.dir} • ${if (r > 0) "MENANG" else "KALAH"} ${signed(r)}R"
        post(context, event.id.hashCode() + 1, title, "Ditutup @ ${fmt(event.num("price"))}")
    }

    private fun post(context: Context, id: Int, title: String, text: String) {
        if (Build.VERSION.SDK_INT >= 33 &&
            context.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED
        ) return
        val n = NotificationCompat.Builder(context, CH_SIGNAL)
            .setSmallIcon(R.drawable.ic_stat)
            .setContentTitle(title)
            .setContentText(text)
            .setSubText(APP_NAME)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setDefaults(NotificationCompat.DEFAULT_ALL)
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
