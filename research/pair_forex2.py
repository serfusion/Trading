"""Uji sinyal 💰 di 6 pair forex tambahan (Twelve Data 2013–2026) — python -m research.pair_forex2 [unduh]

Permintaan pengguna (3 Okt 2026): "uji pair lain lagi". Dibatasi 6 pair supaya kredit Twelve Data harian (800, dipakai
juga oleh cloud live) tidak habis. Perak/platina butuh paket berbayar (404). Penilaian = research/sinyal_tambahan.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from .eksternal import asset
from .pair_data import _dir, twelvedata
from .sinyal_tambahan import LIVE, btc_real_spread, runner, stat, verdict
from .strategy_lab import Bars

OUT = Path(__file__).resolve().parent.parent / "docs" / "eksternal" / "hasil_pair_forex2.txt"
PAIRS = {"NZDUSD": 0.00015, "GBPAUD": 0.00030, "EURAUD": 0.00025, "CADJPY": 0.025, "NZDJPY": 0.025, "AUDNZD": 0.00030}


def load(sym: str) -> pd.DataFrame:
    f = _dir() / f"{sym}.parquet"
    if f.exists():
        return pd.read_parquet(f)
    df = twelvedata(sym, "2013-01-01", "2026-10-03")
    df = df[~df.index.duplicated()]
    df.to_parquet(f)
    print(sym, len(df), df.index[0], df.index[-1], flush=True)
    return df


def main() -> None:
    if "unduh" in sys.argv:
        for s in PAIRS:
            load(s)
        return
    btc_real_spread(asset("BTCUSD").b)
    rows = []
    for sym, sp in PAIRS.items():
        df = load(sym)
        b = Bars(df[df.high > df.low], sp)
        for label, cats in (("semua", None), ("konf+⭐", ("konf+⭐",)), ("konf+⭐ & ⭐", ("konf+⭐", "⭐")),
                            ("seperti XAU (konf+⭐ & konf)", LIVE["XAUUSD"])):
            s = stat(runner(b, sym, cats, skip_open=True))
            rows.append((sym, label, s, verdict(s)))
    L = ["# 6 pair forex tambahan (research/pair_forex2.py)", "", "TP1 0,7R. LAMA < Okt 2021.", ""]
    for sym, label, s, v in rows:
        if not s.get("n"):
            L.append(f"{sym:7} {label:30} n=0")
            continue
        L.append(f"{sym:7} {label:30} n{s['n']:5} nB{s['n_baru']:5} WR {s['wr_l']:3.0f}/{s['wr_b']:3.0f}% "
                 f"R {s['avg_l']:+.2f}/{s['avg_b']:+.2f} th+ {s['th']:3.0f}%  {v}")
    L.append(f"\nLOLOS {sum(r[3] == 'LOLOS' for r in rows)} dari {len(rows)}")
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
