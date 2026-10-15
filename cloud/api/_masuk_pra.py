"""📍 Gaya pengguna: MASUK 1 detik SEBELUM rilis, tahan 1 detik s/d 1–3 menit (15 Okt 2026).

Pengguna: "style trading saya entry 1 detik sebelum release news dan bertahan 1 detik hingga 1–3 menit ke depan, karena entry
pada detik ke 2 pasti delay dan tertinggal jauh". Angka dari research/masuk_pra.py (tick asli Exness XAUUSDc 2016–2026, spread
saat berita; masuk BUY di ask / SELL di bid t0−1 dtk, tutup di bid/ask detik h) → masuk_pra.json:

- pra_satu["t1"] (sebelum rilis): untung% bila masuk t−1 SEARAH tebakan lalu tahan 1 dtk … 3 mnt, per kelompok berita & ARAH
  tebakan, sebelum / sejak Okt 2021, pembanding selalu BUY. Status: teruji (≥ 60% tahan 1 mnt, ≥ 20 rilis, kedua periode ≥ 55%
  & rata-rata > 0) / belum terbukti (≥ 55%, rata-rata ≥ +$0,20/oz) / jangan. Tanpa tebakan = lempar koin − spread → jangan.
- pra_satu["lanjut"]["posisi"] (setelah rilis, ⚡LIVE di aplikasi): posisi APA PUN yang dibuka t−1 — emas bergerak ≥ $X di
  detik 1/2 SEARAH posisi → untung% bila tahan s/d 10/30/60/180 dtk; BERLAWANAN → tahan pun jarang kembali untung (tutup);
  hampir diam (< $0,30) → rata-rata rugi ±spread. Kelompok berita bila ≥ 20 rilis, selain itu semua berita ("g").

Info saja, tanpa order. Env MASUK_PRA=0 mematikan.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import _pra_aset

_F = Path(__file__).with_name("masuk_pra.json")
DATA = json.loads(_F.read_text(encoding="utf-8")) if _F.exists() else {}
N_MIN = 20                      # kelompok berita dipakai bila kejadian ≥ 20, selain itu angka semua berita
TERUJI = ("teruji", "tutup kertas")


def aktif() -> bool:
    return os.environ.get("MASUK_PRA", "1") != "0" and bool(DATA.get("t1"))


def grup(title: str) -> str:
    g = next((g for k, g in _pra_aset.GRUP if k in (title or "")), "SEMUA")
    return {"ISM Jasa": "ISM"}.get(g, g)


def usd(v: float) -> str:
    return f"{'+' if v >= 0 else '−'}${abs(v):.2f}".replace(".", ",")


def t1(row: dict) -> dict | None:
    """Masuk t−1 searah tebakan pra_satu (lot biasa): status + teks singkat + poin bukti."""
    if not aktif() or not isinstance(row, dict) or not row.get("time"):
        return None
    arah = row.get("arah")
    if arah not in ("naik", "turun"):
        a = (DATA.get("acak") or {}).get("60")
        sp = (DATA.get("spread") or {}).get("median")
        teks = "📍 Masuk t−1: JANGAN — tanpa tebakan = lempar koin"
        return {"status": "jangan", "teks": teks,
                "bukti": (f"📍 Masuk 1 dtk sebelum rilis tanpa arah teruji: BUY/SELL acak rata-rata {usd(a)}/oz (tahan 1 mnt; "
                          f"spread saat berita median ${sp:.2f})".replace(f"{sp:.2f}", f"{sp:.2f}".replace(".", ","))
                          if a is not None and sp is not None
                          else "📍 Masuk 1 dtk sebelum rilis tanpa arah teruji = lempar koin dikurangi spread")}
    g = grup(row.get("title") or "")
    x = (DATA.get("t1", {}).get(g) or {}).get(arah)
    pos = "BUY" if arah == "naik" else "SELL"
    if not x or x.get("n", 0) < 10:
        return {"status": "belum diuji", "teks": f"📍 Masuk t−1 {pos}: belum diuji untuk tebakan ini → tunggu ⚡LIVE",
                "bukti": f"📍 Tebakan {arah.upper()} {row.get('nama') or g} belum punya cukup rilis bertick (masuk t−1) untuk diuji"}
    H = x["H"]
    w60, r60 = H["60"]
    lama, baru = x.get("lama"), x.get("baru")
    ok = lambda p: bool(p) and p[2] >= 5 and p[0] >= 55 and p[1] > 0  # noqa: E731
    if w60 >= 60 and x["n"] >= N_MIN and ok(lama) and ok(baru) and r60 >= 0.2:
        st = "teruji"
    elif w60 >= 55 and r60 >= 0.2:
        st = "belum terbukti"
    else:
        st = "jangan"
    if st == "teruji" and row.get("status") not in TERUJI:   # tebakan utama lemah/belum terbukti → t−1 tidak boleh lebih tinggi
        st = "belum terbukti"
    tanda = {"teruji": "✅", "belum terbukti": "⚠️", "jangan": "✗"}[st]
    if st == "jangan":
        teks = f"📍 Masuk t−1 {pos}: JANGAN — tahan 1 mnt dulu untung {w60}%, rata-rata {usd(r60)}/oz ({x['n']} rilis)"
    else:
        w30 = (H.get("30") or [None])[0]
        rng = f"{min(w30, w60)}–{max(w30, w60)}%" if w30 is not None and w30 != w60 else f"{w60}%"
        teks = f"📍 Masuk t−1 {pos} → tahan 30 dtk–1 mnt: untung {rng} ({x['n']} rilis) {tanda}"
    per = []
    if lama:
        per.append(f"sebelum Okt 2021 {lama[0]}% ({usd(lama[1])}/oz)")
    if baru:
        per.append(f"sejak {baru[0]}% ({usd(baru[1])}/oz)")
    bb = x.get("buy_baru")
    jangka = " • ".join(f"{lbl} {H[h][0]}%" for h, lbl in (("1", "detik 1"), ("5", "5 dtk"), ("30", "30 dtk"),
                                                            ("60", "1 mnt"), ("180", "3 mnt")) if h in H)
    bukti = (f"📍 Gaya masuk 1 dtk sebelum rilis (lot biasa, spread asli Exness, {x['n']} rilis {g} tebakan {arah.upper()}): "
             f"untung bila ditutup di {jangka}; rata-rata 1 mnt {usd(r60)}/oz" + (" • " + " / ".join(per) if per else "")
             + (f" • pembanding selalu BUY sejak Okt 2021 {bb[0]}% ({usd(bb[1])}/oz)" if bb else "")
             + " • tutup di detik 1 hampir selalu rugi (spread & emas belum bergerak); keputusan tahan/tutup di detik 2 (⚡LIVE)")
    return {"status": st, "arah": arah, "grup": g, "n": x["n"], "teks": teks, "bukti": bukti,
            "tahan": {h: v[0] for h, v in H.items()}}


def posisi(title: str) -> dict | None:
    """Tabel ⚡LIVE posisi t−1 (searah 's|X' / berlawanan 'l|X' / hampir diam 'kecil') per detik 1 & 2."""
    if not aktif():
        return None
    ps = DATA.get("posisi") or {}
    g = grup(title)
    sendiri, semua = ps.get(g) or {}, ps.get("SEMUA") or {}
    out = {"g": g if sendiri else "SEMUA"}
    for d in ("1", "2"):
        a, b = sendiri.get(d) or {}, semua.get(d) or {}
        isi = {}
        for k in set(a) | set(b):
            x = a.get(k) if (a.get(k) or {}).get("n", 0) >= N_MIN else b.get(k)
            if x and x.get("n", 0) >= 10:
                isi[k] = {**x, "g": g if x is a.get(k) else "SEMUA"}
        if isi:
            out[d] = isi
    return out if len(out) > 1 else None


def attach(persiapan: dict) -> None:
    """Pasang t1 + posisi ke pra_satu (dan poin 📍 di detail)."""
    if not isinstance(persiapan, dict) or not aktif():
        return
    ps = persiapan.get("pra_satu")
    if not isinstance(ps, dict):
        return
    t = t1(ps)
    if t:
        ps["t1"] = t
        if isinstance(ps.get("poin"), list) and not any(str(x).startswith("📍") for x in ps["poin"]):
            i = next((k for k, x in enumerate(ps["poin"]) if str(x).startswith(("👥", "🔗", "Setelah rilis"))), len(ps["poin"]))
            ps["poin"].insert(i, t["bukti"])
            ps["bukti"] = "\n".join("• " + x for x in ps["poin"])
    p = posisi(ps.get("title") or "")
    if p:
        ps.setdefault("lanjut", {})
        if isinstance(ps["lanjut"], dict):
            ps["lanjut"]["posisi"] = p
