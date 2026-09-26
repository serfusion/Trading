"""Uji strategi populer dari forum/web di data yang sama (python -m research.popular).

1. EMA 9/21 cross (M15) - populer di forum/YouTube.
2. RSI(2) mean reversion H1 dengan filter EMA200 (Connors) - populer di QuantifiedStrategies.
3. Ensemble Donchian H1 (rata-rata 3 set parameter) - diversifikasi parameter.
Semua: SL ATR, entry open bar berikutnya, spread dihitung, SL dicek lebih dulu.
"""
import numpy as np
import pandas as pd

from xau_bot.smc import atr

from .alt import donchian
from .data import resample
from .multi_tp import fmt
from .run_scan import dataset


def ema(x, n):
    return pd.Series(x).ewm(span=n, adjust=False).mean().to_numpy()


def rsi(c, n):
    d = np.diff(c, prepend=c[0])
    up = pd.Series(np.clip(d, 0, None)).ewm(alpha=1 / n, adjust=False).mean()
    dn = pd.Series(np.clip(-d, 0, None)).ewm(alpha=1 / n, adjust=False).mean()
    return (100 - 100 / (1 + up / dn.replace(0, np.nan))).fillna(50).to_numpy()


def run(df, sp, signal, exit_fn, sl_atr, max_hold):
    o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    a = atr(df, 14)
    out, i = [], 210
    while i < len(c) - 2:
        d = signal(i)
        if not d:
            i += 1
            continue
        entry = o[i + 1] + (sp if d > 0 else 0)
        risk = sl_atr * a[i]
        sl = entry - d * risk
        r = None
        for j in range(i + 1, min(i + 1 + max_hold, len(c) - 1)):
            if (l[j] <= sl) if d > 0 else (h[j] + sp >= sl):
                r = -1.0
                break
            if exit_fn(j, d):
                r = ((o[j + 1] - entry) if d > 0 else (entry - o[j + 1] - sp)) / risk
                break
        if r is None:
            r = ((c[j] - entry) if d > 0 else (entry - c[j] - sp)) / risk
        out.append(r)
        i = j + 1
    return np.array(out)


def ema_cross(df, sp):
    c = df["close"].to_numpy(float)
    f, s = ema(c, 9), ema(c, 21)
    sig = lambda i: 1 if f[i] > s[i] and f[i - 1] <= s[i - 1] else (-1 if f[i] < s[i] and f[i - 1] >= s[i - 1] else 0)
    ex = lambda j, d: (f[j] < s[j]) if d > 0 else (f[j] > s[j])
    return run(df, sp, sig, ex, 1.5, 200)


def rsi2(df, sp):
    c = df["close"].to_numpy(float)
    r, e = rsi(c, 2), ema(c, 200)
    sig = lambda i: 1 if c[i] > e[i] and r[i] < 10 else (-1 if c[i] < e[i] and r[i] > 90 else 0)
    ex = lambda j, d: (r[j] > 70) if d > 0 else (r[j] < 30)
    return run(df, sp, sig, ex, 3.0, 48)


def ensemble(h1, sp):
    parts = [donchian(h1, sp, ne, nx, 20, 3.0).R.to_numpy() for ne, nx in [(40, 15), (55, 20), (80, 30)]]
    return np.concatenate(parts) / 3  # risiko dibagi 3 per sinyal


def main():
    m15 = dataset("m15_2012")[0]
    m5 = dataset("m5_2025")[0]
    cut = pd.Timestamp("2018-01-01", tz="UTC")
    sets = {"2012-17": (m15[m15.index < cut], .30), "2018-22": (m15[m15.index >= cut], .30),
            "2025-26": (resample(m5, "15min"), .25)}
    tests = {
        "EMA 9/21 cross M15": lambda d, sp: ema_cross(resample(d, "15min"), sp),
        "RSI(2) + EMA200 H1 (Connors)": lambda d, sp: rsi2(resample(d, "60min"), sp),
        "Ensemble Donchian H1 (3 set)": lambda d, sp: ensemble(resample(d, "60min"), sp),
        "Donchian H1 55/20 (bot sekarang)": lambda d, sp: donchian(resample(d, "60min"), sp, 55, 20, 20, 3.0).R.to_numpy(),
    }
    for name, fn in tests.items():
        print(name)
        for k, (d, sp) in sets.items():
            print(f"   {k}: {fmt(fn(d, sp))}")


if __name__ == "__main__":
    main()
