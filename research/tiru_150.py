"""Meniru EA trader (Signal Strike) dengan target $150/bulan — python -m research.tiru_150

Pertanyaan pengguna (3 Okt 2026): di luar sinyal 💰, kalau klaim trader itu kita tiru, bisa dapat $150 per bulan?
Aturan hasil rekonstruksi `research/signal_strike.py` (lot x1,2 dibulatkan per layer, TP rata-rata +$1,9, jarak tetap
sebagai pendekatan indikator) dijalankan dengan mesin `research/martingale_ea.py`:

1. Per bulan kalender (Jun 2012 – Sep 2026): akun baru tiap awal bulan, EA selalu aktif sampai akhir bulan atau akun
   habis. Hasil bulan = profit tertutup + floating di akhir bulan (dinilai pasar), atau −modal bila habis.
2. Lot awal & modal diskalakan bersama (rasio sama ≈ risiko habis sama) supaya median bulan yang selamat ≈ $150.
3. Jalan terus 12 bulan dari tiap awal bulan, setor ulang modal setiap akun habis.
LAMA = mulai < Okt 2021, BARU = Okt 2021+.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from .martingale_ea import SPLIT, USC, arrays, load, sim
from .signal_strike import MODAL_TG

OUT = Path(__file__).resolve().parent.parent / "docs" / "eksternal" / "hasil_tiru_150.txt"
TARGET = 150.0

BASIS = [
    # nama, arah, lot0, pengali, jarak, TP, maks layer, modal USC, rekursif, jeda antar keranjang (menit)
    ("S1 seperti trader 0,07 lot/$524, jeda 30 mnt", 1, 0.07, 1.2, 2.25, 1.9, 40, MODAL_TG, True, 30),
    ("S1 seperti trader 0,07 lot/$524, jeda 45 mnt", 1, 0.07, 1.2, 2.25, 1.9, 40, MODAL_TG, True, 45),
    ("S3 klaim minimum 0,03 lot/$524, jeda 30 mnt", 1, 0.03, 1.2, 2.25, 1.9, 40, MODAL_TG, True, 30),
    ("S3 klaim minimum 0,03 lot/$524, jeda 45 mnt", 1, 0.03, 1.2, 2.25, 1.9, 40, MODAL_TG, True, 45),
    ("S1 selalu aktif (tanpa jeda, pembanding)", 1, 0.07, 1.2, 2.25, 1.9, 40, MODAL_TG, True, 0),
]


def jalan(df: pd.DataFrame, v: tuple, a: pd.Timestamp, b: pd.Timestamp, stop: bool):
    """Hasil $ periode [a, b): profit tertutup + floating akhir − modal x jumlah habis; jumlah habis; waktu habis pertama;
    profit tertutup $."""
    t = df.index
    c = arrays(df)[3]
    i0, i1 = max(int(t.searchsorted(a)), 1), int(t.searchsorted(b))
    kw = dict(jeda_menit=v[9]) if len(v) <= 10 else dict(jeda_menit=v[9], stop_pct=v[10], akhir_pekan=v[11])
    if len(v) > 12:
        kw["krisis"] = v[12]
    cl, ruins, _, st = sim(df, *v[1:9], i0=i0, i1=i1, stop=stop, **kw)
    flo = 0.0
    if not (stop and len(ruins)) and st["n"]:
        flo = USC * (st["sl"] * st["d"] * c[i1 - 1] - st["sc"]) + st["bal"] - v[7]
    hasil = (cl.usc.sum() + flo - len(ruins) * v[7]) / 100
    return hasil, len(ruins), (ruins[0] if len(ruins) else None), cl.usc.sum() / 100


def bulanan(df: pd.DataFrame, v: tuple) -> pd.DataFrame:
    awal = pd.date_range(pd.Timestamp("2012-06-01", tz="UTC"), df.index[-1], freq="MS")
    rows = []
    for a, b in zip(awal[:-1], awal[1:]):
        hasil, n, _, _ = jalan(df, v, a, b, stop=True)
        rows.append(dict(t=a, usd=hasil, habis=n > 0))
    return pd.DataFrame(rows)


def skala(v: tuple, k: float) -> tuple:
    lot0 = max(round(v[2] * k, 2), 0.01)
    k = lot0 / v[2]                       # modal mengikuti pembulatan lot
    return (v[0], v[1], lot0, v[3], v[4], v[5], v[6], v[7] * k, v[8], v[9])


def ringkas(m: pd.DataFrame, modal: float, lab: str) -> str:
    ok = m[~m.habis]
    med = f"${ok.usd.median():6.0f}" if len(ok) else "     -"
    return (f"  {lab:12s} {len(m):3d} bln | akun habis {100 * m.habis.mean():4.1f}% bulan | bulan selamat: median {med}, "
            f"rugi {100 * (ok.usd < 0).mean() if len(ok) else 0:3.0f}% | ≥ $150 {100 * (m.usd >= TARGET).mean():3.0f}% "
            f"bulan | rata-rata bersih semua bulan ${m.usd.mean():+6.0f} (modal ${modal:,.0f})")


def setahun(df: pd.DataFrame, v: tuple) -> pd.DataFrame:
    """Akun baru tiap awal bulan, berhenti di akun habis pertama atau 12 bulan."""
    awal = pd.date_range(pd.Timestamp("2012-06-01", tz="UTC"), df.index[-1] - pd.Timedelta(days=365), freq="MS")
    rows = []
    for a in awal:
        hasil, n, tr, tarik = jalan(df, v, a, a + pd.Timedelta(days=365), stop=True)
        bln = (tr - a).days / 30.44 if tr is not None else 12.0
        rows.append(dict(t=a, usd=hasil, habis=n > 0, bln=bln, tarik=tarik))
    return pd.DataFrame(rows)


def ringkas_th(y: pd.DataFrame, modal: float, lab: str) -> str:
    return (f"  {lab:12s} {len(y):3d} awal | selamat 12 bln {100 * (~y.habis).mean():3.0f}% | umur median "
            f"{y.bln.median():4.1f} bln | ditarik sebelum habis/12 bln median ${y.tarik.median():6,.0f} | hasil bersih median "
            f"${y.usd.median():+7,.0f}, rata-rata ${y.usd.mean():+7,.0f} | negatif {100 * (y.usd < 0).mean():3.0f}%")


def main() -> None:
    df = load()
    out = [f"Target ${TARGET:.0f}/bulan. Data {df.index[0]:%Y-%m-%d} s/d {df.index[-1]:%Y-%m-%d}. BUY, aturan rekonstruksi "
           "Signal Strike; jeda 30–45 mnt antar keranjang = kalibrasi September 2026 (1.401–1.886 trade vs laporan 1.792).",
           "Lot awal & modal diskalakan bersama supaya median bulan selamat BARU (Okt 2021+) ≈ $150.", ""]
    for v0 in BASIS:
        m0 = bulanan(df, v0)
        sel = m0[(m0.t >= SPLIT) & ~m0.habis]
        k = TARGET / sel.usd.median()
        v = skala(v0, k)
        m = bulanan(df, v)
        modal = v[7] / 100
        out.append(f"{v0[0]} → lot awal {v[2]:.2f}, modal ${modal:,.0f} (median bulan selamat BARU skala 1: ${sel.usd.median():.0f})")
        out.append(ringkas(m[m.t < SPLIT], modal, "LAMA <Okt21"))
        out.append(ringkas(m[m.t >= SPLIT], modal, "BARU Okt21+"))
        out.append(ringkas(m[m.t >= pd.Timestamp("2025-10-01", tz="UTC")], modal, "12 bln akhir"))
        th = m.groupby(m.t.dt.year).agg(habis=("habis", "sum"), usd=("usd", "sum"))
        out.append("  per tahun (bulan habis / bersih $): " + " ".join(f"{y}:{int(r.habis)}/{r.usd:+,.0f}" for y, r in th.iterrows()))
        y = setahun(df, v)
        out.append("  Satu akun dijalankan terus (berhenti di habis pertama, maks 12 bln):")
        out.append(ringkas_th(y[y.t < SPLIT], modal, "LAMA <Okt21"))
        out.append(ringkas_th(y[y.t >= SPLIT], modal, "BARU Okt21+"))
        out.append("")
        print("\n".join(out[-10:]), flush=True)
    OUT.write_text("\n".join(out) + "\n")
    print("->", OUT)


if __name__ == "__main__":
    main()
