"""Uji astrologi finansial pada rilis berita AS: apakah posisi planet saat rilis menebak arah emas?

python -m research.astrologi       # -> docs/eksternal/hasil_astrologi.txt

Pertanyaan pengguna (1 Okt 2026): gambar chart Astro-Seek "2 Oct 2026, 08:30 am, Washington D.C." (= saat rilis NFP)
-> "apa itu, dan apakah hasilnya bisa diterapkan pada sistem kita jika akurat datanya?"

Posisi planet dihitung dengan PyEphem (zodiak tropis, ekuinoks tanggal itu = cara Astro-Seek), lokasi Washington D.C.
(38°54'N 77°2'W), rumah Placidus hanya untuk Ascendant. Fitur ditetapkan SEBELUM melihat hasil (yang umum dipakai
astrologi finansial):
  1. elemen Bulan (api/tanah/udara/air)          5. Bulan aspek keras (0/90/180°, orb 6°) dengan Mars atau Saturnus
  2. fase Bulan (bertambah / berkurang)           6. Matahari aspek keras dengan Saturnus (ada di chart pengguna)
  3. Merkurius retrograde                          7. elemen Ascendant
  4. tanda Bulan (12)                              8. elemen Mars
Target: emas naik 1 menit setelah rilis (mid tick t0-1 dtk -> t0+60 dtk; Dukascopy, cadangan Exness) dan arah kejutan
untuk emas (Act vs konsensus). Untuk tiap fitur: % naik per kategori vs dasar, uji chi-kuadrat, LAMA (< Okt 2021) vs
BARU, dan "aturan dari LAMA diterapkan ke BARU" (kategori terbaik di LAMA -> akurasinya di BARU). Banyak uji ->
p dikoreksi Bonferroni.
"""
from __future__ import annotations

import math
from pathlib import Path

import ephem
import numpy as np
import pandas as pd

from .news_detik import NEW, events, prepare

OUT = Path(__file__).resolve().parent.parent / "docs" / "eksternal" / "hasil_astrologi.txt"
LAT, LON = "38.9", "-77.0333"
ZODIAK = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn",
          "Aquarius", "Pisces"]
ELEMEN = ["api", "tanah", "udara", "air"]                     # Aries api, Taurus tanah, Gemini udara, Cancer air, ...
FITUR = ["elemen Bulan", "fase Bulan", "Merkurius retro", "tanda Bulan", "Bulan keras Mars/Saturnus",
         "Matahari keras Saturnus", "elemen Ascendant", "elemen Mars"]


def lon(body, t: ephem.Date) -> float:
    body.compute(t, epoch=t)
    return math.degrees(float(ephem.Ecliptic(body, epoch=t).lon)) % 360


def ascendant(t: ephem.Date) -> float:
    o = ephem.Observer()
    o.lat, o.lon, o.date, o.epoch = LAT, LON, t, t
    ramc = float(o.sidereal_time())
    eps = math.radians(23.4393 - 0.0000004 * (t - ephem.Date("2000/1/1")))
    phi = float(o.lat)
    asc = math.atan2(math.cos(ramc), -(math.sin(ramc) * math.cos(eps) + math.tan(phi) * math.sin(eps)))
    return math.degrees(asc) % 360


def hard(a: float, b: float, orb: float = 6.0) -> bool:
    d = abs((a - b + 180) % 360 - 180)
    return any(abs(d - x) <= orb for x in (0, 90, 180))


def chart(ts: pd.Timestamp) -> dict:
    t = ephem.Date(ts.tz_convert("UTC").tz_localize(None).to_pydatetime())
    sun, moon, merc = lon(ephem.Sun(), t), lon(ephem.Moon(), t), lon(ephem.Mercury(), t)
    mars, sat = lon(ephem.Mars(), t), lon(ephem.Saturn(), t)
    merc_next = lon(ephem.Mercury(), ephem.Date(t + 1))
    asc = ascendant(t)
    sign = lambda x: int(x // 30)  # noqa: E731
    return {"elemen Bulan": ELEMEN[sign(moon) % 4], "fase Bulan": "bertambah" if (moon - sun) % 360 < 180 else "berkurang",
            "Merkurius retro": "ya" if (merc_next - merc + 540) % 360 - 180 < 0 else "tidak",
            "tanda Bulan": ZODIAK[sign(moon)],
            "Bulan keras Mars/Saturnus": "ya" if hard(moon, mars) or hard(moon, sat) else "tidak",
            "Matahari keras Saturnus": "ya" if hard(sun, sat) else "tidak",
            "elemen Ascendant": ELEMEN[sign(asc) % 4], "elemen Mars": ELEMEN[sign(mars) % 4],
            "_pos": {"Matahari": sun, "Bulan": moon, "Merkurius": merc, "Mars": mars, "Saturnus": sat, "ASC": asc}}


def chi2_p(table: np.ndarray) -> float:
    """p chi-kuadrat (uji independensi kategori x naik/turun), tanpa scipy bila tidak ada."""
    try:
        from scipy.stats import chi2_contingency
        return float(chi2_contingency(table)[1]) if table.shape[0] > 1 else 1.0
    except Exception:  # noqa: BLE001
        return float("nan")


def dataset() -> pd.DataFrame:
    rows = []
    for e in events().itertuples():
        mv = None
        for aset in ("XAU", "XAU_EXNESS"):
            p = prepare(e.time, aset)
            if p is not None and p.at(-1) >= 0:
                mv = float(p.mid[p.at(60)] - p.mid[p.at(-1)])
                break
        if mv is None or mv == 0:
            continue
        c = chart(e.time)
        c.pop("_pos")
        rows.append({"time": e.time, "group": e.group, "naik": float(mv > 0),
                     "kejutan_emas": e.bias if e.bias in (1.0, -1.0) else np.nan, **c})
    return pd.DataFrame(rows)


def report() -> str:
    t0 = pd.Timestamp("2026-10-02 12:30", tz="UTC")
    c = chart(t0)
    pos = c.pop("_pos")
    L = ["# Astrologi finansial vs arah emas setelah rilis (research/astrologi.py)", "",
         "Cek posisi chart pengguna (2 Okt 2026 08:30 ET, Washington): " +
         ", ".join(f"{k} {ZODIAK[int(v // 30)]} {v % 30:.2f}°" for k, v in pos.items()),
         "Fitur chart itu: " + ", ".join(f"{k} = {v}" for k, v in c.items()), ""]
    df = dataset()
    base = df.naik.mean()
    L.append(f"Rilis dengan tick: {len(df)} ({df.time.min():%Y-%m}..{df.time.max():%Y-%m}); dasar emas naik 1 menit "
             f"{base * 100:.1f}%; uji = {len(FITUR)} fitur x 2 target -> Bonferroni x{2 * len(FITUR)}")
    for target, lab in (("naik", "emas naik 1 menit"), ("kejutan_emas", "kejutan bagus untuk emas")):
        L.append(f"\n== Target: {lab} ==")
        x = df[df[target].notna()].copy()
        x["y"] = (x[target] > 0).astype(float)
        for f in FITUR:
            g = x.groupby(f).y.agg(["mean", "size"])
            tab = np.array([[((x[f] == k) & (x.y == 1)).sum(), ((x[f] == k) & (x.y == 0)).sum()] for k in g.index])
            p = chi2_p(tab)
            old, new = x[x.time < NEW], x[x.time >= NEW]
            go = old.groupby(f).y.mean()
            best = go.idxmax() if len(go) else None
            worst = go.idxmin() if len(go) else None
            nb = new[new[f] == best].y.mean() if best is not None else np.nan
            nw = new[new[f] == worst].y.mean() if worst is not None else np.nan
            cells = " | ".join(f"{k} {m * 100:4.1f}% (n={n})" for k, (m, n) in g.iterrows())
            L.append(f"  {f:26} p={p:.3f} (Bonferroni {min(1, p * 2 * len(FITUR)):.2f}) | {cells}")
            L.append(f"  {'':26} aturan dari LAMA: terbaik '{best}' -> BARU {nb * 100:.1f}% naik; terburuk '{worst}' "
                     f"-> BARU {nw * 100:.1f}% (dasar BARU {new.y.mean() * 100:.1f}%)")
    return "\n".join(L) + "\n"


def main() -> None:
    txt = report()
    OUT.write_text(txt, encoding="utf-8")
    print(txt)
    print(f"ditulis {OUT}")


if __name__ == "__main__":
    main()
