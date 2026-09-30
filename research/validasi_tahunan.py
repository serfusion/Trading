"""Validasi per TAHUN (lampau s.d. sekarang): arah "hentakan" emas beberapa detik setelah berita vs arah kejutan,
dan tebakan Kalshi. python -m research.validasi_tahunan -> docs/eksternal/hasil_validasi_tahunan.txt

Pertanyaan pengguna (30 Sep 2026): "data yang kamu cocokkan untuk prediksi hentakan beberapa detik setelah news valid
dalam tahun lampau hingga sekarang?"

Aturan (ditetapkan sebelum melihat hasil):
A. Hentakan vs kejutan konsensus ForexFactory (s.d. Jan 2026): per tahun, % rilis yang gerak mid emas dari t0-1 dtk
   ke t0+2 / +5 / +60 dtk searah kejutan (data lemah untuk USD -> emas naik). Semua berita bintang 3, CPI, NFP.
B. 2026 (konsensus FF tidak tersedia): kejutan diukur terhadap EKSPEKTASI PASAR Kalshi saat pasar tutup = angka
   dengan peluang terbesar (CPI, core CPI, pengangguran: selisih peluang antar strike 0,1; NFP: median interpolasi).
   Hasil dibandingkan dengan cara yang sama di 2022-2025 agar setara.
C. Tebakan Kalshi 24 jam sebelum (research/kalshi_uji.py) per tahun: arah kejutan CPI & core CPI benar berapa %.
Tick: Exness (2015-2026) dan Dukascopy (2010-2026).
"""
from __future__ import annotations

import glob
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .eksternal import cache_path
from .kalshi import SERIES
from .kalshi_uji import accuracy, rows as kalshi_rows, strike
from .news_data import INVERSE
from .news_detik import EXNESS, events, prepare

OUT = Path(__file__).resolve().parent.parent / "docs" / "eksternal" / "hasil_validasi_tahunan.txt"
SECS = [2, 5, 60]
FEEDS = {"XAU_EXNESS": "Exness", "XAU": "Dukascopy"}


def moves(aset: str, times: list[pd.Timestamp]) -> dict:
    """waktu -> {detik: gerak mid dari t0-1} (None bila tick tidak ada)."""
    out = {}
    for t in times:
        p = prepare(t, aset)
        if p is None:
            continue
        i = p.at(-1)
        if i < 0:
            continue
        out[t] = {s: float(p.mid[p.at(s)] - p.mid[i]) for s in SECS}
    return out


def table(df: pd.DataFrame, mv: dict, label: str) -> list[str]:
    """df: time, bias (+1 emas naik / -1 turun). Baris per tahun: % searah di +2/+5/+60 dtk."""
    L = []
    rows = [(r.time, r.bias, mv[r.time]) for r in df.itertuples() if r.time in mv and r.bias in (1.0, -1.0)]
    if not rows:
        return L
    x = pd.DataFrame([{"tahun": t.year, **{f"s{s}": np.sign(m[s]) * b for s in SECS}} for t, b, m in rows])
    for yr, g in list(x.groupby("tahun")) + [("SEMUA", x)]:
        cells = " | ".join(f"+{s} dtk {(g[f's{s}'] > 0).mean() * 100:3.0f}%" for s in SECS)
        L.append(f"  {label:26} {yr!s:5} n={len(g):4} | {cells}")
    return L


def kalshi_expect(ms: list[dict], step: float | None) -> float | None:
    """Angka paling mungkin menurut Kalshi saat pasar tutup (candle terakhir)."""
    pts = []
    for m in ms:
        k = strike(m)
        c = m.get("candle") or []
        if k is None or not c:
            continue
        _, bid, ask, last, _ = c[-1]
        p = (bid + ask) / 2 if bid is not None and ask is not None and ask >= bid else last
        if p is not None:
            pts.append((k, p))
    pts.sort()
    if len(pts) < 2:
        return None
    if step:                                                   # modus: P(X = v) = P(> v - step) - P(> v)
        best, bp = None, -1.0
        for (k0, p0), (k1, p1) in zip(pts, pts[1:]):
            if abs(k1 - k0 - step) < 1e-9 and p0 - p1 > bp:
                best, bp = k1, p0 - p1
        return best
    for (k0, p0), (k1, p1) in zip(pts, pts[1:]):               # median: P(> x) = 0,5
        if p0 >= 0.5 >= p1 and p0 != p1:
            return k0 + (k1 - k0) * (p0 - 0.5) / (p0 - p1)
    return None


def kalshi_surprises() -> pd.DataFrame:
    """Semua event Kalshi yang selesai (2021-2026): waktu rilis, arah kejutan untuk emas vs ekspektasi Kalshi."""
    out = []
    for series, (name, step) in SERIES.items():
        if series == "KXFEDDECISION":
            continue
        for f in sorted(glob.glob(str(cache_path(f"kalshi/{series}") / "*.json"))):
            d = json.loads(Path(f).read_text(encoding="utf-8"))
            ms = d["pasar"]
            try:
                act = float(str(ms[0].get("nilai")).replace(",", ""))
            except (TypeError, ValueError):
                continue
            exp = kalshi_expect(ms, step)
            if exp is None:
                continue
            close = min(pd.Timestamp(m["tutup"]) for m in ms)
            t0 = close.ceil("30min") if close.minute >= 25 else close   # 12:25 / 12:29 -> 12:30
            usd = np.sign(round(act - exp, 6)) * (-1 if name in INVERSE else 1)
            if usd != 0:
                out.append({"time": t0, "seri": series, "bias": -float(usd)})
    df = pd.DataFrame(out)
    # CPI & core CPI rilis bersamaan: satu arah per waktu (jumlah)
    g = df.groupby(["time", df.seri.isin(["KXCPI", "KXCPICORE"])]).agg(bias=("bias", "sum"), seri=("seri", "first"))
    g = g.reset_index(level=1, drop=True).reset_index()
    g["bias"] = np.sign(g.bias)
    return g[g.bias != 0]


def report() -> str:
    L = ["# Validasi per tahun: hentakan emas setelah berita (research/validasi_tahunan.py)", ""]
    ev = events()
    ev = ev[ev.bias.isin([1.0, -1.0])]
    ks = kalshi_surprises()
    times = sorted(set(ev.time) | set(ks.time))
    mv = {a: moves(a, times) for a in FEEDS}
    L.append("== A. Hentakan searah kejutan KONSENSUS ForexFactory (s.d. Jan 2026) ==")
    for a, name in FEEDS.items():
        L += table(ev, mv[a], f"{name} semua bintang 3")
        L += table(ev[ev.group == "CPI"], mv[a], f"{name} CPI")
        L += table(ev[ev.group == "NFP"], mv[a], f"{name} NFP")
        L.append("")
    L.append("== B. Hentakan searah kejutan terhadap EKSPEKTASI Kalshi (2021-2026, termasuk 2026) ==")
    for a, name in FEEDS.items():
        L += table(ks, mv[a], f"{name} Kalshi semua")
        L += table(ks[ks.seri.isin(["KXCPI", "KXCPICORE"])], mv[a], f"{name} Kalshi CPI")
        L += table(ks[ks.seri.isin(["KXPAYROLLS", "KXU3"])], mv[a], f"{name} Kalshi NFP+pengangguran")
        L.append("")
    L.append("== C. Tebakan Kalshi 24 jam sebelum: arah kejutan CPI & core CPI benar (konsensus FF, 2022-2025) ==")
    kr = kalshi_rows()
    cpi = kr[kr.seri.isin(["KXCPI", "KXCPICORE"])]
    for yr, g in list(cpi.groupby(cpi.t0.dt.year)) + [("SEMUA", cpi)]:
        a = accuracy(g, "24 jam", 0.10)
        if a["n"]:
            L.append(f"  CPI+core {yr!s:5} kejutan n={a['n']:3} benar {a['benar']:5.1f}% | sama dengan Cons {a['sama']:4.1f}%")
    return "\n".join(L) + "\n"


def main() -> None:
    txt = report()
    OUT.write_text(txt, encoding="utf-8")
    print(txt)
    print(f"ditulis {OUT}")


if __name__ == "__main__":
    main()
