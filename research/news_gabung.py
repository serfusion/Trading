"""Gabungan kejutan SEMUA berita terbaru → arah emas 1 jam setelah berita berikutnya — python -m research.news_gabung

Permintaan pengguna 7 Okt 2026 ("tambahkan dari seluruh berita terupdate untuk meningkatkan peringkat"). Untuk tiap rilis
target, skor = jumlah arah-emas dari kejutan berita LAIN yang sudah rilis dalam jendela 7 / 30 hari (+1 bila data lebih
lemah dari perkiraan untuk USD = biasanya emas naik; klaim & pengangguran dibalik). Juga per kelompok (inflasi, tenaga
kerja). Aturan lolos (dikunci sebelum melihat BARU): searah & ≥ 58% di LAMA (< Okt 2021) DAN BARU, n ≥ 30 masing-masing,
lalu dicek per tahun. NFP juga dibandingkan dengan model mean reversion (nfp_mean.csv).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import binomtest

from .eksternal import cache_path
from .news_prediksi import EVENTS, INVERSE, calendar
from .news_semua import SPLIT, build

OUT = Path(__file__).resolve().parent.parent / "docs" / "eksternal" / "hasil_news_gabung.txt"
INFL = {"CPI m/m", "Core CPI m/m", "CPI y/y", "PPI m/m", "Core PPI m/m", "Core PCE Price Index m/m",
        "Average Hourly Earnings m/m"}
KERJA = {"Non-Farm Employment Change", "Unemployment Rate", "ADP Non-Farm Employment Change", "Unemployment Claims",
         "JOLTS Job Openings"}


def skor(cal: pd.DataFrame, t: pd.Timestamp, ev: str, hari: int, grup: set | None) -> float:
    x = cal[(cal.time < t) & (cal.time >= t - pd.Timedelta(days=hari)) & (cal.event != ev)]
    if grup:
        x = x[x.event.isin(grup)]
    return float(x.g.sum())


def main() -> None:
    cal = calendar()
    cal = cal[cal.event.isin(EVENTS) & cal.a.notna() & cal.f.notna()].sort_values("time").copy()
    s = np.sign(cal.a - cal.f)
    cal["g"] = np.where(cal.event.isin(INVERSE), s, -s)          # +1 = kejutan yang biasanya menaikkan emas
    d = build()
    for lab, hari, grup in (("s7", 7, None), ("s30", 30, None), ("infl30", 30, INFL), ("kerja30", 30, KERJA)):
        d[lab] = [skor(cal, t, ev, hari, grup) for t, ev in zip(d.time, d.event)]
    d["tahun"] = d.time.dt.year
    L = ["# Gabungan kejutan semua berita terbaru → emas 1 jam (research/news_gabung.py)",
         "Lolos = searah & ≥ 58% di LAMA dan BARU, n ≥ 30 masing-masing. Skor + = kejutan pro-emas.", ""]
    lolos, coba = [], 0
    for ev, g in d.groupby("event"):
        for f in ("s7", "s30", "infl30", "kerja30"):
            for thr in (1, 2, 3):
                for arah, m in (("naik", g[f] >= thr), ("turun", g[f] <= -thr)):
                    coba += 1
                    x = g[m]
                    hit = x.up60 if arah == "naik" else 1 - x.up60
                    a, b = hit[x.time < SPLIT], hit[x.time >= SPLIT]
                    if len(a) >= 30 and len(b) >= 30 and a.mean() >= .58 and b.mean() >= .58:
                        th = hit.groupby(x.tahun).mean()
                        lolos.append((ev, f, thr, arah, a.mean(), len(a), b.mean(), len(b),
                                      (th >= .5).mean(), binomtest(int(hit.sum()), len(hit), .5).pvalue))
    L.append(f"Dicoba {coba} aturan; diharapkan lolos karena kebetulan ±{coba * 0.02:.0f}–{coba * 0.05:.0f}.")
    L.append(f"LOLOS: {len(lolos)}")
    for r in lolos:
        L.append(f"   {r[0]} | {r[1]} {'≥' if r[3] == 'naik' else '≤'}{'' if r[3] == 'naik' else '-'}{r[2]} → emas {r[3]} | "
                 f"LAMA {r[4]:.0%} (n {r[5]}) | BARU {r[6]:.0%} (n {r[7]}) | tahun ≥50%: {r[8]:.0%} | p {r[9]:.3f}")
    # model gabungan sederhana: tanda skor 30 hari, semua berita
    L += ["", "## Tanda skor 30 hari (semua berita) → arah emas, per periode & tahun"]
    m = d[d.s30 != 0]
    hit = ((m.s30 > 0) == (m.up60 == 1)).astype(float)
    L.append(f"   semua: {hit.mean():.0%} (n {len(m)}) | LAMA {hit[m.time < SPLIT].mean():.0%} | BARU {hit[m.time >= SPLIT].mean():.0%}")
    L.append("   per tahun: " + " ".join(f"{y}:{v:.0%}" for y, v in hit.groupby(m.tahun).mean().items()))
    # mean reversion NFP
    L += ["", "## NFP: gabungan kejutan vs mean reversion (nfp_mean.csv)"]
    try:
        t = pd.read_csv(cache_path("nfp_mean.csv"), parse_dates=["next_rel"])
        n = d[d.event == "Non-Farm Employment Change"].copy()
        n["day"] = n.time.dt.tz_convert(None).dt.normalize()
        t["day"] = t.next_rel.dt.normalize()
        j = n.merge(t[["day", "lead", "z24", "up"]], on="day", how="inner")
        for lab, mm in (("pendahulu membaik (≥+2)", j.lead >= 2), ("pendahulu memburuk (≤−2)", j.lead <= -2),
                        ("skor kerja30 ≥ +2", j.kerja30 >= 2), ("skor kerja30 ≤ −2", j.kerja30 <= -2)):
            x = j[mm]
            if len(x):
                L.append(f"   {lab}: n {len(x)} | emas naik 1 jam {x.up60.mean():.0%} | NFP berikutnya naik {x.up.mean():.0%}")
        L.append(f"   korelasi skor kerja30 vs skor pendahulu: {j.kerja30.corr(j.lead):+.2f}")
    except Exception as e:  # noqa: BLE001
        L.append(f"   gagal: {e}")
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
