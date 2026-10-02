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
# reaksi emas 1 MENIT per judul & hasil (research/reaksi_menit.py, tick) -> dipakai lebih dulu daripada 1 jam (STATS)
_REAKSI_PATH = Path(__file__).resolve().parent / "reaksi.json"
REAKSI = (json.loads(_REAKSI_PATH.read_text(encoding="utf-8")).get("judul") or {}) if _REAKSI_PATH.exists() else {}
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


MIN_GERAK = 0.30      # $/ons: gerak median lebih kecil dari ini (±1,5–2x spread Exness $0,16–0,20) = "belum gerak"
_KEY = {"sesuai": "sama"}


def tahap(title: str, hasil: str) -> list[dict]:
    """Arah emas 1, 2, 3 DETIK dan 1 MENIT setelah rilis untuk satu hasil (bawah / atas / sesuai).

    Permintaan pengguna 2 Okt 2026: "tuliskan hasilnya dan persentase akan ke mana setelah 1 detik news release".
    Dari tick (research/reaksi_menit.py): % naik dihitung dari rilis yang harganya sudah bergerak; "belum gerak" bila
    gerak median < MIN_GERAK (detik pertama NFP/CPI/PPI: ±$0,10–0,20 ≈ spread, arah ≈ 50:50). Kuat (hijau/merah)
    hanya bila >= 60% di Dukascopy, arah sama >= 55% di tick Exness dan sejak Okt 2021."""
    r = (REAKSI.get(title) or {}).get(_KEY.get(hasil, hasil)) or {}
    out = []
    for sec, x in sorted((r.get("cepat") or {}).items(), key=lambda kv: int(kv[0])):
        up = x["naik"] >= 0.5
        pct = int(round(100 * (x["naik"] if up else 1 - x["naik"])))
        kata = "naik" if up else "turun"

        def same(v):
            return v is None or (v if up else 1 - v) >= 0.55
        kuat = False
        if x["gerak"] < MIN_GERAK:
            teks, angka, kecil = "belum gerak ⚪", f"±${x['gerak']:.2f}".replace(".", ","), "belum gerak ⚪"
        elif pct < 55:
            teks, angka, kecil = "≈ 50:50 ⚪", "50:50", "acak ⚪"
        else:
            kuat = pct >= 60 and same(x.get("ex")) and same(x.get("baru"))
            teks = (f"{pct}% NAIK 🟢" if up else f"{pct}% TURUN 🔴") if kuat else f"{pct}% {kata} ⚪"
            angka, kecil = teks.split(" ", 1)
        ex = x.get("ex")
        # angka/kata: sel aplikasi 3.18 (angka besar di atas, kata kecil di bawah)
        out.append({"dtk": f"{sec} dtk", "teks": teks, "angka": angka, "kata": kecil, "kuat": kuat, "persen": pct,
                    "arah": kata,
                    "gerak": x["gerak"], "n": x["n"],
                    "exness": None if ex is None else int(round(100 * (ex if up else 1 - ex)))})
    if r.get("naik60") is not None:
        b = r.get("baru_naik60")
        a = arah_emas({"naik1j": round(r["naik60"] * 100), "n": r.get("n"),
                       "baru_naik1j": None if b is None else round(b * 100)})
        if a:
            out.append({"dtk": "1 mnt", "teks": a["teks"], "angka": a["teks"].split(" ", 1)[0],
                        "kata": a["teks"].split(" ", 1)[1], "kuat": a["kuat"], "persen": a["persen"],
                        "arah": a["arah"], "gerak": None, "n": a["n"], "exness": None})
    # 3 & 6 JAM (XAU M15; permintaan 2 Okt 2026 setelah NFP naik $40 lalu berbalik): angka "53–69%" bila semua tahun
    # dan sejak Okt 2021 beda >= 10 poin -> terlihat bahwa arah berita melemah seiring waktu
    for h, x in sorted((r.get("jam") or {}).items(), key=lambda kv: int(kv[0])):
        b = x.get("baru")
        a = arah_emas({"naik1j": round(x["naik"] * 100), "n": x["n"], "baru_naik1j": None if b is None else round(b * 100)})
        if not a:
            continue
        angka, kata = a["teks"].split(" ", 1)
        pb = None if b is None else int(round(100 * (b if a["arah"] == "naik" else 1 - b)))
        if pb is not None and abs(pb - a["persen"]) >= 10:
            angka = f"{min(pb, a['persen'])}–{max(pb, a['persen'])}%"
        out.append({"dtk": f"{h} jam", "teks": a["teks"], "angka": angka, "kata": kata, "kuat": a["kuat"],
                    "persen": a["persen"], "arah": a["arah"], "gerak": None, "n": a["n"], "exness": None,
                    "baru": pb})
    return out


def _fmt(x: float) -> str:
    return f"{x / 1e6:g}M" if x >= 1e6 else f"{x / 1e3:g}K" if x >= 1e3 else f"{x:g}"


def kejutan(title: str, hasil: str, z: float, stages: list[dict]) -> dict | None:
    """Besar kejutan (|Act - perkiraan| vs ambang 1,5x median riwayat): persen 1 menit khusus kejutan BESAR / kecil
    (research/reaksi_menit.besar_kecil). Sel "1 mnt" di `stages` ikut diganti. None bila data tidak cukup."""
    r = REAKSI.get(title) or {}
    amb = r.get("ambang")
    if amb is None or hasil not in ("bawah", "atas"):
        return None
    nama = "besar" if z >= amb else "kecil"
    x = (r.get(hasil) or {}).get(nama)
    if not x:
        return None
    b = x.get("baru_naik60")
    a = arah_emas({"naik1j": round(x["naik60"] * 100), "n": x["n"], "baru_naik1j": None if b is None else round(b * 100)})
    if not a:
        return None
    for c in stages:
        if c["dtk"] == "1 mnt":
            c.update(teks=a["teks"], angka=a["teks"].split(" ", 1)[0], kata=a["teks"].split(" ", 1)[1], kuat=a["kuat"],
                     persen=a["persen"], arah=a["arah"], n=a["n"])
    label = f"kejutan {'BESAR' if nama == 'besar' else 'kecil'} ({_fmt(z)} {'≥' if nama == 'besar' else '<'} {_fmt(amb)})"
    return {"ukuran": nama, "label": label, **{k: a[k] for k in ("teks", "kuat", "persen", "arah")},
            "bukti": f"{label}: emas 1 mnt {a['persen']}% {a['arah']} ({x['n']} rilis, gerak ±"
                     + f"${x['gerak60']:.2f})".replace(".", ",")}


def tahap_teks(stages: list[dict]) -> str:
    """"1 dtk belum gerak (±$0,17) • 2 dtk 85% NAIK (±$2,68) • 3 dtk 91% NAIK • 1 mnt 81% NAIK" (tanpa emoji)."""
    parts = []
    for x in stages:
        t = x["teks"] if not x["dtk"].endswith("jam") else f"{x['angka']} {x['kata']}"
        t = t.replace(" 🟢", "").replace(" 🔴", "").replace(" ⚪", "")
        if x.get("gerak") is not None and x["dtk"] in ("1 dtk", "2 dtk"):
            t += f" (±${x['gerak']:.2f})".replace(".", ",")
        parts.append(f"{x['dtk']} {t}")
    return " • ".join(parts)


def _emas(title: str) -> tuple[dict, str]:
    """({hasil: {naik1j, baru_naik1j, n, tahun}}, jangka) — reaksi 1 menit (tick) bila ada, selain itu 1 jam."""
    r = REAKSI.get(title)
    if r:
        out = {}
        for k, src in (("bawah", "bawah"), ("atas", "atas"), ("sesuai", "sama")):
            if src in r:
                b = r[src].get("baru_naik60")
                out[k] = {"naik1j": round(r[src]["naik60"] * 100), "n": r[src]["n"], "tahun": r.get("tahun"),
                          "baru_naik1j": None if b is None else round(b * 100)}
        return out, "1 menit"
    return (STATS["dasar"].get(title) or {}).get("emas") or {}, "1 jam"


def skenario(title: str) -> list[dict]:
    """Sebelum rilis: arah emas 1 menit (cadangan 1 jam) bila data di bawah / di atas perkiraan (atau = perkiraan)."""
    emas, _ = _emas(title)
    keys = [k for k in ("bawah", "atas") if k in emas] or [k for k in ("sesuai",) if k in emas]
    out = []
    for k in keys:
        a = arah_emas(emas[k])
        if a:
            out.append({"hasil": k, "label": LABEL_HASIL[k], **a})
    return out


OP = {"bawah": "<", "atas": ">", "sesuai": "="}


def skenario_hentakan(title: str, forecast: str) -> list[dict]:
    """Skenario dengan label jelas: "⚡ Hentakan 1 menit bila Act < 89K" (permintaan pengguna 2 Okt 2026), ditambah
    tahap detik 1-2-3 & 1 menit ("tahap"; aplikasi 3.18 menampilkannya sebagai deretan angka, aplikasi lama membaca
    ringkasannya di awal "bukti")."""
    _, jangka = _emas(title)
    f = forecast or "perkiraan"
    out = []
    for x in skenario(title):
        row = dict(x, label=f"⚡ Hentakan {jangka} bila Act {OP[x['hasil']]} {f}")
        st = tahap(title, x["hasil"])
        if any(s["dtk"].endswith("dtk") for s in st):
            row.update(tahap=st, label_tahap=f"⚡ Bila Act {OP[x['hasil']]} {f} → arah emas",
                       bukti_tahap=x["bukti"] + " • detik 1–3 dicek di tick Exness • 3–6 jam: XAU M15, "
                                                 "a–b% = semua tahun vs sejak Okt 2021",
                       bukti=tahap_teks(st) + " • " + x["bukti"])
        out.append(row)
    return out


def kesimpulan(title: str, actual: str, forecast: str) -> dict | None:
    """Setelah Act keluar: arah emas 1 menit (cadangan 1 jam) dari data historis untuk hasil itu (Act vs Cons)."""
    emas, jangka = _emas(title)
    a, f = _num(actual), _num(forecast)
    if not emas or a is None or f is None:
        return None
    hasil = "atas" if a > f else "bawah" if a < f else "sesuai"
    r = arah_emas(emas.get(hasil))
    if not r:
        return None
    st = tahap(title, hasil)
    kej = kejutan(title, hasil, abs(a - f), st)
    if kej:
        r = dict(r, teks=kej["teks"], kuat=kej["kuat"], persen=kej["persen"], arah=kej["arah"],
                 bukti=kej["bukti"] + " • " + r["bukti"])
    detik_txt = tahap_teks(st) + " • " if any(s["dtk"].endswith("dtk") for s in st) else ""
    return {"hasil": hasil, **r, "tahap": st, "kejutan": kej,
            "catatan": f"{LABEL_HASIL[hasil].replace('Data', 'Act')} → emas {detik_txt or jangka + ' • '}{r['bukti']}"}


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
        "skenario": skenario_hentakan(title, forecast),
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
