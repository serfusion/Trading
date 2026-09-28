"""Trading gap pembukaan pekan (python -m research.gap_trade).

Gap = open candle pertama pekan - close Jumat. Dua cara:
- FADE (lawan gap, tunggu tertutup): TP di close Jumat (100%) atau 50% gap, SL = k x gap di luar entry.
- IKUT (searah gap): SL di close Jumat, TP = k x gap.
Entry di open candle pertama (spread 3x normal karena saat buka spread melebar) atau 1 jam setelah buka.
Keluar paksa 24 jam. Hasil dalam R. Latih s/d 2017, uji 2018 ke atas.
"""
import numpy as np
import pandas as pd

from .data import load_m15_2012, resample, server_ny7_to_utc, _clean
from .multi_asset import INSTRUMENTS
from .run_scan import DATA, dataset

SPLIT = pd.Timestamp("2018-01-01", tz="UTC")


def m15_ej(sym):
    div = INSTRUMENTS[sym][0]
    df = pd.read_csv(DATA / "ejtraderLabs_historical-data" / sym / f"{sym}m15.csv", parse_dates=["Date"],
                     index_col="Date")
    df[["open", "high", "low", "close"]] /= div
    df.index = server_ny7_to_utc(df.index)
    return _clean(df)


def xau():
    a = load_m15_2012(DATA / "ejtraderLabs_historical-data/XAUUSD")
    b = resample(dataset("m5_2020")[0], "15min")
    c = resample(dataset("m5_2025")[0], "15min")
    x = pd.concat([a, b[b.index > a.index[-1]]])
    return pd.concat([x, c[c.index > x.index[-1]]])


def events(df):
    t = df.index
    gap_h = np.r_[99.0, (t[1:] - t[:-1]).total_seconds() / 3600]
    d1 = df.resample("1D").agg({"high": "max", "low": "min"}).dropna()
    atr_d = (d1["high"] - d1["low"]).rolling(14).mean()
    ks = np.flatnonzero(gap_h > 30)[1:]
    out = []
    for k in ks:
        a = atr_d[atr_d.index < t[k].normalize()]
        if len(a) == 0 or np.isnan(a.iloc[-1]):
            continue
        out.append((k, a.iloc[-1]))
    return out


def sim(df, spread, evs, mode, thr, k, delay):
    o, h, l, c = (df[x].to_numpy() for x in ("open", "high", "low", "close"))
    t = df.index
    per_h = int(round(3600 / (t[1] - t[0]).total_seconds())) if len(t) > 1 else 1
    rows = []
    for i, atr in evs:
        fri = c[i - 1]
        gap = o[i] - fri
        if abs(gap) < thr * atr:
            continue
        j = i + delay * per_h
        if j >= len(o) - 1:
            continue
        sp = spread * (3 if delay == 0 else 1)
        if mode.startswith("fade"):
            d = -np.sign(gap)
            entry = o[j] + (sp if d > 0 else 0)
            tp = fri if mode == "fade100" else fri + gap / 2
            if (tp - entry) * d <= 0:
                continue                                    # gap sudah tertutup sebelum entry
            sl = entry - d * k * abs(gap)
        else:
            d = np.sign(gap)
            entry = o[j] + (sp if d > 0 else 0)
            sl = fri
            if (entry - sl) * d <= 0:
                continue
            tp = entry + d * k * abs(gap)
        risk = abs(entry - sl)
        end = min(j + 24 * per_h, len(o) - 1)
        px = c[end]
        for m in range(j, end + 1):
            adj = spread if d < 0 else 0
            if (l[m] + adj <= sl) if d > 0 else (h[m] + adj >= sl):
                px = sl
                break
            if m > j and ((h[m] + adj >= tp) if d > 0 else (l[m] + adj <= tp)):
                px = tp
                break
        rows.append((t[i], (px - entry) * d / risk))
    return rows


def show(name, rows):
    if not rows:
        return None
    r = pd.DataFrame(rows, columns=["t", "R"])
    out = []
    for part in (r[r.t < SPLIT], r[r.t >= SPLIT]):
        v = part.R.to_numpy()
        if len(v) < 10:
            return None
        yrs = part.groupby(part.t.dt.year).R.sum()
        out.append((len(v), np.mean(v > 0) * 100, v.mean(), v.mean() / (v.std() or 1e-9) * np.sqrt(len(v)),
                    (yrs > 0).mean() * 100))
    (n1, w1, a1, t1, y1), (n2, w2, a2, t2, y2) = out
    stars = 3 if (t1 > 2 and t2 > 2 and y1 >= 70 and y2 >= 70) else 2 if (t1 > 2 and t2 > 2) else \
        1 if (a1 > 0 and a2 > 0 and t2 > 1) else 0
    print(f"  {name:48s} LATIH n={n1:3d} win={w1:4.1f}% {a1:+.3f}R t={t1:+.1f} | UJI n={n2:3d} win={w2:4.1f}% "
          f"{a2:+.3f}R t={t2:+.1f} thn+={y2:3.0f}% {'★' * stars}")
    return stars


def main():
    data = {"XAUUSD": (xau(), 0.30)}
    for s in ("EURUSD", "GBPUSD", "USDJPY", "EURJPY"):
        data[s] = (m15_ej(s), INSTRUMENTS[s][1])
    for s, sp in (("NAS100_USD", 1.8), ("SPX500_USD", 0.5), ("JP225_USD", 10.0)):
        data[s] = (pd.read_parquet(DATA / "h1" / f"{s}.parquet"), sp)
    for name, (df, sp) in data.items():
        evs = events(df)
        print(f"\n### {name}: {len(evs)} pembukaan pekan")
        for mode in ("fade100", "fade50", "ikut"):
            for thr in (0.1, 0.25, 0.5):
                for k in (1.0, 2.0):
                    for delay in (0, 1):
                        show(f"{mode} gap>={thr}ATR k={k} tunda {delay}j", sim(df, sp, evs, mode, thr, k, delay))


if __name__ == "__main__":
    main()
