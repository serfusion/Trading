"""EA grid martingale ala screenshot trader (3 Okt 2026) — python -m research.martingale_ea

Pertanyaan pengguna: seorang trader XAU/USD mengaku dapat ±$150 per akun dari EA martingale "x2 sampai 20 layer
lebih" dan mau membuka akun ke-3 di VPS — masuk akal? Screenshot: 3 akun Exness Cent (XAUUSDc), saldo masing-masing
±43.000 USC ($430), profit tertutup 11.420–12.616 USC ($114–126). Keranjang 2 Okt: BUY 1,03 / 1,24 / 1,49 / 1,79 lot
(pengali 1,2 — bukan 2), jarak ±$1,35–2,1, ditutup bersama ±02:05 di 4.154. Koreksi (research/signal_strike.py): itu
L14–L17 rantai 0,10 x 1,2 (17 layer), bukan 8 layer mulai 0,5 lot; varian A–G tetap dipakai sebagai pembanding.

Simulasi (aturan ditulis ulang, bukan kode EA): buka layer 1 seketika; tiap harga melawan `step` dari layer terakhir
tambah layer (lot x `mult`, dibulatkan 0,01, maks `maxlay`, ditolak bila free margin kurang, leverage 1:2000);
semua layer ditutup saat harga = rata-rata tertimbang + `tp`; langsung buka keranjang baru. Akun habis bila ekuitas
<= 0 (stop out Exness 0%); lalu setor ulang $430 dan lanjut (seperti membuka akun baru). Saldo dijaga $430: kelebihan
ditarik setiap keranjang tutup (seperti ketiga akun di screenshot). Jalur candle o→l→h→c (candle naik) atau o→h→l→c;
gap pembukaan diisi di harga buka. Spread XAUUSDc $0,20 tiap layer; swap/komisi diabaikan (menguntungkan EA).
Data: M15 2012–Agu 2020, M5 Agu 2020–16 Sep 2026, M5 Twelve Data 16 Sep–3 Okt 2026. 1 lot XAUUSDc = 100 USC per $1
(cek screenshot: 1,79 lot x $9,381 = 1.679,20 USC).
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd

from .data import load_m5_2020, load_m5_2025, load_m15_2012, load_parquet_utc

ROOT = Path(__file__).resolve().parent.parent
DATA = Path(os.getenv("XAU_DATA_DIR", ROOT / "data" / "research"))
TD = DATA / "eksternal" / "twelvedata_m5" / "XAUUSD_20260916_20261003.parquet"
OUT = ROOT / "docs" / "eksternal" / "hasil_martingale_ea.txt"

SPREAD = 0.20      # XAUUSDc 2021–2025 $0,16–0,20 (research.exness.spread_table)
USC = 100.0        # USC per $1 gerak per lot
MODAL = 43_000.0   # USC = $430
LEV = 2000.0
SPLIT = pd.Timestamp("2021-10-01", tz="UTC")

VARIAN = [
    # nama, arah (1 BUY saja, 0 dua arah ikut candle terakhir), lot0, mult, step $, tp $, maks layer
    ("A screenshot: BUY 0,5 lot x1,2 jarak $1,5 TP +$5 maks 20", 1, 0.5, 1.2, 1.5, 5.0, 20),
    ("B sama, maks 30 layer", 1, 0.5, 1.2, 1.5, 5.0, 30),
    ("C sama, dua arah", 0, 0.5, 1.2, 1.5, 5.0, 20),
    ("D x1,2 jarak $3 TP +$5 maks 20", 1, 0.5, 1.2, 3.0, 5.0, 20),
    ("E klaim x2: 0,05 lot jarak $1,5 TP +$3 maks 20", 1, 0.05, 2.0, 1.5, 3.0, 20),
    ("F x2: 0,05 lot jarak $3 TP +$3 maks 20", 1, 0.05, 2.0, 3.0, 3.0, 20),
    ("G x2: 0,01 lot jarak $3 TP +$3 maks 20", 1, 0.01, 2.0, 3.0, 3.0, 20),
]


def load() -> pd.DataFrame:
    a = load_m15_2012(DATA / "ejtraderLabs_historical-data/XAUUSD")
    b = load_m5_2020(DATA / "ilahuerta-IA_backtrader-pullback-window-xauusd/data/XAUUSD_5m_5Yea.csv")
    c = load_m5_2025(DATA / "dineshelumalai007_xauusd-5m/gold_m5_historical.csv")
    parts = [a[a.index < b.index[0]], b[b.index < c.index[0]], c]
    if TD.exists():
        d = load_parquet_utc(TD)
        wd, hr = d.index.dayofweek, d.index.hour   # Twelve Data juga memuat kuotasi akhir pekan → buang
        d = d[~((wd == 5) | ((wd == 4) & (hr >= 21)) | ((wd == 6) & (hr < 22)))]
        parts.append(d[d.index > c.index[-1]])
    df = pd.concat(parts)
    df.index = df.index.as_unit("ns")
    return df


_ARR: dict = {}


def arrays(df: pd.DataFrame) -> tuple:
    if id(df) not in _ARR:
        _ARR.clear()
        _ARR[id(df)] = tuple(df[k].to_numpy().tolist() for k in ("open", "high", "low", "close"))
    return _ARR[id(df)]


def lot_table(lot0: float, mult: float, n: int, rek: bool = False) -> list[float]:
    """rek=True: lot berikut = round(lot sebelumnya x mult, 2) — cocok dengan deal Signal Strike (0,07 → 1,24 di L17)."""
    if not rek:
        return [round(lot0 * mult ** i, 2) for i in range(n)]
    out = [lot0]
    while len(out) < n:
        out.append(round(out[-1] * mult + 1e-9, 2))
    return out


def sim(df: pd.DataFrame, side: int, lot0: float, mult: float, step: float, tp: float, maxlay: int,
        modal: float = MODAL, rek: bool = False, i0: int = 1, i1: int | None = None, stop: bool = False,
        one: bool = False, info: list | None = None, jeda_menit: float = 0.0):
    """Jalankan EA dari bar i0 s/d i1; stop=True berhenti di akun habis pertama (uji tanggal mulai);
    one=True hanya satu keranjang (TP atau akun habis). info (opsional) diisi per keranjang:
    (indeks bar, layer, ekuitas terendah USC, hasil USC, profit tiap layer terbaru→terlama atau None bila habis).
    jeda_menit > 0: keranjang baru baru dibuka di bar pertama setelah jeda (EA lebih selektif; entry tetap acak)."""
    o, h, l, c = arrays(df)
    t = df.index
    lots_tab = lot_table(lot0, mult, maxlay, rek)
    closes, ruins, depth = [], [], []      # (indeks bar, profit USC) / indeks bar / layer per keranjang
    st = dict(bal=modal, d=1, n=0, sl=0.0, sc=0.0, last=0.0, used=0.0, done=False, mineq=modal, ent=[], idle=0)
    tn = t.asi8 if jeda_menit else None
    jeda_ns = int(jeda_menit * 60e9)

    def open_basket(p: float, i: int) -> None:
        d = side if side else (1 if c[i - 1] >= o[i - 1] else -1)
        x = d * p
        st.update(d=d, n=1, sl=lots_tab[0], sc=lots_tab[0] * (x + SPREAD), last=x,
                  used=lots_tab[0] * USC * p / LEV, mineq=st["bal"], ent=[x + SPREAD])

    def seg(a: float, b: float, i: int, gap: bool) -> None:
        while not st["done"] and st["n"]:
            d = st["d"]
            xa, xb = d * a, d * b
            if xb < xa:                                   # melawan posisi
                while st["n"] < maxlay and st["last"] - step >= xb:
                    lvl = xb if gap else st["last"] - step
                    lot = lots_tab[st["n"]]
                    eq = st["bal"] + USC * (st["sl"] * lvl - st["sc"])
                    need = lot * USC * abs(lvl) / LEV
                    if eq - st["used"] < need:
                        break                             # free margin kurang → layer ditolak
                    st["n"] += 1
                    st["sl"] += lot
                    st["sc"] += lot * (lvl + SPREAD)
                    st["used"] += need
                    st["last"] = lvl
                    st["ent"].append(lvl + SPREAD)
                    if gap:
                        break
                eq = st["bal"] + USC * (st["sl"] * xb - st["sc"])
                st["mineq"] = min(st["mineq"], eq)
                if eq <= 0:
                    ruins.append(i)
                    depth.append(st["n"])
                    if info is not None:
                        info.append((i, st["n"], st["mineq"], -st["bal"], None))
                    st["done"] = one
                    st["bal"] = modal
                    if jeda_ns:
                        st.update(n=0, idle=tn[i] + jeda_ns)
                    else:
                        open_basket(b, i)
                return
            tpx = st["sc"] / st["sl"] + tp
            if xb < tpx:
                return
            px = xb if gap else tpx
            st["bal"] += USC * (st["sl"] * px - st["sc"])
            gain = st["bal"] - modal
            closes.append((i, gain))
            depth.append(st["n"])
            if info is not None:
                info.append((i, st["n"], st["mineq"], gain,
                             [lots_tab[k] * USC * (px - e) for k, e in reversed(list(enumerate(st["ent"])))]))
            st["done"] = one
            st["bal"] = modal                             # kelebihan ditarik (bisa negatif kecil karena spread)
            a = d * px
            if jeda_ns:
                st.update(n=0, idle=tn[i] + jeda_ns)
                return
            open_basket(a, i)
            if gap:
                return

    open_basket(o[i0], i0)
    for i in range(i0, i1 or len(o)):
        if jeda_ns and not st["n"] and not st["done"] and tn[i] >= st["idle"]:
            open_basket(o[i], i)
        if i > i0:
            seg(c[i - 1], o[i], i, True)
        pts = (o[i], l[i], h[i], c[i]) if c[i] >= o[i] else (o[i], h[i], l[i], c[i])
        for k in range(3):
            seg(pts[k], pts[k + 1], i, False)
        if (stop and ruins) or st["done"]:
            break
    cl = pd.DataFrame(closes, columns=["i", "usc"]).astype({"i": int, "usc": float})
    cl["t"] = t[cl.i]
    return cl, t[ruins], np.array(depth), st


def keranjang(df: pd.DataFrame, v: tuple, starts: pd.DatetimeIndex, cap_days: int = 60) -> pd.DataFrame:
    """Satu keranjang per waktu mulai (akun $430 baru): TP, akun habis, atau masih terbuka setelah cap_days."""
    t = df.index
    idx = np.unique(t.searchsorted(starts))
    rows = []
    for i0 in idx[(idx >= 1) & (idx < len(t) - 1)]:
        i1 = int(t.searchsorted(t[i0] + pd.Timedelta(days=cap_days)))
        cl, ruins, depth, _ = sim(df, *v[1:], i0=int(i0), i1=i1, one=True)
        hasil = "habis" if len(ruins) else ("tp" if len(cl) else "terbuka")
        end = ruins[0] if len(ruins) else (cl.t.iloc[0] if len(cl) else t[min(i1, len(t)) - 1])
        modal = v[7] if len(v) > 7 else MODAL
        rows.append(dict(t=t[i0], hasil=hasil, jam=(end - t[i0]).total_seconds() / 3600,
                         usd=cl.usc.sum() / 100 if len(cl) else (-modal / 100 if len(ruins) else 0.0),
                         layer=int(depth[0]) if len(depth) else 0, akhir=end, modal=modal / 100))
    return pd.DataFrame(rows)


def ringkas_keranjang(k: pd.DataFrame, lab: str) -> str:
    if k.empty:
        return f"  {lab}: -"
    p = (k.hasil == "habis").mean()
    win = k[k.hasil == "tp"]
    ev = (1 - p) * win.usd.mean() - p * k.modal.iloc[0]
    satu = f"1 dari {1 / p:5.0f}" if p else "tidak ada"
    return (f"  {lab:26s} n {len(k):5d} | akun habis {100 * p:4.1f}% ({satu} keranjang) | untung rata ${win.usd.mean():5.1f}"
            f" | durasi median {k.jam.median():4.1f} jam | layer ≥10: {100 * (k.layer >= 10).mean():4.1f}% | nilai "
            f"harapan/keranjang ${ev:+6.2f} | masih terbuka {100 * (k.hasil == 'terbuka').mean():.1f}%")


def ringkas(name: str, cl: pd.DataFrame, ruins: pd.DatetimeIndex, t0: pd.Timestamp, t1: pd.Timestamp) -> str:
    """Jalan terus dengan setor ulang $430 seketika setiap akun habis (bisa beruntun saat crash)."""
    rows = []
    for lab, a, b in (("LAMA <Okt21", t0, SPLIT), ("BARU Okt21+", SPLIT, t1), ("SEMUA", t0, t1)):
        x = cl[(cl.t >= a) & (cl.t < b)]
        r = ruins[(ruins >= a) & (ruins < b)]
        prof = x.usc.sum() / 100
        rows.append(f"  {lab:12s} ditarik +${prof:9,.0f} | akun habis {len(r):4d}x (−${len(r) * 430:9,.0f}) | bersih "
                    f"${prof - len(r) * 430:+10,.0f}")
    return name + "\n" + "\n".join(rows)


def mulai(df: pd.DataFrame, v: tuple, starts: pd.DatetimeIndex, cap_days: int = 365) -> pd.DataFrame:
    """Akun baru $430 di tiap tanggal mulai; jalan sampai akun habis pertama atau cap_days."""
    t = df.index
    rows = []
    for s0 in starts:
        i0 = max(int(t.searchsorted(s0)), 1)
        i1 = int(t.searchsorted(s0 + pd.Timedelta(days=cap_days)))
        if i0 >= len(t) - 1:
            continue
        cl, ruins, _, _ = sim(df, *v[1:], i0=i0, i1=i1, stop=True)
        end = ruins[0] if len(ruins) else t[min(i1, len(t)) - 1]
        rows.append(dict(t=t[i0], habis=len(ruins) > 0, hari=(end - t[i0]).total_seconds() / 86400,
                         tarik=cl.usc.sum() / 100, modal=(v[7] if len(v) > 7 else MODAL) / 100))
    return pd.DataFrame(rows)


def ringkas_mulai(m: pd.DataFrame, lab: str) -> str:
    if m.empty:
        return f"  {lab}: -"
    pct = lambda d: 100 * ((m.hari <= d) & m.habis).mean()  # noqa: E731
    bersih = m.tarik - m.modal * m.habis
    return (f"  {lab:24s} n {len(m):3d} | habis ≤30 hari {pct(30):3.0f}% ≤90 hari {pct(90):3.0f}% ≤1 th {pct(365):3.0f}% | "
            f"umur median {m.hari.median():5.0f} hari | ditarik median ${m.tarik.median():6,.0f} | bersih rata ${bersih.mean():+6,.0f} (median "
            f"${bersih.median():+5,.0f})")


def main() -> None:
    df = load()
    t0, t1 = df.index[0], df.index[-1]
    out = [f"Data {t0:%Y-%m-%d} s/d {t1:%Y-%m-%d %H:%M} UTC, {len(df):,} bar. Modal $430 dijaga, spread ${SPREAD}.",
           "Hitungan klaim 'x2 sampai 20 layer' (lot XAUUSDc; 1 lot = $1 per $1 gerak):"]
    for l0 in (0.01, 0.05, 0.5):
        lots = [l0 * 2 ** k for k in range(20)]
        for s in (1.5, 3.0):
            flo = sum(lot * (19 - k) * s for k, lot in enumerate(lots)) * USC / 100
            out.append(f"  mulai {l0:4.2f} lot jarak ${s}: layer 20 = {lots[-1]:9,.2f} lot, total {sum(lots):9,.2f} lot "
                       f"(${sum(lots):,.0f} per $1), rugi mengambang saat layer 20 terisi ${flo:,.0f}, margin "
                       f"1:2000 ±${sum(lots) * 4150 * USC / LEV / 100:,.0f}")
    lots12 = [round(0.5 * 1.2 ** k, 2) for k in range(30)]
    for n in (8, 20, 30):
        flo = sum(lot * (n - 1 - k) * 1.5 for k, lot in enumerate(lots12[:n])) * USC / 100
        out.append(f"  x1,2 mulai 0,5 lot jarak $1,5, {n} layer: total {sum(lots12[:n]):6.2f} lot, rentang "
                   f"${(n - 1) * 1.5:.1f}, rugi mengambang ${flo:,.0f}; tiap $1 turun lagi −${sum(lots12[:n]):.2f}")
    out.append("")
    bulanan = pd.date_range(pd.Timestamp("2012-06-01", tz="UTC"), t1, freq="MS")
    pekanan = pd.date_range(t1 - pd.Timedelta(days=365), t1, freq="W-MON")
    for v in VARIAN:
        cl, ruins, depth, st = sim(df, *v[1:])
        out.append(ringkas(v[0], cl, ruins, t0, t1))
        out.append(f"  keranjang {len(cl):,}, layer maks terpakai {depth.max()}, akun habis terakhir: "
                   + ", ".join(f"{r:%Y-%m-%d}" for r in ruins[-4:]))
        th = cl.groupby(cl.t.dt.year).usc.sum() / 100
        rh = pd.Series(1, index=ruins).groupby(ruins.year).sum()
        out.append("  per tahun (ditarik $ / habis x): " + " ".join(
            f"{y}:{th.get(y, 0):,.0f}/{int(rh.get(y, 0))}" for y in sorted(set(th.index) | set(rh.index))))
        m = mulai(df, v, bulanan)
        out.append("  Akun baru tiap awal bulan (maks 1 tahun):")
        out.append(ringkas_mulai(m[m.t < SPLIT], "mulai LAMA <Okt21"))
        out.append(ringkas_mulai(m[m.t >= SPLIT], "mulai BARU Okt21+"))
        out.append(ringkas_mulai(mulai(df, v, pekanan), "tiap Senin 12 bln terakhir"))
        k = keranjang(df, v, pd.date_range(t0.ceil("D"), t1, freq="6h"))
        out.append("  Satu keranjang tiap 6 jam (tidak bergantung aturan entry EA):")
        out.append(ringkas_keranjang(k[k.t < SPLIT], "LAMA <Okt21"))
        out.append(ringkas_keranjang(k[k.t >= SPLIT], "BARU Okt21+"))
        out.append(ringkas_keranjang(k[k.t >= t1 - pd.Timedelta(days=365)], "12 bln terakhir"))
        if v is VARIAN[0]:
            okt = keranjang(df, v, pd.date_range(pd.Timestamp("2026-10-02", tz="UTC"), periods=24, freq="h"))
            out.append("  Keranjang BUY yang dibuka tiap jam pada 2 Okt 2026 (NFP 12:30 UTC):")
            out += ["    " + "  ".join(f"{r.t:%H}→{r.hasil}{'' if r.hasil == 'terbuka' else f' {r.akhir:%H:%M}'}"
                                         f"/{r.layer}L/${r.usd:+.0f}" for r in okt.iloc[k:k + 6].itertuples())
                    for k in range(0, len(okt), 6)]
            i0 = int(df.index.searchsorted(pd.Timestamp("2026-09-17", tz="UTC")))
            cl, ruins, _, st = sim(df, *v[1:], i0=i0)
            out.append(f"  EA selalu aktif sejak 17 Sep 2026 (setor ulang tiap habis): ditarik ${cl.usc.sum() / 100:,.0f}, "
                       f"akun habis {len(ruins)}x: " + ", ".join(f"{r:%d/%m %H:%M}" for r in ruins))
        out.append("")
        print("\n".join(out[-18:]), flush=True)
    OUT.write_text("\n".join(out) + "\n")
    print("\n".join(out[:12]))
    print("->", OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
