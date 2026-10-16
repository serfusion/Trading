"""🧩 Dokumen "ARSITEKTUR konfluensi_85" (unggahan pengguna 16 Okt 2026) diterapkan MENYELURUH — dengan ANGKA UJI ASLI.

Pengguna: "tolong kamu baca dan terapkan semuanya secara menyeluruh supaya bisa 75 persen winrate". Dokumen mengusulkan 5 metode
(palang perkiraan, Kalshi, petunjuk rantai pasok, sapuan likuiditas, rilis bersamaan) + 6 rezim dengan klaim 77–88%; angka JSON
dokumen tidak pernah dihitung dari data (skrip risetnya tanpa data). research/konfluensi_85.py menghitung kelima vektor per rilis
dari data asli (tick Exness 1.627 rilis 2016–2026) dengan aturan rezim dokumen APA ADANYA → konfluensi_85.json.

Modul ini menghitung kelima vektor LIVE untuk berita berikutnya (pra_satu) dengan definisi yang SAMA dengan riset:
  palang    Z = (Forecast − Previous) / MAD 12 rilis terakhir (konfluensi_85.json["mad"]); Z ≥ +0,6 → ▲, Z ≤ −0,6 → ▼
            (pengangguran/klaim dibalik)
  Kalshi    kartu.kalshi (CPI m/m, NFP, core PCE): P(di atas perkiraan) ≥ 65% → ▼, P(di bawah/sama) ≥ 65% → ▲
  petunjuk  arah pra_satu dari petunjuk teruji (CPI indeks/Kalshi, PPI ← minyak, petunjuk berita lain; bukan tren 4 jam saja)
  sapuan    D = (harga − EMA 16×15 mnt) / ATR20 15 mnt (Twelve Data, cache 'pra_tren', ≤ 6 jam sebelum rilis);
            D ≥ +0,7 → ▼, D ≤ −0,7 → ▲
  bersamaan ≥ 2 berita USD dampak tinggi di jam yang sama (kalender pekan ini) — varian A dokumen; varian B = ≥ 2 kelompok
→ rezim dokumen + angka ujinya: poin 🧩 & 🧪 di detail baris XAU, pra_satu["konfluensi"].

Gerbang timpa dokumen (bagian 4) dipakai apa adanya, tetapi dengan status HASIL UJI: arah pra_satu hanya ditimpa bila rezim
berstatus "teruji" (≥ 75% di detik 3, Wilson ≥ 70%, p ≤ 0,01, LAMA & BARU ≥ 5 rilis & ≥ 60%) DAN lebih tinggi dari arah yang ada.
Hasil uji 16 Okt 2026: TIDAK ADA rezim teruji → arah & persen utama tidak berubah (info saja). Env KONFLUENSI_85=0 mematikan.
Tanpa order.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

_F = Path(__file__).with_name("konfluensi_85.json")
try:
    DATA: dict = json.loads(_F.read_text(encoding="utf-8")) if _F.exists() else {}
except Exception:  # noqa: BLE001 - tanpa data: modul diam
    DATA = {}

# sama dengan research/news_data.TIER1 / INVERSE dan research/konfluensi_85.UTAMA / KALSHI
TIER1 = {"NFP": ["Non-Farm Employment Change"], "CPI": ["CPI m/m", "Core CPI m/m", "CPI y/y"],
         "PPI": ["PPI m/m", "Core PPI m/m"], "FOMC": ["Federal Funds Rate", "FOMC Statement"],
         "RETAIL": ["Retail Sales m/m", "Core Retail Sales m/m"], "PCE": ["Core PCE Price Index m/m"],
         "GDP": ["Advance GDP q/q"], "ISM": ["ISM Manufacturing PMI", "ISM Services PMI"], "CLAIMS": ["Unemployment Claims"]}
INVERSE = {"Unemployment Rate", "Unemployment Claims"}
UTAMA = {"CPI": ["CPI m/m"], "PPI": ["PPI m/m"], "NFP": ["Non-Farm Employment Change"], "RETAIL": ["Retail Sales m/m"],
         "ISM": ["ISM Manufacturing PMI", "ISM Services PMI"], "FOMC": ["Federal Funds Rate"],
         "PCE": ["Core PCE Price Index m/m"], "GDP": ["Advance GDP q/q"], "CLAIMS": ["Unemployment Claims"]}
KALSHI_JUDUL = {"CPI": "CPI m/m", "NFP": "Non-Farm Employment Change", "PCE": "Core PCE Price Index m/m"}
GRUP = [("Non-Farm", "NFP"), ("Unemployment Rate", "NFP"), ("Average Hourly", "NFP"), ("ADP", "ADP"), ("CPI", "CPI"),
        ("PPI", "PPI"), ("Retail", "RETAIL"), ("PCE", "PCE"), ("GDP", "GDP"), ("Federal Funds", "FOMC"), ("FOMC", "FOMC"),
        ("JOLTS", "JOLTS"), ("ISM", "ISM"), ("Claims", "CLAIMS")]
NAMA = {"KONFLUENSI_PENUH_NAIK": "PENUH NAIK", "KONFLUENSI_PENUH_TURUN": "PENUH TURUN",
        "SAPUAN_PUCUK_V_SHAPE_NAIK": "SAPUAN PUCUK (turun → V naik)", "SAPUAN_DASAR_V_SHAPE_TURUN": "SAPUAN DASAR (naik → V turun)",
        "KONFLUENSI_MENENGAH_NAIK": "MENENGAH NAIK", "KONFLUENSI_MENENGAH_TURUN": "MENENGAH TURUN"}
KLAIM_V = {"SAPUAN_PUCUK_V_SHAPE_NAIK": 85.7, "SAPUAN_DASAR_V_SHAPE_TURUN": 78.6}   # klaim dokumen pola V (fase 2)
KLAIM = {"KONFLUENSI_PENUH_NAIK": 87.5, "KONFLUENSI_PENUH_TURUN": 86.7, "SAPUAN_PUCUK_V_SHAPE_NAIK": 85.7,
         "SAPUAN_DASAR_V_SHAPE_TURUN": 85.0, "KONFLUENSI_MENENGAH_NAIK": 77.8, "KONFLUENSI_MENENGAH_TURUN": 76.9}  # dokumen
ARAH = {"KONFLUENSI_PENUH_NAIK": "naik", "KONFLUENSI_PENUH_TURUN": "turun", "SAPUAN_PUCUK_V_SHAPE_NAIK": "turun",
        "SAPUAN_DASAR_V_SHAPE_TURUN": "naik", "KONFLUENSI_MENENGAH_NAIK": "naik", "KONFLUENSI_MENENGAH_TURUN": "turun"}
VARIAN = "A_berita"            # dokumen harfiah: ≥ 2 berita di jam yang sama
SAPUAN_JAM = 6                 # sama dengan tren 4 jam (_pra_aset.TREN_JAM): candle 15 mnt diambil ≤ 6 jam sebelum rilis
TERUJI = ("teruji", "tutup kertas")
AWAL = ("👥", "🔗", "Setelah rilis")


def aktif() -> bool:
    return os.environ.get("KONFLUENSI_85", "1") != "0" and bool(DATA.get("varian"))


def _num(v) -> float | None:
    """Sama dengan research/news_data._num ("254K" → 254000, "0.3%" → 0.3, "1,234K" → 1234000)."""
    s = str(v if v is not None else "").strip().replace(",", "")
    m = re.match(r"^([<>]?)(-?\d+(?:\.\d+)?)([KMBT%]?)", s)
    if not m:
        return None
    return float(m.group(2)) * {"K": 1e3, "M": 1e6, "B": 1e9, "T": 1e12}.get(m.group(3), 1.0)


def _k(x: float, d: int = 0) -> str:
    return f"{x:.{d}f}".replace(".", ",")


def _tanda_angka(x: float) -> str:
    r = round(x, 1) + 0.0                                    # −0,04 → "+0,0" (bukan "−0,0")
    return f"{'+' if r >= 0 else '−'}{_k(abs(r), 1)}"


def _ribu(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def grup(title: str) -> str:
    return next((g for k, g in GRUP if k in (title or "")), "SEMUA")


def _waktu(x) -> datetime | None:
    try:
        return datetime.fromisoformat(str(x)).astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def sejam(calendar: list | None, t0: datetime) -> list[dict] | None:
    """Berita USD dampak tinggi di jam rilis yang sama (kalender tab News = High saja, seperti kalender riset).
    None = kalender tidak mencakup waktu itu (berita pekan depan) → bersamaan tidak diketahui."""
    if not calendar:
        return None
    rows = [c for c in calendar if isinstance(c, dict) and _waktu(c.get("time")) == t0]
    if rows:
        return rows
    ts = [w for w in (_waktu(c.get("time")) for c in calendar if isinstance(c, dict)) if w]
    return [] if any(_pekan(w) == _pekan(t0) for w in ts) else None


def _pekan(t: datetime):
    """Minggu kalender ForexFactory (Minggu–Sabtu, jam New York ≈ UTC−4/−5; rilis tidak pernah di tengah malam Minggu)."""
    d = (t - timedelta(hours=4)).date()
    return d - timedelta(days=(d.weekday() + 1) % 7)


def palang(g: str, rows: list[dict]) -> dict | None:
    """Vektor 1: Z palang perkiraan. None = kelompok berita tanpa judul utama di riset."""
    judul = UTAMA.get(g)
    if not judul:
        return None
    r = next((x for x in rows if x.get("title") in judul), None)
    if r is None:
        return {"v": 0.0, "ada": False}
    f, p = _num(r.get("forecast")), _num(r.get("previous"))
    md = ((DATA.get("mad") or {}).get(r["title"]) or {}).get("mad")
    if f is None or p is None or not md:
        return {"v": 0.0, "ada": False, "judul": r["title"]}
    z = (f - p) / md
    s = -1.0 if r["title"] in INVERSE else 1.0
    v = s * (1.0 if z >= 0.6 else -1.0 if z <= -0.6 else 0.0)
    return {"v": v + 0.0, "z": round(z, 2), "ada": True, "judul": r["title"]}


def kalshi(g: str, kartu: list[dict]) -> dict | None:
    """Vektor 2: peluang Kalshi (kartu.kalshi atas/bawah, pecahan 0–1). None = kelompok tanpa pasar Kalshi di riset."""
    judul = KALSHI_JUDUL.get(g)
    if not judul:
        return None
    c = next((c for c in kartu if c.get("title") == judul and isinstance(c.get("kalshi"), dict)), None)
    k = (c or {}).get("kalshi") or {}
    atas, bawah = k.get("atas"), k.get("bawah")
    if not isinstance(atas, (int, float)) or not isinstance(bawah, (int, float)):
        return {"v": 0.0, "ada": False}
    v = -1.0 if atas >= 0.65 else 1.0 if (bawah >= 0.65 or 1 - atas >= 0.65) else 0.0
    return {"v": v, "ada": True, "atas": round(atas * 100), "bawah": round(bawah * 100)}


def petunjuk(ps: dict, persiapan: dict) -> dict:
    """Vektor 3: arah tebakan teruji aplikasi (bukan tren 4 jam saja, bukan cadangan/peluang dasar)."""
    arah = ps.get("arah")
    if arah not in ("naik", "turun"):
        return {"v": 0.0, "ada": False}
    d0 = next((r for r in persiapan.get("pra_daftar") or [] if isinstance(r, dict) and r.get("time") == ps.get("time")), {})
    if str(d0.get("dasar") or "").startswith("Tren"):
        return {"v": 0.0, "ada": False, "tren": True}
    return {"v": 1.0 if arah == "naik" else -1.0, "ada": True}


def sapuan(t: dict | None) -> dict | None:
    """Vektor 4: D = (harga − EMA 4 jam) / ATR20 candle 15 mnt (_pra_aset.ema_atr_m15)."""
    if not isinstance(t, dict):
        return None
    h, e, a = t.get("harga"), t.get("ema16"), t.get("atr20")
    if not all(isinstance(x, (int, float)) for x in (h, e, a)) or a <= 0:
        return None
    d = (h - e) / a
    return {"v": -1.0 if d >= 0.7 else 1.0 if d <= -0.7 else 0.0, "d": round(d, 2), "at": t.get("at")}


def rezim(v_bar: float, v_kalshi: float, v_lead: float, v_sweep: float, ko: bool) -> tuple[str | None, float]:
    """Aturan dokumen apa adanya (= research/konfluensi_85.rezim)."""
    skor = round(1.1 * v_bar + 1.0 * v_kalshi + 1.1 * v_lead + 1.0 * v_sweep, 2)
    if ko and v_sweep <= -1 and v_lead <= -1 and v_bar >= 1:
        return "SAPUAN_PUCUK_V_SHAPE_NAIK", skor
    if ko and v_sweep >= 1 and v_lead >= 1 and v_bar <= -1:
        return "SAPUAN_DASAR_V_SHAPE_TURUN", skor
    if not ko and skor >= 3.2:
        return "KONFLUENSI_PENUH_NAIK", skor
    if not ko and skor <= -3.2:
        return "KONFLUENSI_PENUH_TURUN", skor
    if skor >= 2.0:
        return "KONFLUENSI_MENENGAH_NAIK", skor
    if skor <= -2.0:
        return "KONFLUENSI_MENENGAH_TURUN", skor
    return None, skor


def uji(nama: str | None, varian: str = VARIAN) -> dict:
    return ((DATA.get("varian") or {}).get(varian) or {}).get(nama or "") or {}


def boleh_timpa(o: dict, ps: dict) -> bool:
    """Gerbang dokumen bagian 4: rezim teruji, ≥ 75%, dan lebih baik dari arah yang sudah ada."""
    if not o or o.get("status") != "teruji" or o.get("arah") not in ("naik", "turun"):
        return False
    p = float(o.get("d3") or 0)
    if p < float((DATA.get("ambang") or {}).get("persen", 75.0)):
        return False
    try:
        lama = float(ps.get("persen") or 0)
    except (TypeError, ValueError):
        lama = 0.0
    # GET yang sama memanggil dua kali → arah yang sudah dipasang modul ini dipasang ulang (bukan dibandingkan dengan dirinya)
    return ps.get("sumber") == "konfluensi_85" or ps.get("status") not in TERUJI or p > lama


def _tanda(x: dict | None, nilai: str = "") -> str:
    if not x or not x.get("ada", True) or x.get("v") is None:
        return "–"
    v = x["v"]
    return ("▲" if v > 0 else "▼" if v < 0 else "netral") + (f" ({nilai})" if nilai else "")


def teks_vektor(k: dict) -> str:
    v = k["vektor"]
    z = v.get("palang") or {}
    d = v.get("sapuan") or {}
    ka = v.get("kalshi") or {}
    if k.get("bersamaan") is None:
        ber = "belum diketahui"
    else:
        ber = f"ya ({k['n_berita']} berita)" if k["bersamaan"] else "tidak"
    if d.get("d") is not None:
        sap = _tanda(d, f"D {_tanda_angka(d['d'])}")
    else:
        sap = "– (candle belum ada)" if k.get("sapuan_jendela") else f"– (dihitung ≤ {SAPUAN_JAM} jam sebelum rilis)"
    kal = _tanda(ka, f"atas {ka['atas']}%") if ka.get("ada") else "–"
    pal = _tanda(z, f"Z {_tanda_angka(z['z'])}") if z.get("z") is not None else "–"
    pt = v.get("petunjuk") or {}
    ptk = "– (hanya tren 4 jam)" if pt.get("tren") else _tanda(pt)
    hasil = f"rezim {NAMA[k['rezim']]}" if k.get("rezim") else "tanpa rezim"
    arah_rz = ARAH.get(k.get("rezim") or "")
    if arah_rz and k.get("arah_utama") in ("naik", "turun") and arah_rz != k["arah_utama"]:
        hasil += " (berlawanan dengan arah utama — tidak dipakai)"
    return (f"🧩 5 metode dokumen konfluensi: palang {pal} • Kalshi {kal} • petunjuk {ptk} • sapuan {sap} • bersamaan "
            f"{ber} → skor {_tanda_angka(k['skor'])}: {hasil}")


def teks_uji(k: dict) -> str:
    n_rilis = _ribu(int(DATA.get("n_rilis") or 0))
    rz, o = k.get("rezim"), k.get("uji") or {}
    semua = (DATA.get("varian") or {}).get(VARIAN) or {}
    if not rz:
        lolos = [NAMA.get(r, r) for r, x in semua.items() if isinstance(x, dict) and x.get("status") == "teruji"]
        if lolos:
            return f"🧪 Uji data asli {n_rilis} rilis: rezim lolos " + ", ".join(lolos) + " (rilis ini tidak masuk rezim)"
        return (f"🧪 Uji data asli {n_rilis} rilis (tick Exness {DATA.get('tahun', '2016–2026')}): tak satu rezim pun lolos ≥ 75% "
                f"(klaim dokumen {_k(min(KLAIM.values()), 1)}–{_k(max(KLAIM.values()), 1)}% tidak terbukti) → arah utama tetap")
    n = int(o.get("n") or 0)
    klaim = f"klaim dokumen {_k(KLAIM.get(rz, 0.0), 1)}%"
    if n == 0:
        isi = f"belum pernah terjadi dalam {n_rilis} rilis — tidak bisa diuji"
    elif n < 10:
        benar = round(n * float(o.get("d3") or 0) / 100)
        isi = f"baru muncul {n}× dalam {n_rilis} rilis (benar {benar}/{n} di detik 3) — terlalu sedikit untuk dipercaya"
    else:
        per = []
        if o.get("d3_lama") is not None:
            per.append(f"dulu {_k(o['d3_lama'])}%")
        if o.get("d3_baru") is not None:
            per.append(f"sejak Okt 2021 {_k(o['d3_baru'])}%")
        isi = (f"diuji {n} rilis: arah benar detik 3 {_k(o['d3'])}%" + (f" ({' • '.join(per)})" if per else "")
               + f", untung bersih tahan 1 mnt {_k(o.get('untung60', 0))}%")
    akhir = {"teruji": "✅ teruji, dipakai sebagai arah utama" if k.get("timpa") else "✅ teruji, tetapi arah utama lebih kuat",
             "belum terbukti": "⚠️ belum terbukti, arah utama tetap"}.get(o.get("status"), "tidak lolos, arah utama tetap")
    b = k.get("varian_b") or {}
    tambah = ""
    if b.get("rezim") and b["rezim"] != rz:
        ob = b.get("uji") or {}
        tambah = (f" • varian kelompok: {NAMA[b['rezim']]} {_k(ob.get('d3', 0))}% ({ob.get('n', 0)} rilis, "
                  f"{ob.get('status', 'tidak lolos')})")
    if rz in KLAIM_V and n:                                   # dokumen: fase 1 detik 1–3, lalu V berbalik detik 5–15
        isi += (f" • pola V (searah detik 3 lalu berbalik di detik 10) {_k(float(o.get('v_shape') or 0))}% vs klaim "
                f"{_k(KLAIM_V[rz], 1)}%")
    return f"🧪 Rezim {NAMA[rz]} {isi} • {klaim} → {akhir}" + tambah


def hitung(persiapan: dict, ps: dict, now: datetime, calendar: list | None = None, tren=None) -> dict | None:
    t0 = _waktu(ps.get("time"))
    if t0 is None:
        return None
    g = grup(ps.get("title") or "")
    kartu = [c for k in ("berita", "mendatang") for c in persiapan.get(k) or []
             if isinstance(c, dict) and _waktu(c.get("time")) == t0]
    cal = sejam(calendar, t0)
    rows = cal if cal is not None else kartu                   # palang: kalender High (= riset); kartu bila di luar pekan ini
    pb = palang(g, rows)
    ka = kalshi(g, kartu)
    pt = petunjuk(ps, persiapan)
    sp = None
    jendela = timedelta(0) < t0 - now <= timedelta(hours=SAPUAN_JAM)
    if tren is not None and jendela:
        try:
            sp = sapuan(tren(t0 - now))
        except Exception:  # noqa: BLE001 - tanpa candle: sapuan tidak dihitung
            sp = None
    if cal is None:
        ko, n_ev, n_gr = None, None, None
    else:
        n_ev = len(cal)
        n_gr = len({next((gg for gg, nm in TIER1.items() if c.get("title") in nm), None) for c in cal} - {None})
        ko = n_ev >= 2
    v = [float((x or {}).get("v") or 0.0) for x in (pb, ka, pt, sp)]
    rz, skor = rezim(*v, bool(ko))
    out = {"vektor": {"palang": pb, "kalshi": ka, "petunjuk": pt, "sapuan": sp}, "bersamaan": ko, "n_berita": n_ev,
           "n_kelompok": n_gr, "skor": skor, "rezim": rz, "varian": VARIAN, "uji": uji(rz), "grup": g,
           "sapuan_jendela": jendela, "arah_utama": ps.get("arah"), "dihitung": now.isoformat()}
    if n_gr is not None:
        rb, _ = rezim(*v, n_gr >= 2)
        out["varian_b"] = {"rezim": rb, "uji": uji(rb, "B_kelompok")}
    return out


def _sisip(ps: dict, baris: list[str]) -> None:
    poin = ps.get("poin") if isinstance(ps.get("poin"), list) else []
    poin = [p for p in poin if not str(p).startswith(("🧩", "🧪", "⚡ Fase"))]
    i = next((k for k, x in enumerate(poin) if str(x).startswith(AWAL)), len(poin))
    ps["poin"] = poin[:i] + baris + poin[i:]
    ps["bukti"] = "\n".join("• " + x for x in ps["poin"])


def timpa(persiapan: dict, ps: dict, k: dict) -> None:
    """Hanya bila gerbang dokumen terbuka (rezim teruji): satu arah di baris XAU, daftar, dan semua kartu jam yang sama."""
    o = k["uji"]
    arah, p = o["arah"], round(float(o["d3"]))
    naik = arah == "naik"
    ps.update(arah=arah, persen=p, status="teruji", sumber="konfluensi_85")
    ps["teks"] = f"{ps.get('nama') or k['grup']} {'▲ NAIK' if naik else '▼ TURUN'} {p}% (detik 3) ✅ • {ps.get('sisa') or ''}"
    for r in persiapan.get("pra_daftar") or []:
        if isinstance(r, dict) and r.get("time") == ps.get("time"):
            r.update(arah=arah, persen=p, status="teruji", dasar="Konfluensi 5 metode", teks_sampai="detik 3")
    for key in ("berita", "mendatang"):
        for c in persiapan.get(key) or []:
            if isinstance(c, dict) and c.get("time") == ps.get("time") and isinstance(c.get("arah_detik"), dict):
                c["arah_detik"].update(arah=arah, persen=p, status="teruji",
                                       teks=f"{ps.get('nama') or k['grup']}: emas {arah} {p}% (detik 3)")
    k["timpa"], k["arah_utama"] = True, arah
    v = float(o.get("v_shape") or 0)
    if v >= 65:                                              # dokumen bagian 4: fase 2 V-shape → TP kilat (saran saja)
        balik = "▲ NAIK" if arah == "turun" else "▼ TURUN"
        k["fase"] = (f"⚡ Fase 1 detik 1–3: {'▲ NAIK' if naik else '▼ TURUN'} {p}% → fase 2: pola V {balik} {_k(v)}% "
                     "(uji asli) — ambil untung di detik 3")


def attach(persiapan: dict, now: datetime | None = None, calendar: list | None = None, tren=None) -> None:
    if not isinstance(persiapan, dict) or not aktif():
        return
    ps = persiapan.get("pra_satu")
    if not isinstance(ps, dict) or not ps.get("time"):
        return
    now = now or datetime.now(timezone.utc)
    k = hitung(persiapan, ps, now, calendar, tren)
    if not k:
        return
    k["timpa"] = False
    if boleh_timpa(k["uji"], ps):
        timpa(persiapan, ps, k)
    ps["konfluensi"] = k
    _sisip(ps, [teks_vektor(k), teks_uji(k)] + ([k["fase"]] if k.get("fase") else []))
