"""Entry di DETIK pertama setelah berita AS keluar (XAU/USD, data tick) — adakah yang untung konsisten?

python -m research.news_detik download [maks_file]     # unduh tick Dukascopy jam rilis (lambat, bisa dilanjutkan)
python -m research.news_detik download_mundur          # pekerja ke-2: NFP/CPI/FOMC dari ujung daftar
python -m research.news_detik download_btc             # kline 1 detik BTCUSDT Binance di sekitar rilis
python -m research.news_detik                          # uji semua aturan pada tick yang sudah terunduh

Permintaan pengguna (30 Sep 2026): "detik pertama setelah news keluar banyak orang profit; 15 menit setelahnya
biarkan saja; bahkan 1-5 menit akan saya close jika sudah profit". Riset lama (research/news_trade.py) masuk 15 menit
SETELAH rilis (candle M15), jadi detik-detik pertama belum pernah diuji. Di sini dipakai tick BID/ASK Dukascopy
(milidetik, spread asli yang ikut melebar saat berita).

Kalender: ForexFactory 2010 - Jan 2026 (research/news_data.py, dengan actual & forecast) + NFP/CPI Feb-Sep 2026 dari
tanggal rilis FRED + FOMC 2026 (research/eksternal_berita.py; tanpa actual/forecast -> hanya aturan berbasis harga).

Mesin (ditetapkan sebelum melihat hasil):
- t0 = waktu rilis resmi. Harga acuan = mid tick terakhir SEBELUM t0.
- Keputusan dibuat di t0 + d detik (d = 1, 2, 5, 10, 30) dari informasi yang sudah ada di detik itu saja;
  order dieksekusi di tick pertama >= t0 + d + LATENSI (0,5 dtk) pada ASK (BUY) / BID (SELL) + slippage tambahan
  (0 / $0,30 / $1,00 per ons) -> spread berita yang melebar ikut terbayar.
- Arah:
  KEJUTAN  = ikut kejutan Act vs Cons (data lemah untuk USD -> BUY emas), butuh angka Act dalam d detik;
  GERAK    = ikut gerak pertama: mid(t0+d) - acuan >= ambang ($1 / $2 / $3) -> searah; di bawah ambang -> tidak entry;
  LAWAN    = kebalikan GERAK (fade lonjakan);
  STRADDLE = cara "detik pertama" yang umum: Buy Stop & Sell Stop dipasang 5 detik sebelum rilis di acuan +/- $k
             (k = 1, 2, 3); yang tersentuh lebih dulu terisi di tick pertama yang melewati level (gap = slippage
             nyata) + slippage tambahan, yang lain dibatalkan (OCO); tidak tersentuh dalam 60 detik -> batal.
- Keluar (P&L dihitung di BID untuk BUY / ASK untuk SELL = harga tutup yang nyata):
  PENGGUNA = di detik ke-60, 120, 180, 240, 300 setelah entry: tutup bila sudah profit; bila belum, tahan dan tutup
             paksa di 15 menit (aturan yang disebut pengguna);
  TAHAN n  = tutup di 1 / 5 / 15 menit;
  TP x     = tutup begitu profit >= $x (x = 1, 3) dicek tiap tick, paksa 15 menit;
  semua varian juga diuji dengan SL darurat $5 (dicek tiap tick, lebih dulu dari aturan lain).
- Slippage tambahan hanya di entry; saat keluar dipakai harga BID/ASK tick apa adanya (spread asli).
- Hasil dalam $/ons: 0,01 lot XAU = 1 ons -> $1/ons = $1 per 0,01 lot di akun standar (1 sen di akun Cent).
Kriteria "konsisten" (sebelum melihat hasil): rata-rata > 0 di LAMA (< Okt 2021) DAN BARU, >= 60% tahun positif,
t > 2 di semua data, dan tetap > 0 bila slippage dinaikkan ke $0,30 dan latensi ke 2 detik.
"""
from __future__ import annotations

import io
import json
import lzma
import math
import random
import sys
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from .dukascopy import POINT, URL, _decode_ticks
from .eksternal import cache_path
from .event_stats import releases
from .eksternal_berita import FF_END, FOMC_2026, FRED_RELEASE, _fred_dates, _ny
from .news_data import load_calendar
from .run_scan import DATA

SYM = "XAUUSD"
NEW = pd.Timestamp("2021-10-01", tz="UTC")
TIER = [["NFP", "CPI", "FOMC"], ["PPI", "RETAIL", "GDP", "PCE"], ["ISM"], ["CLAIMS"]]


def events() -> pd.DataFrame:
    """Satu baris per waktu rilis: time, group, bias (+1 = kejutan bagus untuk emas, NaN bila tak ada), besar."""
    ev = releases(load_calendar(DATA))
    ev = ev[(ev.group != "FOMC") | ev.time.dt.minute.isin([0, 15, 30])]     # menit ganjil FOMC = salah scraping
    extra = []
    for g, rid in FRED_RELEASE.items():
        for d in _fred_dates(rid):
            t = _ny(d, "08:30")
            if FF_END <= t <= pd.Timestamp.now(tz="UTC"):
                extra.append({"time": t, "group": g})
    extra += [{"time": _ny(d, "14:00"), "group": "FOMC"} for d in FOMC_2026]
    ev = pd.concat([ev, pd.DataFrame(extra)], ignore_index=True)
    ev = ev[ev.time < pd.Timestamp.now(tz="UTC") - pd.Timedelta(hours=2)]
    ev["besar"] = ev["besar"].fillna(False).astype(bool)
    return ev.drop_duplicates("time").sort_values("time").reset_index(drop=True)


def hours_needed(ev: pd.DataFrame) -> list[pd.Timestamp]:
    """Jam tick yang dibutuhkan, urut prioritas (tier), di dalam tier diacak (seed tetap) agar hasil sebagian tetap
    mewakili semua tahun. Rilis tepat di menit 00 butuh jam sebelumnya juga (harga acuan)."""
    out, seen = [], set()
    rng = random.Random(7)
    for tier in TIER:
        rows = list(ev[ev.group.isin(tier)].time)
        rng.shuffle(rows)
        for t in rows:
            h = t.floor("h")
            for x in ([h - pd.Timedelta(hours=1)] if t.minute == 0 else []) + [h]:
                if x not in seen:
                    seen.add(x)
                    out.append(x)
    return out


def _raw(t0: pd.Timestamp):
    d = cache_path(f"dukascopy/raw_{SYM}_ticks")
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{t0:%Y%m%d_%H}.bi5"


def download(limit: int | None = None, ok_pause: float = 3.0, reverse_tier1: bool = False) -> None:
    """Unduh berurutan dengan jeda adaptif (server membatasi laju: 503 / koneksi diputus).
    reverse_tier1: pekerja kedua, mengunduh NFP/CPI/FOMC dari ujung daftar (bertemu pekerja pertama di tengah)."""
    ev = events()
    hs = hours_needed(ev[ev.group.isin(TIER[0])])[::-1] if reverse_tier1 else hours_needed(ev)
    todo = [h for h in hs if not _raw(h).exists()]
    if limit:
        todo = todo[:limit]
    print(f"{len(todo)} file tick belum ada", flush=True)
    wait, t_start, done, err = 15.0, time.time(), 0, "-"
    for h in todo:
        if _raw(h).exists():                               # sudah diambil pekerja lain
            continue
        url = f"{URL}/{SYM}/{h.year}/{h.month - 1:02d}/{h.day:02d}/{h.hour:02d}h_ticks.bi5"
        while True:
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=90) as r:
                    raw = r.read()
                if raw:
                    lzma.decompress(raw)                   # pastikan utuh sebelum disimpan
                _raw(h).write_bytes(raw)
                wait = max(15.0, wait * 0.7)
                break
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    _raw(h).write_bytes(b"")
                    break
                err = f"HTTP {e.code}"
            except Exception as e:  # noqa: BLE001 - diputus server / file terpotong
                err = type(e).__name__
            time.sleep(wait)
            wait = min(wait * 1.5, 120.0)
        done += 1
        if done % 10 == 0 or done == len(todo):
            rate = (time.time() - t_start) / done
            print(f"{done}/{len(todo)} ({h:%Y-%m-%d %H}h) {rate:.0f} dtk/file, sisa ±{rate * (len(todo) - done) / 3600:.1f} jam"
                  f" [gagal terakhir: {err}]", flush=True)
        time.sleep(ok_pause)


def ticks_around(t: pd.Timestamp) -> pd.DataFrame | None:
    """Tick dari 2 menit sebelum rilis s.d. 16 menit sesudahnya (None bila file belum ada / kosong)."""
    hs = [t.floor("h")] + ([t.floor("h") - pd.Timedelta(hours=1)] if t.minute == 0 else [])
    frames = []
    for h in sorted(hs):
        f = _raw(h)
        if not f.exists():
            return None
        frames.append(_decode_ticks(f.read_bytes(), h, POINT[SYM]))
    df = pd.concat([x for x in frames if len(x)]) if any(len(x) for x in frames) else None
    if df is None:
        return None
    df = df[(df.index >= t - pd.Timedelta(minutes=2)) & (df.index <= t + pd.Timedelta(minutes=16))]
    return df if len(df) else None


# BTC: kline 1 detik BTCUSDT spot Binance (data.binance.vision, 1 file zip per hari) -> jendela rilis disimpan kecil.
# Tanpa bid/ask: harga = close tiap detik (waktu = akhir detik), spread dianggap 0,03% (asumsi riset BTC lain).
BINANCE = "https://data.binance.vision/data/spot/daily/klines/BTCUSDT/1s"
BTC_START = pd.Timestamp("2018-01-01", tz="UTC")
BTC_SPREAD = 0.0003
BTC_UNIT = 0.0005


def _btc_file(t: pd.Timestamp):
    d = cache_path("binance_1s")
    d.mkdir(parents=True, exist_ok=True)
    return d / f"BTCUSDT_{t:%Y%m%d_%H%M}.parquet"


def download_btc() -> None:
    ev = events()
    ev = ev[(ev.time >= BTC_START) & ev.group.isin(TIER[0] + TIER[1])]
    todo = [t for t in ev.time if not _btc_file(t).exists()]
    print(f"BTC: {len(todo)} jendela rilis belum ada", flush=True)
    for n, t in enumerate(todo, 1):
        url = f"{BINANCE}/BTCUSDT-1s-{t:%Y-%m-%d}.zip"
        raw, missing = None, False
        for k in range(8):
            try:
                with urllib.request.urlopen(url, timeout=120) as r:
                    raw = r.read()
                break
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    missing = True
                    break
                time.sleep(2 ** k)
            except Exception:  # noqa: BLE001 - transfer terpotong -> ulang
                time.sleep(2 ** k)
        if raw is None:
            if missing:                                   # file memang tidak ada -> tandai kosong
                pd.DataFrame({"close": []}).to_parquet(_btc_file(t))
            print(f"BTC {t:%Y-%m-%d}: {'tidak ada' if missing else 'gagal, dicoba lagi saat dijalankan ulang'}",
                  flush=True)
            continue
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            k = pd.read_csv(z.open(z.namelist()[0]), header=None, usecols=[0, 4])
        k.columns = ["open_time", "close"]
        unit = "us" if k.open_time.iloc[0] > 1e14 else "ms"          # mulai 2025 dalam mikrodetik
        k.index = pd.to_datetime(k.open_time, unit=unit, utc=True) + pd.Timedelta(seconds=1)
        k = k.loc[(k.index >= t - pd.Timedelta(minutes=2)) & (k.index <= t + pd.Timedelta(minutes=16)), ["close"]]
        k.to_parquet(_btc_file(t))
        if n % 25 == 0:
            print(f"BTC {n}/{len(todo)} ({t:%Y-%m-%d})", flush=True)


def btc_around(t: pd.Timestamp) -> pd.DataFrame | None:
    f = _btc_file(t)
    if not f.exists():
        return None
    k = pd.read_parquet(f)
    if not len(k):
        return None
    half = k.close.to_numpy() * BTC_SPREAD / 2
    return pd.DataFrame({"bid": k.close.to_numpy() - half, "ask": k.close.to_numpy() + half}, index=k.index)


# ----------------------------------------------------------------------------------------------------------- uji
LAT = [0.5, 2.0]                   # detik dari keputusan sampai order sampai di server (0,5 = cepat; 2 = manual)
DECIDE = [1, 2, 5, 10, 30]         # detik setelah rilis saat keputusan diambil
THRESH = [1.0, 2.0, 3.0]           # $ gerak pertama minimal (GERAK / LAWAN) atau jarak pending (STRADDLE)
SLIP = [0.0, 0.3, 1.0]             # $ slippage tambahan saat entry
SL_DARURAT = 5.0
HOLD_MAX = 900
EXITS = ["PENGGUNA", "TAHAN 1m", "TAHAN 5m", "TAHAN 15m", "TP $1", "TP $3"]
CHECK = [60, 120, 180, 240, 300]   # aturan pengguna: tutup di menit 1-5 bila sudah profit
OUT_TXT = Path(__file__).resolve().parent.parent / "docs" / "eksternal" / "hasil_news_detik.txt"


class Tick:
    """Tick satu rilis; waktu T dalam detik relatif terhadap t0 (negatif = sebelum rilis)."""

    def __init__(self, t0: pd.Timestamp, df: pd.DataFrame, unit: float = 1.0):
        self.T = (df.index - t0).total_seconds().to_numpy()
        self.bid, self.ask = df.bid.to_numpy(), df.ask.to_numpy()
        self.mid = (self.bid + self.ask) / 2
        self.unit = unit            # XAU: $1; BTC: 0,05% harga (ambang, SL, TP, slippage & hasil dalam satuan ini)

    def at(self, sec: float) -> int:
        """Indeks kutipan yang berlaku pada detik `sec` (tick terakhir <= sec)."""
        return int(np.searchsorted(self.T, sec, side="right")) - 1

    def after(self, sec: float) -> int | None:
        """Tick pertama >= sec (order sampai di server), None bila tak ada tick dalam 10 detik."""
        k = int(np.searchsorted(self.T, sec, side="left"))
        return k if k < len(self.T) and self.T[k] <= sec + 10 else None


def prepare(t0: pd.Timestamp, aset: str = "XAU") -> Tick | None:
    df = ticks_around(t0) if aset == "XAU" else btc_around(t0)
    if df is None:
        return None
    p = Tick(t0, df, 1.0 if aset == "XAU" else float(df.bid.iloc[0]) * BTC_UNIT)
    pre = (p.T >= -60) & (p.T < 0)
    if not pre.any() or not ((p.T >= 0) & (p.T < 5)).any() or p.T[-1] < 14.5 * 60:
        return None                                   # pasar tutup / data bolong
    return p


def exits(p: Tick, k: int, price: float, d: int) -> dict[tuple[str, bool], float]:
    """P&L ($/ons) tiap aturan keluar, tanpa (False) dan dengan (True) SL darurat."""
    end = int(np.searchsorted(p.T, p.T[k] + HOLD_MAX, side="right"))
    pnl = ((p.bid[k:end] - price) if d > 0 else (price - p.ask[k:end])) / p.unit
    ts = p.T[k:end] - p.T[k]
    hit = np.flatnonzero(pnl <= -SL_DARURAT)
    sl_i = int(hit[0]) if len(hit) else None

    def at(sec: float) -> int:
        return max(int(np.searchsorted(ts, sec, side="right")) - 1, 0)

    idx = {"TAHAN 1m": at(60), "TAHAN 5m": at(300), "TAHAN 15m": at(HOLD_MAX)}
    idx["PENGGUNA"] = idx["TAHAN 15m"]
    for c in CHECK:
        i = at(c)
        if pnl[i] > 0:
            idx["PENGGUNA"] = i
            break
    for x in (1, 3):
        h = np.flatnonzero(pnl >= x)
        idx[f"TP ${x}"] = int(h[0]) if len(h) else idx["TAHAN 15m"]
    out = {}
    for name, i in idx.items():
        out[(name, False)] = float(pnl[i])
        out[(name, True)] = float(pnl[sl_i]) if sl_i is not None and sl_i <= i else float(pnl[i])
    return out


def trades(p: Tick, bias: float, besar: bool) -> list[dict]:
    """Semua varian untuk satu rilis -> daftar {aturan, slip, lat, keluar, sl, pnl, arah}."""
    ref = p.mid[p.at(-0.001)]
    rows = []

    def add(rule: str, slip: float, lat: float, k: int | None, d: int):
        if k is None or d == 0:
            return
        price = p.ask[k] + slip * p.unit if d > 0 else p.bid[k] - slip * p.unit
        for (ex, sl), v in exits(p, k, price, d).items():
            rows.append({"aturan": rule, "slip": slip, "lat": lat, "keluar": ex, "sl": sl, "pnl": v, "arah": d})

    for lat in LAT:
        for dd in DECIDE:
            k = p.after(dd + lat)
            move = p.mid[p.at(dd)] - ref
            for slip in SLIP:
                if bias in (1.0, -1.0):
                    add(f"KEJUTAN {dd}s", slip, lat, k, int(bias))
                    if besar:
                        add(f"KEJUTAN BESAR {dd}s", slip, lat, k, int(bias))
                for th in THRESH:
                    if abs(move) >= th * p.unit:
                        add(f"GERAK {dd}s ${th:.0f}", slip, lat, k, int(np.sign(move)))
                        add(f"LAWAN {dd}s ${th:.0f}", slip, lat, k, -int(np.sign(move)))
    # pending Buy Stop / Sell Stop dipasang 5 detik sebelum rilis (tidak butuh reaksi manusia -> lat = 0)
    ref5 = p.mid[p.at(-5)]
    w = np.flatnonzero((p.T >= -5) & (p.T <= 60))
    for th in THRESH:
        up = w[p.ask[w] >= ref5 + th * p.unit]
        dn = w[p.bid[w] <= ref5 - th * p.unit]
        iu, idn = (up[0] if len(up) else None), (dn[0] if len(dn) else None)
        if iu is None and idn is None or iu == idn:
            continue
        d = 1 if idn is None or (iu is not None and iu < idn) else -1
        k = int(iu if d > 0 else idn)
        for slip in SLIP:
            add(f"STRADDLE ${th:.0f}", slip, 0.0, k, d)
    return rows


def anatomy(p: Tick) -> dict:
    """Ciri detik pertama: besar gerak, spread, dan apakah arah detik ke-5 berlanjut."""
    ref = p.mid[p.at(-0.001)]
    pre = (p.T >= -60) & (p.T < 0)
    u = p.unit
    row = {"spread_pra": float(np.median(p.ask[pre] - p.bid[pre])) / u}
    for s in (0.25, 1, 5, 30, 60, 300, 900):
        i = p.at(s)
        row[f"gerak_{s}"] = float(p.mid[i] - ref) / u
        row[f"spread_{s}"] = float(p.ask[i] - p.bid[i]) / u
    post = (p.T >= 0) & (p.T < 60)
    quiet = (p.T >= -120) & (p.T < -60)
    row["range_pasca"] = float(np.ptp(p.mid[post])) / u if post.any() else np.nan
    row["range_pra"] = float(np.ptp(p.mid[quiet])) / u if quiet.any() else np.nan
    g5, g900 = row["gerak_5"], row["gerak_900"]
    row["lanjut"] = float(np.sign(g900 - g5) == np.sign(g5)) if g5 != 0 else np.nan
    return row


def run(aset: str = "XAU") -> tuple[pd.DataFrame, pd.DataFrame]:
    ev = events()
    if aset == "BTC":
        ev = ev[ev.time >= BTC_START]
    tr, an = [], []
    for e in ev.itertuples():
        p = prepare(e.time, aset)
        if p is None:
            continue
        a = anatomy(p)
        a.update(time=e.time, group=e.group)
        an.append(a)
        for r in trades(p, e.bias if e.bias == e.bias else np.nan, bool(e.besar)):
            r.update(time=e.time, group=e.group)
            tr.append(r)
    return pd.DataFrame(tr), pd.DataFrame(an)


def stats(x: pd.DataFrame) -> dict:
    v = x.pnl.to_numpy()
    n = len(v)
    if n == 0:
        return {"n": 0}
    lama, baru = x[x.time < NEW].pnl, x[x.time >= NEW].pnl
    yr = x.groupby(x.time.dt.year).pnl.sum()
    sd = v.std(ddof=1) if n > 1 else np.nan
    return {"n": n, "wr": float((v > 0).mean() * 100), "avg": float(v.mean()), "total": float(v.sum()),
            "t": float(v.mean() / (sd / math.sqrt(n))) if n > 2 and sd > 0 else np.nan,
            "lama": float(lama.mean()) if len(lama) else np.nan, "n_lama": len(lama),
            "baru": float(baru.mean()) if len(baru) else np.nan, "n_baru": len(baru),
            "tahun": float((yr > 0).mean() * 100), "n_tahun": len(yr)}


def judge(s: dict, robust: dict) -> bool:
    return (s.get("n", 0) >= 30 and s["lama"] > 0 and s["baru"] > 0 and s["tahun"] >= 60 and s["t"] > 2
            and robust.get("n", 0) > 0 and robust["avg"] > 0)


def fmt(name: str, s: dict) -> str:
    if not s.get("n"):
        return f"{name:44} n=0"
    return (f"{name:44} n={s['n']:4} WR {s['wr']:5.1f}% rata {s['avg']:+6.2f} total {s['total']:+8.1f} "
            f"t {s['t']:+5.1f} | LAMA {s['lama']:+6.2f} (n={s['n_lama']}) BARU {s['baru']:+6.2f} (n={s['n_baru']}) "
            f"| tahun+ {s['tahun']:3.0f}% dari {s['n_tahun']}")


# Preset yang ditampilkan di aplikasi (ditetapkan SEBELUM melihat hasil XAU): cara manual yang paling mirip permintaan
# pengguna, dan cara "detik pertama" dengan order pending. Keduanya dengan slippage $0,30 (realistis saat berita).
PRESET = {
    "manual": {"aturan": "GERAK 5s $2", "lat": 2.0, "slip": 0.3, "keluar": "PENGGUNA", "sl": False,
               "label": "ikut lonjakan di detik ke-5 (manual, reaksi 2 dtk), tutup menit 1-5 bila profit, maks 15 mnt"},
    "pending": {"aturan": "STRADDLE $2", "lat": 0.0, "slip": 0.3, "keluar": "PENGGUNA", "sl": False,
                "label": "Buy Stop & Sell Stop $2 dari harga sebelum rilis, tutup menit 1-5 bila profit, maks 15 mnt"},
}
OUT_JSON = Path(__file__).resolve().parent.parent / "cloud" / "api" / "detik.json"
MIN_N = 20


def _pick(tr: pd.DataFrame, pr: dict) -> pd.DataFrame:
    return tr[(tr.aturan == pr["aturan"]) & (tr.lat == pr["lat"]) & (tr.slip == pr["slip"]) &
              (tr.keluar == pr["keluar"]) & (tr.sl == pr["sl"])]


def _r(x: float, nd: int = 2):
    return None if x is None or x != x else round(float(x), nd)


def export_group(tr: pd.DataFrame, an: pd.DataFrame, aset: str, lolos: list[str]) -> dict:
    """Ringkasan satu aset per grup berita -> dict untuk cloud/api/detik.json (dibaca _persiapan.py)."""
    out = {}
    unit = "$" if aset == "XAU" else "x0,05%"
    for grp, g in [("SEMUA", an)] + list(an.groupby("group")):
        if len(g) < MIN_N:
            continue
        baru = g[g.time >= NEW]
        ref = baru if len(baru) >= MIN_N else g
        row = {"n": len(g), "n_baru": len(baru),
               "gerak5": _r(ref.gerak_5.abs().median()), "gerak60": _r(ref.gerak_60.abs().median()),
               "gerak900": _r(ref.gerak_900.abs().median()), "spread_pra": _r(ref.spread_pra.median()),
               "spread1": _r(ref.spread_1.median()), "lanjut": _r(ref.lanjut.mean() * 100, 0)}
        tg = tr if grp == "SEMUA" else tr[tr.group == grp]
        for key, pr in PRESET.items():
            st = stats(_pick(tg, pr))
            row[key] = {k: _r(v) if isinstance(v, float) else v for k, v in st.items()}
        m, pd_ = row["manual"], row["pending"]

        def one(st: dict) -> str:
            if not st.get("n"):
                return "belum ada data"
            return (f"rata {st['avg']:+.2f}{unit}/0,01 lot, menang {st['wr']:.0f}% (n={st['n']}; "
                    f"5 th {st['baru']:+.2f})" if st.get("baru") is not None else
                    f"rata {st['avg']:+.2f}{unit}/0,01 lot, menang {st['wr']:.0f}% (n={st['n']})")
        verdict = ("✅ ada cara yang lolos uji: " + ", ".join(lolos)) if lolos else "❌ tidak ada cara yang untung konsisten"
        row["teks"] = (f"Detik pertama ({aset}, tick {g.time.min():%Y}–{g.time.max():%Y}): gerak 5 dtk ±{row['gerak5']}"
                       f"{unit}, spread {row['spread_pra']}→{row['spread1']}{unit} di detik 1. Ikut lonjakan (manual): "
                       f"{one(m)}. Pending ±$2: {one(pd_)}. {verdict}.")
        row["alarm"] = (f"{aset}: 5 dtk pertama biasanya ±{row['gerak5']}{unit}, spread melebar ke ±{row['spread1']}"
                        f"{unit}. Ikut lonjakan dulu-dulu: {one(m)}. {verdict}.")
        out[grp] = row
    return out


def main(aset: str = "XAU") -> None:
    tr, an = run(aset)
    satuan = "$ per ons" if aset == "XAU" else "satuan 0,05% harga BTC (ambang $1/$2/$3 = 0,05/0,10/0,15%)"
    lines = [f"== {aset} == hasil & ambang dalam {satuan}",
             f"Rilis dengan data lengkap: {len(an)} ({an.time.min():%Y-%m-%d} .. {an.time.max():%Y-%m-%d}); "
             f"per grup: {an.group.value_counts().to_dict()}"]
    ok = (an.range_pasca > 3 * an.range_pra.clip(lower=0.05)).mean() * 100
    lines.append(f"Cek jam kalender: range 60 dtk sesudah rilis > 3x range menit tenang sebelumnya di {ok:.0f}% rilis")
    lines.append("")
    lines.append("== Anatomi detik pertama (median; $ per ons) ==")
    for lab, g in [("SEMUA", an)] + [(k, v) for k, v in an.groupby("group")]:
        for per, gg in (("LAMA", g[g.time < NEW]), ("BARU", g[g.time >= NEW])):
            if len(gg) < 5:
                continue
            med = gg.median(numeric_only=True)
            lines.append(
                f"{lab:7} {per} n={len(gg):4} spread pra {med.spread_pra:.2f} | spread +1s {med.spread_1:.2f} +5s "
                f"{med.spread_5:.2f} +60s {med.spread_60:.2f} | |gerak| +0,25s {gg['gerak_0.25'].abs().median():.2f} "
                f"+1s {gg.gerak_1.abs().median():.2f} +5s {gg.gerak_5.abs().median():.2f} +60s "
                f"{gg.gerak_60.abs().median():.2f} +15m {gg.gerak_900.abs().median():.2f} | arah +5s berlanjut s.d. "
                f"15m {gg.lanjut.mean() * 100:.0f}%")
    lines.append("")
    base = tr[(tr.slip == 0) & (tr.lat <= 0.5)]
    rob = tr[(tr.slip == 0.3) & ((tr.lat == 2.0) | tr.aturan.str.startswith("STRADDLE"))]
    rows = []
    for (rule, ex, sl), g in base.groupby(["aturan", "keluar", "sl"]):
        r = rob[(rob.aturan == rule) & (rob.keluar == ex) & (rob.sl == sl)]
        s, sr = stats(g), stats(r)
        rows.append((rule, ex, sl, s, sr, judge(s, sr)))
    lines.append(f"== {len(rows)} varian (slippage 0, latensi 0,5 dtk; kolom 'kuat' = slippage $0,30 + latensi 2 dtk) ==")
    lolos = [r for r in rows if r[5]]
    lines.append(f"LOLOS kriteria konsisten: {len(lolos)}")
    for rule, ex, sl, s, sr, _ in lolos:
        lines.append(fmt(f"{rule} | {ex}{' +SL$5' if sl else ''}", s) + f" | kuat {sr['avg']:+.2f}")
    lines.append("")
    lines.append("-- aturan pengguna (tutup menit 1-5 bila profit, paksa 15 menit), tanpa SL --")
    for rule, ex, sl, s, sr, _ in sorted(rows, key=lambda r: -r[3].get("avg", -9)):
        if ex == "PENGGUNA" and not sl:
            lines.append(fmt(rule, s) + f" | kuat {sr.get('avg', np.nan):+.2f}")
    lines.append("")
    lines.append("-- 15 varian terbaik (rata-rata) semua cara keluar --")
    for rule, ex, sl, s, sr, _ in sorted(rows, key=lambda r: -r[3].get("avg", -9))[:15]:
        lines.append(fmt(f"{rule} | {ex}{' +SL$5' if sl else ''}", s) + f" | kuat {sr.get('avg', np.nan):+.2f}")
    lines.append("")
    lines.append("-- per grup berita, aturan pengguna tanpa SL, slippage 0 --")
    for grp in ("NFP", "CPI", "FOMC"):
        gb = base[(base.group == grp) & (base.keluar == "PENGGUNA") & ~base.sl]
        best = sorted(((rule, stats(g)) for rule, g in gb.groupby("aturan")), key=lambda r: -r[1]["avg"])
        for rule, s in best[:5]:
            lines.append(fmt(f"{grp} {rule}", s))
    for key, pr in PRESET.items():
        lines.append("")
        lines.append(f"-- preset aplikasi '{key}': {pr['label']} (slippage ${pr['slip']:.2f}) --")
        tp = _pick(tr, pr)
        lines.append(fmt("SEMUA", stats(tp)))
        for grp, g in tp.groupby("group"):
            lines.append(fmt(grp, stats(g)))
    txt = "\n".join(lines)
    print(txt)
    data = json.loads(OUT_JSON.read_text(encoding="utf-8")) if OUT_JSON.exists() else {}
    data[aset] = export_group(tr, an, aset, [f"{r[0]} | {r[1]}{' +SL$5' if r[2] else ''}" for r in lolos])
    data["dibuat"] = pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d")
    OUT_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    out = OUT_TXT.with_name(f"hasil_news_detik_{aset.lower()}.txt")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(txt + "\n", encoding="utf-8")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ("download", "download_mundur"):
        download(int(sys.argv[2]) if len(sys.argv) > 2 else None, reverse_tier1=sys.argv[1] == "download_mundur")
    elif len(sys.argv) > 1 and sys.argv[1] == "download_btc":
        download_btc()
    else:
        main(sys.argv[1].upper() if len(sys.argv) > 1 else "XAU")
