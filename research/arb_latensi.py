"""Mesin latensi bot screenshot ("beli diskon, tebus penuh") — python -m research.arb_latensi

Pertanyaan: seandainya kita menjalankan bot seperti wetharb/circarb, berapa yang didapat bila bot kita bereaksi dalam
L detik (polling RPC + kirim transaksi), dibanding bot yang SUDAH ada di data?

MODEL UTAMA "pembuang bersih" (dipakai untuk vonis; dibuat setelah model per-beli terbukti menghitung ganda):
  - Peluang = setiap swap JUAL oleh pelaku yang secara BERSIH menjual token jembatan pada pra-publik (arc_lawan_pelaku:
    qty_bersih < 0; termasuk router = kumpulan pengguna). Nilai peluang = rugi penjual vs nilai tebus (qty x acuan x 0,99
    - USDC diterima) dikurangi fee 2 kaki (beli balik di pool + fee pool) dan gas.
  - Bot kita menangkapnya bila latensi L < waktu sampai BELI pertama berikutnya di pool itu (pengambil asli).
  - Batas atas: modal & kecepatan tebus (median 2 mnt, p90 1,5 jam) tidak dibatasi; tidak ada efek antrean.
Model lama "menggantikan pengambil" (per swap BELI, hanya pembanding — menghitung ganda token yang diputar bolak-balik):
  - Tiap swap BELI token jembatan Arc (WETH•Arc, CRCL•Arc, NVDA•Arc) di harga <= acuan x (1 - k) adalah peluang yang
    benar-benar diambil seseorang. Untungnya = qty x acuan x 0,99 (biaya tebus jembatan 1%) - USDC dibayar - gas.
  - Waktu reaksi pengambil r = detik sejak kejadian SEBELUMNYA di pool itu (swap yang membuka diskon).
  - Bot kita dengan latensi L mendapatkan peluang itu hanya bila L < r (kita tiba lebih dulu daripada pengambil asli).
    Pesaing yang lebih cepat dari L tetap menang. Tidak ada efek antrean tambahan (perkiraan atas).
  - Robinhood: episode diskon (research/arb_robinhood: robinhood_episode_aksi) dengan jeda_reaksi_dtk & untung_aksi.
Seleksi ambang k: dipilih di PARUH PERTAMA pra-publik (6-11 Sep), diuji di paruh kedua (12-15 Sep) & pasca-publik.
Hanya membaca data yang sudah diunduh (data/research/eksternal/arb/). Laporan: docs/eksternal/hasil_arb_latensi.txt.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
ARB = ROOT / "data" / "research" / "eksternal" / "arb"
OUT = ROOT / "docs" / "eksternal" / "hasil_arb_latensi.txt"
JEMBATAN = ("WETH•Arc (jembatan RH)", "CRCL•Arc (jembatan RH)", "NVDA•Arc (jembatan RH)")
GAS_ARC = 0.003                 # USDC per swap (potret 8 Okt: ±$0,0028)
TEBUS = 0.99                    # jembatan kustodian RH<->Arc: fee 1%
LAT = (0.5, 1, 2, 3, 5, 10, 30, 60)
K = (0.05, 0.10, 0.20, 0.30, 0.40)
GRUP_BOT = {"0xa25790ec97bf6be57c0f7e41b3bb858d13b262b1", "0xcdfe8dabe88e625ed23819066be85d36c2558551",
            "0x9b92efd6d50103696b60a08413c74fd4d3476bdb", "0xa807c38887f6c94efea5ac02f8a6c74c6897eb13",
            "0x76e5c0b9b31acb9fcbe6730fa9ebd790bf3c56e2", "0x186603715be592ea531e1db3f979cba903f3d3f5",
            "0xd410b19adea79ac2d8bbe4f8607a12f1b7329529", "0xc18f971dd86652e4d8f8f1b2695884bf8d7574fe",
            "0x673250c66d8debe10bcbdd0261a3c51065026886", "0x7cff8a2b32b28ab52794c8365ae3d7423dbc87db"}
PUBLIK = pd.Timestamp("2026-09-15 22:00", tz="UTC")
PERIODE = [("pra-publik paruh 1 (s.d. 11 Sep)", None, "2026-09-12"),
           ("pra-publik paruh 2 (12-15 Sep)", "2026-09-12", "2026-09-15 22:00"),
           ("peralihan (15 Sep 22:00 - 16 Sep 06:00)", "2026-09-15 22:00", "2026-09-16 06:00"),
           ("pasca-publik 16 Sep 06:00 - 24 Sep", "2026-09-16 06:00", "2026-09-25"),
           ("2 pekan terakhir (25 Sep - 9 Okt)", "2026-09-25", None)]


def beli_arc() -> pd.DataFrame:
    d = pd.read_parquet(ARB / "arc_swap_aset.parquet",
                        columns=["id", "blok", "li", "tx", "sender", "usd", "qty", "harga", "t", "nama", "acuan",
                                 "acuan_segar", "vs_acuan"])
    d = d[d.nama.isin(JEMBATAN)].sort_values(["id", "blok", "li"]).copy()
    d["r"] = d.groupby("id").t.diff().dt.total_seconds()          # detik sejak kejadian sebelumnya di pool itu
    b = d[(d.usd < 0) & (d.qty > 0) & d.acuan.notna()].copy()       # BELI token: bayar USDC, terima token
    b["untung"] = b.qty * b.acuan * TEBUS - (-b.usd) - GAS_ARC
    b["grup"] = b.sender.isin(GRUP_BOT)
    return b


def pembuang() -> pd.DataFrame:
    """Swap JUAL oleh penjual bersih (pra-publik s.d. 16 Sep 06:00) + waktu sampai beli berikutnya di pool yang sama."""
    s = pd.read_parquet(ARB / "arc_lawan_swap.parquet").sort_values(["id", "blok", "li"]).reset_index(drop=True)
    p = pd.read_parquet(ARB / "arc_lawan_pelaku.parquet")
    jual_bersih = set(zip(p.nama[p.qty_bersih < 0], p.pelaku[p.qty_bersih < 0]))
    ts = s.t.astype("int64").to_numpy() / 1e9
    nxt = np.full(len(s), np.nan)
    for _pid, g in s.groupby("id"):
        idx = g.index.to_numpy()
        beli = (g.qty > 0).to_numpy()
        last, nb = np.nan, np.full(len(g), np.nan)
        for i in range(len(g) - 1, -1, -1):
            nb[i] = last
            if beli[i]:
                last = ts[idx[i]]
        nxt[idx] = nb - ts[idx]
    s["r_beli"] = nxt
    s["rugi"] = -s.pnl_vs_tebus
    fee = s.fee.astype(float) / 1e6
    s["tangkap"] = np.maximum(0.0, s.rugi - 2 * fee * s.usd.abs() - 2 * GAS_ARC)
    m = (s.qty < 0) & (s.rugi > 0) & np.array([(n, a) in jual_bersih for n, a in zip(s.nama, s.pelaku)])
    return s[m]


def _tangkap(d: pd.DataFrame, lat: float) -> float:
    return float(d[(d.r_beli > lat) | d.r_beli.isna()].tangkap.sum())


def _ringkas(b: pd.DataFrame, k: float, lat: float) -> dict:
    x = b[(b.vs_acuan <= -k) & (b.r > lat)]
    return {"n": len(x), "wr": (x.untung > 0).mean() * 100 if len(x) else np.nan, "untung": x.untung.sum(),
            "usd": (-x.usd).sum(), "grup": x[x.grup].untung.sum()}


def _per(b: pd.DataFrame, a, z) -> pd.DataFrame:
    m = pd.Series(True, index=b.index)
    if a:
        m &= b.t >= pd.Timestamp(a, tz="UTC")
    if z:
        m &= b.t < pd.Timestamp(z, tz="UTC")
    return b[m]


def _rh() -> pd.DataFrame:
    e = pd.read_parquet(ARB / "robinhood_episode_aksi.parquet",
                        columns=["t_mulai", "umur_jam", "untung_aksi", "jeda_reaksi_dtk", "n_aksi", "hook"])
    return e[(e.n_aksi > 0) & ~e.hook.astype(bool)]


def laporan() -> str:
    b = beli_arc()
    L = ["Mesin latensi bot screenshot ('beli diskon, tebus penuh') — research/arb_latensi.py, 9 Okt 2026",
         "Model menggantikan pengambil: bot kita (latensi L dtk) mengambil sebuah peluang hanya bila tiba SEBELUM pengambil",
         "asli (L < waktu reaksinya sejak kejadian sebelumnya di pool). Untung = qty x acuan x 0,99 (fee tebus jembatan 1%)",
         f"- USDC - gas ${GAS_ARC}. Perkiraan ATAS: bot lain bisa ikut mempercepat diri; antrean & revert tidak dihitung.",
         "Acuan: ETH = Binance 1 mnt; CRCL/NVDA = NYSE 1 mnt (di luar jam bursa = close terakhir, 'basi').", ""]
    # ---------------------------------------------------------------- 1. pilih ambang k di paruh 1, uji paruh 2
    p1 = _per(b, None, "2026-09-12")
    L.append("1. PILIH AMBANG DISKON k DI PARUH 1 PRA-PUBLIK (6-11 Sep), latensi 3 dtk:")
    best, best_u = None, -1e18
    for k in K:
        s = _ringkas(p1, k, 3)
        L.append(f"   k {k:.0%}: n {s['n']:>4}  WR {s['wr']:5.1f}%  untung ${s['untung']:>9,.0f}  "
                 f"per beli ${s['untung'] / max(s['n'], 1):,.2f}")
        if s["untung"] > best_u:
            best, best_u = k, s["untung"]
    L.append(f"   -> dipilih k = {best:.0%} (untung terbesar di paruh 1), diuji di periode lain di bawah.")
    L.append("")
    # ---------------------------------------------------------------- 2. per periode x latensi
    L.append(f"2. UNTUNG YANG BISA DIAMBIL BOT KITA (k = {best:.0%}) per periode & latensi L (semua 3 token jembatan Arc):")
    L.append("   periode                                    " + "".join(f"L={x:>4}s".rjust(12) for x in LAT))
    for nama, a, z in PERIODE:
        x = _per(b, a, z)
        row = [f"${_ringkas(x, best, lat)['untung']:,.0f}" for lat in LAT]
        L.append(f"   {nama:<43}" + "".join(r.rjust(12) for r in row))
    L.append("   WR (beli yang untung setelah biaya) di periode yang sama:")
    for nama, a, z in PERIODE:
        x = _per(b, a, z)
        row = []
        for lat in LAT:
            s = _ringkas(x, best, lat)
            row.append("-" if not s["n"] else f"{s['wr']:.0f}% n{s['n']}")
        L.append(f"   {nama:<43}" + "".join(r.rjust(12) for r in row))
    L.append("")
    # ---------------------------------------------------------------- 3. waktu reaksi pengambil asli
    L.append("3. WAKTU REAKSI PENGAMBIL ASLI (beli di diskon >= k, detik sejak kejadian sebelumnya di pool):")
    for nama, a, z in PERIODE:
        x = _per(b, a, z)
        x = x[x.vs_acuan <= -best]
        if not len(x):
            L.append(f"   {nama:<43} -")
            continue
        q = x.r.quantile([0.1, 0.5, 0.9])
        L.append(f"   {nama:<43} n {len(x):>5}  P10 {q[0.1]:7.1f}  median {q[0.5]:7.1f}  P90 {q[0.9]:8.1f} dtk  "
                 f"bagian grup screenshot {x.grup.mean():.0%}")
    L.append("")
    # ---------------------------------------------------------------- 4. per token, pra-publik
    L.append("4. PER TOKEN (pra-publik 6-15 Sep, k terpilih):")
    pra = _per(b, None, "2026-09-15 22:00")
    for nm in JEMBATAN:
        x = pra[pra.nama == nm]
        row = [f"${_ringkas(x, best, lat)['untung']:,.0f}" for lat in (1, 3, 10, 30)]
        L.append(f"   {nm:<26} L=1s {row[0]:>9}  L=3s {row[1]:>9}  L=10s {row[2]:>9}  L=30s {row[3]:>9}")
    L.append("")
    # ---------------------------------------------------------------- 5. Robinhood
    e = _rh()
    L.append("5. ROBINHOOD (episode diskon >= 5% di pool aset bernilai, tanpa pool ber-hook; untung per aksi semua pelaku):")
    for nama, a, z in (("1 Jul - 24 Sep", "2026-07-01", "2026-09-25"), ("2 pekan terakhir (25 Sep - 9 Okt)", "2026-09-25", None)):
        m = e.t_mulai >= pd.Timestamp(a, tz="UTC")
        if z:
            m &= e.t_mulai < pd.Timestamp(z, tz="UTC")
        x = e[m]
        row = [f"${x[x.jeda_reaksi_dtk > lat].untung_aksi.sum():,.0f}" for lat in LAT]
        L.append(f"   {nama:<43}" + "".join(r.rjust(12) for r in row))
    L.append("")
    # ---------------------------------------------------------------- 6. MODEL UTAMA: pembuang bersih
    d = pembuang()
    p = pd.read_parquet(ARB / "arc_lawan_pelaku.parquet")
    L.append("6. MODEL UTAMA 'PEMBUANG BERSIH' (pra-publik Arc s.d. 16 Sep 06:00; peluang = jualan pelaku yang bersih MENJUAL,")
    L.append("   ditangkap bila bot kita tiba sebelum pembeli pertama berikutnya; dikurangi fee 2 kaki & gas):")
    L.append("   Pembanding nyata (dinilai pada nilai tebus): untung pembeli bersih "
             + ", ".join(f"{n.split(' ')[0]} ${p[(p.nama == n) & (p.pnl_vs_tebus > 0)].pnl_vs_tebus.sum():,.0f}" for n in JEMBATAN)
             + f"; terbesar satu pelaku ${p.pnl_vs_tebus.max():,.0f}; grup screenshot ±$7 rb.")
    L.append("   periode                                    " + "".join(f"L={x:>4}s".rjust(12) for x in LAT))
    for nama, a, z in PERIODE[:3]:
        x = _per(d, a, z)
        L.append(f"   {nama:<43}" + "".join(f"${_tangkap(x, lat):,.0f}".rjust(12) for lat in LAT))
    for nm in JEMBATAN:
        x = d[d.nama == nm]
        L.append(f"   {nm:<43}" + "".join(f"${_tangkap(x, lat):,.0f}".rjust(12) for lat in LAT))
    q = _per(d, "2026-09-12", "2026-09-15 22:00").r_beli.quantile([0.1, 0.5, 0.9])
    L.append(f"   Reaksi pembeli pertama setelah jualan (12-15 Sep): P10 {q[0.1]:.1f} / median {q[0.5]:.1f} / P90 {q[0.9]:.1f} dtk.")
    L.append("   Catatan: modal yang dibutuhkan besar & harus diputar lewat jembatan (tebus median 2 mnt, p90 1,5 jam; kembali ke Arc")
    L.append("   butuh jembatan USDC) -> hasil nyata jauh di bawah batas atas ini; CRCL dinilai pada close NYSE (akhir pekan basi).")
    L.append("")
    # ---------------------------------------------------------------- vonis
    pa = _per(b, "2026-09-25", None)
    dp = _per(d, "2026-09-12", "2026-09-15 22:00")
    s3 = _ringkas(pa, best, 3)
    rh3 = e[(e.t_mulai >= pd.Timestamp("2026-09-25", tz="UTC")) & (e.jeda_reaksi_dtk > 3)].untung_aksi.sum()
    L += ["VONIS:",
          f"  - Jendela pra-publik Arc (12-15 Sep, model pembuang bersih): batas atas yang bisa ditangkap bot latensi 3 dtk ±${_tangkap(dp, 3):,.0f},",
          f"    10 dtk ±${_tangkap(dp, 10):,.0f}, 30 dtk ±${_tangkap(dp, 30):,.0f} (hampir semuanya CRCL; WR per beli ±100% BILA bisa ditebus).",
          "    Ada karena (a) token jembatan bisa ditebus 1:1 dan (b) chain belum publik sehingga pesaing sedikit. Hasil nyata",
          "    dibatasi modal & kecepatan memutar modal lewat jembatan (grup screenshot: ±$7 rb; pemain terbesar ±$90 rb).",
          f"  - 2 pekan terakhir (25 Sep - 9 Okt): Arc latensi 3 dtk ±${s3['untung']:,.0f} (n {s3['n']}), Robinhood ±${rh3:,.0f} untuk seluruh periode itu",
          "    -> TIDAK layak untuk bot otomatis sekarang (receh, diambil bot < 1 dtk).",
          "  - Bot seperti screenshot hanya berguna di JENDELA PELUNCURAN berikutnya (chain/jembatan baru, pra-publik) — kejadian",
          "    langka yang tidak bisa dijadwalkan, dengan risiko kustodian jembatan (satu EOA), tebusan dihentikan, token tiruan.",
          "  Hasil masa lalu bukan jaminan."]
    txt = "\n".join(L) + "\n"
    OUT.write_text(txt, encoding="utf-8")
    return txt


if __name__ == "__main__":
    print(laporan())
