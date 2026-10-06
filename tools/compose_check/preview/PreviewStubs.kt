package com.xausignal.app

import org.json.JSONObject

// Hanya untuk pratinjau: pengganti ChatScreen.kt (tanpa jaringan; berita contoh dari PreviewData).
data class CalEvent(val title: String)

object ChatClient {
    fun news(): Triple<List<CalEvent>, JSONObject?, JSONObject?> = Triple(emptyList(), null, PreviewData.prep())
}

data class ChatMessage(val role: String, val text: String, val sources: List<String> = emptyList())
