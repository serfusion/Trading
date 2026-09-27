"""Win rate vs profit: semua model SMC/ICT + scalping populer x skema keluar.

python -m research.winrate_study [--m5] [--csv out.csv] [--json android/app/src/main/assets/strategies.json]

Pertanyaan yang dijawab: bagaimana bila TP dibuat kecil (win rate tinggi), SL dipindah ke BE, atau
posisi ditutup sebagian? Apakah ada kombinasi "win rate tinggi + profit"?

Protokol anti-overfitting: untuk setiap model, skema keluar terbaik dipilih HANYA dari periode
2012-17, lalu dinilai apa adanya di 2018-22 dan 2025-26 (out-of-sample). Semua kombinasi juga
dilaporkan supaya terlihat berapa yang positif di ketiga periode.
"""
from __future__ import annotations

import argparse
import json
from datetime import date

import numpy as np
import pandas as pd

from .data import resample
from .scalp import trend_state
from .smc_models import (Frame, Sig, bars_until, bot_smc_signals, donchian_sigs, m_bos_ob, m_breaker,
                         m_cisd, m_fvg, m_judas, m_ote, m_pd_sweep, m_silver_bullet, m_turtle_soup,
                         periods, run, stats, structure)

SCHEMES: dict[str, dict] = {
    "TP bawaan model": {},
    "TP 0,5R": {"tp_r": 0.5},
    "TP 1R": {"tp_r": 1.0},
    "TP 1,5R": {"tp_r": 1.5},
    "TP 2R": {"tp_r": 2.0},
    "TP 3R": {"tp_r": 3.0},
    "BE di 0,5R + TP 1R": {"tp_r": 1.0, "be_r": 0.5},
    "50% di 0,5R + BE, sisa TP 1,5R": {"tp_r": 1.5, "partial": (0.5, 0.5)},
    "50% di 1R + BE, sisa TP 3R": {"tp_r": 3.0, "partial": (1.0, 0.5)},
}
PERIODS = ("2012-17", "2018-22", "2025-26")


# ------------------------------------------------------------------ scalping
def ema(x: np.ndarray, n: int) -> np.ndarray:
    return pd.Series(x).ewm(span=n, adjust=False).mean().to_numpy()


def rsi(c: np.ndarray, n: int) -> np.ndarray:
    d = np.diff(c, prepend=c[0])
    up = pd.Series(np.clip(d, 0, None)).ewm(alpha=1 / n, adjust=False).mean()
    dn = pd.Series(np.clip(-d, 0, None)).ewm(alpha=1 / n, adjust=False).mean()
    return (100 - 100 / (1 + up / dn.replace(0, np.nan))).fillna(50).to_numpy()


def s_breakout(fr: Frame, trend: np.ndarray, chan: int = 20, sl_atr: float = 1.5, hold: int = 16) -> list[Sig]:
    """Scalping breakout searah trend H1: close menembus high/low `chan` candle."""
    hi = pd.Series(fr.h).rolling(chan).max().shift(1).to_numpy()
    lo = pd.Series(fr.l).rolling(chan).min().shift(1).to_numpy()
    out = []
    for i in range(chan + 1, fr.n):
        if trend[i] > 0 and fr.c[i] > hi[i]:
            out.append(Sig(i, 1, sl_dist=sl_atr * fr.a[i], hold=hold))
        elif trend[i] < 0 and fr.c[i] < lo[i]:
            out.append(Sig(i, -1, sl_dist=sl_atr * fr.a[i], hold=hold))
    return out


def s_ema_cross(fr: Frame, fast: int = 9, slow: int = 21, sl_atr: float = 1.5, hold: int = 48) -> list[Sig]:
    """EMA 9/21 cross searah EMA 200."""
    f, s, t = ema(fr.c, fast), ema(fr.c, slow), ema(fr.c, 200)
    out = []
    for i in range(201, fr.n):
        if f[i] > s[i] and f[i - 1] <= s[i - 1] and fr.c[i] > t[i]:
            out.append(Sig(i, 1, sl_dist=sl_atr * fr.a[i], hold=hold))
        elif f[i] < s[i] and f[i - 1] >= s[i - 1] and fr.c[i] < t[i]:
            out.append(Sig(i, -1, sl_dist=sl_atr * fr.a[i], hold=hold))
    return out


def s_rsi2(fr: Frame, sl_atr: float = 2.0, hold: int = 24) -> list[Sig]:
    """RSI(2) pullback (Connors): searah EMA 200, beli saat RSI2 < 10 / jual saat > 90."""
    r, t = rsi(fr.c, 2), ema(fr.c, 200)
    out = []
    for i in range(201, fr.n):
        if fr.c[i] > t[i] and r[i] < 10:
            out.append(Sig(i, 1, sl_dist=sl_atr * fr.a[i], hold=hold))
        elif fr.c[i] < t[i] and r[i] > 90:
            out.append(Sig(i, -1, sl_dist=sl_atr * fr.a[i], hold=hold))
    return out


def s_bollinger(fr: Frame, n: int = 20, k: float = 2.0, sl_atr: float = 1.5, hold: int = 24) -> list[Sig]:
    """Bollinger mean reversion: close sebelumnya di luar band, close sekarang kembali di dalam."""
    m = pd.Series(fr.c).rolling(n).mean().to_numpy()
    sd = pd.Series(fr.c).rolling(n).std().to_numpy()
    up, dn = m + k * sd, m - k * sd
    out = []
    for i in range(n + 1, fr.n):
        if fr.c[i - 1] < dn[i - 1] and fr.c[i] > dn[i]:
            out.append(Sig(i, 1, sl_dist=sl_atr * fr.a[i], hold=hold))
        elif fr.c[i - 1] > up[i - 1] and fr.c[i] < up[i]:
            out.append(Sig(i, -1, sl_dist=sl_atr * fr.a[i], hold=hold))
    return out


def s_orb(fr: Frame, start: int, minutes: int, until: int, exit_min: int) -> list[Sig]:
    """Opening range breakout: range [start, start+minutes) jam NY; close menembus range sebelum
    `until`; SL di tengah range; keluar paksa di `exit_min`. Satu trade per hari."""
    out, used = [], set()
    rng: dict[int, list[float]] = {}
    for i in range(fr.n):
        m, day = int(fr.mins[i]), int(fr.day[i])
        if start <= m < start + minutes:
            r = rng.setdefault(day, [fr.h[i], fr.l[i]])
            r[0], r[1] = max(r[0], fr.h[i]), min(r[1], fr.l[i])
            continue
        if day in used or day not in rng or not (start + minutes <= m < until):
            continue
        hi, lo = rng[day]
        mid = (hi + lo) / 2
        if fr.c[i] > hi:
            out.append(Sig(i, 1, sl=mid, hold=bars_until(fr, i, exit_min)))
            used.add(day)
        elif fr.c[i] < lo:
            out.append(Sig(i, -1, sl=mid, hold=bars_until(fr, i, exit_min)))
            used.add(day)
    return out


# ------------------------------------------------------------------- model
def models(fr: Frame, period: str, trend: np.ndarray) -> dict[str, tuple[str, list[Sig]]]:
    events, _ = structure(fr, 3)
    return {
        "Setup SMC bot (sweep-MSS-FVG/OB)": ("SMC/ICT", bot_smc_signals(period, fr, True)),
        "ICT Silver Bullet 10-11 NY": ("SMC/ICT", m_silver_bullet(fr)),
        "ICT Silver Bullet 3 jendela": ("SMC/ICT", m_silver_bullet(fr, ((180, 240), (600, 660), (840, 900)))),
        "Judas swing / Power of 3": ("SMC/ICT", m_judas(fr)),
        "Judas swing + MSS": ("SMC/ICT", m_judas(fr, mss=True)),
        "Sweep PDH/PDL": ("SMC/ICT", m_pd_sweep(fr)),
        "Sweep PDH/PDL + MSS": ("SMC/ICT", m_pd_sweep(fr, mss=True)),
        "Turtle Soup 20": ("SMC/ICT", m_turtle_soup(fr)),
        "FVG displacement": ("SMC/ICT", m_fvg(fr)),
        "BOS + Order Block": ("SMC/ICT", m_bos_ob(fr, events)),
        "OTE 70,5%": ("SMC/ICT", m_ote(fr, events)),
        "CISD setelah sweep": ("SMC/ICT", m_cisd(fr)),
        "Breaker block": ("SMC/ICT", m_breaker(fr)),
        "Unicorn (breaker + FVG)": ("SMC/ICT", m_breaker(fr, unicorn=True)),
        "Scalping breakout searah trend H1": ("Scalping", s_breakout(fr, trend)),
        "Scalping EMA 9/21 + EMA200": ("Scalping", s_ema_cross(fr)),
        "Scalping RSI(2) Connors": ("Scalping", s_rsi2(fr)),
        "Scalping Bollinger reversal": ("Scalping", s_bollinger(fr)),
        "Scalping ORB London (02-03 NY)": ("Scalping", s_orb(fr, 120, 60, 300, 720)),
        "Scalping ORB New York (09:30-10 NY)": ("Scalping", s_orb(fr, 570, 30, 720, 900)),
    }


def trend_rows(trend_filter: bool) -> list[dict]:
    """Referensi: skema F-ensemble bot per periode. R per trade per set (risiko tiap set = 1R), supaya
    sebanding dengan model lain yang juga dihitung per trade."""
    rows = []
    for period, (df, sp) in periods("H1").items():
        fr = Frame(df, 60)
        keep = None
        if trend_filter:
            h4 = resample(df, "240min")
            bias = fr.map_htf(structure(Frame(h4, 240), 3)[1], h4, 240)
            keep = (lambda i, d: bias[i] == d)
        rs, ts = [], []
        for ne, nx in [(40, 15), (55, 20), (80, 30)]:
            sigs, ex = donchian_sigs(fr, ne, nx, 3.0, keep=keep)
            r, t = run(fr, sigs, sp, ex, f_legs=5, tp1_r=1.0)
            rs.append(r)
            ts.append(t)
        r, t = np.concatenate(rs), ts[0].append(ts[1:])
        r = r[np.argsort(t.asi8, kind="stable")]
        rows.append({"model": "Trend F-ensemble H1" + (" + bias H4 (bot)" if trend_filter else ""),
                     "kind": "Trend", "tf": "H1", "filter": "-", "scheme": "Skema F (5 posisi, TP1 1R, SL+)",
                     "period": period, **stats(r)})
    return rows


def collect(tf: str) -> pd.DataFrame:
    tf_min = {"M5": 5, "M15": 15}[tf]
    rows = []
    for period, (df, sp) in periods(tf).items():
        fr = Frame(df, tf_min)
        h1 = resample(df, "60min")
        trend = trend_state(h1).reindex(df.index + pd.Timedelta(minutes=tf_min),
                                        method="ffill").fillna(0).to_numpy()
        for name, (kind, sigs) in models(fr, period, trend).items():
            variants = {"-": sigs}
            if not name.startswith("Scalping breakout"):
                variants["searah trend H1"] = [s for s in sigs if trend[s.i] == s.d]
            for filt, ss in variants.items():
                for scheme, kw in SCHEMES.items():
                    r, _ = run(fr, ss, sp, **kw)
                    rows.append({"model": name, "kind": kind, "tf": tf, "filter": filt, "scheme": scheme,
                                 "period": period, **stats(r)})
        print(f"selesai {tf} {period}", flush=True)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- laporan
def verdict(per: dict) -> bool:
    return all(p in per and per[p]["avg"] > 0 and per[p]["n"] >= 30 for p in PERIODS)


def summarize(res: pd.DataFrame) -> list[dict]:
    """Per model (M15): skema dipilih di 2012-17 -> hasil OOS; juga skema dengan win rate tertinggi."""
    out = []
    key = ["model", "kind", "tf", "filter", "scheme"]
    table = {k: {r.period: r._asdict() for r in g.itertuples()} for k, g in res.groupby(key, sort=False)}
    for (model, kind, tf, filt), g in res.groupby(["model", "kind", "tf", "filter"], sort=False):
        combos = {k[4]: v for k, v in table.items() if k[:4] == (model, kind, tf, filt)}
        dev = {s: v["2012-17"] for s, v in combos.items() if "2012-17" in v and v["2012-17"]["n"] >= 30}
        if not dev:
            continue
        best = max(dev, key=lambda s: dev[s]["avg"])
        top_win = max(dev, key=lambda s: dev[s]["win"])
        out.append({"model": model, "kind": kind, "tf": tf, "filter": filt,
                    "best_scheme": best, "best": combos[best], "best_pass": verdict(combos[best]),
                    "win_scheme": top_win, "win": combos[top_win], "win_pass": verdict(combos[top_win]),
                    "any_pass": sum(verdict(v) for v in combos.values()), "combos": len(combos)})
    return out


def fmt_cell(v: dict | None) -> str:
    if not v:
        return "-"
    return f"win {v['win']:4.1f}% {v['avg']:+.2f}R PF {v['pf']:.2f} tot {v['sum']:+6.1f}R n={v['n']}"


BREAKEVEN_TP = {"TP 0,5R": 0.5, "TP 1R": 1.0, "TP 1,5R": 1.5, "TP 2R": 2.0, "TP 3R": 3.0}


def scheme_table(res: pd.DataFrame) -> list[dict]:
    """Rata-rata semua model M15 per skema keluar + win rate impas (sebelum spread) untuk TP tetap."""
    m15 = res[res.tf == "M15"]
    out = []
    for scheme in SCHEMES:
        g = m15[m15.scheme == scheme]
        tp = BREAKEVEN_TP.get(scheme)
        out.append({"scheme": scheme, "win": round(float(g["win"].mean()), 1),
                    "avg_r": round(float(g["avg"].mean()), 3),
                    "positive_pct": round(float((g["avg"] > 0).mean() * 100), 1),
                    "breakeven_win": round(100 / (1 + tp), 1) if tp else None})
    return out


def to_app_json(summary: list[dict], trend: pd.DataFrame, res: pd.DataFrame, path: str) -> None:
    """Data untuk layar 'Riset' di aplikasi Android (assets/strategies.json)."""
    def cells(per: dict) -> list[dict]:
        return [{"period": p, "n": int(per[p]["n"]), "win": round(float(per[p]["win"]), 1),
                 "avg_r": round(float(per[p]["avg"]), 3), "total_r": round(float(per[p]["sum"]), 1),
                 "pf": round(float(min(per[p]["pf"], 99)), 2), "dd_r": round(float(per[p]["dd"]), 1)}
                for p in PERIODS if p in per]

    items = []
    for (model, kind), g in trend.groupby(["model", "kind"], sort=False):
        per = {r.period: r._asdict() for r in g.itertuples()}
        items.append({"name": model, "kind": kind, "tf": "H1", "filter": "-",
                      "scheme": g["scheme"].iloc[0], "pass": verdict(per), "periods": cells(per),
                      "note": "Strategi bot (default)" if "bias" in model else "Tanpa filter bias H4"})
    for s in summary:
        if s["tf"] != "M15":
            continue
        items.append({"name": s["model"], "kind": s["kind"], "tf": s["tf"], "filter": s["filter"],
                      "scheme": s["best_scheme"], "pass": s["best_pass"], "periods": cells(s["best"]),
                      "note": f"Skema terbaik di 2012-17; {s['any_pass']} dari {s['combos']} skema lolos 3 periode"})
        if s["win_scheme"] != s["best_scheme"]:
            items.append({"name": s["model"], "kind": s["kind"], "tf": s["tf"], "filter": s["filter"],
                          "scheme": s["win_scheme"], "pass": s["win_pass"], "periods": cells(s["win"]),
                          "note": "Skema dengan win rate tertinggi"})
    m15 = res[res.tf == "M15"]
    grid = m15.groupby(["model", "filter", "scheme"]).apply(
        lambda g: verdict({r.period: r._asdict() for r in g.itertuples()}), include_groups=False)
    doc = {"generated": date.today().isoformat(),
           "source": "python -m research.winrate_study (data XAUUSD asli, spread dihitung)",
           "periods": list(PERIODS),
           "rule": "LOLOS = rata-rata R > 0 di ketiga periode dengan >= 30 trade; skema dipilih hanya dari 2012-17",
           "combos": int(len(grid)), "combos_pass": int(grid.sum()),
           "schemes": scheme_table(res),
           "items": items}
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--m5", action="store_true")
    ap.add_argument("--csv", default="")
    ap.add_argument("--json", default="")
    a = ap.parse_args()
    res = collect("M15")
    if a.m5:
        res = pd.concat([res, collect("M5")], ignore_index=True)
    trend = pd.DataFrame(trend_rows(False) + trend_rows(True))
    if a.csv:
        pd.concat([res, trend], ignore_index=True).to_csv(a.csv, index=False)
    summary = summarize(res)

    print("\n=== Referensi trend (H1) ===")
    for (model,), g in trend.groupby(["model"], sort=False):
        per = {r.period: r._asdict() for r in g.itertuples()}
        print(f"{'LOLOS' if verdict(per) else 'gagal'} {model:42s} | "
              + " | ".join(f"{p}: {fmt_cell(per.get(p))}" for p in PERIODS))

    m15 = res[res.tf == "M15"]
    grid = m15.groupby(["model", "filter", "scheme"]).apply(
        lambda g: verdict({r.period: r._asdict() for r in g.itertuples()}), include_groups=False)
    print(f"\n=== {len(grid)} kombinasi M15 (model x filter x skema): {int(grid.sum())} positif di 3 periode ===")
    for k in grid[grid].index:
        print("  LOLOS:", " | ".join(k))

    print("\n=== Per model: skema terbaik dipilih di 2012-17, lalu diuji OOS ===")
    for s in summary:
        if s["tf"] != "M15":
            continue
        tag = "LOLOS" if s["best_pass"] else "gagal"
        print(f"{tag} {s['model']:36s} {s['filter']:16s} [{s['best_scheme']}]")
        for p in PERIODS:
            print(f"        {p}: {fmt_cell(s['best'].get(p))}")
        if s["win_scheme"] != s["best_scheme"]:
            print(f"      win rate tertinggi [{s['win_scheme']}]: "
                  + " | ".join(f"{p}: win {s['win'][p]['win']:.1f}% {s['win'][p]['avg']:+.2f}R"
                               for p in PERIODS if p in s["win"]))

    wr = m15.groupby("scheme").apply(lambda g: pd.Series({"win%": g["win"].mean(), "avgR": g["avg"].mean(),
                                                           "positif%": (g["avg"] > 0).mean() * 100}),
                                     include_groups=False)
    print("\n=== Rata-rata semua model per skema keluar (M15, 3 periode) ===")
    print(wr.round(3).to_string())
    if a.m5:
        m5 = res[(res.tf == "M5")]
        pos = m5[(m5["avg"] > 0) & (m5["n"] >= 30)].sort_values("avg", ascending=False)
        print(f"\n=== M5 2025-26 (1 periode saja): {len(pos)} dari {len(m5)} kombinasi positif; 8 teratas ===")
        print(pos.head(8)[["model", "filter", "scheme", "n", "win", "avg", "pf", "sum"]].round(3).to_string(index=False))
    if a.json:
        to_app_json(summary, trend, res, a.json)
        print(f"\nJSON aplikasi: {a.json}")


if __name__ == "__main__":
    main()
