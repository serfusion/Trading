"""Sinyal 💰 yang lahir SETELAH berita: lebih bagus? Layak ditandai 📰? python -m research.sinyal_berita [ekspor]

Permintaan pengguna (2 Okt 2026): "bagaimana dengan setelah news? pasang bila sinyal memungkinkan WR tinggi, tandai
saja jika itu sinyal news". Aturan sinyal TIDAK diubah (mesin cloud, research/sl_tangga.backtest); di sini hanya
dilihat apakah sinyal 💰 yang entry-nya <= X jam setelah rilis berita AS berdampak tinggi berbeda mutunya.
Temuan lama (docs/RISET_DATA_EKSTERNAL.md bagian 2, XAU): sinyal <= 4 jam sesudah NFP/CPI/FOMC +0,64R latih /
+0,37R uji vs dasar +0,27 / +0,23.

Kalender: research/eksternal_berita.calendar() (ForexFactory 2010 - Jan 2026 + FRED NFP/CPI + FOMC 2026).
Grup: tier1 = NFP, CPI, FOMC; utama = + PPI, Retail, PCE, GDP. Jendela: rilis di (entry - X jam, entry], X = 1, 2, 4.
"searah kejutan" = arah sinyal sama dengan arah emas yang diharapkan dari kejutan rilis itu (data lemah USD -> BUY).
Juga diuji ulang: lapisan sebelum TP1 (kapan saja) dengan lot ½ — pertanyaan pengguna "sudah TP1 atau belum".
Layak DITANDAI bila (sebelum melihat hasil): n >= 30, R/sinyal > dasar di LAMA DAN BARU, >= 60% tahun > 0.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .eksternal import SPLIT
from .eksternal_berita import MAIN, TIER1, calendar
from .sinyal_lapis import VARIANTS, run, summary

OUT = Path(__file__).resolve().parent.parent / "docs" / "eksternal" / "hasil_sinyal_berita.txt"
EXTRA = {"lapis kapan saja (baru), lapisan lot ½": {"overlap": "any", "fresh": True, "half": True},
         "lapis kapan saja (baru), maks 2, lot ½": {"overlap": "any", "fresh": True, "max_layers": 2, "half": True},
         "lapisan kapan saja (baru hanya lapisan), lot ½": {"overlap": "any", "fresh_layers": True, "half": True},
         "lapisan kapan saja (baru hanya lapisan), maks 2, lot ½": {"overlap": "any", "fresh_layers": True,
                                                                    "max_layers": 2, "half": True},
         "lapis setelah TP1, maks 10, lot ½ (batas pengaman)": {"overlap": "tp1", "max_layers": 10, "half": True}}


def tag(sig: pd.DataFrame, cal: pd.DataFrame, groups: list[str], hours: float) -> tuple[np.ndarray, np.ndarray]:
    """(setelah berita, searah kejutan) per sinyal."""
    c = cal[cal.group.isin(groups)].sort_values("time")
    et = c.time.to_numpy("datetime64[ns]").astype(np.int64)
    t = sig.t.to_numpy("datetime64[ns]").astype(np.int64)
    k = np.searchsorted(et, t, side="right") - 1
    ok = (k >= 0) & (t - et[np.maximum(k, 0)] <= hours * 3600e9)
    bias = np.where(ok, c.gold_bias.to_numpy()[np.maximum(k, 0)], np.nan)
    return ok, ok & (bias == sig.dir.to_numpy())


def line(name: str, x: pd.DataFrame, split: pd.Timestamp) -> tuple[str, dict]:
    if len(x) < 2:
        return f"  {name:44} n={len(x)}", {}
    yr = x.groupby(x.t.dt.year).R.sum()
    s = {"n": len(x), "wr": 100 * (x.R > 0).mean(), "avg": x.R.mean(), "lama": x.R[x.t < split].mean(),
         "baru": x.R[x.t >= split].mean(), "th": (yr > 0).mean() * 100, "nth": len(yr)}
    return (f"  {name:44} n={s['n']:4} WR {s['wr']:5.1f}% R/sin {s['avg']:+.3f} LAMA {s['lama']:+.3f} "
            f"BARU {s['baru']:+.3f} tahun+ {s['th']:3.0f}% ({s['nth']} th)"), s


def report() -> str:
    cal = calendar()
    L = ["# Sinyal 💰 setelah berita & lapisan sebelum TP1 (research/sinyal_berita.py)", ""]
    for name in ("XAUUSD", "BTCUSD"):
        split = SPLIT[name]
        sig = run(name, {})
        L.append(f"== {name}: {len(sig)} sinyal 💰 bawaan (LAMA < {split:%Y}) ==")
        txt, base = line("semua (dasar)", sig, split)
        L.append(txt)
        for gname, groups in (("tier1", TIER1), ("utama", MAIN)):
            for h in (1, 2, 4):
                after, same = tag(sig, cal, groups, h)
                rows = (("setelah", after), ("setelah & searah kejutan", same), ("bukan setelah berita", ~after))
                for lab, m in rows:
                    txt, s = line(f"{gname} {lab} {h} jam", sig[m], split)
                    mark = ""
                    if s and lab != "bukan setelah berita":
                        good = (s["n"] >= 30 and s["lama"] > base["lama"] and s["baru"] > base["baru"]
                                and s["th"] >= 60)
                        mark = "  → LAYAK DITANDAI" if good else ""
                    L.append(txt + mark)
        L.append("")
        L.append(f"  Lapisan sebelum TP1 ({name}):")
        b = summary(run(name, {}), split)
        for vname, v in {**{k: VARIANTS[k] for k in ("lapis setelah TP1, lapisan lot ½",)}, **EXTRA}.items():
            s = summary(run(name, v), split)
            better = (s["yr"] - b["yr"]).reindex(b["yr"].index).fillna(0)
            L.append(f"  {vname:44} sinyal {s['n']:5} ({s['bln']:.1f}/bln) WR {s['wr']:4.1f}% R/sin {s['avg']:+.3f} "
                     f"total {s['tot']:+7.1f} DD {s['dd']:+6.1f} (dasar {b['dd']:+.1f}) total/DD {s['rasio']:.1f} "
                     f"(dasar {b['rasio']:.1f}) LAMA {s['lama']:+.3f} BARU {s['baru']:+.3f} lebih baik "
                     f"{int((better > 0).sum())}/{len(better)} th")
        L.append("")
    return "\n".join(L) + "\n"


# setelan yang dipasang di cloud (cloud/api/sinyal_lapis.json & sinyal_berita.json)
LAYER = {"XAUUSD": ({"overlap": "tp1", "max_layers": 10}, {"mode": "tp1", "max": 10}),
         "BTCUSD": ({"overlap": "any", "fresh_layers": True, "max_layers": 2}, {"mode": "any", "max": 2})}
CLOUD = Path(__file__).resolve().parent.parent / "cloud" / "api"


def export() -> None:
    import json
    cal = calendar()
    lap, ber = {}, {}
    for name, key in (("XAUUSD", "XAU"), ("BTCUSD", "BTC")):
        split = SPLIT[name]
        bt, cfg = LAYER[name]
        df = run(name, bt)
        ly = df[df.lapis]
        lap[key] = {**cfg, "lot": 0.5, "stats": {
            "n": int(len(ly)), "wr": round(100 * float((ly.R > 0).mean()), 1), "avg_r": round(float(ly.R.mean()), 3),
            "periode": f"{df.t.min():%Y}–{df.t.max():%Y}",
            "teks": f"Riwayat lapisan: WR {100 * (ly.R > 0).mean():.0f}% • "
                    f"{ly.R.mean():+.2f}".replace(".", ",") + "R/lapisan "
                    f"({len(ly)} lapisan {df.t.min():%Y}–{df.t.max():%Y})"}}
        sig = run(name, {})
        after, same = tag(sig, cal, MAIN, 4)
        _, base = line("dasar", sig, split)
        _, a = line("setelah", sig[after], split)
        _, b = line("searah", sig[same], split)
        ber[key] = {"jam": 4, "dasar": {k: round(float(base[k]), 3) for k in ("wr", "avg")},
                    "setelah": {**{k: round(float(a[k]), 3) for k in ("wr", "avg", "lama", "baru", "th")}, "n": a["n"]},
                    "searah": {**{k: round(float(b[k]), 3) for k in ("wr", "avg")}, "n": b["n"]},
                    "periode": f"{sig.t.min():%Y}–{sig.t.max():%Y}"}
    (CLOUD / "sinyal_lapis.json").write_text(json.dumps({"dibuat": "research/sinyal_berita.py", **lap},
                                                        ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (CLOUD / "sinyal_berita.json").write_text(json.dumps({"dibuat": "research/sinyal_berita.py", **ber},
                                                         ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(lap, ensure_ascii=False, indent=1))
    print(json.dumps(ber, ensure_ascii=False, indent=1))


def main() -> None:
    import sys
    if sys.argv[1:] == ["ekspor"]:
        export()
        return
    txt = report()
    OUT.write_text(txt, encoding="utf-8")
    print(txt)
    print(f"ditulis {OUT}")


if __name__ == "__main__":
    main()
