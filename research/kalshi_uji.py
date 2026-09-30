"""Uji: bisakah peluang pasar Kalshi beberapa jam sebelum rilis menebak kejutan (Act vs Cons) dan arah emas?

python -m research.kalshi uji      (data dari python -m research.kalshi unduh) -> docs/eksternal/hasil_kalshi.txt
Aturan lihat docstring research/kalshi.py (ditetapkan sebelum melihat hasil).
"""
from __future__ import annotations

import glob
import json
from pathlib import Path

import numpy as np
import pandas as pd

from . import news_pra2 as p2
from .eksternal import cache_path
from .kalshi import SERIES
from .news_data import INVERSE, _num, load_calendar
from .news_detik import fmt, prepare, stats
from .run_scan import DATA

HORIZON = {"24 jam": 24, "6 jam": 6, "2 jam": 2, "1 jam": 1, "saat tutup": 0}
LEAN = [0.0, 0.10, 0.20]
SPLIT = pd.Timestamp("2024-01-01", tz="UTC")          # dua periode untuk cek konsisten (data Kalshi mulai 2021)
OUT = Path(__file__).resolve().parent.parent / "docs" / "eksternal" / "hasil_kalshi.txt"
SHOW = ["tutup 3s", "tutup 10s", "tutup 60s", "tutup 180s", "untung>=$1 maks 60s", "untung>=$2 maks 180s"]


def strike(m: dict) -> float | None:
    """Strike dari ticker (...-T0.3 / -T-0.1 / -T150000)."""
    t = m["ticker"].rsplit("-T", 1)
    try:
        return float(t[1]) if len(t) == 2 else None
    except ValueError:
        return None


def prob_at(m: dict, ts: float) -> float | None:
    """Peluang YES pada waktu ts (unix): candle 1 jam terakhir yang selesai <= ts; mid bid/ask, cadangan harga."""
    c = [x for x in m.get("candle") or [] if x[0] <= ts]
    if not c:
        return None
    _, bid, ask, last, _ = c[-1]
    if bid is not None and ask is not None and 0 < ask <= 1 and ask >= bid:
        return (bid + ask) / 2
    return last


def curve(ms: list[dict], ts: float) -> list[tuple[float, float]]:
    pts = []
    for m in ms:
        k, p = strike(m), prob_at(m, ts)
        if k is not None and p is not None:
            pts.append((k, p))
    return sorted(pts)


def p_above(pts: list[tuple[float, float]], x: float) -> float | None:
    """P(Act > x): strike tepat bila ada, selain itu interpolasi linear antar strike (di luar rentang: None)."""
    for k, p in pts:
        if abs(k - x) < 1e-9:
            return p
    lo = [(k, p) for k, p in pts if k < x]
    hi = [(k, p) for k, p in pts if k > x]
    if not lo or not hi:
        return None
    (k0, p0), (k1, p1) = lo[-1], hi[0]
    return p0 + (p1 - p0) * (x - k0) / (k1 - k0)


def lean(pts, cons: float, step: float | None) -> tuple[float, float] | None:
    """(P di atas Cons, P di bawah Cons)."""
    up = p_above(pts, cons)
    if up is None:
        return None
    if step is None:
        return up, 1 - up
    below_ref = p_above(pts, round(cons - step, 6))
    return (up, 1 - below_ref) if below_ref is not None else None


def rows() -> pd.DataFrame:
    cal = load_calendar(DATA)
    out = []
    for series, (name, step) in SERIES.items():
        if series == "KXFEDDECISION":
            continue
        cc = cal[cal.event == name]
        for f in sorted(glob.glob(str(cache_path(f"kalshi/{series}") / "*.json"))):
            d = json.loads(Path(f).read_text(encoding="utf-8"))
            ms = d["pasar"]
            close = min(pd.Timestamp(m["tutup"]) for m in ms)
            g = cc[(cc.time >= close) & (cc.time <= close + pd.Timedelta(minutes=15))]
            if not len(g):
                continue
            r = g.iloc[0]
            cons, act = _num(r.forecast), _num(r.actual)
            if cons != cons or act != act:
                continue
            row = {"seri": series, "event": d["event"], "t0": r.time, "cons": cons, "act": act,
                   "kejutan": float(np.sign(round(act - cons, 6))), "terbalik": name in INVERSE}
            for lab, h in HORIZON.items():
                ts = (close - pd.Timedelta(hours=h)).timestamp()
                lp = lean(curve(ms, ts), cons, step)
                row[f"atas {lab}"], row[f"bawah {lab}"] = lp if lp else (np.nan, np.nan)
            out.append(row)
    df = pd.DataFrame(out)
    for lab in HORIZON:
        df[f"lean {lab}"] = df[f"atas {lab}"] - df[f"bawah {lab}"]
    return df


def accuracy(df: pd.DataFrame, lab: str, th: float) -> dict:
    x = df[df[f"lean {lab}"].notna() & (df[f"lean {lab}"].abs() >= max(th, 1e-9))]
    k = x[x.kejutan != 0]
    hit = np.sign(k[f"lean {lab}"]) == k.kejutan
    old = k.t0 < SPLIT
    pct = lambda m: float(hit[m].mean() * 100) if m.sum() else np.nan  # noqa: E731
    return {"n_tebak": len(x), "n": len(k), "benar": pct(k.t0.notna()), "awal": pct(old), "akhir": pct(~old),
            "sama": float((x.kejutan == 0).mean() * 100) if len(x) else np.nan}


def gold_dirs(df: pd.DataFrame, lab: str, th: float) -> pd.Series:
    """Arah emas per waktu rilis dari tebakan Kalshi (gabungan seri yang rilis bersamaan: jumlah arah)."""
    x = df[df[f"lean {lab}"].notna() & (df[f"lean {lab}"].abs() >= max(th, 1e-9))].copy()
    x["emas"] = -np.sign(x[f"lean {lab}"]) * np.where(x.terbalik, -1, 1)
    s = np.sign(x.groupby("t0").emas.sum())
    return s[s != 0]


def trade_table(times: list[pd.Timestamp], aset: str) -> dict:
    """waktu rilis -> array directional news_pra2 [skenario, BUY/SELL, cara keluar]."""
    out = {}
    for t in times:
        p = prepare(t, aset)
        if p is None:
            continue
        d = p2.directional(p)
        if d is not None:
            out[t] = d
    return out


def trade_stats(dirs: pd.Series, table: dict, s: int, e: int) -> dict:
    rec = []
    for t, d in dirs.items():
        if t in table:
            rec.append({"time": t, "pnl": table[t][s, 0 if d > 0 else 1, e]})
    x = pd.DataFrame(rec)
    if not len(x):
        return {"n": 0}
    out = stats(x)
    a, b = x[x.time < SPLIT].pnl, x[x.time >= SPLIT].pnl
    out.update(awal=float(a.mean()) if len(a) else np.nan, akhir=float(b.mean()) if len(b) else np.nan)
    return out


def consistent(c: dict, r: dict) -> bool:
    """Seperti news_detik.judge, tetapi periode 2021-2023 vs 2024-2026 (Kalshi baru ada sejak Agu 2021)."""
    return (c.get("n", 0) >= 30 and c["awal"] > 0 and c["akhir"] > 0 and c["tahun"] >= 60 and c["t"] > 2
            and r.get("n", 0) > 0 and r["avg"] > 0)


GROUPS = {"SEMUA": None, "CPI": ["KXCPI", "KXCPICORE"], "NFP+PENGANGGURAN": ["KXPAYROLLS", "KXU3"],
          "PCE": ["KXPCECORE"]}


def per_release(df: pd.DataFrame, lab: str, th: float = 0.10) -> list[str]:
    """Satu baris per rilis: peluang Kalshi, tebakan, kejutan sebenarnya, gerak emas +10 dtk / +1 mnt / +5 mnt."""
    L = []
    for t0, g in df.sort_values("t0").groupby("t0"):
        g = g[g[f"lean {lab}"].abs() >= th]
        if not len(g):
            continue
        cells = []
        for _, r in g.iterrows():
            ok = "sama" if r.kejutan == 0 else "BENAR" if np.sign(r[f"lean {lab}"]) == r.kejutan else "SALAH"
            cells.append(f"{'core' if r.seri.endswith('CORE') else 'head'} atas {r[f'atas {lab}'] * 100:3.0f}% "
                         f"bawah {r[f'bawah {lab}'] * 100:3.0f}% Cons {r.cons:g} Act {r.act:g} {ok}")
        cells = " | ".join(cells)
        emas = -np.sign((np.sign(g[f"lean {lab}"]) * np.where(g.terbalik, -1, 1)).sum())
        p = prepare(t0, "XAU_EXNESS")
        move = "" if p is None else " ".join(
            f"{k} {(p.mid[p.at(s)] - p.mid[p.at(-1)]) * emas:+6.2f}" for k, s in (("+10dtk", 10), ("+1mnt", 60), ("+5mnt", 300)))
        L.append(f"  {t0:%Y-%m-%d} tebak emas {'NAIK ' if emas > 0 else 'TURUN' if emas < 0 else '-    '} | {cells} | "
                 f"untung searah tebakan: {move or 'tidak ada tick'}")
    return L


def cpi_reactions() -> pd.DataFrame:
    """Semua rilis CPI (Dukascopy 2010-2026): arah kejutan untuk emas (bias +1/-1/0) & emas naik di +60 dtk?"""
    from .news_detik import events
    ev = events()
    rows_ = []
    for r in ev[ev.group == "CPI"].itertuples():
        if r.bias != r.bias:
            continue
        p = prepare(r.time, "XAU")
        if p is None:
            continue
        mv = p.mid[p.at(60)] - p.mid[p.at(-1)]
        if mv != 0:
            rows_.append({"t0": r.time, "bias": r.bias, "naik": float(mv > 0)})
    return pd.DataFrame(rows_)


def gold_probability(df: pd.DataFrame, lab: str, reac: pd.DataFrame) -> pd.DataFrame:
    """Peluang emas NAIK 1 menit = P(bawah)*naik|bawah + P(atas)*naik|atas + P(sama)*naik|sama, dengan tingkat
    reaksi dari rilis CPI SEBELUM tanggal itu saja (walk-forward). P(...) = rata-rata headline & core."""
    x = df[df.seri.isin(GROUPS["CPI"])].groupby("t0")[[f"atas {lab}", f"bawah {lab}"]].mean().dropna()
    out = []
    for t0, r in x.iterrows():
        past = reac[reac.t0 < t0]
        rate = {b: past[past.bias == b].naik.mean() for b in (1.0, -1.0, 0.0)}
        if any(v != v for v in rate.values()):
            continue
        same = max(0.0, 1 - r[f"atas {lab}"] - r[f"bawah {lab}"])
        p = r[f"bawah {lab}"] * rate[1.0] + r[f"atas {lab}"] * rate[-1.0] + same * rate[0.0]
        out.append({"t0": t0, "p_naik": p})
    return pd.DataFrame(out)


def fed_table() -> list[str]:
    """Keputusan Fed: peluang Kalshi untuk hasil konsensus FF saat pasar tutup, dan seberapa sering Fed mengejutkan."""
    cal = load_calendar(DATA)
    cc = cal[cal.event == "Federal Funds Rate"]
    L = []
    for f in sorted(glob.glob(str(cache_path("kalshi/KXFEDDECISION") / "*.json"))):
        d = json.loads(Path(f).read_text(encoding="utf-8"))
        ms = d["pasar"]
        close = min(pd.Timestamp(m["tutup"]) for m in ms)
        g = cc[(cc.time >= close) & (cc.time <= close + pd.Timedelta(minutes=15))]
        if not len(g):
            continue
        r = g.iloc[0]
        cons, prev, act = _num(r.forecast), _num(r.previous), _num(r.actual)
        if cons != cons or prev != prev:
            continue
        bp = round((cons - prev) * 100)
        want = "H0" if bp == 0 else (f"C{abs(bp)}" if bp < 0 else f"H{bp}")
        m = [x for x in ms if x["ticker"].endswith("-" + want)]
        p = prob_at(m[0], close.timestamp()) if m else None
        L.append(f"  {r.time:%Y-%m-%d} konsensus {want:4} peluang Kalshi saat tutup "
                 f"{'-' if p is None else f'{p * 100:.0f}%'} | hasil {'SESUAI' if act == cons else 'KEJUTAN'}")
    return L


OUT_JSON = Path(__file__).resolve().parent.parent / "cloud" / "api" / "kalshi.json"
# angka untuk kartu Kalshi di aplikasi (cloud/api/_kalshi.py), diisi oleh report()
EKSPOR: dict = {"dibuat": "research/kalshi_uji.py", "akurasi": {}, "sinyal": {}, "ambang": 0.6}


def report() -> str:
    df = rows()
    L = ["# Kalshi: peluang hasil berita sebelum rilis vs kejutan & arah emas (research/kalshi_uji.py)", ""]
    L.append(f"Rilis dengan data Kalshi + konsensus ForexFactory: {len(df)} "
             f"({df.t0.min():%Y-%m}..{df.t0.max():%Y-%m}); per seri {df.seri.value_counts().to_dict()}")
    L.append("")
    L.append("== Akurasi menebak arah kejutan (hanya rilis dengan kejutan; 50% = lempar koin) ==")
    for series in ["SEMUA"] + sorted(df.seri.unique()):
        x = df if series == "SEMUA" else df[df.seri == series]
        for lab in HORIZON:
            for th in LEAN:
                a = accuracy(x, lab, th)
                if a["n"] >= 10:
                    L.append(f"  {series:10} {lab:10} selisih>={th:.2f} ditebak {a['n_tebak']:3} | kejutan n={a['n']:3} "
                             f"benar {a['benar']:5.1f}% | {SPLIT.year - 3}-{SPLIT.year - 1} {a['awal']:5.1f}% | "
                             f"{SPLIT.year}-2026 {a['akhir']:5.1f}% | sama dengan Cons {a['sama']:4.1f}%")
    L.append("")
    L.append("== Kalibrasi saat tutup: peluang Kalshi 'di atas Cons' vs kenyataan ==")
    x = df[df["atas saat tutup"].notna()]
    for lo, hi in ((0, .2), (.2, .4), (.4, .6), (.6, .8), (.8, 1.01)):
        g = x[(x["atas saat tutup"] >= lo) & (x["atas saat tutup"] < hi)]
        if len(g):
            L.append(f"  peluang {lo * 100:3.0f}-{min(hi, 1) * 100:3.0f}%: n={len(g):3} -> benar-benar di atas "
                     f"{(g.kejutan > 0).mean() * 100:4.1f}%, sama {(g.kejutan == 0).mean() * 100:4.1f}%")
    L.append("")
    L.append("== Uji entry t0-1 searah tebakan Kalshi (mesin news_pra2; CEPAT | REALISTIS | STRES) ==")
    times = sorted(df.t0.unique())
    tables = {a: trade_table(times, a) for a in p2.FEEDS}
    lolos, n_uji = [], 0
    for grp, seri in GROUPS.items():
        sub = df if seri is None else df[df.seri.isin(seri)]
        for lab in HORIZON:
            for th in LEAN:
                dirs = gold_dirs(sub, lab, th)
                for e, ex in enumerate(p2.EXITS):
                    res = {a: [trade_stats(dirs, tables[a], s, e) for s in range(len(p2.SCEN))] for a in p2.FEEDS}
                    if ex in SHOW and th == 0.10 and lab in ("24 jam", "1 jam"):
                        for a, name in p2.FEEDS.items():
                            c, r, st = res[a]
                            if c.get("n", 0) >= 10:
                                L.append(fmt(f"  {name:9} {grp} {lab} >={th:.2f} | {ex}", c)
                                         + f" | 2021-23 {c['awal']:+.2f} 2024-26 {c['akhir']:+.2f}"
                                         + f" | REAL {r['avg']:+.2f} | STRES {st['avg']:+.2f}")
                    n_uji += 1
                    if all(consistent(res[a][0], res[a][1]) for a in p2.FEEDS):
                        lolos.append(f"{grp} | {lab} >={th:.2f} | {ex}")
    L.append("")
    L.append(f"LOLOS di kedua feed (n >= 30): {len(lolos)} dari {n_uji}" + "".join(f"\n  - {x}" for x in lolos))
    L.append("")
    L.append("== Peluang emas NAIK 1 menit (Kalshi x reaksi historis, walk-forward) untuk CPI ==")
    reac = cpi_reactions()
    EKSPOR["reaksi_cpi"] = {k: {"naik": round(float(reac[reac.bias == b].naik.mean()), 3),
                               "n": int((reac.bias == b).sum())} for k, b in (("bawah", 1.0), ("atas", -1.0),
                                                                              ("sama", 0.0))}
    EKSPOR["reaksi_cpi"]["tahun"] = f"{reac.t0.min():%Y}–{reac.t0.max():%Y}"
    for series in sorted(df.seri.unique()):
        a = accuracy(df[df.seri == series], "24 jam", 0.10)
        s = df[df.seri == series]
        EKSPOR["akurasi"][series] = {"n": a["n"], "benar": round(a["benar"], 1), "sama": round(a["sama"], 1),
                                     "tahun": f"{s.t0.min():%Y}–{s.t0.max():%Y}"}
    for lab in ("24 jam", "1 jam"):
        gp = gold_probability(df, lab, reac)
        for a, name in p2.FEEDS.items():
            got = []
            for r in gp.itertuples():
                p = prepare(r.t0, a)
                if p is not None:
                    mv = p.mid[p.at(60)] - p.mid[p.at(-1)]
                    got.append((r.p_naik, float(mv > 0), r.t0))
            g = pd.DataFrame(got, columns=["p", "naik", "t0"])
            for lo, hi, arah in ((0.6, 1.01, "NAIK"), (0.0, 0.4, "TURUN")):
                k = g[(g.p >= lo) & (g.p < hi)]
                if len(k):
                    hit = k.naik.mean() if arah == "NAIK" else 1 - k.naik.mean()
                    L.append(f"  {name:9} {lab:7} peluang {arah} >= 60%: n={len(k):2} -> benar {hit * 100:4.1f}% "
                             f"(rata peluang {abs((k.p if arah == 'NAIK' else 1 - k.p).mean()) * 100:.0f}%)")
            k = g[(g.p > 0.4) & (g.p < 0.6)]
            L.append(f"  {name:9} {lab:7} peluang 40-60% (tidak ditebak): n={len(k)}")
        sig = gp[(gp.p_naik >= 0.6) | (gp.p_naik <= 0.4)]
        dirs = pd.Series(np.where(sig.p_naik >= 0.6, 1.0, -1.0), index=sig.t0)
        for e, ex in enumerate(p2.EXITS):
            if ex not in SHOW:
                continue
            for a, name in p2.FEEDS.items():
                c, r, st = [trade_stats(dirs, tables[a], s, e) for s in range(len(p2.SCEN))]
                if c.get("n", 0):
                    L.append(fmt(f"    entry t0-1 {name:9} {lab} | {ex}", c)
                             + f" | 2021-23 {c['awal']:+.2f} 2024-26 {c['akhir']:+.2f}"
                             + f" | REAL {r['avg']:+.2f} | STRES {st['avg']:+.2f}")
                    if lab == "24 jam" and ex == "tutup 60s":
                        hit = [float(np.sign(p.mid[p.at(60)] - p.mid[p.at(-1)]) == d)
                               for t, d in dirs.items() if (p := prepare(t, a)) is not None]
                        EKSPOR["sinyal"][name] = {"n": c["n"], "benar": round(100 * float(np.mean(hit)), 1),
                                                  "rata60": round(c["avg"], 2), "real": round(r["avg"], 2),
                                                  "t": round(c["t"], 1),
                                                  "tahun": f"{min(dirs.index):%Y}–{max(dirs.index):%Y}"}
    L.append("")
    L.append("== CPI per rilis (tebakan 1 jam sebelum, selisih >= 0,10): gerak emas Exness dari t0-1 ==")
    L += per_release(df[df.seri.isin(GROUPS["CPI"])], "1 jam")
    L.append("")
    L.append("== Keputusan Fed (FOMC): peluang Kalshi untuk hasil konsensus ==")
    L += fed_table()
    return "\n".join(L) + "\n"


def main() -> None:
    txt = report()
    OUT.write_text(txt, encoding="utf-8")
    OUT_JSON.write_text(json.dumps(EKSPOR, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(txt)
    print(f"ditulis {OUT} dan {OUT_JSON}")
