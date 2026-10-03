package com.xausignal.app

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.media.AudioAttributes
import android.media.RingtoneManager
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat

object Notifications {
    private const val CH_SIGNAL = "signals"
    private const val CH_ACTION = "action_loud"   // TP1 / SL+: suara alarm (lebih keras) agar tidak terlewat

    fun createChannels(context: Context) {
        val nm = context.getSystemService(NotificationManager::class.java)
        nm.createNotificationChannel(
            NotificationChannel(CH_SIGNAL, "Sinyal XAU/USD", NotificationManager.IMPORTANCE_HIGH).apply {
                enableVibration(true)
            }
        )
        nm.createNotificationChannel(
            NotificationChannel(CH_ACTION, "TP1 & SL+ (suara keras)", NotificationManager.IMPORTANCE_HIGH).apply {
                enableVibration(true)
                vibrationPattern = longArrayOf(0, 600, 250, 600, 250, 600)
                setSound(
                    RingtoneManager.getDefaultUri(RingtoneManager.TYPE_ALARM)
                        ?: RingtoneManager.getDefaultUri(RingtoneManager.TYPE_NOTIFICATION),
                    AudioAttributes.Builder()
                        .setUsage(AudioAttributes.USAGE_ALARM)
                        .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                        .build()
                )
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
        val badge = (if (event.newsTag() != null) "📰" else "") + (if (event.isLayer()) "🔁" else "") +
            (if (event.isZap()) "⚡" else "") + "💰".repeat(event.moneyBadge()) + "⭐".repeat(event.stars())
        val title = "${if (badge.isBlank()) "" else "$badge "}${event.dir} ${event.symbol()} @ ${event.price("entry")}"
        val m = SignalRepository.money()
        val s07 = event.json.has("wr07") && m.use07(event.id, event.tier())
        val stats = if (event.json.has("wr")) {
            "WR ${fmt(event.json.optDouble(if (s07) "wr07" else "wr"), 0)}% • " +
                "${signed(event.json.optDouble(if (s07) "avg_r07" else "avg_r"))}R • "
        } else ""
        val zap = if (event.isZap()) "⚡ KESEMPATAN EMAS (risiko ${fmt(m.zapRiskPct, 1).replace('.', ',')}%" +
            (if (m.use07(event.id, event.tier())) ", SL+ saat profit 0,7R" else "") + ") • " else ""
        val extra = (if (event.isLayer()) "🔁 LAPISAN (lot ½) • " else "") +
            (event.newsTag()?.let { "📰 setelah ${it.optString("berita")} • " } ?: "")
        val text = extra + zap + stats +
            "SL ${event.price("sl")} • TP ${event.price("tp1")} • Entry " + legsLot(event, m) +
            (event.warText()?.let { "\n$it" } ?: "")
        post(context, event.id.hashCode(), title, text)
    }

    fun info(context: Context, event: SignalEvent) {
        val m = SignalRepository.money()
        val title = "🎯 TP1 kena • ${event.str("symbol").ifBlank { "XAU/USD" }}"
        val left = 5 - m.tpLegs
        post(context, (event.id + "info").hashCode(), title,
            "Tutup ${m.tpLegs} posisi, pindahkan SL $left posisi sisa ke ${slPlus(event)} SEKARANG. " +
                "$left posisi running jangan ditutup: tunggu notifikasi TUTUP.", CH_ACTION)
    }

    fun be07(context: Context, event: SignalEvent) {
        val sym = event.str("symbol").ifBlank { "XAU/USD" }
        post(context, (event.id + "be07").hashCode(), "🛡️ SL+ sekarang • $sym",
            "Profit 0,7R: pindahkan SL semua posisi ke ${slPlus(event)}", CH_ACTION)
    }

    /** Harga SL+ dari cloud (entry ± 0,10); event lama tanpa harga -> "entry". */
    private fun slPlus(event: SignalEvent): String =
        if (event.num("sl_plus") != null) event.price("sl_plus") else "entry"

    fun close(context: Context, event: SignalEvent) {
        val sym = event.symbol()
        if (event.isVoid()) {
            post(context, event.id.hashCode() + 1, "BATAL ${event.dir} $sym", "Sinyal dari data saat pasar tutup, abaikan")
            return
        }
        val events = SignalRepository.events.value
        // Sinyal kembar memakai 1 harga TUTUP (set paling lambat, tutup paling akhir). Set lain yang lebih cepat
        // tutup tanpa notifikasi: posisi Anda belum perlu ditutup.
        if ((SignalRepository.primaryOf(events)[event.id] ?: event.id) != event.id) return
        val m = SignalRepository.money()
        val win = SignalRepository.isWin(event, events)
        val title = "🏁 TUTUP ${event.dir} $sym • ${if (win) "PROFIT" else "MINUS"}"
        val amount = SignalRepository.amount(event, m)
        val text = "Tutup SEMUA posisi sinyal ini di MT5. Harga @ ${event.price("price")}" +
            (event.str("reason").takeIf { it.isNotBlank() }?.let { " • $it" } ?: "") +
            (amount?.let { "\nHasil ≈ ${moneyMain(it, m)} (${idrLine(it, m)})" } ?: "")
        post(context, event.id.hashCode() + 1, title, text)
    }

    /** ⏱️ Pengingat 1 menit sebelum rilis berita (NewsAlarm). Informasi saja: aplikasi tidak membuka order. */
    fun news(context: Context, items: List<NewsAlarm.Item>) {
        val first = items.minByOrNull { it.at } ?: return
        val title = "⏱️ 1 menit lagi: ${items.joinToString(" + ") { it.title }}"
        // beberapa berita di jam yang sama (NFP + Unemployment Rate + AHE): pakai teks khusus grup bila ada
        val own = items.filter { it.specific && it.info.isNotBlank() }
        val info = (own.ifEmpty { items }).map { it.info }.filter { it.isNotBlank() }.distinct()
        val text = "Rilis ${first.whenText}." + (if (info.isEmpty()) "" else "\n" + info.joinToString("\n")) +
            "\nSpread melebar di detik pertama."
        post(context, ("news" + first.at).hashCode(), title, text, CH_ACTION)
    }

    private fun post(context: Context, id: Int, title: String, text: String, channel: String = CH_SIGNAL) {
        if (Build.VERSION.SDK_INT >= 33 &&
            context.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED
        ) return
        val n = NotificationCompat.Builder(context, channel)
            .setSmallIcon(R.drawable.ic_stat)
            .setContentTitle(title)
            .setContentText(text)
            .setStyle(NotificationCompat.BigTextStyle().bigText(text))
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
