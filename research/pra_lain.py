"""🔎 Metode LAIN (bukan Kalshi) untuk Fed, PPI, PCE, JOLTS → arah XAU 2–10 dtk setelah rilis (juga 1 & 15 menit).

python -m research.pra_lain               → docs/eksternal/hasil_pra_lain.txt

Permintaan pengguna 10 Okt 2026: "cari juga PPI, FED, PCE, JOLTS, dll — metode yang berbeda-beda, bukan hanya Kalshi".
Aturan ditetapkan SEBELUM melihat hasil; data hanya yang terbit sebelum rilis (FRED nilai rilis pertama); arah dipilih di
LAMA (< Okt 2021) bila LAMA n ≥ 15, selain itu sesuai teori; dinilai juga di BARU.
  FED (keputusan suku bunga, 14:00 ET):
    Y2     yield 2 th naik 5 hari bursa sebelum rapat (pasar sudah memasang nada keras)
    AKSI   aksi yang diharapkan konsensus (turun / naik / tahan) dari kalender
    DOT    rapat dengan proyeksi ekonomi/dot plot (Mar, Jun, Sep, Des)
    PRA2   gerak emas 2 jam sebelum pengumuman (drift pra-FOMC, Lucca & Moench 2015)
    T24    tren emas 24 jam sebelum pengumuman
    LALU   arah emas 10 dtk pada pengumuman Fed sebelumnya
  PPI:  PP   survei Fed daerah "harga yang dibayar" (Philly + Empire) bulan acuan naik → PPI di atas → emas turun
        DXY  dolar (indeks luas Fed) naik bulan acuan → harga impor turun → PPI di bawah → emas naik
        WTI  minyak WTI bulan acuan naik → PPI di atas → emas turun
  PCE:  NOW  nowcast core PCE Cleveland Fed (sebelum rilis) vs konsensus → searah
        CPIC kejutan core CPI bulan acuan searah
  JOLTS: NFP  kejutan NFP bulan acuan JOLTS (terbit ±1 bulan sebelumnya) searah
         ADP  kejutan ADP bulan acuan searah;  IND  lowongan Indeed bulan acuan naik → di atas
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import binom

from .news_detik import DATA, NEW
from .news_data import load_calendar, _num

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "eksternal" / "hasil_pra_lain.txt"
HH = (2, 3, 5, 10)


def sg(v) -> float:
    return 0.0 if v is None or v != v or v == 0 else float(np.sign(v))


def kal() -> pd.DataFrame:
    c = load_calendar(DATA)
    c = c[c.time >= pd.Timestamp("2009-06-01", tz="UTC")].copy()
    c["a"], c["f"], c["p"] = c.actual.map(_num), c.forecast.map(_num), c.previous.map(_num)
    c["s"] = np.sign(c.a - c.f)
    return c


def bulan_ini(df: pd.DataFrame, t: pd.Timestamp, bulan: pd.Timestamp) -> float:
    s = df[df.available < t].value
    return float(s.get(bulan, np.nan))


def ubah(df: pd.DataFrame, t: pd.Timestamp, bulan: pd.Timestamp) -> float:
    return sg(bulan_ini(df, t, bulan) - bulan_ini(df, t, (bulan.to_period("M") - 1).to_timestamp()))


def harian_ubah(df: pd.DataFrame, t: pd.Timestamp, hari: int) -> float:
    s = df[df.available < t].value
    return sg(s.iloc[-1] - s.iloc[-1 - hari]) if len(s) > hari else 0.0


def rata_bulan(df: pd.DataFrame, t: pd.Timestamp, bulan: pd.Timestamp) -> float:
    s = df[df.available < t].value
    cur = s[(s.index >= bulan) & (s.index < bulan + pd.offsets.MonthBegin(1))]
    pb = (bulan.to_period("M") - 1).to_timestamp()
    prv = s[(s.index >= pb) & (s.index < bulan)]
    return sg(cur.mean() - prv.mean()) if len(cur) >= 5 and len(prv) >= 5 else 0.0


def fitur() -> pd.DataFrame:
    from .eksternal_makro import fred
    from .pra_per_berita import fred_awal
    from .pra_xau_semua import bangun
    from .cpi_gabung import nowcast_table
    from .sumber_lain import indeed
    d = bangun()
    c = kal()
    y2 = fred("DGS2")
    wti = fred("DCOILWTICO")
    dxy = fred("DTWEXBGS")
    pp = [fred_awal("PPCDFSA066MSFRBPHI"), fred_awal("PPCDISA066MSFRBNY")]
    nc = nowcast_table()
    nc_all = nc
    try:
        from .cpi_gabung import JUDUL
        JUDUL["Core PCE Inflation"] = "Core PCE Price Index m/m"
        nc_all = nowcast_table()
    except Exception:  # noqa: BLE001
        pass
    ind = indeed()
    rows = []
    for r in d.itertuples():
        t, g = r.t0, r.grup
        if g not in ("FOMC", "PPI", "PCE", "JOLTS"):
            continue
        x = {"t0": t, "grup": g}
        m1 = (t.tz_convert(None).to_period("M") - 1).to_timestamp()
        if g == "FOMC":
            x["Y2"] = harian_ubah(y2, t, 5)
            fr = c[(c.event == "Federal Funds Rate") & ((c.time - t).abs() <= pd.Timedelta(hours=1))]
            if len(fr) and fr.f.iloc[0] == fr.f.iloc[0] and fr.p.iloc[0] == fr.p.iloc[0]:
                x["AKSI"] = sg(fr.f.iloc[0] - fr.p.iloc[0]) or 0.0
            x["DOT"] = 1.0 if t.month in (3, 6, 9, 12) else -1.0
            x["PRA2"] = r.M60 if r.M60 == r.M60 else 0.0      # pendekatan: gerak 60 mnt (pra_xau_semua, ketat)
            x["T24"] = r.H24 if r.H24 == r.H24 else 0.0
            x["LALU"] = r.LALU if r.LALU == r.LALU else 0.0
        elif g == "PPI":
            x["PP"] = -sg(sum(ubah(s, t, m1) for s in pp))
            x["DXY"] = rata_bulan(dxy, t, m1)
            x["WTI"] = -rata_bulan(wti, t, m1)
        elif g == "PCE":
            row = c[(c.event == "Core PCE Price Index m/m") & ((c.time - t).abs() <= pd.Timedelta(hours=1))]
            f = row.f.iloc[0] if len(row) else np.nan
            gnc = nc_all[(nc_all.event == "Core PCE Price Index m/m") & (nc_all.ref == m1.strftime("%Y-%m"))
                         & (nc_all.date < t.normalize())]
            if len(gnc) and f == f:
                dlt = gnc.sort_values("date").now.iloc[-1] - f
                x["NOW"] = -sg(dlt) if abs(dlt) >= 0.03 else 0.0
            cc = c[(c.event == "Core CPI m/m") & (c.time < t) & (c.time >= t - pd.Timedelta(days=25))]
            x["CPIC"] = -sg(cc.s.iloc[-1]) if len(cc) else 0.0
        elif g == "JOLTS":
            m2 = (m1.to_period("M") - 1).to_timestamp()               # bulan acuan JOLTS = 2 bulan sebelum rilis
            awal = (m2 + pd.offsets.MonthBegin(1)).tz_localize("UTC")   # rilis NFP/ADP bulan acuan = awal bulan berikutnya
            nf = c[(c.event == "Non-Farm Employment Change") & (c.time > awal) & (c.time < t)
                   & (c.time <= awal + pd.Timedelta(days=12))]
            x["NFP"] = -sg(nf.s.iloc[-1]) if len(nf) else 0.0
            ad = c[(c.event == "ADP Non-Farm Employment Change") & (c.time > awal) & (c.time < t)
                   & (c.time <= awal + pd.Timedelta(days=10))]
            x["ADP"] = -sg(ad.s.iloc[-1]) if len(ad) else 0.0
            try:
                s = ind[ind.index < t.tz_convert(None) - pd.Timedelta(days=1)]
                cur = s[(s.index >= m2) & (s.index < m2 + pd.offsets.MonthBegin(1))].mean()
                prv = s[(s.index >= m2 - pd.offsets.MonthBegin(1)) & (s.index < m2)].mean()
                x["IND"] = -sg(cur - prv)
            except Exception:  # noqa: BLE001
                x["IND"] = 0.0
        rows.append(x)
    fx = pd.DataFrame(rows)
    keep = ["t0"] + [col for col in d.columns if col.startswith("y")]
    return fx.merge(d[keep], on="t0", how="left")


FITUR = {"FOMC": ["Y2", "AKSI", "DOT", "PRA2", "T24", "LALU"], "PPI": ["PP", "DXY", "WTI"], "PCE": ["NOW", "CPIC"],
         "JOLTS": ["NFP", "ADP", "IND"]}


def skor(x: pd.DataFrame, v: np.ndarray, hs=HH) -> dict:
    baru_m = (pd.DatetimeIndex(x.t0) >= NEW)
    ok_all, nw_all = [], []
    for h in hs:
        y = x[f"y{h}_XAU_EXNESS"].to_numpy()
        y = np.where(np.isnan(y), x[f"y{h}_XAU"].to_numpy(), y)
        m = (v != 0) & ~np.isnan(y) & (y != 0)
        ok_all.append(np.sign(v[m]) == np.sign(y[m]))
        nw_all.append(np.asarray(baru_m)[m])
    ok, nw = np.concatenate(ok_all), np.concatenate(nw_all)
    n5, k5 = len(ok_all[2]), int(ok_all[2].sum())
    return {"benar": ok.mean() * 100 if len(ok) else np.nan, "n": n5,
            "lama": ok[~nw].mean() * 100 if (~nw).any() else np.nan, "n_lama": int((~nw_all[2]).sum()),
            "baru": ok[nw].mean() * 100 if nw.any() else np.nan, "n_baru": int(nw_all[2].sum()),
            "p": float(binom.sf(k5 - 1, n5, .5)) if n5 else 1.0}


def main() -> None:
    df = fitur()
    L = ["# 🔎 Metode lain (bukan Kalshi) untuk Fed, PPI, PCE, JOLTS → arah XAU 2–10 dtk", __doc__.split("\n\n")[1], ""]
    lolos = []
    for g, fs in FITUR.items():
        x = df[df.grup == g].reset_index(drop=True)
        L.append(f"\n## {g} ({len(x)} rilis dengan data emas)")
        t = pd.DatetimeIndex(x.t0)
        for f in fs:
            if f not in x:
                continue
            v = x[f].fillna(0).to_numpy()
            lama = t < NEW
            sl = skor(x[lama], v[lama])
            arah = (1.0 if sl["benar"] >= 50 else -1.0) if sl["n"] >= 15 and sl["benar"] == sl["benar"] else 1.0
            e = skor(x, arah * v)
            ok = (e["benar"] >= 60 and e["n"] >= 20 and (e["lama"] >= 55 or e["n_lama"] < 10) and e["baru"] >= 55
                  and e["p"] < 0.05)
            if ok:
                lolos.append((g, f, e))
            L.append(f"   {'✅' if ok else '  '} {f:5s} ({'searah' if arah > 0 else 'dibalik'}) 2–10 dtk {e['benar']:.1f}% "
                     f"(n {e['n']}; LAMA {e['lama']:.0f}% n {e['n_lama']}, BARU {e['baru']:.0f}% n {e['n_baru']}; "
                     f"p {e['p']:.3f})")
    L += ["", "## LOLOS (≥ 60%, LAMA & BARU ≥ 55%, p < 0,05)"]
    L += [f"   {g} • {f}: {e['benar']:.1f}% (n {e['n']})" for g, f, e in lolos] or ["   TIDAK ADA"]
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    _ = json


if __name__ == "__main__":
    main()
