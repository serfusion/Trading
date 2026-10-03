"""Uji Polymarket: tebakan kejutan (Act vs konsensus FF) & keputusan Fed. python -m research.polymarket uji
Aturan: docstring research/polymarket.py & research/kalshi_uji.py (ditetapkan sebelum melihat hasil).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .kalshi_uji import accuracy, rows as kalshi_rows
from .news_data import INVERSE, _num, load_calendar
from .polymarket import load, probs, split
from .run_scan import DATA

HORIZON = {"24 jam": 24, "6 jam": 6, "1 jam": 1, "saat tutup": 0.05}
OUT = Path(__file__).resolve().parent.parent / "docs" / "eksternal" / "hasil_polymarket.txt"
SERI = {"CPI m/m": "KXCPI", "Core CPI m/m": "KXCPICORE", "Non-Farm Employment Change": "KXPAYROLLS",
        "Unemployment Rate": "KXU3"}


def rows() -> pd.DataFrame:
    """Satu baris per rilis yang punya event Polymarket & konsensus FF: P(atas/bawah) per horizon."""
    cal = load_calendar(DATA)
    out = []
    for d in load():
        if d["jenis"] == "Federal Funds Rate":
            continue
        akhir = pd.Timestamp(d["akhir"]) if d.get("akhir") else None
        if akhir is None:
            continue
        cc = cal[(cal.event == d["jenis"]) & ((cal.time - akhir).abs() <= pd.Timedelta(days=3))]
        if not len(cc):
            continue
        r = cc.iloc[((cc.time - akhir).abs()).argmin()]
        cons, act = _num(r.forecast), _num(r.actual)
        if cons != cons or act != act:
            continue
        cont = d["jenis"] == "Non-Farm Employment Change"
        if cont:
            cons, act = cons / 1000, act / 1000                       # keranjang NFP dalam ribu
        row = {"seri": SERI[d["jenis"]], "jenis": d["jenis"], "slug": d["slug"], "t0": r.time, "cons": cons,
               "act": act, "kejutan": float(np.sign(round(act - cons, 6))), "terbalik": d["jenis"] in INVERSE,
               "volume": float(d.get("volume") or 0)}
        for lab, h in HORIZON.items():
            s = split(probs(d["pasar"], (r.time - pd.Timedelta(hours=h)).timestamp()), cons, cont)
            row[f"atas {lab}"], row[f"bawah {lab}"] = (s["atas"], s["bawah"]) if s else (np.nan, np.nan)
            row[f"lean {lab}"] = row[f"atas {lab}"] - row[f"bawah {lab}"]
        out.append(row)
    return pd.DataFrame(out)


def fed() -> list[str]:
    cal = load_calendar(DATA)
    cc = cal[cal.event == "Federal Funds Rate"]
    L = []
    for d in load():
        if d["jenis"] != "Federal Funds Rate" or not d.get("akhir"):
            continue
        akhir = pd.Timestamp(d["akhir"])
        g = cc[(cc.time - akhir).abs() <= pd.Timedelta(days=3)]
        if not len(g):
            continue
        r = g.iloc[((g.time - akhir).abs()).argmin()]
        cons, prev, act = _num(r.forecast), _num(r.previous), _num(r.actual)
        if cons != cons or prev != prev:
            continue
        bp = round((cons - prev) * 100)
        want = "no change" if bp == 0 else f"{abs(bp)} bps {'decrease' if bp < 0 else 'increase'}"
        m = [x for x in d["pasar"] if want in (x["keranjang"] or "").lower()]
        ts = (r.time - pd.Timedelta(hours=1)).timestamp()
        h = [p for t, p in (m[0]["harga"] if m else []) if t <= ts]
        L.append(f"  {r.time:%Y-%m-%d} konsensus {want:16} peluang Polymarket 1 jam sebelum "
                 f"{'-' if not h else f'{h[-1] * 100:.0f}%'} | hasil {'SESUAI' if act == cons else 'KEJUTAN'} | "
                 f"volume ${float(d.get('volume') or 0):,.0f}")
    return sorted(L)


def report() -> str:
    df = rows()
    L = ["# Polymarket: peluang hasil berita sebelum rilis (research/polymarket_uji.py)", ""]
    if df.empty:
        return "\n".join(L + ["Tidak ada rilis yang cocok dengan konsensus ForexFactory."]) + "\n"
    L.append(f"Rilis cocok dengan konsensus FF: {len(df)} ({df.t0.min():%Y-%m}..{df.t0.max():%Y-%m}); per jenis "
             f"{df.jenis.value_counts().to_dict()}; volume median ${df.volume.median():,.0f}")
    L.append("\n== Akurasi menebak arah kejutan (rilis dengan kejutan; selisih peluang >= 10 poin) ==")
    for jenis in ["SEMUA"] + sorted(df.jenis.unique()):
        x = df if jenis == "SEMUA" else df[df.jenis == jenis]
        for lab in HORIZON:
            a = accuracy(x, lab, 0.10)
            if a["n"]:
                L.append(f"  {jenis:28} {lab:10} ditebak {a['n_tebak']:3} | kejutan n={a['n']:3} benar {a['benar']:5.1f}% "
                         f"| sama dengan Cons {a['sama']:4.1f}%")
    L.append("\n== Polymarket vs Kalshi pada rilis yang SAMA (24 jam sebelum, selisih >= 10 poin) ==")
    kr = kalshi_rows()
    for jenis, seri in SERI.items():
        p = df[df.jenis == jenis][["t0", "lean 24 jam", "kejutan"]].rename(columns={"lean 24 jam": "poly"})
        k = kr[kr.seri == seri][["t0", "lean 24 jam"]].rename(columns={"lean 24 jam": "kalshi"})
        m = p.merge(k, on="t0")
        m = m[m.kejutan != 0]
        if not len(m):
            continue
        cells = []
        for col in ("poly", "kalshi"):
            z = m[m[col].abs() >= 0.10]
            cells.append(f"{col} benar {(np.sign(z[col]) == z.kejutan).mean() * 100:4.1f}% (n={len(z)})" if len(z)
                         else f"{col} -")
        both = m[(m.poly.abs() >= .1) & (m.kalshi.abs() >= .1) & (np.sign(m.poly) == np.sign(m.kalshi))]
        cells.append(f"keduanya sepakat benar {(np.sign(both.poly) == both.kejutan).mean() * 100:4.1f}% (n={len(both)})"
                     if len(both) else "sepakat -")
        L.append(f"  {jenis:28} " + " | ".join(cells))
    L.append("\n== Keputusan Fed: peluang Polymarket untuk hasil konsensus ==")
    L += fed()
    return "\n".join(L) + "\n"


def main() -> None:
    txt = report()
    OUT.write_text(txt, encoding="utf-8")
    print(txt)
    print(f"ditulis {OUT}")
