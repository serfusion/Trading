"""🔎 Cari ATURAN SEBELUM RILIS yang (hampir) selalu benar — 14 Okt 2026, permintaan pengguna "cari aturan sebelum rilis dan
pasang" (setelah "UJI TUTUP KERTAS bukan setelah rilisnya").

python -m research.aturan_pra            → docs/eksternal/hasil_aturan_pra.txt (+ cloud/api/aturan_pra.json bila ada yang lolos)

Data: data/research/eksternal/pra_xau_semua_v2.parquet (research/pra_xau_semua.py: 2.051 rilis USD 2010–2026, semua fitur
≤ t0−1 dtk). Target = arah harga tengah XAU t0−1 dtk → t0+2 dtk (detik 2 = patokan aplikasi; tick Exness, cadangan Dukascopy),
gerak 0 tidak dihitung.

Aturan penilaian (ditetapkan SEBELUM melihat hasil):
- Fitur hanya yang bisa dihitung cloud LIVE sebelum rilis: KEJ (petunjuk teruji per berita), EXP (perkiraan vs angka lalu),
  PS (kejutan rilis lalu), M15/M60/H4/H24 (gerak emas), TREN/TRD (EMA 50/200 H1), GRUP (arah mayoritas jenis berita),
  LALU (arah detik 10 rilis lalu jenis sama), BTC60 (BTC 60 dtk). Fitur tick (D10/D30/TIK/BTC10) TIDAK (cloud tak punya tick).
- Aturan = gabungan 1–3 syarat (fitur = +1/−1), lingkup satu jenis berita atau semua; arah tebakan = mayoritas di data latih.
- TUTUP KERTAS per tahun Y (2014–2026): aturan dipilih hanya dari tahun < Y bila n latih ≥ 25, tepat ≥ 65%, p binomial ≤ 0,005,
  dan ≥ 60% di kedua paruh tahun latih. Rilis tahun Y yang terkena aturan → tebakan dari aturan dengan batas bawah Wilson
  tertinggi. Yang dilaporkan = hasil tahun Y (belum pernah dilihat saat memilih).
- Pembanding: selalu-NAIK pada rilis yang sama; acak = prosedur sama dengan arah emas diacak dalam tiap tahun (30×).
- LOLOS untuk dipasang: tutup kertas ≥ 65% dengan n ≥ 40, LAMA (< Okt 2021) & BARU masing-masing ≥ 60%, > selalu-NAIK
  ≥ 10 poin, dan > persentil 95 acak.
"""
from __future__ import annotations

import itertools
import json
from math import sqrt
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "research" / "eksternal" / "pra_xau_semua_v2.parquet"
OUT = ROOT / "docs" / "eksternal" / "hasil_aturan_pra.txt"
JSON = ROOT / "cloud" / "api" / "aturan_pra.json"
LIVE = ["KEJ", "EXP", "PS", "M15", "M60", "H4", "H24", "TREN", "TRD", "GRUP", "LALU", "BTC60"]
TICK = ["D10", "D30", "D120", "TIK", "BTC10"]
BARU = pd.Timestamp("2021-10-01", tz="UTC")
L: list[str] = []


def say(s: str = "") -> None:
    print(s)
    L.append(s)


def p_binom(k: int, n: int) -> float:
    from scipy.stats import binom
    return float(binom.sf(k - 1, n, 0.5)) if n else 1.0


def wilson_lb(k: int, n: int, z: float = 1.96) -> float:
    if n == 0:
        return 0.0
    p = k / n
    return (p + z * z / (2 * n) - z * sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / (1 + z * z / n)


def muat(h: int = 2) -> pd.DataFrame:
    d = pd.read_parquet(DATA)
    y = d[f"y{h}_XAU_EXNESS"].where(d[f"y{h}_XAU_EXNESS"].notna(), d[f"y{h}_XAU"])
    d["y"] = np.sign(y)
    d = d[d.y.notna() & (d.y != 0)].reset_index(drop=True)
    d["th"] = d.t0.dt.year
    return d


def kondisi(d: pd.DataFrame, fitur: list[str]) -> tuple[list[str], np.ndarray]:
    nama, kol = [], []
    for f in fitur:
        if f not in d:
            continue
        v = d[f].fillna(0).to_numpy()
        for s in (1, -1):
            nama.append(f"{f}{'+' if s > 0 else '−'}")
            kol.append(v == s)
    return nama, np.array(kol)


def cari(d: pd.DataFrame, fitur: list[str], acak: np.random.Generator | None = None, maks_syarat: int = 3) -> pd.DataFrame:
    """Tutup kertas per tahun → DataFrame tebakan (indeks rilis, tebak, aturan)."""
    y = d.y.to_numpy().copy()
    th = d.th.to_numpy()
    if acak is not None:                               # arah diacak di dalam tiap tahun (struktur waktu dijaga)
        for t in np.unique(th):
            m = th == t
            y[m] = acak.permutation(y[m])
    tahun = np.arange(th.min(), th.max() + 1)
    ti = th - th.min()
    nama, C = kondisi(d, fitur)
    fi = [n[:-1] for n in nama]
    lingkup = [("SEMUA", np.ones(len(d), bool))] + [(g, (d.grup == g).to_numpy()) for g in d.grup.unique()]
    naik = y > 0
    calon = []                                          # (nama aturan, mask, naik per tahun, total per tahun)
    for g, mg in lingkup:
        if mg.sum() < 25:
            continue
        for k in range(1, maks_syarat + 1):
            for idx in itertools.combinations(range(len(nama)), k):
                if len({fi[i] for i in idx}) < k:
                    continue
                m = mg.copy()
                for i in idx:
                    m &= C[i]
                if m.sum() < 25:
                    continue
                tot = np.bincount(ti[m], minlength=len(tahun))
                up = np.bincount(ti[m & naik], minlength=len(tahun))
                calon.append((f"{g}: " + " & ".join(nama[i] for i in idx), m, up, tot))
    hasil = []
    for j, Y in enumerate(tahun):
        if Y < 2014:
            continue
        lalu = slice(0, j)
        tahun_lalu = tahun[:j]
        tengah = int(np.median(tahun_lalu)) if len(tahun_lalu) else Y
        terpilih = []
        for nm, m, up, tot in calon:
            n = tot[lalu].sum()
            if n < 25:
                continue
            u = up[lalu].sum()
            arah = 1 if u * 2 >= n else -1
            k = u if arah > 0 else n - u
            if k / n < 0.65 or p_binom(k, n) > 0.005:
                continue
            a = tahun_lalu <= tengah
            n1, n2 = tot[:j][a].sum(), tot[:j][~a].sum()
            u1, u2 = up[:j][a].sum(), up[:j][~a].sum()
            k1 = u1 if arah > 0 else n1 - u1
            k2 = u2 if arah > 0 else n2 - u2
            if n1 < 8 or n2 < 8 or k1 / n1 < 0.60 or k2 / n2 < 0.60:
                continue
            terpilih.append((wilson_lb(k, n), arah, nm, m))
        if not terpilih:
            continue
        terpilih.sort(key=lambda x: -x[0])
        kini = np.flatnonzero(th == Y)
        for i in kini:
            for lb, arah, nm, m in terpilih:
                if m[i]:
                    hasil.append({"i": i, "tebak": arah, "y": y[i], "aturan": nm, "lb": lb, "th": Y})
                    break
    return pd.DataFrame(hasil)


def ringkas(d: pd.DataFrame, h: pd.DataFrame, judul: str) -> dict:
    if h.empty:
        say(f"  {judul}: tidak ada aturan yang lolos syarat pemilihan di tahun mana pun")
        return {"n": 0}
    h = h.copy()
    h["benar"] = h.tebak == h.y
    lama = (d.t0.iloc[h.i] < BARU).to_numpy()
    base = (h.y > 0).mean()
    r = {"n": len(h), "benar": float(h.benar.mean()), "dasar": float(base),
         "lama": float(h.benar[lama].mean()) if lama.any() else None, "n_lama": int(lama.sum()),
         "baru": float(h.benar[~lama].mean()) if (~lama).any() else None, "n_baru": int((~lama).sum()),
         "naik": float(h.benar[h.tebak > 0].mean()) if (h.tebak > 0).any() else None, "n_naik": int((h.tebak > 0).sum()),
         "turun": float(h.benar[h.tebak < 0].mean()) if (h.tebak < 0).any() else None, "n_turun": int((h.tebak < 0).sum())}
    f = lambda x: "–" if x is None else f"{100 * x:.0f}%"          # noqa: E731
    say(f"  {judul}: tutup kertas {f(r['benar'])} (n {r['n']} dari {len(d)} rilis) | selalu-NAIK {f(base)} | "
        f"LAMA {f(r['lama'])} (n {r['n_lama']}) / BARU {f(r['baru'])} (n {r['n_baru']}) | tebak NAIK {f(r['naik'])} "
        f"(n {r['n_naik']}) / TURUN {f(r['turun'])} (n {r['n_turun']})")
    per = h.groupby("th").benar.agg(["mean", "size"])
    say("     per tahun: " + " • ".join(f"{t} {100 * m:.0f}% ({n})" for t, (m, n) in per.iterrows()))
    return r


def main() -> None:
    L.clear()
    d = muat()
    say("🔎 ATURAN SEBELUM RILIS (gabungan 1–3 syarat) — TUTUP KERTAS per tahun, target arah XAU detik 2")
    say(f"   {len(d)} rilis {d.t0.min():%Y}–{d.t0.max():%b %Y}; naik detik 2 {100 * (d.y > 0).mean():.0f}% (dasar)")
    say("=" * 110)
    say("A. Fitur LIVE (bisa dihitung cloud):")
    h = cari(d, LIVE)
    rA = ringkas(d, h, "semua aturan terpilih")
    if not h.empty:
        top = h.aturan.value_counts().head(12)
        say("     aturan paling sering terpakai: " + " | ".join(f"{k} ×{v}" for k, v in top.items()))
        for nm, g in h.groupby("aturan"):
            if len(g) >= 8:
                say(f"       {nm}: {100 * (g.tebak == g.y).mean():.0f}% (n {len(g)})")
    for hh in (1, 5, 10):
        ringkas(muat(hh), cari(muat(hh), LIVE), f"target detik {hh}")
    say("B. Pembanding: fitur LIVE + tick (D10/D30/D120/TIK/BTC10 — tidak bisa dipasang, hanya untuk melihat batas atas):")
    ringkas(d, cari(d, LIVE + TICK, maks_syarat=2), "dengan fitur tick (2 syarat)")
    say("C. ACAK (arah emas diacak dalam tiap tahun, prosedur sama, 30×):")
    rng = np.random.default_rng(14)
    acak = []
    for _ in range(30):
        ha = cari(d, LIVE, acak=rng)
        acak.append(float((ha.tebak == ha.y).mean()) if len(ha) else np.nan)
    a = np.array([x for x in acak if x == x])
    p95 = float(np.percentile(a, 95)) if len(a) else np.nan
    say(f"  acak: rata-rata {100 * np.mean(a):.1f}%, P95 {100 * p95:.1f}% ({len(a)} dari 30 putaran memilih aturan)")
    lolos = (rA.get("n", 0) >= 40 and rA["benar"] >= 0.65 and (rA["lama"] or 0) >= 0.60 and (rA["baru"] or 0) >= 0.60
             and rA["benar"] - rA["dasar"] >= 0.10 and rA["benar"] > p95)
    say("=" * 110)
    say(f"PUTUSAN: {'LOLOS → dipasang' if lolos else 'TIDAK LOLOS → tidak dipasang'} (syarat: ≥ 65%, n ≥ 40, LAMA & BARU ≥ 60%, "
        f"> selalu-NAIK +10 poin, > P95 acak)")
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    # selalu ditulis: poin 🧾 berita tanpa tebakan memakai angka ini (cloud/api/_pra_aset.satu); "lolos" menentukan pemasangan
    JSON.write_text(json.dumps({"dibuat": f"{pd.Timestamp.now('UTC'):%Y-%m-%d}", "lolos": bool(lolos), "hasil": rA,
                                "acak_rata": float(np.mean(a)), "acak_p95": p95, "n_rilis": len(d),
                                "docs": "docs/eksternal/hasil_aturan_pra.txt"}, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
