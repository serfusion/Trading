"""⏱️ KHUSUS XAU: arah emas 1–10 detik setelah rilis untuk berita berikutnya (rencana pengguna: entry 1 detik sebelum
rilis). Permintaan 10 Okt 2026: "jangan terpaut untung/rugi — hasil 1–10 detik ke depan naik atau turun saja", "hanya XAU".

Arah = petunjuk teruji berita itu (_petunjuk.py: Kalshi, kejutan bulan lalu, berbalik, minyak WTI, survei Fed daerah,
GDPNow → arah emas). Persen = seberapa sering harga XAU (tengah bid/ask, tick Exness) pada detik 1/2/3/5/10 setelah
rilis bergerak searah tebakan dibanding 1 detik sebelum rilis (research/pra_xau_arah.py → pra_aset.json["xau_arah"],
2010–2026). ✅ = konsisten periode lama & baru (p < 0,05); ⚠️ = di atas 55% tetapi belum terbukti; ⚪ = ≈ lempar koin.
INFORMASI saja, tanpa order.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import _prediksi

_PATH = Path(__file__).resolve().parent / "pra_aset.json"
DATA = json.loads(_PATH.read_text(encoding="utf-8")) if _PATH.exists() else {}
H = (1, 2, 3, 5, 10)
JUDUL = ("CPI m/m", "Core CPI m/m", "ISM Services PMI", "Advance GDP q/q", "Unemployment Rate",
         "Non-Farm Employment Change", "Core PPI m/m", "PPI m/m", "JOLTS Job Openings")


def varian(title: str, b: dict) -> str | None:
    """Nama varian riset yang sama dengan petunjuk yang memberi arah saat ini."""
    t = b.get("tebak") or {}
    lain = b.get("sepakat_lain") or []
    if title in ("CPI m/m", "Core CPI m/m"):
        if b.get("kalshi_sepakat"):
            return "CPI • Kalshi & kejutan lalu sepakat"
        if "K" in t:
            return "CPI • Kalshi"
        if "K|P&WTI" in lain:
            return "CPI • + minyak WTI sepakat"
        if "K|P" in t:
            return "CPI • Kalshi, cadangan kejutan lalu"
        if "WTI" in t:
            return "CPI • minyak WTI saja"
    if title == "ISM Services PMI":
        return "ISM Jasa • + aktivitas Fed daerah sepakat" if "-P&GA" in lain else "ISM Jasa • berbalik"
    if title == "Advance GDP q/q":
        return "GDP • GDPNow"
    if title in ("Unemployment Rate", "Non-Farm Employment Change"):
        return "NFP • pengangguran Kalshi/kejutan lalu"
    if title in ("Core PPI m/m", "PPI m/m"):
        return "PPI • kejutan CPI pekan ini" if "CPI" in t else "Core PPI • berbalik"
    if title == "JOLTS Job Openings":
        return "JOLTS • berbalik"
    return None


def ringkas(var: str, arah: str) -> dict | None:
    v = ((DATA.get("xau_arah") or {}).get(var) or {}).get("h") or {}
    sel = []
    for h in H:
        r = (v.get(f"{h}|0") or {}).get("exness") or {}
        if r.get("n"):
            sel.append({"h": h, "benar": r["benar"], "n": r["n"], "lama": r.get("lama"), "baru": r.get("baru"),
                        "konsisten": bool((v.get(f"{h}|0") or {}).get("konsisten"))})
    if not sel:
        return None
    jauh = [x for x in sel if x["h"] >= 2] or sel                 # detik 1 sering belum bergerak (< $0,30)
    lo, hi = min(x["benar"] for x in jauh), max(x["benar"] for x in jauh)
    if all(x["konsisten"] for x in jauh):
        status, tanda = "teruji", "✅"
    elif hi >= 55:
        status, tanda = "belum terbukti", "⚠️"
    else:
        status, tanda = "acak", "⚪"
    rentang = f"{lo:.0f}%" if round(lo) == round(hi) else f"{lo:.0f}–{hi:.0f}%"
    simbol = "NAIK ▲" if arah == "naik" else "TURUN ▼"
    return {"arah": arah, "status": status,
            "teks": f"XAU {simbol} • benar {rentang} (2–10 dtk) {tanda}" if status != "acak"
            else f"XAU • ≈ 50:50 di detik 2–10 (petunjuk berita ini tidak teruji untuk detik) {tanda}",
            "detik": sel,
            "kecil": " • ".join(f"{x['h']} dtk {x['benar']:.0f}%" for x in sel) + f" (n {sel[-1]['n']} rilis)",
            "bukti": f"dasar: {var} • harga XAU 1 dtk sebelum vs sesudah rilis, tick Exness 2015–2026 • lama/baru "
                     + " • ".join(f"{x['h']} dtk {x['lama'] or '-'}/{x['baru'] or '-'}%" for x in sel).replace(".", ",")}


GRUP = [("Non-Farm", "NFP"), ("Unemployment Rate", "NFP"), ("Average Hourly", "NFP"), ("ADP", "ADP"), ("CPI", "CPI"),
        ("PPI", "PPI"), ("Retail", "RETAIL"), ("PCE", "PCE"), ("GDP", "GDP"), ("Federal Funds", "FOMC"),
        ("JOLTS", "JOLTS"), ("ISM Services", "ISM Jasa"), ("ISM", "ISM"), ("Claims", "CLAIMS")]


def kepastian(title: str) -> str | None:
    """Detik 2 (dan 1): bila emas sudah bergerak ≥ $0,50 dari harga 1 dtk sebelum rilis, seberapa sering arah itu masih
    sama di detik 10 (research/pra_xau_dalam.py bagian B, tick Exness 2015–2026)."""
    lj = DATA.get("lanjut") or {}
    g = next((g for k, g in GRUP if k in title), "SEMUA")
    r2 = lj.get(f"{g}|2|0.5|10") or lj.get("SEMUA|2|0.5|10")
    if not r2:
        return None
    r1 = lj.get(f"{g}|1|0.5|10") or {}
    teks = (f"📌 Pasti-nya di detik 2: bila emas sudah bergerak ≥ $0,50 dari harga 1 dtk sebelum rilis, arah itu masih "
            f"sama di detik 10 pada {r2['tetap']:.0f}% rilis (n {r2['n']})")
    if r1.get("n"):
        teks += f" • di detik 1: {r1['tetap']:.0f}% (n {r1['n']})"
    return teks.replace(".", ",") + ". Berlawanan dengan posisi → tutup cepat."


def attach(persiapan: dict, now: datetime | None = None) -> None:
    """persiapan["pra"] = berita besar berikutnya + arah XAU 1–10 detik (atau alasan bila belum ada tebakan)."""
    if not isinstance(persiapan, dict) or not DATA.get("xau_arah"):
        return
    now = now or datetime.now(timezone.utc)
    kartu = [c for k in ("berita", "mendatang") for c in persiapan.get(k) or [] if isinstance(c, dict)
             and not c.get("released") and datetime.fromisoformat(c["time"]) > now]
    if not kartu:
        return
    t0 = min(c["time"] for c in kartu)
    sama = [c for c in kartu if c["time"] == t0]
    ber = [c for c in sama if (c.get("petunjuk_teruji") or {}).get("arah_emas") and varian(c["title"],
                                                                                         c["petunjuk_teruji"])]
    c = next((x for x in ber if x["title"] == "CPI m/m"), ber[0] if ber else sama[0])
    out = {"judul": f"⏱️ Entry 1 dtk sebelum {_prediksi.nama(c['title'])} • {c.get('when', '')}", "title": c["title"],
           "time": c["time"], "catatan": "Arah dari petunjuk teruji; persen = seberapa sering harga XAU 1–10 detik "
                                         "setelah rilis bergerak searah (bukan untung/rugi). Info saja."}
    b = c.get("petunjuk_teruji") or {}
    var = varian(c["title"], b) if b.get("arah_emas") else None
    r = ringkas(var, b["arah_emas"]) if var else None
    if r:
        out.update(r)
    else:
        out.update({"status": "acak", "teks": "XAU • arah belum bisa ditebak (tanpa petunjuk teruji) ⚪",
                    "kecil": "≈ 50:50 di detik 1–10", "bukti": "berita ini tidak punya petunjuk sebelum rilis yang lolos uji"})
    k = kepastian(c["title"])
    if k:
        out["kepastian"] = k
    persiapan["pra"] = out
