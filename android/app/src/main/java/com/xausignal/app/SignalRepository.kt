package com.xausignal.app

import android.content.Context
import android.content.SharedPreferences
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import org.json.JSONArray
import org.json.JSONObject
import java.time.LocalDateTime
import java.time.OffsetDateTime
import java.time.ZoneOffset
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Locale

/** Satu pesan dari bot (signal / close / heartbeat / info). */
data class SignalEvent(val msgId: String, val type: String, val json: JSONObject) {
    val id: String get() = str("id").ifBlank { msgId }
    val dir: String get() = str("dir")
    val status: String get() = str("status")

    fun str(key: String): String =
        if (json.has(key) && !json.isNull(key)) json.optString(key, "") else ""

    fun num(key: String): Double? =
        if (json.has(key) && !json.isNull(key)) json.optDouble(key).takeIf { !it.isNaN() } else null

    fun timeText(): String = formatTime(str("time"))
}

private val WIB: ZoneId = ZoneId.of("Asia/Jakarta")
private val TIME_FMT: DateTimeFormatter = DateTimeFormatter.ofPattern("dd MMM HH:mm", Locale("id"))

fun formatTime(raw: String): String = try {
    OffsetDateTime.parse(raw.replace(" ", "T")).atZoneSameInstant(WIB).format(TIME_FMT) + " WIB"
} catch (e: Exception) {
    raw
}

fun fmt(value: Double?, digits: Int = 2): String =
    if (value == null) "-" else String.format(Locale.US, "%,.${digits}f", value)

data class Stats(val closed: Int, val wins: Int, val totalR: Double)

/** Pengaturan uang untuk menghitung profit/rugi dari sinyal. */
data class MoneySettings(
    val cent: Boolean,
    val legLot: Double,
    val idrRate: Double,
    val starLot: Double = legLot,
    val tpLegs: Int = 1,            // posisi yang ditutup di TP1 (1 atau 3)
    val be07: Boolean = false,      // SL+ saat profit 0,7R (bukan menunggu TP1)
    val modalIdr: Double = 0.0,     // modal (Rp) yang dipakai hitung lot; 0 = pakai lot manual
    val riskPct: Double = 0.5,      // rugi maks per sinyal saat SL, % modal (🥈/🥉; biasa = setengahnya)
    val zapRiskPct: Double = 1.0,   // rugi maks sinyal ⚡ kesempatan emas
    val slAuto: Boolean = true,     // SL+ otomatis: ⚡ & BTC di 0,7R, XAU lainnya setelah TP1
    val autoModal: Boolean = false, // modal = modal awal + profit/rugi riwayat sejak disimpan
    val baseModalIdr: Double = modalIdr,
) {
    val currency: String get() = if (cent) "USC" else "USD"

    /** Kunci hasil skema di event TUTUP cloud (r_by), mis. "3_07". */
    val schemeKey: String get() = "${tpLegs}_${if (be07) "07" else "tp1"}"

    /**
     * SL+ di 0,7R untuk sinyal ini? Otomatis: ⚡ dan BTC (research/momen.py: ⚡ + SL+ 0,7R WR 63–64%, profit setara;
     * BTC profit sama dengan WR +8 poin); XAU lainnya menunggu TP1 (profit XAU lebih besar).
     */
    fun use07(id: String, tier: String): Boolean = if (slAuto) id.startsWith("BTC-") || tier == "zap" else be07

    fun schemeFor(id: String, tier: String): String = "${tpLegs}_${if (use07(id, tier)) "07" else "tp1"}"

    /** Risiko % per peringkat: ⚡ = zapRiskPct, biasa = setengah riskPct, lainnya riskPct. */
    fun riskFor(tier: String): Double = when (tier) {
        "zap" -> zapRiskPct
        "biasa" -> riskPct / 2
        else -> riskPct
    }

    /** Lot per posisi: sinyal ⭐ memakai lot ⭐, sinyal biasa memakai lot biasa. */
    fun lotFor(star: Boolean): Double = if (star) starLot else legLot

    /** Saldo akun dalam mata uang akun (USC untuk Cent, USD untuk akun USD). */
    val balance: Double get() = if (cent) modalIdr / idrRate * 100.0 else modalIdr / idrRate

    /**
     * Lot per posisi untuk satu sinyal. Modal diisi: dihitung dari jarak SL sinyal supaya rugi semua posisi saat SL
     * ≈ [riskPct]% modal (dibulatkan ke bawah, minimal 0,01). Modal kosong: lot manual.
     */
    fun lotForSignal(star: Boolean, riskPoints: Double?, pointValue: Double, legs: Int, tier: String = ""): Double {
        if (modalIdr <= 0.0 || riskPoints == null || riskPoints <= 0.0) return lotFor(star)
        val hundredths = Math.floor(balance * riskFor(tier) / 100.0 / (riskPoints * legs * pointValue) + 1e-9)
        return (hundredths / 100.0).coerceAtLeast(0.01)
    }
}

fun SignalEvent.legs(): Int = num("legs")?.toInt() ?: 5

/** Jarak entry–SL awal (poin harga). */
fun SignalEvent.riskPoints(): Double? = num("risk_points")
    ?: num("entry")?.let { e -> num("sl")?.let { Math.abs(e - it) } }

/** Lot per posisi yang dimasukkan untuk sinyal ini (sinyal 🔁 lapisan: × lot_mult, mis. ½). */
fun SignalEvent.entryLot(m: MoneySettings): Double =
    withLotMult(m.lotForSignal(isStar(), riskPoints(), num("point_value") ?: 1.0, legs(), tier()), lotMult())

/** 🔁 Sinyal lapisan (cloud 2 Okt 2026): sinyal baru saat sinyal lain di set yang sama masih berjalan, lot ½. */
fun SignalEvent.isLayer(): Boolean = json.optBoolean("lapis", false)

fun SignalEvent.lotMult(): Double = num("lot_mult") ?: 1.0

/** Lot × pengali, dibulatkan ke bawah ke 0,01 (minimal 0,01). */
fun withLotMult(lot: Double, mult: Double): Double =
    if (mult >= 1.0) lot else (Math.floor(lot * mult * 100.0 + 1e-9) / 100.0).coerceAtLeast(0.01)

/** 📰 Sinyal setelah berita besar AS (≤ 4 jam): judul & teks riwayat dari cloud; null bila bukan. */
fun SignalEvent.newsTag(): JSONObject? = json.optJSONObject("news")

/** Peringkat dari cloud: zap (⚡ kesempatan emas), silver (🥈), bronze (🥉), biasa; "" = sinyal lama. */
fun SignalEvent.tier(): String = str("tier")

fun SignalEvent.isZap(): Boolean = tier() == "zap"

/** Label ⚠️ mode perang (minyak melonjak) dari cloud; null bila tidak aktif. */
fun SignalEvent.warText(): String? =
    json.optJSONObject("war")?.takeIf { it.optBoolean("on") }?.optString("text")?.ifBlank { null }

fun tierLabel(tier: String): String = when (tier) {
    "zap" -> "⚡ Emas"
    "silver" -> "🥈"
    "bronze" -> "🥉"
    "biasa" -> "Biasa"
    else -> ""
}

/** Rugi semua posisi bila SL kena (mata uang akun, positif). */
fun SignalEvent.maxLoss(m: MoneySettings): Double? = riskPoints()?.let {
    it * legs() * Math.round(entryLot(m) * 100.0) * (num("point_value") ?: 1.0)
}

fun SignalEvent.isStar(): Boolean = json.optBoolean("star", false)

/** Simbol sinyal (XAU/USD bila kosong). */
fun SignalEvent.symbol(): String = str("symbol").ifBlank { "XAU/USD" }

/** Harga dengan digit sesuai instrumen: JPY 3, forex lain 5, emas/BTC 2. */
fun priceText(symbol: String, v: Double?): String {
    if (v == null) return "-"
    val digits = if (symbol.contains("JPY")) 3 else if (Math.abs(v) < 20) 5 else 2
    return fmt(v, digits)
}

fun SignalEvent.price(key: String): String = priceText(symbol(), num(key))

/** Jumlah ★ (win rate historis) dan 💰 (profit historis). Sinyal lama: ★ = tanda kuat lama. */
fun SignalEvent.stars(): Int = if (json.has("stars")) json.optInt("stars") else if (isStar()) 1 else 0
fun SignalEvent.moneyBadge(): Int = json.optInt("money", 0)

/** Posisi virtual yang masih terbuka di cloud (dari heartbeat `exits`). */
data class CloudOpen(val symbol: String, val id: String, val dir: String, val set: String, val level: Double,
                     val bars: Int)

/** Set "T55/20" -> 20 (candle channel keluar); 0 untuk gap / sinyal tanpa set. */
fun SignalEvent.exitBars(): Int = str("set").substringAfter('/', "").toIntOrNull() ?: 0

/** Sinyal gap pekan forex (1 posisi, TP & SL, tutup otomatis 24 jam). */
fun SignalEvent.isGap(): Boolean = str("mode") == "gap"

/** Kelompok pair untuk "Pair yang saya ikuti": XAU, BTC, GAP (forex gap pekan), atau SPOT (💎 spot Binance). */
fun SignalEvent.pairGroup(): String = if (type.startsWith("spot")) "SPOT" else symbol().let {
    if (it.startsWith("XAU")) "XAU" else if (it.startsWith("BTC") || it.startsWith("ETH")) "BTC" else "GAP"
}

/** Waktu event (UTC), null bila tidak terbaca. */
fun SignalEvent.instant(): java.time.Instant? = try {
    OffsetDateTime.parse(str("time").replace(" ", "T")).toInstant()
} catch (e: Exception) {
    null
}

/**
 * Pesan TUTUP terlewat (mis. HP lama tidak mengecek > 12 jam sehingga cache ntfy habis): heartbeat cloud terbaru
 * (≥ 15 menit setelah sinyal) memuat daftar posisi terbuka (`exits`) dan sinyal ini tidak ada di sana.
 */
fun SignalEvent.closedByHeartbeat(hb: SignalEvent?): Boolean {
    val arr = hb?.json?.optJSONArray("exits") ?: return false
    if (isGap()) return false
    val t0 = instant() ?: return false
    val t1 = hb?.instant() ?: return false
    if (t1.isBefore(t0.plusSeconds(15 * 60))) return false
    return (0 until arr.length()).none { arr.optJSONObject(it)?.optString("id") == id }
}

/** "WR 82% • +0,26R/sinyal (2012–2020, 34 sinyal)" atau kosong untuk sinyal lama. */
fun SignalEvent.statsLine(): String {
    if (!json.has("wr")) return ""
    val avg = json.optDouble("avg_r")
    val sign = if (avg > 0) "+" else ""
    return "WR ${fmt(json.optDouble("wr"), 0)}% • ${sign}${fmt(avg, 2)}R/sinyal " +
        "(${str("period")}, ${json.optInt("n_hist")} sinyal)"
}

private val NEW_YORK: ZoneId = ZoneId.of("America/New_York")
private val STAMP: DateTimeFormatter = DateTimeFormatter.ofPattern("yyyyMMddHHmm")

/**
 * Sinyal batal: ditandai cloud (void) atau lahir dari candle akhir pekan saat pasar tutup
 * (Jumat 17:00 – Minggu 18:00 New York). ID sinyal cloud berakhiran waktu candle UTC, mis. ...-202609272100.
 */
fun SignalEvent.isVoid(): Boolean {
    if (json.optBoolean("void", false)) return true
    if (id.startsWith("BTC-") || symbol().contains("BTC")) return false      // BTC jalan 24/7
    val stamp = id.substringAfterLast('-')
    if (stamp.length != 12 || !stamp.all { it.isDigit() }) return false
    return try {
        val ny = LocalDateTime.parse(stamp, STAMP).atZone(ZoneOffset.UTC).withZoneSameInstant(NEW_YORK)
        val wd = ny.dayOfWeek.value   // Senin = 1 ... Minggu = 7
        wd == 6 || (wd == 5 && ny.hour >= 17) || (wd == 7 && ny.hour < 18)
    } catch (e: Exception) {
        false
    }
}

data class PeriodStats(
    val label: String,
    val wins: Int,
    val losses: Int,
    val profit: Double,   // jumlah untung (mata uang akun)
    val loss: Double,     // jumlah rugi (negatif)
) {
    val net: Double get() = profit + loss
    val total: Int get() = wins + losses
}

/** Penyimpanan sinyal (memori + SharedPreferences) yang dipakai layar & service. */
object SignalRepository {
    private const val PREFS = "xau_signal"
    private const val MAX_EVENTS = 300

    private val _events = MutableStateFlow<List<SignalEvent>>(emptyList())
    val events: StateFlow<List<SignalEvent>> = _events

    private val _heartbeat = MutableStateFlow<SignalEvent?>(null)
    val heartbeat: StateFlow<SignalEvent?> = _heartbeat

    /** Harga terakhir per simbol (XAU/USD, BTC/USD, ...). */
    private val _prices = MutableStateFlow<Map<String, SignalEvent>>(emptyMap())
    val prices: StateFlow<Map<String, SignalEvent>> = _prices

    /** 💎 Ringkasan sinyal spot terbaru dari cloud (spot_status: posisi terbuka, close terakhir, hasil teruji). */
    private val _spot = MutableStateFlow<JSONObject?>(null)
    val spot: StateFlow<JSONObject?> = _spot
    private var spotDirty: String? = null

    private val _connection = MutableStateFlow("Memuat...")
    val connection: StateFlow<String> = _connection

    private var prefs: SharedPreferences? = null

    /** Percakapan tab Tanya (disimpan di HP, maksimal 40 pesan). */
    private val _chat = MutableStateFlow<List<ChatMessage>>(emptyList())
    val chat: StateFlow<List<ChatMessage>> = _chat

    @Synchronized
    fun init(context: Context) {
        if (prefs != null) return
        prefs = context.applicationContext.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        load()
        loadChat()
        refreshAutoModal()
    }

    /** Alamat cloud Vercel (mis. https://nama.vercel.app) untuk tab Tanya. */
    fun cloudUrl(): String = prefs?.getString("cloud", "") ?: ""

    fun saveCloudUrl(url: String) {
        var u = url.trim().trimEnd('/')
        if (u.isNotEmpty() && !u.startsWith("http")) u = "https://$u"
        prefs?.edit()?.putString("cloud", u)?.apply()
    }

    @Synchronized
    fun addChat(m: ChatMessage) {
        _chat.value = (_chat.value + m).takeLast(40)
        saveChat()
    }

    @Synchronized
    fun clearChat() {
        _chat.value = emptyList()
        saveChat()
    }

    private fun saveChat() {
        val arr = JSONArray()
        _chat.value.forEach { m ->
            arr.put(JSONObject().put("r", m.role).put("t", m.text).put("s", JSONArray(m.sources)))
        }
        prefs?.edit()?.putString("chat", arr.toString())?.apply()
    }

    private fun loadChat() {
        _chat.value = try {
            val arr = JSONArray(prefs?.getString("chat", "[]") ?: "[]")
            (0 until arr.length()).map { i ->
                val o = arr.getJSONObject(i)
                val s = o.optJSONArray("s") ?: JSONArray()
                ChatMessage(o.optString("r"), o.optString("t"), (0 until s.length()).map { s.getString(it) })
            }
        } catch (e: Exception) {
            emptyList()
        }
    }

    fun server(): String = prefs?.getString("server", DEFAULT_SERVER) ?: DEFAULT_SERVER

    /**
     * Lot disimpan sebagai teks ("0.02"). Versi lama menyimpan Float: 0.01f dibaca sebagai Double menjadi
     * 0.009999999776482582, jadi nilai lama tetap dibaca lalu dibulatkan ke kelipatan 0,01.
     */
    fun money(): MoneySettings {
        val p = prefs
        val lot = p?.getString("leg_lot_text", null)?.toDoubleOrNull()
            ?: p?.let { if (it.contains("leg_lot")) it.getFloat("leg_lot", 0.01f).toDouble() else null }
            ?: 0.01
        val star = p?.getString("star_lot_text", null)?.toDoubleOrNull() ?: lot
        return MoneySettings(
            cent = p?.getBoolean("cent", true) ?: true,
            legLot = roundLot(lot).coerceAtLeast(0.01),
            // kurs bawaan Rp17.500 (30 Sep 2026); nilai bawaan lama 16.500 dianggap belum diisi
            idrRate = Math.round((p?.getFloat("idr_rate", 17500f) ?: 17500f).toDouble()).toDouble()
                .let { if (it == 16500.0) 17500.0 else it },
            starLot = roundLot(star).coerceAtLeast(0.01),
            tpLegs = 1,                 // skema tetap: 1 posisi TP1 + 4 running, SL+ saat TP1 kena (2.8)
            be07 = false,
            modalIdr = (p?.getString("modal_idr", null)?.toDoubleOrNull() ?: 0.0).let {
                if (it > 0 && p?.getBoolean("auto_modal", false) == true) it + autoPnlIdr else it
            },
            riskPct = p?.getFloat("risk_pct", 0.5f)?.toDouble() ?: 0.5,
            zapRiskPct = p?.getFloat("zap_risk_pct", 1.0f)?.toDouble() ?: 1.0,
            slAuto = p?.getBoolean("sl_auto", true) ?: true,
            autoModal = p?.getBoolean("auto_modal", false) ?: false,
            baseModalIdr = p?.getString("modal_idr", null)?.toDoubleOrNull() ?: 0.0,
        )
    }

    /** Profit/rugi (Rp) sinyal yang TUTUP sejak modal disimpan, untuk "Modal otomatis". Dihitung ulang per polling. */
    @Volatile
    private var autoPnlIdr = 0.0

    fun autoPnl(): Double = autoPnlIdr

    private fun refreshAutoModal() {
        val p = prefs ?: return
        if (!p.getBoolean("auto_modal", false)) {
            autoPnlIdr = 0.0
            return
        }
        val since = p.getLong("modal_start", 0L)
        val base = money().copy(autoModal = false).let { it.copy(modalIdr = it.baseModalIdr) }
        val events = _events.value
        val primary = primaryOf(events)
        autoPnlIdr = events.filter {
            it.type == "close" && !it.isVoid() && (primary[it.id] ?: it.id) == it.id &&
                (it.instant()?.toEpochMilli() ?: 0L) >= since
        }.sumOf { e -> amount(e, base)?.let { toIdr(it, base) } ?: 0.0 }
    }

    fun saveMoney(m: MoneySettings) {
        // hitungan "Modal otomatis" mulai dari nol hanya bila modal awal diubah atau fitur baru dinyalakan
        val p0 = prefs
        val reset = p0 != null && (p0.getString("modal_idr", null) != m.baseModalIdr.toLong().toString() ||
            (m.autoModal && !p0.getBoolean("auto_modal", false)) || !p0.contains("modal_start"))
        if (reset) p0?.edit()?.putLong("modal_start", System.currentTimeMillis())?.apply()
        prefs?.edit()?.putBoolean("cent", m.cent)?.putString("leg_lot_text", lotText(m.legLot))?.remove("leg_lot")
            ?.putString("star_lot_text", lotText(m.starLot))
            ?.putInt("tp_legs", m.tpLegs)?.putBoolean("be07", m.be07)
            ?.putString("modal_idr", m.baseModalIdr.toLong().toString())?.putFloat("risk_pct", m.riskPct.toFloat())
            ?.putFloat("zap_risk_pct", m.zapRiskPct.toFloat())?.putBoolean("sl_auto", m.slAuto)
            ?.putBoolean("auto_modal", m.autoModal)
            ?.putFloat("idr_rate", m.idrRate.toFloat())?.apply()
        refreshAutoModal()
        _moneyVersion.value = _moneyVersion.value + 1
    }

    private val _moneyVersion = MutableStateFlow(0)
    val moneyVersion: StateFlow<Int> = _moneyVersion

    /** Profit/rugi satu sinyal TUTUP dalam mata uang akun (USD atau USC). */
    fun amount(e: SignalEvent, m: MoneySettings): Double? {
        e.num("pnl")?.let { return it }
        // hasil sesuai skema pilihan (1/3 posisi TP1, SL+ setelah TP1 / di 0,7R); sinyal lama: hasil standar
        val byScheme = e.json.optJSONObject("r_by")
        val key = m.schemeFor(e.id, e.tier())
        val r = if (byScheme != null && byScheme.has(key)) byScheme.optDouble(key) else e.num("r")
            ?: return null
        val risk = e.num("risk_points") ?: return null
        val legs = e.num("legs") ?: 5.0
        // 0,01 lot = 1 oz -> 1 unit mata uang akun per 1 poin harga (USD untuk akun USD, USC untuk Cent)
        val pointValue = e.num("point_value") ?: 1.0     // forex: nilai 1,0 harga per 0,01 lot
        // sinyal 🔁 lapisan: event TUTUP membawa "lapis"; lot ½ dari sinyal biasa
        val lot = withLotMult(m.lotForSignal(e.isStar(), risk, pointValue, legs.toInt(), e.tier()),
            if (e.json.optBoolean("lapis", false)) 0.5 else 1.0)
        return r * risk * legs * Math.round(lot * 100.0) * pointValue
    }

    /**
     * Sinyal kembar: beberapa set dengan simbol, arah, entry, dan candle sama. Entry cukup 1×, jadi hasil tiap
     * set dibagi jumlah kembarnya supaya riwayat/statistik = uang yang benar-benar didapat. id -> jumlah set.
     */
    fun twinCounts(events: List<SignalEvent>): Map<String, Int> = index(events).twins

    /**
     * Sinyal kembar di-entry sekali dengan SATU harga TUTUP: set paling lambat (candle keluar terbanyak, mis.
     * T80/30), yang juga selalu tutup paling akhir. Riset (research: grup 3 set XAU 2012–2026): keluar di set
     * paling lambat +0,42R/grup vs rata-rata 3 set +0,33R vs TUTUP pertama +0,22R; BTC +0,47 / +0,40 / +0,33R.
     * id sinyal -> id sinyal utama grupnya. Grup dibaca dari id ("T80/30-SELL-<candle>") dan memakai sinyal, TUTUP,
     * DAN posisi terbuka di heartbeat cloud (`exits`) — tetap benar walau data sinyal lama tidak ada di HP
     * (mis. aplikasi di-install ulang): TUTUP set cepat tidak dianggap final selama set utama masih terbuka.
     */
    fun primaryOf(events: List<SignalEvent>, prices: Map<String, SignalEvent> = _prices.value): Map<String, String> {
        val ids = events.filter { it.type == "signal" || it.type == "close" }.map { it.id } +
            prices.values.flatMap { hb -> cloudOpen(hb).map { it.id } }
        return ids.filter { it.isNotBlank() }.distinct().groupBy { twinKey(it) }.values.flatMap { g ->
            val p = g.maxByOrNull { exitBarsOf(it) } ?: g.first()
            g.map { it to p }
        }.toMap()
    }

    private val SET_ID = Regex("^(.*?)T\\d+/(\\d+)-(BUY|SELL)-(\\w+)$")

    /** "BTC-T55/20-BUY-202609280100" -> "BTC-BUY-202609280100": sama untuk semua set dari candle & arah yang sama. */
    fun twinKey(id: String): String =
        SET_ID.find(id)?.let { it.groupValues[1] + it.groupValues[3] + "-" + it.groupValues[4] } ?: id

    /** Jumlah candle channel keluar dari id ("T80/30-…" -> 30); 0 bila bukan sinyal trend. */
    fun exitBarsOf(id: String): Int = SET_ID.find(id)?.groupValues?.get(2)?.toIntOrNull() ?: 0

    /** Posisi yang masih terbuka di cloud menurut heartbeat (`exits`): id, arah, set, level TUTUP. */
    fun cloudOpen(hb: SignalEvent?): List<CloudOpen> {
        val arr = hb?.json?.optJSONArray("exits") ?: return emptyList()
        return (0 until arr.length()).mapNotNull { i ->
            val o = arr.optJSONObject(i) ?: return@mapNotNull null
            CloudOpen(hb.symbol(), o.optString("id"), o.optString("dir"), o.optString("set"), o.optDouble("level"),
                o.optInt("bars"))
        }
    }

    /**
     * Indeks pencarian (TP1, TUTUP, 0,7R, sinyal kembar) untuk satu daftar pesan. Dihitung sekali per daftar lalu
     * dipakai ulang, bukan dicari ulang di seluruh daftar untuk tiap kartu setiap kali harga bergerak (HP panas).
     */
    private class Index(events: List<SignalEvent>) {
        val tp1 = HashMap<String, SignalEvent>()
        val close = HashMap<String, SignalEvent>()
        val be07 = HashSet<String>()
        val twins: Map<String, Int>

        init {
            events.forEach { e ->
                when (e.type) {
                    "close" -> close.putIfAbsent(e.id, e)
                    "info" -> {
                        val id = e.str("id")
                        if (e.str("text").contains("TP1")) tp1.putIfAbsent(id, e)
                        if (e.str("kind") == "be07") be07.add(id)
                    }
                }
            }
            val groups = events.filter { it.type == "signal" }
                .groupBy { listOf(it.symbol(), it.dir, it.price("entry"), it.id.substringAfterLast('-')) }.values
            twins = groups.flatMap { g -> g.map { it.id to g.size } }.toMap()
        }
    }

    private val indexCache = ArrayList<Pair<List<SignalEvent>, Index>>()

    @Synchronized
    private fun index(events: List<SignalEvent>): Index {
        indexCache.firstOrNull { it.first === events }?.let { return it.second }
        val ix = Index(events)
        indexCache.add(0, events to ix)
        while (indexCache.size > 4) indexCache.removeAt(indexCache.size - 1)
        return ix
    }

    /** Menang = TP1 kena (gap: TP kena); kalah = SL atau TUTUP sebelum TP1. */
    /** PROFIT = hasil uang > 0 (skema pilihan, 3.26); data lama tanpa R: TP1 kena. Dulu TP1 kena = PROFIT, padahal
     *  TUTUP sebelum TP1 bisa untung dan TP1 lalu SL+ hanya ±impas. */
    fun isWin(close: SignalEvent, events: List<SignalEvent>): Boolean =
        amount(close, money())?.let { it > 0 }
            ?: (close.json.optBoolean("tp1_hit", false) || tp1Event(events, close.id) != null)

    fun toIdr(amount: Double, m: MoneySettings): Double =
        if (m.cent) amount / 100.0 * m.idrRate else amount * m.idrRate

    private fun zoned(e: SignalEvent): java.time.ZonedDateTime? = try {
        OffsetDateTime.parse(e.str("time").replace(" ", "T")).atZoneSameInstant(WIB)
    } catch (ex: Exception) {
        null
    }

    fun periodStats(events: List<SignalEvent>, m: MoneySettings, keyOf: (java.time.ZonedDateTime) -> String,
                    labelOf: (String) -> String = { it }, star: Boolean? = null,
                    symbol: String? = null): List<PeriodStats> {
        // (menang?, uang) per sinyal; sinyal kembar dihitung sekali lewat set utamanya (harga TUTUP yang dipakai)
        val groups = LinkedHashMap<String, MutableList<Pair<Boolean, Double>>>()
        val primary = primaryOf(events)
        events.filter {
            it.type == "close" && !it.isVoid() && (star == null || it.isStar() == star) &&
                (symbol == null || it.symbol() == symbol) && (primary[it.id] ?: it.id) == it.id
        }.forEach { e ->
            val t = zoned(e) ?: return@forEach
            val a = amount(e, m) ?: return@forEach
            groups.getOrPut(keyOf(t)) { mutableListOf() }.add((a > 0) to a)
        }
        return groups.entries.sortedByDescending { it.key }.map { (k, v) ->
            PeriodStats(labelOf(k), v.count { it.first }, v.count { !it.first },
                v.map { it.second }.filter { it > 0 }.sum(), v.map { it.second }.filter { it <= 0 }.sum())
        }
    }
    fun topic(): String = prefs?.getString("topic", "") ?: ""

    /** Pair yang diikuti (XAU, BTC, GAP): sinyal, notifikasi, dan ringkasan di tab Sinyal. Bawaan: semua. */
    fun followed(): Set<String> {
        val p = prefs
        val set = (p?.getString("follow", null) ?: "XAU,BTC,GAP,SPOT").split(",").filter { it.isNotBlank() }.toSet()
        // 💎 Spot (4.1) menyala sekali untuk pengguna lama; setelah itu mengikuti pilihan di Pengaturan
        if (p != null && !p.getBoolean("spot_mig", false)) {
            p.edit().putBoolean("spot_mig", true).putString("follow", (set + "SPOT").joinToString(",")).apply()
            return set + "SPOT"
        }
        return set
    }

    fun saveFollowed(groups: Set<String>) {
        prefs?.edit()?.putString("follow", groups.joinToString(","))?.apply()
    }

    fun termsAccepted(): Boolean = prefs?.getBoolean("terms_ok", false) ?: false
    fun acceptTerms() {
        prefs?.edit()?.putBoolean("terms_ok", true)?.apply()
    }

    // Ditulis ke disk sekali per polling lewat flush(), bukan per pesan (hemat CPU, disk, dan baterai).
    private var lastId: String? = null
    private val dirtyHb = HashMap<String, String>()
    private var eventsDirty = false

    fun lastMessageId(): String? = lastId ?: prefs?.getString("last_id", null)

    @Synchronized
    fun saveSettings(server: String, topic: String) {
        val changed = server != server() || topic != topic()
        prefs?.edit()?.putString("server", server.trim().trimEnd('/'))?.putString("topic", topic.trim())?.apply()
        if (changed) clear()
    }

    fun setConnection(text: String) {
        _connection.value = text
    }

    @Synchronized
    fun clear() {
        _events.value = emptyList()
        _heartbeat.value = null
        _prices.value = emptyMap()
        lastId = null
        dirtyHb.clear()
        eventsDirty = false
        val e = prefs?.edit() ?: return
        prefs?.all?.keys?.filter { it.startsWith("hb_") }?.forEach { e.remove(it) }
        e.remove("last_id").remove("events").remove("heartbeat").apply()
    }

    /** Tambah pesan; return null bila duplikat. */
    @Synchronized
    fun add(msgId: String, payload: JSONObject): SignalEvent? {
        val type = payload.optString("type", "info")
        val event = SignalEvent(msgId, type, payload)
        lastId = msgId
        if (type == "spot_status") {                  // ringkasan, bukan riwayat: tidak memenuhi daftar 300 pesan
            _spot.value = payload
            spotDirty = payload.toString()
            return event
        }
        if (type == "heartbeat") {
            val sym = payload.optString("symbol", "XAU/USD").ifBlank { "XAU/USD" }
            _prices.value = _prices.value + (sym to event)
            if (sym.startsWith("XAU")) _heartbeat.value = event
            dirtyHb[sym] = payload.toString()
            return event
        }
        if (_events.value.any { it.msgId == msgId }) return null
        _events.value = (listOf(event) + _events.value).take(MAX_EVENTS)
        eventsDirty = true
        return event
    }

    /** Simpan pesan & harga terbaru ke disk sekali per polling. */
    @Synchronized
    fun flush() {
        val e = prefs?.edit() ?: return
        lastId?.let { e.putString("last_id", it) }
        dirtyHb.forEach { (sym, json) ->
            e.putString("hb_$sym", json)
            if (sym.startsWith("XAU")) e.putString("heartbeat", json)
        }
        dirtyHb.clear()
        spotDirty?.let { e.putString("spot_status", it) }
        spotDirty = null
        if (eventsDirty) {
            val arr = JSONArray()
            _events.value.forEach { arr.put(JSONObject().put("m", it.msgId).put("p", it.json)) }
            e.putString("events", arr.toString())
            eventsDirty = false
        }
        e.apply()
        refreshAutoModal()
    }

    /**
     * Semua sinyal (per set) yang belum punya sinyal TUTUP. Dengan [prices] (heartbeat per simbol), sinyal yang
     * menurut heartbeat terbaru sudah tidak terbuka di cloud (pesan TUTUP terlewat) juga tidak dihitung aktif.
     */
    fun openSignals(events: List<SignalEvent>, prices: Map<String, SignalEvent> = emptyMap()): List<SignalEvent> {
        val closed = events.filter { it.type == "close" }.map { it.id }.toSet()
        return events.filter {
            it.type == "signal" && (it.status == "signal" || it.status == "opened") && it.id !in closed &&
                !it.isVoid() && !it.closedByHeartbeat(prices[it.symbol()])
        }
    }

    fun slPlusActive(events: List<SignalEvent>, signalId: String): Boolean =
        tp1Event(events, signalId) != null ||
            (signalId in index(events).be07 && money().use07(signalId, signalTier(signalId)))

    /** Peringkat sinyal (dari event sinyal di HP) untuk id ini; "" bila tidak ada. */
    fun signalTier(signalId: String): String =
        _events.value.firstOrNull { it.type == "signal" && it.id == signalId }?.tier() ?: ""

    /** Info TP1 kena (lalu SL+) untuk sinyal ini, bila ada. */
    fun tp1Event(events: List<SignalEvent>, signalId: String): SignalEvent? = index(events).tp1[signalId]

    fun closeEvent(events: List<SignalEvent>, signalId: String): SignalEvent? = index(events).close[signalId]

    fun stats(events: List<SignalEvent>): Stats {
        val closes = events.filter { it.type == "close" && it.num("r") != null }
        val rs = closes.mapNotNull { it.num("r") }
        return Stats(rs.size, rs.count { it > 0 }, rs.sum())
    }

    private fun load() {
        val p = prefs ?: return
        try {
            val arr = JSONArray(p.getString("events", "[]"))
            val list = ArrayList<SignalEvent>()
            for (i in 0 until arr.length()) {
                val o = arr.getJSONObject(i)
                val payload = o.getJSONObject("p")
                list.add(SignalEvent(o.getString("m"), payload.optString("type", "info"), payload))
            }
            _events.value = list
            p.getString("heartbeat", null)?.let {
                val hb = JSONObject(it)
                _heartbeat.value = SignalEvent("hb", "heartbeat", hb)
            }
            p.getString("spot_status", null)?.let { _spot.value = JSONObject(it) }
            _prices.value = p.all.keys.filter { it.startsWith("hb_") }.associate { k ->
                k.removePrefix("hb_") to SignalEvent("hb", "heartbeat", JSONObject(p.getString(k, "{}") ?: "{}"))
            }
        } catch (e: Exception) {
            _events.value = emptyList()
        }
    }

    const val DEFAULT_SERVER = "https://ntfy.sh"
}
