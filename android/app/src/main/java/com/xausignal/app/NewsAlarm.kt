package com.xausignal.app

import android.app.AlarmManager
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.Build
import org.json.JSONArray
import org.json.JSONObject
import java.time.OffsetDateTime

/**
 * ⏱️ Pengingat berita: alarm tepat 1 menit sebelum rilis berita USD berdampak tinggi (kalender GET /api/chat),
 * supaya pengguna siap di detik pertama. Isi notifikasi = angka riset detik pertama dari cloud
 * (research/news_detik.py -> persiapan.detik). HANYA pengingat: tidak membuka order.
 */
object NewsAlarm {
    private const val PREFS = "news_alarm"
    private const val LEAD = 60_000L                  // bunyi 1 menit sebelum rilis
    private const val REFRESH = 6 * 3_600_000L        // kalender diambil ulang dari poller tiap 6 jam

    /** specific = teks riset khusus grup berita ini (bukan ringkasan SEMUA). */
    data class Item(val at: Long, val title: String, val whenText: String, val info: String,
                    val specific: Boolean = false)

    private fun prefs(context: Context) = context.applicationContext.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    fun enabled(context: Context): Boolean = prefs(context).getBoolean("on", true)

    fun setEnabled(context: Context, on: Boolean) {
        prefs(context).edit().putBoolean("on", on).apply()
        schedule(context)
    }

    /** Simpan berita pekan ini dari GET /api/chat (kalender + teks detik pertama per grup) lalu jadwalkan alarm. */
    fun update(context: Context, calendar: List<CalEvent>, persiapan: JSONObject?) {
        val detik = persiapan?.optJSONObject("detik")
        val arr = JSONArray()
        calendar.forEach { e ->
            val at = try {
                OffsetDateTime.parse(e.time).toInstant().toEpochMilli()
            } catch (x: Exception) {
                return@forEach
            }
            val own = detik?.optJSONObject(e.group)
            val info = (own ?: detik?.optJSONObject("SEMUA"))?.optString("alarm").orEmpty()
            arr.put(JSONObject().put("at", at).put("title", e.title).put("when", e.whenText).put("info", info)
                .put("specific", own != null))
        }
        prefs(context).edit().putString("items", arr.toString()).putLong("fetched", System.currentTimeMillis()).apply()
        schedule(context)
    }

    /** Dipanggil poller latar belakang: ambil ulang kalender bila data sudah > 6 jam (atau belum pernah). */
    fun refreshIfStale(context: Context) {
        if (!enabled(context)) return
        if (System.currentTimeMillis() - prefs(context).getLong("fetched", 0L) < REFRESH) return
        val (cal, _, prep) = ChatClient.news()
        if (cal.isNotEmpty()) update(context, cal, prep)
    }

    fun items(context: Context): List<Item> = try {
        val arr = JSONArray(prefs(context).getString("items", "[]") ?: "[]")
        (0 until arr.length()).map { i ->
            val o = arr.getJSONObject(i)
            Item(o.optLong("at"), o.optString("title"), o.optString("when"), o.optString("info"),
                o.optBoolean("specific"))
        }
    } catch (e: Exception) {
        emptyList()
    }

    /** Berita berikutnya yang pengingatnya belum lewat (untuk ditampilkan di kartu). */
    fun next(context: Context, now: Long = System.currentTimeMillis()): Item? =
        items(context).filter { it.at - LEAD > now }.minByOrNull { it.at }

    private fun pending(context: Context): PendingIntent {
        val intent = Intent(context, NewsAlarmReceiver::class.java).setAction(NewsAlarmReceiver.ACTION)
        return PendingIntent.getBroadcast(context, 1, intent, PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
    }

    fun schedule(context: Context) {
        val am = context.getSystemService(AlarmManager::class.java) ?: return
        val pi = pending(context)
        val nxt = if (enabled(context)) next(context) else null
        if (nxt == null) {
            am.cancel(pi)
            return
        }
        val at = nxt.at - LEAD
        val exact = if (Build.VERSION.SDK_INT >= 31) am.canScheduleExactAlarms() else true
        try {
            if (exact) am.setExactAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, at, pi)
            else am.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, at, pi)
        } catch (e: SecurityException) {
            am.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, at, pi)
        }
    }

    /** Berita yang rilis dalam 3 menit ke depan (beberapa berita bisa rilis di jam yang sama -> satu notifikasi). */
    fun due(context: Context, now: Long = System.currentTimeMillis()): List<Item> =
        items(context).filter { it.at in (now - 30_000L)..(now + 3 * 60_000L) }
}

class NewsAlarmReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val app = context.applicationContext
        val due = NewsAlarm.due(app)
        if (due.isNotEmpty() && NewsAlarm.enabled(app)) {
            Notifications.createChannels(app)
            Notifications.news(app, due)
        }
        NewsAlarm.schedule(app)
    }

    companion object {
        const val ACTION = "com.xausignal.app.NEWS_ALARM"
    }
}
