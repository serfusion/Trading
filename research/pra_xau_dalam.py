"""⏱️ XAU 1–10 detik: riset MENDALAM NFP, PPI, JOLTS (tebakan sebelum rilis) + kepastian setelah detik pertama.

python -m research.pra_xau_dalam          → docs/eksternal/hasil_pra_xau_dalam.txt + cloud/api/pra_aset.json

Permintaan pengguna 10 Okt 2026 (VERY IMPORTANT URGENT): "sisa NFP, PPI, JOLTS yang belum dianalisa menyeluruh; cari semua
informasinya; hitung yang benar-benar pasti untuk XAU 1–10 detik pasca rilis". Semua aturan ditetapkan SEBELUM melihat
hasil; data hanya yang sudah terbit sebelum rilis.

A. Tebakan ARAH KEJUTAN (Act vs konsensus) sebelum rilis — lalu ARAH XAU 1–10 detik (harga tengah t0−1 vs t0+h, tick
   Exness; Dukascopy pembanding) mengikuti reaksi historis per judul (cloud/api/reaksi.json):
   NFP / pengangguran / upah:
     P     kejutan rilis sebelumnya searah;  -P berbalik
     ADP   kejutan ADP pekan itu searah (≤ 7 hari)          CLM  klaim 4 pekan (terbalik)
     K     pasar Kalshi (2023–2025)                          IND  lowongan Indeed bulan acuan; EMP survei Fed daerah
     KUMP  periode pengumpulan BLS pendek (≤ 24 hari dari tanggal 12 bulan acuan ke rilis) → NFP DI BAWAH (respons
           survei rendah → cetakan awal lemah; hipotesis dari literatur revisi NFP)
     BLN   musiman bulan: arah kejutan mayoritas bulan kalender yang sama di tahun-tahun SEBELUMNYA (walk-forward;
           ≥ 5 tahun & ≥ 65% searah)
     ANK   anchoring Campbell-Sharpe: kejutan searah (konsensus − angka bulan lalu)
   PPI / core PPI:
     CPI   kejutan CPI (core CPI untuk core PPI) yang rilis ≤ 10 hari SEBELUM PPI, searah
     -P, P, WTI (minyak bulan acuan), PP (harga yang dibayar Fed daerah), BLN, ANK
   JOLTS (bulan acuan = 2 bulan sebelum rilis):
     IND2  lowongan Indeed bulan acuan JOLTS (2 bulan sebelum rilis) naik → DI ATAS
     -P, P, CLM, BLN, ANK
B. KEPASTIAN SETELAH DETIK PERTAMA (bisa dilihat setelah entry): bila harga sudah bergerak ≥ $x di detik 1 (atau 2),
   seberapa sering arah itu masih sama di detik 3/5/10 — untuk memutuskan TAHAN atau TUTUP cepat.
Lolos (A) = > 50% di LAMA (< Okt 2021) & BARU, p binomial < 0,05, dan arah XAU 2–10 dtk > 55% di Exness & Dukascopy.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .berita_gabung import emas, nilai, tabel, teks
from .news_detik import NEW, prepare
from .pra_xau_arah import binom_p

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "eksternal" / "hasil_pra_xau_dalam.txt"
JSON = ROOT / "cloud" / "api" / "pra_aset.json"
H = [1, 2, 3, 5, 10]
NFP_J = ["Non-Farm Employment Change", "Unemployment Rate", "Average Hourly Earnings m/m"]
PPI_J = ["PPI m/m", "Core PPI m/m"]
JOLTS_J = ["JOLTS Job Openings"]
FEEDS = ("XAU_EXNESS", "XAU")


def fitur_tambahan(df: pd.DataFrame) -> pd.DataFrame:
    """Kolom prediktor baru per baris (event, t0) — semua dari data sebelum rilis."""
    from .news_prediksi import calendar, last_before
    from .sumber_lain import fitur, indeed, ubah_bulan
    cal = calendar()
    ind = indeed()
    df = df.copy()
    sg = lambda v: 0.0 if v is None or v != v or v == 0 else float(np.sign(v))  # noqa: E731
    base = fitur(df[df.event.isin(NFP_J + PPI_J + JOLTS_J)].copy())[["t0", "event", "WTI", "PP", "EMP", "CC", "IND"]]
    df = df.merge(base, on=["t0", "event"], how="left")
    rows = []
    for r in df.itertuples():
        t, ev = r.t0, r.event
        f = {}
        f["ADP"] = last_before(cal, "ADP Non-Farm Employment Change", t, 7) if ev in NFP_J else np.nan
        if ev == "Unemployment Rate" and f["ADP"] == f["ADP"]:
            f["ADP"] = -f["ADP"]
        if ev in NFP_J + JOLTS_J:
            cl = cal[(cal.event == "Unemployment Claims") & (cal.time < t) & (cal.time >= t - pd.Timedelta(days=28))]
            v = -float(np.sign(cl.s.sum())) if len(cl) else np.nan
            f["CLM"] = -v if ev == "Unemployment Rate" else v
        ref12 = (t - pd.DateOffset(months=1)).replace(day=12)
        hari = (t.normalize() - ref12.normalize()).days
        f["KUMP"] = (-1.0 if hari <= 24 else 0.0) if ev in NFP_J else np.nan
        if ev == "Unemployment Rate" and f["KUMP"] == f["KUMP"]:
            f["KUMP"] = -f["KUMP"]
        # musiman bulan (walk-forward): mayoritas tanda kejutan bulan kalender sama di tahun-tahun sebelumnya
        lalu = cal[(cal.event == ev) & (cal.time < t - pd.Timedelta(days=300)) & (cal.time.dt.month == t.month)]
        lalu = lalu[lalu.s != 0]
        if len(lalu) >= 5 and max((lalu.s > 0).mean(), (lalu.s < 0).mean()) >= 0.65:
            f["BLN"] = 1.0 if (lalu.s > 0).mean() >= 0.65 else -1.0
        else:
            f["BLN"] = 0.0
        # anchoring: konsensus − angka bulan lalu (cetakan awal)
        sebelum = cal[(cal.event == ev) & (cal.time < t)].tail(1)
        f["ANK"] = sg(r.f - sebelum.a.iloc[0]) if len(sebelum) and hasattr(r, "f") else np.nan
        if ev in PPI_J:
            src = "CPI m/m" if ev == "PPI m/m" else "Core CPI m/m"
            f["CPI"] = last_before(cal, src, t, 10)
        if ev in JOLTS_J:
            ref = (t - pd.DateOffset(months=2)).to_period("M")
            s = ind.value[ind.available < t]
            per = pd.DatetimeIndex(s.index).to_period("M")
            a, b = s[per == ref], s[per == ref - 1]
            f["IND2"] = sg(a.mean() - b.mean()) if len(a) and len(b) else np.nan
        rows.append(f)
    out = pd.concat([df.reset_index(drop=True), pd.DataFrame(rows)], axis=1)
    _ = ubah_bulan
    return out


def gerak_xau(times) -> dict:
    out = {}
    for f in FEEDS:
        out[f] = {}
        for t in times:
            p = prepare(pd.Timestamp(t), f)
            if p is None:
                continue
            i = p.at(-1)
            if i < 0 or p.T[i] < -60:
                continue
            out[f][t] = {h: float(p.mid[p.at(h)] - p.mid[i]) for h in H if p.at(h) >= 0}
    return out


def e2e(x: pd.DataFrame, col: str, gk: dict) -> dict:
    """Arah XAU per detik bila mengikuti tebakan kolom `col` (arah emas lewat reaksi per judul)."""
    y = x[x[col].notna() & (x[col] != 0) & x.arah_bawah.notna()]
    arah = pd.Series(np.where(y[col] < 0, y.arah_bawah, y.arah_atas), index=y.t0).groupby(level=0).sum()
    arah = np.sign(arah[arah != 0])
    out = {}
    for f in FEEDS:
        for h in H:
            v = [(t, np.sign(gk[f][t][h]) * d) for t, d in arah.items() if t in gk[f] and h in gk[f][t]
                 and gk[f][t][h] != 0]
            if not v:
                continue
            tt = pd.DatetimeIndex([a for a, _ in v])
            ok = np.array([b > 0 for _, b in v])
            k, n = int(ok.sum()), len(ok)
            out[(f, h)] = {"benar": round(k / n * 100, 1), "n": n, "p": round(binom_p(k, n), 4),
                           "lama": round(float(ok[tt < NEW].mean() * 100), 1) if (tt < NEW).any() else None,
                           "baru": round(float(ok[tt >= NEW].mean() * 100), 1) if (tt >= NEW).any() else None}
    return out


def lanjut(gk: dict, times_grup: dict) -> dict:
    """B: arah detik k (1/2) bertahan sampai detik h (3/5/10) bila gerak detik k ≥ x."""
    out = {}
    for g, ts in times_grup.items():
        for k in (1, 2):
            for x in (0.3, 0.5, 1.0, 2.0):
                for h in (3, 5, 10):
                    v = []
                    for t in ts:
                        m = gk["XAU_EXNESS"].get(t)
                        if not m or k not in m or h not in m or abs(m[k]) < x or m[h] == 0:
                            continue
                        v.append((t, np.sign(m[k]) == np.sign(m[h])))
                    if len(v) >= 10:
                        tt = pd.DatetimeIndex([a for a, _ in v])
                        ok = np.array([b for _, b in v])
                        out[f"{g}|{k}|{x}|{h}"] = {"tetap": round(float(ok.mean() * 100), 1), "n": len(ok),
                                                   "lama": round(float(ok[tt < NEW].mean() * 100), 1) if (tt < NEW).any() else None,
                                                   "baru": round(float(ok[tt >= NEW].mean() * 100), 1) if (tt >= NEW).any() else None}
    return out


def main() -> None:
    df = emas(tabel())
    df = df[df.event.isin(NFP_J + PPI_J + JOLTS_J + ["CPI m/m", "ISM Services PMI"])].copy()
    df["-P"] = -df.P
    df = fitur_tambahan(df)
    df["-P"] = -df.P
    times = sorted(set(df.t0))
    gk = gerak_xau(times)
    L = ["# ⏱️ XAU 1–10 detik: riset mendalam NFP, PPI, JOLTS", __doc__.split("\n\n")[1], ""]
    kolom = {"Non-Farm Employment Change": ["P", "-P", "ADP", "CLM", "K", "IND", "EMP", "KUMP", "BLN", "ANK"],
             "Unemployment Rate": ["P", "-P", "ADP", "CLM", "K", "IND", "EMP", "KUMP", "BLN", "ANK"],
             "Average Hourly Earnings m/m": ["P", "-P", "BLN", "ANK"],
             "PPI m/m": ["CPI", "P", "-P", "WTI", "PP", "BLN", "ANK"],
             "Core PPI m/m": ["CPI", "P", "-P", "PP", "BLN", "ANK"],
             "JOLTS Job Openings": ["IND2", "P", "-P", "CLM", "BLN", "ANK"]}
    simpan = {}
    for ev, cols in kolom.items():
        x = df[df.event == ev].copy()
        L += ["", f"## {ev} ({len(x)} rilis {x.t0.min():%Y-%m}–{x.t0.max():%Y-%m})"]
        for c in cols:
            if c not in x or not x[c].notna().any():
                continue
            v = nilai(x, c)
            t, ok = teks(v)
            r = e2e(x, c, gk)
            ex = [r.get(("XAU_EXNESS", h), {}).get("benar") for h in H]
            du = [r.get(("XAU", h), {}).get("benar") for h in H]
            n_ex = r.get(("XAU_EXNESS", 3), {}).get("n")
            lolos = ok and all(e is not None and e > 55 for e in ex[1:]) and all(d is not None and d > 55 for d in du[1:])
            L.append(f"   {'✅' if lolos else ('🟡' if ok else '  ')} {c:5s} angka: {t}")
            L.append(f"         XAU searah (Exness, n {n_ex}): " + " • ".join(f"{h} dtk {e}%" for h, e in zip(H, ex))
                     + " | Dukascopy: " + " • ".join(f"{h} dtk {d}%" for h, d in zip(H, du)))
            if ok or lolos:
                simpan[f"{ev}|{c}"] = {"angka": v, "xau": {f"{f}|{h}": r.get((f, h)) for f in FEEDS for h in H},
                                      "lolos": bool(lolos)}
    # varian gabungan PPI (headline & core): kejutan CPI pekan itu → arah XAU (format pra_aset.json["xau_arah"])
    x = df[df.event.isin(PPI_J)].copy()
    r = e2e(x, "CPI", gk)
    v_ppi = {"grup": "PPI", "h": {f"{h}|0": {"exness": r.get(("XAU_EXNESS", h), {}), "dukascopy": r.get(("XAU", h), {}),
                                                "konsisten": False} for h in H}}
    # semua grup berita (news_detik.events) untuk B: kepastian setelah detik pertama
    from .news_detik import events
    ev = events()
    ev = ev[ev.time >= pd.Timestamp("2015-01-01", tz="UTC")]
    tg = {g: sorted(ev[ev.group == g].time) for g in ("NFP", "CPI", "PPI", "RETAIL", "PCE", "GDP", "FOMC", "JOLTS",
                                                      "ISM", "ADP", "CLAIMS")}
    tg["ISM Jasa"] = sorted(set(df[df.event == "ISM Services PMI"].t0))
    tg["SEMUA"] = sorted(ev.time)
    gk.update({f: {**gk[f], **gerak_xau([t for ts in tg.values() for t in ts if t not in gk[f]])[f]} for f in FEEDS})
    lj = lanjut(gk, tg)
    L += ["", "## B. Kepastian setelah detik pertama (tick Exness): arah detik k bertahan sampai detik h bila gerak detik k ≥ x"]
    for g in tg:
        for k in (1, 2):
            if g == "SEMUA" and k == 1:
                pass
            baris = []
            for x in (0.3, 0.5, 1.0, 2.0):
                parts = [f"{h} dtk {lj[f'{g}|{k}|{x}|{h}']['tetap']}%" for h in (3, 5, 10) if f"{g}|{k}|{x}|{h}" in lj]
                n = lj.get(f"{g}|{k}|{x}|10", {}).get("n")
                if parts:
                    baris.append(f"≥${x:g} (n {n}): " + ", ".join(parts))
            if baris:
                L.append(f"   {g:8s} detik {k}: " + " | ".join(baris))
    d = json.loads(JSON.read_text(encoding="utf-8")) if JSON.exists() else {}
    d["dalam"] = simpan
    d["lanjut"] = lj
    d.setdefault("xau_arah", {})["PPI • kejutan CPI pekan ini"] = v_ppi
    # aturan "CPI" untuk PPI & core PPI ke petunjuk.json (dibaca _petunjuk.py)
    pj = ROOT / "cloud" / "api" / "petunjuk.json"
    pd_ = json.loads(pj.read_text(encoding="utf-8"))
    for ev_ in PPI_J:
        y = df[df.event == ev_]
        v = nilai(y, "CPI")
        ek = e2e(y, "CPI", gk).get(("XAU_EXNESS", 3), {})
        pd_["aturan"].setdefault(ev_, {})["CPI"] = {
            "benar": v["semua"][0], "n": v["semua"][1], "lama": list(v["LAMA"]), "baru": list(v["BARU"]),
            "emas": [round((ek.get("benar") or 0) * (ek.get("n") or 0) / 100), ek.get("n") or 0],
            "tahun": "2010–2025", "jenis": "xau 3 dtk"}
    pj.write_text(json.dumps(pd_, ensure_ascii=False, indent=1), encoding="utf-8")
    JSON.write_text(json.dumps(d, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
