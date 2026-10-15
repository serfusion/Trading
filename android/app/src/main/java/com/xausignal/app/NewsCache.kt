package com.xausignal.app

import android.content.Context
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import org.json.JSONObject
import java.io.File
import java.util.concurrent.locks.ReentrantLock
import kotlin.concurrent.withLock

/**
 * 4.45 (pengguna 15 Okt 2026: "terkadang menunggu news di bawah XAU lama muncul, terkadang tidak muncul, saya mau langsung
 * muncul"). Dulu baris di bawah XAU menunggu GET /api/chat penuh (cloud ±1–17 dtk, batas 40 dtk; gagal = kosong lalu menunggu
 * 60 dtk) dan 2–3 permintaan penuh berjalan bersamaan saat aplikasi dibuka. Kini respons terakhir yang berhasil disimpan di HP
 * (berita_cache.json) → langsung tampil saat dibuka (hitung mundur dihitung HP sendiri), lalu diperbarui di latar. Satu
 * permintaan bersama: pemanggil yang datang saat permintaan lain berjalan memakai hasil permintaan itu.
 */
object NewsCache {
    private const val FILE = "berita_cache.json"
    private var file: File? = null
    private val lock = ReentrantLock()
    @Volatile private var raw: String? = null
    @Volatile private var lastOk = 0L

    /** Waktu (ms) data tersimpan terakhir berhasil diambil dari cloud; 0 = belum pernah. */
    @Volatile var savedAt: Long = 0L
        private set

    private val _prep = MutableStateFlow<JSONObject?>(null)

    /** Persiapan berita (pra_satu, kartu, …) terbaru: dari HP saat dibuka, lalu dari cloud. */
    val prep: StateFlow<JSONObject?> = _prep

    @Synchronized
    fun init(context: Context) {
        if (file != null) return
        val f = File(context.applicationContext.filesDir, FILE)
        file = f
        try {
            if (f.exists() && f.length() > 0) {
                val r = f.readText()
                _prep.value = JSONObject(r).optJSONObject("persiapan")
                raw = r
                savedAt = f.lastModified()
            }
        } catch (e: Exception) {
            raw = null                                   // file rusak → abaikan, diganti saat GET berikutnya berhasil
        }
    }

    fun raw(): String? = raw

    /** Jalankan [block] (GET cloud, isi mentah atau null) sekali untuk semua pemanggil bersamaan. null = gagal. */
    fun fetch(block: () -> String?): String? {
        val mulai = System.currentTimeMillis()
        lock.withLock {
            if (lastOk >= mulai) return raw              // permintaan lain baru saja berhasil saat kita menunggu giliran
            val r = block() ?: return null
            simpan(r)
            return r
        }
    }

    private fun simpan(r: String) {
        val now = System.currentTimeMillis()
        try {
            _prep.value = JSONObject(r).optJSONObject("persiapan")
        } catch (e: Exception) {
            return
        }
        raw = r
        savedAt = now
        lastOk = now
        try {
            file?.writeText(r)
        } catch (e: Exception) {
            // penyimpanan penuh → tetap tampil dari memori
        }
    }
}
