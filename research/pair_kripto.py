"""Uji sinyal 💰 di pair kripto Binance + perak (XAG) — python -m research.pair_kripto [unduh]

Permintaan pengguna (3 Okt 2026): "uji pair lain lagi". Mesin & penilaian sama dengan research/sinyal_tambahan.py
(TP1 0,7R, kategori konf+⭐/konf/⭐/biasa, LOLOS = WR >= 55% & R > 0 di LAMA dan BARU, n BARU >= 40, >= 60% tahun +).
Spread kripto alt 0,10% (perkiraan konservatif akun Standard Exness), ETH 0,05%. Data 1 jam data.binance.vision
(cache data/research/eksternal/pair_h1/<SYM>USD.parquet). Tiap koin diuji: semua / konf+⭐ / konf+⭐ & ⭐, sendiri
dan hanya saat sinyal 💰 BTC searah terbuka.
"""
from __future__ import annotations

import io
import sys
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

from .eksternal import asset
from .pair_data import _dir
from .sinyal_tambahan import LIVE, SPLIT, btc_real_spread, open_gate, runner, stat, verdict
from .strategy_lab import Bars

OUT = Path(__file__).resolve().parent.parent / "docs" / "eksternal" / "hasil_pair_kripto.txt"
COINS = ["SOL", "BNB", "XRP", "ADA", "DOGE", "LTC", "LINK", "DOT", "AVAX", "TRX", "BCH", "XLM", "ATOM", "ETC",
         "UNI", "FIL", "NEAR", "MATIC", "AAVE", "XMR", "EOS", "ALGO", "SHIB", "TON", "SUI"]


def coin(sym: str) -> pd.DataFrame | None:
    f = _dir() / f"{sym}USD.parquet"
    if f.exists():
        return pd.read_parquet(f)
    parts = []
    for p in pd.period_range("2017-08", "2026-09", freq="M"):
        url = f"https://data.binance.vision/data/spot/monthly/klines/{sym}USDT/1h/{sym}USDT-1h-{p.strftime('%Y-%m')}.zip"
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                z = zipfile.ZipFile(io.BytesIO(r.read()))
        except Exception:  # noqa: BLE001
            continue
        raw = pd.read_csv(z.open(z.namelist()[0]), header=None, usecols=[0, 1, 2, 3, 4])
        raw.columns = ["t", "open", "high", "low", "close"]
        unit = "us" if raw.t.iloc[0] > 1e14 else "ms"
        raw.index = pd.to_datetime(raw.t, unit=unit, utc=True)
        parts.append(raw[["open", "high", "low", "close"]].astype(float))
    if not parts:
        return None
    df = pd.concat(parts).sort_index()
    df = df[~df.index.duplicated()]
    df.to_parquet(f)
    print(f"{sym}: {len(df)} candle {df.index[0]:%Y-%m} .. {df.index[-1]:%Y-%m}", flush=True)
    return df


def main() -> None:
    if "unduh" in sys.argv:
        for c in COINS:
            coin(c)
        return
    bb = asset("BTCUSD").b
    btc_real_spread(bb)
    base = runner(bb, "BTCUSD", LIVE["BTCUSD"], skip_open=False)
    rows = []
    for c in COINS:
        df = coin(c)
        if df is None or len(df) < 20000 or df.index[0] > SPLIT - pd.Timedelta(days=365):
            rows.append((c, "data kurang (perlu mulai < Okt 2020)", {"n": 0}, "-"))
            continue
        b = Bars(df[df.high > df.low], "0.10%")
        for label, cats in (("semua", None), ("konf+⭐", ("konf+⭐",)), ("konf+⭐ & ⭐", ("konf+⭐", "⭐"))):
            for gl, gate in (("", None), (" saat 💰 BTC searah", open_gate(b, base))):
                s = stat(runner(b, c, cats, skip_open=False, gate=gate))
                rows.append((c, label + gl, s, verdict(s)))
                print(c, label + gl, verdict(s), flush=True)
    L = ["# Pair kripto tambahan (research/pair_kripto.py)", "", "TP1 0,7R, spread 0,10%. LAMA < Okt 2021.", "",
         f"{'koin':6} {'varian':34} {'n':>5} {'nB':>4} {'WR L':>5} {'WR B':>5} {'R L':>6} {'R B':>6} {'th+':>4}  hasil"]
    for c, label, s, v in rows:
        if s.get("n", 0) == 0:
            L.append(f"{c:6} {label}")
            continue
        L.append(f"{c:6} {label:34} {s['n']:5} {s['n_baru']:4} {s['wr_l']:5.0f} {s['wr_b']:5.0f} {s['avg_l']:+6.2f} "
                 f"{s['avg_b']:+6.2f} {s['th']:4.0f}  {v}")
    lol = [r for r in rows if r[3] == "LOLOS"]
    L += ["", f"Diuji {sum(1 for r in rows if r[2].get('n'))} varian. LOLOS {len(lol)}."]
    for c, label, s, v in sorted(lol, key=lambda r: -r[2]["avg_b"]):
        L.append(f"  LOLOS: {c} {label} — WR {s['wr_l']:.0f}%/{s['wr_b']:.0f}%, R {s['avg_l']:+.2f}/{s['avg_b']:+.2f}, "
                 f"n BARU {s['n_baru']}")
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
