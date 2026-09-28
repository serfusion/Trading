"""(2) Real yield DFII10 & dolar (FRED) sebagai filter sinyal 💰 (python -m research.eksternal_makro).

Data FRED (api.stlouisfed.org, secret FRED_API_KEY): DFII10 (yield riil 10 th TIPS, harian), DTWEXBGS (indeks
dolar luas, harian tetapi terbit MINGGUAN tiap Senin lewat H.10), DGS10 (yield nominal 10 th, pembanding).

Tanpa look-ahead: nilai tanggal d dianggap terbit pada vintage ALFRED pertama SETELAH d, pukul 21:00 UTC
(FRED biasanya memperbarui sore hari waktu AS). Sebelum ada vintage (DFII10 < 2006, DTWEXBGS < Feb 2019):
DFII10 = hari kerja berikutnya 21:00 UTC, DTWEXBGS = Senin berikutnya 21:00 UTC. Nilai revisi terakhir yang dipakai
(revisi seri ini kecil); ini dicatat sebagai keterbatasan.

Varian (ditetapkan sebelum melihat hasil): perubahan L hari bursa (L = 5, 20, 60) dari nilai terakhir yang sudah
terbit. "searah makro": BUY emas hanya bila yield riil / dolar TURUN (perubahan < 0), SELL hanya bila NAIK.
"lawan makro" = kebalikannya (untuk melihat apakah informasinya terbalik).
"""
from __future__ import annotations

import json
import os
import urllib.request

import numpy as np
import pandas as pd

from .eksternal import asof, asset, bar_filter, cache_path, fmt_judge, judge, per_year, realistic_summary

SERIES = ["DFII10", "DTWEXBGS", "DGS10"]
LOOKBACK = (5, 20, 60)


def _get(url: str, name: str) -> dict:
    path = cache_path(name)
    if not path.exists():
        with urllib.request.urlopen(url + f"&api_key={os.environ['FRED_API_KEY']}&file_type=json", timeout=60) as r:
            path.write_bytes(r.read())
    return json.loads(path.read_text())


def fred(series: str) -> pd.DataFrame:
    """Observasi + waktu terbit (UTC): kolom value, available; index = tanggal data."""
    base = "https://api.stlouisfed.org/fred/series"
    obs = _get(f"{base}/observations?series_id={series}&observation_start=2003-01-01", f"fred_{series}.json")
    vint = _get(f"{base}/vintagedates?series_id={series}&limit=10000", f"fred_{series}_vintage.json")
    df = pd.DataFrame(obs["observations"])
    df = df[df.value != "."]
    s = pd.Series(df.value.astype(float).to_numpy(), index=pd.DatetimeIndex(df.date))
    v = pd.DatetimeIndex(sorted(vint["vintage_dates"]))
    k = v.searchsorted(s.index, side="right")                     # vintage pertama > tanggal data
    first = pd.DatetimeIndex([v[i] if i < len(v) else pd.NaT for i in k])
    if series == "DTWEXBGS":
        fallback = s.index + pd.offsets.Week(weekday=0)            # Senin berikutnya
    else:
        fallback = s.index + pd.offsets.BDay(1)
    avail = first.where(~(first.isna() | (k == 0)), fallback)     # sebelum vintage pertama -> aturan jeda
    avail = (avail + pd.Timedelta(hours=21)).tz_localize("UTC")
    return pd.DataFrame({"value": s.to_numpy(), "available": avail}, index=s.index)


def lag_report(df: pd.DataFrame, name: str) -> str:
    lag = (df.available - df.index.tz_localize("UTC")).dt.total_seconds() / 86400
    return (f"{name}: {df.index[0]:%Y-%m-%d} .. {df.index[-1]:%Y-%m-%d}, {len(df)} nilai, jeda terbit median "
            f"{lag.median():.1f} hari (maks {lag.max():.0f})")


def change_at(times: pd.Series, df: pd.DataFrame, lookback: int) -> np.ndarray:
    """Perubahan L observasi dari nilai terakhir yang sudah terbit pada `times`."""
    ch = df.value - df.value.shift(lookback)
    return asof(pd.DatetimeIndex(times), ch, pd.DatetimeIndex(df.available))


def variants(sig: pd.DataFrame, data: dict[str, pd.DataFrame]) -> dict[str, np.ndarray]:
    d = sig.dir.to_numpy()
    out = {}
    for L in LOOKBACK:
        ry = change_at(sig.t, data["DFII10"], L)
        usd = change_at(sig.t, data["DTWEXBGS"], L)
        nom = change_at(sig.t, data["DGS10"], L)
        # searah = arah emas berlawanan dengan arah yield/dolar; NaN (belum ada data) -> tetap dikirim
        for tag, x in (("yield riil", ry), ("dolar", usd), ("yield nominal", nom)):
            ok = np.isnan(x) | (np.sign(x) != d)
            out[f"{tag} {L}h searah"] = ok
            out[f"{tag} {L}h lawan"] = np.isnan(x) | (np.sign(x) != -d)
        both = (np.isnan(ry) | (np.sign(ry) != d)) & (np.isnan(usd) | (np.sign(usd) != d))
        out[f"yield riil+dolar {L}h searah"] = both
    return out


def main() -> None:
    data = {s: fred(s) for s in SERIES}
    for s, df in data.items():
        print(lag_report(df, s))
    for name in ("XAUUSD", "BTCUSD"):
        a = asset(name)
        for label, sig in (("💰 dikirim", a.money), ("semua sinyal", a.sig)):
            print(f"\n=== {name} — {label}: {len(sig)} sinyal {sig.t.min():%Y-%m} .. {sig.t.max():%Y-%m} "
                  f"(latih < {a.split:%Y}) — lolos/dibuang [dasar] dalam R rata-rata per sinyal ===")
            vs = variants(sig, data)
            res = {k: judge(sig, v, a.split) for k, v in vs.items()}
            for k, j in res.items():
                print(fmt_judge(k, j))
            if label == "💰 dikirim":
                best = max(res, key=lambda k: res[k]["latih_keep"] - res[k]["latih_base"])
                print(f"-> terbaik di LATIH: {best}; per tahun lolos/dibuang(n): {per_year(sig, vs[best])}")
                for k in (k for k in res if res[k]["konsisten"]):
                    print(f"-> {k} konsisten; uji nyata (filter di allow seperti cloud):")
                    print(realistic_summary(a, bar_filter(a, lambda g, k=k: variants(g, data)[k])))


if __name__ == "__main__":
    main()
