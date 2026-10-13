"""⚡ CPI modal kecil: risiko LONJAKAN MELAWAN di detik pertama (habis padahal arah benar) + leverage optimal + cara meredam

python -m research.cpi_spike      → docs/eksternal/hasil_cpi_spike.txt

Pertanyaan pengguna 13 Okt 2026: "kadang ada spike — prediksi benar di detik 2/3 tetapi detik pertama berlawanan, alhasil habis
semua tanpa menikmati profit. Berapa lot kira-kira? Riset & uji validasi, keluarkan seluruh kemampuan."

Tick ASLI Exness XAUUSDc, tebakan CPI KUAT aplikasi (IDX|K+S tutup kertas). Lot penuh pada leverage L: modal habis bila emas
melawan ≥ harga / L (dolar per ons; tidak bergantung besar modal). Masuk = tick terakhir ≤ t0 − 1 dtk (BUY di ask, SELL di
bid); harga tutup = bid (BUY) / ask (SELL) → spread ikut dihitung sebagai gerak melawan.
Ditetapkan SEBELUM melihat hasil:
  1. MAE ($/ons) dari masuk s/d detik 1/2/3/5/10; "arah benar" = mid detik 10 searah tebakan.
  2. Per leverage 100/200/300/500/750/1000: modal habis (dan berapa yang habis padahal arah benar), lentur (detik 2 rugi →
     tutup; untung → tahan s/d detik 10), rata-rata & median per $100, pembanding arah acak.
  3. Cara meredam: (A) BERTAHAP: tahap 1 lot leverage L1 (100/200) di t−1; di detik 2 bila untung → tambah tahap 2 sampai
     total L (500/1000) dengan harga t+2,5 dtk (jeda klik 0,5 dtk), tutup semua detik 10; rugi → tutup tahap 1 di detik 2.
     (B) MASUK SETELAH RILIS searah tebakan pada t+0,5 / +1 / +1,5 dtk, lentur. (C) SL darurat −50% / −80% modal (dieksekusi
     di tick pertama yang menembus, harga tick itu = slip ikut).
  Semua dilaporkan LAMA (< Okt 2021) & BARU, per tahun (BARU), dan vs arah acak (5.000×).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from . import cpi_detik as C
from .cpi_allin2 import SPLIT, arr
from .exness import ticks_around

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "eksternal" / "hasil_cpi_spike.txt"
MODAL = 100.0
LEVS = (100, 200, 300, 500, 750, 1000)


def idx_le(s, x):
    return int(np.searchsorted(s, x, side="right")) - 1


def jalan(a, g: int, masuk: float, lev: float, rencana: str, l1: float = 0, sl: float | None = None):
    """(P/L $, habis?) satu rilis. rencana: 'lentur' | 'bertahap'."""
    s, bid, ask = a
    i0 = idx_le(s, masuk)
    if i0 < 0 or masuk - s[i0] > 30:
        return None
    p0 = ask[i0] if g > 0 else bid[i0]
    kp = bid if g > 0 else ask
    lev1 = l1 if rencana == "bertahap" else lev
    oz1 = MODAL * lev1 / p0

    def pl_seg(oz, px0, a_, b_):
        seg = kp[a_:b_ + 1]
        return oz * (seg - px0) * g
    i2 = idx_le(s, 2.0)
    i10 = idx_le(s, 10.0)
    if i2 <= i0 or i10 <= i2:
        return None
    seg2 = pl_seg(oz1, p0, i0 + 1, i2)
    batas = -MODAL if sl is None else -sl * MODAL
    hit = np.flatnonzero(seg2 <= batas)
    if len(hit):
        v = float(seg2[hit[0]])
        return (max(-MODAL, v), v <= -MODAL)
    if seg2[-1] <= 0:                                        # detik 2 rugi → tutup
        return float(seg2[-1]), False
    if rencana == "bertahap":
        ia = idx_le(s, 2.5)
        pa = ask[ia] if g > 0 else bid[ia]
        oz2 = MODAL * (lev - l1) / pa
        tot = pl_seg(oz1, p0, ia + 1, i10) + oz2 * (kp[ia + 1:i10 + 1] - pa) * g
        tot = np.concatenate([seg2, tot])
    else:
        tot = np.concatenate([seg2, pl_seg(oz1, p0, i2 + 1, i10)])
    hit = np.flatnonzero(tot <= batas)
    if len(hit):
        v = float(tot[hit[0]])
        return (max(-MODAL, v), v <= -MODAL)
    return float(tot[-1]), False


def main() -> None:
    df = C.turunan(C.tabel())
    df = df[df.th >= 2016].reset_index(drop=True)
    ts = C.tetap(df, "IDX|K+S")
    A, rows = {}, []
    for i, r in df.iterrows():
        g = int(np.sign(ts.iloc[i]))
        if not g:
            continue
        tk = ticks_around("XAUUSDc", r.t0)
        if tk is None:
            continue
        a = arr(tk, r.t0)
        s, bid, ask = a
        i0 = idx_le(s, -1.0)
        if i0 < 0:
            continue
        A[i] = a
        p0 = ask[i0] if g > 0 else bid[i0]
        kp = bid if g > 0 else ask
        m0 = (bid[i0] + ask[i0]) / 2
        o = {"t0": r.t0, "g": g, "harga": p0, "spread0": ask[i0] - bid[i0]}
        for h in (1, 2, 3, 5, 10):
            j = idx_le(s, h)
            o[f"mae{h}"] = float(max(0.0, -(np.min((kp[i0 + 1:j + 1] - p0) * g)))) if j > i0 else np.nan
        j10 = idx_le(s, 10)
        o["benar"] = np.sign(((bid[j10] + ask[j10]) / 2 - m0) * g) > 0
        j1 = idx_le(s, 1)
        o["lawan_d1"] = np.sign(((bid[j1] + ask[j1]) / 2 - m0) * g) < 0
        rows.append(o)
    x = pd.DataFrame(rows)
    x["baru"] = x.t0 >= SPLIT
    L = ["# ⚡ CPI: lonjakan melawan di detik pertama & leverage (research/cpi_spike.py)", __doc__.split("\n\n")[2], ""]
    L.append(f"Rilis CPI tebakan kuat dengan tick: {len(x)} (BARU {int(x.baru.sum())}); harga median ${x.harga.median():,.0f}; "
             f"spread saat masuk median ${x.spread0.median():.2f}")
    L.append("\n## 1. Gerak melawan terbesar (MAE, $/ons, termasuk spread) dari masuk t−1 dtk")
    for per, m in (("LAMA", ~x.baru), ("BARU", x.baru)):
        z = x[m]
        for nama, sub in (("arah BENAR", z[z.benar]), ("arah SALAH", z[~z.benar])):
            if len(sub):
                L.append(f"   {per} {nama:10s} n {len(sub):2d} | " + " | ".join(
                    f"s/d detik {h}: median ${sub[f'mae{h}'].median():.2f} P90 ${sub[f'mae{h}'].quantile(0.9):.2f} "
                    f"maks ${sub[f'mae{h}'].max():.2f}" for h in (1, 2, 10)))
        L.append(f"   {per} detik 1 berlawanan arah tebakan: {int(z.lawan_d1.sum())}/{len(z)}, di antaranya arah akhirnya BENAR "
                 f"{int((z.lawan_d1 & z.benar).sum())}")
    L.append("\n## 2. Per leverage (lot penuh, lentur): habis bila melawan ≥ harga/leverage")
    rng = np.random.default_rng(31)
    hasil, tabel, tabel_lama = {}, [], {}
    for lev in LEVS:
        jar = x.harga.median() / lev
        for per, m in (("LAMA", ~x.baru), ("BARU", x.baru)):
            z = x[m]
            habis2 = z[z.mae2 >= z.harga / lev]
            rec, rb, rs = [], [], []
            for _, r in z.iterrows():
                i = next(k for k, v in A.items() if df.t0[k] == r.t0)
                o = jalan(A[i], int(r.g), -1.0, lev, "lentur")
                ob, os_ = jalan(A[i], 1, -1.0, lev, "lentur"), jalan(A[i], -1, -1.0, lev, "lentur")
                if o and ob and os_:
                    rec.append(o)
                    rb.append(ob[0])
                    rs.append(os_[0])
            pl = np.array([v for v, _ in rec])
            mc = np.array([h for _, h in rec])
            koin = rng.integers(0, 2, size=(5000, len(pl)))
            ac = np.where(koin == 1, np.array(rb), np.array(rs)).mean(axis=1)
            hasil[(lev, per)] = pl
            if per == "BARU":
                benar = x[x.baru & x.benar]
                tabel.append({"lev": lev, "untung": round(float((pl > 0).mean() * 100)), "rata": round(float(pl.mean()), 1),
                              "habis": int(mc.sum()), "n": len(pl),
                              "habis_benar": int((benar.mae10 / benar.harga >= 1 / lev).sum()),
                              "acak": round(float(ac.mean()), 1)})
            else:
                tabel_lama[lev] = round(float(pl.mean()), 1)
            L.append(f"   1:{lev:<4} (habis bila melawan ${jar:5.2f}) {per}: habis {int(mc.sum()):2d}/{len(pl)} "
                     f"(padahal arah benar {int(habis2.benar.sum())}) | untung {(pl > 0).mean() * 100:3.0f}% | rata "
                     f"${pl.mean():+7.1f} median ${np.median(pl):+6.1f} /$100 (acak ${ac.mean():+6.1f}, p {(ac >= pl.mean()).mean():.2f})")
    for t in tabel:
        t["lama_rata"] = tabel_lama.get(t["lev"])
    L.append("\n## 3. Cara meredam (BARU | LAMA, per $100; vs acak BARU)")

    def uji(nama, fn):
        out = {}
        for per, m in (("BARU", x.baru), ("LAMA", ~x.baru)):
            pl, mc, rb, rs = [], [], [], []
            for _, r in x[m].iterrows():
                i = next(k for k, v in A.items() if df.t0[k] == r.t0)
                o, ob, os_ = fn(A[i], int(r.g)), fn(A[i], 1), fn(A[i], -1)
                if o and ob and os_:
                    pl.append(o[0])
                    mc.append(o[1])
                    rb.append(ob[0])
                    rs.append(os_[0])
            pl = np.array(pl)
            koin = rng.integers(0, 2, size=(5000, len(pl)))
            ac = np.where(koin == 1, np.array(rb), np.array(rs)).mean(axis=1)
            out[per] = (pl, int(np.sum(mc)), ac)
        b, lm = out["BARU"], out["LAMA"]
        L.append(f"   {nama:44s} BARU untung {(b[0] > 0).mean() * 100:3.0f}% rata ${b[0].mean():+7.1f} habis {b[1]:2d} "
                 f"(acak ${b[2].mean():+6.1f}, p {(b[2] >= b[0].mean()).mean():.2f}) | LAMA rata ${lm[0].mean():+7.1f} habis {lm[1]}")
        return out
    simpan_cara = {}
    for l1, lev in ((100, 500), (100, 1000), (200, 1000), (200, 500)):
        simpan_cara[f"bertahap_{l1}_{lev}"] = uji(f"(A) bertahap 1:{l1} di t−1 → total 1:{lev} di detik 2,5", lambda a, g, l1=l1, lev=lev: jalan(a, g, -1.0, lev, "bertahap", l1))
    for lev in (200, 500, 1000):
        uji(f"    pembanding: langsung 1:{lev} di t−1 (lentur)", lambda a, g, lev=lev: jalan(a, g, -1.0, lev, "lentur"))
    for t in (0.5, 1.0, 1.5):
        for lev in (200, 500):
            uji(f"(B) masuk t+{t} dtk 1:{lev} (lentur)", lambda a, g, t=t, lev=lev: jalan(a, g, t, lev, "lentur"))
    for sl in (0.5, 0.8):
        for lev in (500, 1000):
            simpan_cara[f"sl{int(sl * 100)}_{lev}"] = uji(f"(C) SL darurat −{int(sl * 100)}% modal 1:{lev} (lentur)", lambda a, g, sl=sl, lev=lev: jalan(a, g, -1.0, lev, "lentur", sl=sl))
    # 4. Apakah lonjakan melawan (% harga) membesar saat emas mahal (2025–2026)? → per rilis BARU arah benar
    L.append("\n## 4. Per rilis BARU arah BENAR: gerak melawan terbesar s/d detik 10 (% harga) — urut terbesar")
    bn = x[x.baru & x.benar].assign(pct=lambda z: z.mae10 / z.harga * 100).sort_values("pct", ascending=False)
    for _, r in bn.iterrows():
        L.append(f"   {r.t0:%Y-%m-%d} {'BUY ' if r.g > 0 else 'SELL'} harga ${r.harga:,.0f} melawan ${r.mae10:.2f} = "
                 f"{r.pct:.3f}% • detik 1 {'MELAWAN' if r.lawan_d1 else 'searah'}")
    th = bn.assign(th=bn.t0.dt.year).groupby("th").pct.agg(["count", "median", "max"])
    L.append("   per tahun (n / median / maks %): " + " • ".join(
        f"{t}: {int(v['count'])} / {v['median']:.3f} / {v['max']:.3f}" for t, v in th.iterrows()))
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    # → cloud/api/cpi_detik.json["allin"]["spike"] (aplikasi: tabel leverage + jarak habis + lonjakan detik 1)
    import json
    bn = x[x.baru & x.benar]

    def ring(o):
        b, lm = o["BARU"], o["LAMA"]
        return {"untung": round(float((b[0] > 0).mean() * 100)), "rata": round(float(b[0].mean()), 1), "habis": b[1],
                "lama_rata": round(float(lm[0].mean()), 1)}
    spike = {"dibuat": pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d %H:%M UTC"),
             "mae_benar_maks_pct": round(float((bn.mae10 / bn.harga).max() * 100), 3),
             "mae_benar_p90_pct": round(float((bn.mae10 / bn.harga).quantile(0.9) * 100), 3),
             "d1_lawan": int(x[x.baru].lawan_d1.sum()), "d1_lawan_benar": int((x[x.baru].lawan_d1 & x[x.baru].benar).sum()),
             "n_baru": int(x.baru.sum()), "tabel": tabel, "saran_lev": 500,
             "bertahap": ring(simpan_cara["bertahap_200_1000"]), "sl80_1000": ring(simpan_cara["sl80_1000"])}
    f = ROOT / "cloud" / "api" / "cpi_detik.json"
    d = json.loads(f.read_text(encoding="utf-8"))
    d.setdefault("allin", {})["spike"] = spike
    f.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(spike, ensure_ascii=False))


if __name__ == "__main__":
    main()
