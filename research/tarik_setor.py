"""Skema TARIK-SETOR: tarik profit rutin, setor ulang dari uang tarikan saat akun habis (4 Okt 2026)
python -m research.tarik_setor

Permintaan pengguna: "EA MT5 harus profit bagaimanapun caranya, mungkin pakai sistem deposit dan tarik dana supaya
ketika margin call masih ada uang lampau yang kita tarik, deposit lagi". Diuji dengan DOMPET = semua uang pengguna
(tabungan di luar broker + saldo akun): setoran awal & setiap setor ulang = uang keluar dari dompet, setiap tarikan =
uang masuk dompet, akhir periode = saldo akun + floating ikut dihitung (dinilai pasar).

A. EA grid/martingale (mesin research/martingale_ea.sim, BUY, TP rata-rata +$1,9, jeda 45 mnt) × 7 cara tarik:
   tiap keranjang (saldo dijaga = modal), harian, pekanan, bulanan, saat saldo ≥ 1,5x / 2x modal, tidak pernah.
B. Strategi yang punya keunggulan (sinyal 💰 replay cloud, piramida tren) dengan risiko tetap $ per sinyal di akun $400:
   apakah tarik-setor membuat risiko besar di akun kecil jadi aman?
Akun habis = ekuitas ≤ 0 (stop out Exness 0%; perlindungan saldo negatif → rugi maksimal = saldo akun). LAMA = Jun 2012 –
Sep 2021, BARU = Okt 2021 – 3 Okt 2026, masing-masing dijalankan dari akun baru.
"""
from __future__ import annotations

import math
import os
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

from .krisis_filter import KONFIG as KRISIS
from .martingale_ea import SPLIT, USC, arrays, load, sim
from .signal_strike import MODAL_TG

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "eksternal" / "hasil_tarik_setor.txt"
VER = ROOT / "data" / "research" / "eksternal" / "verifikasi"
M4 = 40_000.0
AWAL = pd.Timestamp("2012-06-01", tz="UTC")

# nama, arah, lot0, pengali, jarak, TP, maks layer, modal USC, rekursif, jeda, batas rugi, akhir pekan, krisis
EA = [
    ("X2f BAWAAN EA v1.00: x2 0,01 lot jarak $5 maks 15 + batas rugi 30% + akhir pekan", 1, 0.01, 2.0, 5.0, 1.9, 15, M4,
     False, 45, 0.3, True, None),
    ("X2a x2 0,01 lot jarak $2,25 tanpa pengaman, modal $400", 1, 0.01, 2.0, 2.25, 1.9, 40, M4, False, 45, 0.0, False, None),
    ("X2a sama, modal $200", 1, 0.01, 2.0, 2.25, 1.9, 40, M4 / 2, False, 45, 0.0, False, None),
    ("X2a sama, modal $100", 1, 0.01, 2.0, 2.25, 1.9, 40, M4 / 4, False, 45, 0.0, False, None),
    ("R1a x1,2 0,05 lot jarak $2,25 (rasio trader), modal $400", 1, 0.05, 1.2, 2.25, 1.9, 40, M4, True, 45, 0.0, False, None),
    ("S1 rekonstruksi trader 0,07 lot/$524, jeda 30 mnt", 1, 0.07, 1.2, 2.25, 1.9, 40, MODAL_TG, True, 30, 0.0, False, None),
    tuple(KRISIS[6]),     # Q1 $400 x1,2 0,05 + filter krisis 'beku' + akhir pekan
    tuple(KRISIS[-1]),    # Q4 BAWAAN EA v1.10
]
CARA = [(None, "tiap keranjang"), ("D", "harian"), ("W", "pekanan"), ("M", "bulanan"), (1.5, "saldo ≥ 1,5x"),
        (2.0, "saldo ≥ 2x"), (math.inf, "tidak ditarik")]
_G: dict = {}


def _init(df: pd.DataFrame) -> None:
    _G["df"] = df


def dompet(ev: list[tuple[pd.Timestamp, float]], akhir: float, a: pd.Timestamp, b: pd.Timestamp) -> dict:
    """ev = arus kas dompet (+ tarikan, − setoran) berurutan waktu; akhir = nilai akun di akhir periode."""
    e = pd.DataFrame(ev, columns=["t", "usd"]).sort_values("t", kind="stable")
    kum = e.usd.cumsum()
    bulan = pd.date_range(a, b, freq="MS")
    per = e.groupby(e.t.dt.tz_localize(None).dt.to_period("M")).usd.sum()
    m = pd.Series([per.get(p.tz_localize(None).to_period("M"), 0.0) for p in bulan[:-1]], dtype=float)
    roll = lambda k: (m.rolling(k).sum().dropna() > 0).mean() if len(m) >= k else float("nan")  # noqa: E731
    n_bln = max((b - a).days / 30.44, 1.0)
    bersih = float(e.usd.sum() + akhir)
    return dict(bersih=bersih, per_bln=bersih / n_bln, setor=int((e.usd < 0).sum()), keluar_maks=float(-kum.min()),
                bln_pos=float((m > 0).mean()), r6=roll(6), r12=roll(12),
                th=" ".join(f"{y}:{v:+,.0f}" for y, v in e.groupby(e.t.dt.year).usd.sum().items()))


def jalankan_ea(arg: tuple) -> dict:
    v, tarik, lab, per = arg
    df = _G["df"]
    t, c = df.index, arrays(df)[3]
    a, b = (AWAL, SPLIT) if per == "LAMA" else (SPLIT, t[-1])
    i0, i1 = max(int(t.searchsorted(a)), 1), int(t.searchsorted(b))
    tk: list = []
    cl, ruins, _, st = sim(df, *v[1:9], i0=i0, i1=i1, jeda_menit=v[9], stop_pct=v[10], akhir_pekan=v[11], krisis=v[12],
                           tarik=tarik, tarikan=tk)
    modal = v[7] / USC
    ev = [(t[i0], -modal)] + [(r, -modal) for r in ruins]
    ev += [(x.t, x.usc / USC) for x in cl.itertuples()] if tarik is None else [(t[i], u / USC) for i, u in tk]
    akhir = st["bal"] / USC
    if st["n"]:
        akhir += st["sl"] * st["d"] * c[i1 - 1] - st["sc"]
        akhir = max(akhir, 0.0)
    out = dict(ea=v[0][:3] + (" $" + f"{modal:.0f}" if v[0].startswith("X2a") else ""), nama=v[0], cara=lab, per=per,
               keranjang=len(cl), habis=len(ruins), hasil_keranjang=float(cl.usc.sum() / USC) if tarik is not None else float("nan"))
    out.update(dompet(ev, akhir, a, b))
    return out


def jalur_r(t: pd.Series, pnl: np.ndarray, modal: float, cara: str) -> tuple[list, float, int]:
    """Akun dengan risiko tetap $: urut waktu tutup. cara: 'trade' (tarik kelebihan tiap trade), 'M', 'tidak'."""
    bal, ev, habis, per0 = modal, [(t.iloc[0], -modal)], 0, None
    for tt, x in zip(t, pnl):
        bal += x
        if bal <= 0:                       # rugi maksimal = saldo akun (perlindungan saldo negatif)
            habis += 1
            ev.append((tt, -modal))
            bal = modal
            continue
        p = (tt.year, tt.month)
        if bal > modal and (cara == "trade" or (cara == "M" and per0 is not None and p != per0)):
            ev.append((tt, bal - modal))
            bal = modal
        per0 = p
    return ev, bal, habis


def bagian_b() -> list[str]:
    from . import piramida as pr
    from . import verifikasi as vf
    from .grid_cari import R_USD, fitur
    seri = {}
    for aset in ("XAU", "BTC"):                    # replay kode cloud konfigurasi live, R bersih spread asli Exness
        d = vf.net(aset, vf.load(aset))
        d["t"] = pd.to_datetime(d.t_close, utc=True)
        d["w"] = np.where(d.lapis, 0.5, 1.0)      # lapisan = lot ½
        seri[f"💰 {aset}"] = d.sort_values("t", kind="stable").rename(columns={"r": "r_kotor", "R": "r"})[["t", "r", "w"]]
    df = load()
    pr._init(df, fitur(df))
    p = pr.jalankan(("tren2", 3.0, 2.0, 6, 1.0), detail=True)
    seri["piramida 3 ATR"] = pd.DataFrame(dict(t=p.tutup, r=p.r, w=1.0)).sort_values("t")
    seri["💰 XAU + BTC (EA mengikuti keduanya)"] = pd.concat([seri["💰 XAU"], seri["💰 BTC"]]).sort_values("t", kind="stable")
    out = ["B. Strategi dengan keunggulan, akun $400, risiko tetap per sinyal (lapisan ½), urut waktu tutup "
           "(posisi bersamaan tidak dinilai floating → hasil sebenarnya sedikit lebih buruk). R piramida = $"
           f"{R_USD:.0f} dasar riset, diskalakan.", ""]
    for aset, d in seri.items():
        out.append(aset)
        for per, sel in (("LAMA", d.t < SPLIT), ("BARU", d.t >= SPLIT)):
            x = d[sel & (d.t >= AWAL)]
            if x.empty:
                continue
            a, b = x.t.iloc[0].normalize(), x.t.iloc[-1]
            kum = np.r_[0, np.cumsum((x.r * x.w).to_numpy())]
            dd_r = float((np.maximum.accumulate(kum) - kum).max())
            out.append(f"  {per}: n {len(x)}, WR {100 * (x.r > 0).mean():.0f}%, total {kum[-1]:+.0f}R, DD terdalam {dd_r:.0f}R "
                       "(akun $400 aman bila DD x risiko < $400)")
            for pct in (0.5, 1.0, 2.0, 5.0, 10.0):
                risk = 400 * pct / 100
                hasil = []
                for cara in ("trade", "M", "tidak"):
                    ev, bal, habis = jalur_r(x.t, (x.r * x.w * risk).to_numpy(), 400.0, cara)
                    w = dompet(ev, bal, a, b)
                    pos = f", bulan dompet + {100 * w['bln_pos']:.0f}%" if cara != "tidak" else ""
                    hasil.append(f"{ {'trade': 'tarik tiap trade', 'M': 'tarik bulanan', 'tidak': 'tanpa tarik'}[cara]}: "
                                 f"${w['per_bln']:+7.1f}/bln, habis {habis}x, uang keluar maks ${w['keluar_maks']:,.0f}{pos}")
                out.append(f"  {per} risiko {pct:4.1f}% (${risk:.0f}): DD ${dd_r * risk:,.0f} | " + " | ".join(hasil))
        out.append("")
    return out


def main() -> None:
    import sys
    if "b" in sys.argv[1:]:                        # hanya bagian B (cepat), ganti bagian B di file hasil
        lama = OUT.read_text().split("\nB. ")[0] if OUT.exists() else ""
        out = bagian_b()
        OUT.write_text(lama.rstrip("\n") + "\n\n" + "\n".join(out) + "\n")
        print("\n".join(out))
        return
    df = load()
    jobs = [(v, cara, lab, per) for v in EA for cara, lab in CARA for per in ("LAMA", "BARU")]
    with Pool(min(os.cpu_count() or 2, 8), initializer=_init, initargs=(df,)) as pool:
        res = pd.DataFrame(pool.map(jalankan_ea, jobs, chunksize=1))
    res.to_csv(OUT.with_suffix(".csv"), index=False, float_format="%.2f")
    out = [__doc__.strip().splitlines()[0], "",
           f"Data {df.index[0]:%Y-%m-%d} s/d {df.index[-1]:%Y-%m-%d}. Kolom: bersih dompet $/bulan | setoran (awal + setor "
           "ulang) | uang keluar maks (yang harus disiapkan) | bulan dompet + | jendela 6 / 12 bulan + | keranjang | habis.", "",
           "A. EA grid/martingale"]
    for nama, g in res.groupby("nama", sort=False):
        out.append(nama)
        for r in g.itertuples():
            out.append(f"  {r.per} {r.cara:15s} ${r.per_bln:+7.1f}/bln (total ${r.bersih:+8,.0f}) | setor {r.setor:3d}x | keluar maks "
                       f"${r.keluar_maks:7,.0f} | bln + {100 * r.bln_pos:3.0f}% | 6 bln + {100 * r.r6:3.0f}% | 12 bln + "
                       f"{100 * r.r12:3.0f}% | keranjang {r.keranjang:6,d} habis {r.habis:3d}")
        terbaik = g[g.per == "BARU"].sort_values("per_bln").iloc[-1]
        out.append(f"  BARU terbaik: {terbaik.cara} ${terbaik.per_bln:+.1f}/bln; per tahun: {terbaik.th}")
        out.append("")
    b = res[res.per == "BARU"]
    out.append(f"Ringkas BARU: {len(b)} kombinasi EA x cara tarik, positif {(b.bersih > 0).sum()}, "
               f"terbaik ${b.per_bln.max():+.1f}/bln, rata-rata ${b.per_bln.mean():+.1f}/bln. LAMA positif "
               f"{(res[res.per == 'LAMA'].bersih > 0).sum()} dari {len(b)}.")
    out.append("")
    out += bagian_b()
    OUT.write_text("\n".join(out) + "\n")
    print("\n".join(out))
    print("->", OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
