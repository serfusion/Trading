"""⏱️ Putaran 2 ("coba lagi"): petunjuk MIKRO-PASAR detik terakhir sebelum rilis → arah XAU 1–10 detik setelah rilis.

python -m research.pra_xau_mikro          → docs/eksternal/hasil_pra_xau_mikro.txt

Melanjutkan research/pra_xau_semua.py (tabel & target sama, 2.051 rilis 2010–2026). Petunjuk baru, semua ≤ t0−1 dtk,
aturan ditetapkan SEBELUM melihat hasil (+1 = mengarah naik):
  IMB10 IMB30   aliran tick: (tick naik − tick turun) / semua perubahan harga 10 / 30 dtk terakhir; |x| ≥ 0,2 → tanda
  LAST1 LAST3   gerak harga 1 / 3 detik terakhir (t0−2 → t0−1, t0−4 → t0−1)
  POS           posisi harga di rentang 60 menit (candle M15 tutup + tick): di atas 75% → +1, di bawah 25% → −1
  POS_B         kebalikan POS (rentang ditolak / "sapu stop" ke sisi lain)
  BULAT         angka bulat $10 terdekat ≤ $3: arah ke angka itu (magnet)
  SEPI          aktivitas tick 30 dtk terakhir vs 120 dtk sebelumnya < 0,5 (pasar "menahan napas") × tren 4 jam
Uji: arah dipilih di LAMA (< Okt 2021) → dinilai BARU; uji acak permutasi; gabungan dengan petunjuk berita (KEJ) & tren
4 jam (H4) yang sudah dipasang. LOLOS = BARU > 55%, n ≥ 30, p < 0,05, searah Dukascopy, dan > kebetulan.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .news_detik import prepare
from .pra_xau_semua import ARAH_F, bangun, nilai, sg

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "eksternal" / "hasil_pra_xau_mikro.txt"
CACHE = ROOT / "data" / "research" / "eksternal" / "pra_xau_mikro.parquet"
MIKRO = ["IMB10", "IMB30", "LAST1", "LAST3", "POS", "POS_B", "BULAT", "SEPI"]


def _imb(p, i: int, detik: float) -> float:
    m = (p.T > p.T[i] - detik) & (np.arange(len(p.T)) <= i)
    d = np.diff(p.mid[m])
    d = d[d != 0]
    if len(d) < 3:
        return 0.0
    x = (np.sum(d > 0) - np.sum(d < 0)) / len(d)
    return float(np.sign(x)) if abs(x) >= 0.2 else 0.0


def fitur(df: pd.DataFrame) -> pd.DataFrame:
    if CACHE.exists():
        return pd.read_parquet(CACHE)
    from .event_stats import xau_m15
    m15 = xau_m15()
    rows = []
    for t, h4 in zip(df.t0, df.H4.fillna(0)):
        t = pd.Timestamp(t)
        r = {"t0": t}
        for f in ("XAU_EXNESS", "XAU"):
            p = prepare(t, f)
            if p is None:
                continue
            i = p.at(-1)
            if i < 1 or p.T[i] < -60:
                continue
            m0 = float(p.mid[i])
            r["IMB10"], r["IMB30"] = _imb(p, i, 10), _imb(p, i, 30)
            for lag, nm in ((1, "LAST1"), (3, "LAST3")):
                j = p.at(-1 - lag)
                r[nm] = sg(m0 - float(p.mid[j])) if j >= 0 and p.T[j] >= -1 - lag - 3 else 0.0
            n30 = int(((p.T > -31) & (p.T <= -1)).sum())
            n120 = int(((p.T > -121) & (p.T <= -31)).sum())
            r["SEPI"] = float(h4) if n120 >= 8 and n30 / 30 < 0.5 * n120 / 90 else 0.0
            tutup = m15[(m15.index + pd.Timedelta(minutes=15) <= t) & (m15.index >= t - pd.Timedelta(minutes=60))]
            if len(tutup) >= 3:
                pre = p.mid[(p.T >= p.T[0]) & (p.T <= -1)]
                hi = max(float(tutup.high.max()), float(pre.max()))
                lo = min(float(tutup.low.min()), float(pre.min()))
                if hi - lo > 0.5:
                    pos = (m0 - lo) / (hi - lo)
                    r["POS"] = 1.0 if pos > 0.75 else -1.0 if pos < 0.25 else 0.0
            bulat = round(m0 / 10) * 10
            r["BULAT"] = sg(bulat - m0) if abs(bulat - m0) <= 3 else 0.0
            break
        rows.append(r)
    x = pd.DataFrame(rows)
    x["POS_B"] = -x.get("POS", pd.Series(0.0, index=x.index)).fillna(0.0)
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    x.to_parquet(CACHE)
    return x


def gabung() -> pd.DataFrame:
    df = bangun()
    fx = fitur(df)
    return df.merge(fx, on="t0", how="left")


def main() -> None:
    import research.pra_xau_semua as s1
    df = gabung()
    L = ["# ⏱️ Putaran 2 — petunjuk mikro-pasar detik terakhir sebelum rilis → arah XAU 1–10 dtk",
         __doc__.split("\n\n")[1], "", "Terisi: " + ", ".join(f"{f} {int((df[f].fillna(0) != 0).sum())}" for f in MIKRO)]
    asli = list(ARAH_F)
    s1.ARAH_F[:] = MIKRO
    try:
        lolos = s1.uji_tunggal(df, L)
        ac = s1.acak(df, 100)
    finally:
        s1.ARAH_F[:] = asli
    L += ["", "## LOLOS (aturan tunggal mikro)"]
    L += [f"   {g} • {f} ({'lanjut' if a > 0 else 'balik'}) • {h} dtk: BARU Exness {e['baru']:.1f}% (n {e['n_baru']}, p "
          f"{e['p_baru']:.3f}), Duka {d['baru']:.1f}%, semua {e['benar']:.1f}%, tahun > 50%: {e['tahun']}"
          for g, f, h, a, e, d in lolos] or ["   TIDAK ADA"]
    L.append(f"\n## UJI ACAK (permutasi {len(ac)}×): kebetulan rata-rata {np.mean(ac):.1f}, 95% ≤ {np.percentile(ac, 95):.0f}; "
             f"sungguhan {len(lolos)} → peluang kebetulan ≥ {len(lolos)}: {np.mean(np.array(ac) >= len(lolos)) * 100:.0f}%")
    # gabungan dengan yang sudah dipasang: KEJ & H4 searah (+ tiap petunjuk mikro searah/berlawanan)
    t = pd.DatetimeIndex(df.t0.to_numpy())
    K, T4 = df.KEJ.fillna(0).to_numpy(), df.H4.fillna(0).to_numpy()
    dasar = np.where((K != 0) & (K == T4), K, 0.0)
    L.append("\n## Gabungan: petunjuk berita & tren 4 jam SEARAH (dasar 63–67%) × petunjuk mikro")
    for f in MIKRO:
        v = df[f].fillna(0).to_numpy()
        for nama, pred in (("searah", np.where((dasar != 0) & (v == dasar), dasar, 0.0)),
                           ("berlawanan", np.where((dasar != 0) & (v != 0) & (v != dasar), dasar, 0.0))):
            s = [nilai(pred, df[f"y{h}_XAU_EXNESS"].to_numpy(), t) for h in (1, 3, 10)]
            L.append(f"   {f:6s} {nama:10s} " + " | ".join(
                f"{h} dtk {x['benar']:.0f}% (n {x['n']}, LAMA {x['lama']:.0f} BARU {x['baru']:.0f})" for h, x in
                zip((1, 3, 10), s)))
    # tanpa petunjuk berita: tren 4 jam × mikro
    tanpa = np.where(K == 0, T4, 0.0)
    L.append("\n## Berita TANPA petunjuk: tren 4 jam (dasar 55–56%) × petunjuk mikro searah")
    for f in MIKRO:
        v = df[f].fillna(0).to_numpy()
        pred = np.where((tanpa != 0) & (v == tanpa), tanpa, 0.0)
        s = [nilai(pred, df[f"y{h}_XAU_EXNESS"].to_numpy(), t) for h in (1, 3, 10)]
        L.append(f"   {f:6s} " + " | ".join(
            f"{h} dtk {x['benar']:.0f}% (n {x['n']}, LAMA {x['lama']:.0f} BARU {x['baru']:.0f}, p {x['p_baru']:.3f})"
            for h, x in zip((1, 3, 10), s)))
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
