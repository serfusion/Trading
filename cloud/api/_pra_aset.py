"""⏱️ KHUSUS XAU: arah emas 1–10 detik setelah rilis untuk berita berikutnya (rencana pengguna: entry 1 detik sebelum
rilis). Permintaan 10 Okt 2026: "jangan terpaut untung/rugi — hasil 1–10 detik ke depan naik atau turun saja", "hanya XAU".

Arah = petunjuk teruji berita itu (_petunjuk.py: Kalshi, kejutan bulan lalu, berbalik, minyak WTI, survei Fed daerah,
GDPNow → arah emas). Persen = seberapa sering harga XAU (tengah bid/ask, tick Exness) pada detik 1/2/3/5/10 setelah
rilis bergerak searah tebakan dibanding 1 detik sebelum rilis (research/pra_xau_arah.py → pra_aset.json["xau_arah"],
2010–2026). ✅ = konsisten periode lama & baru (p < 0,05); ⚠️ = di atas 55% tetapi belum terbukti; ⚪ = ≈ lempar koin.

➕ Tren emas 4 jam (research/pra_xau_semua.py, 2.051 rilis 2010–2026, fitur KETAT ≤ 1 dtk sebelum rilis): harga terbaru vs
harga 4 jam lalu (Twelve Data 15 mnt, cache baris Supabase 'pra_tren'). Petunjuk berita & tren SEARAH → benar 63–67%
di detik 2–10 (lama 62–69%, baru 59–66%; ISM 70–76%); BERLAWANAN → 49–55% ≈ lempar koin; berita tanpa petunjuk: tren
saja 55–56% (lemah). Semua metode lain (gerak tick 10–120 dtk, BTC, konsensus vs angka lalu, kejutan lalu semua berita, model
walk-forward) ≈ 50–55% di periode baru dan tidak lebih baik dari uji acak. INFORMASI saja, tanpa order.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import _core
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


TREN_JAM = 6                      # tren hanya dihitung bila rilis ≤ 6 jam lagi (sebelumnya tidak bermakna)


def hitung_tren(bars: list, now: datetime) -> dict | None:
    """Harga terbaru vs open candle 15 mnt pertama yang mulai ≥ now − 4 jam (= fitur H4 riset)."""
    bars = [b for b in bars if b.h > b.l and not _core.weekend_closed(b.t)]
    if len(bars) < 8 or now - bars[-1].t > timedelta(minutes=45):
        return None                                   # pasar tutup / data basi
    acuan = now - timedelta(hours=4)
    ref = next((b for b in bars if b.t >= acuan), None)
    if ref is None or ref.t - acuan > timedelta(hours=1) or ref is bars[-1]:
        return None
    g4 = round(bars[-1].c - ref.o, 2)
    if g4 == 0:
        return None
    return {"g4": g4, "harga": bars[-1].c, "acuan": ref.o, "at": _core.iso(now)}


def tren_emas(store, now: datetime, fetch, sisa: timedelta) -> dict | None:
    """Tren 4 jam dengan cache (5 mnt bila rilis ≤ 1 jam lagi, selain itu 15 mnt) di baris Supabase 'pra_tren'."""
    ttl = timedelta(minutes=5 if sisa <= timedelta(hours=1) else 15)
    st = {}
    try:
        st = store.get_state("pra_tren") or {} if store else {}
    except Exception:  # noqa: BLE001
        st = {}
    if st.get("at") and timedelta(0) <= now - _core.parse_iso(st["at"]) <= ttl:
        return st
    try:
        t = hitung_tren(fetch(), now)
    except Exception:  # noqa: BLE001 - tanpa tren: baris tren tidak tampil
        t = None
    if t and store:
        try:
            store.save_state(t, "pra_tren")
        except Exception:  # noqa: BLE001
            pass
    return t


def _rentang(blok: dict) -> tuple[str, int, dict, float]:
    sel = [(blok.get(str(h)) or {}).get("exness") or {} for h in (2, 3, 5, 10)]
    sel = [x for x in sel if x.get("n")]
    if not sel:
        return "", 0, {}, 0.0
    lo, hi = min(x["benar"] for x in sel), max(x["benar"] for x in sel)
    r = f"{lo:.0f}%" if round(lo) == round(hi) else f"{lo:.0f}–{hi:.0f}%"
    return r, max(x["n"] for x in sel), sel[-1], sum(x["benar"] for x in sel) / len(sel)


def baris_tren(title: str, arah_berita: str | None, t: dict, khusus: dict | None = None) -> dict | None:
    """➕ baris tren emas 4 jam: searah / berlawanan dengan petunjuk berita, atau tren saja (berita tanpa petunjuk).
    `khusus` = angka gabungan milik aturan per berita ({"sepakat"|"berlawanan": {benar, lama, baru, n}})."""
    tr = DATA.get("tren") or {}
    if not tr or not t:
        return None
    naik = t["g4"] > 0
    simbol = "NAIK ▲" if naik else "TURUN ▼"
    g = next((g for k, g in GRUP if k in title), "SEMUA")
    g = "ISM" if g == "ISM Jasa" else g
    gerak = f"{'+' if naik else '−'}${abs(t['g4']):.2f}".replace(".", ",")
    jam = _core.parse_iso(t["at"]).strftime("%H:%M")
    if arah_berita:
        hub = "sepakat" if (arah_berita == "naik") == naik else "berlawanan"
        k = (khusus or {}).get(hub)
        if k:
            r, n, akhir, rata, lingkup = f"{k['benar']:.0f}%", k["n"], k, k["benar"], "aturan berita ini"
        else:
            blok = (tr.get(hub) or {}).get(g) or {}
            if not blok or ((blok.get("3") or {}).get("exness") or {}).get("n", 0) < 40:
                g, blok = "SEMUA", (tr.get(hub) or {}).get("SEMUA") or {}
            r, n, akhir, rata = _rentang(blok)
            lingkup = "semua berita berpetunjuk" if g == "SEMUA" else g
        if not r:
            return None
        if hub == "sepakat":
            teks = f"➕ Tren emas 4 jam {simbol} ({gerak}) SEARAH → benar {r} ⚠️"
            putusan = f"Tebakan terbaik: XAU {simbol} (petunjuk berita & tren searah)"
        else:
            teks = f"⚠️ Tren emas 4 jam {simbol} ({gerak}) BERLAWANAN → hanya {r} ≈ lempar koin"
            putusan = "≈ 50:50 — petunjuk berita & tren berlawanan, lebih aman tidak entry"
    else:
        hub = "tanpa"
        r, n, akhir, rata = _rentang((tr.get("tanpa") or {}).get("SEMUA") or {})
        if not r:
            return None
        lingkup = "semua berita tanpa petunjuk"
        teks = f"Tren emas 4 jam {simbol} ({gerak}) → ikut tren benar {r} (lemah, ≈ lempar koin) ⚪"
        putusan = "≈ 50:50 — tanpa petunjuk berita, tren saja lemah"
    return {"arah": "naik" if naik else "turun", "hubungan": hub, "g4": t["g4"], "teks": teks, "putusan": putusan,
            "persen": round(rata),
            "bukti": (f"tren = harga terbaru vs 4 jam lalu (dihitung {jam} UTC; cek lagi 1–5 mnt sebelum rilis) • "
                      f"{lingkup}: 2–10 dtk {r} (n {n}) • lama {akhir.get('lama')}% / baru {akhir.get('baru')}% • "
                      f"ditemukan setelah melihat data → perlu uji maju").replace(".", ",")}


# 🎯 Daftar berita mendatang di bawah XAU (aplikasi 4.30, permintaan pengguna 10 Okt 2026: "CPI peluang emas naik 68%
# - 4 hari lagi"). Persen = seberapa sering arah tebakan benar 2–10 dtk setelah rilis (rata-rata detik 2/3/5/10, tick
# Exness). Sumber: petunjuk teruji (_petunjuk → xau_arah) atau aturan per berita yang konsisten lama & baru
# (research/pra_per_berita.py → pra_aset.json["per_berita"]): hari NFP = kalender survei BLS (5 pekan antar pekan survei
# → pengangguran di atas → emas naik, 57%; + tren 4 jam searah 62%). Tanpa petunjuk → "≈ 50:50" (tidak dikarang).
URUT = ("Non-Farm Employment Change", "CPI m/m", "Core CPI m/m", "Federal Funds Rate", "PPI m/m", "Core PPI m/m",
        "Retail Sales m/m", "Core Retail Sales m/m", "ISM Services PMI", "ISM Manufacturing PMI", "JOLTS Job Openings",
        "Advance GDP q/q", "Core PCE Price Index m/m", "ADP Non-Farm Employment Change", "Unemployment Claims")
NFP_HARI = ("Non-Farm Employment Change", "Unemployment Rate", "Average Hourly Earnings m/m")
MAKS_DAFTAR = 5
DAFTAR_HARI = 31


def sisa_teks(dt: timedelta) -> str:
    s = dt.total_seconds()
    if s >= 86400:
        return f"{int(s // 86400)} hari lagi"
    if s >= 3600:
        return f"{int(s // 3600)} jam lagi"
    return f"{max(1, int(s // 60))} mnt lagi"


def pekan5(t0: datetime) -> bool:
    """True bila jarak pekan survei BLS (pekan Minggu–Sabtu yang memuat tgl 12) bulan acuan vs bulan sebelumnya 5 pekan."""
    def minggu(th: int, bl: int) -> datetime:
        d = datetime(th, bl, 12)
        return d - timedelta(days=(d.weekday() + 1) % 7)
    th, bl = (t0.year, t0.month - 1) if t0.month > 1 else (t0.year - 1, 12)
    th0, bl0 = (th, bl - 1) if bl > 1 else (th - 1, 12)
    return (minggu(th, bl) - minggu(th0, bl0)).days >= 35


def _persen(sel: list) -> float:
    jauh = [x["benar"] for x in sel if x["h"] >= 2] or [x["benar"] for x in sel]
    return sum(jauh) / len(jauh)


def tebak_kartu(c: dict) -> dict | None:
    """Arah + persen untuk satu kartu berita (tanpa tren)."""
    b = c.get("petunjuk_teruji") or {}
    var = varian(c["title"], b) if b.get("arah_emas") else None
    r = ringkas(var, b["arah_emas"]) if var else None
    if r and r["status"] != "acak":
        return {"arah": r["arah"], "persen": round(_persen(r["detik"])), "status": r["status"],
                "dasar": var, "bukti": r["bukti"]}
    pb = (DATA.get("per_berita") or {}).get("Unemployment Rate|PK5")
    if c["title"] in NFP_HARI and pb:
        lima = pekan5(datetime.fromisoformat(c["time"]))
        ur_atas = (1.0 if lima else -1.0) * pb["arah"] > 0
        return {"arah": "naik" if ur_atas else "turun", "persen": round(pb["benar"]), "status": "lemah",
                "dasar": "Pengangguran • kalender survei BLS",
                "khusus": {"sepakat": pb.get("tren_searah"), "berlawanan": pb.get("tren_lawan")},
                "bukti": (f"dasar: {'5' if lima else '4'} pekan antar pekan survei BLS → pengangguran cenderung "
                          f"{'DI ATAS' if ur_atas else 'DI BAWAH'} perkiraan (tebakan angka {pb['kejutan']:.0f}%) • emas "
                          f"2–10 dtk benar {pb['benar']:.0f}% (n {pb['n']}; lama {pb['lama']:.0f}% / baru {pb['baru']:.0f}%) "
                          f"• lemah, tetapi konsisten dua periode").replace(".", ",")}
    return None


def daftar(persiapan: dict, now: datetime, tren=None) -> list:
    kartu = [c for k in ("berita", "mendatang") for c in persiapan.get(k) or [] if isinstance(c, dict)
             and c.get("time") and not c.get("released") and datetime.fromisoformat(c["time"]) > now
             and datetime.fromisoformat(c["time"]) - now <= timedelta(days=DAFTAR_HARI)]
    per_waktu: dict[str, list] = {}
    for c in kartu:
        per_waktu.setdefault(c["time"], []).append(c)
    out = []
    for t0 in sorted(per_waktu)[:MAKS_DAFTAR * 2]:
        cs = per_waktu[t0]
        kandidat = [(tebak_kartu(c), c) for c in cs]
        ada = [(g, c) for g, c in kandidat if g]
        prio = lambda gc: (0 if gc[0] else 1, URUT.index(gc[1]["title"]) if gc[1]["title"] in URUT else 99)  # noqa: E731
        g, c = sorted(ada or kandidat, key=prio)[0]
        if not ada and c["title"] not in URUT:
            continue                                              # berita kecil tanpa petunjuk: tidak ditampilkan
        nm = _prediksi.nama(c["title"] if not (g and g["dasar"].startswith("Pengangguran")) else NFP_HARI[0])
        sisa = sisa_teks(datetime.fromisoformat(t0) - now)
        row = {"title": c["title"], "nama": nm, "time": t0, "when": c.get("when", ""), "sisa": sisa}
        if g:
            tanda = "✅" if g["status"] == "teruji" else "⚠️"
            row.update(arah=g["arah"], persen=g["persen"], status=g["status"], bukti=g["bukti"],
                       teks=f"{nm} • peluang emas {g['arah']} {g['persen']}% {tanda} • {sisa}")
        else:
            row.update(arah=None, persen=50, status="acak", bukti="belum ada petunjuk sebelum rilis yang lolos uji "
                                                                  "untuk berita ini (diuji 2010–2026)",
                       teks=f"{nm} • ≈ 50:50 (belum ada petunjuk teruji) • {sisa}")
        if not out and tren is not None and datetime.fromisoformat(t0) - now <= timedelta(hours=TREN_JAM):
            khusus = g.get("khusus") if g else None
            bt = baris_tren(c["title"], g["arah"] if g else None, tren(datetime.fromisoformat(t0) - now), khusus)
            if bt:
                row["tren"] = bt
                if g and bt["hubungan"] == "sepakat":
                    pr = bt["persen"] if khusus else max(g["persen"], bt["persen"])
                    row.update(persen=pr, status="tren searah",
                               teks=f"{nm} • peluang emas {g['arah']} {pr}% (+ tren searah) ⚠️ • {sisa}")
                elif g and bt["hubungan"] == "berlawanan":
                    row.update(persen=50, status="acak",
                               teks=f"{nm} • ≈ 50:50 (petunjuk & tren 4 jam berlawanan) • {sisa}")
        out.append(row)
        if len(out) >= MAKS_DAFTAR:
            break
    return out


def attach(persiapan: dict, now: datetime | None = None, tren=None) -> None:
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
    if tren is not None:                                   # tren diambil sekali per permintaan (cache Supabase)
        asli, memo = tren, {}
        tren = lambda s_: memo["v"] if "v" in memo else memo.setdefault("v", asli(s_))  # noqa: E731
    sisa = datetime.fromisoformat(c["time"]) - now
    if tren is not None and sisa <= timedelta(hours=TREN_JAM):
        bt = baris_tren(c["title"], b.get("arah_emas") if r else None, tren(sisa))
        if bt:
            out["tren"] = bt
    elif tren is not None:
        out["tren_nanti"] = f"➕ Tren emas 4 jam tampil ≤ {TREN_JAM} jam sebelum rilis"
    persiapan["pra"] = out
    try:
        dl = daftar(persiapan, now, tren)
        if dl:
            persiapan["pra_daftar"] = dl
    except Exception:  # noqa: BLE001 - daftar opsional
        pass
