"""⏱️ Entry 1 DETIK SEBELUM rilis memakai petunjuk teruji baru (Kalshi, kejutan bulan lalu, berbalik, GDPNow).

python -m research.pra_gabung            → docs/eksternal/hasil_pra_gabung.txt

Permintaan pengguna 10 Okt 2026: "saya entry 1 detik sebelum news (gap / naik-turun sangat tinggi) — telusuri, riset
dan uji validitas dulu". Lanjutan research/news_pra2.py (mesin eksekusi tick yang sama, aturan ditetapkan sebelum hasil):
  • Arah per waktu rilis = arah EMAS dari tebakan kejutan (research/berita_gabung.py, aturan yang lolos di sana) menurut
    reaksi historis per judul (cloud/api/reaksi.json); beberapa berita di detik yang sama → jumlah suara (0 = lewati).
  • Entry t0−1 dtk: BUY di ASK / SELL di BID (tick Dukascopy 2010–2026 & tick asli Exness Cent 2015–2026).
    CEPAT = terisi di kutipan t0−1 tanpa slippage; REALISTIS = terisi 0,5 dtk kemudian + slippage $0,30 masuk & keluar;
    STRES = 0,5 dtk + $1,00. Keluar: tutup 1/2/3/5/10/20/30/45/60/90/120/180 dtk, atau kunci untung ≥ $x.
  • Lolos (news_detik.judge): n ≥ 30, LAMA & BARU > 0, ≥ 60% tahun positif, t > 2 pada CEPAT, REALISTIS > 0, di KEDUA
    feed. Hasil $ per ons = $ per 0,01 lot (akun Cent: sen).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from . import news_pra2 as p2
from .news_detik import fmt, judge, prepare, stats

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "eksternal" / "hasil_pra_gabung.txt"
# judul → kolom aturan terbaik di berita_gabung (lolos arah angka)
ATURAN = {"CPI m/m": "K|P", "Core CPI m/m": "K|P", "CPI y/y": "P", "Unemployment Rate": "K|P", "Core PPI m/m": "-P",
          "ISM Services PMI": "-P", "JOLTS Job Openings": "-P", "Advance GDP q/q": "G"}
TAMPIL = ["tutup 1s", "tutup 2s", "tutup 3s", "tutup 10s", "tutup 30s", "tutup 60s", "tutup 180s", "untung>=$1 maks 60s",
          "untung>=$2 maks 180s"]


def arah_rilis() -> dict[str, pd.Series]:
    """Varian → Series (waktu rilis → +1 BUY / −1 SELL)."""
    from .berita_gabung import emas, tabel
    df = emas(tabel())
    df["-P"] = -df.P
    df["K|P"] = np.where(df.K.fillna(0) != 0, df.K, df.P)
    df["K&P"] = np.where((df.K.fillna(0) != 0) & (df.K == df.P), df.K, 0.0)

    def g(col: str, judul: list[str]) -> pd.Series:
        x = df[df.event.isin(judul) & df[col].notna() & (df[col] != 0) & df.arah_bawah.notna()]
        v = np.where(x[col] < 0, x.arah_bawah, x.arah_atas)
        s = pd.Series(v, index=x.t0).groupby(level=0).sum()
        return np.sign(s[s != 0])
    cpi = ["CPI m/m", "Core CPI m/m"]
    out = {"CPI: Kalshi": g("K", cpi), "CPI: Kalshi & kejutan lalu sepakat": g("K&P", cpi),
           "CPI: Kalshi, cadangan kejutan lalu": g("K|P", cpi), "CPI: kejutan lalu": g("P", cpi + ["CPI y/y"]),
           "NFP-hari: pengangguran Kalshi/kejutan lalu": g("K|P", ["Unemployment Rate"]),
           "ISM Jasa: berbalik": g("-P", ["ISM Services PMI"]), "Core PPI: berbalik": g("-P", ["Core PPI m/m"]),
           "JOLTS: berbalik": g("-P", ["JOLTS Job Openings"]), "GDP: GDPNow": g("G", ["Advance GDP q/q"])}
    semua = []
    for judul, col in ATURAN.items():
        semua.append(g(col, [judul]))
    s = pd.concat(semua).groupby(level=0).sum()
    out["SEMUA aturan teruji (suara)"] = np.sign(s[s != 0])
    return out


def main() -> None:
    dirs = arah_rilis()
    times = sorted({t for s in dirs.values() for t in s.index})
    L = ["# ⏱️ Entry 1 detik sebelum rilis + petunjuk teruji baru (tick Dukascopy & Exness)", __doc__.split("\n\n")[1],
         ""]
    tab = {}
    for feed in ("XAU", "XAU_EXNESS"):
        tab[feed] = {}
        for t in times:
            p = prepare(pd.Timestamp(t), feed)
            if p is None:
                continue
            d = p2.directional(p)
            if d is not None:
                tab[feed][t] = d
        L.append(f"{p2.FEEDS[feed]}: tick tersedia untuk {len(tab[feed])} dari {len(times)} waktu rilis")
    sk = list(p2.SCEN)
    lolos = []
    for nama, s in dirs.items():
        L += ["", f"## {nama} (tebakan arah di {len(s)} rilis)"]
        for ex in TAMPIL:
            e = p2.EXITS.index(ex)
            baris = []
            res = {}
            for feed in ("XAU", "XAU_EXNESS"):
                for si, sc in enumerate(sk):
                    rec = [{"time": t, "pnl": tab[feed][t][si, 0 if d > 0 else 1, e]} for t, d in s.items()
                           if t in tab[feed]]
                    res[(feed, sc)] = stats(pd.DataFrame(rec)) if rec else {"n": 0}
            for feed in ("XAU", "XAU_EXNESS"):
                c, r, st = res[(feed, "CEPAT")], res[(feed, "REALISTIS")], res[(feed, "STRES")]
                baris.append(fmt(f"{p2.FEEDS[feed]:9s} {ex} CEPAT", c))
                if r.get("n"):
                    baris.append(f"{'':44}   REALISTIS rata {r['avg']:+.2f} WR {r['wr']:.0f}% | STRES rata {st['avg']:+.2f}")
            ok = all(judge(res[(f, "CEPAT")], res[(f, "REALISTIS")]) for f in ("XAU", "XAU_EXNESS"))
            if ok:
                lolos.append(f"{nama} • {ex}")
            L += [("✅ " if ok else "   ") + b for b in baris]
    L += ["", "## Lolos di kedua feed", *(lolos or ["TIDAK ADA"])]
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
