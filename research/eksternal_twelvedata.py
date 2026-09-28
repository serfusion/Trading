"""Feed Twelve Data (dipakai cloud) vs data historis riset (python -m research.eksternal_twelvedata).

Butuh secret environment TWELVEDATA_API_KEY (1 panggilan API, 5.000 candle H1 XAU/USD ≈ 10 bulan).
Pertanyaan: apakah statistik 💰 dari data historis (ekspor MT5 NY+7, dineshelumalai007) berlaku untuk feed yang
benar-benar dipakai cloud? Dibandingkan di jendela yang sama:
- selisih harga close per candle H1 (median & persentil 95), candle yang hanya ada di satu sumber;
- sinyal mesin cloud (3 set Donchian, kategori konf+⭐/konf/⭐/biasa) di kedua sumber: berapa % sinyal yang sama
  (set & arah sama, waktu selisih <= 1 jam) dan berapa % kategorinya sama.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

from .data import resample
from .eksternal import _categorized, cache_path
from .run_scan import dataset
from .strategy_lab import Bars

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cloud" / "api"))
import _core  # noqa: E402


def twelvedata_h1() -> pd.DataFrame:
    path = cache_path("twelvedata_XAUUSD_h1.json")
    if not path.exists():
        q = urllib.parse.urlencode({"symbol": "XAU/USD", "interval": "1h", "outputsize": 5000, "timezone": "UTC",
                                    "order": "ASC", "apikey": os.environ.get("TWELVEDATA_API_KEY", "")})
        try:
            with urllib.request.urlopen("https://api.twelvedata.com/time_series?" + q, timeout=60) as r:
                raw = r.read()
        except urllib.error.HTTPError as e:
            raise SystemExit(f"Twelve Data menolak ({e.code}): cek TWELVEDATA_API_KEY di pengaturan environment "
                             "(nilai baru hanya terbaca di sesi baru)") from e
        data = json.loads(raw)
        if data.get("status") != "ok":
            raise SystemExit(f"Twelve Data: {data.get('message')}")
        path.write_bytes(raw)
    data = json.loads(path.read_text())
    v = pd.DataFrame(data["values"])
    df = v[["open", "high", "low", "close"]].astype(float)
    df.index = pd.DatetimeIndex(pd.to_datetime(v.datetime)).tz_localize("UTC")
    # buang candle saat pasar tutup, sama dengan cloud (_core.market_open)
    keep = [_core.market_open(t.to_pydatetime()) for t in df.index]
    return df[keep & (df.high > df.low)]


def match(a: pd.DataFrame, b: pd.DataFrame) -> tuple[float, float]:
    """% sinyal a yang juga ada di b (set & arah sama, waktu <= 1 jam), dan % kategori sama di antaranya."""
    hit = same = 0
    for r in a.itertuples():
        c = b[(b.set == r.set) & (b.dir == r.dir) & ((b.t - r.t).abs() <= pd.Timedelta(hours=1))]
        if len(c):
            hit += 1
            same += c.cat.iloc[0] == r.cat
    return 100 * hit / max(len(a), 1), 100 * same / max(hit, 1)


def main() -> None:
    td = twelvedata_h1()
    hist = resample(dataset("m5_2025")[0], "60min")
    lo, hi = max(td.index[0], hist.index[0]), min(td.index[-1], hist.index[-1])
    td_w, hist_w = td[(td.index >= lo) & (td.index <= hi)], hist[(hist.index >= lo) & (hist.index <= hi)]
    both = td_w.index.intersection(hist_w.index)
    diff = (td_w.close.reindex(both) - hist_w.close.reindex(both)).abs()
    print(f"Twelve Data H1: {len(td)} candle {td.index[0]:%Y-%m-%d} .. {td.index[-1]:%Y-%m-%d}; jendela sama "
          f"{lo:%Y-%m-%d} .. {hi:%Y-%m-%d}: {len(both)} candle di keduanya, hanya TD {len(td_w.index.difference(both))},"
          f" hanya historis {len(hist_w.index.difference(both))}")
    print(f"Selisih close: median ${diff.median():.2f}, p95 ${diff.quantile(0.95):.2f}, maks ${diff.max():.2f}")
    s_td = _categorized(Bars(td_w, 0.30), True)
    s_hi = _categorized(Bars(hist_w, 0.30), True)
    warm = lo + pd.Timedelta(days=90)                      # indikator (EMA200, momentum 60 hari) perlu pemanasan
    s_td, s_hi = s_td[s_td.t >= warm], s_hi[s_hi.t >= warm]
    m1, c1 = match(s_td, s_hi)
    m2, c2 = match(s_hi, s_td)
    print(f"Sinyal sejak {warm:%Y-%m-%d}: Twelve Data {len(s_td)} (💰 {s_td.cat.isin(['konf+⭐', 'konf']).sum()}), "
          f"historis {len(s_hi)} (💰 {s_hi.cat.isin(['konf+⭐', 'konf']).sum()})")
    print(f"  sinyal TD yang juga ada di historis: {m1:.0f}% (kategori sama {c1:.0f}%); "
          f"sebaliknya {m2:.0f}% (kategori sama {c2:.0f}%)")
    for tag, s in (("Twelve Data", s_td), ("historis", s_hi)):
        g = s.groupby("cat").R
        print(f"  {tag}: " + " | ".join(f"{c} n={n} rata={m:+.2f}R" for c, n, m in
                                         zip(g.size().index, g.size(), g.mean())))


if __name__ == "__main__":
    main()
