"""⏱️ Prediksi ARAH XAU 1–10 detik setelah rilis, SEBELUM rilis — semua berita, semua metode yang bisa diuji.

python -m research.pra_xau_semua          → docs/eksternal/hasil_pra_xau_semua.txt (+ data/research/eksternal/pra_xau_semua.parquet)

Permintaan pengguna 10 Okt 2026 (URGENT): "2 detik terlalu lambat — candle 1 detik setelah rilis bot sudah entry; prediksi
arah XAU SEBELUM news apa pun, cari di semua metode, riset dan uji validitas". Aturan ditetapkan sebelum melihat hasil:

TARGET  tanda harga tengah (bid+ask)/2 XAU dari t0−1 dtk ke t0+1/2/3/5/10 dtk (tick Exness 2015–2026; Dukascopy 2010–2026
        pembanding). Rilis yang harganya belum bergerak (selisih 0) tidak dihitung.
FITUR   (semua sudah diketahui sebelum t0−1; +1 = mengarah naik):
  KEJ    petunjuk kejutan teruji per berita → arah emas (research/berita_gabung, sumber_lain, pra_xau_dalam)
  D10 D30 D120   gerak tick 10/30/120 detik terakhir sebelum rilis (lanjut)
  M15 M60        gerak candle 15 & 60 menit sebelum rilis;  H4 H24  gerak 4 & 24 jam (H1)
  TREN   close H1 di atas EMA 50 H1;  TRD   close H1 di atas EMA 200 H1
  GRUP   arah mayoritas detik 1 untuk jenis berita itu di tahun-tahun SEBELUMNYA (walk-forward, ≥ 20 rilis, ≥ 55%)
  LALU   arah detik 10 rilis sebelumnya untuk jenis berita yang sama
  Non-arah (untuk model): VOL volatilitas 60 menit / median 20 hari, SPR spread Exness t0−1, JAM jam UTC.
UJI 1   aturan tunggal: arah (lanjut atau kebalikan) DIPILIH di LAMA (< Okt 2021) per fitur & per jenis berita, lalu
        dinilai di BARU (≥ Okt 2021) — hasil BARU inilah yang jujur.
UJI 2   model walk-forward per tahun (logistik & gradient boosting; dilatih hanya tahun sebelumnya), semua rilis & per
        jenis berita; juga subset "yakin" (peluang ≥ 0,60 / ≥ 0,65).
LOLOS   BARU > 55%, n ≥ 30, p binomial < 0,05, dan searah di Dukascopy.
"""
from __future__ import annotations

import json
from math import comb
from pathlib import Path

import numpy as np
import pandas as pd

from .news_detik import NEW, events, prepare

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "eksternal" / "hasil_pra_xau_semua.txt"
CACHE = ROOT / "data" / "research" / "eksternal" / "pra_xau_semua_v2.parquet"
H = [1, 2, 3, 5, 10]
FEEDS = ("XAU_EXNESS", "XAU")
ARAH_F = ["KEJ", "EXP", "PS", "PSB", "TIK", "D10", "D30", "D120", "BTC10", "BTC60", "M15", "M60", "H4", "H24", "TREN",
          "TRD", "GRUP", "LALU"]


def binom_p(k: int, n: int) -> float:
    return float(sum(comb(n, i) for i in range(k, n + 1)) / 2 ** n) if n else 1.0


def sg(v) -> float:
    return 0.0 if v is None or v != v or v == 0 else float(np.sign(v))


def kejutan_arah() -> pd.Series:
    """Waktu rilis → arah emas dari petunjuk teruji (suara semua judul yang rilis bersamaan)."""
    from .berita_gabung import emas, tabel
    from .pra_xau_dalam import fitur_tambahan
    from .sumber_lain import fitur
    df = emas(tabel())
    df["-P"] = -df.P
    df["K|P"] = np.where(df.K.fillna(0) != 0, df.K, df.P)
    judul = ["CPI m/m", "Core CPI m/m", "CPI y/y", "ISM Services PMI", "Unemployment Rate"]
    fx = fitur(df[df.event.isin(judul)].copy())[["t0", "event", "WTI", "GA"]]
    df = df.merge(fx, on=["t0", "event"], how="left")
    ppi = fitur_tambahan(df[df.event.isin(["PPI m/m", "Core PPI m/m"])].copy())[["t0", "event", "CPI"]]
    df = df.merge(ppi, on=["t0", "event"], how="left")
    aturan = {"CPI m/m": ["K|P", "WTI"], "Core CPI m/m": ["K|P"], "CPI y/y": ["P"], "ISM Services PMI": ["-P", "GA"],
              "Advance GDP q/q": ["G"], "Core PPI m/m": ["CPI"], "PPI m/m": ["CPI"]}
    parts = []
    for judul_, cols in aturan.items():
        x = df[df.event == judul_]
        for c in cols:
            y = x[x[c].notna() & (x[c] != 0) & x.arah_bawah.notna()]
            parts.append(pd.Series(np.where(y[c] < 0, y.arah_bawah, y.arah_atas), index=y.t0))
    s = pd.concat(parts).groupby(level=0).sum()
    return np.sign(s[s != 0])


def kalender_fitur() -> pd.DataFrame:
    """Per waktu rilis: EXP (konsensus vs angka lalu) & PS (kejutan rilis lalu) → arah emas, suara semua judul."""
    import json
    from .news_prediksi import calendar
    rx = json.loads((ROOT / "cloud" / "api" / "reaksi.json").read_text(encoding="utf-8")).get("judul") or {}
    arah = {ev: (1.0 if r["bawah"]["naik60"] >= 0.5 else -1.0, 1.0 if r["atas"]["naik60"] >= 0.5 else -1.0)
            for ev, r in rx.items() if "bawah" in r and "atas" in r}
    cal = calendar()
    rows = []
    for ev, g in cal.groupby("event"):
        if ev not in arah:
            continue
        g = g.sort_values("time")
        bawah, atas = arah[ev]
        gap = (g.time - g.time.shift(1)).dt.days
        for t, f, pa, ps, d in zip(g.time, g.f, g.a.shift(1), g.s.shift(1), gap):
            if d != d or d > 45:
                continue
            exp = np.sign(f - pa) if pa == pa else 0.0
            rows.append({"t0": t, "EXP": 0.0 if exp == 0 else (bawah if exp < 0 else atas),
                         "PS": 0.0 if ps != ps or ps == 0 else (bawah if ps < 0 else atas)})
    return np.sign(pd.DataFrame(rows).groupby("t0")[["EXP", "PS"]].sum())


def bangun() -> pd.DataFrame:
    """Satu baris per rilis. KETAT: semua fitur hanya dari data ≤ t0−1 dtk. Candle M15/H1 yang dipakai hanya yang SUDAH
    TUTUP sebelum t0; harga "sekarang" = close candle M15 terakhir dikoreksi gerak tick dari t0−1 ke tick terakhir < t0
    (supaya detik terakhir sebelum rilis tidak ikut)."""
    if CACHE.exists():
        return pd.read_parquet(CACHE)
    from .eksternal import asset
    from .event_stats import xau_m15
    ev = events()
    ev = ev[ev.time >= pd.Timestamp("2010-01-01", tz="UTC")].sort_values("time").drop_duplicates("time")
    m15 = xau_m15()
    h1 = asset("XAUUSD").b.df[["open", "high", "low", "close"]].astype(float)
    h1 = h1[h1.high > h1.low]
    ema50 = h1.close.ewm(span=50, adjust=False).mean()
    ema200 = h1.close.ewm(span=200, adjust=False).mean()
    rng = (h1.high - h1.low)
    kej = kejutan_arah()
    kf = kalender_fitur()
    rows = []
    for r in ev.itertuples():
        t = r.time
        row = {"t0": t, "grup": r.group, "KEJ": float(kej.get(t, 0.0)), "JAM": t.hour + t.minute / 60}
        if t in kf.index:
            row["EXP"], row["PS"] = float(kf.EXP[t]), float(kf.PS[t])
        dlast = None
        for f in FEEDS:
            p = prepare(t, f)
            if p is None:
                continue
            i = p.at(-1)
            if i < 1 or p.T[i] < -60:
                continue
            m0 = float(p.mid[i])
            row[f"m0_{f}"] = m0
            for h in H:
                k = p.at(h)
                if k >= 0:
                    row[f"y{h}_{f}"] = float(p.mid[k] - m0)
            j0 = p.at(-1e-6)                                   # tick terakhir sebelum t0
            dl = float(p.mid[j0] - m0) if j0 >= i else 0.0
            if f == "XAU" or dlast is None:
                dlast = dl
            if f == "XAU_EXNESS" or "D10" not in row:
                for lag, nm in ((10, "D10"), (30, "D30"), (110, "D120")):
                    j = p.at(-1 - lag)
                    row[nm] = sg(m0 - float(p.mid[j])) if j >= 0 and p.T[j] >= -125 else 0.0
                d = np.diff(p.mid[:i + 1])
                nz = np.flatnonzero((d != 0) & (p.T[1:i + 1] >= -31))
                row["TIK"] = sg(d[nz[-1]]) if len(nz) else 0.0
            row["SPR" if f == "XAU_EXNESS" else "SPR_D"] = float(p.ask[i] - p.bid[i])
        if not any(k.startswith("y") for k in row):
            continue
        b = prepare(t, "BTC") if t >= pd.Timestamp("2018-01-01", tz="UTC") else None
        if b is not None:
            i = b.at(-1)
            if i >= 0 and b.T[i] >= -5:
                for lag, nm in ((60, "BTC60"), (10, "BTC10")):
                    j = b.at(-1 - lag)
                    if j >= 0 and b.T[j] >= -1 - lag - 5:
                        row[nm] = sg(b.mid[i] - b.mid[j])
        tutup = m15[m15.index + pd.Timedelta(minutes=15) <= t]
        if len(tutup) >= 100 and t - (tutup.index[-1] + pd.Timedelta(minutes=15)) <= pd.Timedelta(minutes=15):
            sekarang = float(tutup.close.iloc[-1]) - (dlast or 0.0)
            for menit, nm in ((15, "M15"), (60, "M60"), (240, "H4"), (1440, "H24")):
                k = tutup.index.searchsorted(t - pd.Timedelta(minutes=menit))
                batas = pd.Timedelta(minutes=max(60, menit // 2))
                if k < len(tutup) and tutup.index[k] - (t - pd.Timedelta(minutes=menit)) <= batas:
                    row[nm] = sg(sekarang - float(tutup.open.iloc[k]))
            vol60 = float(tutup.high.iloc[-4:].max() - tutup.low.iloc[-4:].min())
            k = h1.index.searchsorted(t - pd.Timedelta(hours=1), side="right") - 1   # H1 terakhir yang SUDAH tutup
            if k >= 480:
                row["TREN"] = 1.0 if sekarang > ema50.iloc[k] else -1.0
                row["TRD"] = 1.0 if sekarang > ema200.iloc[k] else -1.0
                med = float(rng.iloc[k - 480:k + 1].median())
                row["VOL"] = vol60 / med if med else np.nan
        rows.append(row)
    df = pd.DataFrame(rows).sort_values("t0").reset_index(drop=True)
    # GRUP (walk-forward) & LALU (rilis sebelumnya jenis sama), dari Exness bila ada, selain itu Dukascopy
    y1 = df["y1_XAU_EXNESS"].where(df["y1_XAU_EXNESS"].notna(), df.get("y1_XAU"))
    y10 = df["y10_XAU_EXNESS"].where(df["y10_XAU_EXNESS"].notna(), df.get("y10_XAU"))
    df["_s1"], df["_s10"] = np.sign(y1), np.sign(y10)
    grp, lalu = [], []
    for i, r in df.iterrows():
        sebelum = df[(df.grup == r.grup) & (df.t0 < r.t0 - pd.Timedelta(days=200))]
        s = sebelum._s1[sebelum._s1 != 0]
        grp.append((1.0 if (s > 0).mean() >= 0.55 else -1.0 if (s < 0).mean() >= 0.55 else 0.0) if len(s) >= 20 else 0.0)
        prev = df[(df.grup == r.grup) & (df.t0 < r.t0)].tail(1)
        lalu.append(float(prev._s10.iloc[0]) if len(prev) and prev._s10.iloc[0] == prev._s10.iloc[0] else 0.0)
    df["GRUP"], df["LALU"] = grp, lalu
    df["PSB"] = -df.get("PS", pd.Series(0.0, index=df.index)).fillna(0.0)
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(CACHE)
    return df


def binom_sf(k: int, n: int) -> float:
    from scipy.stats import binom
    return float(binom.sf(k - 1, n, 0.5)) if n else 1.0


def nilai(pred: np.ndarray, y: np.ndarray, t: pd.DatetimeIndex, tahun: bool = True) -> dict:
    m = (pred != 0) & (y != 0) & ~np.isnan(y)
    ok = np.sign(pred[m]) == np.sign(y[m])
    tt = t[m]
    k, n = int(ok.sum()), int(m.sum())
    lama, baru = ok[tt < NEW], ok[tt >= NEW]
    if tahun:
        th = pd.Series(ok).groupby(tt.year).agg(["mean", "size"])
        th = th[th["size"] >= 5]
    return {"n": n, "benar": k / n * 100 if n else np.nan, "p": binom_sf(k, n),
            "lama": lama.mean() * 100 if len(lama) else np.nan, "n_lama": len(lama),
            "baru": baru.mean() * 100 if len(baru) else np.nan, "n_baru": len(baru),
            "p_baru": binom_sf(int(baru.sum()), len(baru)),
            "tahun": f"{int((th['mean'] > 0.5).sum())}/{len(th)}" if tahun else ""}


GRUPNYA = ("NFP", "CPI", "PPI", "RETAIL", "PCE", "GDP", "FOMC", "JOLTS", "ISM", "ADP", "CLAIMS", "KONSUMEN", "RUMAH",
           "MANUFAKTUR", "DURABLE", "MINYAK", "ECI", "PMI", "NERACA", "TIC")


def lolos_cek(e: dict, ol: dict, d: dict) -> bool:
    """LOLOS: orientasi dari LAMA (≥ 52%, n ≥ 30), BARU Exness > 55% (n ≥ 30, p < 0,05), Dukascopy BARU > 50%."""
    return (ol["n"] >= 30 and ol["benar"] >= 52 and e["n_baru"] >= 30 and e["baru"] > 55 and e["p_baru"] < 0.05
            and (d["baru"] != d["baru"] or d["baru"] > 50))


def _kombinasi(df: pd.DataFrame):
    grupnya = ["SEMUA"] + [g for g in GRUPNYA if (df.grup == g).sum() >= 40]
    for g in grupnya:
        x = df if g == "SEMUA" else df[df.grup == g]
        for f in ARAH_F:
            if f in x and not (x[f].fillna(0) == 0).all():
                yield g, x, f


def uji_satu(x: pd.DataFrame, f: str, h: int, tahun: bool = True):
    t = pd.DatetimeIndex(x.t0)
    pr = x[f].fillna(0).to_numpy()
    ye = x[f"y{h}_XAU_EXNESS"].to_numpy()
    yd = x[f"y{h}_XAU"].to_numpy()
    lama = t < NEW
    ol = nilai(pr[lama], np.where(np.isnan(ye[lama]), yd[lama], ye[lama]), t[lama], False)
    arah = 1.0 if (ol["benar"] != ol["benar"] or ol["benar"] >= 50) else -1.0
    e, d = nilai(arah * pr, ye, t, tahun), nilai(arah * pr, yd, t, False)
    if ol["benar"] == ol["benar"] and ol["benar"] < 50:
        ol = dict(ol, benar=100 - ol["benar"])
    return arah, ol, e, d


def uji_tunggal(df: pd.DataFrame, L: list[str]) -> list[tuple]:
    """Arah fitur dipilih di LAMA (Exness 2015–Sep 2021 + Dukascopy 2010–Sep 2021) lalu dinilai di BARU."""
    lolos = []
    akhir = None
    for g, x, f in _kombinasi(df):
        if g != akhir:
            L.append(f"\n## {g} ({len(x)} rilis)")
            akhir = g
        baris = []
        for h in (1, 3, 10):
            arah, ol, e, d = uji_satu(x, f, h)
            ok = lolos_cek(e, ol, d)
            if ok:
                lolos.append((g, f, h, arah, e, d))
            baris.append(f"{h}dtk {'✅' if ok else ''}{'lanjut' if arah > 0 else 'balik'} LAMA {ol['benar']:.0f}% "
                         f"(n {ol['n']}) → BARU Exness {e['baru']:.0f}% (n {e['n_baru']}, p {e['p_baru']:.3f}) "
                         f"Duka {d['baru']:.0f}% • thn {e['tahun']}")
        L.append(f"   {f:5s} " + " | ".join(baris))
    return lolos


def acak(df: pd.DataFrame, ulang: int = 100, seed: int = 7) -> list[int]:
    """Uji permutasi SELURUH prosedur: target diacak di dalam tiap jenis berita (keterkaitan fitur ↔ hasil diputus),
    lalu dihitung berapa kombinasi yang 'lolos' — ini jumlah lolos yang muncul karena kebetulan saja."""
    rng = np.random.default_rng(seed)
    hasil = []
    for _ in range(ulang):
        z = df.copy()
        for g, idx in z.groupby("grup").groups.items():
            ii = np.asarray(idx)
            perm = rng.permutation(len(ii))
            for h in (1, 3, 10):
                for c in (f"y{h}_XAU_EXNESS", f"y{h}_XAU"):
                    z.loc[ii, c] = z.loc[ii, c].to_numpy()[perm]
        n = 0
        for g, x, f in _kombinasi(z):
            for h in (1, 3, 10):
                arah, ol, e, d = uji_satu(x, f, h, False)
                n += lolos_cek(e, ol, d)
        hasil.append(n)
    return hasil


def suara(df: pd.DataFrame, L: list[str]) -> None:
    """Gabungan: tiap (grup, fitur) yang di LAMA ≥ 53% (n ≥ 40) memberi suara sesuai orientasinya; dinilai di BARU."""
    L.append("\n## SUARA — gabungan semua (grup, fitur) yang ≥ 53% di LAMA (n ≥ 40), dinilai di BARU")
    t = pd.DatetimeIndex(df.t0.to_numpy())
    lama = t < NEW
    for h in (1, 3, 10):
        ye = df[f"y{h}_XAU_EXNESS"].to_numpy()
        y = np.where(np.isnan(ye), df[f"y{h}_XAU"].to_numpy(), ye)
        vote = np.zeros(len(df))
        dipakai = []
        for g, x, f in _kombinasi(df):
            m = np.ones(len(df), bool) if g == "SEMUA" else (df.grup == g).to_numpy()
            pr = df[f].fillna(0).to_numpy() * m
            r = nilai(pr[lama], y[lama], t[lama])
            if r["n"] >= 40 and r["benar"] == r["benar"] and abs(r["benar"] - 50) >= 3:
                a = 1.0 if r["benar"] > 50 else -1.0
                vote += a * pr
                dipakai.append(f"{g}:{f}{'+' if a > 0 else '−'}")
        for ambang in (1, 2, 3, 4):
            pred = np.where(np.abs(vote) >= ambang, np.sign(vote), 0.0)
            e = nilai(pred, ye, t)
            L.append(f"   {h:2d} dtk |suara| ≥ {ambang}: LAMA {e['lama']:.1f}% (n {e['n_lama']}) → BARU Exness {e['baru']:.1f}% "
                     f"(n {e['n_baru']}, p {e['p_baru']:.3f}) • thn {e['tahun']}")
        L.append(f"        {len(dipakai)} aturan dipakai: " + ", ".join(dipakai[:30]) + (" …" if len(dipakai) > 30 else ""))


def uji_model(df: pd.DataFrame, L: list[str]) -> None:
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.linear_model import LogisticRegression
    fitur = ARAH_F + ["VOL", "SPR", "JAM"]
    gd = pd.get_dummies(df.grup, prefix="g", dtype=float)
    X = pd.concat([df[fitur].astype(float), gd], axis=1)
    L.append("\n## UJI 2 — model walk-forward per tahun (dilatih tahun sebelumnya saja), target arah Exness (cadangan Dukascopy)")
    for h in H:
        y = df[f"y{h}_XAU_EXNESS"].where(df[f"y{h}_XAU_EXNESS"].notna(), df[f"y{h}_XAU"])
        ok = y.notna() & (y != 0)
        Xh, yh = X[ok].reset_index(drop=True), (y[ok] > 0).astype(int).reset_index(drop=True)
        th = pd.DatetimeIndex(df.t0[ok].to_numpy())
        for nama, mk in (("logistik", lambda: LogisticRegression(C=0.3, max_iter=2000)),
                         ("boosting", lambda: HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05,
                                                                              max_iter=150, min_samples_leaf=40,
                                                                              random_state=0))):
            p = np.full(len(yh), np.nan)
            for th_ in range(2013, 2027):
                tr = th.year < th_
                te = th.year == th_
                if tr.sum() < 200 or te.sum() == 0:
                    continue
                m = mk().fit(Xh[tr].fillna(0), yh[tr])
                p[te] = m.predict_proba(Xh[te].fillna(0))[:, 1]
            sel = ~np.isnan(p)
            baris = []
            for ambang in (0.5, 0.6, 0.65):
                pick = sel & ((p >= ambang) | (p <= 1 - ambang)) if ambang > 0.5 else sel & (p != 0.5)
                pred = np.where(p[pick] >= 0.5, 1, 0)
                benar = pred == yh[pick].to_numpy()
                tt = th[pick]
                bl, bb = benar[tt < NEW], benar[tt >= NEW]
                baris.append(f"p≥{ambang:.2f}: {benar.mean() * 100:.1f}% (n {pick.sum()}) LAMA {bl.mean() * 100 if len(bl) else float('nan'):.1f}% "
                             f"BARU {bb.mean() * 100 if len(bb) else float('nan'):.1f}% (n {len(bb)}, p {binom_p(int(bb.sum()), len(bb)):.3f})")
            L.append(f"   {h:2d} dtk {nama:9s} " + " | ".join(baris))


def main() -> None:
    df = bangun()
    L = ["# ⏱️ Prediksi arah XAU 1–10 detik SEBELUM rilis — semua berita, semua metode", __doc__.split("\n\n")[1], "",
         f"Rilis dengan data: {len(df)} (Exness {df['y1_XAU_EXNESS'].notna().sum()}, Dukascopy {df['y1_XAU'].notna().sum()})"]
    for h in H:
        ye = df[f"y{h}_XAU_EXNESS"].dropna()
        ye = ye[ye != 0]
        L.append(f"Dasar {h} dtk: naik {(ye > 0).mean() * 100:.1f}% (Exness, n {len(ye)})")
    L.append("Terisi: " + ", ".join(f"{f} {int((df[f].fillna(0) != 0).sum())}" for f in ARAH_F if f in df))
    lolos = uji_tunggal(df, L)
    suara(df, L)
    uji_model(df, L)
    jml = sum(1 for _ in _kombinasi(df)) * 3
    L += ["", f"## LOLOS (aturan tunggal dari {jml} kombinasi grup × petunjuk × detik; orientasi LAMA ≥ 52%, BARU > 55%, "
          "p < 0,05, searah Dukascopy)"]
    L += [f"   {g} • {f} ({'lanjut' if a > 0 else 'balik'}) • {h} dtk: BARU Exness {e['baru']:.1f}% (n {e['n_baru']}, p "
          f"{e['p_baru']:.3f}), Duka {d['baru']:.1f}%, semua {e['benar']:.1f}%, tahun > 50%: {e['tahun']}"
          for g, f, h, a, e, d in lolos] or ["   TIDAK ADA"]
    ac = acak(df)
    L += ["", f"## UJI ACAK (permutasi {len(ac)}×): jumlah 'lolos' bila hasil diacak = rata-rata {np.mean(ac):.1f}, "
          f"95% ≤ {np.percentile(ac, 95):.0f}, maks {max(ac)}; sungguhan {len(lolos)} → "
          f"peluang kebetulan ≥ {len(lolos)}: {np.mean(np.array(ac) >= len(lolos)) * 100:.0f}%"]
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


JSON = ROOT / "cloud" / "api" / "pra_aset.json"
OUT_TREN = ROOT / "docs" / "eksternal" / "hasil_pra_xau_tren.txt"
TREN_GRUP = ("SEMUA", "CPI", "ISM", "PPI", "GDP")


def _skor(df: pd.DataFrame, pred: np.ndarray, h: int, feed: str) -> dict:
    y = df[f"y{h}_{feed}"].to_numpy()
    r = nilai(pred, y, pd.DatetimeIndex(df.t0.to_numpy()))
    return {k: (round(float(v), 1) if isinstance(v, float) and k not in ("p", "p_baru") else
                round(float(v), 4) if isinstance(v, float) else v) for k, v in r.items()}


def tren(df: pd.DataFrame | None = None) -> None:
    """Petunjuk berita (KEJ) × tren emas 4 jam (H4) + H4 saja untuk berita tanpa petunjuk → pra_aset.json["tren"].
    Ditemukan SETELAH melihat hasil putaran 1 (gabungan dua petunjuk), jadi dicek ketahanannya: definisi tren lain
    (24 jam, EMA 50 H1) memberi pola sama; tetap perlu uji maju."""
    df = bangun() if df is None else df
    K, T4 = df.KEJ.fillna(0).to_numpy(), df.H4.fillna(0).to_numpy()
    sepakat = np.where((K != 0) & (K == T4), K, 0.0)
    lawan = np.where((K != 0) & (T4 != 0) & (K != T4), K, 0.0)
    tanpa = np.where(K == 0, T4, 0.0)
    out = {"catatan": "KEJ = arah emas dari petunjuk teruji berita; H4 = harga 1 dtk sebelum rilis vs 4 jam sebelumnya "
                      "(candle M15 yang sudah tutup). Ditemukan setelah melihat data → perlu uji maju.",
           "sepakat": {}, "berlawanan": {}, "tanpa": {}}
    L = ["# ⏱️ Petunjuk berita × tren emas 4 jam → arah XAU 1–10 detik setelah rilis", tren.__doc__.split("\n\n")[0], ""]
    for nama, pred, grupnya in (("sepakat", sepakat, TREN_GRUP), ("berlawanan", lawan, TREN_GRUP),
                                ("tanpa", tanpa, ("SEMUA",) + tuple(g for g in GRUPNYA if (df.grup == g).sum() >= 40))):
        L.append(f"\n## {nama}")
        for g in grupnya:
            m = np.ones(len(df), bool) if g == "SEMUA" else (df.grup == g).to_numpy()
            p = pred * m
            out[nama][g] = {str(h): {"exness": _skor(df, p, h, "XAU_EXNESS"), "dukascopy": _skor(df, p, h, "XAU")}
                            for h in H}
            e = out[nama][g]
            L.append(f"   {g:10s} " + " | ".join(
                f"{h} dtk {e[str(h)]['exness']['benar']}% (n {e[str(h)]['exness']['n']}, LAMA {e[str(h)]['exness']['lama']} "
                f"BARU {e[str(h)]['exness']['baru']}, thn {e[str(h)]['exness']['tahun']}; Duka {e[str(h)]['dukascopy']['benar']})"
                for h in (1, 3, 10)))
    d = json.loads(JSON.read_text(encoding="utf-8")) if JSON.exists() else {}
    d["tren"] = out
    JSON.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    OUT_TREN.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    import sys
    if sys.argv[1:2] == ["tren"]:
        tren()
    else:
        main()
