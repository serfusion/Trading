"""💥 CPI modal kecil + lot maksimal — SEMUA metode (lanjutan research/cpi_allin.py) → docs/eksternal/hasil_cpi_allin2.txt

python -m research.cpi_allin2

Permintaan pengguna 13 Okt 2026: "sudah diuji metode apapun? hasilnya bagus? kalau bagus pasang … risiko kehilangan modal kecil
dapat diterima selama keuntungan prediksi sebelumnya menutup kerugian; akurasi harus teruji 1–5 detik pertama, terutama CPI".

Tick ASLI Exness XAUUSDc (bid/ask), 126 rilis CPI 2016–2026, modal $100 per rilis (rugi maks $100: margin call / perlindungan
saldo negatif). Grid (ditetapkan sebelum melihat hasil):
  ARAH   kuat (IDX|K+S tutup kertas) | aplikasi (IDX|K) | hanya NAIK | Kalshi m/m saja | KEJAR (tanpa tebakan: masuk SETELAH
         rilis searah gerak mid t0−1→t0+1 dtk; latensi 0,5 dtk) | SEMPURNA (kejutan diketahui; batas atas) | selalu BUY
  MASUK  t0 − 1 / 3 / 10 dtk (KEJAR: t0 + 1,5 dtk)
  KELUAR tutup di detik 2 / 3 / 5 / 10 · "TP cepat": tutup begitu untung ≥ 50% modal, paling lambat detik 5 · "SL 50%": tutup
         bila rugi ≥ 50% modal, selain itu detik 5
  LEV    1:100 / 200 / 500 / 1000 / 2000
Lolos = rata-rata $/rilis > 0 di LAMA (< Okt 2021) DAN BARU, ≥ 60% tahun positif, n ≥ 8 per periode; tetangga (leverage &
detik sebelah) juga positif. Belum termasuk latensi klik manusia & requote (kecuali KEJAR 0,5 dtk).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from . import cpi_detik as C
from .exness import ticks_around

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "eksternal" / "hasil_cpi_allin2.txt"
MODAL = 100.0
LEV = (100, 200, 500, 1000, 2000)
MASUK = (1, 3, 10)
KELUAR = ("d2", "d3", "d5", "d10", "tp50", "sl50")
SPLIT = pd.Timestamp("2021-10-01", tz="UTC")


def arr(tk: pd.DataFrame, t0: pd.Timestamp):
    s = (tk.index - t0).total_seconds().to_numpy()
    return s, tk.bid.to_numpy(), tk.ask.to_numpy()


def sim(a, arah: int, masuk_s: float, keluar: str, lev: int) -> tuple[float, bool] | None:
    """(P/L $, margin call?) untuk satu rilis. a = (detik relatif t0, bid, ask). masuk_s negatif = sebelum rilis."""
    s, bid, ask = a
    i0 = np.searchsorted(s, masuk_s, side="right") - 1          # tick terakhir ≤ waktu masuk
    if i0 < 0 or masuk_s - s[i0] > 30:
        return None
    masuk = ask[i0] if arah > 0 else bid[i0]
    oz = MODAL * lev / masuk
    akhir = {"d2": 2, "d3": 3, "d5": 5, "d10": 10, "tp50": 5, "sl50": 5}[keluar]
    i1 = np.searchsorted(s, akhir, side="left")
    if i1 >= len(s):
        return None
    px = (bid if arah > 0 else ask)[i0 + 1:i1 + 1]
    pl = oz * (px - masuk) * arah
    if not len(pl):
        return None
    if keluar == "tp50":
        k = np.nonzero(pl >= 0.5 * MODAL)[0]
        mc = np.nonzero(pl <= -MODAL)[0]
        if len(mc) and (not len(k) or mc[0] < k[0]):
            return -MODAL, True
        if len(k):
            return float(pl[k[0]]), False
    elif keluar == "sl50":
        k = np.nonzero(pl <= -0.5 * MODAL)[0]
        if len(k):
            return max(-MODAL, float(pl[k[0]])), bool(pl[k[0]] <= -MODAL)
    else:
        if pl.min() <= -MODAL:
            return -MODAL, True
    return max(-MODAL, float(pl[-1])), False


def main() -> None:
    df = C.turunan(C.tabel())
    df = df[df.th >= 2016].reset_index(drop=True)
    tb, ts = C.tetap(df, "IDX|K"), C.tetap(df, "IDX|K+S")
    sempurna = pd.Series(-np.sign(np.where(df.s_core != 0, df.s_core, df.s_mm)), index=df.index)
    kal = pd.Series(-df.mm_K.to_numpy(), index=df.index)
    A = {}
    for i, r in df.iterrows():
        tk = ticks_around("XAUUSDc", r.t0)
        if tk is not None:
            A[i] = arr(tk, r.t0)
    kejar = {}
    for i, a in A.items():                                       # arah gerak mid t0−1 → t0+1 (diketahui di detik 1,5)
        s, b, k = a
        j0, j1 = np.searchsorted(s, -1, side="right") - 1, np.searchsorted(s, 1, side="right") - 1
        if j0 >= 0 and j1 > j0:
            d = (b[j1] + k[j1]) / 2 - (b[j0] + k[j0]) / 2
            kejar[i] = int(np.sign(d)) if abs(d) >= 0.05 else 0
    ARAH = {"kuat": ts, "aplikasi": tb, "hanya NAIK": tb.where(tb > 0, 0), "Kalshi m/m": kal,
            "KEJAR detik 1": pd.Series(kejar).reindex(df.index).fillna(0), "SEMPURNA": sempurna,
            "selalu BUY": pd.Series(1.0, index=df.index)}
    rows = []
    for nama, s_ in ARAH.items():
        for m in ((-1.5,) if nama.startswith("KEJAR") else tuple(-x for x in MASUK)):
            for kel in KELUAR:
                for lev in LEV:
                    out = []
                    for i, a in A.items():
                        g = int(np.sign(s_.get(i, 0)))
                        if not g:
                            continue
                        mm = 1.5 if nama.startswith("KEJAR") else m
                        o = sim(a, g, mm, kel, lev)
                        if o:
                            out.append((df.t0[i], *o))
                    if not out:
                        continue
                    x = pd.DataFrame(out, columns=["t0", "pl", "mc"])
                    lm, bm = x[x.t0 < SPLIT], x[x.t0 >= SPLIT]
                    th = x.groupby(x.t0.dt.year).pl.sum()
                    rows.append({"arah": nama, "masuk": mm, "keluar": kel, "lev": lev, "n_l": len(lm), "n_b": len(bm),
                                 "l": lm.pl.mean() if len(lm) else np.nan, "b": bm.pl.mean() if len(bm) else np.nan,
                                 "benar_l": (lm.pl > 0).mean() * 100 if len(lm) else np.nan,
                                 "benar_b": (bm.pl > 0).mean() * 100 if len(bm) else np.nan,
                                 "mc_l": int(lm.mc.sum()), "mc_b": int(bm.mc.sum()),
                                 "th": (th > 0).mean() * 100, "tot": x.pl.sum()})
    R = pd.DataFrame(rows)
    R["lolos0"] = (R.l > 0) & (R.b > 0) & (R.th >= 60) & (R.n_l >= 8) & (R.n_b >= 8)

    def tetangga(r) -> bool:
        li = LEV.index(r.lev)
        sub = R[(R.arah == r.arah) & (R.masuk == r.masuk)]
        ok = True
        for lv in [LEV[j] for j in (li - 1, li + 1) if 0 <= j < len(LEV)]:
            q = sub[(sub.keluar == r.keluar) & (sub.lev == lv)]
            ok &= bool(len(q) and q.lolos0.iloc[0])
        return ok
    R["lolos"] = [bool(r.lolos0 and tetangga(r)) for r in R.itertuples()]
    L = ["# 💥 CPI modal kecil — semua metode (research/cpi_allin2.py)", __doc__.split("\n\n")[1], "",
         f"Rilis dengan tick: {len(A)} • konfigurasi diuji: {len(R)} • lolos syarat dasar: {int(R.lolos0.sum())} • "
         f"lolos + tetangga: {int(R.lolos.sum())}", ""]
    L.append("## Ringkasan per ARAH (konfigurasi terbaik menurut min(LAMA, BARU) $/rilis)")
    for nama in ARAH:
        sub = R[R.arah == nama].copy()
        sub["skor"] = sub[["l", "b"]].min(axis=1)
        for _, r in sub.sort_values("skor", ascending=False).head(3).iterrows():
            L.append(f"   {nama:14s} masuk {r.masuk:+.1f} dtk keluar {r.keluar:4s} 1:{r.lev:<4} | LAMA n{r.n_l:3} ${r.l:+7.1f} "
                     f"benar {r.benar_l:3.0f}% MC {r.mc_l:2} | BARU n{r.n_b:3} ${r.b:+7.1f} benar {r.benar_b:3.0f}% MC "
                     f"{r.mc_b:2} | tahun + {r.th:3.0f}% | {'✅ LOLOS' if r.lolos else ('lolos dasar' if r.lolos0 else '')}")
    L.append("\n## Semua konfigurasi yang LOLOS (+ tetangga)")
    for _, r in R[R.lolos].sort_values("b", ascending=False).iterrows():
        L.append(f"   {r.arah:14s} masuk {r.masuk:+.1f} keluar {r.keluar:4s} 1:{r.lev:<4} | LAMA ${r.l:+7.1f} (n{r.n_l}, MC {r.mc_l}) "
                 f"| BARU ${r.b:+7.1f} (n{r.n_b}, MC {r.mc_b}) | tahun + {r.th:.0f}%")
    if not R.lolos.any():
        L.append("   (tidak ada)")
    L.append("\n## Pembanding acak: berapa konfigurasi 'selalu BUY' / 'SEMPURNA' yang lolos dasar")
    for nama in ("selalu BUY", "SEMPURNA"):
        sub = R[R.arah == nama]
        L.append(f"   {nama}: {int(sub.lolos0.sum())}/{len(sub)}")
    R.to_csv(ROOT / "docs" / "eksternal" / "hasil_cpi_allin2.csv", index=False, float_format="%.2f")
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__" and len(__import__("sys").argv) == 1:
    main()


def acak(n_acak: int = 20000, seed: int = 7) -> list[str]:
    """Masuk t0−1 dtk (cara pengguna): tebakan vs ARAH ACAK pada rilis yang sama (lempar koin per rilis).

    Dengan rugi dibatasi = modal (perlindungan saldo negatif), arah acak pun bisa positif di leverage besar karena menang
    tidak dibatasi → tebakan baru berarti bila MENGALAHKAN acak. p = peluang acak ≥ hasil tebakan (satu sisi)."""
    df = C.turunan(C.tabel())
    df = df[df.th >= 2016].reset_index(drop=True)
    tebak = {"kuat (aplikasi tanpa ⚠️)": C.tetap(df, "IDX|K+S"), "aplikasi (semua)": C.tetap(df, "IDX|K")}
    tebak["hanya NAIK"] = tebak["aplikasi (semua)"].where(tebak["aplikasi (semua)"] > 0, 0)
    tebak["⚠️ lemah saja"] = tebak["aplikasi (semua)"].where(tebak["kuat (aplikasi tanpa ⚠️)"] == 0, 0)
    A = {i: arr(tk, r.t0) for i, r in df.iterrows() if (tk := ticks_around("XAUUSDc", r.t0)) is not None}
    rng = np.random.default_rng(seed)
    L = ["", "## Masuk t0 − 1 dtk: tebakan vs ARAH ACAK (rilis yang sama; p = peluang acak ≥ tebakan)"]
    for nama, s_ in tebak.items():
        L.append(f"### {nama}")
        for kel in ("d1", "d2", "d3", "d5"):
            for lev in LEV:
                rec = []
                for i, a in A.items():
                    g = int(np.sign(s_.get(i, 0)))
                    if not g:
                        continue
                    ob, os_ = sim1(a, 1, kel, lev), sim1(a, -1, kel, lev)
                    if ob and os_:
                        rec.append((df.t0[i] >= SPLIT, g, ob[0], os_[0], ob[1] if g > 0 else os_[1]))
                if not rec:
                    continue
                x = pd.DataFrame(rec, columns=["baru", "g", "buy", "sell", "mc"])
                x["pl"] = np.where(x.g > 0, x.buy, x.sell)
                teks = []
                for per, sub in (("LAMA", x[~x.baru]), ("BARU", x[x.baru])):
                    if len(sub) < 5:
                        teks.append(f"{per} n{len(sub)}")
                        continue
                    koin = rng.integers(0, 2, size=(n_acak, len(sub)))
                    r_ = np.where(koin == 1, sub.buy.to_numpy(), sub.sell.to_numpy()).mean(axis=1)
                    p = (r_ >= sub.pl.mean()).mean()
                    teks.append(f"{per} n{len(sub):2} benar {(sub.pl > 0).mean() * 100:3.0f}% ${sub.pl.mean():+7.1f} "
                                f"(acak ${r_.mean():+7.1f}) MC {int(sub.mc.sum()):2} p {p:.2f}")
                L.append(f"   tutup {kel} 1:{lev:<4} | " + " | ".join(teks))
    return L


def sim1(a, arah: int, keluar: str, lev: int):
    """sim() untuk masuk t0 − 1 dtk; d1 = tutup di detik 1."""
    if keluar == "d1":
        s, bid, ask = a
        i0 = np.searchsorted(s, -1, side="right") - 1
        i1 = np.searchsorted(s, 1, side="left")
        if i0 < 0 or -1 - s[i0] > 30 or i1 >= len(s):
            return None
        masuk = ask[i0] if arah > 0 else bid[i0]
        oz = MODAL * lev / masuk
        pl = oz * ((bid if arah > 0 else ask)[i0 + 1:i1 + 1] - masuk) * arah
        if not len(pl):
            return None
        return (-MODAL, True) if pl.min() <= -MODAL else (max(-MODAL, float(pl[-1])), False)
    return sim(a, arah, -1, keluar, lev)


if __name__ == "__main__" and len(__import__("sys").argv) > 1 and __import__("sys").argv[1] == "acak":
    L = acak()
    print("\n".join(L))
    with OUT.open("a", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")


def simpan() -> dict:
    """Angka untuk baris 💥 aplikasi → cloud/api/cpi_detik.json["allin"] (masuk t0−1 dtk, tutup detik 2, modal $100)."""
    import json
    df = C.turunan(C.tabel())
    df = df[df.th >= 2016].reset_index(drop=True)
    tb, ts = C.tetap(df, "IDX|K"), C.tetap(df, "IDX|K+S")
    lemah = tb.where(ts == 0, 0)
    A = {i: arr(tk, r.t0) for i, r in df.iterrows() if (tk := ticks_around("XAUUSDc", r.t0)) is not None}

    def jalan(s_, lev, kel="d2"):
        rec = []
        for i, a in A.items():
            g = int(np.sign(s_.get(i, 0)))
            if g and (o := sim1(a, g, kel, lev)):
                rec.append((df.t0[i], *o))
        return pd.DataFrame(rec, columns=["t0", "pl", "mc"])

    out: dict = {"aturan": "masuk 1 dtk sebelum rilis searah tebakan kuat, tutup detik 2, lot maks (modal × leverage); "
                           "tick asli Exness XAUUSDc 2016–2026, modal $100/rilis, rugi maks = modal",
                 "dibuat": pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d %H:%M UTC"), "lev": {}}
    for lev in (200, 500, 2000):
        x = jalan(ts, lev)
        b, lm = x[x.t0 >= SPLIT], x[x.t0 < SPLIT]
        kalah = (b.pl <= 0).astype(int)
        out["lev"][str(lev)] = {"rata": round(float(b.pl.mean()), 1), "mc": int(b.mc.sum()),
                                "menang_rata": round(float(b.pl[b.pl > 0].mean()), 1),
                                "kalah_beruntun": int((kalah.groupby((kalah != kalah.shift()).cumsum()).cumsum() * kalah).max()),
                                "lama_rata": round(float(lm.pl.mean()), 1)}
        if lev == 200:
            out.update(n_baru=len(b), untung_baru=round(float((b.pl > 0).mean() * 100)), n_lama=len(lm),
                       untung_lama=round(float((lm.pl > 0).mean() * 100)),
                       th_2026=[int((b[b.t0.dt.year == 2026].pl > 0).sum()), int((b.t0.dt.year == 2026).sum())],
                       gagal="2019–2021")
    d1 = jalan(ts, 200, "d1")
    out["detik1_untung_baru"] = round(float((d1[d1.t0 >= SPLIT].pl > 0).mean() * 100))
    w = jalan(lemah, 2000)
    wb = w[w.t0 >= SPLIT]
    out["lemah"] = {"n_baru": len(wb), "untung_baru": round(float((wb.pl > 0).mean() * 100)), "mc_2000": int(wb.mc.sum())}
    f = ROOT / "cloud" / "api" / "cpi_detik.json"
    d = json.loads(f.read_text(encoding="utf-8"))
    d["allin"] = out
    f.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return out


if __name__ == "__main__" and len(__import__("sys").argv) > 1 and __import__("sys").argv[1] == "simpan":
    print(simpan())
