package com.xausignal.app

import androidx.compose.foundation.background
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
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
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

/** Berita minggu ini dari cloud (GET /api/chat) untuk mengisi Cons & Prev otomatis. */
data class CalEvent(val title: String, val whenText: String, val forecast: String, val previous: String)

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

    fun calendar(): List<CalEvent> {
        val base = SignalRepository.cloudUrl()
        if (base.isBlank()) return emptyList()
        val request = Request.Builder().url("$base/api/chat").get()
            .header("X-Chat-Key", SignalRepository.topic()).build()
        return try {
            client.newCall(request).execute().use { res ->
                val arr = JSONObject(res.body?.string().orEmpty()).optJSONArray("calendar") ?: JSONArray()
                (0 until arr.length()).map { i ->
                    val o = arr.getJSONObject(i)
                    CalEvent(o.optString("title"), o.optString("when"), o.optString("forecast"), o.optString("previous"))
                }
            }
        } catch (e: Exception) {
            emptyList()
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

@Composable
fun ChatTab() {
    val messages by SignalRepository.chat.collectAsState()
    var input by remember { mutableStateOf("") }
    var busy by remember { mutableStateOf(false) }
    var showForm by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()
    val list = rememberLazyListState()

    fun send(text: String) {
        val q = text.trim()
        if (q.isEmpty() || busy) return
        input = ""
        busy = true
        SignalRepository.addChat(ChatMessage("user", q))
        scope.launch {
            val reply = withContext(Dispatchers.IO) {
                ChatClient.ask(SignalRepository.chat.value.filter { !it.text.startsWith("⚠️") })
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
                    NoteBox(
                        "Tanya soal berita (NFP, CPI, FOMC, …), sinyal terbuka, atau skema SL+/TP. Jawaban dihitung " +
                            "dari data historis 2012–2026 (bukan AI). Setelah berita keluar, tekan 📝 Act/Cons/Prev " +
                            "lalu isi angkanya (Cons & Prev terisi otomatis dari kalender), atau ketik mis. " +
                            "\"NFP Act: 45K Cons: 98K Prev: 162K\". Bukan jaminan profit; chat tidak membuka order."
                    )
                    if (SignalRepository.cloudUrl().isBlank()) {
                        NoteBox("Isi \"Alamat cloud\" di Pengaturan (alamat Vercel yang sama dengan cron).", SellColor)
                    }
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
        if (showForm) ReleaseForm(busy) { text -> showForm = false; send(text) }
        Row(
            Modifier.fillMaxWidth().padding(vertical = 8.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            TextButton(onClick = { showForm = !showForm }) { Text(if (showForm) "✖" else "📝") }
            if (messages.isNotEmpty()) {
                IconButton(onClick = { SignalRepository.clearChat() }, enabled = !busy) {
                    Icon(Icons.Filled.Delete, contentDescription = "Hapus percakapan", tint = Muted)
                }
            }
            OutlinedTextField(
                value = input, onValueChange = { input = it.take(1500) },
                placeholder = { Text("Tulis pertanyaan…") },
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
private fun ReleaseForm(busy: Boolean, onSend: (String) -> Unit) {
    var events by remember { mutableStateOf<List<CalEvent>>(emptyList()) }
    var name by remember { mutableStateOf("") }
    var act by remember { mutableStateOf("") }
    var cons by remember { mutableStateOf("") }
    var prev by remember { mutableStateOf("") }
    var rows by remember { mutableStateOf<List<String>>(emptyList()) }
    LaunchedEffect(Unit) { events = withContext(Dispatchers.IO) { ChatClient.calendar() } }

    fun line(): String? = if (name.isBlank() || act.isBlank()) null else
        "${name.trim()} Act: ${act.trim()}" + (if (cons.isNotBlank()) " Cons: ${cons.trim()}" else "") +
            (if (prev.isNotBlank()) " Prev: ${prev.trim()}" else "")

    AppCard {
        CardTitle("Isi data rilis (Act / Cons / Prev)")
        Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            if (events.isNotEmpty()) {
                events.forEach { e ->
                    AssistChip(onClick = { name = e.title; cons = e.forecast; prev = e.previous; act = "" },
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
            SelectionContainer { Text(m.text, style = MaterialTheme.typography.bodyMedium) }
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
