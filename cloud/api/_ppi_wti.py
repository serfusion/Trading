"""⛽ PPI: arah emas dari minyak WTI bulan acuan — aturan pra-registrasi research/riset_inflasi.py (11 Okt 2026), lolos
semua kriteria + verifikasi adversarial 13 Okt (research/ppi_wti_cek.py) → angka uji cloud/api/ppi_wti.json
(research/ppi_wti.py).

Aturan: rata-rata WTI 5 observasi s/d tanggal 13 bulan acuan (bulan sebelum rilis PPI) vs bulan sebelumnya naik ≥ 5% → PPI
cenderung DI ATAS konsensus → emas TURUN; turun ≥ 5% → emas NAIK; selain itu tidak menebak (≈ 50:50). Uji 2016–2026: arah
lonjakan menit 1 69% (lama 66% / sejak Okt 2021 72%), detik 1 48% (≈ acak), detik 2 55%, detik 5–60 64–69%.

Data live berlapis: FRED API (env FRED_API_KEY) → FRED CSV publik (_perang.fred_rows) → ETF USO Twelve Data (cadangan, ≈ WTI).
Cache baris Supabase 'ppi_wti' 6 jam. Env PPI_WTI=0 mematikan (kartu PPI kembali tanpa tebakan). INFORMASI saja, tanpa order.

🔗 SETELAH CPI (13 Okt 2026, izin pengguna "Pasang! … otomatis jika sudah keluar"; research/ppi_dasar.py tahap 4 →
ppi_wti.json["cpi_ppi"]): bila CPI bulan acuan sama sudah terbit ≤ 4 hari sebelum PPI (kartu "Core CPI m/m" rilis dengan
Act & perkiraan), tebakan WTI diperbarui otomatis: kejutan inti CPI SEARAH tebakan (inti di atas ↔ emas TURUN) 74% (lama 60 /
baru 79), CPI inti SESUAI 82% (lama 50 / baru 100), BERLAWANAN 44% (lama 43 / baru 44) → ⚠️ lemah. Env PPI_CPI=0 mematikan.
"""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

JUDUL = ("PPI m/m", "Core PPI m/m")
DATA = json.loads((Path(__file__).with_name("ppi_wti.json")).read_text(encoding="utf-8"))
FRED = "https://api.stlouisfed.org/fred/series/observations?"
TTL = timedelta(hours=6)
BULAN = ("Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des")


def aktif() -> bool:
    return os.environ.get("PPI_WTI", "1") != "0" and bool(DATA)


def _bulan_lalu(d: date) -> date:
    return date(d.year - 1, 12, 1) if d.month == 1 else date(d.year, d.month - 1, 1)


def jendela13(obs: list[tuple[date, float]], ref: date) -> float | None:
    """Rata-rata 5 observasi terakhir s/d tanggal 13 bulan ref (sama dengan research/riset_inflasi.jendela13)."""
    batas = ref + timedelta(days=12)
    x = [v for d, v in obs if d <= batas][-5:]
    akhir = [d for d, _ in obs if d <= batas]
    if len(x) < 5 or (batas - akhir[-1]).days >= 7:
        return None
    return sum(x) / 5


def _fred_api(key: str, mulai: date, opener=None) -> list[tuple[date, float]]:
    q = {"series_id": "DCOILWTICO", "api_key": key, "file_type": "json", "observation_start": mulai.isoformat()}
    with (opener or urllib.request.urlopen)(urllib.request.Request(FRED + urllib.parse.urlencode(q)), timeout=8) as r:
        obs = json.load(r)["observations"]
    return [(date.fromisoformat(o["date"]), float(o["value"])) for o in obs if o["value"] not in (".", "")]


def minyak(store, now: datetime, opener=None, env=None) -> tuple[list[tuple[date, float]], str]:
    """(observasi harian, sumber). Cache Supabase 'ppi_wti' 6 jam; gagal semua → ([], alasan)."""
    env = os.environ if env is None else env
    cache = {}
    if store is not None:
        try:
            cache = store.get_state("ppi_wti") or {}
        except Exception:  # noqa: BLE001
            cache = {}
    if cache.get("t") and now - datetime.fromisoformat(cache["t"]) < TTL and cache.get("obs"):
        return [(date.fromisoformat(d), v) for d, v in cache["obs"]], cache.get("src", "cache")
    mulai = (now - timedelta(days=100)).date()
    obs, src = [], ""
    key = env.get("FRED_API_KEY", "")
    if key:
        try:
            obs, src = _fred_api(key, mulai, opener), "FRED"
        except Exception:  # noqa: BLE001 - kunci salah / jaringan → lapis berikutnya
            obs = []
    if not obs:
        try:
            import _perang
            obs, src = _perang.fred_rows(days=100), "FRED"
        except Exception:  # noqa: BLE001
            obs = []
    if not obs and env.get("TWELVEDATA_API_KEY") and store is not None:
        try:
            q = urllib.parse.urlencode({"symbol": "USO", "interval": "1day", "outputsize": 80, "order": "ASC",
                                        "apikey": env["TWELVEDATA_API_KEY"]})
            with (opener or urllib.request.urlopen)(urllib.request.Request(
                    "https://api.twelvedata.com/time_series?" + q), timeout=8) as r:
                vals = json.load(r).get("values") or []
            seen = {}
            for v in vals:                                   # Twelve Data harian bisa memuat Sabtu/Minggu ganda
                d = date.fromisoformat(v["datetime"][:10])
                if d.weekday() < 5:
                    seen[d] = float(v["close"])
            obs, src = sorted(seen.items()), "USO"
        except Exception:  # noqa: BLE001
            obs = []
    if obs and store is not None:
        try:
            store.save_state({"t": now.isoformat(), "src": src, "obs": [[d.isoformat(), v] for d, v in obs]}, "ppi_wti")
        except Exception:  # noqa: BLE001
            pass
    return obs, (src or "minyak tidak terbaca")


def tebak(t0: datetime, obs: list[tuple[date, float]], src: str = "FRED") -> dict | None:
    ny = (t0 - timedelta(hours=5)).date()                    # tanggal rilis (08:30 New York)
    ref = _bulan_lalu(date(ny.year, ny.month, 1))
    a, b = jendela13(obs, ref), jendela13(obs, _bulan_lalu(ref))
    if a is None or b is None:
        return None
    d = (a / b - 1) * 100
    if abs(d) < DATA.get("ambang", 5.0):
        return None
    naik = d < 0                                             # minyak turun → PPI di bawah → emas NAIK
    lj, pdk = DATA["lonjakan"], DATA["per_detik"]
    cp = DATA.get("cpi_ppi") or {}
    # 14 Okt (pengguna "perbaiki data tidak sesuai"): angka AUDIT 128 rilis resmi (docs/AUDIT_DATA.md) PER ARAH tebakan —
    # dulu 69% (data lama tanpa 8 rilis salah); tebakan TURUN (minyak naik) hanya 55% → ⚠️ lemah
    pa = (cp.get("per_arah") or {}).get("naik" if naik else "turun")
    if pa:
        lj = pa
    nama_src = "minyak WTI" if src != "USO" else "ETF minyak USO (cadangan)"
    teks_d = lambda h: f"{pdk[h]:.0f}%".replace(".", ",") if pdk.get(h) is not None else "–"  # noqa: E731
    lemah = bool(pa) and not naik and lj["semua"]["persen"] < 60
    out = {"arah": "naik" if naik else "turun", "persen": round(lj["semua"]["persen"]),
            "status": "lemah" if lemah else "tutup kertas",
            "teks_sampai": "lonjakan menit 1", "lama": round(lj["lama"]["persen"]), "baru": round(lj["baru"]["persen"]),
            "n": lj["semua"]["n"], "dasar": "PPI • minyak WTI", "tanpa_tren": True, "per_detik": pdk,
            "minyak": {"ref": ref.isoformat(), "rata": round(a, 2), "lalu": round(b, 2), "ubah": round(d, 1), "src": src},
            "bukti": (f"{nama_src} 5 hari s/d 13 {BULAN[ref.month - 1]} ${a:.2f} vs bulan sebelumnya ${b:.2f} ({d:+.1f}%) → PPI "
                      f"cenderung {'DI BAWAH' if naik else 'DI ATAS'} perkiraan → emas {'NAIK' if naik else 'TURUN'} • uji "
                      f"2016–2026: arah lonjakan menit 1 {lj['semua']['persen']:.0f}% ({lj['semua']['n']} rilis), lama "
                      f"{lj['lama']['persen']:.0f}% / sejak Okt 2021 {lj['baru']['persen']:.0f}% • detik 1 {teks_d('1')} "
                      f"(≈ acak), detik 2 {teks_d('2')}, detik 5 {teks_d('5')}").replace(".", ",")}
    if pa:
        out["bukti"] = out["bukti"].replace("uji 2016–2026: arah", f"uji 128 rilis resmi, tebakan {out['arah'].upper()} saja: arah")
    if lemah:                                                # kurva per detik lama = semua arah → tidak berlaku untuk TURUN
        out["per_detik"] = {}
        out["bukti"] = out["bukti"].split(" • detik 1")[0] + " • detik 1–10 untuk tebakan TURUN di bawah 50% (audit)"
        out["peringatan"] = (f"tebakan TURUN (minyak naik) dulu hanya benar {lj['semua']['persen']:.0f}% (sejak 2024 "
                             f"{lj['s2024']['persen']:.0f}%)").replace(".", ",")
    return out


def _num(v) -> float | None:
    try:
        return float(str(v).replace("%", "").replace(",", ".").strip())
    except (TypeError, ValueError):
        return None


def _cpi_bulan_sama(t: datetime, t0: datetime) -> bool:
    """CPI bulan acuan SAMA dengan PPI t0 = CPI terbit di bulan kalender yang sama, sebelum PPI (research/ppi_dasar.py:
    CPI bulan acuan sama sudah terbit sebelum PPI). Cek ALFRED 2014–2026: 74/75 pasangan cocok, 0 salah pasang; jarak CPI→PPI
    1–17 hari (Feb 2026: 14, Jan 2026: 17) — batas hari tetap (dulu 4 hari) melewatkan 11 dari 75 pasangan."""
    return t < t0 and (t.year, t.month) == (t0.year, t0.month)


def _ci(c: dict) -> dict | None:
    if not isinstance(c, dict) or c.get("title") != "Core CPI m/m" or not c.get("time") or c.get("released") is False:
        return None
    a, f = _num(c.get("actual")), _num(c.get("forecast"))
    if a is None or f is None:
        return None
    return {"actual": a, "forecast": f, "s": (a > f) - (a < f), "time": c["time"]}


def simpan_cpi(calendar: list, store) -> dict | None:
    """Simpan hasil CPI inti terakhir dari kalender ke baris Supabase 'ppi_cpi' (dipanggil tiap GET & tiap jam oleh tick)."""
    ci = None
    for c in calendar or []:
        x = _ci(c)
        if x and (ci is None or x["time"] > ci["time"]):
            ci = x
    if ci and store is not None:
        try:
            if (store.get_state("ppi_cpi") or {}) != ci:
                store.save_state(ci, "ppi_cpi")
        except Exception:  # noqa: BLE001
            pass
    return ci


def cpi_inti(persiapan: dict, t0: datetime, calendar: list | None = None, store=None) -> dict | None:
    """Kejutan inti CPI bulan acuan sama sebelum PPI t0: kartu persiapan → kalender pekan ini → simpanan Supabase 'ppi_cpi'.
    15 Okt 2026 (bug): kartu CPI hilang 6 jam setelah rilis (_persiapan.KEEP_AFTER) sedangkan PPI terbit 1–17 hari kemudian
    → hasil CPI tidak terbaca dan PPI kembali ke angka tanpa CPI (74% → 55%)."""
    for c in list(persiapan.get("berita") or []) + list(calendar or []):
        x = _ci(c)
        if x and _cpi_bulan_sama(datetime.fromisoformat(x["time"]), t0):
            simpan_cpi([c], store)
            return x
    if store is not None:
        try:
            ci = store.get_state("ppi_cpi") or {}
        except Exception:  # noqa: BLE001
            ci = {}
        if ci.get("time") and ci.get("s") is not None and _cpi_bulan_sama(datetime.fromisoformat(ci["time"]), t0):
            return ci
    return None


def status_sel(benar: float, n: int, lama=None, n_lama: int = 0, baru=None, n_baru: int = 0) -> str:
    """Status jujur satu sel (aturan audit 15 Okt, sama dengan _pra_aset.status_arah; LAMA/BARU hanya menentukan bila
    sub-periodenya ≥ 5 rilis): < 52% atau LAMA/BARU < 50% → "acak" (arah TIDAK ditampilkan — dulu "PPI NAIK 43%" tampil,
    arah yang lebih sering salah); ≥ 60% & n ≥ 20 & LAMA/BARU ≥ 55% → "tutup kertas" (✅); ≥ 55% → "belum terbukti"
    (sampel kecil, mis. 9/10); selain itu "lemah"."""
    lm = lama if lama is not None and n_lama >= 5 else None
    br = baru if baru is not None and n_baru >= 5 else None
    if benar < 52 or (lm is not None and lm < 50) or (br is not None and br < 50):
        return "acak"
    if benar >= 60 and n >= 20 and (lm is None or lm >= 55) and (br is None or br >= 55):
        return "tutup kertas"
    return "belum terbukti" if benar >= 55 else "lemah"


def pakai_cpi(g: dict | None, ci: dict | None) -> dict | None:
    cp = DATA.get("cpi_ppi") or {}
    if not g or not ci or not cp or os.environ.get("PPI_CPI", "1") == "0":
        return g
    emas_cpi = -ci["s"]                                       # inti CPI di atas → emas turun
    tb = 1 if g["arah"] == "naik" else -1
    rel = "sesuai" if ci["s"] == 0 else ("sepakat" if emas_cpi == tb else "berlawanan")
    x = cp.get(rel) or {}
    if x.get("semua") is None:
        return g
    # 15 Okt 2026 (pengguna: "aplikasi stuck TURUN 74%"): angka sel MENCAMPUR tebakan NAIK & TURUN (sepakat: NAIK 7/7,
    # TURUN 7/12 dan detik 2 hanya 4/12) → pakai angka ARAH yang ditebak bila tersedia (research/ppi_dasar.cpi_ppi).
    xa = (x.get("per_arah") or {}).get(g["arah"]) or {}
    per_arah = xa.get("semua") is not None and xa.get("n_semua", 0) >= 5
    if per_arah:
        x = xa
    ket = {"sepakat": "searah tebakan", "sesuai": "sesuai perkiraan", "berlawanan": "BERLAWANAN dengan tebakan"}[rel]
    arah_c = "DI ATAS" if ci["s"] > 0 else ("DI BAWAH" if ci["s"] < 0 else "SESUAI")
    pct = lambda v: "–" if v is None else f"{v:.0f}%"           # noqa: E731
    d2 = f"; detik 2 {pct(x.get('d2'))}" if per_arah and x.get("d2") is not None else ""
    awal = (f"🔗 CPI inti {ci['actual']:g}% vs perkiraan {ci['forecast']:g}% ({arah_c}) → {ket} • tebakan "
            f"{g['arah'].upper() if per_arah else 'PPI-WTI'} dalam situasi ini dulu benar {x['semua']:.0f}% ({x['n_semua']} "
            f"rilis; lama {pct(x.get('lama'))} / sejak Okt 2021 {pct(x.get('baru'))}{d2})").replace(".", ",")
    out = {**g, "persen": round(x["semua"]), "lama": round(x["lama"]) if x.get("lama") is not None else None,
           "baru": round(x["baru"]) if x.get("baru") is not None else None, "n": x["n_semua"],
           "cpi_inti": {**ci, "hubungan": rel, **({"d2": x.get("d2")} if per_arah else {})},
           "bukti": awal + " • " + g["bukti"]}
    # 15 Okt malam (simulasi menyeluruh): dulu sel BERLAWANAN tetap menampilkan arah minyak "PPI NAIK 43%" (lebih sering
    # salah) dan sel 9/10 rilis berlabel ✅ teruji → kini aturan audit yang sama dengan berita lain (status_sel)
    st = status_sel(x["semua"], x["n_semua"], x.get("lama"), x.get("n_lama", 0), x.get("baru"), x.get("n_baru", 0))
    if st == "acak":
        tebak_cpi = "TURUN" if ci["s"] > 0 else "NAIK" if ci["s"] < 0 else None
        out.update(arah=None, acak=True, status="acak",
                   alasan=(f"minyak → emas {g['arah'].upper()}" + (f", CPI inti {arah_c} → emas {tebak_cpi}" if tebak_cpi
                                                                   else f", CPI inti {arah_c}")
                           + f"; tebakan {g['arah'].upper()} seperti ini dulu hanya benar {x['semua']:.0f}% "
                             f"({x['n_semua']} rilis) → ≈ 50:50").replace(".", ","))
        return out
    out["status"] = st
    if rel == "berlawanan":
        out["peringatan"] = "kejutan inti CPI kemarin berlawanan dengan tebakan minyak"
    elif st != "tutup kertas":
        out["peringatan"] = (f"tebakan {g['arah'].upper()} di situasi ini dulu {x['semua']:.0f}% dari {x['n_semua']} rilis"
                             + (f", detik 2 {pct(x.get('d2'))}" if x.get("d2") is not None else "")
                             + (" (sampel kecil)" if x["n_semua"] < 20 else "")).replace(".", ",")
    else:                                                    # CPI sudah mendukung → angka situasi ini yang berlaku
        out.pop("peringatan", None)
    return out


def attach(persiapan: dict, store, now: datetime | None = None, opener=None, env=None, calendar=None) -> None:
    """c["ppi_wti"] = tebakan (atau None) di setiap kartu PPI yang belum rilis (≤ 31 hari)."""
    if not isinstance(persiapan, dict) or not aktif():
        return
    now = now or datetime.now(timezone.utc)
    simpan_cpi(calendar or [], store)                      # 15 Okt: hasil CPI inti disimpan selagi masih di kalender
    kartu = [c for k in ("berita", "mendatang") for c in persiapan.get(k) or [] if isinstance(c, dict)
             and c.get("title") in JUDUL and c.get("time") and not c.get("released")]
    kartu = [c for c in kartu if now < datetime.fromisoformat(c["time"]) <= now + timedelta(days=31)]
    if not kartu:
        return
    obs, src = minyak(store, now, opener, env)
    for c in kartu:
        t0 = datetime.fromisoformat(c["time"])
        g = tebak(t0, obs, src) if obs else None
        h = pakai_cpi(g, cpi_inti(persiapan, t0, calendar, store))
        if h and h.get("acak"):                            # petunjuk berlawanan → tanpa arah, alasan tetap dikirim
            c["ppi_wti"], c["ppi_wti_acak"] = None, h
        else:
            c["ppi_wti"] = h
            c.pop("ppi_wti_acak", None)
