"""🎯 Peluang emas NAIK/TURUN SEBELUM rilis untuk SEMUA berita (termasuk FOMC), terkalibrasi & bisa dihitung live (16 Okt 2026).

python -m research.pra_peluang         → cloud/api/pra_peluang.json + docs/eksternal/hasil_pra_peluang.txt

Pengguna: "saya mau sebelum rilis pun kamu sudah predict persentase naik/turun dan berubah up to date sekaligus mengecek data
informasi tambahan di internet dan tambahkan persentasenya — bukan setelah rilis". Target = gaya pengguna: masuk t0−1 dtk,
emas (harga tengah tick Exness) lebih tinggi/rendah di detik 30 dan 60 (research/masuk_pra kutipan, 1.627 rilis 2016–2026).
Fitur = yang bisa dibaca cloud live sebelum rilis (semua ≤ t0−1; harian FRED memakai nilai HARI SEBELUMNYA):
  M60 H4 H24  arah emas 1/4/24 jam terakhir (H1)      TREN TRD  close H1 di atas EMA 50 / EMA 200 H1
  KEJ         petunjuk berita teruji (arah emas)          Y2  arah yield 2 tahun 5 hari kerja (FRED DGS2)
  USD         arah dolar luas 5 hari kerja (FRED DTWEXBGS)
Model: logistik L2 per kelompok berita (dan SEMUA), walk-forward per tahun (dilatih HANYA tahun sebelumnya). Dinilai dengan
akurasi per arah tebakan, Brier vs "dasar" (frekuensi naik tahun-tahun sebelumnya), kalibrasi per kelas peluang, LAMA/BARU.
Hasil dipakai cloud (_pra_peluang.py) HANYA sebagai angka peluang jujur: bila model tidak lebih baik dari dasar, yang tampil
= dasar + koreksi tren yang teruji (tidak dibesar-besarkan).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
EKS = ROOT / "data" / "research" / "eksternal"
OUT_JSON = ROOT / "cloud" / "api" / "pra_peluang.json"
OUT_TXT = ROOT / "docs" / "eksternal" / "hasil_pra_peluang.txt"
SPLIT = pd.Timestamp("2021-10-01", tz="UTC")
FITUR = ["M60", "H4", "H24", "TREN", "TRD", "KEJ", "Y2", "USD"]
TARGET = {"30": 30, "60": 60}
MIN_GRUP = 60


def fred(seri: str) -> pd.Series:
    d = json.loads((EKS / f"fred_{seri}.json").read_text(encoding="utf-8"))
    s = pd.Series({pd.Timestamp(o["date"]): float(o["value"]) for o in d["observations"] if o["value"] not in (".", "")})
    return s.sort_index()


def arah5(s: pd.Series, t0: pd.Timestamp) -> float:
    """Arah perubahan 5 hari kerja sampai HARI SEBELUM rilis (nilai FRED harian baru terbit setelah tutup pasar)."""
    hari = (t0.tz_convert("America/New_York").normalize().tz_localize(None)) - pd.Timedelta(days=1)
    x = s[s.index <= hari]
    if len(x) < 6:
        return 0.0
    return float(np.sign(x.iloc[-1] - x.iloc[-6]))


def data() -> pd.DataFrame:
    from .masuk_pra import kutipan, mid
    q = kutipan()
    q["t0"] = pd.to_datetime(q.t0, utc=True)
    s = pd.read_parquet(EKS / "pra_xau_semua_v2.parquet")
    s["t0"] = pd.to_datetime(s.t0, utc=True)
    s = s.drop_duplicates(["t0", "grup"])[["t0", "grup", "M60", "H4", "H24", "TREN", "TRD", "KEJ"]]
    df = q.merge(s, on=["t0", "grup"], how="inner")
    m0 = (df.bid_in + df.ask_in) / 2
    for k, h in TARGET.items():
        g = mid(df, h) - m0.to_numpy()
        df[f"up{k}"] = np.where(g > 0, 1.0, np.where(g < 0, 0.0, np.nan))
    y2, usd = fred("DGS2"), fred("DTWEXBGS")
    df["Y2"] = [arah5(y2, t) for t in df.t0]
    df["USD"] = [arah5(usd, t) for t in df.t0]
    for f in FITUR:
        df[f] = df[f].fillna(0.0)
    return df


def fit(X: np.ndarray, y: np.ndarray, C: float = 0.3):
    from sklearn.linear_model import LogisticRegression
    return LogisticRegression(C=C, max_iter=500).fit(X, y)


def walk(g: pd.DataFrame, tgt: str) -> pd.DataFrame:
    """Peluang naik walk-forward per tahun (latih tahun < y); kolom p (model) & dasar (frekuensi naik tahun < y)."""
    g = g.dropna(subset=[tgt]).sort_values("t0")
    out = []
    for y in range(2017, 2027):
        tr, te = g[g.t0.dt.year < y], g[g.t0.dt.year == y]
        if len(tr) < 30 or te.empty or tr[tgt].nunique() < 2:
            continue
        m = fit(tr[FITUR].to_numpy(), tr[tgt].to_numpy())
        out.append(te.assign(p=m.predict_proba(te[FITUR].to_numpy())[:, 1], dasar=tr[tgt].mean()))
    return pd.concat(out) if out else pd.DataFrame()


def nilai(pr: pd.DataFrame, tgt: str) -> dict:
    y, p, b = pr[tgt].to_numpy(), pr.p.to_numpy(), pr.dasar.to_numpy()
    tebak = p >= 0.5
    ok = tebak == (y == 1)
    lama = (pr.t0 < SPLIT).to_numpy()
    o = {"n": int(len(pr)), "benar": round(float(ok.mean() * 100), 1),
         "lama": round(float(ok[lama].mean() * 100), 1) if lama.sum() >= 10 else None,
         "baru": round(float(ok[~lama].mean() * 100), 1) if (~lama).sum() >= 10 else None,
         "naik_nyata": round(float(y.mean() * 100), 1),
         "brier": round(float(((p - y) ** 2).mean()), 4), "brier_dasar": round(float(((b - y) ** 2).mean()), 4)}
    for nm, m in (("naik", tebak), ("turun", ~tebak)):
        if m.sum() >= 5:
            o[f"benar_{nm}"] = round(float(ok[m].mean() * 100), 1)
            o[f"n_{nm}"] = int(m.sum())
    kal = []
    for lo, hi in ((0, .4), (.4, .45), (.45, .5), (.5, .55), (.55, .6), (.6, 1.01)):
        m = (p >= lo) & (p < hi)
        if m.sum() >= 5:
            kal.append({"dari": lo, "ke": min(hi, 1.0), "n": int(m.sum()), "p_rata": round(float(p[m].mean() * 100), 1),
                        "naik_nyata": round(float(y[m].mean() * 100), 1)})
    o["kalibrasi"] = kal
    return o


def main() -> None:
    df = data()
    L = ["# 🎯 Peluang emas sebelum rilis, semua berita (research/pra_peluang.py)", __doc__.split("\n\n")[1],
         f"rilis: {df.t0.nunique()} jam rilis, {len(df)} baris; fitur {FITUR}"]
    hasil = {"dibuat": pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d"), "sumber": "research/pra_peluang.py", "fitur": FITUR,
             "grup": {}}
    grups = ["SEMUA"] + [g for g, n in df.groupby("grup").size().items() if n >= MIN_GRUP]
    for grp in grups:
        g = df if grp == "SEMUA" else df[df.grup == grp]
        res = {}
        for tgt in ("up30", "up60"):
            pr = walk(g, tgt)
            if pr.empty:
                continue
            res[tgt] = nilai(pr, tgt)
        if not res:
            continue
        r = res.get("up60") or {}
        lebih = r.get("brier", 1) < r.get("brier_dasar", 0)
        # model akhir (semua tahun) untuk dipakai live
        gg = g.dropna(subset=["up60"])
        m = fit(gg[FITUR].to_numpy(), gg.up60.to_numpy())
        hasil["grup"][grp] = {"n": int(len(gg)), "dasar_naik": round(float(gg.up60.mean() * 100), 1),
                              "dasar_lama": round(float(gg[gg.t0 < SPLIT].up60.mean() * 100), 1),
                              "dasar_baru": round(float(gg[gg.t0 >= SPLIT].up60.mean() * 100), 1),
                              "coef": [round(float(c), 4) for c in m.coef_[0]], "intercept": round(float(m.intercept_[0]), 4),
                              "uji": res, "lebih_baik_dari_dasar": bool(lebih)}
        L.append(f"\n## {grp} (n {len(gg)}; emas naik 1 mnt: semua {hasil['grup'][grp]['dasar_naik']}% • LAMA "
                 f"{hasil['grup'][grp]['dasar_lama']}% • BARU {hasil['grup'][grp]['dasar_baru']}%)")
        for tgt, o in res.items():
            L.append(f"   {tgt}: benar {o['benar']}% (n {o['n']}; LAMA {o['lama']} / BARU {o['baru']}) • tebakan NAIK "
                     f"{o.get('benar_naik')}% (n {o.get('n_naik')}) • TURUN {o.get('benar_turun')}% (n {o.get('n_turun')}) • Brier "
                     f"{o['brier']} vs dasar {o['brier_dasar']} {'✅ lebih baik' if o['brier'] < o['brier_dasar'] else '✗ tidak lebih baik'}")
            L.append("      kalibrasi: " + " • ".join(f"p {k['dari']:.2f}–{k['ke']:.2f}: rata {k['p_rata']}% → nyata {k['naik_nyata']}% "
                                                     f"(n {k['n']})" for k in o["kalibrasi"]))
        L.append("      koef: " + ", ".join(f"{f} {c:+.2f}" for f, c in zip(FITUR, hasil["grup"][grp]["coef"])))
    # satu per satu: tiap fitur sendiri di SEMUA (naik 1 mnt bila fitur +1 vs −1), LAMA/BARU
    L.append("\n## Fitur tunggal (SEMUA rilis): emas naik 1 mnt bila fitur +1 / −1 (LAMA | BARU)")
    for f in FITUR:
        a = []
        for per, m in (("LAMA", df.t0 < SPLIT), ("BARU", df.t0 >= SPLIT)):
            x = df[m].dropna(subset=["up60"])
            a.append(f"{per} +1 {x[x[f] > 0].up60.mean() * 100:.0f}% (n {(x[f] > 0).sum()}) / −1 {x[x[f] < 0].up60.mean() * 100:.0f}% "
                     f"(n {(x[f] < 0).sum()})")
        L.append(f"   {f:5s}: " + " | ".join(a))
    OUT_JSON.write_text(json.dumps(hasil, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    OUT_TXT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
