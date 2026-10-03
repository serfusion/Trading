"""Verifikasi "Signal Strike EA" (grid martingale trader, 3 Okt 2026) — python -m research.signal_strike

Bukti dari pengguna: (1) notifikasi Telegram "BUY Entry | Lot 0.07 | 4177.890" 07:05 dan "Profit Closed +1274.85 USC,
Balance 53682.14 USC, TP HIT L17 + Close All" 09:05 (WIB = UTC+7 → 00:05 & 02:05 UTC, 2 Okt 2026); (2) 17 deal tutup
2 Okt 02:05:00–02:05:04; (3) laporan MT5 "bulan lalu": 1.792 trade, net +42.654,80 USC, PF 2,83, Balance Drawdown
Maximal 2.937,30 (5,36%) = 14 kalah beruntun −2.937,30, long 1.602 / short 190, profit terbesar 1.859,50.
Klaim: layer minus selalu ditutup layer berikutnya, tidak pernah tutup minus, minimal 0,03 lot, floating 2 jam aman,
bot 24 jam termasuk saat berita.

Bagian: (a) rekonstruksi lot & harga entry tiap layer dari deal (profit BUY = lot x 100 x (tutup − entry));
(b) uji pengali lot; (c) floating & jarak ke akun habis; (d) September 2026 dengan aturan hasil rekonstruksi vs laporan
(drawdown saldo ala MT5 vs drawdown ekuitas); (e) peluang per keranjang & umur akun 2012–2026 (research.martingale_ea).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .martingale_ea import SPLIT, USC, keranjang, load, lot_table, mulai, ringkas_keranjang, ringkas_mulai, sim

OUT = Path(__file__).resolve().parent.parent / "docs" / "eksternal" / "hasil_signal_strike.txt"

# deal tutup 2 Okt 02:05 (urutan layar: terbaru → terlama)
TUTUP = [4155.394, 4155.186, 4155.122, 4155.173, 4155.173, 4155.476, 4155.476, 4155.476, 4155.476, 4155.244,
         4155.184, 4155.184, 4155.184, 4155.248, 4155.251, 4155.251, 4155.084]
PROFIT = [1700.91, 870.25, 537.50, 217.66, 106.68, 5.00, -112.65, -167.37, -205.12, -235.32, -220.40, -219.08,
          -205.75, -197.19, -188.51, -166.83, -159.64]
MODAL_TG = 53682.14 - 1274.85     # saldo sebelum keranjang ditutup (USC)

# nama, arah, lot0, pengali, jarak $, TP $ dari rata-rata, maks layer, modal USC, lot rekursif
VARIAN = [
    ("S1 rekonstruksi: BUY 0,07 lot x1,2 jarak $2,25 TP +$1,9, modal $524", 1, 0.07, 1.2, 2.25, 1.9, 40, MODAL_TG, True),
    ("S2 sama, dua arah", 0, 0.07, 1.2, 2.25, 1.9, 40, MODAL_TG, True),
    ("S3 klaim minimum 0,03 lot", 1, 0.03, 1.2, 2.25, 1.9, 40, MODAL_TG, True),
    ("S4 jarak $1,8", 1, 0.07, 1.2, 1.8, 1.9, 40, MODAL_TG, True),
    ("S5 jarak $3", 1, 0.07, 1.2, 3.0, 1.9, 40, MODAL_TG, True),
    ("S6 akun screenshot pertama: 0,10 lot, modal $430", 1, 0.10, 1.2, 2.25, 1.9, 40, 43_000.0, True),
    ("S7 TP +$5 dari rata-rata", 1, 0.07, 1.2, 2.25, 5.0, 40, MODAL_TG, True),
]


def rekonstruksi(out: list) -> tuple[np.ndarray, np.ndarray]:
    tutup, prof = np.array(TUTUP[::-1]), np.array(PROFIT[::-1])        # L1..L17
    out.append(f"(a) 17 deal: jumlah {prof.sum():+,.2f} USC (Telegram +1.274,85; selisih {prof.sum() - 1274.85:+.2f}). "
               f"L1: 0,07 x 100 x (4177,890 − {tutup[0]}) = {7 * (4177.890 - tutup[0]):.2f} → cocok −159,64.")
    out.append("(b) Uji pengali lot (entry = tutup − profit/(100 x lot); harus turun terus untuk BUY):")
    for m in (1.1, 1.15, 1.2, 1.25, 1.3):
        for rek in (True, False):
            lots = np.array(lot_table(0.07, m, 17, rek))
            ent = tutup - prof / (USC * lots)
            stp = -np.diff(ent)
            out.append(f"  x{m} {'rekursif' if rek else 'pangkat  '}: L17 {lots[-1]:.2f} lot, jarak {stp.min():5.2f}..{stp.max():5.2f}"
                       f", naik {int((stp <= 0).sum())}x, simpangan {stp.std():.2f}")
    lots = np.array(lot_table(0.07, 1.2, 17, True))
    ent = tutup - prof / (USC * lots)
    out.append("  Terpilih x1,2 rekursif (satu-satunya yang L1 = 0,07 dan entry selalu turun dengan jarak wajar):")
    for k in range(17):
        out.append(f"    L{k + 1:2d} {lots[k]:4.2f} lot entry {ent[k]:8.3f}"
                   + (f" jarak {ent[k - 1] - ent[k]:4.2f}" if k else "           ") + f"  profit {prof[k]:+8.2f}")
    avg = (lots * ent).sum() / lots.sum()
    out.append(f"  total {lots.sum():.2f} lot (${lots.sum():.2f} per $1), rata-rata entry {avg:.3f}, tutup ±"
               f"{tutup.mean():.3f} = rata-rata +${tutup.mean() - avg:.2f}; jarak rata-rata ${np.diff(-ent).mean():.2f}, "
               f"median ${np.median(np.diff(-ent)):.2f}")
    return lots, ent


def floating(out: list, lots: np.ndarray, ent: np.ndarray) -> None:
    eq0 = MODAL_TG / 100
    out.append(f"(c) Floating keranjang 2 Okt (saldo sebelum tutup ${eq0:,.2f}):")
    for low, lab in ((4141.5, "± saat L17 masuk"), (4140.0, ""), (4134.45, "low Twelve Data 01:10")):
        fl = float((lots * (low - ent)).sum())
        out.append(f"  harga {low:8.2f} {lab:22s}: floating ${fl:7.2f} ({100 * fl / eq0:5.1f}% ekuitas)")
    tanpa = ent[-1] - (eq0 + float((lots * (ent[-1] - ent)).sum())) / lots.sum()
    out.append(f"  tanpa layer baru: akun habis bila harga ±{tanpa:.1f} (${ent[-1] - tanpa:.0f} di bawah L17, "
               f"${ent[0] - tanpa:.0f} di bawah L1)")
    tab = lot_table(0.07, 1.2, 40, True)
    sl, sc, p, k = float(lots.sum()), float((lots * ent).sum()), float(ent[-1]), 17
    while True:
        p -= 2.25
        if eq0 + sl * p - sc <= 0 or k >= 40:
            break
        sl, sc, k = sl + tab[k], sc + tab[k] * p, k + 1
    out.append(f"  dengan layer lanjut tiap $2,25 (x1,2): habis sekitar L{k} di ±{p:.1f} (${ent[0] - p:.0f} di bawah L1); "
               f"lot L18–L20 = {tab[17]}, {tab[18]}, {tab[19]}")
    for l0, md in ((0.03, MODAL_TG), (0.10, 43_000.0)):
        tb = lot_table(l0, 1.2, 60, True)
        sl = sc = 0.0
        p0 = 4177.89
        for k in range(60):
            p = p0 - 2.25 * k
            sl, sc = sl + tb[k], sc + tb[k] * p
            if md / 100 + sl * (p - 2.25) - sc <= 0:
                break
        out.append(f"  mulai {l0:.2f} lot modal ${md / 100:.0f}: habis sekitar L{k + 1} (${2.25 * (k + 1):.0f} turun dari L1)")


def mt5_drawdown(deals: list[float], modal: float) -> tuple[float, int, float]:
    """Drawdown saldo ala laporan MT5 dari urutan deal, kalah beruntun terpanjang & jumlahnya (USC)."""
    bal = np.cumsum(np.r_[modal, deals])
    dd = float((np.maximum.accumulate(bal) - bal).max())
    run = best = 0
    s = worst = 0.0
    for x in deals:
        if x < 0:
            run, s = run + 1, s + x
            if run > best:
                best, worst = run, s
        else:
            run, s = 0, 0.0
    return dd, best, worst


def september(out: list, df: pd.DataFrame) -> None:
    out.append("(d) September 2026, EA selalu aktif (laporan asli: 1.792 trade, +$426,55, long 1.602 / short 190, DD saldo "
               "2.937,30 USC = 14 kalah beruntun, profit trade terbesar 1.859,50 USC):")
    t = df.index
    i0 = int(t.searchsorted(pd.Timestamp("2026-09-01", tz="UTC")))
    i1 = int(t.searchsorted(pd.Timestamp("2026-10-01", tz="UTC")))
    for v in VARIAN[:3]:
        info: list = []
        cl, ruins, _, _ = sim(df, *v[1:], i0=i0, i1=i1, info=info)
        ok = [r for r in info if r[4] is not None]
        deals = [x for r in ok for x in r[4]]
        dd, run, worst = mt5_drawdown(deals, v[7])
        low = min(ok, key=lambda r: r[2])
        out.append(f"  {v[0][:26]:26s}: {len(info)} keranjang / {len(deals)} trade; akun habis {len(ruins)}x ("
                   + ", ".join(f"{r:%d/%m %H:%M}" for r in ruins) + ")")
        out.append(f"      keranjang yang selamat saja: DD saldo ala MT5 {dd:,.0f} USC ({100 * dd / v[7]:.1f}%, {run} kalah "
                   f"beruntun {worst:,.0f}) TETAPI floating terdalam {low[2] - v[7]:,.0f} USC ({100 * (low[2] / v[7] - 1):.0f}% "
                   f"modal, {low[1]} layer, {t[low[0]]:%d/%m %H:%M}); profit trade terbesar {max(deals):,.0f}")


def nfp(out: list, df: pd.DataFrame) -> None:
    """EA selalu aktif 2 Okt 2026 sejak 12:00 UTC (NFP 12:30, emas 4.225 → 4.126 pada 13:00–15:55)."""
    v = VARIAN[0]
    info: list = []
    i0 = int(df.index.searchsorted(pd.Timestamp("2026-10-02 12:00", tz="UTC")))
    sim(df, *v[1:], i0=i0, info=info)
    out.append("(f) 2 Okt 2026 sejak 12:00 UTC, EA S1 selalu aktif — keranjang ≥ 8 layer:")
    for r in info:
        if r[1] >= 8:
            out.append(f"  tutup {df.index[r[0]]:%H:%M} {'TP' if r[4] else 'AKUN HABIS'}: {r[1]} layer, floating terdalam "
                       f"${(r[2] - v[7]) / 100:,.0f} ({100 * (r[2] / v[7] - 1):.0f}%), hasil ${r[3] / 100:+,.2f}")
    sl = cs = 0.0
    tab = lot_table(0.07, 1.2, 40, True)
    for k, lot in enumerate(tab[:21]):
        pk = 4177.89 - 2.25 * k
        sl, cs = sl + lot, cs + lot * pk
        if k + 1 in (14, 17, 20, 21):
            out.append(f"  keranjang {k + 1} layer jarak $2,25: total {sl:.2f} lot, floating di layer terakhir "
                       f"${sl * pk - cs:,.0f} ({100 * (sl * pk - cs) / (MODAL_TG / 100):.0f}% dari $524)")


def main() -> None:
    out: list[str] = []
    lots, ent = rekonstruksi(out)
    floating(out, lots, ent)
    out.append("")
    print("\n".join(out), flush=True)
    df = load()
    t0, t1 = df.index[0], df.index[-1]
    september(out, df)
    i = int(df.index.searchsorted(pd.Timestamp("2026-10-02 00:05", tz="UTC")))
    info: list = []
    sim(df, *VARIAN[0][1:], i0=i, one=True, info=info)
    r = info[0]
    out.append(f"  Ulang keranjang 2 Okt 00:05 (Twelve Data, low lebih dalam dari Exness): {'TP' if r[4] else 'HABIS'} "
               f"{df.index[r[0]]:%H:%M} UTC, {r[1]} layer, hasil ${r[3] / 100:+.2f}, floating terdalam "
               f"${(r[2] - VARIAN[0][7]) / 100:,.0f}")
    nfp(out, df)
    out.append("")
    print("\n".join(out[-20:]), flush=True)
    bulanan = pd.date_range(pd.Timestamp("2012-06-01", tz="UTC"), t1, freq="MS")
    enam = pd.date_range(t0.ceil("D"), t1, freq="6h")
    for v in VARIAN:
        out.append(v[0])
        k = keranjang(df, v, enam)
        out.append("  Satu keranjang tiap 6 jam:")
        for lab, sel in (("LAMA <Okt21", k.t < SPLIT), ("BARU Okt21+", k.t >= SPLIT),
                         ("12 bln terakhir", k.t >= t1 - pd.Timedelta(days=365))):
            out.append(ringkas_keranjang(k[sel], lab))
        win = k[k.hasil == "tp"]
        out.append(f"  keranjang ≥10 layer: {100 * (win.layer >= 10).mean():.0f}% keranjang menang tetapi "
                   f"{100 * win.usd[win.layer >= 10].sum() / win.usd.sum():.0f}% profit; untung keranjang 1 layer "
                   f"${win.usd[win.layer == 1].mean():.2f}, 10–17 layer ${win.usd[(win.layer >= 10) & (win.layer <= 17)].mean():.2f}")
        m = mulai(df, v, bulanan)
        out.append("  Akun baru tiap awal bulan (EA selalu aktif, maks 1 tahun):")
        out.append(ringkas_mulai(m[m.t < SPLIT], "mulai LAMA <Okt21"))
        out.append(ringkas_mulai(m[m.t >= SPLIT], "mulai BARU Okt21+"))
        if v is VARIAN[0]:
            okt = keranjang(df, v, pd.date_range(pd.Timestamp("2026-10-02", tz="UTC"), periods=21, freq="h"))
            out.append("  Keranjang BUY dibuka tiap jam 2 Okt 2026 (jam→hasil jam tutup/layer/$):")
            out += ["    " + "  ".join(f"{r.t:%H}→{r.hasil} {r.akhir:%H:%M}/{r.layer}L/${r.usd:+.0f}"
                                         for r in okt.iloc[j:j + 6].itertuples()) for j in range(0, len(okt), 6)]
        out.append("")
        print("\n".join(out[-14:]), flush=True)
    OUT.write_text("\n".join(out) + "\n")
    print("->", OUT)


if __name__ == "__main__":
    main()
