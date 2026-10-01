"""Validasi "perkiraan hari H": peluang emas naik 1 menit setelah rilis, dihitung beberapa jam sebelum rilis.

python -m research.hari_h_uji     # -> docs/eksternal/hasil_hari_h.txt + cloud/api/hari_h.json

Rumus (sama dengan cloud/api/_hari_h.py): P(naik) = P(di bawah) x naik|bawah + P(sama) x naik|sama + P(di atas) x
naik|atas. P(...) dari pasar prediksi (Kalshi, Polymarket, atau rata-rata keduanya) terhadap konsensus ForexFactory;
naik|hasil = reaksi emas 1 menit per judul (research/reaksi_menit.py) dari rilis SEBELUM tanggal itu (walk-forward).
Target: arah mid emas t0-1 dtk -> t0+60 dtk (Dukascopy, cadangan Exness). Sinyal = peluang >= 60% atau <= 40%.
Uji entry: BUY/SELL t0-1 searah sinyal, mesin research/news_pra2.py (CEPAT/REALISTIS), tutup 60 dtk.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from . import news_pra2 as p2
from .kalshi_uji import rows as kalshi_rows
from .news_detik import prepare, stats
from .polymarket_uji import rows as poly_rows
from .reaksi_menit import OUT_CSV, rates

TITLE = {"KXCPI": "CPI m/m", "KXCPICORE": "Core CPI m/m", "KXPAYROLLS": "Non-Farm Employment Change",
         "KXU3": "Unemployment Rate", "KXPCECORE": "Core PCE Price Index m/m"}
HOR = ["24 jam", "1 jam"]
TH = 0.10
OUT = Path(__file__).resolve().parent.parent / "docs" / "eksternal" / "hasil_hari_h.txt"
OUT_JSON = Path(__file__).resolve().parent.parent / "cloud" / "api" / "hari_h.json"


def p_naik(p: dict, r: dict) -> float | None:
    """p = {"atas","bawah"} (sama = sisa); r = reaksi per hasil. Hasil tanpa reaksi dibuang lalu dinormalkan."""
    if p.get("atas") is None or p.get("bawah") is None or p["atas"] != p["atas"]:
        return None
    w = {"atas": p["atas"], "bawah": p["bawah"], "sama": max(0.0, 1 - p["atas"] - p["bawah"])}
    num = sum(w[k] * r[k]["naik60"] for k in w if k in r)
    den = sum(w[k] for k in w if k in r)
    return num / den if den > 0 else None


def estimates(src: pd.DataFrame, react: pd.DataFrame, name: str) -> pd.DataFrame:
    out = []
    for row in src.itertuples(index=False):
        title = TITLE.get(row.seri)
        if not title:
            continue
        r = rates(react, before=row.t0).get(title)
        if not r:
            continue
        rec = {"t0": row.t0, "title": title, "sumber": name}
        for h in HOR:
            rec[h] = p_naik({"atas": getattr(row, f"atas_{h.replace(' ', '_')}", None),
                             "bawah": getattr(row, f"bawah_{h.replace(' ', '_')}", None)}, r)
        out.append(rec)
    return pd.DataFrame(out)


def _flat(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [c.replace(" ", "_") for c in df.columns]
    return df


def moves(times) -> dict:
    out = {}
    for t in times:
        for aset in ("XAU", "XAU_EXNESS"):
            p = prepare(pd.Timestamp(t), aset)
            if p is not None and p.at(-1) >= 0:
                out[pd.Timestamp(t)] = (float(p.mid[p.at(60)] - p.mid[p.at(-1)]), p)
                break
    return out


def report() -> tuple[str, dict]:
    react = pd.read_csv(OUT_CSV, parse_dates=["time"])
    ks = estimates(_flat(kalshi_rows()), react, "Kalshi")
    ps = estimates(_flat(poly_rows()), react, "Polymarket")
    both = ks.merge(ps, on=["t0", "title"], suffixes=("_k", "_p"))
    gab = pd.DataFrame({"t0": both.t0, "title": both.title, "sumber": "gabungan",
                        **{h: both[[f"{h}_k", f"{h}_p"]].mean(axis=1) for h in HOR}})
    est = pd.concat([ks, ps, gab], ignore_index=True)
    mv = moves(sorted(est.t0.unique()))
    est["naik"] = est.t0.map(lambda t: float(mv[t][0] > 0) if t in mv and mv[t][0] != 0 else np.nan)
    L = ["# Validasi perkiraan hari H (research/hari_h_uji.py)", "",
         f"Rilis: Kalshi {len(ks)}, Polymarket {len(ps)}, keduanya {len(gab)}; sinyal = peluang >= {50 + TH * 100:.0f}% "
         f"atau <= {50 - TH * 100:.0f}%", ""]
    ekspor = {}
    for (sumber, title), g in est.groupby(["sumber", "title"]):
        for h in HOR:
            x = g[g[h].notna() & g.naik.notna()]
            s = x[(x[h] - 0.5).abs() >= TH]
            if not len(x):
                continue
            hit = ((s[h] > 0.5) == (s.naik == 1)).mean() * 100 if len(s) else np.nan
            brier = float(((x[h] - x.naik) ** 2).mean())
            L.append(f"  {sumber:10} {title:28} {h:7} semua n={len(x):3} brier {brier:.3f} (0,25 = lempar koin) | "
                     f"sinyal n={len(s):3} benar {hit:5.1f}%"
                     + (f" | {s.t0.min():%Y}-{s.t0.max():%Y}" if len(s) else ""))
            if h == "24 jam":
                ekspor.setdefault(title, {})[sumber] = {"n": int(len(s)), "benar": None if hit != hit else round(hit, 1),
                                                        "brier": round(brier, 3), "n_semua": int(len(x)),
                                                        "tahun": f"{x.t0.min():%Y}–{x.t0.max():%Y}"}
    L.append("\n== Entry t0-1 searah sinyal (tutup 60 dtk; CEPAT | REALISTIS), semua judul ==")
    e = p2.EXITS.index("tutup 60s")
    for sumber, g in est.groupby("sumber"):
        for h in HOR:
            s = g[g[h].notna() & ((g[h] - 0.5).abs() >= TH)].drop_duplicates("t0")
            rec = {sc: [] for sc in p2.SCEN}
            for row in s.to_dict("records"):
                if row["t0"] not in mv:
                    continue
                d = p2.directional(mv[row["t0"]][1])
                if d is None:
                    continue
                side = 0 if row[h] > 0.5 else 1
                for i, sc in enumerate(p2.SCEN):
                    rec[sc].append({"time": row["t0"], "pnl": d[i, side, e]})
            c, r = (stats(pd.DataFrame(rec[k])) if rec[k] else {"n": 0} for k in ("CEPAT", "REALISTIS"))
            if c.get("n"):
                L.append(f"  {sumber:10} {h:7} n={c['n']:3} untung di {c['wr']:4.1f}% rilis | rata {c['avg']:+.2f}/0,01 "
                         f"lot (t {c['t']:+.1f}) | realistis {r['avg']:+.2f}")
    return "\n".join(L) + "\n", ekspor


def main() -> None:
    txt, ekspor = report()
    OUT.write_text(txt, encoding="utf-8")
    OUT_JSON.write_text(json.dumps({"dibuat": "research/hari_h_uji.py", "ambang": 0.5 + TH, "validasi": ekspor},
                                   ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(txt)
    print(f"ditulis {OUT} dan {OUT_JSON}")


if __name__ == "__main__":
    main()
