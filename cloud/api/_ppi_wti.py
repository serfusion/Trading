"""⛽ PPI: arah emas dari minyak WTI bulan acuan — aturan pra-registrasi research/riset_inflasi.py (11 Okt 2026), lolos
semua kriteria + verifikasi adversarial 13 Okt (research/ppi_wti_cek.py) → angka uji cloud/api/ppi_wti.json
(research/ppi_wti.py).

Aturan: rata-rata WTI 5 observasi s/d tanggal 13 bulan acuan (bulan sebelum rilis PPI) vs bulan sebelumnya naik ≥ 5% → PPI
cenderung DI ATAS konsensus → emas TURUN; turun ≥ 5% → emas NAIK; selain itu tidak menebak (≈ 50:50). Uji 2016–2026: arah
lonjakan menit 1 69% (lama 66% / sejak Okt 2021 72%), detik 1 48% (≈ acak), detik 2 55%, detik 5–60 64–69%.

Data live berlapis: FRED API (env FRED_API_KEY) → FRED CSV publik (_perang.fred_rows) → ETF USO Twelve Data (cadangan, ≈ WTI).
Cache baris Supabase 'ppi_wti' 6 jam. Env PPI_WTI=0 mematikan (kartu PPI kembali tanpa tebakan). INFORMASI saja, tanpa order.
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
    nama_src = "minyak WTI" if src != "USO" else "ETF minyak USO (cadangan)"
    teks_d = lambda h: f"{pdk[h]:.0f}%".replace(".", ",") if pdk.get(h) is not None else "–"  # noqa: E731
    return {"arah": "naik" if naik else "turun", "persen": round(lj["semua"]["persen"]), "status": "tutup kertas",
            "teks_sampai": "lonjakan menit 1", "lama": round(lj["lama"]["persen"]), "baru": round(lj["baru"]["persen"]),
            "n": lj["semua"]["n"], "dasar": "PPI • minyak WTI", "tanpa_tren": True, "per_detik": pdk,
            "minyak": {"ref": ref.isoformat(), "rata": round(a, 2), "lalu": round(b, 2), "ubah": round(d, 1), "src": src},
            "bukti": (f"{nama_src} 5 hari s/d 13 {BULAN[ref.month - 1]} ${a:.2f} vs bulan sebelumnya ${b:.2f} ({d:+.1f}%) → PPI "
                      f"cenderung {'DI BAWAH' if naik else 'DI ATAS'} perkiraan → emas {'NAIK' if naik else 'TURUN'} • uji "
                      f"2016–2026: arah lonjakan menit 1 {lj['semua']['persen']:.0f}% ({lj['semua']['n']} rilis), lama "
                      f"{lj['lama']['persen']:.0f}% / sejak Okt 2021 {lj['baru']['persen']:.0f}% • detik 1 {teks_d('1')} "
                      f"(≈ acak), detik 2 {teks_d('2')}, detik 5 {teks_d('5')}").replace(".", ",")}


def attach(persiapan: dict, store, now: datetime | None = None, opener=None, env=None) -> None:
    """c["ppi_wti"] = tebakan (atau None) di setiap kartu PPI yang belum rilis (≤ 31 hari)."""
    if not isinstance(persiapan, dict) or not aktif():
        return
    now = now or datetime.now(timezone.utc)
    kartu = [c for k in ("berita", "mendatang") for c in persiapan.get(k) or [] if isinstance(c, dict)
             and c.get("title") in JUDUL and c.get("time") and not c.get("released")]
    kartu = [c for c in kartu if now < datetime.fromisoformat(c["time"]) <= now + timedelta(days=31)]
    if not kartu:
        return
    obs, src = minyak(store, now, opener, env)
    for c in kartu:
        c["ppi_wti"] = tebak(datetime.fromisoformat(c["time"]), obs, src) if obs else None
