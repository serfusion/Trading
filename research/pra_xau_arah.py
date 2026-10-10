"""⏱️ KHUSUS XAU: arah emas 1–10 detik setelah rilis vs tebakan SEBELUM rilis — tanpa untung/rugi.

python -m research.pra_xau_arah          → docs/eksternal/hasil_pra_xau_arah.txt + cloud/api/pra_aset.json["xau_arah"]

Permintaan pengguna 10 Okt 2026: "jangan terpaut untung/rugi; yang saya mau hasil 1–10 detik ke depan naik atau turun;
seperti kamu dapat data XAU naik lalu cek setelah news 1–10 detik sesuai naik atau tidak" lalu "hanya XAU saja".
Cara (ditetapkan sebelum melihat hasil):
  • Harga tengah (bid+ask)/2 pada t0−1 dtk dibanding t0+1/2/3/5/10 dtk, tick Exness (broker pengguna) & Dukascopy.
  • Benar = harga bergerak searah tebakan. Dua hitungan: SEMUA gerak (berapa pun) dan gerak ≥ $0,30 (lebih besar dari
    spread; gerak lebih kecil = "belum gerak", tidak dihitung).
  • Tebakan per waktu rilis dari petunjuk teruji (research/berita_gabung.py + sumber_lain.py), beberapa varian:
    CPI: Kalshi; Kalshi & kejutan lalu sepakat; Kalshi/kejutan lalu (cadangan); + minyak WTI sepakat; WTI saja.
    ISM Jasa: berbalik dari kejutan lalu; + aktivitas Fed daerah sepakat. GDP: GDPNow. Pengangguran (hari NFP):
    Kalshi/kejutan lalu; + Indeed sepakat. Core PPI: berbalik. JOLTS: berbalik.
  • Arah emas dari tebakan angka memakai reaksi historis per judul (cloud/api/reaksi.json).
  • Konsisten = > 50% di LAMA (< Okt 2021) & BARU dan p binomial < 0,05 di semua data.
"""
from __future__ import annotations

import json
from math import comb
from pathlib import Path

import numpy as np
import pandas as pd

from .news_detik import NEW, prepare

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "eksternal" / "hasil_pra_xau_arah.txt"
JSON = ROOT / "cloud" / "api" / "pra_aset.json"
H = [1, 2, 3, 5, 10]
MIN_GERAK = 0.30
FEEDS = ("XAU_EXNESS", "XAU")


def binom_p(k: int, n: int) -> float:
    return float(sum(comb(n, i) for i in range(k, n + 1)) / 2 ** n) if n else 1.0


def varian() -> dict[str, tuple[str, pd.Series]]:
    """nama → (grup berita, Series waktu rilis → +1 emas naik / −1 turun)."""
    from .berita_gabung import emas, tabel
    from .sumber_lain import fitur
    df = emas(tabel())
    df["-P"] = -df.P
    df["K|P"] = np.where(df.K.fillna(0) != 0, df.K, df.P)
    df["K&P"] = np.where((df.K.fillna(0) != 0) & (df.K == df.P), df.K, 0.0)
    judul = ["CPI m/m", "Core CPI m/m", "CPI y/y", "ISM Services PMI", "Unemployment Rate"]
    fx = fitur(df[df.event.isin(judul)].copy())
    df = df.merge(fx[["t0", "event", "WTI", "GA", "IND"]], on=["t0", "event"], how="left")
    df["K|P&WTI"] = np.where((df["K|P"].fillna(0) != 0) & (df["K|P"] == df.WTI), df["K|P"], 0.0)
    df["-P&GA"] = np.where((df["-P"].fillna(0) != 0) & (df["-P"] == df.GA), df["-P"], 0.0)
    df["K|P&IND"] = np.where((df["K|P"].fillna(0) != 0) & (df["K|P"] == df.IND), df["K|P"], 0.0)

    def g(col: str, judul_: list[str]) -> pd.Series:
        x = df[df.event.isin(judul_) & df[col].notna() & (df[col] != 0) & df.arah_bawah.notna()]
        v = np.where(x[col] < 0, x.arah_bawah, x.arah_atas)
        s = pd.Series(v, index=x.t0).groupby(level=0).sum()
        return np.sign(s[s != 0])
    cpi = ["CPI m/m", "Core CPI m/m"]
    return {
        "CPI • Kalshi": ("CPI", g("K", cpi)),
        "CPI • Kalshi & kejutan lalu sepakat": ("CPI", g("K&P", cpi)),
        "CPI • Kalshi, cadangan kejutan lalu": ("CPI", g("K|P", cpi)),
        "CPI • + minyak WTI sepakat": ("CPI", g("K|P&WTI", ["CPI m/m"])),
        "CPI • minyak WTI saja": ("CPI", g("WTI", ["CPI m/m", "CPI y/y"])),
        "ISM Jasa • berbalik": ("ISM", g("-P", ["ISM Services PMI"])),
        "ISM Jasa • + aktivitas Fed daerah sepakat": ("ISM", g("-P&GA", ["ISM Services PMI"])),
        "GDP • GDPNow": ("GDP", g("G", ["Advance GDP q/q"])),
        "NFP • pengangguran Kalshi/kejutan lalu": ("NFP", g("K|P", ["Unemployment Rate"])),
        "NFP • + Indeed sepakat": ("NFP", g("K|P&IND", ["Unemployment Rate"])),
        "Core PPI • berbalik": ("PPI", g("-P", ["Core PPI m/m"])),
        "JOLTS • berbalik": ("JOLTS", g("-P", ["JOLTS Job Openings"])),
    }


def gerak(times) -> dict:
    """feed → waktu → {h: perubahan mid t0−1 → t0+h}."""
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


def nilai(arah: pd.Series, gk: dict, h: int, minimal: float) -> dict:
    rows = [(t, np.sign(gk[t][h]) * d) for t, d in arah.items() if t in gk and h in gk[t] and abs(gk[t][h]) >= max(
        minimal, 1e-9)]
    if not rows:
        return {"n": 0}
    t = pd.DatetimeIndex([r[0] for r in rows])
    v = np.array([r[1] > 0 for r in rows])
    lama, baru = v[t < NEW], v[t >= NEW]
    k, n = int(v.sum()), len(v)
    return {"n": n, "benar": round(k / n * 100, 1), "p": round(binom_p(k, n), 4),
            "lama": round(float(lama.mean() * 100), 1) if len(lama) else None, "n_lama": int(len(lama)),
            "baru": round(float(baru.mean() * 100), 1) if len(baru) else None, "n_baru": int(len(baru)),
            "tebakan": int(len(arah))}


def main() -> None:
    V = varian()
    times = sorted({t for _, s in V.values() for t in s.index})
    gk = gerak(times)
    L = ["# ⏱️ XAU: arah 1–10 detik setelah rilis vs tebakan sebelum rilis (tanpa untung/rugi)", __doc__.split("\n\n")[1],
         ""]
    hasil = {}
    for nama, (grp, s) in V.items():
        L += ["", f"## {nama} ({len(s)} rilis bertebakan)"]
        hasil[nama] = {"grup": grp, "h": {}}
        for minimal, lab in ((0.0, "semua gerak"), (MIN_GERAK, f"gerak ≥ ${MIN_GERAK:.2f}")):
            for h in H:
                r = {f: nilai(s, gk[f], h, minimal) for f in FEEDS}
                e, d = r["XAU_EXNESS"], r["XAU"]
                ok = (e.get("n", 0) >= 20 and (e.get("lama") or 0) > 50 and (e.get("baru") or 0) > 50
                      and e.get("p", 1) < 0.05 and (d.get("benar") or 0) > 50)
                hasil[nama]["h"][f"{h}|{minimal:g}"] = {"exness": e, "dukascopy": d, "konsisten": ok}
                L.append(f"   {'✅' if ok else '  '} {lab:13s} {h:2d} dtk: Exness benar {e.get('benar')}% (n {e.get('n')}, "
                         f"p {e.get('p')}; LAMA {e.get('lama')}% n {e.get('n_lama')}, BARU {e.get('baru')}% "
                         f"n {e.get('n_baru')}) | Dukascopy {d.get('benar')}% (n {d.get('n')})")
    d = json.loads(JSON.read_text(encoding="utf-8")) if JSON.exists() else {}
    d["xau_arah"] = hasil
    JSON.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
