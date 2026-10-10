"""🌐 Metode global tambahan (10 Okt 2026, "cari lagi metode di seluruh alam semesta") → arah XAU 1–10 dtk setelah rilis.

python -m research.pra_xau_global          → docs/eksternal/hasil_pra_xau_global.txt

Aturan ditetapkan SEBELUM melihat hasil; semua data terbit sebelum t0−1 dtk; arah dipilih di LAMA (< Okt 2021) lalu
dinilai di BARU (≥ Okt 2021); target sama dengan research/pra_xau_semua.py (harga tengah t0−1 → t0+2/3/5/10 dtk).
  ESI30 ESI60  momentum kejutan ekonomi AS (seperti Citi Economic Surprise Index): jumlah kejutan semua rilis berdampak
               tinggi 30 / 60 hari terakhir (+ = data lebih kuat dari konsensus). Literatur: kejutan berautokorelasi →
               rilis berikutnya juga kuat → emas TURUN.
  ESIG         sama tetapi hanya rilis jenis berita yang sama (90 hari).
  COT          posisi spekulan emas CFTC (managed money, indeks persentil 3 tahun): ≥ 80% (ramai beli) / ≤ 20% (ramai jual)
  COT4         perubahan posisi 4 pekan
  USD4 USD24   tren EUR/USD 4 / 24 jam sebelum rilis (EUR/USD naik = dolar melemah)
  USD&EMAS     dolar melemah & emas naik 4 jam (atau sebaliknya) sepakat → arah emas
  KEJ&USD      petunjuk berita teruji & tren dolar sepakat (KEJ dari research/pra_xau_semua.py)
LOLOS = BARU > 55%, n ≥ 30, p < 0,05, LAMA ≥ 52%, Dukascopy searah; plus uji acak permutasi untuk seluruh keluarga.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .news_detik import DATA, NEW

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "eksternal" / "hasil_pra_xau_global.txt"
CACHE = ROOT / "data" / "research" / "eksternal" / "pra_xau_global.parquet"


def sg(v) -> float:
    return 0.0 if v is None or v != v or v == 0 else float(np.sign(v))


def tambah(df: pd.DataFrame) -> pd.DataFrame:
    if CACHE.exists():
        return pd.read_parquet(CACHE)
    from .eksternal_cot import fetch
    from .news_data import load_calendar
    cal = load_calendar(DATA)
    cal = cal[cal.usd_surprise.notna()].sort_values("time")
    cot = fetch("XAUUSD")
    eu = pd.read_parquet(ROOT / "data" / "research" / "eksternal" / "pair_h1" / "EURUSD.parquet")
    eu = eu[eu.high > eu.low]
    rows = []
    for t, g in zip(df.t0, df.grup):
        x = {}
        lalu = cal[(cal.time < t - pd.Timedelta(minutes=5))]
        for hari, nm in ((30, "ESI30"), (60, "ESI60")):
            w = lalu[lalu.time >= t - pd.Timedelta(days=hari)]
            x[nm] = -sg(w.usd_surprise.sum()) if len(w) >= 5 else 0.0
        same = lalu[(lalu.group == g) & (lalu.time >= t - pd.Timedelta(days=90))]
        x["ESIG"] = -sg(same.usd_surprise.sum()) if len(same) else 0.0
        c = cot[cot.available < t]
        if len(c) and c.idx.iloc[-1] == c.idx.iloc[-1]:
            i = c.idx.iloc[-1]
            x["COT"] = 1.0 if i >= 0.8 else -1.0 if i <= 0.2 else 0.0
            x["COT4"] = sg(c.d4.iloc[-1])
        k = eu.index.searchsorted(t - pd.Timedelta(hours=1), side="right") - 1     # H1 terakhir yang SUDAH tutup
        if k >= 24:
            cnow = eu.close.iloc[k]
            x["USD4"] = sg(cnow - eu.close.iloc[k - 4])
            x["USD24"] = sg(cnow - eu.close.iloc[k - 24])
        rows.append(x)
    out = pd.concat([df.reset_index(drop=True), pd.DataFrame(rows)], axis=1)
    h4 = out.H4.fillna(0)
    out["USD&EMAS"] = np.where((out.USD4.fillna(0) != 0) & (out.USD4 == h4), h4, 0.0)
    kej = out.KEJ.fillna(0)
    out["KEJ&USD"] = np.where((kej != 0) & (kej == out.USD4.fillna(0)), kej, 0.0)
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(CACHE)
    return out


FITUR = ["ESI30", "ESI60", "ESIG", "COT", "COT4", "USD4", "USD24", "USD&EMAS", "KEJ&USD"]


def main() -> None:
    import research.pra_xau_semua as s1
    df = tambah(s1.bangun())
    L = ["# 🌐 Metode global tambahan → arah XAU 1–10 dtk setelah rilis", __doc__.split("\n\n")[1], "",
         "Terisi: " + ", ".join(f"{f} {int((df[f].fillna(0) != 0).sum())}" for f in FITUR)]
    asli = list(s1.ARAH_F)
    s1.ARAH_F[:] = FITUR
    try:
        lolos = s1.uji_tunggal(df, L)
        ac = s1.acak(df, 100)
    finally:
        s1.ARAH_F[:] = asli
    L += ["", "## LOLOS"]
    L += [f"   {g} • {f} ({'lanjut' if a > 0 else 'balik'}) • {h} dtk: BARU Exness {e['baru']:.1f}% (n {e['n_baru']}, p "
          f"{e['p_baru']:.3f}), Duka {d['baru']:.1f}%, semua {e['benar']:.1f}%, tahun > 50%: {e['tahun']}"
          for g, f, h, a, e, d in lolos] or ["   TIDAK ADA"]
    L.append(f"\n## UJI ACAK (permutasi {len(ac)}×): kebetulan rata-rata {np.mean(ac):.1f}, 95% ≤ {np.percentile(ac, 95):.0f}; "
             f"sungguhan {len(lolos)} → peluang kebetulan ≥ {len(lolos)}: {np.mean(np.array(ac) >= len(lolos)) * 100:.0f}%")
    # ringkas: rata-rata detik 2–10 untuk SEMUA berita, LAMA & BARU
    L.append("\n## Ringkas SEMUA berita (orientasi teori: + = arah fitur) — rata-rata detik 2/3/5/10, Exness (cadangan Duka)")
    t = pd.DatetimeIndex(df.t0.to_numpy())
    for f in FITUR + ["KEJ"]:
        v = df[f].fillna(0).to_numpy()
        hasil = []
        for h in (2, 3, 5, 10):
            y = df[f"y{h}_XAU_EXNESS"].to_numpy()
            y = np.where(np.isnan(y), df[f"y{h}_XAU"].to_numpy(), y)
            m = (v != 0) & ~np.isnan(y) & (y != 0)
            ok = np.sign(v[m]) == np.sign(y[m])
            hasil.append((ok, t[m]))
        semua = np.concatenate([o for o, _ in hasil])
        lama = np.concatenate([o[tt < NEW] for o, tt in hasil])
        baru = np.concatenate([o[tt >= NEW] for o, tt in hasil])
        L.append(f"   {f:9s} {semua.mean() * 100:5.1f}% (n {len(hasil[2][0])}) • LAMA {lama.mean() * 100:5.1f}% • "
                 f"BARU {baru.mean() * 100:5.1f}%")
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
