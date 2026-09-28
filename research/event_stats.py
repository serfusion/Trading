"""Basis pengetahuan statistik berita untuk chat aplikasi (python -m research.event_stats).

Menulis cloud/api/pengetahuan.md: reaksi XAU/USD (M15, 2012-2026) & BTC/USD (H1, 2016-2026) terhadap rilis berita
AS high-impact dari kalender ForexFactory historis (research/news_data.py, dengan actual & forecast), dipisah per
jenis berita, arah kejutan (actual vs forecast, dilihat dari sisi emas) dan besar kejutan; FOMC dipisah sesuai
ekspektasi vs kejutan. Ditambah performa sinyal 💰 di sekitar berita dan ringkasan riset filter.

Semua angka = frekuensi historis (bukan jaminan). Setiap sel menyertakan n (jumlah kejadian).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .data import resample
from .eksternal import asset
from .news_data import load_calendar
from .run_scan import DATA, dataset

OUT = Path(__file__).resolve().parent.parent / "cloud" / "api" / "pengetahuan.md"
PRIORITY = ["FOMC", "NFP", "CPI", "PCE", "GDP", "PPI", "RETAIL", "ISM", "CLAIMS"]
MAIN_EVENT = {"NFP": ["Non-Farm Employment Change"], "CPI": ["Core CPI m/m", "CPI m/m"],
              "PPI": ["Core PPI m/m", "PPI m/m"], "RETAIL": ["Core Retail Sales m/m", "Retail Sales m/m"],
              "PCE": ["Core PCE Price Index m/m"], "GDP": ["Advance GDP q/q"],
              "ISM": ["ISM Manufacturing PMI", "ISM Services PMI"], "CLAIMS": ["Unemployment Claims"],
              "FOMC": ["Federal Funds Rate"]}
NAMA = {"NFP": "NFP (Non-Farm Payrolls)", "CPI": "CPI (inflasi konsumen)", "PPI": "PPI (inflasi produsen)",
        "RETAIL": "Retail Sales", "PCE": "Core PCE", "GDP": "GDP awal", "ISM": "ISM PMI",
        "CLAIMS": "Unemployment Claims (mingguan)", "FOMC": "FOMC (suku bunga Fed)"}
WIN = {"15m": 1, "1j": 4, "4j": 16, "1h": 96}          # jumlah candle M15 sejak open candle rilis


def xau_m15() -> pd.DataFrame:
    a = dataset("m15_2012")[0]
    b = resample(dataset("m5_2020")[0], "15min")
    c = resample(dataset("m5_2025")[0], "15min")
    df = pd.concat([a, b[b.index > a.index[-1]]])
    return pd.concat([df, c[c.index > df.index[-1]]])


def _num(s) -> float:
    from .news_data import _num as n
    return n(s)


def releases(cal: pd.DataFrame) -> pd.DataFrame:
    """Satu baris per waktu rilis: grup utama, bias emas (+1 kejutan bagus utk emas), besar kejutan relatif."""
    cal = cal[cal.group.isin(PRIORITY)].copy()
    cal["surp"] = cal.actual.map(_num) - cal.forecast.map(_num)
    rows = []
    for t, g in cal.groupby("time"):
        grp = min(g.group, key=PRIORITY.index)
        gg = g[g.group == grp]
        main = gg[gg.event.isin(MAIN_EVENT[grp])]
        bias = gg.gold_bias.dropna()
        rows.append({"time": t, "group": grp, "bias": float(np.sign(bias.sum())) if len(bias) else np.nan,
                     "event": main.event.iloc[0] if len(main) else gg.event.iloc[0],
                     "surp": float(main.surp.iloc[0]) if len(main) else np.nan,
                     "actual": main.actual.iloc[0] if len(main) else None,
                     "forecast": main.forecast.iloc[0] if len(main) else None})
    ev = pd.DataFrame(rows)
    # besar kejutan relatif terhadap median |kejutan| grup-event yang sama
    ev["besar"] = False
    for (grp, name), g in ev.groupby(["group", "event"]):
        med = g.surp.abs().replace(0, np.nan).median()
        if med and med == med:
            ev.loc[g.index, "besar"] = g.surp.abs() >= 2 * med
    return ev


def reactions(ev: pd.DataFrame, px: pd.DataFrame, win: dict[str, int], bar: pd.Timedelta) -> pd.DataFrame:
    o, c = px.open.to_numpy(), px.close.to_numpy()
    idx = px.index
    out = []
    for e in ev.itertuples():
        i = idx.searchsorted(e.time, side="right") - 1
        if i < 1 or not (idx[i] <= e.time < idx[i] + bar) or i + max(win.values()) >= len(px):
            continue
        base = o[i]
        row = {"time": e.time}
        for k, n in win.items():
            row[k] = (c[i + n - 1] - base) / base * 100          # % dari harga saat rilis
        row["lanjut1j"] = np.sign(c[i + 4] - c[i]) == np.sign(c[i] - base) if bar.seconds == 900 else np.nan
        out.append(row)
    return ev.merge(pd.DataFrame(out), on="time")


def _fmt_group(r: pd.DataFrame, keys: list[str], price_now: float) -> list[str]:
    lines = []
    for tag, m in (("Kejutan BAGUS untuk emas (data lemah / dovish)", r.bias > 0),
                   ("Kejutan BURUK untuk emas (data kuat / hawkish)", r.bias < 0),
                   ("Sesuai perkiraan / tanpa angka", ~(r.bias.abs() > 0))):
        g = r[m]
        if len(g) < 5:
            continue
        d = np.where(g.bias.abs() > 0, g.bias, 1.0)
        cells = []
        for k in keys:
            if tag.startswith("Sesuai"):
                cells.append(f"{k}: naik {100 * (g[k] > 0).mean():.0f}%, median |gerak| {g[k].abs().median():.2f}%")
            else:
                s = g[k] * d
                cells.append(f"{k}: searah {100 * (s > 0).mean():.0f}%, rata {s.mean():+.2f}% (≈${s.mean() / 100 * price_now:+.0f})")
        lines.append(f"- {tag} (n={len(g)}): " + "; ".join(cells))
        big = g[g.besar]
        if len(big) >= 5 and not tag.startswith("Sesuai"):
            s = big[keys[1]] * big.bias
            lines.append(f"  - hanya kejutan BESAR (≥2× median, n={len(big)}): {keys[1]} searah {100 * (s > 0).mean():.0f}%, "
                         f"rata {s.mean():+.2f}%")
    if "lanjut1j" in r and r.lanjut1j.notna().any():
        lines.append(f"- Setelah candle 15 menit pertama tutup, 1 jam berikutnya searah candle itu: "
                     f"{100 * r.lanjut1j.astype(float).mean():.0f}% (n={r.lanjut1j.notna().sum()}) → mengejar candle rilis ≈ lempar koin")
    return lines


def fomc_table(ev: pd.DataFrame, r: pd.DataFrame) -> list[str]:
    f = r[r.group == "FOMC"].copy()
    f["a"], f["f"] = f.actual.map(_num), f.forecast.map(_num)
    f = f.dropna(subset=["a", "f"])
    f["prev"] = f.a.shift(1)
    f["jenis"] = np.where(f.a > f.prev + 1e-9, "naik", np.where(f.a < f.prev - 1e-9, "turun", "tetap"))
    f["kejutan"] = np.where(abs(f.a - f.f) > 1e-9, np.where(f.a > f.f, "lebih hawkish", "lebih dovish"), "sesuai")
    lines = [f"Keputusan FOMC dengan angka actual & forecast: n={len(f)} ({f.time.min():%Y}–{f.time.max():%Y}); "
             f"kejutan suku bunga hanya {int((f.kejutan != 'sesuai').sum())} kali — keputusan hampir selalu sudah "
             "diperkirakan pasar (CME FedWatch / konsensus). Yang menggerakkan emas: pernyataan, dot plot, konferensi pers."]
    for (jenis, kej), g in f.groupby(["jenis", "kejutan"]):
        if len(g) < 2:
            lines.append(f"- {jenis}, {kej} (n={len(g)}): {g.time.dt.strftime('%Y-%m-%d').tolist()}")
            continue
        lines.append(f"- Suku bunga {jenis}, {kej} (n={len(g)}): emas 1 jam naik {100 * (g['1j'] > 0).mean():.0f}% "
                     f"(median {g['1j'].median():+.2f}%), 1 hari naik {100 * (g['1h'] > 0).mean():.0f}% "
                     f"(median {g['1h'].median():+.2f}%), median |gerak| 1 jam {g['1j'].abs().median():.2f}%")
    return lines


def money_near_news(cal: pd.DataFrame) -> list[str]:
    a = asset("XAUUSD")
    m = a.money
    ev = np.unique(cal[cal.group.isin(["NFP", "CPI", "FOMC"])].time.to_numpy("datetime64[ns]").astype(np.int64))
    t = m.t.to_numpy("datetime64[ns]").astype(np.int64)
    h = 3600 * 10**9

    def near(lo, hi):
        a_ = np.searchsorted(ev, t + int(lo * h), side="right")
        b_ = np.searchsorted(ev, t + int(hi * h), side="right")
        return b_ > a_
    rows = []
    for tag, mask in (("lahir ≤ 4 jam SESUDAH NFP/CPI/FOMC", near(-4, 0)),
                      ("lahir ≤ 24 jam SEBELUM NFP/CPI/FOMC", near(0, 24)),
                      ("jauh dari berita", ~near(-4, 0) & ~near(0, 24))):
        g = m[mask]
        rows.append(f"- Sinyal XAU 💰 {tag}: n={len(g)}, WR {100 * (g.R > 0).mean():.0f}%, rata {g.R.mean():+.2f}R")
    return rows


def main() -> None:
    cal = load_calendar(DATA)
    ev = releases(cal)
    px = xau_m15()
    price_now = float(px.close.iloc[-1])
    r = reactions(ev, px, WIN, pd.Timedelta(minutes=15))
    btc = asset("BTCUSD").b.df
    rb = reactions(ev, btc, {"1j": 1, "4j": 4, "1h": 24}, pd.Timedelta(hours=1))
    L = ["# Basis pengetahuan statistik (dibuat otomatis oleh research/event_stats.py — jangan disunting manual)",
         "",
         f"Data: kalender ForexFactory historis {ev.time.min():%Y-%m}–{ev.time.max():%Y-%m} (actual vs forecast), "
         f"XAU/USD M15 {px.index[0]:%Y-%m}–{px.index[-1]:%Y-%m}, BTC/USD H1 Bitstamp {btc.index[0]:%Y}–{btc.index[-1]:%Y-%m}. "
         f"Gerak dalam % dari harga saat rilis; perkiraan $ memakai harga emas terakhir ≈ ${price_now:,.0f}. "
         "'searah' = harga bergerak ke arah yang 'seharusnya' menurut kejutan (data AS lebih lemah / Fed lebih dovish → "
         "emas naik; data lebih kuat / hawkish → emas turun). 'rata' dihitung ke arah itu: pada baris kejutan BURUK, "
         "'rata +0,24%' berarti emas rata-rata TURUN 0,24%. Jendela (15m, 1j = 1 jam, 4j, 1h = 1 hari) diukur dari open "
         "candle 15 menit tempat rilis (sudah termasuk lonjakan pertama; orang yang masuk SETELAH rilis tidak mendapat "
         "gerak candle pertama, dan spread saat rilis melebar).",
         "", "## 1. Reaksi XAU/USD per jenis berita", ""]
    for grp in PRIORITY:
        g = r[r.group == grp]
        if len(g) < 10:
            continue
        L.append(f"### {NAMA[grp]} — {len(g)} rilis")
        L += _fmt_group(g, ["15m", "1j", "4j", "1h"], price_now)
        L.append("")
    L += ["### FOMC — keputusan vs ekspektasi", *fomc_table(ev, r), "",
          "## 2. Reaksi BTC/USD terhadap berita AS yang sama (H1)",
          "'searah' untuk BTC = BTC naik setelah data lemah/dovish dan turun setelah data kuat/hawkish (sama seperti emas).",
          ""]
    for grp in ["FOMC", "NFP", "CPI"]:
        g = rb[rb.group == grp]
        if len(g) < 10:
            continue
        L.append(f"### {NAMA[grp]} — {len(g)} rilis (BTC)")
        L += _fmt_group(g, ["1j", "4j", "1h"], float(btc.close.iloc[-1]))
        L.append("")
    L += ["## 3. Sinyal 💰 bot di sekitar berita (XAU, 2013–2026)", *money_near_news(cal), "",
          "## 4. Ringkasan riset filter (docs/RISET_DATA_EKSTERNAL.md)", *KESIMPULAN, "",
          "## 5. Cara kerja sinyal bot (untuk menjelaskan ke pengguna)", *CARA_KERJA, ""]
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"ditulis {OUT} ({len(r)} rilis XAU, {len(rb)} rilis BTC, {len(OUT.read_text())} karakter)")


CARA_KERJA = [
    "- Sistem trend H1: 3 set Donchian (breakout 40/55/80 candle, keluar 15/20/30). SL = 3 × ATR(20); tiap sinyal "
    "5 posisi: posisi #1 TP1 = 1R, sisanya ditahan sampai sinyal TUTUP; setelah TP1 SL sisa pindah ke entry (SL+).",
    "- Kategori: konf+⭐ (searah EMA50/200, supertrend, momentum 60 hari DAN tren D1 + breakout H4), konf, ⭐, biasa. "
    "Hanya kategori ber-💰 yang dikirim. Statistik historis per sinyal (WR / rata-rata R / n): XAU konf+⭐ 49,2% / "
    "+0,31R / 850; XAU konf 48,1% / +0,09R / 335; BTC ⭐ 49,5% / +0,68R / 382; BTC konf+⭐ 47,8% / +0,31R / 811; "
    "BTC konf 48,1% / +0,23R / 430. Gap pekan forex (AUD/USD, USD/JPY, EUR/JPY, AUD/JPY, EUR/CHF): WR 74–90%, "
    "+0,10 s/d +0,26R.",
    "- 1R = rugi bila kena SL awal. WR rendah itu normal untuk trend-following: banyak rugi kecil, sedikit untung besar.",
]

KESIMPULAN = [
    "- Uji ±70 varian filter per aset (berita, yield riil, dolar, COT, sesi, GVZ/VIX, yield 2 th, musiman) "
    "dengan kriteria latih/uji ketat: untuk XAU 💰 TIDAK ADA yang konsisten. Sinyal 💰 XAU yang lahir sesudah berita "
    "justru lebih baik (berita memicu breakout).",
    "- BTC 💰: dua filter konsisten dan dipasang di cloud: (a) lewati BUY saat funding Binance 24 jam di 10% "
    "tertinggi setahun, lewati SELL saat di 10% terendah (short squeeze); (b) lewati sinyal di bulan September "
    "(11 dari 11 tahun rugi, rata-rata −0,43R).",
    "- XAU: saat volatilitas tersirat emas (GVZ, FRED GVZCLS) naik dalam 5 hari terakhir, sinyal 💰 rata-rata +0,04R "
    "(WR 45,5%, n=506) vs +0,40R (WR 51,4%, n=679) saat tidak naik; tetapi hanya 8 dari 14 tahun searah → informasi, "
    "bukan filter.",
    "- Scalping berita (ikut/lawan candle rilis) diuji 2012–2026: tidak ada yang positif konsisten setelah spread.",
    "- SL+ bertangga (mis. 2R→SL 1R, 3R→SL 2R), TP2/TP3 bertingkat, dan trailing ATR diuji pada sinyal 💰 "
    "(research/sl_tangga.py): WR hanya naik ≤1 poin tetapi profit per sinyal turun 12–32% (XAU) dan 35–51% (BTC). "
    "Skema bawaan (TP1 1R untuk 1 posisi, 4 posisi jalan, SL+ setelah TP1) tetap yang terbaik di antara itu. "
    "Tanpa TP1 (5 posisi jalan) total lebih besar tetapi WR turun ke 34–37%.",
    "- Hasil masa lalu bukan jaminan; WR sinyal trend memang rendah (≈45–50%) dan profit datang dari sedikit trend besar.",
]


if __name__ == "__main__":
    main()
