"""Sinyal SPOT Binance "sudah turun jauh, saatnya beli" — python -m research.spot_dip

Permintaan pengguna (4 Okt 2026): sinyal spot (beli saja, tanpa leverage) saat harga sudah terlalu turun, WR & profit
tinggi. Data 1 jam data.binance.vision (research/pair_kripto.py, data/research/eksternal/pair_h1) + BTC/ETH,
dijadikan candle HARIAN UTC. Entry di open hari berikutnya; biaya 0,10% per sisi + slippage 0,05% (pulang-pergi 0,30%).
SL dicek sebelum TP pada hari yang sama (konservatif). Satu posisi per koin.

Entry (dipilih sebelum melihat hasil):
  DD{N}_{X}  : close turun >= X% dari high N hari          (N 20/60, X 10/15/20/30)
  RSI{L}     : RSI(14) harian < L                            (L 20/25/30)
  BB{k}      : close di bawah Bollinger(20, k)               (k 2 / 2,5)
  Z2         : z-score close vs rata-rata 20 hari < -2
  MERAH3_{X} : 3 hari merah beruntun, total turun >= X%      (X 10/15)
  filter tren: semua / hanya bila close > SMA200 (beli koreksi dalam tren naik)
Keluar: TP +3/+5/+10% dengan batas 5/10/20 hari, atau "balik ke rata-rata" (close > SMA20) batas 10/20 hari;
  tanpa SL dan SL -15%.
Pembanding: entry acak pada hari yang sama banyaknya dengan aturan keluar yang sama ("acak"), supaya WR tinggi karena
  pasar naik tidak dianggap keunggulan.
LOLOS (ditetapkan sebelum melihat hasil): WR >= 60% & rata-rata > 0 & rata-rata > acak, di LAMA (< Okt 2021) DAN BARU,
  n BARU >= 30 (gabungan koin), >= 60% tahun positif.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .pair_data import _dir

OUT = Path(__file__).resolve().parent.parent / "docs" / "eksternal" / "hasil_spot_dip.txt"
SPLIT = pd.Timestamp("2021-10-01", tz="UTC")
COST = 0.003
COINS = ["BTC", "ETH", "BNB", "XRP", "ADA", "DOGE", "LTC", "LINK", "TRX", "BCH", "XLM", "ATOM", "ETC", "MATIC", "EOS",
         "ALGO", "XMR", "SOL", "DOT", "AVAX", "UNI", "FIL", "NEAR", "AAVE"]


def daily(sym: str) -> pd.DataFrame | None:
    if sym == "BTC":
        from .eksternal import asset
        h = asset("BTCUSD").b.df
    else:
        f = _dir() / f"{sym}USD.parquet"
        if not f.exists():
            return None
        h = pd.read_parquet(f)
    d = h.resample("1D").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
    if d.index[0] > pd.Timestamp("2020-10-01", tz="UTC"):
        return None
    return d


def rsi(c: pd.Series, n: int = 14) -> pd.Series:
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def entries(d: pd.DataFrame) -> dict[str, np.ndarray]:
    c = d.close
    m20, s20 = c.rolling(20).mean(), c.rolling(20).std()
    r = rsi(c)
    red = (c < d.open)
    out = {}
    for n in (20, 60):
        hi = d.high.rolling(n).max()
        for x in (10, 15, 20, 30):
            out[f"DD{n}_{x}"] = (c <= hi * (1 - x / 100)).to_numpy()
    for lv in (20, 25, 30):
        out[f"RSI{lv}"] = (r < lv).to_numpy()
    for k in (2.0, 2.5):
        out[f"BB{k}"] = (c < m20 - k * s20).to_numpy()
    out["Z2"] = ((c - m20) / s20 < -2).to_numpy()
    three = red & red.shift(1, fill_value=False) & red.shift(2, fill_value=False)
    drop3 = c / c.shift(3) - 1
    for x in (10, 15):
        out[f"MERAH3_{x}"] = (three & (drop3 <= -x / 100)).to_numpy()
    return out


def simulate(d: pd.DataFrame, sig: np.ndarray, exit_rule: tuple, sl: float | None) -> list[tuple]:
    """Return list (tanggal entry, hasil bersih %). Entry open hari berikut; satu posisi per koin."""
    o, h, lo, c = (d[k].to_numpy() for k in ("open", "high", "low", "close"))
    m20 = d.close.rolling(20).mean().to_numpy()
    kind, tp, days = exit_rule
    res, i, n = [], 0, len(d)
    while i < n - 2:
        if not sig[i]:
            i += 1
            continue
        j = i + 1
        e = o[j]
        out_px, k = None, j
        while k < n and k <= j + days:
            if sl is not None and lo[k] <= e * (1 - sl):
                out_px = min(e * (1 - sl), o[k]) if k > j else e * (1 - sl)
                break
            if kind == "tp" and h[k] >= e * (1 + tp):
                out_px = max(e * (1 + tp), o[k]) if k > j else e * (1 + tp)
                break
            if kind == "mean" and c[k] > m20[k] and k + 1 < n:
                out_px = o[k + 1]
                k += 1
                break
            k += 1
        if out_px is None:
            k = min(j + days, n - 1)
            out_px = c[k]
        res.append((d.index[j], out_px / e - 1 - COST))
        i = k + 1
    return res


def stat(rows: list[tuple]) -> dict:
    if not rows:
        return {"n": 0}
    df = pd.DataFrame(rows, columns=["t", "r"])
    lama, baru = df[df.t < SPLIT], df[df.t >= SPLIT]
    yr = df.groupby(df.t.dt.year).r.mean()
    wr = lambda x: (x.r > 0).mean() * 100 if len(x) else np.nan  # noqa: E731
    mean = lambda x: x.r.mean() * 100 if len(x) else np.nan  # noqa: E731
    return {"n": len(df), "nl": len(lama), "nb": len(baru), "wr_l": wr(lama), "wr_b": wr(baru),
            "avg_l": mean(lama), "avg_b": mean(baru), "th": (yr > 0).mean() * 100,
            "worst": df.r.min() * 100}


def main() -> None:
    data = {s: d for s in COINS if (d := daily(s)) is not None}
    print("koin:", ", ".join(data))
    rng = np.random.default_rng(3)
    exits = [("tp", tp, dd) for tp in (0.03, 0.05, 0.10) for dd in (5, 10, 20)] + \
            [("mean", 0, dd) for dd in (10, 20)]
    ent = {s: entries(d) for s, d in data.items()}
    sma200 = {s: (d.close > d.close.rolling(200).mean()).to_numpy() for s, d in data.items()}
    names = list(next(iter(ent.values())).keys())
    rows = []
    for name in names:
        for trend in (False, True):
            for ex in exits:
                for sl in (None, 0.15):
                    allr, rnd = [], []
                    for s, d in data.items():
                        sig = ent[s][name] & (sma200[s] if trend else True)
                        allr += simulate(d, sig, ex, sl)
                        # pembanding acak: jumlah hari sinyal sama, posisi acak
                        k = int(sig.sum())
                        if k:
                            rs = np.zeros(len(d), bool)
                            rs[rng.choice(len(d) - 2, size=min(k, len(d) - 2), replace=False)] = True
                            rnd += simulate(d, rs, ex, sl)
                    st, sr = stat(allr), stat(rnd)
                    if st["n"] == 0:
                        continue
                    ok = bool(st["nb"] >= 30 and st["wr_l"] >= 60 and st["wr_b"] >= 60 and st["avg_l"] > 0
                          and st["avg_b"] > 0 and st["avg_l"] > sr.get("avg_l", 0) and st["avg_b"] > sr.get("avg_b", 0)
                          and st["th"] >= 60)
                    label = (f"{name}{' +tren' if trend else ''} | {'TP ' + str(int(ex[1] * 100)) + '%' if ex[0] == 'tp' else 'balik SMA20'}"
                             f" maks {ex[2]}h | SL {'-15%' if sl else 'tanpa'}")
                    rows.append((label, st, sr, ok))
    lol = [r for r in rows if r[3]]
    L = ["# Sinyal spot 'sudah turun jauh' (research/spot_dip.py)", "",
         f"Koin: {', '.join(data)} (harian, 2017–2026). Biaya pulang-pergi 0,30%. Hasil = % per trade bersih.",
         f"Diuji {len(rows)} kombinasi. LOLOS {len(lol)}.", "",
         f"{'aturan':62} {'n':>5} {'nB':>4} {'WR L':>5} {'WR B':>5} {'avg L':>6} {'avg B':>6} {'acak L':>6} {'acak B':>6} "
         f"{'th+':>4} {'terburuk':>8}"]
    key = sorted(rows, key=lambda r: (not r[3], -(r[1]["avg_b"] if r[1]["avg_b"] == r[1]["avg_b"] else -99)))
    for label, st, sr, ok in key[:60]:
        L.append(f"{label:62} {st['n']:5} {st['nb']:4} {st['wr_l']:5.0f} {st['wr_b']:5.0f} {st['avg_l']:+6.2f} "
                 f"{st['avg_b']:+6.2f} {sr.get('avg_l', np.nan):+6.2f} {sr.get('avg_b', np.nan):+6.2f} "
                 f"{st['th']:4.0f} {st['worst']:+8.1f}  {'LOLOS' if ok else ''}")
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[:70]))


if __name__ == "__main__":
    main()
