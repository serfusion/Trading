"""Uji ketahanan sinyal spot 'sudah turun jauh' — python -m research.spot_dip2

Lanjutan research/spot_dip.py (putaran 1: 704 kombinasi, 68 lolos di 21 koin yang MASIH hidup). Putaran 1 punya
3 kelemahan yang diuji di sini:
  1. Bias koin selamat: koin yang ambruk/delisting (LUNA, FTT, SRM, UST, WAVES, BTT, MITH, ...) tidak ikut, padahal
     "beli saat turun jauh" paling berbahaya justru di koin seperti itu. Data data.binance.vision (termasuk pair yang
     sudah dihapus) via research/pair_kripto.coin; seri dipotong di celah > 3 hari (LUNA lama vs LUNA baru).
  2. Sinyal bergerombol: saat pasar ambruk banyak koin memberi sinyal di hari yang sama → n efektif jauh lebih kecil
     dan rugi datang bersamaan. Diuji dengan simulasi portofolio: modal dibagi N slot (1/N ekuitas per posisi),
     sinyal saat slot penuh dilewati, ekuitas dihitung harian (mark-to-market) → CAGR, drawdown maksimum.
  3. Pemilihan aturan setelah melihat hasil: aturan dipilih HANYA dari periode LAMA (< Okt 2021), lalu dilihat di BARU.
Biaya 0,30% pulang-pergi (fee spot 0,1%/sisi + slippage). Entry open hari berikutnya, satu posisi per koin.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from .pair_data import _dir
from .spot_dip import COINS, COST, SPLIT, entries

OUT = Path(__file__).resolve().parent.parent / "docs" / "eksternal" / "hasil_spot_dip2.txt"
MATI = ["LUNA", "LUNC", "FTT", "SRM", "UST", "WAVES", "XEM", "BTT", "MITH", "ICX", "ZEC", "DASH", "IOTA", "NEO",
        "QTUM", "OMG", "ONT", "VET", "ZIL", "BAT", "ENJ", "MANA", "SAND", "AXS", "CHZ", "HOT", "NANO", "XTZ", "KAVA",
        "COMP", "MKR", "SNX", "CRV", "SUSHI", "YFI", "EGLD", "THETA", "FTM", "RUNE", "ANKR", "WIN", "COCOS", "STRAT",
        "BCC", "VEN", "HC", "NPXS", "DENT", "KEY", "TOMO"]


def segments(sym: str) -> list[pd.DataFrame]:
    """Candle harian UTC, dipotong di celah > 3 hari; segmen < 120 hari dibuang."""
    if sym == "BTC":
        from .eksternal import asset
        h = asset("BTCUSD").b.df
    else:
        f = _dir() / f"{sym}USD.parquet"
        if not f.exists():
            return []
        h = pd.read_parquet(f)
    d = h.resample("1D").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
    d = d[(d.close > 0) & (d.low > 0)]
    cut = np.where(d.index.to_series().diff() > pd.Timedelta(days=3))[0]
    out, a = [], 0
    for b in list(cut) + [len(d)]:
        seg = d.iloc[a:b]
        if len(seg) >= 120:
            out.append(seg)
        a = b
    return out


def trades(d: pd.DataFrame, sig: np.ndarray, kind: str, tp: float, days: int, sl: float | None, coin: str) -> list[dict]:
    o, h, lo, c = (d[k].to_numpy() for k in ("open", "high", "low", "close"))
    m20 = d.close.rolling(20).mean().to_numpy()
    res, i, n = [], 0, len(d)
    while i < n - 2:
        if not sig[i]:
            i += 1
            continue
        j = i + 1
        e = o[j]
        px, k = None, j
        while k < n and k <= j + days:
            if sl is not None and lo[k] <= e * (1 - sl):
                px = min(e * (1 - sl), o[k]) if k > j else e * (1 - sl)
                break
            if kind == "tp" and h[k] >= e * (1 + tp):
                px = max(e * (1 + tp), o[k]) if k > j else e * (1 + tp)
                break
            if kind == "mean" and c[k] > m20[k] and k + 1 < n:
                k += 1
                px = o[k]
                break
            k += 1
        if px is None:
            k = min(j + days, n - 1)
            px = c[k]
        res.append({"coin": coin, "t": d.index[j], "t_out": d.index[k], "j": j, "k": k, "e": e, "x": px,
                    "r": px / e - 1 - COST})
        i = k + 1
    return res


RULES = {   # nama -> (entry, filter tren SMA200, jenis keluar, TP, maks hari, SL)
    "MERAH3_15+tren TP5% 20h": ("MERAH3_15", True, "tp", 0.05, 20, None),
    "MERAH3_10+tren TP3% 10h": ("MERAH3_10", True, "tp", 0.03, 10, None),
    "MERAH3_10+tren TP5% 10h": ("MERAH3_10", True, "tp", 0.05, 10, None),
    "DD20_30 TP5% 20h": ("DD20_30", False, "tp", 0.05, 20, None),
    "DD20_30 TP10% 10h": ("DD20_30", False, "tp", 0.10, 10, None),
    "DD20_30+tren TP5% 20h": ("DD20_30", True, "tp", 0.05, 20, None),
    "RSI30 TP10% 20h": ("RSI30", False, "tp", 0.10, 20, None),
    "RSI25 balik SMA20 20h": ("RSI25", False, "mean", 0, 20, None),
    "BB2.5+tren TP5% 10h": ("BB2.5", True, "tp", 0.05, 10, None),
    "MERAH3_10+tren TP5% 10h SL15": ("MERAH3_10", True, "tp", 0.05, 10, 0.15),
}


def rule_trades(data: dict[str, list[pd.DataFrame]], rule: tuple) -> pd.DataFrame:
    name, trend, kind, tp, days, sl = rule
    rows = []
    for coin, segs in data.items():
        for si, d in enumerate(segs):
            sig = entries(d)[name]
            if trend:
                sig = sig & (d.close > d.close.rolling(200).mean()).to_numpy()
            rows += trades(d, sig, kind, tp, days, sl, f"{coin}#{si}" if len(segs) > 1 else coin)
    return pd.DataFrame(rows)


def summary(df: pd.DataFrame) -> str:
    if df.empty:
        return "n 0"
    out = []
    for lab, m in (("LAMA", df.t < SPLIT), ("BARU", df.t >= SPLIT), ("2025+", df.t >= pd.Timestamp("2025-01-01", tz="UTC"))):
        x = df[m]
        if len(x):
            out.append(f"{lab} n{len(x)} hari{x.t.dt.normalize().nunique()} WR {(x.r > 0).mean() * 100:.0f}% "
                       f"rata {x.r.mean() * 100:+.2f}% kalah-rata {x.r[x.r <= 0].mean() * 100 if (x.r <= 0).any() else 0:+.1f}%")
    return " | ".join(out) + f" | terburuk {df.r.min() * 100:+.0f}% ({df.loc[df.r.idxmin(), 'coin']})"


def portfolio(df: pd.DataFrame, data: dict[str, list[pd.DataFrame]], slots: int, start=None, end=None) -> dict:
    """Ekuitas harian: tiap posisi 1/slots ekuitas saat entry; sinyal saat slot penuh dilewati."""
    if df.empty:
        return {}
    closes = {}
    for coin, segs in data.items():
        for si, d in enumerate(segs):
            closes[f"{coin}#{si}" if len(segs) > 1 else coin] = d.close
    df = df.sort_values(["t", "coin"])
    if start is not None:
        df = df[df.t >= start]
    if end is not None:
        df = df[df.t < end]
    if df.empty:
        return {}
    days = pd.date_range(df.t.min().normalize(), df.t_out.max().normalize(), freq="D", tz="UTC")
    cash, eq_curve, open_pos, taken = 1.0, [], [], 0
    by_day = {t: g for t, g in df.groupby(df.t.dt.normalize())}
    prev = None
    for day in days:
        def value(when):
            return sum(p["size"] * (closes[p["coin"]].asof(when) / p["e"]) for p in open_pos)
        # ukuran posisi memakai ekuitas penutupan KEMARIN (entry di open hari ini, tanpa melihat close hari ini)
        equity = cash + (value(prev) if prev is not None else sum(p["size"] for p in open_pos))
        if day in by_day:
            for _, tr in by_day[day].iterrows():
                if len(open_pos) >= slots or any(p["coin"] == tr.coin for p in open_pos):
                    continue
                size = min(equity / slots, cash)
                if size <= 0:
                    continue
                cash -= size
                open_pos.append({"coin": tr.coin, "t_out": tr.t_out, "e": tr.e, "r": tr.r, "size": size})
                taken += 1
        # posisi yang keluar hari ini (TP/batas waktu; hasil sudah termasuk biaya) baru masuk kas setelah entry hari ini
        still = []
        for p in open_pos:
            if p["t_out"].normalize() <= day:
                cash += p["size"] * (1 + p["r"])
            else:
                still.append(p)
        open_pos = still
        eq_curve.append(cash + value(day))
        prev = day
    eq = pd.Series(eq_curve, index=days)
    yrs = (days[-1] - days[0]).days / 365.25
    dd = (eq / eq.cummax() - 1).min()
    return {"akhir": eq.iloc[-1], "cagr": eq.iloc[-1] ** (1 / yrs) - 1 if yrs > 0 else 0, "dd": dd, "taken": taken,
            "n": len(df), "tahun": eq.resample("YE").last().pct_change().fillna(eq.resample("YE").last().iloc[0] - 1)}


def btc_hold(data, start, end) -> tuple[float, float]:
    c = data["BTC"][0].close
    c = c[(c.index >= start) & (c.index < end)]
    yrs = (c.index[-1] - c.index[0]).days / 365.25
    return (c.iloc[-1] / c.iloc[0]) ** (1 / yrs) - 1, (c / c.cummax() - 1).min()


def main() -> None:
    hidup = {s: segs for s in COINS if (segs := segments(s))}
    mati = {s: segs for s in MATI if (segs := segments(s))}
    semua = {**hidup, **mati}
    L = ["# Uji ketahanan sinyal spot 'sudah turun jauh' (research/spot_dip2.py)", "",
         f"Koin hidup ({len(hidup)}): {', '.join(hidup)}",
         f"Koin ambruk/delisting/lama ({len(mati)}): {', '.join(mati)}",
         "Biaya 0,30% pulang-pergi. hari = jumlah hari berbeda (sinyal bergerombol). LAMA < Okt 2021.", ""]
    L.append("## 1. Per trade: koin hidup saja vs + koin ambruk")
    allt = {}
    for nm, rule in RULES.items():
        a = rule_trades(hidup, rule)
        b = rule_trades(semua, rule)
        allt[nm] = b
        L += [f"{nm}", f"   hidup : {summary(a)}", f"   semua : {summary(b)}"]
    L += ["", "## 2. Portofolio (modal dibagi slot, 1/slot ekuitas per posisi, semua koin termasuk yang ambruk)"]
    t0, t1 = pd.Timestamp("2018-01-01", tz="UTC"), pd.Timestamp("2026-10-01", tz="UTC")
    for lab, s, e in (("LAMA 2018–Sep 2021", t0, SPLIT), ("BARU Okt 2021–2026", SPLIT, t1)):
        bc, bd = btc_hold(semua, s, e)
        L.append(f"-- {lab}: pembanding BTC beli-tahan CAGR {bc * 100:+.0f}%/th, DD {bd * 100:.0f}%")
        for nm, df in allt.items():
            for slots in (5, 10):
                p = portfolio(df, semua, slots, s, e)
                if p:
                    L.append(f"   {nm:32} slot {slots:2}: CAGR {p['cagr'] * 100:+6.1f}%/th  DD {p['dd'] * 100:6.1f}%  "
                             f"diambil {p['taken']}/{p['n']}")
    L += ["", "## 3. Pilih dari LAMA saja, lihat BARU (semua koin)"]
    rank = sorted(((nm, df[df.t < SPLIT].r.mean(), df[df.t >= SPLIT]) for nm, df in allt.items()),
                  key=lambda x: -x[1])
    for nm, lama, baru in rank:
        L.append(f"   {nm:32} LAMA rata {lama * 100:+.2f}% -> BARU rata {baru.r.mean() * 100:+.2f}% "
                 f"WR {(baru.r > 0).mean() * 100:.0f}% (n {len(baru)})")
    best = rank[0][0]
    p = portfolio(allt[best], semua, 5, SPLIT, t1)
    if p:
        L += ["", f"Per tahun (BARU, slot 5) aturan terbaik LAMA '{best}':"]
        L += [f"   {t.year}: {v * 100:+.0f}%" for t, v in p["tahun"].items()]
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    sys.exit(main())
