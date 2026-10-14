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
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import _core
import _cpi_detik
import _ppi_wti
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


def tutup_kertas(row: dict) -> str | None:
    """Poin "🧾 Tutup kertas SEBELUM rilis" (14 Okt 2026, pengguna: "UJI TUTUP KERTAS bukan setelah rilisnya", "yang hampir
    selalu benar"): ketepatan tebakan yang dibuat SEBELUM rilis, diuji per tahun hanya dengan data tahun-tahun sebelumnya,
    per arah tebakan + pembanding selalu-NAIK. Hanya CPI (cpi_detik.json uji.saring) & PPI (ppi_wti.json cpi_ppi.per_arah)."""
    t, arah = row.get("title") or "", row.get("arah")
    if not arah:
        return None
    if t in _cpi_detik.JUDUL and "WTI" not in (row.get("dasar") or ""):       # hanya aturan CPI detik (bukan WTI lama)
        sr = (_cpi_detik.DATA.get("uji") or {}).get("saring") or {}
        if not sr:
            return None
        if row.get("status") == "lemah" and row.get("lemah_jenis") != "yoyc":
            lm = sr.get("lemah") or {}
            return (f"🧾 Tutup kertas sebelum rilis (situasi lemah seperti ini): {lm.get('semua', 0):.0f}% dari "
                    f"{lm.get('n_rilis')} rilis • sejak Okt 2021 {lm.get('baru', 0):.0f}% • 2024+ {lm.get('s2024', 0):.0f}%"
                    ).replace(".", ",")
        k, n = sr.get("naik_2024") or [0, 0]
        teks = (f"🧾 Tutup kertas sebelum rilis (detik 2): 2016–2026 {sr['semua']:.0f}% ({sr['n_rilis']} rilis) • sejak "
                f"Okt 2021 {sr['baru']:.0f}% • tebakan NAIK sejak 2024 {k}/{n}" + (f" ({100 * k / n:.0f}%)" if n else "")
                + f" vs selalu-NAIK 2024+ {(_cpi_detik.DATA['uji'].get('selalu_naik_2024') or 81):.0f}%")
        if row.get("lemah_jenis") == "yoyc":
            teks += " • situasi inti y/y sekarang (YOYc) hanya 55%"
        return teks.replace(".", ",")
    if t in _ppi_wti.JUDUL:
        pa = ((_ppi_wti.DATA.get("cpi_ppi") or {}).get("per_arah") or {}).get(arah) or {}
        if not pa:
            return None
        g = lambda k: pa.get(k) or {}                                     # noqa: E731
        return (f"🧾 Tutup kertas sebelum rilis (tebakan {arah.upper()}): {g('semua').get('persen', 0):.0f}% ({g('semua').get('n')} "
                f"rilis) • dulu {g('lama').get('persen', 0):.0f}% • sejak Okt 2021 {g('baru').get('persen', 0):.0f}% • 2024+ "
                f"{g('s2024').get('persen', 0):.0f}% (n {g('s2024').get('n')})").replace(".", ",")
    return None


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
            "persen": round(rata), "n": n,
            **{k: round(akhir[k]) for k in ("lama", "baru") if akhir.get(k) is not None},
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
SATU_NAMA = {"Core CPI": "CPI", "CPI tahunan": "CPI", "Core PPI": "PPI", "Core Retail Sales": "Retail Sales"}
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
    if c.get("title") in _cpi_detik.JUDUL and _cpi_detik.aktif():
        # CPI: HANYA aturan tutup kertas IDX|K (_cpi_detik.py, 11 Okt 2026); varian lama (minyak WTI dst.) tidak lolos
        # tutup kertas sejak 2022 → tidak dipakai lagi. Tanpa petunjuk = None (≈ 50:50).
        return c.get("cpi_detik") or None
    if c.get("title") in _ppi_wti.JUDUL and _ppi_wti.aktif() and "ppi_wti" in c:
        # PPI: aturan minyak WTI bulan acuan (13 Okt 2026, lolos + verifikasi); "kejutan CPI pekan itu" lama tidak lolos
        return c.get("ppi_wti") or None
    b = c.get("petunjuk_teruji") or {}
    var = varian(c["title"], b) if b.get("arah_emas") else None
    r = ringkas(var, b["arah_emas"]) if var else None
    if r and r["status"] != "acak":
        jauh = [x for x in r["detik"] if x["h"] >= 2] or r["detik"]
        lb = {k: round(sum(x[k] for x in jauh) / len(jauh)) for k in ("lama", "baru")
              if all(x.get(k) is not None for x in jauh)}
        return {"arah": r["arah"], "persen": round(_persen(r["detik"])), "status": r["status"],
                "dasar": var, "bukti": r["bukti"], "n": max(x["n"] for x in jauh), **lb}
    pb = (DATA.get("per_berita") or {}).get("Unemployment Rate|PK5")
    if c["title"] in NFP_HARI and pb:
        lima = pekan5(datetime.fromisoformat(c["time"]))
        ur_atas = (1.0 if lima else -1.0) * pb["arah"] > 0
        return {"arah": "naik" if ur_atas else "turun", "persen": round(pb["benar"]), "status": "lemah",
                "lama": round(pb["lama"]), "baru": round(pb["baru"]), "n": pb["n"],
                "dasar": "Pengangguran • kalender survei BLS",  # = kunci pra_aset.json["jangka"]
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
        # petunjuk TERKUAT di waktu rilis itu (mis. core CPI "Kalshi & kejutan lalu sepakat" 66% mengalahkan headline
        # "minyak WTI saja" 56%), seri → urutan URUT (permintaan pengguna 10 Okt: CPI ≥ 65% bila ada petunjuknya)
        prio = lambda gc: (0 if gc[0] else 1, -(gc[0]["persen"] if gc[0] else 0),  # noqa: E731
                           URUT.index(gc[1]["title"]) if gc[1]["title"] in URUT else 99)
        g, c = sorted(ada or kandidat, key=prio)[0]
        if not ada and c["title"] not in URUT:
            continue                                              # berita kecil tanpa petunjuk: tidak ditampilkan
        nm = _prediksi.nama(c["title"] if not (g and g["dasar"].startswith("Pengangguran")) else NFP_HARI[0])
        nm = SATU_NAMA.get(nm, nm)                         # core & headline rilis bersamaan = satu berita
        sisa = sisa_teks(datetime.fromisoformat(t0) - now)
        row = {"title": c["title"], "nama": nm, "time": t0, "when": c.get("when", ""), "sisa": sisa}
        if c.get("forecast"):                                      # 📊 poin konsensus (14 Okt 2026)
            row["kons"] = {"f": c["forecast"], "p": c.get("previous") or ""}
        if g:
            tanda = "✅" if g["status"] in TERUJI else "⚠️"
            row.update(arah=g["arah"], persen=g["persen"], status=g["status"], bukti=g["bukti"], dasar=g["dasar"],
                       **{k: g[k] for k in ("lama", "baru", "n", "teks_sampai", "tanpa_tren", "peringatan", "per_detik",
                                            "terbaru", "lemah_jenis") if k in g},
                       teks=f"{nm} • peluang emas {g['arah']} {g['persen']}% {tanda} • {sisa}")
        else:
            row.update(arah=None, persen=50, status="acak", bukti="belum ada petunjuk sebelum rilis yang lolos uji "
                                                                  "untuk berita ini (diuji 2010–2026)",
                       teks=f"{nm} • ≈ 50:50 (belum ada petunjuk teruji) • {sisa}")
        if not out and tren is not None and datetime.fromisoformat(t0) - now <= timedelta(hours=TREN_JAM) \
                and not (g and g.get("tanpa_tren")):                 # gabungan tren × aturan CPI baru belum diuji
            khusus = g.get("khusus") if g else None
            bt = baris_tren(c["title"], g["arah"] if g else None, tren(datetime.fromisoformat(t0) - now), khusus)
            if bt:
                row["tren"] = bt
                angka_tren = {k: bt[k] for k in ("lama", "baru", "n") if k in bt}
                if g and bt["hubungan"] == "sepakat":
                    pr = bt["persen"] if khusus else max(g["persen"], bt["persen"])
                    if khusus or bt["persen"] > g["persen"]:
                        row.update(angka_tren)
                    row.update(persen=pr, status="tren searah",
                               teks=f"{nm} • peluang emas {g['arah']} {pr}% (+ tren searah) ⚠️ • {sisa}")
                elif g and bt["hubungan"] == "berlawanan":
                    # tetap SATU arah (permintaan pengguna 10 Okt: "cukup naik atau turun"): arah petunjuk, persen jujur
                    row.update(persen=bt["persen"], status="lemah", **angka_tren,
                               teks=f"{nm} • peluang emas {g['arah']} {bt['persen']}% (tren berlawanan) ⚠️ • {sisa}")
                elif not g:                                       # tanpa petunjuk: arah = tren 4 jam (55–56%, lemah)
                    row.update(arah=bt["arah"], persen=bt["persen"], status="lemah", bukti=bt["bukti"], **angka_tren,
                               dasar="Tren emas 4 jam (berita tanpa petunjuk)",
                               teks=f"{nm} • peluang emas {bt['arah']} {bt['persen']}% (tren 4 jam) ⚠️ • {sisa}")
        out.append(row)
        if len(out) >= MAKS_DAFTAR:
            break
    return out


JANGKA_H = (10, 30, 60, 180, 300, 600, 900, 1800, 3600)


def label_h(h: int) -> str:
    return f"{h} dtk" if h < 60 else f"{h // 60} mnt" if h < 3600 else "1 jam"


def jangka(dasar: str | None, arah: str | None) -> dict | None:
    """Berlaku sampai kapan (pra_aset.json["jangka"], research/pra_jangka.py): X = jangka terpanjang (mulai 10 dtk)
    yang ketepatannya tetap ≥ 55%; setelah X: arah & persen di jangka berikutnya (≈ 50:50 bila 45–55%)."""
    p = (DATA.get("jangka") or {}).get(dasar or "")
    if not p or not arah:
        return None
    x = 10
    for h in JANGKA_H:
        v = p.get(str(h))
        if not v or v["benar"] < 55:
            break
        x = h
    lanjut = next((h for h in JANGKA_H if h > x and p.get(str(h))), None)
    out = {"sampai": x, "teks_sampai": f"1–{label_h(x)}" if x < 60 else f"s/d {label_h(x)}"}
    if lanjut:
        b = p[str(lanjut)]["benar"]
        naik = arah == "naik"
        if b >= 55:
            ket = f"{'▲ NAIK' if naik else '▼ TURUN'} {b:.0f}%"
        elif b <= 45:
            ket = f"{'▼ TURUN' if naik else '▲ NAIK'} {100 - b:.0f}%"
        else:
            ket = "≈ 50:50"
        out.update(setelah=lanjut, teks_setelah=f"setelah {label_h(lanjut)} {ket}")
    out["rinci"] = " • ".join(f"{label_h(int(h))} {v['benar']:.0f}%" for h, v in p.items() if int(h) >= 2)
    return out


def menit_info(title: str) -> dict | None:
    """Arah SETELAH beberapa menit (research/pra_menit.py → pra_aset.json["menit"]): bila emas di detik 2 sudah bergerak
    ≥ $0,50, arah itu masih sama di menit 5 pada X% rilis (per jenis berita, n ≥ 15; selain itu semua berita)."""
    mn = (DATA.get("menit") or {}).get("0.5") or {}
    g = next((g for k, g in GRUP if k in title), "SEMUA")
    g = "ISM" if g == "ISM Jasa" else g
    r = mn.get(g) or {}
    if not r.get("300") or r["300"]["n"] < 15:
        g, r = "SEMUA", mn.get("SEMUA") or {}
    if not r.get("300"):
        return None
    rinci = " • ".join(f"{label_h(int(h))} {r[h]['sama']:.0f}%" for h in ("60", "300", "900", "3600") if h in r)
    return {"persen": round(r["300"]["sama"]), "grup": g,
            "teks": f"1–5 mnt: ikuti arah detik 2 ({r['300']['sama']:.0f}%)",
            "singkat": f"Setelah rilis: emas gerak ≥ $0,50 di detik 2 → ikuti arahnya s/d 5 mnt ({r['300']['sama']:.0f}%)",
            "bukti": (f"setelah rilis: bila emas di detik 2 sudah bergerak ≥ $0,50, arah itu masih sama di {rinci} "
                      f"(n {r['300']['n']}, {'semua berita' if g == 'SEMUA' else g}, 2010–2026)").replace(".", ",")}


STATUS_SATU = {"teruji": "✅ Teruji", "belum terbukti": "⚠️ Belum terbukti", "tren searah": "⚠️ Belum terbukti",
               "lemah": "⚠️ Lemah", "tutup kertas": "✅ Teruji tutup kertas"}
TERUJI = ("teruji", "tutup kertas")


def dasar_singkat(dasar: str | None) -> str:
    """"CPI • minyak WTI saja" → "minyak WTI" (nama berita sudah ada di baris utama)."""
    s = (dasar or "").split(" • ", 1)[-1]
    return s.removeprefix("+ ").removesuffix(" saja")


def ringkas_terbaru(teks: str) -> list[str]:
    """Baris 🔄/🎲/🧮/⚖️ dari _cpi_detik.terbaru → poin pendek (14 Okt, "dipersingkat poin-poin saja"):
    "📊 Konsensus (11:15 WIB): m/m 0,6% • …", "🎲 Kalshi atas/bawah perkiraan: m/m 18/34% • …",
    satu "🧮 Tersirat vs konsensus: y/y 3,71 vs 3,6 → condong DI ATAS • inti y/y 2,43 vs 2,5 → inti jarang DI BAWAH (3/33)"."""
    out, tersirat = [], []
    for x in (b.strip() for b in teks.split("\n")):
        if not x:
            continue
        if m := re.match(r"🔄 Data terbaru (.+?): perkiraan (.*)", x):
            out.append(f"📊 Konsensus ({m.group(1)}): {m.group(2)}")
        elif x.startswith("🎲 Kalshi: "):
            out.append("🎲 Kalshi atas/bawah perkiraan: " + re.sub(r" di atas ([\d,]+)% / di bawah ([\d,]+)%", r" \1/\2%",
                                                                  x.removeprefix("🎲 Kalshi: ")))
        elif m := re.match(r"🧮 (.+?) tersirat ([\d,]+)% vs perkiraan ([\d,]+)% → (.*)", x):
            ekor = re.sub(r"\(dulu (\d+) dari (\d+) rilis\)", r"(\1/\2)", m.group(4)).replace(" perkiraan", "")
            ekor = ekor.replace("y/y condong", "condong").replace("inti m/m jarang", "inti jarang")
            tersirat.append(f"{m.group(1)} {m.group(2)} vs {m.group(3)} → {ekor}")
        else:
            out.append(x)
    if tersirat:
        i = next((k for k, x in enumerate(out) if x.startswith("⚖️")), len(out))
        out.insert(i, "🧮 Tersirat vs konsensus: " + " • ".join(tersirat))
    return out


_F_ATURAN = Path(__file__).with_name("aturan_pra.json")
ATURAN = json.loads(_F_ATURAN.read_text(encoding="utf-8")) if _F_ATURAN.exists() else {}


def cari_teks() -> str:
    """Poin 🧾 berita TANPA tebakan (14 Okt 2026, "cari aturan sebelum rilis dan pasang"): hasil pencarian aturan gabungan
    1–3 syarat, tutup kertas per tahun (research/aturan_pra.py → aturan_pra.json) — tidak lolos → tetap ≈ 50%."""
    h = ATURAN.get("hasil") or {}
    if not h.get("n"):
        return ("⚪ Tutup kertas: belum ada petunjuk teruji sebelum rilis (≈ 50%) • ≤ 6 jam sebelum rilis arah dari tren "
                "emas 4 jam (55–56%, lemah)")
    n_rilis = f"{ATURAN.get('n_rilis', 0):,}".replace(",", ".")
    return (f"🧾 Tutup kertas: ±40 ribu aturan sebelum rilis dicari di {n_rilis} rilis → di tahun berikutnya hanya "
            f"benar {100 * h['benar']:.0f}% (n {h['n']}; selalu-NAIK {100 * h['dasar']:.0f}%, acak {100 * ATURAN['acak_rata']:.0f}–"
            f"{100 * ATURAN['acak_p95']:.0f}%) → belum ada tebakan, ≈ 50% • ≤ 6 jam sebelum rilis: tren emas 4 jam (55–56%, lemah)")


def kons_teks(k: dict) -> str:
    return f"📊 Konsensus: {k['f']}" + (f" • sebelumnya {k['p']}" if k.get("p") else "")


def tambah_orang(s: dict, sent: dict | None) -> None:
    """Poin 👥 sentimen orang (_sentimen.py, INFO — diuji tidak menambah ketepatan) disisipkan sebelum poin "Setelah rilis"."""
    pn = (sent or {}).get("poin") if isinstance(sent, dict) else None
    if not pn or not isinstance(s.get("poin"), list):
        return
    i = next((k for k, x in enumerate(s["poin"]) if x.startswith("Setelah rilis")), len(s["poin"]))
    s["poin"].insert(i, pn)
    s["bukti"] = "\n".join("• " + x for x in s["poin"])


def satu(row: dict) -> dict:
    """SATU baris untuk berita berikutnya (aplikasi 4.31, permintaan pengguna: "cukup news berikutnya naik atau turun"):
    "CPI ▼ TURUN 56% (1–10 dtk) ⚠️ • 4 hari lagi". Tanpa arah (belum ada petunjuk & > 6 jam) → kapan arah muncul.
    10 Okt (permintaan "singkat jelas padat, langsung ke intinya"): keterangan menit pindah ke detail; detail = 2 baris
    (status + LAMA/BARU + dasar; aturan setelah rilis) menggantikan daftar angka per detik/per jangka."""
    out = {k: row.get(k) for k in ("title", "nama", "time", "arah", "persen", "status", "sisa")}
    # 14 Okt 2026 (permintaan pengguna "di bawah XAU selalu tampil persentase; hide/show dipersingkat poin-poin saja:
    # tutup kertas, konsensus, survei orang, dll"): detail = daftar poin "• …" (aplikasi menampilkan bukti saat diketuk)
    mi = menit_info(row.get("title") or "")
    # ⏱️ baris langsung per detik di aplikasi (13 Okt 2026, pengguna: "persentase berubah setiap detik hingga menit XX,
    # menggantikan jeda XAU"): angka uji per detik (CPI: tutup kertas aturan tersaring) + arah menit
    if row.get("per_detik"):
        out["per_detik"] = {k: round(v) for k, v in row["per_detik"].items() if v is not None}
    if mi:
        out["menit_pct"] = mi["persen"]
    lj = DATA.get("lanjut") or {}                         # ⚡ 4.39: arah LIVE ≥ $0,50 di detik 1/2 → bertahan s/d detik 10
    g_ = next((g for k, g in GRUP if k in (row.get("title") or "")), "SEMUA")
    r2 = lj.get(f"{g_}|2|0.5|10") or lj.get("SEMUA|2|0.5|10")
    if r2:
        r1 = lj.get(f"{g_}|1|0.5|10") or {}
        out["lanjut"] = {"2": round(r2["tetap"]), "1": round(r1["tetap"]) if r1.get("tetap") else None, "n": r2["n"]}
    if row.get("arah"):
        naik = row["arah"] == "naik"
        tanda = "" if row.get("status") in TERUJI else " ⚠️"
        j = jangka(row.get("dasar"), row["arah"]) or {"teks_sampai": row.get("teks_sampai") or "1–10 dtk"}
        out["teks"] = (f"{row['nama']} {'▲ NAIK' if naik else '▼ TURUN'} {row['persen']}% ({j['teks_sampai']}){tanda}"
                       f" • {row['sisa']}")
        uji = [f"{STATUS_SATU.get(row.get('status'), '⚠️ Belum terbukti')}: {row['persen']}% ({j['teks_sampai']})"]
        if row.get("lama") is not None and row.get("baru") is not None:
            uji.append(f"dulu {row['lama']}% • sejak Okt 2021 {row['baru']}%")
        dasar = dasar_singkat(row.get("dasar"))
        tr = row.get("tren") or {}
        if tr.get("hubungan") in ("sepakat", "berlawanan") and not dasar.startswith("Tren"):
            dasar += " + tren 4 jam " + ("searah" if tr["hubungan"] == "sepakat" else "berlawanan")
        if dasar:
            uji.append(f"dasar: {dasar}")
        baris = [" • ".join(uji)]
        if row.get("peringatan"):                          # CPI: tebakan TURUN saat tren naik / Kalshi core berlawanan
            baris.append(f"Lemah karena {row['peringatan'].split(' (')[0]}")   # angka rinci ada di poin 🧮
        if (row.get("terbaru") or {}).get("teks"):         # 13 Okt: konsensus/Kalshi/y/y terbaru + persen rilis serupa
            baris += ringkas_terbaru(row["terbaru"]["teks"])
            out["terbaru"] = row["terbaru"]
        elif row.get("kons"):
            baris.append(kons_teks(row["kons"]))
        out["jangka"] = j
    else:
        # selalu ada persen (14 Okt): tanpa petunjuk teruji = ≈ 50%, jujur; arah tren 4 jam muncul ≤ 6 jam sebelum rilis
        out["teks"] = f"{row['nama']} ⚪ ≈50% (arah muncul ≤ {TREN_JAM} jam sebelum rilis) • {row['sisa']}"
        baris = [cari_teks()]
        if row.get("kons"):
            baris.append(kons_teks(row["kons"]))
    tk = tutup_kertas(row)
    if tk:
        baris.insert(1, tk)
    if mi:
        baris.append(mi["singkat"])
    out["poin"] = baris
    out["bukti"] = "\n".join("• " + x for x in baris)
    a = allin(row)
    if a:
        out["allin"] = a
    return out


def kripto_teks() -> str:
    """13 Okt (pengguna "setelah itu ETH dan BTC"): tebakan CPI kuat juga diuji di kripto (research/kripto_cpi.py, spread
    asli Exness) → info di bukti 💥; emas tetap terbaik (lebih sering untung)."""
    k = (_cpi_detik.DATA.get("allin") or {}).get("kripto") or {}
    e, b = k.get("ETH") or {}, k.get("BTC") or {}
    if not e or not b:
        return ""
    return (f"\n₿ Kripto (CPI kuat, sejak 2022, spread asli Exness, HMR 1:200): ETH arah detik 2 {e['d2']}%, lentur "
            f"+${e['lentur']:.0f}/$100 (untung {e['untung']}% rilis, habis {e['mc']}×) • BTC {b['d2']}%, +${b['lentur']:.0f} "
            f"(untung {b['untung']}%, habis {b['mc']}×) — emas tetap terbaik")


def allin(row: dict) -> dict | None:
    """💥 Modal kecil + lot maksimal (permintaan pengguna 13 Okt 2026: masuk 1 dtk sebelum rilis, modal kecil siap hilang,
    untung berlipat bila arah 1–5 dtk benar). HANYA CPI: research/cpi_allin2.py (tick Exness, tutup kertas, vs arah acak)
    → cpi_detik.json["allin"]. Tebakan kuat → masuk & tutup detik 2; ⚠️ lemah → JANGAN (sumber margin call). Info saja,
    tanpa order. Env CPI_ALLIN=0 mematikan."""
    if row.get("title") in _ppi_wti.JUDUL and row.get("arah") and row.get("status") in TERUJI:
        # 13 Okt: PPI-WTI diuji dengan cara yang sama (research/ppi_wti.py) → jauh lebih lemah dari CPI
        lv = (_ppi_wti.DATA.get("allin_lentur") or {})
        x2 = lv.get("200") or {}
        return {"kuat": False, "teks": "💥 Modal kecil PPI: lemah — utamakan CPI",
                "bukti": (f"Uji sejak 2022 (lentur, {x2.get('n_baru')} rilis): untung di {x2.get('untung_baru')}% rilis; per "
                          f"modal $100 1:100 +${(lv.get('100') or {}).get('rata', 0):.0f}, 1:200 +${x2.get('rata', 0):.0f}, "
                          f"1:500 +${(lv.get('500') or {}).get('rata', 0):.0f} (modal habis {(lv.get('500') or {}).get('mc', 0)}×) • "
                          "2016–2021 rugi • detik 1 ≈ acak (48%) — CPI jauh lebih kuat (+$30, 72%)")}
    d = _cpi_detik.DATA.get("allin") or {}
    if os.environ.get("CPI_ALLIN", "1") == "0" or not d or row.get("title") not in _cpi_detik.JUDUL \
            or not row.get("arah"):
        return None
    lv = d.get("lev") or {}
    if row.get("lemah_jenis") == "yoyc" and (_cpi_detik.DATA.get("yoyc") or {}).get("naik"):
        # 13 Okt (izin "Pasang!"): inti jarang di bawah → BUY lentur rugi rata-rata (research/cpi_skenario.py bagian E)
        y = _cpi_detik.DATA["yoyc"]["naik"]
        b, bb, bs = y["semua"], y["baru"], (_cpi_detik.DATA["yoyc"].get("naik_biasa") or {}).get("semua") or {}
        usd = lambda v: f"{'+' if v >= 0 else '−'}${abs(v):.1f}".replace(".", ",")  # noqa: E731
        return {"kuat": False, "keluar": "detik2",
                "teks": "💥 Modal kecil: JANGAN (inti jarang di bawah) • bila tetap masuk BUY: TUTUP detik 2, jangan lentur",
                "bukti": (f"Situasi ini (konsensus inti y/y lebih tinggi dari tersirat) {b['n']} rilis 2016–2026: BUY t−1 dtk "
                          f"tutup detik 2 {usd(b['d2'])}/oz, lentur {usd(b['lentur'])}/oz, terburuk lentur "
                          f"{usd(b['terburuk_lentur'])} • sejak Okt 2021 ({bb['n']} rilis): detik 2 {usd(bb['d2'])}, lentur {usd(bb['lentur'])} • "
                          f"tebakan NAIK biasa: detik 2 {usd(bs.get('d2', 0))}, lentur {usd(bs.get('lentur', 0))} • leverage maks "
                          "1:200 bila tetap masuk")}
    if row.get("status") not in TERUJI:
        w = d.get("lemah") or {}
        return {"kuat": False, "teks": "💥 Modal kecil: JANGAN (tebakan ⚠️ lemah)",
                "bukti": f"Tebakan lemah sejak 2022 untung di {w.get('untung_baru')}% rilis • 1:2000 modal habis "
                         f"{w.get('mc_2000')} dari {w.get('n_baru')} rilis"}
    sisi = "BUY" if row["arah"] == "naik" else "SELL"
    th = d.get("th_2026") or [0, 0]
    le = d.get("lentur") or {}
    # 13 Okt (pengguna: "ya boleh lentur", tutup 1–10 dtk): detik 2 rugi → tutup, untung → tahan s/d detik 10
    lv_ = le.get("lev") or lv

    def rp(k: str) -> str:
        x = lv_.get(k) or {}
        habis = f" (modal habis {x['mc']}×)" if x.get("mc") else ""
        return f"1:{k} +${x.get('rata', 0):.0f}{habis}"
    if le:
        teks = f"💥 Modal kecil: {sisi} 1 dtk sebelum rilis → detik 2 rugi TUTUP, untung tahan s/d detik 10"
        uji = (f"Teruji 2022–2026 (lentur): untung di {le.get('untung_baru')}% rilis ({d.get('n_baru')} rilis; tutup detik 2 "
               f"saja {d.get('untung_baru')}%) • rata-rata per modal $100: {rp('100')}, {rp('200')}, {rp('500')}, {rp('1000')}")
    else:
        teks = f"💥 Modal kecil: {sisi} 1 dtk sebelum rilis → TUTUP detik 2"
        uji = (f"Teruji 2022–2026: untung di {d.get('untung_baru')}% rilis ({d.get('n_baru')} rilis; 2026: {th[0]}/{th[1]}) "
               f"• rata-rata per modal $100: {rp('200')}, {rp('500')}, {rp('2000')}")
    sp = d.get("spike") or {}
    if sp:
        # 13 Okt (pengguna: "detik pertama bisa berlawanan lalu habis padahal prediksi benar"): research/cpi_spike.py
        uji += (f"\n⚡ Detik 1 melawan tebakan di {sp['d1_lawan']}/{sp['n_baru']} rilis ({sp['d1_lawan_benar']} akhirnya benar) • "
                f"lonjakan melawan terbesar saat arah benar {sp['mae_benar_maks_pct']:.3f}% harga → lot ≤ 1:{sp['saran_lev']} tidak "
                f"pernah habis karena lonjakan itu (habis bila melawan {100 / sp['saran_lev']:.1f}%); 1:1000 habis "
                f"{next((t['habis_benar'] for t in sp['tabel'] if t['lev'] == 1000), 0)}× padahal arah benar").replace(".", ",")
    # 13 Okt (pengguna: "selalu cek forecast, konsensus, dll agar persentase berubah up to date"): hasil modal kecil untuk
    # SITUASI hari ini (research/cpi_konflik.py: y/y tersirat / Kalshi inti berlawanan vs sepakat), dari data terbaru
    sit = (row.get("terbaru") or {}).get("situasi")
    ka = ((_cpi_detik.DATA.get("konflik") or {}).get("allin") or {})
    kunci = {"keduanya": "yoy", "yoy": "yoy", "inti": "inti", "sepakat": "sepakat"}.get(sit or "")
    sb, sm = ((ka.get(kunci) or {}).get("baru") or {}), ((ka.get("semua") or {}).get("baru") or {})
    if kunci and sb.get("n", 0) >= 10 and sm.get("n"):
        x5, a5 = sb.get("500") or {}, sm.get("500") or {}
        lemah = (x5.get("untung") or 0) < (a5.get("untung") or 0)
        ket = {"yoy": "y/y tersirat berlawanan", "inti": "Kalshi inti berlawanan", "sepakat": "petunjuk lain sepakat"}[kunci]
        if lemah:
            teks = (f"💥 Modal kecil: {sisi} 1 dtk sebelum rilis (lentur) • ⚖️ situasi sekarang untung {x5['untung']}% "
                    f"(biasa {a5['untung']}%)")
        def usd(v: float | None) -> str:
            v = v or 0.0
            return f"{'+' if v >= 0 else '−'}${abs(v):.0f}"
        uji = (f"⚖️ Situasi sekarang ({ket}): sejak Okt 2021 untung di {x5.get('untung')}% rilis ({sb['n']} rilis) • per "
               f"$100 1:200 {usd((sb.get('200') or {}).get('rata'))}, 1:500 {usd(x5.get('rata'))} (habis "
               f"{x5.get('habis', 0)}×), 1:1000 {usd((sb.get('1000') or {}).get('rata'))} (habis "
               f"{(sb.get('1000') or {}).get('habis', 0)}×)" + (f" — lebih lemah dari biasa ({a5['untung']}%)" if lemah else "")
               + "\n" + uji)
    out = {"kuat": True, "arah": sisi, "lev": 200, "keluar": "lentur" if le else "detik2", "teks": teks}
    if sp:
        out.update(lev_tabel=[{k: t[k] for k in ("lev", "untung", "rata", "habis", "habis_benar", "n", "lama_rata") if k in t}
                              for t in sp["tabel"] if t["lev"] in (100, 200, 500, 1000)],
                   saran_lev=sp["saran_lev"], bertahap=sp.get("bertahap"))
    return {**out,
            "bukti": (f"{uji}\n"
                      f"⚠️ {d.get('gagal')} GAGAL (untung {d.get('untung_lama')}%) • tutup detik 1 = rugi • Exness HMR: order "
                      "15 mnt sebelum–90 dtk sesudah berita, leverage emas dibatasi 1:100–1:1000 (cek di akun) • pakai "
                      "akun terpisah berisi modal kecil saja" + kripto_teks())}


def tandai(persiapan: dict, daftar_: list, now: datetime | None = None) -> None:
    """Arah 1–10 dtk yang SAMA dipasang di SETIAP kartu berita yang belum rilis (c["arah_detik"]) → aplikasi memakai satu
    kerangka di semua tempat (hitung mundur, alarm, tab News) dan tidak lagi menampilkan angka "1 jam". Kartu lain di
    waktu rilis yang sama (core CPI, CPI tahunan, …) diberi ganda=True supaya tidak tampil dobel. Tanpa petunjuk:
    "arah 1–10 dtk muncul ≤ 6 jam sebelum rilis" (tidak dikarang)."""
    now = now or datetime.now(timezone.utc)
    per = {r["time"]: r for r in daftar_}
    grup: dict[str, list] = {}
    for k in ("berita", "mendatang"):
        for c in persiapan.get(k) or []:
            if isinstance(c, dict) and c.get("time") and not c.get("released") \
                    and datetime.fromisoformat(c["time"]) > now:
                grup.setdefault(c["time"], []).append(c)
    for t0, cs in grup.items():
        r = per.get(t0)
        info = None
        if r and r.get("arah"):
            info, judul = r, r["title"]
        else:
            kand = [(tebak_kartu(c), c) for c in cs]
            ada = sorted([(g["persen"], -i, g, c) for i, (g, c) in enumerate(kand) if g], key=lambda x: x[:2])
            if ada:
                _, _, g, c = ada[-1]
                nm = _prediksi.nama(c["title"] if not g["dasar"].startswith("Pengangguran") else NFP_HARI[0])
                info, judul = {**g, "nama": SATU_NAMA.get(nm, nm)}, c["title"]
            else:
                judul = sorted((URUT.index(c["title"]) if c["title"] in URUT else 99, i, c["title"])
                               for i, c in enumerate(cs))[0][2]
        nama_semua = []
        for c in sorted(cs, key=lambda c: URUT.index(c["title"]) if c["title"] in URUT else 99):
            n_ = SATU_NAMA.get(_prediksi.nama(c["title"]), _prediksi.nama(c["title"]))
            if n_ not in nama_semua:
                nama_semua.append(n_)
        nm = (info or {}).get("nama") or " & ".join(nama_semua[:2])   # mis. "PPI & Retail Sales" (rilis bersamaan)
        utama_dipakai = False
        mi = menit_info(judul)
        for c in cs:
            ganda = c["title"] != judul or utama_dipakai
            utama_dipakai = utama_dipakai or not ganda
            if info:
                j = jangka(info.get("dasar"), info["arah"]) or {"teks_sampai": info.get("teks_sampai") or "1–10 dtk"}
                c["arah_detik"] = {"arah": info["arah"], "persen": info["persen"], "status": info["status"],
                                   "ganda": ganda,
                                   "teks": f"{nm}: emas {info['arah']} {info['persen']}% ({j['teks_sampai']})"}
            else:
                c["arah_detik"] = {"arah": None, "persen": None, "status": "acak", "ganda": ganda,
                                   "teks": f"{nm}: arah 1–10 dtk muncul ≤ {TREN_JAM} jam sebelum rilis"}
            if mi:
                c["arah_detik"]["menit"] = mi["teks"]
            if info:
                selaras(c, info, nm)


def selaras(c: dict, info: dict, nm: str) -> None:
    """14 Okt (pengguna: "isi tab News ada data yang tidak sesuai"): detail kartu memuat angka lain untuk berita yang sama
    (prediksi 1 jam "🥈 Kuat", 🎲 Kalshi × reaksi 63%, perkiraan hari H) padahal baris utama memakai arah teruji detik
    (mis. "CPI: emas naik 54% ⚠️ lemah"). Blok pertama detail kini = arah yang dipakai aplikasi + alasannya; blok lain diberi
    label "info tambahan, bukan arah utama" dan badge peringkat 1 jam yang bertentangan dibuang."""
    lemah = info.get("status") not in TERUJI
    utama = {"judul": "⏱️ Arah yang dipakai aplikasi",
             "teks": f"{nm}: emas {info['arah'].upper()} {info['persen']}% ({info.get('teks_sampai') or '1–10 dtk'})"
                     + (" ⚠️ lemah" if lemah else " ✅ teruji"),
             "catatan": (f"Lemah karena {info['peringatan']} • " if info.get("peringatan") else "")
                        + (f"dulu {info['lama']}% • sejak Okt 2021 {info['baru']}% • " if info.get("lama") is not None
                           and info.get("baru") is not None else "")
                        + "angka lain di bawah ini hanya info tambahan"}
    p = c.get("prediksi")
    if isinstance(p, dict):
        lain = [b for b in p.get("detail") or [] if isinstance(b, dict) and b.get("judul") != "Dasar angka"]
        for b in lain:
            if str(b.get("judul", "")).startswith("🎲"):
                b["judul"] = "🎲 Info pasar (Kalshi × reaksi 1 menit, bukan arah utama)"
            elif str(b.get("judul", "")).startswith("📈") and "bukan arah utama" not in b["judul"]:
                b["judul"] += " • prediksi 1 jam (bukan arah utama)"
                for lbl in ("⚡ Sangat kuat: ", "🥈 Kuat: ", "🥉 Cukup: ", "Biasa: "):
                    b["teks"] = str(b.get("teks", "")).replace(lbl, "")
        p["detail"] = [utama] + lain
    h = c.get("hari_h")
    if isinstance(h, dict) and h.get("label"):
        h["label"] = "🎯 Info pasar hari H (Kalshi × reaksi 1 menit, bukan arah utama)"


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
    kuat = sorted(((tebak_kartu(x) or {}).get("persen", 0), -i) for i, x in enumerate(ber))
    c = ber[-kuat[-1][1]] if kuat and kuat[-1][0] else (ber[0] if ber else sama[0])
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
    cpi = next((x for x in sama if x.get("title") in _cpi_detik.JUDUL), None) if _cpi_detik.aktif() else None
    if cpi is not None:                                    # CPI: aturan tutup kertas IDX|K menggantikan varian lama
        c, g, r = cpi, cpi.get("cpi_detik"), None
        out.update(title=c["title"], judul=f"⏱️ Entry 1 dtk sebelum {_prediksi.nama(c['title'])} • {c.get('when', '')}")
        out.pop("detik", None)
        if g:
            u = _cpi_detik.DATA.get("uji") or {}
            naik = g["arah"] == "naik"
            pdk = g.get("per_detik") or u.get("per_detik") or {}
            out.update(arah=g["arah"], status=g.get("status", "tutup kertas"), bukti=g["bukti"],
                       teks=f"XAU {'NAIK ▲' if naik else 'TURUN ▼'} • benar {g['persen']}% ({g.get('teks_sampai')}) "
                            f"{'✅' if g.get('status', 'tutup kertas') in TERUJI else '⚠️'}",
                       kecil=" • ".join(f"{h} dtk {v:.0f}%" for h, v in pdk.items()
                                        if v is not None and h in ("1", "2", "3", "5", "10")) + f" ({g.get('n') or u.get('n_rilis')} rilis, tutup kertas 2016–2026)")
        else:
            out.update(status="acak", arah=None, teks="XAU • arah belum bisa ditebak (konsensus indeks & Kalshi belum "
                                                      "memberi arah) ⚪",
                       kecil="≈ 50:50 di detik 2–10", bukti="aturan CPI tutup kertas belum punya petunjuk untuk rilis ini")
    k = kepastian(c["title"])
    if k:
        out["kepastian"] = k
    if tren is not None:                                   # tren diambil sekali per permintaan (cache Supabase)
        asli, memo = tren, {}
        tren = lambda s_: memo["v"] if "v" in memo else memo.setdefault("v", asli(s_))  # noqa: E731
    sisa = datetime.fromisoformat(c["time"]) - now
    if tren is not None and sisa <= timedelta(hours=TREN_JAM):
        bt = baris_tren(c["title"], (b.get("arah_emas") if r else None) if cpi is None else None, tren(sisa))
        if bt:
            out["tren"] = bt
    elif tren is not None:
        out["tren_nanti"] = f"➕ Tren emas 4 jam tampil ≤ {TREN_JAM} jam sebelum rilis"
    persiapan["pra"] = out
    try:
        dl = daftar(persiapan, now, tren)
        if dl:
            persiapan["pra_daftar"] = dl
            persiapan["pra_satu"] = satu(dl[0])
            tambah_orang(persiapan["pra_satu"], persiapan.get("sentimen"))
            tandai(persiapan, dl, now)
    except Exception:  # noqa: BLE001 - daftar opsional
        pass
