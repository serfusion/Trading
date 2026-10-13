"""🎯 BTC & ETH: cari subset sinyal 💰 dengan WR (TP1 kena) lebih tinggi — pilih di LAMA, uji di BARU (antrian pengguna 13 Okt
"riset eth, btc, dll hingga wr tinggi"). python -m research.kripto_wr → docs/eksternal/hasil_kripto_wr.txt

Data: replay kode cloud asli (data/research/eksternal/verifikasi/cloud_{BTC,ETH}.csv, research/verifikasi_cloud.py).
Fitur (ditetapkan sebelum melihat hasil): arah, kategori, tier, set, lapisan, sesi jam UTC (Asia 0–7, Eropa 8–12, AS 13–20,
malam 21–23), akhir pekan, dan semua PASANGAN dua fitur. Seleksi di LAMA (< Okt 2021): WR ≥ WR dasar LAMA + 5 poin & n ≥ 30.
Uji di BARU: tetap ≥ dasar BARU + 5 poin DAN R/sinyal ≥ dasar BARU, n ≥ 20. Pembanding kebetulan: label TP1 BARU diacak
200× → berapa subset terpilih yang "bertahan" karena kebetulan.
"""
from __future__ import annotations

from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "eksternal" / "hasil_kripto_wr.txt"
SPLIT = pd.Timestamp("2021-10-01", tz="UTC")
FITUR = ["dir", "cat", "tier", "set", "lapis", "sesi", "akhir_pekan"]


def siap(a: str) -> pd.DataFrame:
    x = pd.read_csv(ROOT / "data" / "research" / "eksternal" / "verifikasi" / f"cloud_{a}.csv")
    x["t"] = pd.to_datetime(x.t_signal, utc=True)
    h = x.t.dt.hour
    x["sesi"] = np.select([h < 8, h < 13, h < 21], ["Asia", "Eropa", "AS"], "malam")
    x["akhir_pekan"] = x.t.dt.weekday >= 5
    x["menang"] = x.tp1.astype(bool)
    x["baru"] = x.t >= SPLIT
    return x


def subsets(x: pd.DataFrame):
    for f in FITUR:
        for v in x[f].dropna().unique():
            yield (f"{f}={v}",), x[f] == v
    for f1, f2 in combinations(FITUR, 2):
        for (v1, v2), _ in x.groupby([f1, f2]):
            yield (f"{f1}={v1}", f"{f2}={v2}"), (x[f1] == v1) & (x[f2] == v2)


def main() -> None:
    L = ["# 🎯 BTC & ETH: subset WR tinggi (research/kripto_wr.py)", __doc__.split("\n\n")[1], ""]
    rng = np.random.default_rng(29)
    for a in ("BTC", "ETH"):
        x = siap(a)
        lm, br = x[~x.baru], x[x.baru]
        wl, wb, rb = lm.menang.mean() * 100, br.menang.mean() * 100, br.r.mean()
        L.append(f"## {a}: {len(x)} sinyal • dasar WR LAMA {wl:.0f}% ({len(lm)}) • BARU {wb:.0f}% ({len(br)}), R/sinyal BARU {rb:+.2f}")
        pilih = []
        for nama, m in subsets(x):
            ml, mb = m & ~x.baru, m & x.baru
            if ml.sum() >= 30 and x.menang[ml].mean() * 100 >= wl + 5:
                pilih.append((nama, m))
        tahan = []
        for nama, m in pilih:
            mb = m & x.baru
            if mb.sum() >= 20:
                w, r = x.menang[mb].mean() * 100, x.r[mb].mean()
                ok = bool(w >= wb + 5 and r >= rb)
                tahan.append((ok, w, r, int(mb.sum()), x.menang[m & ~x.baru].mean() * 100, nama))
        n_ok = sum(t[0] for t in tahan)
        acak = []
        for _ in range(200):
            perm = br.menang.sample(frac=1, random_state=int(rng.integers(1e9))).to_numpy()
            mp = pd.Series(perm, index=br.index)
            k = 0
            for nama, m in pilih:
                mb = m & x.baru
                if mb.sum() >= 20 and mp[mb[mb].index].mean() * 100 >= wb + 5 and x.r[mb].mean() >= rb:
                    k += 1
            acak.append(k)
        L.append(f"   terpilih di LAMA: {len(pilih)} subset • diuji di BARU (n ≥ 20): {len(tahan)} • BERTAHAN: {n_ok} "
                 f"(label diacak: rata-rata {np.mean(acak):.1f}, ≥ {n_ok} pada {np.mean(np.array(acak) >= n_ok) * 100:.0f}%)")
        for ok, w, r, n, w_l, nama in sorted(tahan, key=lambda t: (-t[0], -t[1]))[:12]:
            L.append(f"   {'✅' if ok else '  '} {' & '.join(nama):45s} LAMA WR {w_l:3.0f}% → BARU WR {w:3.0f}% (n {n}) R/sinyal {r:+.2f}")
        L.append("")
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
