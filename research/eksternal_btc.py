"""(5) Funding rate & open interest BTC (Binance) sebagai filter sinyal BTC 💰 (python -m research.eksternal_btc).

Data: data.binance.vision (api.binance.com diblokir 451 dari server ini)
- futures/um monthly fundingRate BTCUSDT (2020-01 ->): funding tiap 8 jam, diketahui pada calc_time.
- futures/um daily metrics BTCUSDT (2020-09 ->): open interest & rasio long/short tiap 5 menit, diketahui pada
  create_time + 5 menit.
Sinyal BTC tetap dari Bitstamp BTC/USD H1 (sama dengan cloud); Binance hanya sebagai fitur.

Karena data mulai 2020, pembagian latih/uji disesuaikan: funding latih 2020-2021 / uji 2022-2026;
OI & rasio L/S latih 2020-09..2022 / uji 2023-2026.
Varian (ditetapkan sebelum melihat hasil):
- funding hindari/ikut ramai P80/P90: rata-rata 3 funding terakhir (24 jam), persentil 1 tahun (1.095 funding)
- OI 24j naik / turun: sinyal dikirim hanya bila open interest 24 jam terakhir naik / turun
- L/S akun hindari ramai P80: lewati BUY bila rasio long/short akun global >= persentil 80 (30 hari), SELL <= P20
"""
from __future__ import annotations

import io
import urllib.error
import urllib.request
import zipfile

import numpy as np
import pandas as pd

from .eksternal import asof, asset, bar_filter, cache_path, fmt_judge, judge, per_year, realistic_summary

BASE = "https://data.binance.vision/data/futures/um"
SPLIT_FUNDING = pd.Timestamp("2022-01-01", tz="UTC")
SPLIT_OI = pd.Timestamp("2023-01-01", tz="UTC")


def _zip_csv(url: str) -> pd.DataFrame | None:
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            raw = r.read()
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        return pd.read_csv(z.open(z.namelist()[0]))


def funding() -> pd.DataFrame:
    path = cache_path("binance_funding_BTCUSDT.parquet")
    if path.exists():
        return pd.read_parquet(path)
    frames = []
    for p in pd.period_range("2019-09", pd.Timestamp.now().strftime("%Y-%m"), freq="M"):
        df = _zip_csv(f"{BASE}/monthly/fundingRate/BTCUSDT/BTCUSDT-fundingRate-{p}.zip")
        if df is None:          # bulan berjalan belum ada file bulanan -> file harian
            for d in pd.date_range(p.to_timestamp(), min(p.to_timestamp(how="end"), pd.Timestamp.now()), freq="D"):
                dd = _zip_csv(f"{BASE}/daily/fundingRate/BTCUSDT/BTCUSDT-fundingRate-{d:%Y-%m-%d}.zip")
                if dd is not None:
                    frames.append(dd)
            continue
        frames.append(df)
    df = pd.concat(frames)
    out = pd.DataFrame({"rate": df.last_funding_rate.astype(float).to_numpy()},
                       index=pd.to_datetime(df.calc_time, unit="ms", utc=True)).sort_index()
    out = out[~out.index.duplicated()]
    out.to_parquet(path)
    return out


def metrics() -> pd.DataFrame:
    """OI & rasio L/S per jam (nilai terakhir di jam itu)."""
    path = cache_path("binance_metrics_BTCUSDT.parquet")
    have = pd.read_parquet(path) if path.exists() else None
    frames = [have] if have is not None else []
    last = have.index.max() if have is not None else pd.Timestamp("2020-01-01", tz="UTC")
    for d in pd.date_range(last.normalize().tz_localize(None) + pd.Timedelta(days=1), pd.Timestamp.now().normalize(), freq="D"):
        df = _zip_csv(f"{BASE}/daily/metrics/BTCUSDT/BTCUSDT-metrics-{d:%Y-%m-%d}.zip")
        if df is None or df.empty:
            continue
        t = pd.to_datetime(df.create_time, utc=True)
        h = pd.DataFrame({"oi": pd.to_numeric(df.sum_open_interest, errors="coerce").to_numpy(),
                          "ls": pd.to_numeric(df.count_long_short_ratio, errors="coerce").to_numpy()},
                         index=t).resample("60min").last()
        frames.append(h)
        if len(frames) % 100 == 0:
            pd.concat(frames).sort_index().to_parquet(path)
            print(f"metrics s/d {d:%Y-%m-%d}", flush=True)
    out = pd.concat(frames).sort_index()
    out = out[~out.index.duplicated()]
    out.to_parquet(path)
    return out


def variants(sig: pd.DataFrame, fr: pd.DataFrame, mt: pd.DataFrame) -> dict[str, np.ndarray]:
    t = pd.DatetimeIndex(sig.t)
    d = sig.dir.to_numpy()
    f3 = fr.rate.rolling(3).mean()
    fpct = f3.rolling(1095, min_periods=365).apply(lambda v: (v <= v[-1]).mean(), raw=True)
    fp = asof(t, fpct, fr.index)                                        # diketahui saat calc_time
    avail = mt.index + pd.Timedelta(minutes=60)                         # nilai terakhir jam itu -> akhir jam
    oi24 = asof(t, mt.oi / mt.oi.shift(24) - 1, avail)
    ls = mt.ls.rolling(24 * 30, min_periods=24 * 7).apply(lambda v: (v <= v[-1]).mean(), raw=True)
    lsp = asof(t, ls, avail)
    out = {}
    for p in (0.8, 0.9):
        crowded = ((d > 0) & (fp >= p)) | ((d < 0) & (fp <= 1 - p))
        against = ((d > 0) & (fp <= 1 - p)) | ((d < 0) & (fp >= p))
        out[f"funding hindari ramai P{p * 100:.0f}"] = np.isnan(fp) | ~crowded
        out[f"funding ikut ramai P{p * 100:.0f}"] = np.isnan(fp) | ~against
    out["OI 24j naik"] = np.isnan(oi24) | (oi24 > 0)
    out["OI 24j turun"] = np.isnan(oi24) | (oi24 < 0)
    crowded = ((d > 0) & (lsp >= 0.8)) | ((d < 0) & (lsp <= 0.2))
    out["L/S akun hindari ramai P80"] = np.isnan(lsp) | ~crowded
    return out


def main() -> None:
    fr, mt = funding(), metrics()
    print(f"funding: {len(fr)} nilai {fr.index[0]:%Y-%m-%d} .. {fr.index[-1]:%Y-%m-%d}; "
          f"metrics: {mt.oi.notna().sum()} jam {mt.index[0]:%Y-%m-%d} .. {mt.index[-1]:%Y-%m-%d}")
    a = asset("BTCUSD")
    for label, sig in (("💰 dikirim", a.money), ("semua sinyal", a.sig)):
        sig = sig[sig.t >= fr.index[0] + pd.Timedelta(days=365)].reset_index(drop=True)
        vs = variants(sig, fr, mt)
        print(f"\n=== BTCUSD — {label}: {len(sig)} sinyal {sig.t.min():%Y-%m} .. {sig.t.max():%Y-%m} ===")
        res = {}
        for k, v in vs.items():
            split = SPLIT_FUNDING if k.startswith("funding") else SPLIT_OI
            res[k] = judge(sig, v, split)
            print(fmt_judge(f"{k} (uji >= {split:%Y})", res[k]))
        if label == "💰 dikirim":
            best = max(res, key=lambda k: res[k]["latih_keep"] - res[k]["latih_base"])
            print(f"-> terbaik di LATIH: {best}; per tahun lolos/dibuang(n): {per_year(sig, vs[best])}")
            for k in (k for k in res if res[k]["konsisten"]):
                print(f"-> {k} konsisten; uji nyata (filter di allow seperti cloud):")
                print(realistic_summary(a, bar_filter(a, lambda g, k=k: variants(g, fr, mt)[k])))


if __name__ == "__main__":
    main()
