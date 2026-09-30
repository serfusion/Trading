"""Uji ulang "mode perang" dengan proksi minyak Twelve Data (ETF USO = WTI, BNO = Brent) (python -m research.perang_uso
[--duka]).

Latar: WTI/USD & Brent di Twelve Data butuh paket berbayar; yang gratis hanya ETF USO/BNO (harian, jam NYSE). Twelve
Data XAU/USD harian dipakai untuk studi kejadian emas. Aturan ditetapkan sebelum melihat hasil:

A. Filter XAU 💰 (sama dengan research/mode_perang.py, sumber pemicu diganti): mode perang = close USO/BNO naik >= X%
   dalam N hari bursa, dipakai sejak 21:15 UTC hari itu (sesudah NYSE tutup, aman untuk musim panas & dingin).
   Kisi N = 5/10/20 × X = 5/7,5/10/15%, kriteria konsisten = judge() di mode_perang. Uji nyata: jeda 💰 selama
   USO (dan BNO) >= +10%/10 hari. Dibandingkan dengan pemicu FRED (yang dipasang di cloud).
B. Peluang trade (sama dengan research/perang_peluang.py): pemicu USO/BNO >= 10% / 15% dalam 10 hari, entry di open
   hari bursa berikutnya, arah dari LAMA saja, SL 2 × ATR20, TP 1R/2R, tutup paksa 10 hari, SL dicek dulu.
   Aset: USO, BNO, XAU. Biaya: 0,05% harga per trade (kira-kira spread USOIL/XAU di broker, dinyatakan dalam R).
"Positif" = A: kombinasi 10 hari >= 10% konsisten DAN uji nyata membaik di LAMA & BARU; B: KANDIDAT (arah sama,
t > 2, untung di LAMA & BARU). Hanya bila positif, hasil dicek ulang dengan data Dukascopy (LIGHTCMDUSD/BRENTCMDUSD).
"""
from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request

import numpy as np
import pandas as pd

from .eksternal import asof, cache_path
from .eksternal_makro import fred
from .momen import base_entries, line
from .mode_perang import judge, lookup, real_summary
from .perang_peluang import NEW, forward, triggers, trade, tstat

COST = 0.0005


def twelvedata_d1(symbol: str) -> pd.DataFrame:
    """Candle harian Twelve Data (cache JSON; butuh TWELVEDATA_API_KEY, 1 kredit per simbol)."""
    path = cache_path(f"twelvedata_{symbol.replace('/', '')}_d1.json")
    if not path.exists():
        q = urllib.parse.urlencode({"symbol": symbol, "interval": "1day", "outputsize": 5000, "order": "ASC",
                                    "apikey": os.environ.get("TWELVEDATA_API_KEY", "")})
        with urllib.request.urlopen("https://api.twelvedata.com/time_series?" + q, timeout=60) as r:
            raw = r.read()
        if json.loads(raw).get("status") != "ok":
            raise SystemExit(f"Twelve Data {symbol}: {json.loads(raw).get('message')}")
        path.write_bytes(raw)
    v = pd.DataFrame(json.loads(path.read_text())["values"])
    df = v[["open", "high", "low", "close"]].astype(float)
    df.index = pd.DatetimeIndex(pd.to_datetime(v.datetime)).tz_localize("UTC")
    return df[~df.index.duplicated(keep="last")].sort_index()


def dukascopy_d1(sym: str) -> pd.DataFrame:
    """Candle harian BID Dukascopy (hari UTC; python -m research.dukascopy d1 2011 2026 <sym>). Candle Minggu
    (pasar baru buka ±22:00 UTC) digabung ke hari Senin agar "N hari bursa" sama dengan sumber lain."""
    df = pd.read_parquet(cache_path(f"dukascopy/{sym}_d1_BID.parquet"))
    return df[df.index.dayofweek < 5]


# sumber pemicu: (close, waktu terbit close itu)
def src_twelve(df: pd.DataFrame) -> tuple[pd.Series, pd.DatetimeIndex]:
    return df.close, df.index + pd.Timedelta(hours=21, minutes=15)          # sesudah NYSE tutup


def src_duka(df: pd.DataFrame) -> tuple[pd.Series, pd.DatetimeIndex]:
    return df.close, df.index + pd.Timedelta(days=1, minutes=5)             # candle hari UTC selesai


def src_fred(series: str) -> tuple[pd.Series, pd.DatetimeIndex]:
    f = fred(series)
    return f.value, pd.DatetimeIndex(f.available)


def war_at(t: pd.DatetimeIndex, src: tuple[pd.Series, pd.DatetimeIndex], n: int, thr: float) -> np.ndarray:
    close, av = src
    return asof(t, close / close.shift(n) - 1, av) >= thr


def grid(e: pd.DataFrame, sources: dict) -> None:
    t = pd.DatetimeIndex(e.t)
    for lab, src in sources.items():
        ok_n = 0
        for n in (5, 10, 20):
            for thr in (0.05, 0.075, 0.10, 0.15):
                txt, ok = judge(e, war_at(t, src, n, thr))
                ok_n += ok
                print(f"{lab} +{thr:.1%}/{n}h: {txt}{'  KONSISTEN' if ok else ''}")
        print(f"-> {lab}: konsisten {ok_n} dari 12 kombinasi\n")


def real(name: str, rule, tag: str) -> None:
    """Uji nyata: rule(t) -> bool di waktu candle sinyal; jeda 💰 selama True."""
    real_summary(name, lambda t, d: bool(rule(pd.DatetimeIndex([t]))[0]), tag)


def part_a(oil: dict) -> None:
    print("## A. Filter XAU 💰 dengan pemicu USO/BNO\n")
    e = base_entries("XAUUSD")
    print(f"dasar LAMA {line(e.R[e.per == 'LAMA'])} | BARU {line(e.R[e.per == 'BARU'])}")
    grid(e, oil)
    t = pd.DatetimeIndex(e.t)
    f_war = war_at(t, src_fred("DCOILWTICO"), 10, 0.10)
    for lab, src in oil.items():
        u_war = war_at(t, src, 10, 0.10)
        print(f"tumpang tindih sinyal perang (>= 10%/10h) FRED WTI {f_war.sum()} vs {lab} {u_war.sum()}: "
              f"sama {(f_war & u_war).sum()}, hanya FRED {(f_war & ~u_war).sum()}, hanya {lab} {(u_war & ~f_war).sum()}")
    print("\nUji nyata (jeda 💰 selama pemicu aktif, sinyal berikutnya boleh masuk):")
    for lab, src in oil.items():
        real("XAUUSD", lambda t, src=src: war_at(t, src, 10, 0.10), f"jeda {lab} >= 10%/10h")
    print()


def part_c(sources: dict) -> None:
    """Dukascopy + gabungan sumber (hanya dijalankan bila A positif)."""
    print("## C. Dukascopy WTI/Brent & gabungan sumber (>= 10% dalam 10 hari)\n")
    e = base_entries("XAUUSD")
    grid(e, {k: v for k, v in sources.items() if k.startswith("Duka")})
    t = pd.DatetimeIndex(e.t)
    flags = {k: war_at(t, v, 10, 0.10) for k, v in sources.items()}
    wti = ("FRED WTI", "USO", "Duka WTI")
    combos = {
        "FRED WTI (dipasang)": lambda tt: war_at(tt, sources["FRED WTI"], 10, 0.10),
        "Duka WTI": lambda tt: war_at(tt, sources["Duka WTI"], 10, 0.10),
        "Duka Brent": lambda tt: war_at(tt, sources["Duka Brent"], 10, 0.10),
        "WTI salah satu (FRED/USO/Duka)": lambda tt: np.any([war_at(tt, sources[k], 10, 0.10) for k in wti], 0),
        "WTI >= 2 dari 3": lambda tt: np.sum([war_at(tt, sources[k], 10, 0.10) for k in wti], 0) >= 2,
        "USO atau Duka WTI (tanpa FRED)": lambda tt: np.any([war_at(tt, sources[k], 10, 0.10)
                                                             for k in ("USO", "Duka WTI")], 0),
        "semua 5 sumber, salah satu": lambda tt: np.any([war_at(tt, s, 10, 0.10) for s in sources.values()], 0),
    }
    print("sinyal 💰 yang ditandai perang per sumber: " + ", ".join(f"{k} {v.sum()}" for k, v in flags.items()))
    for lab in ("WTI salah satu (FRED/USO/Duka)", "WTI >= 2 dari 3", "USO atau Duka WTI (tanpa FRED)",
                "semua 5 sumber, salah satu"):
        txt, ok = judge(e, combos[lab](t))
        print(f"{lab}: {txt}{'  KONSISTEN' if ok else ''}")
    print("\nUji nyata:")
    for lab, rule in combos.items():
        real("XAUUSD", rule, lab)
    print()


def part_b(data: dict[str, pd.DataFrame]) -> None:
    print("## B. Peluang trade setelah lonjakan minyak (USO/BNO sebagai pemicu & aset)\n")
    for trig in ("USO", "BNO"):
        for thr in (0.10, 0.15):
            days = triggers(data[trig], thr)
            old, new = days[days < NEW], days[days >= NEW]
            print(f"### Pemicu {trig} naik >= {thr:.0%} dalam 10 hari: {len(days)} episode (LAMA {len(old)}, "
                  f"BARU {len(new)})")
            print("   episode BARU: " + ", ".join(f"{d:%Y-%m-%d}" for d in new))
            for a, df in data.items():
                cells = []
                for h in (1, 5, 10, 20):
                    f = forward(df, days, h)
                    fo, fn = f[f.index < NEW], f[f.index >= NEW]
                    cells.append(f"{h}h {fo.mean():+.2f}/{fn.mean():+.2f}% (t {tstat(f):+.1f})")
                print(f"   {a:4s} LAMA/BARU: " + " | ".join(cells))
            for a, df in data.items():
                f5 = forward(df, days, 5)
                d = 1 if f5[f5.index < NEW].mean() > 0 else -1
                for tp in (1.0, 2.0):
                    r = trade(df, days, d, tp, cost=COST)
                    ro, rn = r[r.index < NEW], r[r.index >= NEW]
                    flag = "  <- KANDIDAT" if (len(ro) >= 8 and len(rn) >= 3 and ro.mean() > 0 and rn.mean() > 0
                                               and tstat(f5 * d) > 2) else ""
                    print(f"      {a:4s} {'BUY ' if d > 0 else 'SELL'} TP {tp:.0f}R: LAMA n={len(ro)} "
                          f"WR={100 * (ro > 0).mean():.0f}% {ro.mean():+.2f}R | BARU n={len(rn)} "
                          f"WR={100 * (rn > 0).mean() if len(rn) else 0:.0f}% "
                          f"{rn.mean() if len(rn) else 0:+.2f}R{flag}")
            print()


def main():
    print("# Uji ulang mode perang dengan proksi Twelve Data USO/BNO (research/perang_uso.py)\n")
    data = {"USO": twelvedata_d1("USO"), "BNO": twelvedata_d1("BNO"), "XAU": twelvedata_d1("XAU/USD")}
    for k, df in data.items():
        print(f"{k}: {len(df)} hari {df.index[0]:%Y-%m-%d} .. {df.index[-1]:%Y-%m-%d}")
    print()
    part_a({"USO": src_twelve(data["USO"]), "BNO": src_twelve(data["BNO"])})
    part_b(data)
    if "--duka" in sys.argv:
        part_c({"FRED WTI": src_fred("DCOILWTICO"), "FRED Brent": src_fred("DCOILBRENTEU"),
                "USO": src_twelve(data["USO"]), "Duka WTI": src_duka(dukascopy_d1("LIGHTCMDUSD")),
                "Duka Brent": src_duka(dukascopy_d1("BRENTCMDUSD"))})


if __name__ == "__main__":
    main()
