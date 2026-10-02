"""Entry BEBERAPA MENIT setelah berita, tutup beberapa menit kemudian (XAU/USD, data tick) — adakah yang WR tinggi DAN
untung konsisten?

python -m research.news_menit            # -> docs/eksternal/hasil_news_menit.txt

Permintaan pengguna (2 Okt 2026): "sinyal setelah news dengan WR tinggi; entry beberapa menit saja setelah itu close,
bukan hold. NFP cenderung sell, tapi ada yang spike buy dulu setelah rilis baru sell." research/news_detik.py hanya
memutuskan di detik 1-30; di sini keputusan di menit 0,5-5 dengan Act sudah diketahui.

Mesin (ditetapkan sebelum melihat hasil; sama dengan news_detik):
- Acuan = mid tick terakhir sebelum t0. Keputusan di t0 + d (d = 30, 60, 120, 180, 300 dtk) hanya dari data sampai d.
- Eksekusi manual: tick pertama >= t0 + d + 2 dtk di ASK (BUY) / BID (SELL) + slippage $0,30 (REALISTIS) — juga
  (riset lama news_detik: tanpa latensi/slippage pun detik awal tidak lolos).
- Arah (bias = kejutan Act vs Cons: +1 = data lemah untuk USD -> emas naik):
  KEJUTAN   = ikut kejutan.
  GERAK $x  = ikut gerak acuan -> d bila |gerak| >= $x (x = 2, 4).          LAWAN $x = kebalikannya (fade).
  SPIKE-BALIK $x = pola pengguna: gerak acuan -> d >= $x MELAWAN kejutan (mis. NFP di atas perkiraan tetapi emas
              spike naik) -> masuk SEARAH kejutan (harapan: berbalik).
  KONFIRMASI $x = gerak >= $x SEARAH kejutan -> ikut.
  PULLBACK  = searah kejutan, hanya bila harga sudah mundur >= 40% dari gerak terjauh searah kejutan (0 -> d)
              dan gerak terjauh itu >= $2 (masuk saat koreksi, bukan di puncak spike).
- Keluar: tahan H (1, 3, 5, 10 menit; d + H <= 15 menit) | TP $3 / SL $3 | TP $5 / SL $5 (paksa di H), dicek tiap tick,
  SL lebih dulu. P&L di BID (BUY) / ASK (SELL) = harga tutup nyata. $/ons = $ per 0,01 lot (sen di akun Cent).
- Feed: Dukascopy 2010-2026 dan tick asli Exness 2015-2026 (akun Cent pengguna).
Kriteria LOLOS (sebelum melihat hasil): REALISTIS di KEDUA feed: n >= 30, rata > 0 di LAMA (< Okt 2021) DAN BARU,
>= 60% tahun positif, t > 2. Ratusan kombinasi diuji -> satu-dua yang lolos di satu feed saja wajar karena kebetulan.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

from .news_detik import EXNESS, NEW, events, prepare

OUT = Path(__file__).resolve().parent.parent / "docs" / "eksternal" / "hasil_news_menit.txt"
DECIDE = (30, 60, 120, 180, 300)
HOLD = (60, 180, 300, 600)
EXITS = [("tahan", None, None), ("TP3/SL3", 3.0, 3.0), ("TP5/SL5", 5.0, 5.0)]
MODES = {"REALISTIS": (2.0, 0.30)}
FEEDS = ("XAU", "XAU_EXNESS")
GROUPS = {"NFP": ["NFP"], "CPI": ["CPI"], "NFP+CPI+PPI": ["NFP", "CPI", "PPI"], "SEMUA": None}


def exit_pnl(p, k: int, price: float, d: int, hold: float, tp: float | None, sl: float | None) -> float:
    t_end = p.T[k] + hold
    end = int(np.searchsorted(p.T, t_end, side="right"))
    if end <= k:
        return float("nan")
    pnl = (p.bid[k:end] - price) if d > 0 else (price - p.ask[k:end])
    if sl is not None:
        hs = np.flatnonzero(pnl <= -sl)
        ht = np.flatnonzero(pnl >= tp)
        i_s = hs[0] if len(hs) else None
        i_t = ht[0] if len(ht) else None
        if i_s is not None and (i_t is None or i_s <= i_t):
            return float(pnl[i_s])
        if i_t is not None:
            return float(pnl[i_t])
    return float(pnl[-1])


def directions(p, ref: float, d: int, bias: float) -> dict[str, int]:
    out = {}
    move = p.mid[p.at(d)] - ref
    has_bias = bias in (1.0, -1.0)
    if has_bias:
        out["KEJUTAN"] = int(bias)
    for x in (2, 4):
        if abs(move) >= x:
            s = int(np.sign(move))
            out[f"GERAK ${x}"] = s
            out[f"LAWAN ${x}"] = -s
            if has_bias and s == -int(bias):
                out[f"SPIKE-BALIK ${x}"] = int(bias)
            if has_bias and s == int(bias):
                out[f"KONFIRMASI ${x}"] = int(bias)
    if has_bias:
        w = (p.T >= 0) & (p.T <= d)
        if w.any():
            path = (p.mid[w] - ref) * bias
            peak = float(path.max())
            now = float(move * bias)
            if peak >= 2 and now <= 0.6 * peak:
                out["PULLBACK"] = int(bias)
    return out


def run(feed: str) -> pd.DataFrame:
    ev = events()
    if feed in EXNESS:
        ev = ev[ev.time >= EXNESS[feed][1]]
    rows = []
    for e in ev.itertuples():
        p = prepare(e.time, feed)
        if p is None:
            continue
        ref = p.mid[p.at(-0.001)]
        bias = e.bias if e.bias == e.bias else np.nan
        for d in DECIDE:
            dirs = directions(p, ref, d, bias)
            if not dirs:
                continue
            for mode, (lat, slip) in MODES.items():
                k = p.after(d + lat)
                if k is None:
                    continue
                for rule, s in dirs.items():
                    price = p.ask[k] + slip if s > 0 else p.bid[k] - slip
                    for h in HOLD:
                        if d + lat + h > 15 * 60:
                            continue
                        for ex, tp, sl in EXITS:
                            v = exit_pnl(p, k, price, s, h, tp, sl)
                            if v == v:
                                rows.append({"time": e.time, "group": e.group, "d": d, "mode": mode, "rule": rule,
                                             "hold": h, "exit": ex, "pnl": v})
    return pd.DataFrame(rows)


def stats(x: pd.DataFrame) -> dict:
    v = x.pnl.to_numpy()
    n = len(v)
    if n < 2:
        return {"n": n}
    lama, baru = x[x.time < NEW].pnl, x[x.time >= NEW].pnl
    yr = x.groupby(x.time.dt.year).pnl.sum()
    sd = v.std(ddof=1)
    return {"n": n, "wr": (v > 0).mean() * 100, "avg": v.mean(),
            "t": v.mean() / (sd / math.sqrt(n)) if sd > 0 else np.nan,
            "lama": lama.mean() if len(lama) else np.nan, "baru": baru.mean() if len(baru) else np.nan,
            "n_baru": len(baru), "tahun": (yr > 0).mean() * 100}


def ok(s: dict) -> bool:
    return (s.get("n", 0) >= 30 and s["lama"] > 0 and s["baru"] > 0 and s["tahun"] >= 60 and s["t"] > 2)


def fmt(s: dict) -> str:
    if s.get("n", 0) < 2:
        return "n<2"
    return (f"n={s['n']:4} WR {s['wr']:5.1f}% rata {s['avg']:+6.2f} t {s['t']:+5.1f} LAMA {s['lama']:+6.2f} "
            f"BARU {s['baru']:+6.2f} (n {s['n_baru']}) th+ {s['tahun']:3.0f}%")


def report() -> str:
    data = {f: run(f) for f in FEEDS}
    L = ["# Entry beberapa menit setelah berita (research/news_menit.py)", "",
         "Satuan $ per 0,01 lot XAU (sen di akun Cent). REALISTIS = masuk 2 dtk setelah keputusan + slippage $0,30.", ""]
    keys = ["d", "rule", "hold", "exit"]
    tested, lolos, rows = 0, [], []
    for gname, grp in GROUPS.items():
        per = {}
        for f, df in data.items():
            x = df[df["mode"] == "REALISTIS"]
            if grp:
                x = x[x.group.isin(grp)]
            per[f] = {k: stats(g) for k, g in x.groupby(keys)}
        for k in per["XAU"]:
            a, b = per["XAU"][k], per["XAU_EXNESS"].get(k, {"n": 0})
            tested += 1
            rows.append((gname, k, a, b))
            if ok(a) and ok(b):
                lolos.append((gname, k, a, b))
    L.append(f"Kombinasi diuji (grup x keputusan x arah x tahan x keluar): {tested}; LOLOS di kedua feed: {len(lolos)}")
    L.append("")
    for gname, k, a, b in sorted(lolos, key=lambda r: -min(r[2]["avg"], r[3]["avg"])):
        L.append(f"LOLOS {gname:12} masuk +{k[0]}s {k[1]:15} tahan {k[2] // 60} mnt {k[3]:8}")
        L.append(f"   Dukascopy {fmt(a)}")
        L.append(f"   Exness    {fmt(b)}")
    # WR tertinggi (n >= 30 di kedua feed) — apakah WR tinggi juga untung?
    L.append("\n== WR tertinggi (REALISTIS, n >= 30 di kedua feed, rata-rata WR dua feed) ==")
    hi = [r for r in rows if r[2].get("n", 0) >= 30 and r[3].get("n", 0) >= 30]
    hi.sort(key=lambda r: -(r[2]["wr"] + r[3]["wr"]))
    for gname, k, a, b in hi[:15]:
        L.append(f"{gname:12} +{k[0]}s {k[1]:15} tahan {k[2] // 60} mnt {k[3]:8} | Duka WR {a['wr']:4.0f}% rata "
                 f"{a['avg']:+5.2f} | Exness WR {b['wr']:4.0f}% rata {b['avg']:+5.2f} | {'LOLOS' if ok(a) and ok(b) else 'tidak'}")
    # pola pengguna: NFP spike melawan kejutan lalu berbalik
    L.append("\n== Pola pengguna: NFP spike MELAWAN kejutan -> masuk searah kejutan (REALISTIS) ==")
    for f, df in data.items():
        x = df[(df["mode"] == "REALISTIS") & (df.group == "NFP") & df.rule.str.startswith("SPIKE-BALIK")]
        for k, g in x[x.exit == "tahan"].groupby(["d", "rule", "hold"]):
            L.append(f"  {f:10} +{k[0]}s {k[1]:15} tahan {k[2] // 60} mnt: {fmt(stats(g))}")
    # seberapa sering NFP spike melawan kejutan
    L.append("\n== NFP: seberapa sering gerak menit awal MELAWAN kejutan? ==")
    for f, df in data.items():
        x = df[(df["mode"] == "REALISTIS") & (df.group == "NFP") & (df.hold == 60) & (df.exit == "tahan")]
        n_rel = x[x.rule == "KEJUTAN"].groupby("d").time.nunique()
        for dd in DECIDE:
            sb = x[(x.d == dd) & (x.rule == "SPIKE-BALIK $2")].time.nunique()
            if dd in n_rel.index:
                L.append(f"  {f:10} +{dd}s: spike >= $2 melawan kejutan di {sb}/{n_rel[dd]} rilis ({sb / n_rel[dd] * 100:.0f}%)")

    return "\n".join(L) + "\n"


def main() -> None:
    txt = report()
    OUT.write_text(txt, encoding="utf-8")
    print(txt)
    print(f"ditulis {OUT}")


if __name__ == "__main__":
    main()
