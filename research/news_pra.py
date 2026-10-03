"""Entry 1 detik SEBELUM berita keluar, tutup 1-3 detik setelah entry: bisakah arahnya ditebak?

python -m research.news_pra            # XAU Exness (broker pengguna) + Dukascopy pembanding -> docs/eksternal/hasil_news_pra.txt

Permintaan pengguna (30 Sep 2026): "1 detik sebelum news keluar saya akan entry ... saya harap kamu bisa memprediksi
kejutannya karena 1-3 detik saya akan close posisi setelah entry".

Aturan (ditetapkan sebelum melihat hasil):
- Tick XAU asli Exness Cent (XAUUSDc 2015-2026) dan Dukascopy (2010-2026) sebagai pembanding; semua rilis berita USD
  bintang 3 (research/news_detik.events()); t0 = waktu rilis resmi.
- Entry: keputusan di t0-1 dtk. CEPAT = terisi di kutipan t0-1 dtk tanpa slippage. REALISTIS = terisi 0,5 dtk kemudian
  (kutipan t0-0,5) + slippage $0,30. BUY di ASK, SELL di BID.
- Tutup: h = 1, 2, 3 dtk setelah entry terisi (REALISTIS: + 0,5 dtk sampai terisi dan slippage $0,30 lagi, karena
  tutup terjadi di tengah lonjakan). Pembanding: tahan sampai t0+5 / t0+10 / t0+60 dtk.
- Arah (hanya informasi yang SUDAH ADA sebelum t0):
  SELALU BUY / SELALU SELL;
  ULANG     = arah kejutan rilis sebelumnya di grup yang sama terulang (<= 45 hari; klaim <= 10 hari);
  ACT->PREV = Act cenderung ke arah angka Prev (tanda Act - Cons = tanda Prev - Cons);
  P...      = petunjuk yang TERBUKTI menebak arah kejutan di research/news_prediksi.py (untuk CPI);
  DRIFT n / LAWAN n = ikut / lawan gerak harga n detik terakhir sebelum t0-1 (n = 10, 30, 60, 110);
  ORAKEL    = arah kejutan sebenarnya (TIDAK mungkin diketahui sebelum rilis) -> batas atas "tebakan 100% benar".
  Arah emas dari kejutan: data lebih lemah untuk USD -> BUY emas (sama dengan riset lain).
- Akurasi minimal agar impas (dari ORAKEL): p* = -rata(salah) / (rata(benar) - rata(salah)).
- Lolos bila rata > 0 di LAMA (< Okt 2021) dan BARU, >= 60% tahun positif, t > 2, REALISTIS > 0 (n >= 30), dan
  positif di KEDUA feed. Banyak kombinasi diuji -> satu dua yang "lolos" di satu feed bisa kebetulan.
- Cek jam feed: gerak t0-1 -> t0 (sebelum angka keluar) searah kejutan? Bila jauh di atas 50%, jam feed meleset / ada
  kebocoran, dan hasil entry t0-1 di feed itu tidak bisa dipercaya.
- Hasil dalam $ per ons = $ per 0,01 lot (akun Cent: sen).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from . import news_prediksi as npd
from .news_data import INVERSE, _num
from .news_detik import EXNESS, NEW, events, fmt, judge, prepare, stats

H = [1, 2, 3]
HOLD = {"t0+5s": 6.0, "t0+10s": 11.0, "t0+60s": 61.0}     # detik setelah entry CEPAT (entry di t0-1)
SCEN = {"CEPAT": (0.0, 0.0), "REALISTIS": (0.5, 0.3)}      # (latensi dtk, slippage $) di entry & tutup
DRIFT = [10, 30, 60, 110]
FEEDS = {"XAU_EXNESS": "Exness", "XAU": "Dukascopy"}
GROUPS = ["SEMUA", "NFP", "CPI", "PPI", "ADP", "RETAIL", "GDP", "PCE", "ISM", "CLAIMS", "FOMC", "JOLTS"]
OUT = Path(__file__).resolve().parent.parent / "docs" / "eksternal" / "hasil_news_pra.txt"


def simple_clues(ev: pd.DataFrame) -> dict[str, pd.Series]:
    """Petunjuk dari baris ev saja: nama -> arah emas (+1 BUY / -1 SELL / NaN tidak entry), info sebelum t0."""
    out = {"SELALU BUY": pd.Series(1.0, index=ev.index), "SELALU SELL": pd.Series(-1.0, index=ev.index)}
    rep, last = {}, {}
    for i, r in ev.iterrows():
        prev = last.get(r.group)
        lim = 10 if r.group == "CLAIMS" else 45
        if prev is not None and (r.time - prev[0]).days <= lim and prev[1] in (1.0, -1.0):
            rep[i] = prev[1]
        last[r.group] = (r.time, r.bias)
    out["ULANG kejutan sebelumnya"] = pd.Series(rep, dtype=float).reindex(ev.index)
    cp = {}
    for i, r in ev.iterrows():
        f, pv = _num(r.forecast), _num(r.previous)
        if f == f and pv == pv and pv != f and isinstance(r.event, str):
            usd = np.sign(pv - f) * (-1 if r.event in INVERSE else 1)      # tebakan kejutan untuk USD
            cp[i] = -usd
    out["ACT->PREV"] = pd.Series(cp, dtype=float).reindex(ev.index)
    return out


def clues(ev: pd.DataFrame) -> dict[str, pd.Series]:
    """simple_clues + petunjuk yang terbukti di research/news_prediksi.py."""
    out = simple_clues(ev)
    # petunjuk yang terbukti menebak arah kejutan (news_prediksi) -> arah emas per waktu rilis
    cal = npd.calendar()
    by_time = {t: i for i, t in zip(ev.index, ev.time)}
    for name, (target, pred) in npd.predictors(cal).items():
        if not npd.judge(cal, target, pred)["terbukti"]:
            continue
        s = {}
        for ci, v in pred.dropna().items():
            i = by_time.get(cal.time[ci])
            if i is not None and v != 0:
                s[i] = -float(np.sign(v)) * (-1 if target in npd.INVERSE else 1)
        out[name.split(":")[0]] = pd.Series(s, dtype=float).reindex(ev.index)
    return out


def pnl(p, d: int, lat: float, slip: float, h: float) -> float:
    """Entry keputusan t0-1 (terisi t0-1+lat), tutup h dtk setelah terisi (+lat) -> $/ons."""
    i = p.at(-1 + lat)
    j = p.at(-1 + lat + h + lat)
    if i < 0 or p.T[i] < -60:
        return np.nan
    return float((p.bid[j] - p.ask[i]) if d > 0 else (p.bid[i] - p.ask[j])) - 2 * slip


def run(aset: str, ev: pd.DataFrame, cl: dict[str, pd.Series]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(trades, arah): trades = satu baris per (rilis, petunjuk, skenario, h); arah = gerak mid vs kejutan."""
    if aset in EXNESS:
        ev = ev[ev.time >= EXNESS[aset][1]]
    tr, ar = [], []
    for i, r in ev.iterrows():
        p = prepare(r.time, aset)
        if p is None:
            continue
        m1 = p.mid[p.at(-1)]
        row = {"time": r.time, "group": r.group, "bias": r.bias}
        for k in (-5, 0, 1, 2, 3, 5, 10, 60):                    # gerak mid dari t0-1 (dan t0-5 -> t0-1)
            row[f"g{k}"] = float((p.mid[p.at(k)] - m1) if k != -5 else (m1 - p.mid[p.at(-5)]))
        row["spread"] = float(p.ask[p.at(-1)] - p.bid[p.at(-1)])
        ar.append(row)
        dirs = {name: s.get(i, np.nan) for name, s in cl.items()}
        if r.bias in (1.0, -1.0):
            dirs["ORAKEL (kejutan diketahui)"] = r.bias
            dirs["ORAKEL SALAH (kebalikan)"] = -r.bias
        for n in DRIFT:
            j = p.at(-1 - n)
            if j < 0:                                  # belum ada tick (indeks -1 = tick TERAKHIR -> bocor)
                continue
            mv = m1 - p.mid[j]
            if abs(mv) >= 0.01:
                dirs[f"DRIFT {n}s"] = float(np.sign(mv))
                dirs[f"LAWAN {n}s"] = -float(np.sign(mv))
        for name, d in dirs.items():
            if d not in (1.0, -1.0):
                continue
            for sc, (lat, slip) in SCEN.items():
                for h in H:
                    tr.append({"time": r.time, "group": r.group, "arah": name, "sc": sc, "h": f"{h}s",
                               "pnl": pnl(p, int(d), lat, slip, h)})
            for lab, h in HOLD.items():
                tr.append({"time": r.time, "group": r.group, "arah": name, "sc": "CEPAT", "h": lab,
                           "pnl": pnl(p, int(d), 0.0, 0.0, h)})
    tr = pd.DataFrame(tr).dropna(subset=["pnl"])
    return tr, pd.DataFrame(ar)


def pick(tr: pd.DataFrame, arah: str, sc: str, h: str, grp: str = "SEMUA") -> pd.DataFrame:
    x = tr[(tr.arah == arah) & (tr.sc == sc) & (tr.h == h)]
    return x if grp == "SEMUA" else x[x.group == grp]


def breakeven(tr: pd.DataFrame, sc: str, h: str, grp: str = "SEMUA") -> float:
    ok = pick(tr, "ORAKEL (kejutan diketahui)", sc, h, grp).pnl.mean()
    bad = pick(tr, "ORAKEL SALAH (kebalikan)", sc, h, grp).pnl.mean()
    return float(-bad / (ok - bad) * 100) if ok == ok and bad == bad and ok > bad else np.nan


def report() -> str:
    ev = events()
    cl = clues(ev)
    res = {a: run(a, ev, cl) for a in FEEDS}
    L = ["# Entry 1 detik sebelum rilis, tutup 1-3 detik setelah entry (research/news_pra.py)", ""]
    for a, lab in FEEDS.items():
        tr, ar = res[a]
        kn = ar[ar.bias.isin([1.0, -1.0])]
        L.append(f"== {lab}: {len(ar)} rilis ({ar.time.min():%Y-%m} .. {ar.time.max():%Y-%m}), "
                 f"{len(kn)} dengan kejutan (Act != Cons), spread median di t0-1: ${ar.spread.median():.2f} ==")
        L.append("Cek jam feed & 'ke mana emas' (% gerak mid searah kejutan; 50% = lempar koin):")
        for per, g in (("SEMUA", kn), ("LAMA", kn[kn.time < NEW]), ("BARU", kn[kn.time >= NEW])):
            if not len(g):
                continue
            cells = []
            for k in (-5, 0, 1, 2, 3, 5, 10, 60):
                s = np.sign(g[f"g{k}"]) * g.bias
                cells.append(f"{'t0-5→-1' if k == -5 else f't0{k:+d}'} {(s > 0).mean() * 100:3.0f}%"
                             f" (diam {(s == 0).mean() * 100:2.0f}%)")
            L.append(f"  {per:5} n={len(g):4} | " + " | ".join(cells))
        L.append("  Median |gerak| dari t0-1 ($): " + " | ".join(
            f"t0{k:+d} {ar[f'g{k}'].abs().median():.2f}" for k in (0, 1, 2, 3, 5, 10, 60)))
        L.append("")
        L.append("ORAKEL (arah kejutan diketahui sempurna sebelum rilis — batas atas) & akurasi minimal agar impas:")
        for sc in SCEN:
            for h in H + (list(HOLD) if sc == "CEPAT" else []):
                h = h if isinstance(h, str) else f"{h}s"
                s = stats(pick(tr, "ORAKEL (kejutan diketahui)", sc, h))
                L.append(fmt(f"  {sc} tutup {h}", s) + f" | impas bila tebakan benar >= {breakeven(tr, sc, h):.0f}%")
        L.append("")
    L.append("== Semua petunjuk sebelum rilis (tutup 1-3 dtk; CEPAT & REALISTIS; SEMUA grup dan per grup) ==")
    names = sorted(set(res["XAU_EXNESS"][0].arah) | set(res["XAU"][0].arah))
    lolos = []
    for name in names:
        if name.startswith("ORAKEL"):
            continue
        for h in [f"{x}s" for x in H]:
            for grp in GROUPS:
                cells, ok_all = [], True
                for a, lab in FEEDS.items():
                    tr = res[a][0]
                    s, r = stats(pick(tr, name, "CEPAT", h, grp)), stats(pick(tr, name, "REALISTIS", h, grp))
                    if s.get("n", 0) < 30:
                        ok_all = False
                        continue
                    ok = judge(s, r)
                    ok_all &= ok
                    cells.append(fmt(f"  {lab:9} {name} | {h} | {grp}", s) + f" | REALISTIS {r['avg']:+.2f}"
                                 + ("  LOLOS" if ok else ""))
                if cells and (grp == "SEMUA" or any("LOLOS" in c for c in cells)):
                    L += cells
                if ok_all and len(cells) == len(FEEDS):
                    lolos.append(f"{name} | tutup {h} | {grp}")
    L.append("")
    L.append(f"LOLOS di kedua feed: {len(lolos)}" + ("".join(f"\n  - {x}" for x in lolos) if lolos else ""))
    return "\n".join(L) + "\n"


def main() -> None:
    txt = report()
    OUT.write_text(txt, encoding="utf-8")
    print(txt)
    print(f"ditulis {OUT}")


if __name__ == "__main__":
    main()
