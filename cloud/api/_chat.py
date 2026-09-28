"""Chat asisten riset untuk aplikasi (POST /api/chat): Claude API + basis pengetahuan statistik + konteks langsung.

- Basis pengetahuan: pengetahuan.md (dibuat research/event_stats.py dari data 2012-2026), dimasukkan ke system
  prompt dan di-cache (prompt caching) karena sama untuk setiap pertanyaan.
- Konteks langsung (tidak di-cache): waktu sekarang, kalender berita USD high-impact minggu ini (ForexFactory),
  harga & posisi virtual sinyal XAU/BTC terakhir dari Supabase.
- Web search (server tool Anthropic) untuk angka berita yang baru keluar, peluang CME FedWatch, dll.
Chat hanya memberi informasi; tidak membuka/menutup order.
"""
from __future__ import annotations

import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

MODEL = "claude-opus-5"
KNOWLEDGE = (Path(__file__).resolve().parent / "pengetahuan.md").read_text(encoding="utf-8")
MAX_TURNS = 12              # riwayat yang dikirim dari aplikasi (pesan terakhir)
MAX_CHARS = 2000            # per pesan
CALENDAR_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"

RULES = """Kamu asisten riset di aplikasi sinyal trading "Dividend Indicator" (XAU/USD, BTC/USD, gap pekan forex).
Pengguna orang Indonesia; jawab dalam bahasa Indonesia yang sederhana, ringkas, dan praktis.

Aturan wajib:
1. Setiap peluang/persentase harus berasal dari BASIS PENGETAHUAN di bawah (sebut n dan periodenya) atau dari hasil
   web search terbaru (sebut sumbernya). Jangan mengarang angka. Bila datanya tidak ada, katakan terus terang.
2. Nyatakan peluang sebagai frekuensi historis ("dari 67 rilis NFP yang lebih lemah dari perkiraan, emas naik dalam
   1 jam pada 73%"), bukan kepastian. Sampel kecil (n < 20) harus disebut lemah.
3. Jangan pernah menjanjikan profit atau WR tinggi. Ingatkan: spread melebar dan slippage saat berita; setelah
   candle 15 menit pertama tutup, arah berikutnya secara historis ≈ 50/50, jadi mengejar lonjakan berita bukan edge.
4. Manajemen risiko: selalu pakai SL; risiko 0,25-0,5% modal per sinyal; jangan menambah lot untuk menutup rugi,
   jangan martingale/grid. Boleh menyarankan TIDAK trading bila tidak ada keunggulan.
5. Untuk berita yang sudah keluar: cari angka actual vs forecast (web search, utamakan sumber resmi: bls.gov,
   bea.gov, federalreserve.gov, atau kantor berita besar), tentukan arah & besar kejutan dari sisi emas, lalu beri
   statistik reaksi dari basis pengetahuan dan kaitkan dengan sinyal/posisi bot yang sedang terbuka.
6. Untuk FOMC: keputusan yang sesuai ekspektasi (mis. peluang CME FedWatch tinggi) biasanya sudah tercermin di harga;
   kejutan suku bunga sangat jarang. Cari peluang FedWatch/konsensus terbaru bila ditanya, jelaskan skenario
   (sesuai ekspektasi / lebih hawkish / lebih dovish) dengan statistik yang ada.
7. Kamu tidak bisa membuka/menutup order. Sinyal bot tetap mengikuti aturannya sendiri.
8. Format: paragraf pendek atau poin; akhiri dengan baris "Peluang (historis): ..." bila relevan dan baris
   "Sumber: ..." untuk data web. Tanpa tabel lebar (layar HP)."""


def system_blocks() -> list[dict]:
    """System prompt stabil (di-cache): aturan + basis pengetahuan. Jangan taruh data yang berubah di sini."""
    return [{"type": "text", "text": RULES},
            {"type": "text", "text": "BASIS PENGETAHUAN\n\n" + KNOWLEDGE, "cache_control": {"type": "ephemeral"}}]


def _get_json(url: str, timeout: int = 8):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def calendar_text(rows: list[dict] | None) -> str:
    if not rows:
        return "Kalender minggu ini: tidak tersedia."
    out = []
    for r in rows:
        if r.get("country") != "USD" or r.get("impact") != "High":
            continue
        try:
            t = datetime.fromisoformat(r["date"]).astimezone(timezone.utc)
        except (KeyError, ValueError):
            continue
        out.append(f"- {t:%a %d %b %H:%M} UTC: {r.get('title')} (forecast {r.get('forecast') or '-'}, "
                   f"sebelumnya {r.get('previous') or '-'})")
    return "Berita USD high-impact minggu ini (ForexFactory):\n" + ("\n".join(out) if out else "- tidak ada")


def bot_text(states: dict[str, dict]) -> str:
    lines = []
    for asset, st in states.items():
        if not st:
            continue
        lines.append(f"{asset}: harga terakhir {st.get('price')}, tick {st.get('last_tick')}")
        for name, s in sorted((st.get("systems") or {}).items()):
            v = s.get("virtual")
            if v:
                lines.append(f"  - posisi terbuka {name}: {v.get('dir')} entry {round(float(v.get('entry', 0)), 2)}, "
                             f"SL {round(float(v.get('sl', 0)), 2)}, TP1 {round(float(v.get('tp1', 0)), 2)}, "
                             f"kategori {v.get('cat', '-')}, TP1 kena {bool(v.get('tp1_hit'))}")
            else:
                lines.append(f"  - {name}: tidak ada posisi (tren {s.get('trend', '-')})")
    return "Status bot (Supabase):\n" + ("\n".join(lines) if lines else "- tidak tersedia")


def filter_text(funding_cache: dict | None, now: datetime) -> str:
    """Status filter BTC 💰 yang terpasang (funding ramai & September)."""
    import _core
    import _funding
    pct = _funding.percentile_last([v for _, v in (funding_cache or {}).get("f") or []])
    lines = [f"Filter BTC 💰: funding Binance 24 jam persentil "
             f"{'-' if pct is None else f'{pct:.0%}'} (1 tahun, data s/d {(funding_cache or {}).get('day', '-')}); "
             "BUY dilewati bila ≥90%, SELL bila ≤10%."]
    if _core.new_york(now).month == 9:
        lines.append("Sekarang September: sinyal BTC 💰 dilewati (11/11 tahun rugi).")
    return "\n".join(lines)


def live_context(now: datetime, calendar_rows, states: dict[str, dict], funding_cache: dict | None = None) -> str:
    return (f"KONTEKS LANGSUNG dari server (bukan dari pengguna), {now:%Y-%m-%d %H:%M} UTC:\n"
            f"{calendar_text(calendar_rows)}\n{bot_text(states)}\n{filter_text(funding_cache, now)}")


def clean_history(messages: list) -> list[dict]:
    """Riwayat dari aplikasi -> format Messages API (user/assistant bergantian, diawali user, diakhiri user)."""
    out: list[dict] = []
    for m in (messages or [])[-MAX_TURNS:]:
        role = m.get("role") if isinstance(m, dict) else None
        text = str(m.get("content", ""))[:MAX_CHARS].strip() if role else ""
        if role not in ("user", "assistant") or not text:
            continue
        if out and out[-1]["role"] == role:
            out[-1]["content"] += "\n\n" + text
        else:
            out.append({"role": role, "content": text})
    while out and out[0]["role"] != "user":
        out.pop(0)
    if not out or out[-1]["role"] != "user":
        raise ValueError("pesan terakhir harus dari pengguna")
    return out


def ask(client, messages: list, context: str, model: str = MODEL, max_continue: int = 3) -> dict:
    """Satu jawaban. `client` = anthropic.Anthropic() (atau tiruan di tes)."""
    msgs = clean_history(messages)
    last = msgs[-1]["content"]
    msgs[-1] = {"role": "user", "content": [{"type": "text", "text": context},
                                            {"type": "text", "text": "Pertanyaan pengguna:\n" + last}]}
    params = dict(
        model=model, max_tokens=8000, system=system_blocks(), betas=["server-side-fallback-2026-07-01"],
        fallbacks="default", thinking={"type": "adaptive"}, output_config={"effort": "low"},
        tools=[{"type": "web_search_20260209", "name": "web_search", "max_uses": 3}],
    )
    convo = list(msgs)
    resp = client.beta.messages.create(messages=convo, **params)
    for _ in range(max_continue):                     # server tool (web search) bisa berhenti sementara
        if resp.stop_reason != "pause_turn":
            break
        convo = msgs + [{"role": "assistant", "content": resp.content}]
        resp = client.beta.messages.create(messages=convo, **params)
    if resp.stop_reason == "refusal":
        return {"ok": True, "reply": "Maaf, pertanyaan ini tidak bisa saya jawab. Coba ubah pertanyaannya.",
                "sources": [], "model": getattr(resp, "model", model)}
    texts, sources, seen = [], [], set()
    for block in resp.content:
        if getattr(block, "type", None) != "text":
            continue
        texts.append(block.text)
        for c in getattr(block, "citations", None) or []:
            url = getattr(c, "url", None)
            if url and url not in seen:
                seen.add(url)
                sources.append({"title": getattr(c, "title", None) or url, "url": url})
    reply = "".join(texts).strip() or "Maaf, belum ada jawaban. Coba lagi."
    if resp.stop_reason == "max_tokens":
        reply += "\n\n(jawaban terpotong)"
    return {"ok": True, "reply": reply, "sources": sources, "model": getattr(resp, "model", model)}


def fetch_calendar() -> list | None:
    try:
        return _get_json(CALENDAR_URL)
    except Exception:  # noqa: BLE001 - kalender opsional
        return None
