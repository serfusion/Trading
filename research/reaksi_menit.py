"""Reaksi emas 1 dtk, 5 dtk & 1 menit setelah rilis, per judul berita dan per hasil (di bawah / sama / di atas konsensus).

python -m research.reaksi_menit     # -> data/research/eksternal/reaksi_menit.csv + cloud/api/reaksi.json

Dipakai "perkiraan hari H" di kartu 🎯 (cloud/api/_hari_h.py): peluang pasar prediksi (Kalshi/Polymarket) untuk tiap
hasil x seberapa sering emas naik 1 menit setelah hasil itu. Gerak = mid tick dari t0-1 dtk ke t0+1 / +5 / +60 dtk.
Arah 1 DETIK (permintaan pengguna 2 Okt 2026: "tuliskan hasilnya dan persentase akan ke mana setelah 1 detik news
release") dihitung dari rilis yang harganya sudah bergerak di detik itu ("diam" = mid belum berubah, dilaporkan terpisah)
dan dicek di dua feed: Dukascopy dan tick asli Exness (broker pengguna).
Konsensus & Act: kalender ForexFactory (research/news_prediksi.calendar(), s.d. Jan 2026). Tick: Dukascopy 2010-2026
(utama) dan Exness Cent 2015-2026 (cek). Periode LAMA (< Okt 2021) dan BARU dilaporkan.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .eksternal import cache_path
from .news_detik import NEW, prepare
from .news_prediksi import EVENTS, calendar

OUT_CSV = cache_path("reaksi_menit.csv")
OUT_JSON = Path(__file__).resolve().parent.parent / "cloud" / "api" / "reaksi.json"
FEEDS = {"XAU": "duka", "XAU_EXNESS": "exness"}
HASIL = {-1.0: "bawah", 0.0: "sama", 1.0: "atas"}
SECS = (1, 2, 3, 5, 60)
CEPAT = (1, 2, 3)                     # detik pertama yang ditampilkan di aplikasi (cloud/api/_persiapan.tahap)


def cepat(k: pd.DataFrame, feed: str, sec: int) -> dict:
    """Arah emas `sec` detik setelah rilis: % naik dari rilis yang harganya sudah bergerak, % masih diam,
    median |gerak| ($/ons) dari yang bergerak."""
    col = f"{feed}_{sec}"
    if col not in k:
        return {}
    v = k[col].dropna()
    mv = v[v != 0]
    if len(mv) < 5:
        return {}
    return {"naik": round(float((mv > 0).mean()), 3), "n": int(len(mv)), "diam": round(float((v == 0).mean()), 3),
            "gerak": round(float(mv.abs().median()), 2)}


def build() -> pd.DataFrame:
    cal = calendar()
    cal = cal[cal.event.isin(EVENTS)]
    rows, ticks = [], {}
    for t in sorted(cal.time.unique()):
        for aset, lab in FEEDS.items():
            p = prepare(pd.Timestamp(t), aset)
            if p is None or p.at(-1) < 0:
                continue
            m1 = p.mid[p.at(-1)]
            ticks[(t, lab)] = tuple(float(p.mid[p.at(k)] - m1) for k in SECS)
    for r in cal.itertuples():
        row = {"time": r.time, "event": r.event, "s": r.s, "z": abs(r.a - r.f)}
        for lab in FEEDS.values():
            g = ticks.get((r.time, lab)) or (np.nan,) * len(SECS)
            row.update({f"{lab}_{k}": v for k, v in zip(SECS, g)})
        rows.append(row)
    df = pd.DataFrame(rows)
    return df[df.duka_60.notna() | df.exness_60.notna()].reset_index(drop=True)


def rates(df: pd.DataFrame, before: pd.Timestamp | None = None, feed: str = "duka") -> dict:
    """{judul: {hasil: {"naik60", "naik5", "n"}}} dari rilis SEBELUM `before` (walk-forward) bila diberikan."""
    x = df if before is None else df[df.time < before]
    x = x[x[f"{feed}_60"].notna() & (x[f"{feed}_60"] != 0)]
    out = {}
    for ev, g in x.groupby("event"):
        cell = {}
        for s, lab in HASIL.items():
            k = g[g.s == s]
            if len(k) >= 5:
                kb = k[k.time >= NEW]
                cell[lab] = {"naik60": round(float((k[f"{feed}_60"] > 0).mean()), 3),
                             "naik5": round(float((k[f"{feed}_5"] > 0).mean()), 3), "n": int(len(k)),
                             "baru_naik60": round(float((kb[f"{feed}_60"] > 0).mean()), 3) if len(kb) >= 5 else None}
                fast = {}
                for sec in CEPAT:
                    c, b = cepat(k, feed, sec), cepat(kb, feed, sec)
                    if c:
                        fast[str(sec)] = dict(c, baru=b.get("naik"))
                if fast:
                    cell[lab]["cepat"] = fast
        if cell:
            cell["tahun"] = f"{g.time.min():%Y}–{g.time.max():%Y}"
            out[ev] = cell
    return out


BESAR = 1.5          # kejutan BESAR = |Act - perkiraan| >= 1,5x median |kejutan| judul itu (uji 2 Okt 2026)


def besar_kecil(df: pd.DataFrame, out: dict, feed: str = "duka") -> None:
    """Tambah out[judul]["ambang"] dan out[judul][hasil]["besar"/"kecil"]: reaksi emas per besar kejutan."""
    x = df[df[f"{feed}_60"].notna() & (df[f"{feed}_60"] != 0) & (df.s != 0) & df.z.notna()]
    for ev, g in x.groupby("event"):
        if ev not in out or len(g) < 20:
            continue
        amb = float(BESAR * g.z.median())
        out[ev]["ambang"] = round(amb, 6)
        for s, lab in ((-1.0, "bawah"), (1.0, "atas")):
            if lab not in out[ev]:
                continue
            for nama, k in (("besar", g[(g.s == s) & (g.z >= amb)]), ("kecil", g[(g.s == s) & (g.z < amb)])):
                if len(k) < 5:
                    continue
                kb = k[k.time >= NEW]
                v2 = k[f"{feed}_2"].dropna()
                v2 = v2[v2 != 0]
                out[ev][lab][nama] = {
                    "naik60": round(float((k[f"{feed}_60"] > 0).mean()), 3), "n": int(len(k)),
                    "baru_naik60": round(float((kb[f"{feed}_60"] > 0).mean()), 3) if len(kb) >= 5 else None,
                    "naik2": round(float((v2 > 0).mean()), 3) if len(v2) >= 5 else None,
                    "gerak60": round(float(k[f"{feed}_60"].abs().median()), 2)}


JAM = (3, 6)          # arah emas beberapa JAM setelah rilis (XAU M15), permintaan pengguna 2 Okt 2026 (NFP berbalik)


def jam_stats(out: dict) -> None:
    """Tambah out[judul][hasil]["jam"] = {"3": {naik, n, baru}, "6": ...}: % emas di atas harga open candle M15 rilis
    setelah 3 / 6 jam (research/nfp_berbalik.py untuk NFP). Persen dari rilis yang harganya berubah."""
    from .event_stats import xau_m15
    m = xau_m15()
    idx = m.index
    cal = calendar()
    cal = cal[cal.event.isin(list(out))]
    rows = []
    for r in cal.itertuples():
        t = pd.Timestamp(r.time)
        k = idx.searchsorted(t)
        if k >= len(idx) or idx[k] != t:
            continue
        o = m.open.iloc[k]
        row = {"time": t, "event": r.event, "s": r.s}
        for h in JAM:
            j = idx.searchsorted(t + pd.Timedelta(hours=h)) - 1
            row[f"j{h}"] = float(m.close.iloc[j] - o) if 0 <= j < len(idx) and idx[j] >= t else np.nan
        rows.append(row)
    df = pd.DataFrame(rows)
    for ev, g in df.groupby("event"):
        for s, lab in HASIL.items():
            k = g[g.s == s]
            if lab not in out[ev] or len(k) < 5:
                continue
            cell = {}
            for h in JAM:
                v = k[f"j{h}"].dropna()
                v = v[v != 0]
                vb = k[k.time >= NEW][f"j{h}"].dropna()
                vb = vb[vb != 0]
                if len(v) >= 5:
                    cell[str(h)] = {"naik": round(float((v > 0).mean()), 3), "n": int(len(v)),
                                    "baru": round(float((vb > 0).mean()), 3) if len(vb) >= 5 else None}
            if cell:
                out[ev][lab]["jam"] = cell


def main() -> None:
    df = build()
    df.to_csv(OUT_CSV, index=False)
    out = rates(df)
    besar_kecil(df, out)
    jam_stats(out)
    ex = rates(df, feed="exness")
    for ev, c in out.items():                     # cek feed kedua (tick asli Exness) untuk arah 1-3 detik
        for lab in ("bawah", "sama", "atas"):
            e = ((ex.get(ev) or {}).get(lab) or {}).get("cepat") or {}
            for sec, x in ((c.get(lab) or {}).get("cepat") or {}).items():
                if sec in e:
                    x["ex"], x["ex_n"] = e[sec]["naik"], e[sec]["n"]
    OUT_JSON.write_text(json.dumps({"dibuat": "research/reaksi_menit.py",
                                    "feed": "Dukascopy (mid t0-1 dtk -> +1/2/3/60 dtk); cepat.*.ex = tick Exness; jam = XAU M15 3/6 jam",
                                    "judul": out}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(df)} rilis; ditulis {OUT_CSV} dan {OUT_JSON}\n")
    for ev, c in out.items():
        cells = []
        for lab in ("bawah", "sama", "atas"):
            if lab in c:
                g = df[(df.event == ev) & (df.s == {"bawah": -1, "sama": 0, "atas": 1}[lab]) & df.duka_60.notna()]
                old, new = g[g.time < NEW], g[g.time >= NEW]
                ex = df[(df.event == ev) & (df.s == {"bawah": -1, "sama": 0, "atas": 1}[lab]) & df.exness_60.notna()]
                d1 = "".join(f"; {sec}d naik {x['naik'] * 100:3.0f}% (n={x['n']}, diam {x['diam'] * 100:.0f}%, BARU "
                             f"{(x.get('baru') or 0) * 100:.0f}%, Exness {(x.get('ex') or 0) * 100:.0f}%, "
                             f"|gerak| ${x['gerak']:.2f})" for sec, x in (c[lab].get("cepat") or {}).items())
                cells.append(f"{lab} naik1m {c[lab]['naik60'] * 100:3.0f}% (n={c[lab]['n']:3}; LAMA "
                             f"{(old.duka_60 > 0).mean() * 100:3.0f}% BARU {(new.duka_60 > 0).mean() * 100:3.0f}%; "
                             f"Exness {(ex.exness_60 > 0).mean() * 100:3.0f}%){d1}")
        print(f"- {ev} ({c['tahun']}): " + " | ".join(cells))


if __name__ == "__main__":
    main()
