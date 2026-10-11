"""⏱️ CPI → arah emas 1–10 DETIK setelah rilis, diuji TUTUP KERTAS (walk-forward per tahun), semua sumber.

python -m research.cpi_detik              → docs/eksternal/hasil_cpi_detik.txt

Permintaan pengguna 11 Okt 2026: "INGAT PATOKAN 1–10 DETIK SETELAH RELEASE, HITUNG MUNDURNYA SEPERTI ITU, USAHAKAN 65%,
CARI DI MANAPUN DATANYA". Target = tanda harga tengah XAU t0−1 dtk → t0+1/2/3/5/10 dtk (tick Exness, cadangan
Dukascopy; rilis yang harganya tidak bergerak tidak dihitung). "1–10 dtk" = rata-rata 2/3/5/10 dtk (seperti aplikasi)
dan 1 dtk dilaporkan terpisah.
Sumber konsensus: ForexFactory 2010–Jan 2026 + Nasdaq/Investing.com (research/nasdaq_kalender) untuk 2026 dan untuk
konsensus INDEKS CPI tanpa pembulatan. Petunjuk (tanda = tebakan CPI di atas konsensus; emas ditebak berlawanan),
ditetapkan sebelum melihat hasil:
  P_*     kejutan rilis lalu judul sama (headline, core, y/y)          KON  core: konsensus < angka bulan lalu → di atas
  YOY     y/y tersirat (indeks NSA, konsensus m/m) vs konsensus y/y     K_*  Kalshi 1 jam sebelum (2022–2025)
  IDXc    core m/m tersirat dari konsensus INDEKS core (tanpa pembulatan) − konsensus core m/m (dibulatkan) ≥ 0,02
  IDXy    y/y tersirat dari konsensus INDEKS NSA / indeks NSA 12 bln lalu − konsensus y/y ≥ 0,02
  IDXm    headline m/m tersirat dari konsensus indeks NSA (+ selisih musiman tahun lalu) − konsensus m/m ≥ 0,02
  N_*     nowcast Cleveland Fed   WTI/BENSIN  energi bulan acuan naik → headline di atas
  h_*     (hanya di model) gerak emas 30/120 dtk, 15/60 mnt, 4/24 jam sebelum rilis (research/pra_xau_semua)
TUTUP KERTAS: untuk tahun Y hanya rilis < Y yang dilihat. Tiga cara:
  (a) aturan tetap: persen tampil = ketepatan s/d tahun lalu; dipakai hanya bila > 50% & n ≥ 10
  (b) PILIH TERBAIK: tiap tahun pilih aturan dengan ketepatan lalu tertinggi (n ≥ 15) → dipakai di tahun Y
  (c) MODEL: logistik L2 pada semua petunjuk + konstanta (condong naik), dilatih hanya tahun < Y; tebak bila peluang
      ≥ ambang (0,55/0,60/0,65) atau ≤ 1 − ambang, selain itu "tidak menebak"
LAMA < Okt 2021, BARU ≥ Okt 2021 (dilaporkan juga 2022+).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "eksternal" / "hasil_cpi_detik.txt"
EKS = ROOT / "data" / "research" / "eksternal"
DET = (1, 2, 3, 5, 10)
JAUH = (2, 3, 5, 10)
MULAI = 2013
HARGA = ["D30", "D120", "M15", "M60", "H4", "H24"]


def sgn(v, batas: float = 0.0) -> float:
    return float(np.sign(v)) if v == v and abs(v) >= batas and v != 0 else 0.0


def emas() -> pd.DataFrame:
    v = pd.read_parquet(EKS / "pra_xau_semua_v2.parquet")
    v = v[v.grup == "CPI"].copy()
    for h in DET:
        v[f"g{h}"] = v[f"y{h}_XAU_EXNESS"].fillna(v[f"y{h}_XAU"])
    for c in HARGA:                                   # gerak harga SEBELUM rilis (+1 naik); dibalik agar "−" = emas naik
        v[f"h_{c}"] = -np.sign(v[c].fillna(0))
    ny = v.t0.dt.tz_convert("America/New_York")
    v = v[(ny.dt.hour == 8) & (ny.dt.minute == 30)]   # CPI selalu 08:30 New York (10 Mar 2021/2022 tercatat ganda 07:30)
    return v[["t0"] + [f"g{h}" for h in DET] + [f"h_{c}" for c in HARGA]].sort_values("t0").reset_index(drop=True)


def kalshi(df: pd.DataFrame) -> pd.DataFrame:
    """Kalshi 1 jam sebelum tutup pasar vs konsensus tabel ini (FF, cadangan Nasdaq) → juga rilis 2026."""
    import glob
    import json
    from .kalshi_uji import curve, lean
    for seri, kol, fk in (("KXCPI", "mm_K", "mm_f"), ("KXCPICORE", "core_K", "core_f")):
        df[kol] = 0.0
        for f in sorted(glob.glob(str(EKS / "kalshi" / seri / "*.json"))):
            d = json.loads(Path(f).read_text(encoding="utf-8"))
            ms = d["pasar"]
            close = min(pd.Timestamp(m["tutup"]) for m in ms)
            i = df.index[(df.t0 >= close) & (df.t0 <= close + pd.Timedelta(minutes=15))]
            if not len(i) or df.at[i[0], fk] != df.at[i[0], fk]:
                continue
            lp = lean(curve(ms, (close - pd.Timedelta(hours=1)).timestamp()), df.at[i[0], fk], 0.1)
            if lp and abs(lp[0] - lp[1]) >= 0.10:
                df.at[i[0], kol] = float(np.sign(lp[0] - lp[1]))
    return df


def tabel() -> pd.DataFrame:
    from .cpi_emas import tabel as ff_tabel
    from .eksternal_makro import fred
    from .nasdaq_kalender import cpi as nas
    from .sumber_lain import ubah_bulan
    df = emas()
    ff = ff_tabel()
    keep = ["t0", "mm_s", "core_s", "yy_s", "mm_N", "core_N"]
    df = df.merge(ff[keep], on="t0", how="left")
    cal = __import__("research.news_prediksi", fromlist=["calendar"]).calendar()
    nsa, sa = fred("CPIAUCNS").value, fred("CPIAUCSL").value
    core_sa = fred("CPILFESL").value
    rows = []
    for _, r in df.iterrows():
        t = r.t0
        ny = t.tz_convert("America/New_York").normalize().tz_localize(None)
        n = nas(ny)
        same = cal[(cal.time - t).abs() <= pd.Timedelta(minutes=5)]
        f = {e: same[same.event == e] for e in ("CPI m/m", "Core CPI m/m", "CPI y/y")}
        o = {"t0": t, "sumber": "FF" if len(f["CPI m/m"]) else ("Nasdaq" if n else "-")}
        for k, e, nk in (("mm", "CPI m/m", "mm"), ("core", "Core CPI m/m", "core"), ("yy", "CPI y/y", "yy")):
            if len(f[e]):
                o[f"{k}_f"], o[f"{k}_a"] = float(f[e].f.iloc[0]), float(f[e].a.iloc[0])
            else:
                o[f"{k}_f"], o[f"{k}_a"] = n.get(f"{nk}_f", np.nan), n.get(f"{nk}_a", np.nan)
            o[f"{k}_ns_f"] = n.get(f"{nk}_f", np.nan)                     # cek kecocokan FF vs Nasdaq
            o[f"s_{k}"] = sgn(o[f"{k}_a"] - o[f"{k}_f"])
        o["core_prev"] = n.get("core_p", np.nan)
        ref = (t.tz_convert(None) - pd.DateOffset(months=1)).to_period("M").to_timestamp()
        p1, p12, p13 = ref - pd.DateOffset(months=1), ref - pd.DateOffset(months=12), ref - pd.DateOffset(months=13)
        # YOY (konsensus m/m + efek basis, indeks NSA)
        o["YOY"] = 0.0
        if p13 in nsa.index and p1 in nsa.index and o["mm_f"] == o["mm_f"] and o["yy_f"] == o["yy_f"]:
            sea = (nsa[p12] / nsa[p13] - 1) - (sa[p12] / sa[p13] - 1)
            imp = (nsa[p1] * (1 + o["mm_f"] / 100 + sea) / nsa[p12] - 1) * 100
            o["YOY"] = sgn(imp - o["yy_f"], 0.05)
        # konsensus indeks tanpa pembulatan (Nasdaq)
        o["IDXc"] = o["IDXy"] = o["IDXm"] = 0.0
        cf, cp = n.get("cidx_f", np.nan), n.get("cidx_p", np.nan)
        if cf == cf and cp == cp and o["core_f"] == o["core_f"]:
            o["IDXc"] = sgn((cf / cp - 1) * 100 - o["core_f"], 0.02)
        nf = n.get("nsa_f", np.nan)
        if nf == nf and p12 in nsa.index and o["yy_f"] == o["yy_f"]:
            o["IDXy"] = sgn((nf / nsa[p12] - 1) * 100 - o["yy_f"], 0.02)
        if nf == nf and p1 in nsa.index and p13 in nsa.index and o["mm_f"] == o["mm_f"]:
            sea = (nsa[p12] / nsa[p13] - 1) - (sa[p12] / sa[p13] - 1)
            o["IDXm"] = sgn(((nf / nsa[p1] - 1) - sea) * 100 - o["mm_f"], 0.02)
        o["IDXcy"] = 0.0
        if cf == cf and p12 in core_sa.index and n.get("core_yy_f") == n.get("core_yy_f"):
            o["IDXcy"] = sgn((cf / core_sa[p12] - 1) * 100 - n["core_yy_f"], 0.02)
        rows.append(o)
    x = pd.DataFrame(rows)
    df = df.drop(columns=["mm_s", "core_s", "yy_s"]).merge(x, on="t0", how="left")
    # kejutan lalu (rilis sebelumnya ≤ 45 hari) & KON
    for k in ("mm", "core", "yy"):
        prev = df[f"s_{k}"].shift(1)
        dekat = (df.t0 - df.t0.shift(1)) <= pd.Timedelta(days=45)
        df[f"P_{k}"] = np.where(dekat, prev.fillna(0), 0.0)
    df["KON"] = [sgn(p - f) for p, f in zip(df.core_prev, df.core_f)]
    en = {"WTI": fred("DCOILWTICO"), "BENSIN": fred("GASREGW")}
    for k, s in en.items():
        df[f"mm_{k}"] = [sgn(ubah_bulan(s, t)) for t in df.t0]
    for c in ("mm_N", "core_N"):
        df[c] = df[c].fillna(0.0)
    df = kalshi(df)
    df["th"] = df.t0.dt.year
    return df


PETUNJUK = ["P_mm", "P_core", "P_yy", "KON", "YOY", "IDXc", "IDXy", "IDXm", "IDXcy", "mm_K", "core_K", "mm_N", "core_N",
            "mm_WTI", "mm_BENSIN"]
TURUNAN = {"YOY|P": ("YOY", "P_yy"), "IDXc|P": ("IDXc", "P_core"), "IDXy|YOY": ("IDXy", "YOY"),
           "K|P core": ("core_K", "P_core"), "K|P mm": ("mm_K", "P_mm")}


def turunan(df: pd.DataFrame) -> pd.DataFrame:
    for nama, (a, b) in TURUNAN.items():
        df[nama] = np.where(df[a] != 0, df[a], df[b])
    df["SUARA"] = np.sign(df[["P_mm", "P_core", "YOY", "IDXc", "IDXy", "KON"]].sum(axis=1))
    df["SUARA_IDX"] = np.sign(df[["IDXc", "IDXy", "IDXm"]].sum(axis=1))
    # ditambahkan SETELAH melihat hasil putaran pertama (dicatat di laporan): indeks dulu, cadangan Kalshi headline
    df["IDX|K"] = np.where(df.SUARA_IDX != 0, df.SUARA_IDX, df.mm_K)
    df["K|IDX"] = np.where(df.mm_K != 0, df.mm_K, df.SUARA_IDX)
    df["PLAFON_core"], df["PLAFON_yy"], df["PLAFON_mm"] = df.s_core, df.s_yy, df.s_mm
    df["PLAFON_net"] = np.sign(df.s_core * 2 + df.s_mm + df.s_yy)
    return df


def gerak(df: pd.DataFrame, h: int) -> pd.Series:
    return np.sign(df[f"g{h}"].fillna(0))


def tepat(df: pd.DataFrame, tebak: pd.Series, hs=JAUH) -> tuple[int, int]:
    """Benar/total (tebakan emas vs gerak), dijumlah atas jangka hs (rilis diam tidak dihitung)."""
    k = n = 0
    for h in hs:
        g = gerak(df, h)
        m = (tebak != 0) & (g != 0)
        k += int((g[m] == tebak[m]).sum())
        n += int(m.sum())
    return k, n


def pct(k, n) -> str:
    return f"{k / n * 100:5.1f}%" if n else "    –"


def per_periode(df: pd.DataFrame, tebak: pd.Series, hs=JAUH) -> str:
    out = []
    for nama, m in (("semua", df.th >= MULAI), ("LAMA", (df.th >= MULAI) & (df.t0 < "2021-10-01")),
                    ("BARU", df.t0 >= "2021-10-01"), ("2022+", df.th >= 2022)):
        k, n = tepat(df[m], tebak[m], hs)
        out.append(f"{nama} {pct(k, n)} ({k}/{n})")
    rilis = int(((tebak != 0) & (df.th >= MULAI)).sum())
    return " | ".join(out) + f" | rilis ditebak {rilis}"


def tetap(df: pd.DataFrame, col: str) -> pd.Series:
    """(a) aturan tetap, dipakai di tahun Y hanya bila ketepatan s/d Y−1 > 50% (n ≥ 10)."""
    emas_ = -df[col]
    out = pd.Series(0.0, index=df.index)
    for th in range(MULAI, int(df.th.max()) + 1):
        k, n = tepat(df[df.th < th], emas_[df.th < th])
        if n >= 10 * len(JAUH) and k / n > 0.5:
            out[df.th == th] = emas_[df.th == th]
    return out


def pilih(df: pd.DataFrame, kolom: list[str]) -> tuple[pd.Series, list]:
    """(b) tiap tahun pakai aturan dengan ketepatan lalu tertinggi."""
    out, log = pd.Series(0.0, index=df.index), []
    for th in range(MULAI, int(df.th.max()) + 1):
        lalu = df.th < th
        skor = []
        for c in kolom:
            k, n = tepat(df[lalu], -df[c][lalu])
            if n >= 15 * len(JAUH):
                skor.append((k / n, c))
        if skor:
            s, c = max(skor)
            out[df.th == th] = -df[c][df.th == th]
            log.append((th, c, s))
    return out, log


def model(df: pd.DataFrame, kolom: list[str], ambang: float) -> pd.Series:
    """(c) logistik walk-forward: target = mayoritas arah 2–10 dtk; tebakan emas +1/−1/0."""
    from sklearn.linear_model import LogisticRegression
    y = np.sign(sum(gerak(df, h) for h in JAUH))
    X = -df[kolom].to_numpy()
    out = pd.Series(0.0, index=df.index)
    for th in range(MULAI, int(df.th.max()) + 1):
        tr = ((df.th < th) & (y != 0)).to_numpy()
        te = (df.th == th).to_numpy()
        if tr.sum() < 30 or not te.any():
            continue
        m = LogisticRegression(C=0.3).fit(X[tr], (y[tr] > 0).astype(int))
        p = m.predict_proba(X[te])[:, 1]
        out[te] = np.where(p >= ambang, 1.0, np.where(p <= 1 - ambang, -1.0, 0.0))
    return out


def main() -> None:
    df = turunan(tabel())
    L = ["# ⏱️ CPI → arah emas 1–10 detik, tutup kertas", __doc__.split("\n\n")[1], ""]
    cocok = df[(df.sumber == "FF") & df.core_ns_f.notna()]
    L.append(f"Cek konsensus FF vs Nasdaq (rilis sama): headline {np.mean(cocok.mm_f == cocok.mm_ns_f) * 100:.0f}%, core "
             f"{np.mean(cocok.core_f == cocok.core_ns_f) * 100:.0f}%, y/y {np.mean(cocok.yy_f == cocok.yy_ns_f) * 100:.0f}% "
             f"sama (n {len(cocok)}); rilis berkonsensus Nasdaq saja: {(df.sumber == 'Nasdaq').sum()}; indeks core "
             f"terisi {(df.IDXc != 0).sum()}, NSA {(df.IDXy != 0).sum()}")
    dasar = pd.Series(1.0, index=df.index)
    L.append("\n## Pembanding")
    for h in DET:
        L.append(f"   selalu NAIK {h:2d} dtk: {per_periode(df, dasar, (h,))}")
    L.append("   selalu NAIK 2–10 dtk: " + per_periode(df, dasar))
    L.append("\n## Plafon (bila kejutan SUDAH diketahui) — 1 dtk vs 2–10 dtk")
    for c in ("PLAFON_core", "PLAFON_yy", "PLAFON_mm", "PLAFON_net"):
        L.append(f"   {c:12s} 1 dtk: {per_periode(df, -df[c], (1,))}")
        L.append(f"   {c:12s} 2–10: {per_periode(df, -df[c])}")
    semua = PETUNJUK + list(TURUNAN) + ["SUARA", "SUARA_IDX", "IDX|K", "K|IDX"]
    L.append("\n## (0) Ketepatan ANGKA petunjuk (tebakan kejutan benar?) — untuk konteks")
    for c in semua:
        for k in ("core", "yy", "mm"):
            if c.startswith(("P_", "mm_", "core_")) and k not in c and not c.endswith(k):
                continue
        tgt = "s_core" if ("core" in c or c in ("KON", "IDXc", "IDXc|P", "IDXcy", "SUARA", "SUARA_IDX")) else (
            "s_mm" if ("mm" in c or c == "IDXm") else "s_yy")
        m = (df[c] != 0) & (df[tgt] != 0)
        k, n = int((df[c][m] == df[tgt][m]).sum()), int(m.sum())
        b = m & (df.t0 >= "2021-10-01")
        kb, nb = int((df[c][b] == df[tgt][b]).sum()), int(b.sum())
        L.append(f"   {c:10s} vs {tgt:6s}: {pct(k, n)} (n {n}) | BARU {pct(kb, nb)} (n {nb})")
    L.append("\n## (a) Aturan tetap, tutup kertas (dipakai hanya bila tahun-tahun lalu > 50%) — 2–10 dtk | 1 dtk")
    hasil = []
    for c in semua:
        tb = tetap(df, c)
        L.append(f"   {c:10s} 2–10: {per_periode(df, tb)}")
        L.append(f"   {'':10s} 1 dtk: {per_periode(df, tb, (1,))}")
        k, n = tepat(df[df.th >= 2022], tb[df.th >= 2022])
        hasil.append((k / n if n else 0, c, n))
    L.append("\n## (b) Pilih aturan terbaik tiap tahun (dari tahun-tahun lalu)")
    tb, log = pilih(df, semua)
    L.append("   " + "; ".join(f"{th}: {c} ({s * 100:.0f}%)" for th, c, s in log))
    L.append(f"   2–10: {per_periode(df, tb)}")
    L.append(f"   1 dtk: {per_periode(df, tb, (1,))}")
    L.append("\n## (c) Model logistik walk-forward (semua petunjuk + kecenderungan naik)")
    for kol_nama, kol in (("semua petunjuk", PETUNJUK), ("tanpa Kalshi/nowcast", [c for c in PETUNJUK if c[-2:] not in
                                                                                    ("_K", "_N")]),
                         ("+ harga sebelum rilis", PETUNJUK + [f"h_{c}" for c in HARGA])):
        for a in (0.50, 0.55, 0.60, 0.65):
            tb = model(df, kol, a)
            L.append(f"   {kol_nama:22s} ambang {a:.2f} 2–10: {per_periode(df, tb)}")
    L.append("\n## Per tahun — aturan tetap terbaik 2022+ (2–10 dtk)")
    for s, c, n in sorted(hasil, reverse=True)[:5]:
        tb = tetap(df, c)
        row = []
        for th in range(MULAI, int(df.th.max()) + 1):
            k, n2 = tepat(df[df.th == th], tb[df.th == th])
            row.append(f"{th % 100:02d}:{k}/{n2}" if n2 else f"{th % 100:02d}:–")
        L.append(f"   {c:10s} ({s * 100:.0f}% 2022+) " + " ".join(row))
    L.append("\n## IDX|K per detik (tutup kertas)")
    tb = tetap(df, "IDX|K")
    for h in DET:
        L.append(f"   {h:2d} dtk: {per_periode(df, tb, (h,))}")
    L.append("\n## Kertas dibuka satu per satu — IDX|K, rilis 2022–2026 (gerak $ 1/2/3/5/10 dtk; ✅/❌ per detik 2–10)")
    for i, r in df[df.th >= 2022].iterrows():
        g = tb[i]
        if g == 0:
            L.append(f"   {r.t0:%Y-%m-%d} tidak menebak (petunjuk kosong / tahun lalu ≤ 50%)")
            continue
        tanda = "".join("·" if r[f"g{h}"] == 0 or r[f"g{h}"] != r[f"g{h}"] else ("✅" if np.sign(r[f"g{h}"]) == g else "❌")
                        for h in JAUH)
        L.append(f"   {r.t0:%Y-%m-%d} indeks {r.SUARA_IDX:+.0f} Kalshi {r.mm_K:+.0f} → tebak {'NAIK ' if g > 0 else 'TURUN'} | "
                 + " ".join(f"{r[f'g{h}']:+6.2f}" for h in DET) + f" | {tanda}")
    # rilis 14 Okt 2026: nilai petunjuk
    t = df[df.t0 >= "2026-10-01"]
    if len(t):
        L.append("\nCPI 14 Okt 2026: " + ", ".join(f"{c}={t[c].iloc[0]:+.0f}" for c in semua))
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
