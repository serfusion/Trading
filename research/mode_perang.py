"""Validasi "mode perang" (guncangan minyak) dan momen hari untuk BTC (python -m research.mode_perang).

Lanjutan research/momen.py. Mode perang = harga minyak (FRED DCOILWTICO / DCOILBRENTEU, dipakai sejak waktu
terbitnya) naik >= X% dalam N hari bursa. Diuji di sinyal 💰 dengan periode LAMA (< 2021-10) dan BARU (5 tahun
terakhir). Konsisten bila: rata-rata sinyal di mode perang <= 0 di LAMA DAN BARU, sinyal normal > dasar di keduanya,
>= 60% tahun (yang punya sinyal perang) perang < normal, p-acak < 0,05. Lalu uji nyata: filter di allow() seperti
cloud (sinyal ditolak -> candle berikutnya boleh masuk lagi).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .eksternal import asof, asset
from .eksternal_makro import fred
from .momen import base_entries, line, perm_p
from .rekomendasi import BTC_SWAP_LONG_DAY, entries, swap_r, trades


def oil(series: str, n: int) -> tuple[pd.Series, pd.DatetimeIndex]:
    df = fred(series)
    return df.value / df.value.shift(n) - 1, pd.DatetimeIndex(df.available)


def judge(e: pd.DataFrame, war: np.ndarray) -> tuple[str, bool]:
    r, per, yrs = e.R.to_numpy(), e.per.to_numpy(), e.t.dt.year.to_numpy()
    cells, ok = [], True
    for p in ("LAMA", "BARU"):
        s = per == p
        w, nrm, base = r[war & s], r[~war & s], r[s].mean()
        cells.append(f"{p} perang {w.mean() if len(w) else np.nan:+.2f}R ({len(w)}) normal {nrm.mean():+.3f} "
                     f"[dasar {base:+.3f}]")
        ok &= len(w) >= 5 and w.mean() <= 0 and nrm.mean() > base
    wins = tot = 0
    for y in np.unique(yrs):
        w, nrm = r[war & (yrs == y)], r[~war & (yrs == y)]
        if len(w) >= 1 and len(nrm) >= 3:
            tot += 1
            wins += w.mean() < nrm.mean()
    p = perm_p(r, ~war)
    ok &= bool(tot) and wins / tot >= 0.6 and p < 0.05
    return " | ".join(cells) + f" | tahun {wins}/{tot} p={p:.3f}", bool(ok)


def realistic(name: str, skip_fn) -> pd.DataFrame:
    """Entry 💰 dengan filter di allow(); BTC: juga filter September (cloud) & swap."""
    sep = (lambda t, d: t.month == 9) if name == "BTCUSD" else (lambda t, d: False)
    e = entries(trades(name, skip=lambda t, d: sep(t, d) or skip_fn(t, d)))
    if name == "BTCUSD":
        e["R"] = e.R - swap_r(e, name, BTC_SWAP_LONG_DAY, 0.0)
    e["per"] = np.where(e.t >= pd.Timestamp("2021-10-01", tz="UTC"), "BARU", "LAMA")
    return e


def real_summary(name: str, skip_fn, tag: str):
    base, new = realistic(name, lambda t, d: False), realistic(name, skip_fn)
    for lab, e in (("tanpa", base), (tag, new)):
        print(f"   nyata {lab:22s}: " + " | ".join(f"{p} {line(e.R[e.per == p])}" for p in ("LAMA", "BARU")))
    yb = base.groupby(base.t.dt.year).R.sum()
    yn = new.groupby(new.t.dt.year).R.sum()
    d = (yn - yb).fillna(0).round(1)
    print(f"   selisih per tahun: {dict(d)} -> membaik {(d > 0).sum()}, memburuk {(d < 0).sum()}")


def lookup(name: str, ch: pd.Series, avail: pd.DatetimeIndex) -> dict:
    t = asset(name).b.t
    return dict(zip(t, asof(pd.DatetimeIndex(t), ch, avail)))


def main():
    print("# Mode perang (guncangan minyak) & momen hari BTC (research/mode_perang.py)\n")
    grid = {}
    for n in ("XAUUSD", "BTCUSD"):
        e = base_entries(n)
        print(f"## {n}: dasar LAMA {line(e.R[e.per == 'LAMA'])} | BARU {line(e.R[e.per == 'BARU'])}")
        for series, lab in (("DCOILWTICO", "WTI"), ("DCOILBRENTEU", "Brent")):
            for days in (5, 10, 20):
                ch, av = oil(series, days)
                x = asof(pd.DatetimeIndex(e.t), ch, av)
                for thr in (0.05, 0.075, 0.10, 0.15):
                    txt, ok = judge(e, x >= thr)
                    grid[(n, lab, days, thr)] = ok
                    print(f"{lab} +{thr:.1%}/{days}h: {txt}{'  KONSISTEN' if ok else ''}")
        print(f"-> konsisten {sum(v for k, v in grid.items() if k[0] == n)} dari "
              f"{sum(1 for k in grid if k[0] == n)} kombinasi\n")

    print("## Uji nyata XAU: jeda sinyal 💰 selama WTI naik >= 10% dalam 10 hari")
    ch, av = oil("DCOILWTICO", 10)
    look = lookup("XAUUSD", ch, av)
    real_summary("XAUUSD", lambda t, d: look.get(t, np.nan) >= 0.10, "jeda mode perang")
    for thr in (0.05, 0.075, 0.15):
        real_summary("XAUUSD", lambda t, d, thr=thr: look.get(t, np.nan) >= thr, f"jeda >= {thr:.1%}")

    print("\n## BTC per hari (UTC, candle sinyal)")
    e = base_entries("BTCUSD")
    b = asset("BTCUSD").b
    dow = b.t[e.i.to_numpy()].dayofweek.to_numpy()
    for k, nama in enumerate(("Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu")):
        m = dow == k
        print(f"   {nama:7s}: " + " | ".join(f"{p} {line(e.R[m & (e.per == p).to_numpy()])}" for p in ("LAMA", "BARU")))
    wk = np.isin(dow, (4, 5, 6))
    txt, ok = judge(e, wk)
    print(f"   Jumat–Minggu sebagai 'dibuang': {txt}{'  KONSISTEN' if ok else ''}")
    real_summary("BTCUSD", lambda t, d: (t - pd.Timedelta(hours=1)).dayofweek in (4, 5, 6), "lewati Jumat–Minggu")


if __name__ == "__main__":
    main()
