"""🎯 Persiapan berita (GET /api/chat -> "persiapan"): pengganti chip "Contoh pertanyaan" di tab Tanya.

Permintaan pengguna 30 Sep 2026: kumpulkan data untuk bersiap menghadapi berita dan simpulkan dalam persen.
Persen dari cloud/api/persiapan.json (research/news_prediksi.py, kalender ForexFactory 2010–2026 + XAU M15):
peluang hasil di bawah / sesuai / di atas konsensus, % emas naik 1 jam per hasil, % emas naik 1 jam bila hasil
belum diketahui (= tebakan sebelum rilis), dan petunjuk sebelum rilis yang sudah diuji. Ditambah ⏱️ detik pertama
setelah rilis (cloud/api/detik.json dari research/news_detik.py, data tick): besar gerak & spread di detik awal dan
hasil entry "ikut lonjakan" / pending Buy-Sell Stop; teks "alarm" dipakai pengingat 1 menit sebelum rilis di aplikasi.
INFORMASI saja: tidak membuka order dan tidak mengubah sinyal. Hanya library standar Python.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

STATS = json.loads((Path(__file__).resolve().parent / "persiapan.json").read_text(encoding="utf-8"))
# ⏱️ detik pertama setelah rilis (research/news_detik.py, data tick): per aset -> per grup berita -> teks & angka
_DETIK_PATH = Path(__file__).resolve().parent / "detik.json"
DETIK = json.loads(_DETIK_PATH.read_text(encoding="utf-8")) if _DETIK_PATH.exists() else {}
# judul -> grup (dicek berurutan). ADP rilis terpisah (Rabu) -> bukan NFP; UR & AHE rilis bersamaan dengan NFP.
GROUP = [("ADP", None), ("Non-Farm", "NFP"), ("Unemployment Rate", "NFP"), ("Average Hourly Earnings", "NFP"),
         ("CPI", "CPI"), ("PPI", "PPI"), ("Federal Funds", "FOMC"), ("FOMC", "FOMC"), ("Retail Sales", "RETAIL"),
         ("PCE", "PCE"), ("GDP", "GDP"), ("ISM", "ISM"), ("Unemployment Claims", "CLAIMS")]
WIB = timedelta(hours=7)
HARI = ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"]
BULAN = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
KEEP_AFTER = timedelta(hours=6)       # berita yang baru lewat masih ditampilkan sebentar
IMPAS = 0.5                           # |rata $/0,01 lot| < ini (sudah termasuk slippage $0,30) = ≈ impas
EDGE = 10                             # |% naik - 50| minimal (di semua data DAN 5 tahun) agar disebut "condong"


def _when(t: datetime) -> str:
    w = t + WIB
    return f"{HARI[w.weekday()]} {w.day:02d} {BULAN[w.month - 1]} {w:%H:%M} WIB"


def _pct(x) -> str:
    return "-" if x is None else f"{x:.0f}%"


def lean(naik: int | None, baru: int | None) -> str:
    """Label tebakan arah emas 1 jam sebelum rilis."""
    if naik is None or baru is None:
        return "data kurang"
    if naik - 50 >= EDGE and baru - 50 >= EDGE:
        return "condong naik"
    if 50 - naik >= EDGE and 50 - baru >= EDGE:
        return "condong turun"
    return "≈ lempar koin"


def _clue_text(c: dict) -> str:
    mark = "✅ terbukti" if c["terbukti"] else "❌ tidak terbukti"
    txt = (f"{c['nama']}: arah benar {c['benar']:.0f}% (lama {_pct(c['lama'])} / 5 th {_pct(c['baru'])}, n={c['n']}) "
           f"{mark}")
    if c.get("emas_naik1j"):
        lo, hi = c["emas_naik1j"]
        txt += f"; emas naik 1 jam tetap {lo}%" + (f"–{hi}%" if hi != lo else "")
    return txt


def group_of(title: str) -> str | None:
    return next((g for key, g in GROUP if key in (title or "")), None)


def detik(group: str | None, field: str = "teks") -> str:
    """Teks detik pertama XAU (+ BTC) untuk grup berita; grup tanpa cukup data memakai ringkasan SEMUA."""
    parts = []
    for aset in ("XAU", "BTC"):
        d = DETIK.get(f"{aset}_EXNESS") or DETIK.get(aset) or {}       # utamakan tick asli broker (Exness)
        row = d.get(group or "") or d.get("SEMUA")
        if row and row.get(field):
            parts.append(row[field])
    return " ".join(parts)


def _usd(x: float) -> str:
    return f"{'+' if x >= 0 else '−'}${abs(x):.2f}".replace(".", ",")


def detik_ringkas(group: str | None) -> dict | None:
    """Pending Buy/Sell Stop ±$1 XAU (tick Exness) untuk berita ini: satu angka besar + bukti singkat.
    Rata-rata sudah termasuk slippage $0,30. "% untung" = persen rilis yang ditutup untung."""
    row = (DETIK.get("XAU_EXNESS") or {}).get(group or "") or {}
    p1 = row.get("pending1") or {}
    n = p1.get("n") or 0
    if n < 30:
        return None
    avg, wr = p1["avg"], p1["wr"]
    bukti = f"teruji {row.get('tahun', '')} ({n} rilis, tick Exness)"
    if avg >= IMPAS:
        teks = f"{wr:.0f}% untung ⚠️"
        x = p1.get("x")
        bukti += f" • rata {_usd(avg)}/0,01 lot • " + (
            f"feed {p1.get('x_feed', 'lain')} {_usd(x)} → belum terbukti" if x is not None and x <= 0
            else "belum diuji maju → belum terbukti")
    elif avg > -IMPAS:
        teks = "≈ impas ⚪"
        bukti += f" • rata {_usd(avg)}/0,01 lot (untung {wr:.0f}% rilis)"
    else:
        teks = "RUGI 🔴"
        bukti += f" • rata {_usd(avg)}/0,01 lot walau untung di {wr:.0f}% rilis (rugi saat kalah lebih besar)"
    return {"judul": "⏱️ Pending ±$1 detik pertama", "teks": teks, "bukti": bukti}


def detik_singkat(group: str | None) -> str:
    """Satu baris untuk notifikasi ⏱️: "Pending ±$1: 77% untung ⚠️ • teruji 2015–2026 (130 rilis …) …"."""
    d = detik_ringkas(group)
    return "" if d is None else f"Pending ±$1: {d['teks']} • {d['bukti']}"


def _num(text: str) -> float | None:
    import re
    m = re.match(r"^\s*([<>]?)(-?\d+(?:[.,]\d+)?)\s*([kKmMbBtT%]?)", text or "")
    if not m:
        return None
    mult = {"k": 1e3, "m": 1e6, "b": 1e9, "t": 1e12}.get(m.group(3).lower(), 1.0)
    return float(m.group(2).replace(",", ".")) * mult


LABEL_HASIL = {"bawah": "Data < perkiraan", "atas": "Data > perkiraan", "sesuai": "Data = perkiraan"}


def arah_emas(e: dict | None) -> dict | None:
    """Reaksi emas 1 jam untuk satu hasil (bawah/atas/sesuai) -> angka besar "75% NAIK 🟢" + bukti singkat.
    Kuat hanya bila >= 60% di semua data DAN arah yang sama >= 55% sejak Okt 2021 (konsisten lama & baru)."""
    if not e or e.get("naik1j") is None:
        return None
    naik, baru, n = int(e["naik1j"]), e.get("baru_naik1j"), int(e.get("n") or 0)
    up = naik >= 50
    pct = naik if up else 100 - naik
    pct_baru = None if baru is None else (baru if up else 100 - baru)
    kata = "naik" if up else "turun"
    bukti = f"teruji {e.get('tahun') or '2012–2025'} ({n} rilis)"
    if pct_baru is not None:
        bukti += f" • sejak Okt 2021: {pct_baru}% {kata}"
    kuat = pct >= 60 and (pct_baru is None or pct_baru >= 55)
    if kuat:
        teks = f"{pct}% NAIK 🟢" if up else f"{pct}% TURUN 🔴"
    else:                                         # angka tetap ditampilkan, tapi abu-abu & diberi label
        teks = f"{pct}% {kata} ⚪"
        bukti = ("tidak konsisten" if pct >= 60 else "lemah" if pct >= 55 else "≈ lempar koin") + " • " + bukti
    return {"arah": kata, "persen": pct, "n": n, "kuat": kuat, "teks": teks, "bukti": bukti}


def skenario(title: str) -> list[dict]:
    """Sebelum rilis: arah emas 1 jam bila data di bawah / di atas perkiraan (atau = perkiraan bila hanya itu)."""
    emas = (STATS["dasar"].get(title) or {}).get("emas") or {}
    keys = [k for k in ("bawah", "atas") if k in emas] or [k for k in ("sesuai",) if k in emas]
    out = []
    for k in keys:
        a = arah_emas(emas[k])
        if a:
            out.append({"hasil": k, "label": LABEL_HASIL[k], **a})
    return out


def kesimpulan(title: str, actual: str, forecast: str) -> dict | None:
    """Setelah Act keluar: arah emas 1 jam dari data historis untuk hasil itu (Act dibanding Cons)."""
    st = STATS["dasar"].get(title)
    a, f = _num(actual), _num(forecast)
    if not st or a is None or f is None:
        return None
    hasil = "atas" if a > f else "bawah" if a < f else "sesuai"
    r = arah_emas((st.get("emas") or {}).get(hasil))
    if not r:
        return None
    return {"hasil": hasil, **r,
            "catatan": f"{LABEL_HASIL[hasil].replace('Data', 'Act')} → emas 1 jam • {r['bukti']}"}


def alarm_texts() -> dict:
    """{grup: {"alarm": teks}} untuk pengingat ⏱️ 1 menit sebelum rilis di aplikasi (NewsAlarm)."""
    groups = {g for _, g in GROUP if g} | {"SEMUA"}
    return {g: {"alarm": detik_singkat(g) or detik(g, "alarm")} for g in sorted(groups)
            if detik_singkat(g) or detik(g, "alarm")}


def card(title: str, t: datetime, forecast: str, previous: str, now: datetime) -> dict | None:
    st = STATS["dasar"].get(title)
    if not st:
        return None
    semua, baru = st["semua"], st["baru"]
    emas = st.get("emas", {})
    sebelum = st.get("emas_sebelum", {})
    return {
        "title": title, "time": t.isoformat(), "when": _when(t), "released": now >= t,
        "forecast": forecast or "", "previous": previous or "",
        "hasil": {k: semua[k] for k in ("bawah", "sesuai", "atas")}, "n": semua["n"],
        "hasil_baru": {k: baru[k] for k in ("bawah", "sesuai", "atas")}, "n_baru": baru["n"],
        "emas_jika": {k: v["naik1j"] for k, v in emas.items()},
        "emas_sebelum": sebelum.get("naik1j"), "emas_sebelum_baru": sebelum.get("baru_naik1j"),
        "arah": lean(sebelum.get("naik1j"), sebelum.get("baru_naik1j")),
        "kebalikan": bool(st.get("kebalikan")),
        "petunjuk": [_clue_text(c) for c in st.get("petunjuk", [])],
        "detik": detik(group_of(title)),
        "detik_singkat": detik_singkat(group_of(title)),
        # tampilan singkat aplikasi 3.15: angka besar + bukti (teruji tahun..tahun, jumlah rilis)
        "skenario": skenario(title),
        "detik_ringkas": detik_ringkas(group_of(title)),
    }


def cards(calendar_rows: list | None, now: datetime | None = None) -> dict:
    """Kartu per berita USD (dampak tinggi/sedang) pekan ini yang punya statistik, urut waktu."""
    now = now or datetime.now(timezone.utc)
    out = []
    for r in calendar_rows or []:
        if r.get("country") != "USD" or r.get("impact") not in ("High", "Medium"):
            continue
        try:
            t = datetime.fromisoformat(r["date"]).astimezone(timezone.utc)
        except (KeyError, ValueError, TypeError):
            continue
        if t < now - KEEP_AFTER:
            continue
        c = card(r.get("title") or "", t, r.get("forecast") or "", r.get("previous") or "", now)
        if c:
            out.append(c)
    out.sort(key=lambda c: c["time"])
    return {"periode": STATS.get("periode"), "kesimpulan": STATS.get("kesimpulan"), "berita": out,
            "detik": alarm_texts()}
