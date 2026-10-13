"""🔎 Verifikasi adversarial kandidat research/riset_dalam.py (13 Okt 2026) — tujuan: MEMBANTAH klaim.

python -m research.riset_dalam_cek      → docs/eksternal/hasil_riset_dalam_cek.txt

Kandidat yang lolos kriteria per kelompok: GDP_LAIN P (GDP prelim/final ← kejutan rilis GDP sebelumnya) dan UOM_FIN U_REVSPX
(UoM final ← S&P 500 sejak prelim). Pemeriksaan (ditetapkan sebelum dijalankan):
 1. HITUNG ULANG INDEPENDEN: petunjuk dibangun lagi langsung dari arsip FF mentah (bukan tabel fitur riset), walk-forward
    sendiri (tahun Y dipakai bila tahun-tahun sebelumnya > 50%, n ≥ 10), target lonjakan dari riset_dalam/lonjakan.parquet.
 2. LOOK-AHEAD: 15 rilis contoh dicetak dengan waktu semua masukan (rilis GDP sebelumnya; close S&P 500 terakhir yang dipakai).
 3. PERMUTASI GLOBAL: SEMUA 66 aturan dari 10 kelompok; hasil emas diacak di dalam tiap kelompok 2.000×; p = peluang aturan
    TERBAIK dari seluruh 66 ≥ angka kandidat (koreksi banyak-uji yang jujur; kriteria per kelompok terlalu longgar).
 4. KETAHANAN: rilis ganjil/genap, sendiri saja, prelim vs final (GDP), ambang S&P ±0,5/1,5%, target detik 2/5/10/60 & arah
    tutup menit 1, per tahun.
 5. JALUR KEJUTAN: apakah petunjuk menebak ANGKA (kejutan) — bila emas benar > PLAFON, keunggulan bukan dari berita.
 6. PLASEBO U_REVSPX: aturan yang sama pada jam 10:00 ET hari Jumat LAIN (tanpa UoM) → bila sama baiknya, ini efek pasar
    umum, bukan petunjuk berita.
Bantah (refuted) bila: angka tidak terulang, p global ≥ 0,05, rapuh di ketahanan, atau plasebo sama baiknya.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .riset_dalam_data import DIR, ff_mentah, ticks

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "eksternal" / "hasil_riset_dalam_cek.txt"
SPLIT = pd.Timestamp("2021-10-01", tz="UTC")


def wf(clue: np.ndarray, y: np.ndarray, th: np.ndarray) -> np.ndarray:
    """Walk-forward per tahun (ditulis ulang): tebakan emas = −clue bila tahun-tahun lalu benar > 50% (n ≥ 10)."""
    g, out = -clue, np.zeros(len(clue))
    for Y in sorted(set(th)):
        m = (th < Y) & (g != 0) & (y != 0)
        if m.sum() >= 10 and (g[m] == y[m]).mean() > 0.5:
            out[th == Y] = g[th == Y]
    return out


def rate(tb, y, m) -> str:
    ok = m & (tb != 0) & (y != 0)
    return f"{(tb[ok] == y[ok]).mean() * 100:.0f}% ({int((tb[ok] == y[ok]).sum())}/{int(ok.sum())})" if ok.any() else "–"


def periode(tb, y, t0, th) -> str:
    return " | ".join(f"{k} {rate(tb, y, m)}" for k, m in (("2016+", th >= 2016), ("LAMA", (th >= 2016) & (t0 < SPLIT)),
                                                             ("BARU", t0 >= SPLIT)))


def gdp_independen(L: list) -> pd.DataFrame:
    from .riset_dalam_data import _num
    ff = ff_mentah()
    g = ff[ff.event.isin(["Advance GDP q/q", "Prelim GDP q/q", "Final GDP q/q"])].copy()
    g["a"], g["f"] = g.actual.map(_num), g.forecast.map(_num)
    g = g.dropna(subset=["a", "f"]).sort_values("t0").drop_duplicates("t0").reset_index(drop=True)
    g["s"] = np.sign(g.a - g.f)
    g["P"] = g.s.shift(1)
    g["P_t0"] = g.t0.shift(1)
    lj = pd.read_parquet(DIR / "lonjakan.parquet")[["t0", "arah", "d2", "d5", "d10", "d60", "sendiri"]].drop_duplicates("t0")
    g = g.merge(lj, on="t0", how="left")
    x = g[(g.event != "Advance GDP q/q") & g.arah.notna()].reset_index(drop=True)
    L.append(f"\n## 1. GDP prelim/final ← kejutan GDP sebelumnya (hitung ulang dari FF mentah; {len(x)} rilis s/d "
             f"{x.t0.max():%Y-%m}; catatan: FF mentah berhenti Jan 2026 → 2026 dari Nasdaq tidak ikut di sini)")
    y, th, t0 = x.arah.to_numpy(), x.t0.dt.year.to_numpy(), x.t0
    tb = wf(x.P.fillna(0).to_numpy(), y, th)
    L.append("   lonjakan            " + periode(tb, y, t0, th))
    kk = (x.P != 0) & (x.s != 0)
    L.append(f"   angka: P menebak kejutan rilis ini {(x.P[kk] == x.s[kk]).mean() * 100:.0f}% (n {int(kk.sum())}; "
             f"LAMA {(x.P[kk & (x.t0 < SPLIT)] == x.s[kk & (x.t0 < SPLIT)]).mean() * 100:.0f}%, BARU "
             f"{(x.P[kk & (x.t0 >= SPLIT)] == x.s[kk & (x.t0 >= SPLIT)]).mean() * 100:.0f}%)")
    for nama, m in (("hanya prelim", x.event == "Prelim GDP q/q"), ("hanya final", x.event == "Final GDP q/q"),
                    ("ganjil", x.index % 2 == 1), ("genap", x.index % 2 == 0), ("sendiri", x.sendiri.fillna(False))):
        mm = np.asarray(m, bool)
        L.append(f"   {nama:19s} " + periode(np.where(mm, tb, 0), y, t0, th))
    for kol in ("d2", "d5", "d10", "d60"):
        yy = x[kol].fillna(0).to_numpy()
        L.append(f"   target {kol:12s} " + periode(wf(x.P.fillna(0).to_numpy(), yy, th), yy, t0, th))
    per = {Y: rate(tb, y, th == Y) for Y in range(2016, int(th.max()) + 1)}
    L.append("   per tahun: " + " • ".join(f"{k}: {v}" for k, v in per.items()))
    L.append("   contoh look-ahead (rilis → masukan P dari rilis sebelumnya, harus lebih awal):")
    for _, r in x.sample(min(15, len(x)), random_state=3).sort_values("t0").iterrows():
        L.append(f"     {r.t0:%Y-%m-%d %H:%M} {r.event:15s} ← {r.P_t0:%Y-%m-%d %H:%M} kejutan {r.P:+.0f} "
                 f"({'OK' if r.P_t0 < r.t0 else 'BOCOR'})")
    return x


def uom_independen(L: list) -> pd.DataFrame:
    from .berita_detik import sp500
    from .riset_dalam_data import _num
    ff = ff_mentah()
    u = ff[ff.event.isin(["Prelim UoM Consumer Sentiment", "Revised UoM Consumer Sentiment"])].copy()
    u = u.sort_values("t0").drop_duplicates("t0").reset_index(drop=True)
    u["a"], u["f"] = u.actual.map(_num), u.forecast.map(_num)
    spx = sp500()
    rows = []
    for i, r in u.iterrows():
        if r.event != "Revised UoM Consumer Sentiment":
            continue
        pre = u[(u.event == "Prelim UoM Consumer Sentiment") & (u.t0 < r.t0) & (u.t0 >= r.t0 - pd.Timedelta(days=25))]
        if not len(pre):
            continue
        tp = pre.t0.iloc[-1]
        s1 = spx[spx.available <= r.t0 - pd.Timedelta(hours=1)]
        s0 = spx[spx.index < tp.tz_convert("America/New_York").tz_localize(None).normalize()]
        if not len(s1) or not len(s0):
            continue
        rows.append({"t0": r.t0, "tp": tp, "ch": (s1.value.iloc[-1] / s0.value.iloc[-1] - 1) * 100,
                     "spx_t1": s1.index[-1], "spx_t0": s0.index[-1], "s": np.sign(r.a - r.f)})
    x = pd.DataFrame(rows)
    lj = pd.read_parquet(DIR / "lonjakan.parquet")[["t0", "arah", "d2", "d5", "d10", "d60", "sendiri"]].drop_duplicates("t0")
    x = x.merge(lj, on="t0", how="left")
    x = x[x.arah.notna()].reset_index(drop=True)
    L.append(f"\n## 2. UoM final ← S&P 500 sejak prelim (hitung ulang dari FF mentah; {len(x)} rilis)")
    y, th, t0 = x.arah.to_numpy(), x.t0.dt.year.to_numpy(), x.t0
    for amb in (0.5, 1.0, 1.5):
        c = np.where(x.ch >= amb, 1.0, np.where(x.ch <= -amb, -1.0, 0.0))
        L.append(f"   ambang ±{amb:.1f}%       " + periode(wf(c, y, th), y, t0, th))
    c = np.where(x.ch >= 1, 1.0, np.where(x.ch <= -1, -1.0, 0.0))
    kk = (c != 0) & (x.s != 0)
    L.append(f"   angka: menebak kejutan UoM final {(c[kk] == x.s[kk]).mean() * 100:.0f}% (n {int(kk.sum())})")
    tb = wf(c, y, th)
    for nama, m in (("ganjil", x.index % 2 == 1), ("genap", x.index % 2 == 0), ("sendiri", x.sendiri.fillna(False))):
        mm = np.asarray(m, bool)
        L.append(f"   {nama:19s} " + periode(np.where(mm, tb, 0), y, t0, th))
    for kol in ("d2", "d5", "d10", "d60"):
        yy = x[kol].fillna(0).to_numpy()
        L.append(f"   target {kol:12s} " + periode(wf(c, yy, th), yy, t0, th))
    L.append("   contoh look-ahead (final ← close S&P terakhir dipakai, harus < hari final):")
    for _, r in x.sample(min(15, len(x)), random_state=3).sort_values("t0").iterrows():
        L.append(f"     final {r.t0:%Y-%m-%d %H:%M} prelim {r.tp:%Y-%m-%d} | S&P {r.spx_t0:%Y-%m-%d} → {r.spx_t1:%Y-%m-%d} "
                 f"{r.ch:+.1f}% ({'OK' if r.spx_t1 < r.t0.tz_convert(None).normalize() else 'BOCOR'})")
    return x


def plasebo(L: list) -> None:
    """Jumat 10:00 ET TANPA UoM (2016–2026): S&P 500 dua pekan terakhir ≥ ±1% → tebakan emas berlawanan (sama dengan
    U_REVSPX) dinilai terhadap lonjakan 0–60 dtk pada jam itu (tick Exness yang ada saja)."""
    from .berita_detik import sp500
    from .riset_dalam_data import jadwal, satu
    spx = sp500()
    j = jadwal()
    uom_hari = set(j[j.grup.isin(["UOM", "CB", "JOLTS"])].t0.dt.tz_convert("America/New_York").dt.date)
    rows = []
    for d in pd.bdate_range("2016-01-01", "2026-09-30", freq="W-FRI"):
        if d.date() in uom_hari:
            continue
        t0 = pd.Timestamp(f"{d:%Y-%m-%d} 10:00").tz_localize("America/New_York").tz_convert("UTC")
        if ticks(t0) is None:
            continue
        o = satu(t0)
        if o.get("arah") is None:
            continue
        s1 = spx[spx.available <= t0 - pd.Timedelta(hours=1)]
        s0 = spx[spx.index < (d - pd.Timedelta(days=14))]
        if len(s1) and len(s0):
            o["ch"] = (s1.value.iloc[-1] / s0.value.iloc[-1] - 1) * 100
            rows.append(o)
    x = pd.DataFrame(rows)
    L.append(f"\n## 3. Plasebo U_REVSPX: Jumat 10:00 ET tanpa UoM/CB/JOLTS yang punya tick ({len(x)} hari)")
    if not len(x):
        L.append("   tidak ada jendela tick di luar jam berita (jendela Exness hanya di sekitar berita) → plasebo tidak bisa")
        return
    c = np.where(x.ch >= 1, 1.0, np.where(x.ch <= -1, -1.0, 0.0))
    ok = (c != 0) & (x.arah != 0)
    L.append(f"   emas lonjakan berlawanan arah S&P: {(-c[ok] == x.arah[ok]).mean() * 100:.0f}% (n {int(ok.sum())})")


def global_perm(L: list, kandidat: dict) -> None:
    from .riset_dalam import KHUSUS, UMUM
    f = pd.read_parquet(DIR / "fitur.parquet")
    f = f[f.arah.notna() & (f.th >= 2016)]
    grup = {k: f[f.kel == k] for k in KHUSUS}
    rng = np.random.default_rng(21)

    def akurasi(x: pd.DataFrame, c: str, y: np.ndarray) -> float:
        g = -x[c].fillna(0).to_numpy()
        ok = (g != 0) & (y != 0)
        return (g[ok] == y[ok]).mean() if ok.sum() >= 40 else np.nan

    obs = {(k, c): akurasi(x, c, x.arah.to_numpy()) for k, x in grup.items() for c in UMUM + KHUSUS[k]}
    maks = []
    for _ in range(2000):
        m = -1.0
        for k, x in grup.items():
            yp = x.arah.to_numpy()[rng.permutation(len(x))]
            for c in UMUM + KHUSUS[k]:
                a = akurasi(x, c, yp)
                if a == a:
                    m = max(m, a)
        maks.append(m)
    maks = np.array(maks)
    L.append("\n## 4. Permutasi GLOBAL (66 aturan, 10 kelompok, ≥ 40 rilis 2016+, akurasi mentah tanpa saringan tahun)")
    for (k, c), v in sorted(obs.items(), key=lambda kv: -(kv[1] if kv[1] == kv[1] else 0))[:8]:
        L.append(f"   {k:9s} {c:9s} mentah {v * 100:.1f}% → p global {(maks >= v).mean():.3f}"
                 + ("  ← kandidat" if (k, c) in kandidat else ""))
    L.append(f"   (rata-rata aturan terbaik acakan {maks.mean() * 100:.1f}%, P95 {np.quantile(maks, 0.95) * 100:.1f}%)")


def main() -> None:
    L = ["# 🔎 Verifikasi adversarial riset mendalam (research/riset_dalam_cek.py)", __doc__.split("\n\n")[1]]
    gdp_independen(L)
    uom_independen(L)
    plasebo(L)
    global_perm(L, {("GDP_LAIN", "P"), ("UOM_FIN", "U_REVSPX")})
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
