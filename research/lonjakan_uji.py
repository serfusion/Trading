"""📈 Uji tutup kertas dengan target ARAH LONJAKAN TERBESAR MENIT PERTAMA (research/lonjakan.py) — CPI & semua berita.

python -m research.lonjakan_uji [cpi|pola|berita|semua]   → docs/eksternal/hasil_lonjakan_uji.txt

Permintaan pengguna 11 Okt 2026: "hitungannya per detik, tapi hasil akhirnya beberapa detik yang diambil tinggi candle per
menit (menit pertama), entah tinggi naik atau tinggi turun". Target = arah lonjakan terbesar 0–60 dtk (bukan detik 1 saja).
Tutup kertas sama seperti sebelumnya: tahun Y hanya melihat rilis < Y; aturan dipakai di tahun Y hanya bila tahun-tahun lalu
benar > 50% (n ≥ 10). Petunjuk disimpan sebagai arah "baik untuk USD" → tebakan emas = kebalikannya.
Validitas: permutasi keluarga (hasil emas diacak antar rilis 2.000×, dibanding aturan TERBAIK acakan; hanya aturan dengan
≥ 40 rilis sejak 2016 & ≥ 20 sejak 2022). LOLOS = tutup kertas ≥ 60% (2016–2026), > 50% LAMA & BARU, p < 0,05.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "eksternal" / "hasil_lonjakan_uji.txt"
SPLIT = pd.Timestamp("2021-10-01", tz="UTC")
MULAI = 2013
N_PERM = 2000


def tutup(usd: np.ndarray, y: np.ndarray, th: np.ndarray) -> np.ndarray:
    """Tebakan emas tutup kertas (0 = tidak menebak) dari petunjuk arah USD."""
    g = -np.asarray(usd, float)
    out = np.zeros(len(g))
    for Y in range(MULAI, int(th.max()) + 1):
        lalu = (th < Y) & (g != 0) & (y != 0)
        if lalu.sum() >= 10 and (g[lalu] == y[lalu]).mean() > 0.5:
            out[th == Y] = g[th == Y]
    return out


def sk(tb: np.ndarray, y: np.ndarray, m: np.ndarray) -> tuple[int, int]:
    ok = m & (tb != 0) & (y != 0)
    return int((tb[ok] == y[ok]).sum()), int(ok.sum())


def pct(k: int, n: int) -> str:
    return f"{k / n * 100:5.1f}% ({k}/{n})" if n else "    –"


def baris(tb, y, t0, th) -> tuple[str, tuple]:
    m = {"semua": th >= 2016, "LAMA": (th >= 2016) & (t0 < SPLIT), "BARU": t0 >= SPLIT, "2022+": th >= 2022,
         "2026": th == 2026}
    r = {k: sk(tb, y, v) for k, v in m.items()}
    return " | ".join(f"{k} {pct(*v)}" for k, v in r.items()), r


def keluarga(C: dict, y: np.ndarray, th: np.ndarray, rng) -> dict:
    """p permutasi keluarga per aturan (mentah, tanpa saringan tahun lalu)."""
    s16, b22 = th >= 2016, th >= 2022
    cukup = [c for c, v in C.items() if ((v != 0) & s16).sum() >= 40 and ((v != 0) & b22).sum() >= 20]
    if not cukup:
        return {}

    def h(v, yy, m):
        g = -v
        ok = m & (g != 0) & (yy != 0)
        return (g[ok] == yy[ok]).mean() if ok.any() else np.nan
    obs = {c: (h(C[c], y, s16), h(C[c], y, b22)) for c in cukup}
    m16, m22 = [], []
    for _ in range(N_PERM):
        yp = y[rng.permutation(len(y))]
        m16.append(np.nanmax([h(C[c], yp, s16) for c in cukup]))
        m22.append(np.nanmax([h(C[c], yp, b22) for c in cukup]))
    m16, m22 = np.array(m16), np.array(m22)
    return {c: (float((m16 >= o[0]).mean()), float((m22 >= o[1]).mean()), o) for c, o in obs.items()}


def uji_grup(nama: str, x: pd.DataFrame, aturan: list[str], L: list, lolos: list, rng, plafon: str | None = None):
    y = x.L.to_numpy()
    th, t0 = x.th.to_numpy(), x.t0
    L.append(f"\n## {nama} ({len(x)} rilis {t0.min():%Y-%m}–{t0.max():%Y-%m}; lonjakan naik "
             f"{(y > 0).sum() / max((y != 0).sum(), 1) * 100:.0f}%)")
    L.append("   selalu NAIK  " + baris(np.ones(len(x)), y, t0, th)[0])
    if plafon:
        L.append("   PLAFON       " + baris(-x[plafon].fillna(0).to_numpy(), y, t0, th)[0])
    C = {c: x[c].fillna(0).to_numpy() for c in aturan if c in x}
    kel = keluarga(C, y, th, rng)
    for c, v in C.items():
        tb = tutup(v, y, th)
        s, r = baris(tb, y, t0, th)
        p = kel.get(c)
        ok = False
        if p:
            (k, n), (kl, nl), (kb, nb) = r["semua"], r["LAMA"], r["BARU"]
            ok = n and k / n >= 0.6 and nl and kl / nl > 0.5 and nb and kb / nb > 0.5 and min(p[0], p[1]) < 0.05
        L.append(f"   {c:9s} {s}" + (f" | p {p[0]:.3f}/{p[1]:.3f}" if p else "") + ("  ✅ LOLOS" if ok else ""))
        if ok:
            lolos.append(f"{nama} {c}")


def lonjakan() -> pd.DataFrame:
    from .lonjakan import tabel
    d = tabel()[["t0", "grup", "arah", "detik", "besar"]].rename(columns={"arah": "L"})
    return d


def cpi(L: list, lolos: list, rng) -> None:
    from . import cpi_detik as cd
    df = cd.turunan(cd.tabel())
    lj = lonjakan()
    df = df.merge(lj[lj.grup == "CPI"][["t0", "L", "detik", "besar"]], on="t0", how="left")
    df = df[df.L.notna()].reset_index(drop=True)
    aturan = cd.PETUNJUK + list(cd.TURUNAN) + ["SUARA", "SUARA_IDX", "IDX|K", "K|IDX"]
    uji_grup("CPI", df, aturan, L, lolos, rng, plafon="PLAFON_net")
    simpan_cpi(df, rng)


def simpan_cpi(df: pd.DataFrame, rng) -> None:
    """cloud/api/cpi_detik.json["lonjakan"]: angka tutup kertas aturan terpasang (IDX|K) dengan target lonjakan menit 1."""
    import json

    from . import cpi_detik as cd
    y, th, t0 = df.L.to_numpy(), df.th.to_numpy(), df.t0
    tb = tutup(df["IDX|K"].to_numpy(), y, th)

    def st(m):
        k, n = sk(tb, y, m)
        return round(k / n * 100, 1) if n else None
    kel = keluarga({c: df[c].fillna(0).to_numpy() for c in cd.PETUNJUK + list(cd.TURUNAN) +
                    ["SUARA", "SUARA_IDX", "IDX|K", "K|IDX"]}, y, th, rng).get("IDX|K", (None, None))
    out = {"semua": st(th >= 2016), "lama": st((th >= 2016) & (t0 < SPLIT)), "baru": st(t0 >= SPLIT),
           "s2022": st(th >= 2022), "n_rilis": int(((tb != 0) & (th >= 2016)).sum()),
           "selalu_naik": round(float((y[th >= 2016] > 0).sum() / max((y[th >= 2016] != 0).sum(), 1) * 100), 1),
           "plafon": None, "puncak_detik": float(df.detik.median()),
           "besar_2024": round(float(df[df.th >= 2024].besar.median()), 2),
           "p_keluarga_2016": kel[0], "p_keluarga_2022": kel[1],
           "per_tahun": {str(Y): list(sk(tb, y, th == Y)) for Y in range(2016, int(th.max()) + 1) if sk(tb, y, th == Y)[1]}}
    pl = -df.PLAFON_net.fillna(0).to_numpy()
    k, n = sk(pl, y, th >= 2016)
    out["plafon"] = round(k / n * 100, 1) if n else None
    d = json.loads(cd.JSON.read_text(encoding="utf-8"))
    d["lonjakan"] = out
    cd.JSON.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def pola(L: list, lolos: list, rng) -> None:
    """Pola tetap per jenis berita (tanpa data berita): mayoritas lalu, rilis terakhir, 3 terakhir, tahun berjalan."""
    lj = lonjakan()
    lj["th"] = lj.t0.dt.year
    for g in ["CPI", "PPI", "FOMC", "ISM", "NFP", "RETAIL", "PCE", "GDP", "JOLTS", "ADP", "CLAIMS", "KONSUMEN"]:
        x = lj[lj.grup == g].sort_values("t0").reset_index(drop=True)
        y, th = x.L.fillna(0).to_numpy(), x.th.to_numpy()
        n = len(x)
        r = {k: np.zeros(n) for k in ("MAYOR", "TAHUN", "LALU1", "LALU3")}
        for i in range(n):
            lalu = y[:i][y[:i] != 0]
            if len(lalu) >= 10:
                r["MAYOR"][i] = np.sign(lalu.sum())
            ini = y[:i][(th[:i] == th[i]) & (y[:i] != 0)]
            if len(ini) >= 2:
                r["TAHUN"][i] = np.sign(ini.sum())
            if len(lalu):
                r["LALU1"][i] = lalu[-1]
            if len(lalu) >= 3:
                r["LALU3"][i] = np.sign(lalu[-3:].sum())
        for k, v in r.items():
            x[k] = -v                                        # simpan sebagai "arah USD" (tebakan emas = −)
        x["L"] = y
        uji_grup(f"POLA {g}", x, list(r), L, lolos, rng)


def berita(L: list, lolos: list, rng) -> None:
    from .berita_detik import ATURAN, tabel
    df = tabel()
    lj = lonjakan()
    df = df.merge(lj[["t0", "L"]], on="t0", how="left")
    for g, at in ATURAN.items():
        x = df[(df.grup == g) & df.L.notna()].reset_index(drop=True)
        if len(x) < 20:
            continue
        khusus = [c for c in at if c not in ("P", "P3", "KON")]
        for c in at:
            if c not in x:
                x[c] = 0.0
        x["SUARA"] = np.sign(x[khusus + ["P"]].fillna(0).sum(axis=1))
        uji_grup(g, x, at + ["SUARA"], L, lolos, rng, plafon="PLAFON")


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "semua"
    L = ["# 📈 Tutup kertas — target: arah lonjakan terbesar menit pertama", __doc__.split("\n\n")[1], ""]
    lolos, rng = [], np.random.default_rng(9)
    if mode in ("cpi", "semua"):
        cpi(L, lolos, rng)
    if mode in ("pola", "semua"):
        pola(L, lolos, rng)
    if mode in ("berita", "semua"):
        berita(L, lolos, rng)
    L.append("\nLOLOS: " + (", ".join(lolos) or "TIDAK ADA"))
    out = OUT if mode == "semua" else OUT.with_name(f"hasil_lonjakan_uji_{mode}.txt")
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
