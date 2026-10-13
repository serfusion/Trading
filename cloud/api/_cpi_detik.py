"""⏱️ CPI → arah EMAS detik 2–10 setelah rilis, aturan teruji TUTUP KERTAS "IDX|K" (research/cpi_detik.py,
docs/CPI_DETIK.md). Dipasang 11 Okt 2026 atas izin pengguna ("setelah persentase tinggi dan uji validitas dapat
dipercaya PASANG"); menggantikan baris CPI lama (minyak WTI 56% — tutup kertas sejak 2022 hanya 49–51%).

Aturan (sama persis dengan riset):
  1. Konsensus INDEKS CPI tanpa pembulatan dari kalender Nasdaq/Investing.com (core index, CPI index n.s.a.):
       core m/m tersirat − konsensus core m/m; y/y tersirat (indeks NSA / NSA 12 bln lalu) − konsensus y/y;
       headline m/m tersirat (NSA + selisih musiman tahun lalu) − konsensus m/m; tiap selisih |≥ 0,02| → ±1; jumlah tanda.
  2. Bila 0 → pasar Kalshi headline: P(di atas konsensus) − P(di bawah) ≥ 0,10 (atau ≤ −0,10).
  3. Tebakan CPI DI ATAS → emas TURUN; DI BAWAH → emas NAIK. Tanpa petunjuk → tidak menebak (≈ 50:50).
Konsensus m/m & y/y: ForexFactory (kartu) bila sudah terbit, selain itu Nasdaq. Persen = uji tutup kertas detik 2/3/5/10
(cloud/api/cpi_detik.json). Nasdaq lambat (±7 dtk) → cache baris Supabase "cpi_detik" (≥ 24 jam sebelum rilis tiap 3 jam,
≤ 24 jam tiap 30 mnt, ≤ 3 jam tiap 10 mnt). Env CPI_DETIK=0 mematikan. INFORMASI saja, tanpa order. Library standar.

SARINGAN (13 Okt 2026, docs/CPI_SALAH.md; pengguna: "perbaiki" lalu "bukannya bisa di predict malah bagus kenapa
dilewati?"): tebakan emas TURUN (CPI di atas) saat emas tren naik (close harian kemarin > rata-rata 200 hari, Twelve Data
harian, cache baris Supabase "cpi_tren" 6 jam; tidak terbaca → dianggap lemah) ATAU pasar Kalshi core condong berlawanan
(|atas−bawah| ≥ 0,10) TETAP ditampilkan tetapi ⚠️ LEMAH dengan angkanya sendiri (uji["saring"]["lemah"]: detik 1–2
62%; sejak 2024 detik 2 45%). Tebakan lain = angka aturan tersaring (uji["saring"]): detik 2 68% (2016–2026),
sejak Okt 2021 81%, sejak 2024 95%. Patokan tampilan = DETIK 2 (pengguna 13 Okt: "yang penting detik 1–2").
Env CPI_SARING=0 = tanpa pemisahan (angka lama).
"""
from __future__ import annotations

import html
import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

import _core
import _kalshi

_PATH = Path(__file__).resolve().parent / "cpi_detik.json"
DATA = json.loads(_PATH.read_text(encoding="utf-8")) if _PATH.exists() else {}
JUDUL = ("CPI m/m", "Core CPI m/m", "CPI y/y")
URL = "https://api.nasdaq.com/api/calendar/economicevents?date={}"
BULAN = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")
NY_JAM = 4                       # selisih New York (EDT) – UTC minimum; tanggal NY rilis 08:30 = tanggal UTC rilis
DASAR = {"indeks": "CPI • konsensus indeks tanpa pembulatan", "kalshi": "CPI • pasar Kalshi headline"}


def aktif() -> bool:
    return os.environ.get("CPI_DETIK", "1") != "0" and bool(DATA.get("uji"))


def angka(s) -> float | None:
    s = html.unescape(str(s or "")).replace("\xa0", " ").replace(",", "").replace("%", "").strip()
    try:
        return float(s)
    except ValueError:
        return None


def _bulan(t: datetime, k: int) -> str:
    """Bulan acuan − k sebagai 'YYYY-MM' (bulan acuan = bulan sebelum rilis)."""
    m = t.year * 12 + (t.month - 1) - 1 - k
    return f"{m // 12}-{m % 12 + 1:02d}"


def _ref_lalu(seri: str, t: datetime) -> tuple[float | None, float | None]:
    """(m/m, y/y) resmi bulan "sebelumnya" (acuan − 1) untuk mengenali urutan baris m/m vs y/y."""
    tab = DATA.get(seri) or {}
    a, b, c = tab.get(_bulan(t, 1)), tab.get(_bulan(t, 2)), tab.get(_bulan(t, 13))
    if a is None or b is None or c is None:
        return None, None
    return (a / b - 1) * 100, (a / c - 1) * 100


def nasdaq(t0: datetime, opener=None) -> dict:
    """Konsensus/sebelumnya CPI AS dari Nasdaq untuk tanggal rilis t0 (parameter API = tanggal + 1 hari)."""
    q = (t0 + timedelta(days=1)).strftime("%Y-%m-%d")
    req = urllib.request.Request(URL.format(q), headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    with (opener or urllib.request.urlopen)(req, timeout=12) as r:
        rows = (json.load(r).get("data") or {}).get("rows") or []
    rows = [x for x in rows if x.get("country") == "United States"]
    o: dict = {}
    for nama, kunci, seri in (("CPI", "mm", "sa"), ("Core CPI", "core", "core")):
        g = [x for x in rows if x.get("eventName") == nama][:2]
        if len(g) < 2:
            continue
        mm, yy = _ref_lalu(seri, t0)
        p0, p1 = angka(g[0].get("previous")), angka(g[1].get("previous"))
        if mm is not None and p0 is not None and p1 is not None:
            if abs(p1 - mm) + abs(p0 - yy) < abs(p0 - mm) + abs(p1 - yy):
                g = [g[1], g[0]]
        elif p0 is not None and p1 is not None and abs(p0) > abs(p1):
            g = [g[1], g[0]]
        o[f"{kunci}_f"], o[f"{kunci}_p"] = angka(g[0].get("consensus")), angka(g[0].get("previous"))
        yk = "yy" if kunci == "mm" else "core_yy"
        o[f"{yk}_f"], o[f"{yk}_p"] = angka(g[1].get("consensus")), angka(g[1].get("previous"))
    for nama, kunci in (("CPI Index, n.s.a.", "nsa"), ("Core CPI Index", "cidx")):
        g = [x for x in rows if x.get("eventName") == nama]
        if g:
            o[f"{kunci}_f"], o[f"{kunci}_p"] = angka(g[0].get("consensus")), angka(g[0].get("previous"))
    return o


def tanda(v: float | None, batas: float) -> int:
    return 0 if v is None or v != v or abs(v) < batas else (1 if v > 0 else -1)


def indeks(t0: datetime, kons: dict, n: dict) -> dict:
    """Selisih konsensus indeks tersirat − konsensus dibulatkan (IDXc, IDXy, IDXm) + suara."""
    a = DATA.get("ambang", 0.02)
    nsa, sa = DATA.get("nsa") or {}, DATA.get("sa") or {}
    p1 = n.get("nsa_p") if n.get("nsa_p") == n.get("nsa_p") and n.get("nsa_p") else nsa.get(_bulan(t0, 1))
    p12, p13 = nsa.get(_bulan(t0, 12)), nsa.get(_bulan(t0, 13))
    s12, s13 = sa.get(_bulan(t0, 12)), sa.get(_bulan(t0, 13))
    d = {"c": None, "y": None, "m": None}
    ada = lambda *x: all(v is not None and v == v for v in x)  # noqa: E731 - bukan None/NaN
    cf, cp, nf = n.get("cidx_f"), n.get("cidx_p"), n.get("nsa_f")
    if ada(cf, cp, kons.get("core")):
        d["c"] = (cf / cp - 1) * 100 - kons["core"]
    if ada(nf, p12, kons.get("yy")):
        d["y"] = (nf / p12 - 1) * 100 - kons["yy"]
    if ada(nf, p1, p12, p13, s12, s13, kons.get("mm")):
        musim = (p12 / p13 - 1) - (s12 / s13 - 1)
        d["m"] = ((nf / p1 - 1) - musim) * 100 - kons["mm"]
    t = {k: tanda(v, a) for k, v in d.items()}
    s = t["c"] + t["y"] + t["m"]
    return {"selisih": {k: (round(v, 3) if v is not None else None) for k, v in d.items()}, "tanda": t,
            "suara": (s > 0) - (s < 0)}


def kalshi(t0: datetime, kons_mm: float | None, get=_kalshi.fetch, seri: str = "KXCPI") -> dict | None:
    """Kalshi headline (atau core: seri KXCPICORE) event bulan acuan vs konsensus → {"atas", "bawah", "lean"}."""
    if kons_mm is None:
        return None
    y, m = (t0.year, t0.month - 1) if t0.month > 1 else (t0.year - 1, 12)
    ev = f"{seri}-{y % 100:02d}{BULAN[m - 1]}-"
    ms = [x for x in get(seri) if str(x.get("ticker", "")).startswith(ev)]
    sp = _kalshi.split(ms, kons_mm, 0.1) if ms else None
    if not sp:
        return None
    return {"atas": round(sp["atas"], 3), "bawah": round(sp["bawah"], 3), "lean": round(sp["atas"] - sp["bawah"], 3)}


def _ttl(sisa: timedelta) -> timedelta:
    if sisa <= timedelta(hours=3):
        return timedelta(minutes=10)
    return timedelta(minutes=30) if sisa <= timedelta(hours=24) else timedelta(hours=3)


def konsensus_nasdaq(t0: datetime, store, now: datetime, opener=None) -> dict:
    """Nasdaq dengan cache Supabase baris 'cpi_detik' (per waktu rilis)."""
    key = t0.isoformat()
    old = {}
    if store is not None:
        try:
            old = store.get_state("cpi_detik") or {}
        except Exception:  # noqa: BLE001
            old = {}
    c = (old.get("nasdaq") or {}).get(key) or {}
    if c.get("t") and now.timestamp() - c["t"] < _ttl(t0 - now).total_seconds():
        return c.get("data") or {}
    try:
        baru = nasdaq(t0, opener)
    except Exception:  # noqa: BLE001 - Nasdaq opsional; pakai cache lama bila ada
        baru = {}
    # Nasdaq kadang mengosongkan kalender pekan berjalan ("No record found") → nilai lama TIDAK ditimpa; hanya nilai baru
    # yang terisi yang menggantikan. Waktu cache tetap diperbarui supaya permintaan berikutnya tidak menunggu ±7 dtk lagi.
    data = {**(c.get("data") or {}), **{k: v for k, v in baru.items() if v is not None}}
    if store is not None:
        try:
            store.save_state({"nasdaq": {key: {"t": now.timestamp(), "data": data}}}, "cpi_detik")
        except Exception:  # noqa: BLE001
            pass
    return data


def saring_aktif() -> bool:
    return os.environ.get("CPI_SARING", "1") != "0" and bool((DATA.get("uji") or {}).get("saring"))


def tren200(t0: datetime, store, now: datetime, key: str | None = None, feed=None) -> int | None:
    """+1 = close harian emas (Senin–Jumat) terakhir sebelum tanggal rilis (UTC) di atas rata-rata 200 hari bursa, −1 di
    bawah, None tidak terbaca. Twelve Data XAU/USD 1day 300 candle (1 kredit), cache baris Supabase 'cpi_tren' 6 jam."""
    old = {}
    if store is not None:
        try:
            old = store.get_state("cpi_tren") or {}
        except Exception:  # noqa: BLE001
            old = {}
    hari = t0.strftime("%Y-%m-%d")
    if old.get("hari") == hari and old.get("t") and now.timestamp() - old["t"] < 6 * 3600:
        return old.get("nilai")
    try:
        key = key or os.environ.get("TWELVEDATA_API_KEY")
        if feed is None and not key:
            return old.get("nilai") if old.get("hari") == hari else None
        bars = (feed or _core.TwelveData(key, "XAU/USD")).candles(300, "1day")
        per_hari = {b.t.strftime("%Y-%m-%d"): b.c for b in sorted(bars, key=lambda b: b.t)
                    if b.t.weekday() < 5}            # Twelve Data memuat candle Sabtu/Minggu (kadang ganda) → buang
        tutup = [c for h, c in sorted(per_hari.items()) if h < hari]
        if len(tutup) < 200:
            return None
        rata = sum(tutup[-200:]) / 200
        nilai = 1 if tutup[-1] > rata else -1
    except Exception:  # noqa: BLE001 - Twelve Data gagal → pakai cache lama untuk rilis yang sama
        return old.get("nilai") if old.get("hari") == hari else None
    if store is not None:
        try:
            store.save_state({"t": now.timestamp(), "hari": hari, "nilai": nilai, "close": round(tutup[-1], 2),
                              "rata200": round(rata, 2)}, "cpi_tren")
        except Exception:  # noqa: BLE001
            pass
    return nilai


def saring(t0: datetime, g: dict | None, tren_fn, get=_kalshi.fetch) -> str | None:
    """Alasan tebakan TURUN ditandai ⚠️ lemah (None = tebakan kuat / bukan TURUN). tren_fn() → +1/−1/None."""
    if not g or g.get("arah") != "turun" or not saring_aktif():
        return None
    t = tren_fn()
    if t is None:
        return "tren emas 200 hari tidak terbaca"
    if t > 0:
        return "emas sedang tren naik (di atas rata-rata 200 hari)"
    try:
        kc = kalshi(t0, (g.get("konsensus") or {}).get("core"), get, "KXCPICORE")
    except Exception:  # noqa: BLE001
        kc = None
    if kc and kc["lean"] <= -DATA.get("lean", 0.10):
        return (f"pasar Kalshi core condong DI BAWAH perkiraan (di bawah {_pct(kc['bawah'] * 100)}, di atas "
                f"{_pct(kc['atas'] * 100)}), berlawanan dengan tebakan")
    return None


def pakai_saring(g: dict | None, alasan: str | None) -> dict | None:
    """Ganti persen/bukti tebakan dengan angka DETIK 2 aturan tersaring; tebakan yang kena saringan = ⚠️ lemah."""
    if not g or not saring_aktif():
        return g
    sr = (DATA.get("uji") or {})["saring"]
    lm = sr.get("lemah") or {}
    # 13 Okt: kurva SETIAP detik 1–10 + 15 dtk…5 mnt (research/cpi_detik_penuh.py) → persen di aplikasi berubah tiap detik
    pdk = (lm if alasan else sr).get("per_detik_penuh") or (lm if alasan else sr).get("per_detik") or {}
    if alasan:
        g = {**g, "persen": round(lm.get("semua") or 0), "status": "lemah", "peringatan": alasan,
             "lama": round(lm["lama"]) if lm.get("lama") is not None else None,
             "baru": round(lm["baru"]) if lm.get("baru") is not None else None, "n": lm.get("n_rilis"),
             "teks_sampai": "detik 2",
             "bukti": (f"⚠️ Tebakan TURUN lemah: {alasan} • tebakan seperti ini dulu benar detik 1 "
                       f"{_pct(pdk.get('1'))}, detik 2 {_pct(pdk.get('2'))} ({lm.get('n_rilis')} rilis 2016–2026; sejak "
                       f"2024 detik 2 {_pct(lm.get('s2024'))}) • " + g["bukti"])}
    else:
        g = {**g, "persen": round(sr.get("semua") or 0), "lama": round(sr["lama"]) if sr.get("lama") is not None else None,
             "baru": round(sr["baru"]) if sr.get("baru") is not None else None, "n": sr.get("n_rilis"),
             "teks_sampai": "detik 2",
             "bukti": (f"uji tutup kertas detik 2: {_pct(sr.get('semua'))} 2016–2026 ({sr.get('n_rilis')} rilis), sejak "
                       f"Okt 2021 {_pct(sr.get('baru'))}, sejak 2024 {_pct(sr.get('s2024'))}; detik 1 {_pct(pdk.get('1'))} "
                       f"(harga belum bergerak) • " + g["bukti"])}
    g["per_detik"] = pdk
    return g


def _pct(x) -> str:
    return f"{x:.0f}%".replace(".", ",") if x is not None else "–"


def tebak(t0: datetime, cards: list[dict], n: dict, get=_kalshi.fetch) -> dict | None:
    """Arah emas detik 2–10 untuk satu waktu rilis CPI (None = tidak ada petunjuk → ≈ 50:50)."""
    kons = {}
    for k, judul, nk in (("mm", "CPI m/m", "mm_f"), ("core", "Core CPI m/m", "core_f"), ("yy", "CPI y/y", "yy_f")):
        f = next((_kalshi._num(c.get("forecast")) for c in cards if c.get("title") == judul and c.get("forecast")), None)
        kons[k] = f if f is not None else n.get(nk)
    ix = indeks(t0, kons, n)
    u = DATA.get("uji") or {}
    jalur, cpi_arah, rinci = None, 0, ""
    if ix["suara"]:
        jalur, cpi_arah = "indeks", ix["suara"]
        bag = [f"{nm} {'di atas' if t > 0 else 'di bawah'}" for nm, t in
               (("core", ix["tanda"]["c"]), ("tahunan", ix["tanda"]["y"]), ("headline", ix["tanda"]["m"])) if t]
        rinci = "konsensus indeks tersirat: " + ", ".join(bag)
    else:
        try:
            ks = kalshi(t0, kons.get("mm"), get)
        except Exception:  # noqa: BLE001
            ks = None
        lean = (ks or {}).get("lean")
        if lean is not None and abs(lean) >= DATA.get("lean", 0.10):
            jalur, cpi_arah = "kalshi", 1 if lean > 0 else -1
            rinci = (f"Kalshi: di atas {kons['mm']:g}% {_pct(ks['atas'] * 100)}, di bawah {_pct(ks['bawah'] * 100)}"
                     ).replace(".", ",")
    if not jalur:
        return None
    arah = "turun" if cpi_arah > 0 else "naik"
    pd2 = u.get("per_detik_2022") or {}
    # patokan utama (permintaan pengguna 11 Okt): arah LONJAKAN TERBESAR menit pertama (research/lonjakan_uji.py);
    # cadangan: detik 2–10 (research/cpi_detik.py) bila angka lonjakan belum ada di cpi_detik.json
    lj = DATA.get("lonjakan") or {}
    utama = lj if lj.get("semua") is not None else u
    sampai = "lonjakan menit 1" if utama is lj else "2–10 dtk"
    bukti = f"{rinci} → CPI condong DI {'ATAS' if cpi_arah > 0 else 'BAWAH'} perkiraan → emas {arah.upper()} • "
    if utama is lj:
        bukti += (f"uji tutup kertas 2016–2026: lonjakan terbesar menit pertama searah {_pct(lj['semua'])} "
                  f"({lj.get('n_rilis')} rilis; lama {_pct(lj.get('lama'))} / sejak Okt 2021 {_pct(lj.get('baru'))}; "
                  f"sejak 2022 {_pct(lj.get('s2022'))}; puncak rata-rata detik {lj.get('puncak_detik', 0):.0f}) • "
                  f"detik 2–10 {_pct(u.get('semua'))} • ")
    else:
        bukti += (f"uji tutup kertas 2016–2026 benar {_pct(u.get('semua'))} (detik 2–10, {u.get('n_rilis')} rilis; "
                  f"lama {_pct(u.get('lama'))} / sejak Okt 2021 {_pct(u.get('baru'))}; sejak 2022 detik 2 "
                  f"{_pct(pd2.get('2'))}, 10 {_pct(pd2.get('10'))}) • ")
    bukti += (f"detik 1 hanya {_pct((u.get('per_detik') or {}).get('1'))} (harga belum bergerak) • selalu NAIK "
              f"{_pct(utama.get('selalu_naik'))}")
    v = DATA.get("validitas") or {}
    if v.get("p_keluarga_2022") is not None:
        bukti += (f" • koreksi banyak-uji (detik 2–10) p {v['p_keluarga_2022']:.3f} sejak 2022 / "
                  f"{v.get('p_keluarga_2016', 0):.3f} 2016–2026").replace(".", ",")
    return {"arah": arah, "persen": round(utama.get("semua") or 0), "status": "tutup kertas", "dasar": DASAR[jalur],
            "lama": round(utama["lama"]) if utama.get("lama") is not None else None,
            "baru": round(utama["baru"]) if utama.get("baru") is not None else None, "n": utama.get("n_rilis"),
            "teks_sampai": sampai, "tanpa_tren": True, "bukti": bukti, "jalur": jalur,
            "indeks": ix, "konsensus": kons}


def attach(persiapan: dict, store, now: datetime | None = None, opener=None, get=_kalshi.fetch, tren=None) -> None:
    """c["cpi_detik"] = tebakan (atau None) di setiap kartu CPI yang belum rilis (≤ 31 hari)."""
    if not isinstance(persiapan, dict) or not aktif():
        return
    now = now or datetime.now(timezone.utc)
    kartu = [c for k in ("berita", "mendatang") for c in persiapan.get(k) or [] if isinstance(c, dict)
             and c.get("title") in JUDUL and c.get("time") and not c.get("released")]
    waktu: dict[str, list] = {}
    for c in kartu:
        t = datetime.fromisoformat(c["time"])
        if now < t <= now + timedelta(days=31):
            waktu.setdefault(c["time"], []).append(c)
    for i, (t0s, cs) in enumerate(sorted(waktu.items())):
        t0 = datetime.fromisoformat(t0s)
        n = konsensus_nasdaq(t0, store, now, opener) if i == 0 and t0 - now <= timedelta(days=8) else {}
        g = tebak(t0, cs, n, get)
        tren_fn = tren or (lambda t0=t0: tren200(t0, store, now))
        g = pakai_saring(g, saring(t0, g, tren_fn, get))
        for c in cs:
            c["cpi_detik"] = g
