"""Deteksi koin (termasuk koin kecil/volatil) yang AKAN NAIK + aturan TP/SL/tutup — python -m research.spot_naik

Permintaan pengguna (5 Okt 2026): "ikut volatil: ketika sudah saatnya naik, sistem mendeteksi koin kecil ini lalu kita
entry; uji SEMUA koin; atur kapan TP dan tutup posisi". Data: research/spot_semua (semua pair USDT Binance, harian,
termasuk delisting -> tanpa bias koin selamat), volume quote USDT.
Metode:
  * Fitur di close hari t: 15 fitur spot_peluang + volume (rasio volume 1/3 hari vs 20 hari, likuiditas), breakout
    (close vs high 20/55 hari sebelumnya), squeeze (peringkat volatilitas 365 hari, vol14/vol60), umur koin.
  * Syarat likuid: rata-rata volume 20 hari ≥ $2 juta (bisa dibeli/jual tanpa slippage besar).
  * Target per aturan keluar (TP, SL, maks hari): naik = TP tersentuh sebelum SL dalam N hari (SL dicek dulu).
  * Gradient boosting WALK-FORWARD per tahun (tahun Y dilatih hanya dengan data sebelum Y), ambang peluang 0,6–0,8.
  * Dinilai per trade & portofolio 10 slot (10% modal per posisi), LAMA (< Okt 2021) dan BARU.
Biaya 0,30% pulang-pergi + slippage tambahan 0,2% untuk koin di luar 50 likuiditas teratas hari itu.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from .spot_dip import SPLIT
from .spot_peluang import GBM, rsi
from .spot_semua import load_all

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "eksternal" / "hasil_spot_naik.txt"
COST = 0.003
MIN_LIQ = 2e6
EXITS = [  # (TP, SL, maks hari)
    (0.03, None, 10), (0.05, 0.05, 10), (0.08, 0.06, 10), (0.10, 0.08, 15), (0.15, 0.10, 20), (0.25, 0.12, 30),
]
FEATS = ["dd20", "dd60", "rsi14", "rsi2", "red", "r1", "r3", "r7", "r30", "z20", "d50", "d200", "vol14", "btc_up",
         "btc_r7", "vr1", "vr3", "liq", "b20", "b55", "vrank", "squeeze", "age", "btc_r1"]


def features(d: pd.DataFrame, btc: pd.DataFrame) -> pd.DataFrame:
    c, h = d.close, d.high
    f = pd.DataFrame(index=d.index)
    f["dd20"] = c / h.rolling(20).max() - 1
    f["dd60"] = c / h.rolling(60).max() - 1
    f["rsi14"] = rsi(c, 14) / 100
    f["rsi2"] = rsi(c, 2) / 100
    red = (c < d.open).astype(int)
    f["red"] = red.groupby((red == 0).cumsum()).cumsum().clip(upper=6)
    for k in (1, 3, 7, 30):
        f[f"r{k}"] = c / c.shift(k) - 1
    m20, s20 = c.rolling(20).mean(), c.rolling(20).std()
    f["z20"] = (c - m20) / s20
    f["d50"] = c / c.rolling(50).mean() - 1
    f["d200"] = c / c.rolling(200).mean() - 1
    lr = np.log(c).diff()
    f["vol14"] = lr.rolling(14).std()
    f["vrank"] = f.vol14.rolling(365, min_periods=60).rank(pct=True)
    f["squeeze"] = f.vol14 / lr.rolling(60).std()
    q = d.qvol
    q20 = q.rolling(20).mean()
    f["vr1"] = q / q20
    f["vr3"] = q.rolling(3).mean() / q20
    f["liq"] = np.log10(q20.clip(lower=1))
    f["b20"] = c / h.shift(1).rolling(20).max() - 1
    f["b55"] = c / h.shift(1).rolling(55).max() - 1
    f["age"] = np.minimum(np.arange(len(d)), 1500) / 1500
    b = btc.close.reindex(d.index).ffill()
    bsma = btc.close.rolling(200).mean().reindex(d.index).ffill()
    f["btc_up"] = (b > bsma).astype(float)
    f["btc_r7"] = b / b.shift(7) - 1
    f["btc_r1"] = b / b.shift(1) - 1
    f["q20"] = q20
    return f


def outcome(d: pd.DataFrame, tp: float, sl: float | None, n: int) -> pd.DataFrame:
    o, h, lo, c = (d[k].to_numpy() for k in ("open", "high", "low", "close"))
    m = len(d)
    hit = np.full(m, np.nan)
    r = np.full(m, np.nan)
    out = np.full(m, -1)
    for t in range(m - n - 1):
        j = t + 1
        e = o[j]
        res = None
        for k in range(j, j + n):
            if sl is not None and lo[k] <= e * (1 - sl):
                px = min(o[k], e * (1 - sl)) if k > j else e * (1 - sl)
                res = (0, px, k)
                break
            if h[k] >= e * (1 + tp):
                px = max(o[k], e * (1 + tp)) if k > j else e * (1 + tp)
                res = (1, px, k)
                break
        if res is None:
            k = j + n - 1
            res = (0, c[k], k)
        hit[t], out[t] = res[0], res[2]
        r[t] = res[1] / e - 1 - COST
    return pd.DataFrame({"hit": hit, "r": r, "k": out}, index=d.index)


def build(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    btc = data["BTC"]
    rows = []
    for coin, d in data.items():
        d = d[(d.close > 0) & (d.low > 0)]
        if len(d) < 260:
            continue
        f = features(d, btc)
        f["coin"] = coin
        f["e"] = d.open.shift(-1)
        f["t_in"] = pd.Series(d.index, index=d.index).shift(-1)
        for i, (tp, sl, n) in enumerate(EXITS):
            x = outcome(d, tp, sl, n)
            f[f"hit{i}"], f[f"r{i}_"] = x.hit, x.r
            f[f"out{i}"] = [d.index[k] if k >= 0 else pd.NaT for k in x.k]
        rows.append(f.iloc[200:])
    df = pd.concat(rows).replace([np.inf, -np.inf], np.nan)
    df = df.dropna(subset=["d200", "vol14", "q20", "hit0"])
    # likuiditas relatif hari itu: peringkat volume 20 hari antar koin
    df["liq_rank"] = df.groupby(level=0).q20.rank(ascending=False)
    return df.sort_index(kind="stable")


def walk_forward(df: pd.DataFrame, target: str, n: int) -> np.ndarray:
    from sklearn.ensemble import HistGradientBoostingClassifier
    p = np.full(len(df), np.nan)
    t = df.index
    for y in range(2019, 2027):
        s = pd.Timestamp(f"{y}-01-01", tz="UTC")
        tr = (t < s - pd.Timedelta(days=n + 2)) & df[target].notna().to_numpy()
        te = (t >= s) & (t < pd.Timestamp(f"{y + 1}-01-01", tz="UTC"))
        if tr.sum() < 5000 or te.sum() == 0:
            continue
        m = HistGradientBoostingClassifier(**GBM).fit(df.loc[tr, FEATS], df.loc[tr, target])
        p[te] = m.predict_proba(df.loc[te, FEATS])[:, 1]
    return p


def take(df: pd.DataFrame, mask: np.ndarray, i: int, p: np.ndarray) -> pd.DataFrame:
    df = df.assign(p=p)
    sel = df[mask & df[f"out{i}"].notna().to_numpy()]
    out = []
    for coin, g in sel.groupby("coin"):
        free = None
        for t, row in g.iterrows():
            if free is not None and row.t_in <= free:
                continue
            slip = 0.002 if row.liq_rank > 50 else 0.0
            out.append({"coin": coin, "t": row.t_in, "t_out": row[f"out{i}"], "e": row.e, "r": row[f"r{i}_"] - slip,
                        "small": row.liq_rank > 50, "p": row.p})
            free = row[f"out{i}"]
    return pd.DataFrame(out).sort_values("t") if out else pd.DataFrame()


def portfolio(tr: pd.DataFrame, closes: dict[str, pd.Series], slots: int, start, end) -> dict:
    tr = tr[(tr.t >= start) & (tr.t < end)]
    if tr.empty:
        return {}
    days = pd.date_range(tr.t.min().normalize(), tr.t_out.max().normalize(), freq="D", tz="UTC")
    by = {t: g.sort_values("p", ascending=False) for t, g in tr.groupby(tr.t.dt.normalize())}
    cash, pos, eq, prev = 1.0, [], [], None

    def val(when):
        return sum(p["s"] * closes[p["c"]].asof(when) / p["e"] for p in pos)
    for day in days:
        equity = cash + (val(prev) if prev is not None else 0)
        for _, x in (by[day].iterrows() if day in by else []):
            if len(pos) >= slots or any(p["c"] == x.coin for p in pos):
                continue
            s = min(equity / slots, cash)
            if s <= 0:
                continue
            cash -= s
            pos.append({"c": x.coin, "e": x.e, "r": x.r, "s": s, "o": x.t_out})
        keep = []
        for p in pos:
            if p["o"].normalize() <= day:
                cash += p["s"] * (1 + p["r"])
            else:
                keep.append(p)
        pos = keep
        eq.append(cash + val(day))
        prev = day
    e = pd.Series(eq, index=days)
    yrs = max((days[-1] - days[0]).days / 365.25, 0.1)
    yr = e.resample("YE").last()
    return {"cagr": e.iloc[-1] ** (1 / yrs) - 1, "dd": (e / e.cummax() - 1).min(),
            "tahun": " ".join(f"{t.year}:{v * 100:+.0f}%" for t, v in yr.pct_change().fillna(yr.iloc[0] - 1).items())}


def line(tr: pd.DataFrame) -> str:
    out = []
    for lab, m in (("LAMA", tr.t < SPLIT), ("BARU", tr.t >= SPLIT), ("2025+", tr.t >= pd.Timestamp("2025-01-01", tz="UTC"))):
        x = tr[m]
        if len(x):
            out.append(f"{lab} n{len(x)} WR {(x.r > 0).mean() * 100:.0f}% rata {x.r.mean() * 100:+.2f}% "
                       f"kalah {x.r[x.r <= 0].mean() * 100 if (x.r <= 0).any() else 0:+.1f}%")
    return " | ".join(out)


def main() -> None:
    data = load_all()
    df = build(data)
    closes = {c: d.close for c, d in data.items()}
    liq = (df.q20 >= MIN_LIQ).to_numpy()
    L = ["# Deteksi koin yang akan naik — semua pair USDT Binance (research/spot_naik.py)",
         f"Koin: {df.coin.nunique()} (termasuk delisting), baris {len(df)}, syarat likuid volume 20 hari ≥ $2 juta.",
         "Biaya 0,30% + slippage 0,2% di luar 50 koin terlikuid. Portofolio 10 slot. LAMA 2019–Sep 2021, BARU Okt 2021–2026.",
         ""]
    s0, s1, s2 = pd.Timestamp("2019-01-01", tz="UTC"), SPLIT, pd.Timestamp("2026-10-01", tz="UTC")
    for i, (tp, sl, n) in enumerate(EXITS):
        p = walk_forward(df, f"hit{i}", n)
        base = df[f"hit{i}"][liq & (df.index >= SPLIT)].mean() * 100
        L.append(f"## Keluar: TP +{tp * 100:.0f}% / SL {'-' + str(int(sl * 100)) + '%' if sl else 'tanpa'} / maks {n} hari "
                 f"(dasar BARU naik {base:.0f}%)")
        for thr in (0.6, 0.7, 0.8, 0.9):
            m = liq & (p >= thr)
            if m.sum() < 30:
                continue
            tr = take(df, m, i, p)
            pl, pb = portfolio(tr, closes, 10, s0, s1), portfolio(tr, closes, 10, s1, s2)
            L.append(f"   p≥{thr}: {line(tr)} | kecil {tr.small.mean() * 100:.0f}%")
            if pl and pb:
                L.append(f"      portofolio LAMA {pl['cagr'] * 100:+.0f}%/th DD {pl['dd'] * 100:.0f}% | BARU "
                         f"{pb['cagr'] * 100:+.0f}%/th DD {pb['dd'] * 100:.0f}% | {pb['tahun']}")
        print("\n".join(L[-10:]), flush=True)
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
