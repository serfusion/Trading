package com.xausignal.app

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.selection.SelectionContainer
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Button
import androidx.compose.material3.FilterChip
import androidx.compose.material3.TextButton
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.key
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.TimeUnit

/** Satu pesan chat. role = "user" / "assistant"; sources = baris "judul — url". */
data class ChatMessage(val role: String, val text: String, val sources: List<String> = emptyList())

private val EXAMPLES = listOf(
    "NFP Act: 45K Cons: 98K Prev: 162K",
    "CPI lebih tinggi dari perkiraan",
    "Sebelum FOMC suku bunga naik, apa yang harus saya lakukan?",
    "Berita apa saja minggu ini?",
    "Sinyal terbuka sekarang",
    "SL+ di 0,7R atau TP1?",
)

/**
 * Berita USD high-impact minggu ini dari cloud (GET /api/chat): tanggal & jam WIB otomatis, Cons & Prev dari
 * ForexFactory, Act otomatis dari data resmi FRED setelah rilis (bila tersedia).
 */
data class CalEvent(val title: String, val whenText: String, val forecast: String, val previous: String,
                    val time: String = "", val released: Boolean = false, val actual: String = "")

/** Pilihan cepat bila kalender minggu ini belum termuat. */
private val DEFAULT_EVENTS = listOf(
    "Non-Farm Employment Change", "Unemployment Rate", "CPI m/m", "Core CPI m/m", "CPI y/y", "PPI m/m",
    "Core PCE Price Index m/m", "Retail Sales m/m", "Advance GDP q/q", "ISM Manufacturing PMI", "ISM Services PMI",
    "Unemployment Claims", "Federal Funds Rate",
)

/** Klien POST <alamat cloud>/api/chat. Kunci = topik ntfy (sama dengan cloud). */
object ChatClient {
    private val client = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .callTimeout(40, TimeUnit.SECONDS)
        .build()

    /** Kalender pekan ini + status tren per indikator (GET /api/chat). */
    fun news(): Pair<List<CalEvent>, JSONObject?> {
        val base = SignalRepository.cloudUrl()
        if (base.isBlank()) return emptyList<CalEvent>() to null
        val request = Request.Builder().url("$base/api/chat").get()
            .header("X-Chat-Key", SignalRepository.topic()).build()
        return try {
            client.newCall(request).execute().use { res ->
                val obj = JSONObject(res.body?.string().orEmpty())
                val arr = obj.optJSONArray("calendar") ?: JSONArray()
                (0 until arr.length()).map { i ->
                    val o = arr.getJSONObject(i)
                    CalEvent(o.optString("title"), o.optString("when"), o.optString("forecast"), o.optString("previous"),
                        o.optString("time"), o.optBoolean("released"), o.optString("actual"))
                } to obj.optJSONObject("tren")
            }
        } catch (e: Exception) {
            emptyList<CalEvent>() to null
        }
    }

    fun ask(history: List<ChatMessage>): ChatMessage {
        val base = SignalRepository.cloudUrl()
        if (base.isBlank()) return ChatMessage("assistant", "⚠️ Isi \"Alamat cloud\" di Pengaturan dulu (mis. https://nama-proyek.vercel.app).")
        val msgs = JSONArray()
        history.takeLast(12).forEach { msgs.put(JSONObject().put("role", it.role).put("content", it.text)) }
        val body = JSONObject().put("messages", msgs).toString()
            .toRequestBody("application/json; charset=utf-8".toMediaType())
        val request = Request.Builder().url("$base/api/chat").post(body)
            .header("X-Chat-Key", SignalRepository.topic()).build()
        return try {
            client.newCall(request).execute().use { res ->
                val obj = try { JSONObject(res.body?.string().orEmpty()) } catch (e: Exception) { JSONObject() }
                if (!res.isSuccessful || !obj.optBoolean("ok")) {
                    ChatMessage("assistant", "⚠️ ${obj.optString("error").ifBlank { "HTTP ${res.code}" }}")
                } else {
                    val src = obj.optJSONArray("sources") ?: JSONArray()
                    val lines = (0 until src.length()).map { i ->
                        val s = src.getJSONObject(i)
                        "${s.optString("title")} — ${s.optString("url")}"
                    }
                    ChatMessage("assistant", obj.optString("reply"), lines)
                }
            }
        } catch (e: Exception) {
            ChatMessage("assistant", "⚠️ Tidak bisa menghubungi cloud: ${e.message ?: e.javaClass.simpleName}")
        }
    }
}

/**
 * Blok "🎯 REKOMENDASI ENTRY" di atas setiap jawaban (ditampilkan tebal & besar): sinyal 💰 yang sedang terbuka
 * dengan entry, SL, TP1, lot dari modal & risiko di Pengaturan, WR & profit historis, level TUTUP, dan status
 * (masih bisa entry / terlambat / sudah berjalan). Tanpa sinyal terbuka: jangan entry, tunggu sinyal 💰.
 * Baris "▶" = data utama, "✅/⚠️/⏳" = status; dibaca oleh [Bubble].
 */
fun entryAdvice(events: List<SignalEvent>, prices: Map<String, SignalEvent>, m: MoneySettings,
                follow: Set<String>): String {
    val groups = SignalRepository.openSignals(events, prices).filter { it.pairGroup() in follow }
        .groupBy { Triple(it.symbol(), it.dir, it.price("entry")) }.values.take(3)
    val out = mutableListOf("🎯 REKOMENDASI ENTRY")
    if (groups.isEmpty()) {
        out += "▶ Belum ada sinyal 💰 terbuka → jangan entry dulu."
        out += "▶ Tunggu notifikasi 💰: entry di harga sinyal, SL & TP1 sesuai sinyal, lot dari aplikasi."
        out += "▶ Entry karena berita: diuji 36 cara (masuk setelah rilis, ikut/lawan kejutan, berbagai SL/TP) di " +
            "XAU 2012–2026 → semua rugi. Jadi tidak ada entry/TP/SL berita yang disarankan."
        out += "Tidak ada entry \"sempurna\". Yang terbukti di data hanya sinyal 💰 (entry saat sinyal, 1 posisi TP1, " +
            "4 posisi running sampai TUTUP); entry manual di luar sinyal tidak diuji."
        return out.joinToString("\n")
    }
    groups.forEach { g ->
        val s = g.first()
        val sym = s.symbol()
        val sign = if (s.dir == "BUY") 1 else -1
        val entry = s.num("entry") ?: return@forEach
        val risk = s.riskPoints() ?: return@forEach
        val pv = s.num("point_value") ?: 1.0
        val cents = Math.round(s.entryLot(m) * 100.0).toDouble()
        val gap = s.isGap()
        val price = prices[sym]?.num("price")
        val tp1Hit = !gap && g.any { SignalRepository.slPlusActive(events, it.id) }
        out += "▶ ${s.dir} $sym @ ${s.price("entry")}" + if (g.size > 1) " (${g.size} set sama, entry 1×)" else ""
        out += "▶ SL ${s.price("sl")} • ${if (gap) "TP" else "TP1 (posisi #1)"} ${s.price("tp1")}"
        out += "▶ Lot: ${legsLot(s, m)}"
        if (s.json.has("wr")) {
            val avgR = s.json.optDouble("avg_r")
            val avgMoney = avgR * risk * s.legs() * cents * pv
            out += "▶ WR ${fmt(s.json.optDouble("wr"), 0)}% • rata-rata ${signed(avgR)}R ≈ ${moneyMain(avgMoney, m)}" +
                " per sinyal (${s.json.optInt("n_hist")} sinyal historis)"
        }
        val tpMoney = (s.num("tp1")?.let { Math.abs(it - entry) } ?: risk) * cents * pv
        val loss = s.maxLoss(m) ?: 0.0
        out += "▶ ${if (gap) "TP" else "TP1"} +${fmt(tpMoney, 0)} ${m.currency} (${idrLine(tpMoney, m)}) • " +
            "SL −${fmt(loss, 0)} ${m.currency} (${idrLine(-loss, m)})"
        val exits = exitLevels(prices[sym], g.map { it.id })
        if (exits.isNotEmpty()) {
            out += "▶ 4 running ditutup saat close H1 ${if (sign > 0) "<" else ">"} " +
                exits.joinToString(" / ") { priceText(sym, it.level) }
        }
        val dist = price?.let { (it - entry) * sign / risk }
        out += when {
            tp1Hit -> "⏳ Sudah berjalan (TP1 kena): JANGAN entry baru. Posisi yang ada: SL 4 posisi di SL+ (≈ entry), " +
                "tunggu TUTUP."
            dist == null -> "⚠️ Harga terbaru belum ada — cek harga broker dulu."
            Math.abs(dist) <= 0.25 -> "✅ Masih bisa entry: harga ${priceText(sym, price)} dekat entry sinyal (${signed(dist)}R)."
            dist > 0 -> "⚠️ Harga sudah ${signed(dist)}R dari entry → terlambat (entry terlambat tidak diuji). " +
                "Lebih aman tunggu sinyal berikutnya."
            else -> "⚠️ Harga ${signed(dist)}R berlawanan arah (mendekati SL) → tidak diuji; lebih aman lewati."
        }
    }
    return out.joinToString("\n")
}

/** "dalam 2 j 15 m" / "sudah rilis" dari waktu ISO kalender. */
private fun countdown(e: CalEvent): String {
    if (e.released) return "✓ sudah rilis"
    return try {
        val m = java.time.Duration.between(java.time.Instant.now(), java.time.OffsetDateTime.parse(e.time).toInstant())
            .toMinutes()
        if (m <= 0) "✓ sudah rilis" else if (m < 60) "⏳ $m menit lagi" else if (m < 24 * 60) "⏳ ${m / 60} j ${m % 60} m lagi"
        else "⏳ ${m / (24 * 60)} hari lagi"
    } catch (ex: Exception) {
        "⏳"
    }
}

/**
 * Status tren sekarang per indikator, diurutkan dari yang paling sering benar di atas tebakan dasar (periode
 * terbaru). Persentase dari riset (research/tren_kedepan.py); ini status, bukan ramalan.
 */
@Composable
private fun TrendCard(tren: JSONObject?, loading: Boolean) {
    var asset by remember { mutableStateOf("XAU/USD") }
    var horizon by remember { mutableStateOf("1 minggu") }
    AppCard {
        CardTitle("📈 Status tren sekarang (per indikator)")
        Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            listOf("XAU/USD", "BTC/USD").forEach { a ->
                FilterChip(selected = asset == a, onClick = { asset = a }, label = { Text(a) })
            }
            listOf("1 hari", "1 minggu", "1 bulan").forEach { h ->
                FilterChip(selected = horizon == h, onClick = { horizon = h }, label = { Text(h) })
            }
        }
        val a = tren?.optJSONObject(asset)
        val j = a?.optJSONObject("jangka")?.optJSONObject(horizon)
        if (a == null || j == null) {
            Text(if (loading) "Memuat…" else a?.optString("error")?.ifBlank { null } ?: "Status tren belum tersedia " +
                "(butuh cloud terbaru).", color = Muted)
            return@AppCard
        }
        Text("Close ${a.optString("tanggal")}: ${priceText(asset, a.optDouble("harga"))} • " +
            "🟢 Bullish ${j.optInt("bullish")} • 🔴 Bearish ${j.optInt("bearish")}",
            fontWeight = FontWeight.Bold)
        val uji = a.optString("uji_mulai")
        val rows = j.optJSONArray("baris") ?: JSONArray()
        for (i in 0 until rows.length()) {
            val r = rows.getJSONObject(i)
            val arah = r.optInt("arah")
            LineDivider()
            Row(verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text(r.optString("nama"), style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Medium)
                    if (arah != 0) {
                        val lebih = r.optDouble("lebih")
                        Text("dasar ${fmt(r.optDouble("dasar_uji"), 0)}% (${signed(lebih, 1)}) • semua data " +
                            "${fmt(r.optDouble("benar"), 0)}%, n=${r.optInt("n")}",
                            style = MaterialTheme.typography.labelSmall, color = Muted)
                    }
                }
                Column(horizontalAlignment = Alignment.End) {
                    Text(if (arah > 0) "🟢 Bullish" else if (arah < 0) "🔴 Bearish" else "⚪ Netral",
                        fontWeight = FontWeight.Bold, color = if (arah > 0) BuyColor else if (arah < 0) SellColor else Muted)
                    if (arah != 0) {
                        Text("benar ${fmt(r.optDouble("benar_uji"), 0)}% ($uji–kini)", fontWeight = FontWeight.ExtraBold,
                            color = Gold, style = MaterialTheme.typography.labelLarge)
                    }
                }
            }
        }
        Text(
            "Persentase = saat indikator menunjukkan arah itu, seberapa sering harga benar-benar bergerak ke arah itu " +
                "dalam $horizon (data ${a.optString("periode")}; urutan: paling sering benar di atas tebakan dasar, " +
                "bisa berubah). Dasar = tebakan \"selalu naik/turun\". Tidak ada indikator yang konsisten lebih baik " +
                "dari tebakan dasar — ini status sekarang, BUKAN ramalan.",
            style = MaterialTheme.typography.labelSmall, color = Muted
        )
    }
}

/** Satu baris kalender: judul, waktu WIB, status, Act (otomatis) / Cons / Prev. */
@Composable
private fun NewsRow(e: CalEvent, onClick: () -> Unit) {
    Row(
        Modifier.fillMaxWidth().clickable(onClick = onClick).padding(vertical = 6.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(Modifier.weight(1f)) {
            Text(e.title, fontWeight = FontWeight.Bold, style = MaterialTheme.typography.bodyMedium)
            Text("${e.whenText} • ${countdown(e)}", style = MaterialTheme.typography.labelSmall, color = Muted)
        }
        Column(horizontalAlignment = Alignment.End) {
            if (e.actual.isNotBlank()) {
                Text("Act ${e.actual}", fontWeight = FontWeight.ExtraBold, color = Gold)
            } else if (e.released) {
                Text("Act: isi →", style = MaterialTheme.typography.labelMedium, color = Gold)
            }
            Text("Cons ${e.forecast.ifBlank { "-" }} • Prev ${e.previous.ifBlank { "-" }}",
                style = MaterialTheme.typography.labelSmall, color = Muted)
        }
    }
}

@Composable
fun NewsTab() {
    val messages by SignalRepository.chat.collectAsState()
    var input by remember { mutableStateOf("") }
    var busy by remember { mutableStateOf(false) }
    var showForm by remember { mutableStateOf(false) }
    var prefill by remember { mutableStateOf<CalEvent?>(null) }
    var calendar by remember { mutableStateOf<List<CalEvent>>(emptyList()) }
    var tren by remember { mutableStateOf<JSONObject?>(null) }
    var calLoading by remember { mutableStateOf(true) }
    val scope = rememberCoroutineScope()
    val list = rememberLazyListState()
    val app = LocalContext.current.applicationContext

    fun reloadCalendar() {
        calLoading = true
        scope.launch {
            val (cal, tr) = withContext(Dispatchers.IO) { ChatClient.news() }
            calendar = cal
            tren = tr
            calLoading = false
        }
    }
    LaunchedEffect(Unit) { reloadCalendar() }

    fun send(text: String) {
        val q = text.trim()
        if (q.isEmpty() || busy) return
        input = ""
        busy = true
        SignalRepository.addChat(ChatMessage("user", q))
        scope.launch {
            val reply = withContext(Dispatchers.IO) {
                SignalPoller.poll(app)       // sinyal & harga terbaru untuk blok rekomendasi entry
                val r = ChatClient.ask(SignalRepository.chat.value.filter { !it.text.startsWith("⚠️") })
                if (r.text.startsWith("⚠️")) r else r.copy(
                    text = entryAdvice(SignalRepository.events.value, SignalRepository.prices.value,
                        SignalRepository.money(), SignalRepository.followed()) + "\n\n" + r.text
                )
            }
            SignalRepository.addChat(reply)
            busy = false
        }
    }

    LaunchedEffect(messages.size, busy) {
        val last = messages.size + (if (busy) 1 else 0)
        if (last > 0) list.animateScrollToItem(last)
    }

    Column(Modifier.fillMaxSize().padding(horizontal = 12.dp)) {
        LazyColumn(
            state = list,
            modifier = Modifier.weight(1f).fillMaxWidth(),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            item {
                Column(Modifier.padding(top = 12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    if (SignalRepository.cloudUrl().isBlank()) {
                        NoteBox("Isi \"Alamat cloud\" di Pengaturan (alamat Vercel yang sama dengan cron).", SellColor)
                    }
                    AppCard {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            CardTitle("📅 Kalender ekonomi minggu ini (USD, WIB)", Modifier.weight(1f))
                            TextButton(onClick = { reloadCalendar() }, enabled = !calLoading) { Text("↻") }
                        }
                        when {
                            calLoading -> Text("Memuat kalender…", color = Muted)
                            calendar.isEmpty() -> Text("Kalender belum termuat. Cek Alamat cloud, lalu tekan ↻.",
                                color = Muted)
                            else -> calendar.forEach { e ->
                                NewsRow(e) {
                                    if (e.actual.isNotBlank()) {
                                        send("${e.title} Act: ${e.actual}" +
                                            (if (e.forecast.isNotBlank()) " Cons: ${e.forecast}" else "") +
                                            (if (e.previous.isNotBlank()) " Prev: ${e.previous}" else ""))
                                    } else {
                                        prefill = e
                                        showForm = true
                                    }
                                }
                                LineDivider()
                            }
                        }
                        Text(
                            "Tanggal & jam menyesuaikan otomatis tiap pekan. Act terisi otomatis dari data resmi (FRED) " +
                                "beberapa menit s/d ±1 jam setelah rilis (NFP, CPI, PPI, Retail, PCE, Claims, GDP). " +
                                "Tekan berita → analisa peluang arah emas; bila Act belum ada, isi sendiri.",
                            style = MaterialTheme.typography.labelSmall, color = Muted
                        )
                    }
                    TrendCard(tren, calLoading)
                    NoteBox(
                        "Saran entry/TP/SL hanya dari sinyal 💰: trading berita sendiri (masuk setelah rilis) sudah " +
                            "diuji 36 cara di data 2012–2026 dan semuanya rugi. Analisa berita = peluang arah historis, " +
                            "bukan sinyal entry. Bukan jaminan profit; aplikasi tidak membuka order."
                    )
                    if (messages.isEmpty()) {
                        CardTitle("Contoh pertanyaan")
                        EXAMPLES.forEach { ex ->
                            AssistChip(onClick = { send(ex) }, label = { Text(ex) })
                        }
                    }
                }
            }
            items(messages) { m -> Bubble(m) }
            if (busy) {
                item {
                    Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.padding(8.dp)) {
                        CircularProgressIndicator(Modifier.padding(end = 10.dp).size(20.dp), color = Gold,
                            strokeWidth = 2.dp)
                        Text("Menghitung dari data…", color = Muted,
                            style = MaterialTheme.typography.bodySmall)
                    }
                }
            }
        }
        if (showForm) {
            key(prefill) { ReleaseForm(busy, calendar, prefill) { text -> showForm = false; prefill = null; send(text) } }
        }
        Row(
            Modifier.fillMaxWidth().padding(vertical = 8.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            TextButton(onClick = { prefill = null; showForm = !showForm }) { Text(if (showForm) "✖" else "📝") }
            if (messages.isNotEmpty()) {
                IconButton(onClick = { SignalRepository.clearChat() }, enabled = !busy) {
                    Icon(Icons.Filled.Delete, contentDescription = "Hapus percakapan", tint = Muted)
                }
            }
            OutlinedTextField(
                value = input, onValueChange = { input = it.take(1500) },
                placeholder = { Text("Tanya soal berita…") },
                modifier = Modifier.weight(1f), maxLines = 4,
            )
            IconButton(onClick = { send(input) }, enabled = !busy && input.isNotBlank()) {
                Icon(Icons.AutoMirrored.Filled.Send, contentDescription = "Kirim", tint = Gold)
            }
        }
    }
}

/**
 * Kartu isian data rilis seperti ForexFactory: Berita, Act, Cons, Prev. Cons & Prev terisi otomatis dari kalender
 * minggu ini. "+ Baris" menambah baris lain (mis. NFP + Unemployment Rate), "Analisa" mengirim semuanya ke chat.
 */
@Composable
private fun ReleaseForm(busy: Boolean, events: List<CalEvent>, initial: CalEvent?, onSend: (String) -> Unit) {
    var name by remember { mutableStateOf(initial?.title ?: "") }
    var act by remember { mutableStateOf(initial?.actual ?: "") }
    var cons by remember { mutableStateOf(initial?.forecast ?: "") }
    var prev by remember { mutableStateOf(initial?.previous ?: "") }
    var rows by remember { mutableStateOf<List<String>>(emptyList()) }

    fun line(): String? = if (name.isBlank() || act.isBlank()) null else
        "${name.trim()} Act: ${act.trim()}" + (if (cons.isNotBlank()) " Cons: ${cons.trim()}" else "") +
            (if (prev.isNotBlank()) " Prev: ${prev.trim()}" else "")

    AppCard {
        CardTitle("Isi data rilis (Act / Cons / Prev)")
        Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            if (events.isNotEmpty()) {
                events.forEach { e ->
                    AssistChip(onClick = { name = e.title; cons = e.forecast; prev = e.previous; act = e.actual },
                        label = { Text("${e.title} • ${e.whenText}") })
                }
            } else {
                DEFAULT_EVENTS.forEach { t -> AssistChip(onClick = { name = t }, label = { Text(t) }) }
            }
        }
        OutlinedTextField(value = name, onValueChange = { name = it }, label = { Text("Berita") }, singleLine = true,
            modifier = Modifier.fillMaxWidth())
        Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            OutlinedTextField(value = act, onValueChange = { act = it }, label = { Text("Act") }, singleLine = true,
                modifier = Modifier.weight(1f))
            OutlinedTextField(value = cons, onValueChange = { cons = it }, label = { Text("Cons") }, singleLine = true,
                modifier = Modifier.weight(1f))
            OutlinedTextField(value = prev, onValueChange = { prev = it }, label = { Text("Prev") }, singleLine = true,
                modifier = Modifier.weight(1f))
        }
        rows.forEach { Text("• $it", style = MaterialTheme.typography.labelSmall, color = Muted) }
        Row(verticalAlignment = Alignment.CenterVertically) {
            TextButton(onClick = { line()?.let { rows = rows + it; act = ""; cons = ""; prev = ""; name = "" } },
                enabled = line() != null) { Text("+ Baris") }
            Spacer(Modifier.weight(1f))
            Button(
                onClick = { onSend((rows + listOfNotNull(line())).joinToString("\n")) },
                enabled = !busy && (rows.isNotEmpty() || line() != null)
            ) { Text("Analisa") }
        }
    }
}

@Composable
private fun Bubble(m: ChatMessage) {
    val mine = m.role == "user"
    Box(Modifier.fillMaxWidth(), contentAlignment = if (mine) Alignment.CenterEnd else Alignment.CenterStart) {
        Column(
            Modifier
                .widthIn(max = 340.dp)
                .background(if (mine) Gold.copy(alpha = 0.18f) else CardColor, RoundedCornerShape(14.dp))
                .padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            SelectionContainer {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    m.text.split("\n\n").forEach { part ->
                        if (!mine && part.startsWith("🎯")) EntryBox(part) else ReplyText(part, mine)
                    }
                }
            }
            if (m.sources.isNotEmpty()) {
                Text("Sumber:", style = MaterialTheme.typography.labelSmall, color = Muted)
                m.sources.take(5).forEach { s ->
                    SelectionContainer {
                        Text(s, style = MaterialTheme.typography.labelSmall, color = Muted, maxLines = 2,
                            modifier = Modifier.horizontalScroll(rememberScrollState()))
                    }
                }
            }
        }
    }
}

/** Blok 🎯 REKOMENDASI ENTRY: judul & arah besar, data utama tebal, status berwarna. */
@Composable
private fun EntryBox(text: String) {
    Column(
        Modifier
            .fillMaxWidth()
            .background(Gold.copy(alpha = 0.14f), RoundedCornerShape(10.dp))
            .padding(10.dp),
        verticalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        text.lines().forEach { line ->
            val body = line.removePrefix("▶").trim()
            when {
                line.startsWith("🎯") -> Text(line, style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.ExtraBold, color = Gold)
                line.startsWith("▶ BUY") || line.startsWith("▶ SELL") -> Text(body,
                    style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.ExtraBold,
                    color = if (body.startsWith("BUY")) BuyColor else SellColor)
                line.startsWith("▶") -> Text(body, style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold)
                line.startsWith("✅") -> Text(line, style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.Bold, color = BuyColor)
                line.startsWith("⚠️") || line.startsWith("⏳") -> Text(line,
                    style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.Bold, color = SellColor)
                else -> Text(line, style = MaterialTheme.typography.bodySmall, color = Muted)
            }
        }
    }
}

/** Teks jawaban; baris kesimpulan dibuat tebal & lebih besar. */
@Composable
private fun ReplyText(text: String, mine: Boolean) {
    Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
        text.lines().forEach { line ->
            val key = !mine && (line.startsWith("Kesimpulan") || line.startsWith("• KEJUTAN") ||
                line.startsWith("Saran berbasis data"))
            if (key) {
                Text(line, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold, color = Gold)
            } else {
                Text(line, style = MaterialTheme.typography.bodyMedium)
            }
        }
    }
}
