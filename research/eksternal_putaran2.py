"""Riset putaran 2: ide dari literatur/web sebagai filter sinyal 💰 (python -m research.eksternal_putaran2).

Ide & sumber (dicari 28 Sep 2026):
- GVZ (volatilitas tersirat emas, FRED GVZCLS) & VIX (FRED VIXCLS): literatur -> berguna sebagai rezim risiko,
  bukan arah (SSRN "Volatility Forecasting in Gold Futures ... Limits of Directional Inference").
- Ekspektasi suku bunga Fed: CME FedWatch tidak punya data historis gratis -> proksi yield 2 tahun (FRED DGS2),
  yang bergerak mengikuti ekspektasi FOMC. Breakeven inflasi 10 th (FRED T10YIE).
- Musiman emas: bias Jumat naik / Senin turun, September lemah (evtradelabs 2003-2026: sebagian besar lemah).
Waktu terbit FRED sama dengan research/eksternal_makro.py (vintage ALFRED, 21:00 UTC).

Varian (ditetapkan sebelum melihat hasil):
- GVZ/VIX tinggi (persentil 1 th >= 80%) dilewati; rendah (<= 20%) dilewati; naik 5 hari dilewati
- yield 2 th 20 hari searah (BUY emas bila turun) / lawan; breakeven 20 hari searah (BUY bila naik) / lawan
- lewati Senin; lewati Jumat; lewati September; lewati 15 Des - 5 Jan (likuiditas tipis)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .eksternal import asof, asset, bar_filter, fmt_judge, judge, per_year, realistic_summary
from .eksternal_makro import fred

SERIES = ["GVZCLS", "VIXCLS", "DGS2", "T10YIE"]


def _pct(df: pd.DataFrame, n: int = 252) -> pd.Series:
    return df.value.rolling(n, min_periods=n // 2).apply(lambda v: (v <= v[-1]).mean(), raw=True)


def variants(sig: pd.DataFrame, data: dict[str, pd.DataFrame]) -> dict[str, np.ndarray]:
    t = pd.DatetimeIndex(sig.t)
    d = sig.dir.to_numpy()
    out = {}
    for s, tag in (("GVZCLS", "GVZ"), ("VIXCLS", "VIX")):
        df = data[s]
        p = asof(t, _pct(df), pd.DatetimeIndex(df.available))
        ch = asof(t, df.value - df.value.shift(5), pd.DatetimeIndex(df.available))
        out[f"{tag} tinggi (P80) dilewati"] = np.isnan(p) | (p < 0.8)
        out[f"{tag} rendah (P20) dilewati"] = np.isnan(p) | (p > 0.2)
        out[f"{tag} naik 5h dilewati"] = np.isnan(ch) | (ch <= 0)
    for s, tag, sign in (("DGS2", "yield 2th", 1), ("T10YIE", "breakeven", -1)):
        df = data[s]
        ch = asof(t, df.value - df.value.shift(20), pd.DatetimeIndex(df.available))
        # searah: BUY emas bila yield 2th turun (sign=+1) / breakeven naik (sign=-1)
        out[f"{tag} 20h searah"] = np.isnan(ch) | (np.sign(ch) * sign != d)
        out[f"{tag} 20h lawan"] = np.isnan(ch) | (np.sign(ch) * sign != -d)
    ny = sig.t.dt.tz_convert("America/New_York")
    out["lewati Senin"] = (ny.dt.dayofweek != 0).to_numpy()
    out["lewati Jumat"] = (ny.dt.dayofweek != 4).to_numpy()
    out["lewati September"] = (ny.dt.month != 9).to_numpy()
    md = ny.dt.month * 100 + ny.dt.day
    out["lewati 15 Des - 5 Jan"] = ~((md >= 1215) | (md <= 105)).to_numpy()
    return out


def main() -> None:
    data = {s: fred(s) for s in SERIES}
    for s, df in data.items():
        print(f"{s}: {df.index[0]:%Y-%m-%d} .. {df.index[-1]:%Y-%m-%d}, {len(df)} nilai, terakhir {df.value.iloc[-1]:.2f}")
    for name in ("XAUUSD", "BTCUSD"):
        a = asset(name)
        for label, sig in (("💰 dikirim", a.money), ("semua sinyal", a.sig)):
            print(f"\n=== {name} — {label}: {len(sig)} sinyal (latih < {a.split:%Y}) — lolos/dibuang [dasar] ===")
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
