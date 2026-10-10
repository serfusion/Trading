"""🗣️ Pernyataan & berita penting terbaru (Fed, Trump/Gedung Putih, pemerintah AS, negara lain) untuk kartu 🎯.

Permintaan pengguna 10 Okt 2026: "perhatikan statement pemimpin penting atau negara yang bisa mengubah chance".
Sumber (dibaca dari Vercel, cache Supabase baris "pernyataan" 10 menit, tiap sumber boleh gagal):
  1. RSS resmi The Fed: siaran pers & pidato (federalreserve.gov/feeds/press_all.xml, speeches.xml)
  2. Google News RSS: judul berita 24 jam terakhir tentang Trump / Gedung Putih / Menkeu AS / Iran / China / OPEC /
     tarif / sanksi / perang + emas / bitcoin / inflasi / suku bunga.
Arah harga TIDAK ditebak dari kata-kata (tanpa AI, keputusan pengguna 28 Sep 2026; kata yang sama bisa menaikkan atau
menurunkan emas — mis. ancaman ke Iran 2026 menaikkan minyak → inflasi → Fed naik → emas turun). Yang dipakai untuk
angka peluang adalah pasar prediksi (_hari_h.py, bereaksi dalam menit), dan untuk sinyal adalah guncangan harga
(_batal.py). Daftar ini menjelaskan "kenapa". INFORMASI saja. Hanya library standar Python.
"""
from __future__ import annotations

import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

TTL = timedelta(minutes=10)
UMUR = timedelta(hours=24)            # judul berita lebih tua dari ini dibuang
UMUR_FED = timedelta(hours=72)        # pidato / siaran pers resmi Fed: 3 hari
MAKS = 6
WIB = timedelta(hours=7)
FED = ("https://www.federalreserve.gov/feeds/press_all.xml", "https://www.federalreserve.gov/feeds/speeches.xml")
GNEWS = "https://news.google.com/rss/search?"
# kueri sederhana + when:1d (kueri OR panjang membuat Google mengabaikan batas waktu — dicek 10 Okt 2026)
QUERIES = ("Trump tariff OR Iran OR Fed OR sanctions OR China when:1d",
           "Federal Reserve OR Warsh inflation OR rate when:1d",
           "Iran OR China OR OPEC OR Russia oil OR war OR sanctions when:1d",
           "gold OR bitcoin plunge OR crash OR surge when:1d")
BERITA_FED = ("CPI m/m", "Core CPI m/m", "Federal Funds Rate", "Non-Farm Employment Change", "Core PCE Price Index m/m",
              "PPI m/m", "JOLTS Job Openings", "Retail Sales m/m")
# siapa → label; urutan = prioritas tampilan
SIAPA = [("Trump", "Trump"), ("White House", "Gedung Putih"), ("Bessent", "Menkeu AS"), ("Treasury", "Menkeu AS"),
         ("Warsh", "Ketua Fed"), ("Powell", "Fed"), ("Jefferson", "Fed"), ("Waller", "Fed"), ("Bowman", "Fed"),
         ("Hammack", "Fed"), ("Barr", "Fed"), ("Logan", "Fed"), ("Goolsbee", "Fed"), ("Williams", "Fed"),
         ("Kashkari", "Fed"), ("Musalem", "Fed"), ("Daly", "Fed"), ("Bostic", "Fed"), ("Fed", "Fed"),
         ("Federal Reserve", "Fed"), ("Iran", "Iran"), ("China", "China"), ("Beijing", "China"), ("Russia", "Rusia"),
         ("OPEC", "OPEC"), ("Israel", "Israel"), ("SEC", "SEC")]
TOPIK = [(r"tariff", "tarif"), (r"sanction", "sanksi"), (r"attack|airstrike|missile|bomb", "serangan"),
         (r"\bwar\b|invasion", "perang"), (r"rate hikes?\b|hike rates|raise rates|tighten", "suku bunga naik"),
         (r"hawkish", "hawkish"), (r"rate cuts?\b|cut rates|lower rates|monetary easing", "suku bunga turun"), (r"dovish", "dovish"),
         (r"inflation|\bCPI\b|prices? surge", "inflasi"), (r"\boil\b|crude|diesel|gasoline|fuel", "minyak/BBM"),
         (r"crypto|bitcoin", "kripto"), (r"\bgold\b", "emas"), (r"ceasefire|truce|peace", "damai/gencatan"),
         (r"\bdeal\b|agreement", "kesepakatan"), (r"\bban\b|crackdown", "larangan"),
         (r"plunge|crash|tumble|sell-?off", "harga anjlok"), (r"surge|soar|rall(y|ies)", "harga melonjak")]
PENTING = ("Trump", "Ketua Fed", "Fed", "Menkeu AS", "Gedung Putih")


def _get(url: str, timeout: float = 5.0, opener=None) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (xau-signal)"})
    with (opener or urllib.request.urlopen)(req, timeout=timeout) as r:
        return r.read(2_000_000)


def _rss(raw: bytes) -> list[dict]:
    """Item RSS 2.0 → [{"judul", "link", "t"}] (t = datetime UTC; item tanpa tanggal dibuang)."""
    out = []
    root = ET.fromstring(raw)
    for it in root.iter("item"):
        title = (it.findtext("title") or "").strip()
        try:
            t = parsedate_to_datetime(it.findtext("pubDate") or "").astimezone(timezone.utc)
        except (TypeError, ValueError):
            continue
        if title:
            out.append({"judul": re.sub(r"\s+", " ", title)[:220], "link": (it.findtext("link") or "").strip(), "t": t,
                        "sumber": (it.findtext("source") or "").strip()})
    return out


def _cocok(text: str, daftar: list[tuple[str, str]], regex: bool = False) -> list[str]:
    seen = []
    for kata, label in daftar:
        pola = kata if regex else rf"\b{re.escape(kata)}"
        if re.search(pola, text, re.IGNORECASE) and label not in seen:
            seen.append(label)
    return seen


def kumpulkan(now: datetime, get=_get) -> tuple[list[dict], list[str]]:
    """(item terbaru, status per sumber). Item: judul, siapa, topik, untuk (judul kalender yang terkait), t, sumber."""
    items, status = [], []
    for url in FED:
        try:
            rows = _rss(get(url))
            for r in rows:
                r["sumber"] = "The Fed (resmi)"
                r["siapa"] = _cocok(r["judul"], SIAPA) or ["Fed"]
            if "speech" not in url:            # siaran pers: hanya kebijakan moneter / pernyataan FOMC / suku bunga
                rows = [r for r in rows if re.search(r"FOMC|monetary|rate|discount|statement|minutes", r["judul"], re.I)]
            items += rows
            status.append(f"{'pidato' if 'speech' in url else 'siaran pers'} Fed ✓")
        except Exception as exc:  # noqa: BLE001 - sumber opsional
            status.append(f"{'pidato' if 'speech' in url else 'siaran pers'} Fed gagal ({type(exc).__name__})")
    ok = 0
    for q in QUERIES:
        try:
            rows = _rss(get(GNEWS + urllib.parse.urlencode({"q": q, "hl": "en-US", "gl": "US", "ceid": "US:en"})))
            ok += 1
        except Exception:  # noqa: BLE001
            continue
        for r in rows:
            r["siapa"] = _cocok(r["judul"], SIAPA)
            r["sumber"] = "Google News"
        # judul berita harus menyebut SIAPA (Trump/Fed/negara) DAN topik pasar (tarif, perang, suku bunga, emas, kripto…)
        items += [r for r in rows if r["siapa"] and _cocok(r["judul"], TOPIK, True)]
    status.append("Google News ✓" if ok else "Google News gagal")
    items = [r for r in items if now - (UMUR_FED if r["sumber"] == "The Fed (resmi)" else UMUR) <= r["t"]
             <= now + timedelta(minutes=5)]
    seen, out = [], []
    # pernyataan orang penting (Trump, Fed, Menkeu, Gedung Putih) didahulukan, lalu yang terbaru
    for r in sorted(items, key=lambda r: (not any(x in PENTING for x in r["siapa"]), -r["t"].timestamp())):
        kata = {w for w in re.findall(r"[a-z]{4,}", r["judul"].lower().rsplit(" - ", 1)[0])}
        if any(len(kata & k) >= 0.5 * min(len(kata), len(k)) for k in seen if k):    # cerita sama, media lain
            continue
        seen.append(kata)
        r["topik"] = _cocok(r["judul"], TOPIK, True)
        fed = any(s in ("Fed", "Ketua Fed") for s in r["siapa"])
        r["untuk"] = list(BERITA_FED) if fed or r["topik"] else []
        out.append(r)
    return out, status


def _wib(t: datetime) -> str:
    w = t + WIB
    return f"{w.day:02d}/{w.month:02d} {w:%H:%M} WIB"


def ringkas(items: list[dict], now: datetime) -> list[dict]:
    """Bentuk tampilan: judul asli (Inggris) + "siapa • topik • kapan • sumber"."""
    out = []
    for r in items[:MAKS]:
        jam = (now - r["t"]).total_seconds() / 3600
        umur = f"{int(jam * 60)} mnt lalu" if jam < 1 else f"{jam:.0f} jam lalu"
        catatan = " • ".join(x for x in (", ".join(r["siapa"]), ", ".join(r.get("topik") or []), umur,
                                         _wib(r["t"]), r.get("sumber") or "") if x)
        out.append({"judul": r["judul"], "catatan": catatan, "link": r.get("link", ""), "untuk": r.get("untuk") or [],
                    "siapa": r["siapa"], "waktu": r["t"].isoformat()})
    return out


def attach(persiapan: dict, store, now: datetime, env: dict | None = None, get=_get) -> None:
    """persiapan["pernyataan"] = {"penting": [...], "status": "...", "waktu": "HH:MM WIB"} (env PERNYATAAN=0 mati)."""
    if not isinstance(persiapan, dict) or (env or {}).get("PERNYATAAN", "1") != "1":
        return
    old = {}
    if store is not None:
        try:
            old = store.get_state("pernyataan") or {}
        except Exception:  # noqa: BLE001
            old = {}
    if old.get("t") and now - datetime.fromisoformat(old["t"]) < TTL:
        items = [dict(r, t=datetime.fromisoformat(r["t"])) for r in old.get("items") or []]
        status, t = old.get("status") or [], datetime.fromisoformat(old["t"])
    else:
        items, status = kumpulkan(now, get)
        t = now
        if not items and old.get("items"):                 # semua sumber gagal → pakai daftar lama
            items = [dict(r, t=datetime.fromisoformat(r["t"])) for r in old["items"]]
        if store is not None:
            try:
                store.save_state({"t": now.isoformat(), "status": status,
                                  "items": [dict(r, t=r["t"].isoformat()) for r in items[:30]]}, "pernyataan")
            except Exception:  # noqa: BLE001
                pass
    items = [r for r in items if now - (UMUR_FED if r.get("sumber") == "The Fed (resmi)" else UMUR) <= r["t"]]
    persiapan["pernyataan"] = {"penting": ringkas(items, now), "status": " • ".join(status),
                               "waktu": f"{t + WIB:%H:%M} WIB",
                               "catatan": "Judul asli dari sumbernya. Arah harga tidak ditebak dari kata-kata: lihat "
                                          "🎲 peluang pasar (bereaksi dalam menit) dan 🛑 bila sinyal dibatalkan."}
