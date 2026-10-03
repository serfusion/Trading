"""Risiko bangkrut EA martingale XAU/USD (lot x2 per layer, 20+ layer) — python -m research.martingale_ruin

Pertanyaan proyek: masuk akalkah klaim EA martingale XAU (lot dikali 2 tiap layer, sampai 20+ layer, dijalankan di
VPS) yang "menghasilkan ±$150 per akun"? Skrip ini TIDAK menjalankan kode EA mana pun; aturannya ditulis ulang:

EA (satu arah per siklus): buka 0,01 lot (BUY, atau SELL untuk pembanding). Tiap harga melawan sejauh G dolar dari
layer terakhir, buka layer baru dengan lot x2 (0,01; 0,02; 0,04; ...) sampai MAKS layer. Semua posisi ditutup saat
harga BID mencapai harga rata-rata tertimbang (harga ASK saat masuk) + T dolar (TP keranjang). Tanpa SL (umum pada EA
semacam ini). Siklus baru dimulai di open candle berikutnya.

Bagian 1 (tabel statis): lot, lot kumulatif, rugi mengambang, margin (1:100/1:500/1:2000) dan modal minimum per layer.
Bagian 2 (sejarah): EA diputar candle M5 XAU Agu 2020 – Sep 2026 dengan modal TAK TERBATAS (hanya dibatasi MAKS layer)
   → daftar siklus: laba saat TP, rugi mengambang terdalam, kebutuhan equity untuk margin layer berikutnya.
   Urutan di dalam candle: candle naik O→L→H→C, candle turun O→H→L→C. Gap: layer diisi di harga open.
Bagian 3 (Monte Carlo): akun dengan modal D mengikuti siklus itu (titik mulai acak di sejarah, dan bootstrap siklus
   acak) sampai (a) laba kumulatif >= $150 = "klaim tercapai", atau (b) akun habis: equity + rugi mengambang <= 0
   (stop out Exness 0%) ATAU equity tidak cukup untuk margin layer berikutnya (EA macet di layer terdalam tanpa
   jalan keluar — dihitung gagal). Juga peluang akun habis dalam 1 tahun bila EA terus dijalankan.
Biaya: spread $0,20 per layer (median XAUUSDc Exness 2021–25 = $0,16–0,20). Swap & komisi diabaikan (menguntungkan EA).
Satuan uang = USD akun standar; akun Cent: bagi semua angka lot/uang dengan 100 (rasio modal/lot yang menentukan).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "research"
OUT = ROOT / "docs" / "eksternal" / "hasil_martingale_ruin.txt"

LOT0 = 0.01
OZ = 100.0                 # 1 lot XAU = 100 oz → $1 gerak harga = $1 per 0,01 lot
SPREAD = 0.20
LEVS = (100, 500, 2000)
TARGET = 150.0
TP = 1.0                   # TP keranjang: $1 di atas harga rata-rata
DEPOSITS = (1000.0, 3000.0, 10000.0, 50000.0)   # $3.000 = patokan memo "Write a verdict on the claim"
RUNS = 1000
PRICE_REF = 4200.0         # harga emas kira-kira Okt 2026 untuk tabel statis
MAX_LOT_ORDER = 200.0      # batas lot per order akun Standard Exness (Cent: 200 lot cent)


def layer_table(g: float, n: int, mult: float = 2.0, price: float = PRICE_REF) -> pd.DataFrame:
    """Per layer k: lot, lot kumulatif, jarak melawan dari layer 1, rugi mengambang SAAT harga mencapai layer k+1
    (sebelum layer k+1 dibuka), margin terpakai, jarak balik yang dibutuhkan untuk TP impas (T=0)."""
    rows = []
    lots, entries = [], []
    for k in range(1, n + 1):
        lots.append(LOT0 * mult ** (k - 1))
        entries.append(-(k - 1) * g)          # harga relatif terhadap layer 1 (arah BUY)
        L = np.array(lots)
        E = np.array(entries)
        cum = L.sum()
        nxt = -k * g
        loss = float((L * OZ * (nxt - E)).sum()) - cum * OZ * SPREAD
        avg = float((L * E).sum() / cum)
        row = dict(layer=k, lot=lots[-1], lot_kum=cum, jarak_melawan=(k - 1) * g,
                   rugi_di_layer_berikut=loss, balik_untuk_impas=avg + SPREAD - E[-1])
        for lev in LEVS:
            m = cum * OZ * price / lev
            row[f"margin_1:{lev}"] = m
            row[f"modal_min_1:{lev}"] = -loss + m      # bertahan sampai harga layer k+1 DAN bisa membuka margin-nya
        rows.append(row)
    return pd.DataFrame(rows)


def load_m5() -> pd.DataFrame:
    """XAU M5: ilahuerta (Agu 2020 – Apr 2025) + dineshelumalai (Apr 2025 – Sep 2026, jam server MT5)."""
    a = pd.read_csv(DATA / "ilahuerta-IA_backtrader-pullback-window-xauusd" / "data" / "XAUUSD_5m_5Yea.csv")
    a.index = pd.to_datetime(a.Date.astype(str) + " " + a.Time)
    a = a.rename(columns=str.lower)[["open", "high", "low", "close"]]
    b = pd.read_csv(DATA / "dineshelumalai007_xauusd-5m" / "gold_m5_historical.csv", index_col=0, parse_dates=True)
    b = b[["open", "high", "low", "close"]]
    cut = b.index[0]
    df = pd.concat([a[a.index < cut], b]).sort_index()
    return df[~df.index.duplicated()]


def cycles(df: pd.DataFrame, g: float, t: float, nmax: int, side: int = 1) -> pd.DataFrame:
    """Putar EA dengan modal tak terbatas. side=+1 BUY, -1 SELL (harga dicerminkan). Satu baris per siklus selesai."""
    o, h, l, c = (df[x].to_numpy(float) * side for x in ("open", "high", "low", "close"))
    if side < 0:
        h, l = l, h
    idx = df.index
    price_lev = df.close.to_numpy(float)
    out = []
    n = len(o)
    i = 0
    while i < n:
        lots = [LOT0]
        cum, wsum = LOT0, LOT0 * (o[i] + SPREAD)
        last = o[i]
        worst = 0.0
        req = {lev: LOT0 * OZ * abs(price_lev[i]) / lev for lev in LEVS}
        t0 = idx[i]
        done = False
        j = i
        while j < n and not done:
            path = (o[j], l[j], h[j], c[j]) if c[j] >= o[j] else (o[j], h[j], l[j], c[j])
            for q, p in enumerate(path):
                # isi layer selama harga melawan G dari layer terakhir (gap di open → isi di harga open)
                while len(lots) < nmax and p <= last - g:
                    lvl = p if q == 0 and p < last - g else last - g
                    fl = cum * OZ * lvl - wsum * OZ          # rugi mengambang tepat sebelum layer dibuka
                    lot = lots[-1] * 2.0
                    lots.append(lot)
                    cum += lot
                    wsum += lot * (lvl + SPREAD)
                    last = lvl
                    worst = min(worst, fl)
                    for lev in LEVS:                         # equity harus menutup rugi + margin setelah dibuka
                        req[lev] = max(req[lev], -fl + cum * OZ * abs(price_lev[j]) / lev)
                fl = cum * OZ * p - wsum * OZ
                worst = min(worst, fl)
                for lev in LEVS:
                    req[lev] = max(req[lev], -fl)
                if p >= wsum / cum + t:
                    profit = cum * OZ * t
                    out.append((t0, idx[j], len(lots), cum, profit, -worst, req[100], req[500], req[2000]))
                    done = True
                    break
            j += 1
        if not done:
            break                      # siklus terakhir belum selesai saat data habis
        i = j
    return pd.DataFrame(out, columns=["t0", "t1", "layer", "lot_kum", "laba", "rugi_terdalam",
                                      "butuh_1:100", "butuh_1:500", "butuh_1:2000"])


def _run(need: np.ndarray, prof: np.ndarray, t1: np.ndarray, s: int, dep: float, days: float | None,
         target: float | None) -> tuple[str, float, float]:
    """Akun modal `dep` mulai siklus ke-s (urutan sejarah). Habis bila kebutuhan equity siklus >= equity saat itu.
    Berhenti di target laba atau setelah `days` hari. Kembali (status, laba/rugi, hari)."""
    end = len(need) if days is None else int(np.searchsorted(t1, t1[s] + days * 86400, side="right"))
    end = max(end, s + 1)
    nd, gain = need[s:end], np.cumsum(prof[s:end])
    eq_before = dep + np.concatenate(([0.0], gain[:-1]))
    bust = np.flatnonzero(nd >= eq_before)
    kb = bust[0] if len(bust) else len(nd)
    if target is not None:
        hit = np.flatnonzero(gain >= target)
        if len(hit) and hit[0] < kb:
            return "target", float(gain[hit[0]]), (t1[s + hit[0]] - t1[s]) / 86400
    if kb < len(nd):
        return "habis", -dep, (t1[s + kb] - t1[s]) / 86400
    return "jalan", float(gain[-1]), (t1[end - 1] - t1[s]) / 86400


def monte_carlo(cyc: pd.DataFrame, dep: float, lev: int, runs: int = 2000, seed: int = 1) -> dict:
    """Titik mulai acak di sejarah (urutan siklus asli)."""
    rng = np.random.default_rng(seed)
    need = cyc[f"butuh_1:{lev}"].to_numpy()
    prof = cyc.laba.to_numpy()
    t1 = cyc.t1.to_numpy().astype("datetime64[s]").astype(float)
    last_start = int(np.searchsorted(t1, t1[-1] - 366 * 86400))
    starts = rng.integers(0, max(1, last_start), runs)
    tg = [_run(need, prof, t1, s, dep, None, TARGET) for s in starts]
    mo = [_run(need, prof, t1, s, dep, 30.4, None) for s in starts]
    yr = [_run(need, prof, t1, s, dep, 365.25, None) for s in starts]
    hari_target = [x[2] for x in tg if x[0] == "target"]
    return dict(
        p_target=np.mean([x[0] == "target" for x in tg]),
        ev_stop_di_target=float(np.mean([x[1] for x in tg])),
        hari_ke_target=float(np.median(hari_target)) if hari_target else float("nan"),
        p_habis_1bln=np.mean([x[0] == "habis" for x in mo]),
        p_habis_1th=np.mean([x[0] == "habis" for x in yr]),
        laba_1bln_median=float(np.median([x[1] for x in mo])),
        ev_1th=float(np.mean([x[1] for x in yr])),
    )


def per_tahun(cyc: pd.DataFrame, dep: float, lev: int = 2000, runs: int = 400, seed: int = 2) -> pd.DataFrame:
    """Peluang akun habis dalam 1 bulan, dikelompokkan menurut tahun titik mulai (LAMA < Okt 2021 vs BARU)."""
    rng = np.random.default_rng(seed)
    need = cyc[f"butuh_1:{lev}"].to_numpy()
    prof = cyc.laba.to_numpy()
    t1 = cyc.t1.to_numpy().astype("datetime64[s]").astype(float)
    yrs = cyc.t0.dt.year.to_numpy()
    rows = []
    for y in np.unique(yrs):
        idx = np.flatnonzero(yrs == y)
        st = [_run(need, prof, t1, s, dep, 30.4, None) for s in rng.choice(idx, runs)]
        tg = [_run(need, prof, t1, s, dep, None, TARGET) for s in rng.choice(idx, runs)]
        rows.append(dict(tahun=int(y), p_target=np.mean([x[0] == "target" for x in tg]),
                         p_habis_1bln=np.mean([x[0] == "habis" for x in st]),
                         laba_1bln_median=float(np.median([x[1] for x in st]))))
    return pd.DataFrame(rows)


def main() -> None:
    lines = []
    w = lines.append
    w("# Risiko bangkrut EA martingale XAU (lot x2) — research/martingale_ruin.py\n")
    for g in (2.0, 5.0):
        tab = layer_table(g, 22)
        w(f"## Tabel per layer, jarak G = ${g:g}, harga ${PRICE_REF:,.0f}, mulai 0,01 lot")
        cols = ["layer", "lot", "lot_kum", "jarak_melawan", "rugi_di_layer_berikut",
                "margin_1:2000", "modal_min_1:500", "modal_min_1:2000"]
        w(tab[cols].to_string(index=False, float_format=lambda x: f"{x:,.2f}"))
        w("")
    df = load_m5()
    w(f"Data M5: {df.index[0]} s.d. {df.index[-1]} ({len(df):,} candle), {df.close.iloc[0]:.0f} → {df.close.iloc[-1]:.0f}\n")
    rows, depth = [], []
    for side, nm in ((1, "BUY"), (-1, "SELL")):
        for g in (2.0, 5.0, 10.0):
            for nmax in (10, 12, 15, 20):
                cyc = cycles(df, g, TP, nmax, side)
                base = dict(arah=nm, G=g, maks=nmax, siklus=len(cyc), layer_terdalam=int(cyc.layer.max()),
                            p_siklus_ke_maks=float((cyc.layer >= nmax).mean()),
                            rugi_terdalam=float(cyc.rugi_terdalam.max()), laba_total=float(cyc.laba.sum()))
                for dep in DEPOSITS:
                    for lev in (500, 2000):
                        rows.append(dict(base, modal=dep, lev=lev, **monte_carlo(cyc, dep, lev, runs=RUNS)))
                if nmax == 20:
                    per_bln = len(cyc) / ((cyc.t1.iloc[-1] - cyc.t0.iloc[0]).days / 30.4)
                    depth.append(dict(arah=nm, G=g, siklus_per_bulan=per_bln,
                                      **{f">={k}": float((cyc.layer >= k).mean() * per_bln) for k in (5, 8, 10, 12, 15, 20)}))
                print(nm, g, nmax, len(cyc), int(cyc.layer.max()), flush=True)
    res = pd.DataFrame(rows)
    res.to_csv(OUT.with_suffix(".csv"), index=False)
    f2 = lambda x: f"{x:,.2f}"
    w("## Rata-rata jumlah siklus per BULAN yang mencapai >= k layer (maks 20 layer, sejarah M5)")
    w(pd.DataFrame(depth).to_string(index=False, float_format=f2))
    w("")
    w(f"## Monte Carlo: {RUNS} titik mulai acak, TP keranjang ${TP:g} di atas rata-rata, target laba ${TARGET:g}")
    w("p_target = peluang laba $150 tercapai SEBELUM akun habis; ev_stop_di_target = rata-rata hasil bila EA DIMATIKAN")
    w("begitu laba $150 (habis = -modal);")
    w("p_habis_1bln/1th = peluang akun habis dalam 1 bulan / 1 tahun; ev_1th = rata-rata hasil 1 tahun (habis = -modal)\n")
    for side in ("BUY", "SELL"):
        w(f"### Arah {side}, leverage 1:2000")
        sub = res[(res.arah == side) & (res.lev == 2000)]
        w(sub[["G", "maks", "siklus", "layer_terdalam", "p_siklus_ke_maks", "rugi_terdalam", "modal", "p_target",
               "ev_stop_di_target", "hari_ke_target", "p_habis_1bln", "p_habis_1th", "laba_1bln_median", "ev_1th"]]
          .to_string(index=False, float_format=f2))
        w("")
    w("### Per tahun mulai (modal $3.000, 1:2000, maks 20 layer; LAMA = 2020–Sep 2021, BARU = sejak Okt 2021)")
    for side, nm in ((1, "BUY"), (-1, "SELL")):
        for g in (2.0, 5.0):
            w(f"{nm} G ${g:g}")
            w(per_tahun(cycles(df, g, TP, 20, side), 3000.0).to_string(index=False, float_format=f2))
    w("")
    w("### Leverage 1:500 (G $2, BUY)")
    sub = res[(res.arah == "BUY") & (res.lev == 500) & (res.G == 2.0)]
    w(sub[["maks", "modal", "p_target", "ev_stop_di_target", "p_habis_1bln", "p_habis_1th", "ev_1th"]].to_string(index=False, float_format=f2))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
