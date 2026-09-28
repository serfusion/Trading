package com.xausignal.app

import androidx.compose.foundation.background
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
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
    "Hasil NFP sudah keluar, apa artinya untuk emas?",
    "Sebelum FOMC pasar memperkirakan suku bunga naik. Apa yang sebaiknya saya lakukan?",
    "Berita besar apa saja minggu ini dan kapan saya sebaiknya hati-hati?",
    "Jelaskan sinyal yang sedang terbuka sekarang.",
)

/** Klien POST <alamat cloud>/api/chat. Kunci = topik ntfy (sama dengan cloud). */
object ChatClient {
    private val client = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(75, TimeUnit.SECONDS)      // fungsi cloud maksimal 60 detik
        .callTimeout(80, TimeUnit.SECONDS)
        .build()

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
                        "Tanya soal berita (NFP, CPI, FOMC), sinyal yang terbuka, atau risiko. Jawaban memakai " +
                            "statistik historis 2012–2026 + berita terbaru dari web. Bukan jaminan profit; " +
                            "chat tidak membuka order."
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
                        Text("Menganalisa data & berita… (bisa sampai 1 menit)", color = Muted,
                            style = MaterialTheme.typography.bodySmall)
                    }
                }
            }
        }
        Row(
            Modifier.fillMaxWidth().padding(vertical = 8.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
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
