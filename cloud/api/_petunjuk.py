"""🧭 Petunjuk teruji sebelum rilis untuk SEMUA berita besar (blok detail di kartu 🎯).

Permintaan pengguna 10 Okt 2026: "jika ada keakuratan selain Kalshi gabungkan juga, telusuri news yang lain juga, riset
dan uji validitas". research/berita_gabung.py menguji 17 berita × 5 sumber (kejutan bulan lalu, Kalshi, nowcast
Cleveland Fed, GDPNow Atlanta Fed, ADP/klaim/PPI) 2010–2025 tanpa look-ahead → cloud/api/petunjuk.json berisi aturan yang
LOLOS (benar > 50% di periode lama & baru, p < 0,05). Dua angka selalu ditampilkan:
  • ketepatan arah ANGKA (Act di atas/di bawah konsensus), dan
  • ketepatan arah EMAS 1 menit setelah rilis bila mengikuti tebakan itu (lebih rendah: emas tidak selalu searah).
Menggabungkan sumber lemah TIDAK menaikkan ketepatan (cpi_gabung: Kalshi 76% vs gabungan 65–71%), kecuali dua sumber
kuat yang SEPAKAT (Kalshi & kejutan bulan lalu, CPI+core: 80%, n 20) — itu yang ditandai. Info saja, tanpa order.
Memori kejutan terakhir per judul: baris Supabase "petunjuk". Hanya library standar Python.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

_PATH = Path(__file__).resolve().parent / "petunjuk.json"
_DATA = json.loads(_PATH.read_text(encoding="utf-8")) if _PATH.exists() else {}
ATURAN = _DATA.get("aturan") or {}
SEPAKAT_LAIN = _DATA.get("sepakat") or {}       # research/sumber_lain.py: petunjuk lama & sumber lain sepakat
INDEED = "https://raw.githubusercontent.com/hiring-lab/job_postings_tracker/master/US/aggregate_job_postings_US.csv"
SUMBER_TTL = 6 * 3600
# kejutan terakhir yang sudah lewat dari kalender pekan ini (diisi tangan dari laporan resmi; dipakai bila memori kosong)
SEED = {"CPI m/m": {"s": 0, "time": "2026-09-11T12:30:00+00:00"},          # Agu 2026: 0,4% = konsensus 0,4%
        "Core CPI m/m": {"s": 1, "time": "2026-09-11T12:30:00+00:00"}}     # Agu 2026: 0,3% > konsensus 0,2%
SEPAKAT = (16, 20)            # Kalshi & kejutan bulan lalu sepakat (CPI + core CPI 2022–2025): 16 dari 20 benar
NAMA = {"P": "Kejutan bulan lalu (searah)", "-P": "Kejutan bulan lalu (berbalik)", "K": "Pasar Kalshi",
        "K|P": "Kalshi, cadangan kejutan lalu", "G": "GDPNow Atlanta Fed", "WTI": "Minyak WTI bulan acuan",
        "IND": "Lowongan Indeed bulan acuan", "EMP": "Survei karyawan Fed daerah (Empire, Philly)",
        "GA": "Survei aktivitas Fed daerah (Empire, Philly)", "CPI": "Kejutan CPI pekan ini (rilis sebelum PPI)"}
CPI_UNTUK = {"PPI m/m": "CPI m/m", "Core PPI m/m": "Core CPI m/m"}    # research/pra_xau_dalam.py (≤ 10 hari sebelum)
FRED_SERI = {"WTI": ["DCOILWTICO"], "EMP": ["NECDISA066MSFRBNY", "NFBNDIF066MSFRBPHI"],
             "GA": ["GACDFSA066MSFRBPHI", "GACDISA066MSFRBNY"]}
INVERS = ("Unemployment Rate", "Unemployment Claims")      # angka naik = buruk bagi ekonomi


def _num(text) -> float | None:
    import _prarilis
    return _prarilis.num(text)


def ingat(calendar: list, store, now: datetime) -> dict:
    """Memori kejutan terakhir per judul (Act vs konsensus) dari kalender; disimpan di baris 'petunjuk'."""
    state = {}
    if store is not None:
        try:
            state = store.get_state("petunjuk") or {}
        except Exception:  # noqa: BLE001
            state = {}
    mem = {**SEED, **(state.get("mem") or {})}
    import _prarilis
    changed = _prarilis.ingat(mem, calendar, ATURAN)
    if changed and store is not None:
        try:
            store.save_state({**state, "mem": mem}, "petunjuk")
        except Exception:  # noqa: BLE001
            pass
    return mem


def _kata(s: float) -> str:
    return "DI ATAS" if s > 0 else "DI BAWAH"


def _pct(k: int, n: int) -> str:
    return f"{round(k / n * 100)}% ({k}/{n})" if n else "-"


def gdpnow(env: dict) -> float | None:
    """Nowcast GDP terbaru Atlanta Fed (FRED GDPNOW; butuh FRED_API_KEY di env Vercel)."""
    key = (env or {}).get("FRED_API_KEY")
    if not key:
        return None
    import urllib.request
    u = ("https://api.stlouisfed.org/fred/series/observations?series_id=GDPNOW&sort_order=desc&limit=1&file_type=json"
         f"&api_key={key}")
    try:
        with urllib.request.urlopen(u, timeout=6) as r:
            obs = json.load(r).get("observations") or []
        return float(obs[0]["value"]) if obs and obs[0]["value"] != "." else None
    except Exception:  # noqa: BLE001
        return None


def _fred(series: str, key: str, mulai: str) -> list[list]:
    import urllib.request
    u = (f"https://api.stlouisfed.org/fred/series/observations?series_id={series}&observation_start={mulai}"
         f"&file_type=json&api_key={key}")
    with urllib.request.urlopen(u, timeout=8) as r:
        return [[o["date"], float(o["value"])] for o in json.load(r).get("observations") or [] if o["value"] != "."]


def _indeed() -> list[list]:
    import urllib.request
    with urllib.request.urlopen(urllib.request.Request(INDEED, headers={"User-Agent": "xau-signal"}), timeout=8) as r:
        rows = r.read().decode("utf-8").splitlines()[1:]
    out = []
    for line in rows:
        x = line.split(",")
        if len(x) >= 5 and x[4] == "total postings":
            out.append([x[0], float(x[2])])
    return out[-200:]


def sumber(store, now: datetime, env: dict | None) -> dict:
    """Data sumber lain (FRED: WTI & survei Fed daerah; Indeed) — cache baris Supabase 'petunjuk_sumber' 6 jam."""
    old = {}
    if store is not None:
        try:
            old = store.get_state("petunjuk_sumber") or {}
        except Exception:  # noqa: BLE001
            old = {}
    if old.get("t") and now.timestamp() - old["t"] < SUMBER_TTL:
        return old
    data, key = {"t": now.timestamp()}, (env or {}).get("FRED_API_KEY")
    mulai = f"{now.year - 1}-{now.month:02d}-01"
    for kode, seri in FRED_SERI.items():
        if not key:
            break
        for nama in seri:
            try:
                data[nama] = _fred(nama, key, mulai)
            except Exception:  # noqa: BLE001 - sumber opsional
                pass
    try:
        data["INDEED"] = _indeed()
    except Exception:  # noqa: BLE001
        pass
    if len(data) == 1 and old:
        return old
    if store is not None:
        try:
            store.save_state(data, "petunjuk_sumber")
        except Exception:  # noqa: BLE001
            pass
    return data


def _bulan(rows: list, t: datetime) -> float | None:
    """Rata-rata bulan acuan (bulan sebelum rilis) − bulan sebelumnya."""
    y, m = (t.year, t.month - 1) if t.month > 1 else (t.year - 1, 12)
    y0, m0 = (y, m - 1) if m > 1 else (y - 1, 12)
    a = [v for d, v in rows if d[:7] == f"{y}-{m:02d}"]
    b = [v for d, v in rows if d[:7] == f"{y0}-{m0:02d}"]
    return (sum(a) / len(a) - sum(b) / len(b)) if a and b else None


def _naik(rows: list) -> float | None:
    return rows[-1][1] - rows[-2][1] if len(rows) >= 2 else None


def _tanda(v) -> float | None:
    return None if v is None or v == 0 else (1.0 if v > 0 else -1.0)


def tanda_lain(kode: str, title: str, card: dict, data: dict) -> float | None:
    """Tanda tebakan (+1 di atas / −1 di bawah konsensus) sumber lain, aturan sama dengan research/sumber_lain.py."""
    try:
        t = datetime.fromisoformat(card["time"])
    except (KeyError, ValueError, TypeError):
        return None
    if kode == "WTI":
        s = _tanda(_bulan(data.get("DCOILWTICO") or [], t))
    elif kode == "IND":
        s = _tanda(_bulan(data.get("INDEED") or [], t))
    elif kode in ("EMP", "GA"):
        tot = sum(x for x in (_tanda(_naik(data.get(n) or [])) for n in FRED_SERI[kode]) if x)
        s = _tanda(tot)
    else:
        return None
    if s is not None and title in INVERS and kode in ("IND", "EMP"):
        s = -s                                          # data kerja kuat → pengangguran DI BAWAH
    return s


def blok(card: dict, mem: dict, env: dict | None = None, data: dict | None = None) -> dict | None:
    """{"judul", "teks", "catatan", "arah_emas"} untuk satu berita; None bila tidak ada aturan teruji / petunjuk."""
    title = card.get("title") or ""
    rules = ATURAN.get(title) or {}
    if not rules or card.get("released"):
        return None
    tebak, baris = {}, []
    import _prarilis                                   # 15 Okt: kejutan lalu hanya bila memori = rilis sebelumnya (≤ 45 hari)
    m_lalu = mem.get(title) or {}
    s_lalu = m_lalu.get("s") if _prarilis.segar(m_lalu, card.get("time"), title) else None
    pasar = (card.get("hari_h") or {}).get("pasar") or card.get("kalshi") or {}
    lean = None
    if pasar.get("atas") is not None and pasar.get("bawah") is not None:
        lean = pasar["atas"] - pasar["bawah"]
    for kode, st in rules.items():
        s = None
        if kode == "P" and s_lalu:
            s = float(s_lalu)
        elif kode == "-P" and s_lalu:
            s = -float(s_lalu)
        elif kode == "K" and lean is not None and abs(lean) >= 0.10:
            s = 1.0 if lean > 0 else -1.0
        elif kode == "K|P":
            s = (1.0 if lean > 0 else -1.0) if lean is not None and abs(lean) >= 0.10 else (float(s_lalu) if s_lalu else None)
        elif kode == "G":
            g, f = gdpnow(env or {}), _num(card.get("forecast"))
            if g is not None and f is not None and abs(g - f) >= 0.2:
                s = 1.0 if g > f else -1.0
        elif kode in ("WTI", "IND", "EMP", "GA"):
            s = tanda_lain(kode, title, card, data or {})
        elif kode == "CPI" and title in CPI_UNTUK:
            m = mem.get(CPI_UNTUK[title]) or {}
            try:
                umur = (datetime.fromisoformat(card["time"]) - datetime.fromisoformat(str(m.get("time")))).days
            except (KeyError, TypeError, ValueError):
                umur = 99
            s = float(m["s"]) if m.get("s") and 0 <= umur <= 10 else None
        if s is None:
            continue
        tebak[kode] = s
        ek, en = st.get("emas") or (0, 0)
        jenis = "arah XAU 3 dtk" if st.get("jenis") == "xau 3 dtk" else "arah emas 1 mnt"
        baris.append(f"{NAMA.get(kode, kode)}: {_kata(s)} perkiraan • teruji {st.get('tahun', '')} benar "
                     f"{_pct(st['benar'], st['n'])} • {jenis} cocok {_pct(ek, en)}")
    if not tebak:
        if s_lalu == 0 and any(k in rules for k in ("P", "-P")):
            baris.append("Kejutan bulan lalu: sama dengan perkiraan → petunjuk ini tidak memberi arah")
        if not baris:
            return None
        return {"judul": "🧭 Petunjuk teruji sebelum rilis", "teks": "Belum ada petunjuk yang memberi arah",
                "catatan": "\n".join(baris), "arah_emas": None}
    utama = tebak.get("K", tebak.get("K|P", tebak.get("G", next(iter(tebak.values())))))
    sepakat = "K" in tebak and s_lalu and float(s_lalu) == tebak["K"]
    teks = f"Angka condong {_kata(utama)} perkiraan"
    lain = [(kk, kn) for kk, kn in (SEPAKAT_LAIN.get(title) or {}).items()
            if kk.split("&")[0] in tebak and kk.split("&")[1] in tebak
            and tebak[kk.split("&")[0]] == tebak[kk.split("&")[1]]]
    if sepakat:
        teks += f" — Kalshi & kejutan bulan lalu SEPAKAT (historis {_pct(*SEPAKAT)} benar)"
    elif lain:
        kk, (k2, n2) = max(lain, key=lambda x: x[1][0] / max(x[1][1], 1))
        a, b = kk.split("&")
        teks += f" — {NAMA.get(a, a)} & {NAMA.get(b, b)} SEPAKAT (historis {_pct(k2, n2)} benar)"
    elif len(set(tebak.values())) > 1:
        teks += " — petunjuk BERTENTANGAN, pakai yang paling teruji (Kalshi)"
    # arah emas: angka di bawah perkiraan → emas naik (kecuali berita "buruk = naik" seperti pengangguran)
    naik = (utama < 0) != (title in INVERS)
    catatan = "\n".join(baris) + ("\nCatatan: tebakan ARAH ANGKA lebih tepat daripada arah EMAS — emas 1 menit setelah "
                                  "rilis hanya cocok ±55–65% walau angkanya tertebak.")
    return {"judul": "🧭 Petunjuk teruji sebelum rilis", "teks": teks, "catatan": catatan,
            "arah_emas": "naik" if naik else "turun", "tebak": tebak, "kalshi_sepakat": bool(sepakat),
            "sepakat_lain": [k for k, _ in lain]}


def attach(persiapan: dict, calendar: list, store, now: datetime, env: dict | None = None) -> None:
    if not isinstance(persiapan, dict) or not ATURAN:
        return
    kartu = [c for k in ("berita", "mendatang") for c in persiapan.get(k) or [] if isinstance(c, dict)]
    if not any(c.get("title") in ATURAN for c in kartu):
        return
    mem = ingat(calendar, store, now)
    data = sumber(store, now, env)
    for c in kartu:
        b = blok(c, mem, env, data)
        if b:
            c["petunjuk_teruji"] = b
