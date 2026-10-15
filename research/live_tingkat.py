"""⚡ Tingkat keyakinan LIVE per berita: gerak emas di DETIK 2 setelah rilis → arah bertahan? (15 Okt 2026)

python -m research.live_tingkat        → cloud/api/live_tingkat.json + docs/eksternal/hasil_live_tingkat.txt

Permintaan pengguna 15 Okt: "PPI wajib 85%+ alias yakin; periksa news lain juga". Sebelum rilis tidak ada petunjuk ≥ 85%
(docs/PPI_15OKT.md). Satu-satunya keadaan ≥ 85% yang teruji = SETELAH rilis: emas sudah bergerak ≥ $X di detik 2 → arah sama di
detik 5 / 10 / lonjakan menit 1 / detik 60. Angka per KELOMPOK berita (CPI, PPI, NFP, FOMC, …) dan SEMUA, LAMA (< Okt 2021) &
BARU, dari gerak detik 2 tick Exness (cadangan Dukascopy) di research/pra_xau_semua (cache pra_xau_semua_v2.parquet) dan arah
lonjakan research/lonjakan.py (lonjakan60.parquet). Plus KEJAR: masuk setelah melihat detik 2 (detik 2,5; bid/ask asli Exness)
tutup detik 10 / 60 → untung % rilis & rata-rata $/oz (spread berita & telat sudah termasuk).
Aplikasi 4.42 memakai tabel ini di baris ⚡LIVE ("YAKIN 93% s/d detik 5" hanya bila tingkatnya ≥ 85% dan n ≥ 10).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
EKS = ROOT / "data" / "research" / "eksternal"
OUT_JSON = ROOT / "cloud" / "api" / "live_tingkat.json"
OUT_TXT = ROOT / "docs" / "eksternal" / "hasil_live_tingkat.txt"
SPLIT = pd.Timestamp("2021-10-01", tz="UTC")
TINGKAT = (0.5, 1.0, 2.0)


def data() -> pd.DataFrame:
    s = pd.read_parquet(EKS / "pra_xau_semua_v2.parquet")
    s["t0"] = pd.to_datetime(s.t0, utc=True)
    s = s[s.t0.dt.year >= 2016].copy()
    for k in ("2", "5", "10"):
        s[f"g{k}"] = s[f"y{k}_XAU_EXNESS"].where(s[f"y{k}_XAU_EXNESS"].notna(), s[f"y{k}_XAU"])
    lj = pd.read_parquet(EKS / "lonjakan60.parquet")[["t0", "grup", "arah", "ex_tutup60", "du_tutup60"]]
    lj["t0"] = pd.to_datetime(lj.t0, utc=True)
    lj["t60"] = lj.ex_tutup60.where(lj.ex_tutup60.notna(), lj.du_tutup60)
    x = s.merge(lj[["t0", "grup", "arah", "t60"]], on=["t0", "grup"], how="left")
    return x[x.g2.notna()].reset_index(drop=True)


def blok(x: pd.DataFrame) -> dict:
    out = {}
    for amb in TINGKAT:
        m = x.g2.abs() >= amb
        a = np.sign(x.g2)
        o = {}
        for nm, y in (("d5", np.sign(x.g5)), ("d10", np.sign(x.g10)), ("m1", x.arah), ("d60", x.t60)):
            ok = m & y.notna() & (y != 0)
            if not ok.any():
                continue
            o[nm] = round(float((a[ok] == y[ok]).mean() * 100))
            if nm == "d5":
                o["n"] = int(ok.sum())
                for per, mm in (("lama", x.t0 < SPLIT), ("baru", x.t0 >= SPLIT)):
                    q = ok & mm
                    o[f"{nm}_{per}"] = round(float((a[q] == y[q]).mean() * 100)) if q.sum() >= 5 else None
        if o.get("n"):
            out[str(amb)] = o
    return out


def kejar(x: pd.DataFrame) -> pd.DataFrame:
    from .exness import ticks_around
    rows = []
    for r in x.itertuples():
        try:
            tk = ticks_around("XAUUSDc", r.t0)
        except Exception:  # noqa: BLE001
            tk = None
        if tk is None or not len(tk):
            continue
        s = (tk.index - r.t0).total_seconds().to_numpy()
        bid, ask = tk.bid.to_numpy(), tk.ask.to_numpy()
        mid = (bid + ask) / 2

        def at(sec, arr):
            i = np.searchsorted(s, sec, side="right") - 1
            return arr[i] if i >= 0 and sec - s[i] < 30 else np.nan
        m0, m2 = at(-1, mid), at(2, mid)
        if np.isnan(m0) or np.isnan(m2) or m0 == m2:
            continue
        a = np.sign(m2 - m0)
        e = at(2.5, ask) if a > 0 else at(2.5, bid)
        for ex in (10, 60):
            c = at(ex, bid) if a > 0 else at(ex, ask)
            rows.append({"t0": r.t0, "grup": r.grup, "mv": m2 - m0, "ex": ex, "pl": (c - e) * a})
    return pd.DataFrame(rows).dropna()


def blok_kejar(k: pd.DataFrame) -> dict:
    out = {}
    for amb in TINGKAT:
        o = {}
        for ex in (10, 60):
            g = k[(k.mv.abs() >= amb) & (k.ex == ex)]
            if len(g) >= 5:
                o[f"t{ex}"] = {"untung": round(float((g.pl > 0).mean() * 100)), "rata": round(float(g.pl.mean()), 2),
                               "n": int(len(g))}
        if o:
            out[str(amb)] = o
    return out


def main() -> None:
    x = data()
    k = kejar(x)
    res, L = {}, ["# ⚡ Tingkat LIVE detik 2 per berita (research/live_tingkat.py)", __doc__.split("\n\n")[1]]
    for g in ["SEMUA"] + sorted(x.grup.unique()):
        xx = x if g == "SEMUA" else x[x.grup == g]
        kk = k if g == "SEMUA" else k[k.grup == g]
        b = blok(xx)
        if not b:
            continue
        res[g] = {"tingkat": b, "kejar": blok_kejar(kk), "n_rilis": int(len(xx))}
        L.append(f"\n## {g} ({len(xx)} rilis 2016–2026)")
        for amb, o in b.items():
            kj = res[g]["kejar"].get(amb, {})
            L.append(f"   detik 2 ≥ ${amb}: detik 5 {o.get('d5')}% (n {o['n']}; lama {o.get('d5_lama')} / baru {o.get('d5_baru')}) • "
                     f"detik 10 {o.get('d10')}% • lonjakan menit 1 {o.get('m1')}% • detik 60 {o.get('d60')}% | KEJAR tutup 10 dtk "
                     f"{kj.get('t10', {}).get('untung')}% ${kj.get('t10', {}).get('rata')} • 60 dtk {kj.get('t60', {}).get('untung')}% "
                     f"${kj.get('t60', {}).get('rata')}")
    OUT_JSON.write_text(json.dumps({"dibuat": pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d"),
                                    "sumber": "research/live_tingkat.py", "grup": res}, ensure_ascii=False, indent=1) + "\n",
                        encoding="utf-8")
    OUT_TXT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
