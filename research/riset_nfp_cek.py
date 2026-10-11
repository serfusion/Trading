"""🔎 Cek ketahanan aturan UR2 (pasca-lihat) dari research/riset_nfp.py — DIAGNOSTIK, bukan aturan baru.

python -m research.riset_nfp_cek   → ditambahkan ke docs/eksternal/hasil_riset_nfp.txt (bagian "Cek ketahanan UR2")

Ditulis 11 Okt 2026 SETELAH hasil riset_nfp terlihat. Tidak ada aturan baru yang dipilih di sini; semua pemeriksaan di bawah
hanya menjawab "apakah UR2 bisa dipercaya?":
  1. sebaran tebakan (emas NAIK vs TURUN) dan ketepatan per sisi; pembanding "selalu TURUN" pada rilis yang sama
     (BARU emas turun 59% → tebakan yang hampir selalu TURUN bisa tampak bagus karena kecenderungan dasar);
  2. apakah UR2 menebak KEJUTAN angkanya (UR, NFP, gabungan plafon) — bila mekanisme ekonominya benar, harus > 50%;
  3. rilis yang DIBUANG UR2 (KLLSW & PK5U tidak sepakat): ketepatan masing-masing komponen di sana;
  4. versi LIVE klaim lanjutan: nilai vintage yang berlaku H−1 (seperti FRED API tanpa realtime) vs rilis pertama
     (FRED API output_type=4); berapa rilis berubah tanda dan ketepatan tutup kertasnya;
  5. bootstrap 95% (rilis diambil ulang 5.000×) dan ketepatan bila tahun terbaik dibuang;
  6. uji binomial satu sisi terhadap 50% dan terhadap kecenderungan dasar (selalu TURUN) pada rilis yang ditebak.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from .lonjakan_uji import SPLIT, sk, tutup
from .riset_nfp import OUT, alfred, asof, pct, rilis_pertama, sabtu_survei, tabel


def binom_p(k: int, n: int, p0: float) -> float:
    """P(X ≥ k) untuk X ~ Binomial(n, p0)."""
    return float(sum(math.comb(n, i) * p0 ** i * (1 - p0) ** (n - i) for i in range(k, n + 1)))


def kllsw_live(x: pd.DataFrame) -> np.ndarray:
    """KLLSW dengan nilai vintage CCSA yang berlaku H−1 (bukan rilis pertama)."""
    cc = alfred("CCSA")
    f_ = rilis_pertama("CCSA")
    out = np.zeros(len(x))
    for i, r in enumerate(x.itertuples()):
        if r.M != r.M:
            continue
        M1 = (r.M.to_period("M") - 1).to_timestamp()
        s0, s1 = sabtu_survei(r.M), sabtu_survei(M1)
        h1 = r.d - pd.Timedelta(days=1)
        if s0 not in f_.index or f_.at[s0, "rs"] >= r.d:
            continue
        a, b = asof(cc, s0, h1), asof(cc, s1, h1)
        if a == a and b == b and a != b:
            out[i] = -np.sign(a - b)
    return out


def kesimpulan(x, y, th, tb, ok, lama, baru, p_dasar: float) -> list[str]:
    import json
    hs = {h["kode_aturan"]: h for h in json.loads((OUT.parent.parent.parent / "data" / "research" / "eksternal" /
                                                   "riset_nfp_hasil.json").read_text(encoding="utf-8"))}
    u = hs["UR2"]
    pra = sorted((h for c, h in hs.items() if c not in ("KOLEKSI", "MODEL", "UR2") and h["n_rilis"] >= 40),
                 key=lambda h: -h["semua"])
    kl, kb = sk(tb, y, lama), sk(tb, y, baru)
    okb = baru & (tb != 0) & (y != 0)
    turun_b = int((y[okb] < 0).sum())
    f = lambda v: "–" if v is None else f"{v:.3f}"  # noqa: E731
    L = ["", "## Kesimpulan (11 Okt 2026)",
         f"- Diuji {len(hs)} aturan (22 pra-registrasi + 3 pasca-lihat); 21 cukup rilis untuk permutasi keluarga 2.000×.",
         "- Pra-registrasi: 0 lolos. Terbaik (≥ 40 rilis): " +
         "; ".join(f"{h['kode_aturan']} {h['semua']:.1f}% n {h['n_rilis']} (LAMA {h['lama']}, BARU {h['baru']}, "
                   f"p {f(h['p16'])}/{f(h['p22'])})" for h in pra[:4]) + ".",
         "  Petunjuk payrolls (ADP vs konsensus swasta, klaim awal pekan survei, ISM, Philly Fed, Challenger, Indeed, revisi,",
         "  tren 3 bulan) menebak kejutan NFP hanya 33–54% → konsensus ekonom sudah memuat informasi itu (kecuali FFNQ 60%",
         "  n 48, tetapi hanya 40 rilis ditebak & arah emas 52,6%). Konsistensi y/y upah",
         "  (AHEM) menebak kejutan AHE 75% (15/20) tetapi konsensus y/y Nasdaq hanya ada di 22 rilis → tidak bisa divalidasi.",
         f"- UR2 (pasca-lihat, tanda(KLLSW + PK5U)) memenuhi kriteria BAKU: {u['semua']}% n {u['n_rilis']}, LAMA {u['lama']}%,",
         f"  BARU {u['baru']}%, p keluarga {f(u['p16'])}/{f(u['p22'])}. TETAPI tidak dapat dipercaya:",
         f"  (a) p sadar-seleksi (langkah 'pilih 2 aturan terbaik lalu gabungkan' diulang di tiap acakan) "
         f"{f(u.get('p16_seleksi'))}/{f(u.get('p22_seleksi'))} → tidak signifikan;",
         f"  (b) di BARU UR2 benar {kb[0]}/{kb[1]}, sama dengan 'selalu TURUN' pada rilis yang sama ({turun_b}/{int(okb.sum())}) "
         f"— {int((tb[okb] < 0).sum())} dari {int(okb.sum())} tebakan BARU adalah TURUN, jadi keunggulan BARU = "
         "kecenderungan dasar emas turun saat NFP;",
         f"      keunggulan hanya di LAMA ({kl[0]}/{kl[1]});",
         "  (c) pada rilis normal (emas searah kejutan sebenarnya) UR2 hanya ±58%; sebagian besar kelebihan datang dari rilis",
         "      anomali/bercampur — tidak sesuai mekanisme 'menebak kejutan UR lalu emas ikut';",
         f"  (d) bootstrap 95% mencakup 52%; binomial terhadap kecenderungan dasar p {p_dasar:.3f}; target sekunder detik 2–10 "
         f"{hs['UR2']['detik_semua']}% (p {f(hs['UR2']['detik_p16'])}/{f(hs['UR2']['detik_p22'])}).",
         "  → UR2 TIDAK disarankan dipasang. Kandidat yang lolos semua syarat + koreksi seleksi: TIDAK ADA.",
         "- Informasi ekonomi kecil yang nyata: klaim LANJUTAN pekan survei menebak arah kejutan pengangguran ±61% (2016+),",
         "  tetapi tidak berubah menjadi arah emas menit pertama (KLLSW 58,5%, p 0,58). Arah emas NFP tetap ditentukan kejutan",
         "  gabungan (plafon 89,5%) yang belum bisa ditebak sebelum rilis.",
         "- Tidak diuji (alasan): Conference Board 'jobs plentiful − hard to get' (berlisensi, tidak ada di Nasdaq/FRED), NFIB",
         "  rencana rekrut (tidak ada di kalender), Kalshi/Polymarket payrolls & U3 1 jam sebelum rilis (data sejak 2023 → < 40",
         "  rilis; putaran pertama KAL/KALUR 37,5% n 16), ADP mingguan & Revelio (sejak 2025).",
         "- Bila kelak ingin uji maju UR2 (perlu izin pengguna, TANPA ditampilkan): live = FRED API CCSA output_type=4 (rilis",
         "  pertama) untuk pekan survei (pekan Minggu–Sabtu berisi tgl 12) bulan ini & bulan lalu + hitung pekan kalender (PK5).",
         "- Ulang: PYTHONPATH=. python3 -m research.riset_nfp segar && PYTHONPATH=. python3 -m research.riset_nfp_cek",
         "  (tabel dibangun ulang dari cache Nasdaq/ALFRED/tick 11 Okt 2026 → identik dengan percobaan sebelumnya)."]
    return L


def main() -> None:
    x = tabel()
    y = x.arah.fillna(0).to_numpy()
    th = x.th.to_numpy()
    t0 = x.t0
    s16 = th >= 2016
    lama, baru = s16 & (t0 < SPLIT).to_numpy(), (t0 >= SPLIT).to_numpy()
    ur2 = x.UR2.to_numpy(float)
    tb = tutup(ur2, y, th)
    L = ["", "## Cek ketahanan UR2 (diagnostik pasca-lihat, research/riset_nfp_cek.py — tidak memilih aturan baru)"]

    # 1. sebaran tebakan
    L.append("1) Sebaran tebakan tutup kertas (target lonjakan; rilis 2016–26 yang ditebak & bergerak):")
    for nm, m in (("2016–26", s16), ("LAMA", lama), ("BARU", baru)):
        ok = m & (tb != 0) & (y != 0)
        up, dn = ok & (tb > 0), ok & (tb < 0)
        k_up, k_dn = int((y[up] > 0).sum()), int((y[dn] < 0).sum())
        k_tr = int((y[ok] < 0).sum())
        L.append(f"   {nm:8s} tebak NAIK {pct(k_up, int(up.sum()))} | tebak TURUN {pct(k_dn, int(dn.sum()))} | "
                 f"pembanding 'selalu TURUN' di rilis yang sama {pct(k_tr, int(ok.sum()))}")

    # 2. menebak kejutan angka?
    L.append("2) Apakah UR2 menebak kejutan ANGKA (arah USD; rilis 2016–26 dengan kejutan ≠ 0)?")
    for nm, ref in (("UR (−kejutan UR)", -x.s_ur.to_numpy()), ("NFP utama", x.s_nfp.to_numpy()),
                    ("gabungan plafon", x.PLAFON.to_numpy())):
        ok = s16 & (ur2 != 0) & (ref != 0)
        L.append(f"   {nm:18s} {pct(int((ur2[ok] == ref[ok]).sum()), int(ok.sum()))}")
    pl = -x.PLAFON.to_numpy()
    ok = s16 & (tb != 0) & (pl != 0) & (y != 0)
    L.append(f"   catatan: pada rilis yang ditebak, arah kejutan sebenarnya (plafon) menjelaskan lonjakan "
             f"{pct(int((pl[ok] == y[ok]).sum()), int(ok.sum()))}; tebakan UR2 sama dengan arah plafon "
             f"{pct(int((tb[ok] == pl[ok]).sum()), int(ok.sum()))}")
    ok = s16 & (tb != 0) & (y != 0)
    L.append("   penguraian tebakan benar UR2 (tutup kertas 2016–26) menurut hubungan emas ↔ kejutan sebenarnya:")
    for nm, m in (("emas SEARAH kejutan gabungan", ok & (pl != 0) & (pl == y)),
                  ("emas MELAWAN kejutan gabungan", ok & (pl != 0) & (pl != y)),
                  ("kejutan bercampur (plafon 0: NFP & UR searah)", ok & (pl == 0))):
        L.append(f"     {nm:46s} {pct(int((tb[m] == y[m]).sum()), int(m.sum()))}")

    # 3. rilis yang dibuang
    kl, pk = x.KLLSW.to_numpy(float), x.PK5U.to_numpy(float)
    beda = s16 & (kl != 0) & (pk != 0) & (kl != pk) & (y != 0)
    L.append(f"3) Rilis 2016–26 yang DIBUANG UR2 (KLLSW ≠ PK5U): {int(beda.sum())}; ketepatan mentah di sana: "
             f"KLLSW {pct(int((-kl[beda] == y[beda]).sum()), int(beda.sum()))}, "
             f"PK5U {pct(int((-pk[beda] == y[beda]).sum()), int(beda.sum()))} (keduanya saling meniadakan → 1 benar, 1 salah)")
    sama = s16 & (ur2 != 0) & (y != 0)
    L.append(f"   rilis yang DIPAKAI (sepakat): {int(sama.sum())}, mentah {pct(int((-ur2[sama] == y[sama]).sum()), int(sama.sum()))}")

    # 4. versi live (vintage H−1)
    kv = kllsw_live(x)
    ganti = s16 & (kv != kl) & (kl != 0)
    ur2v = np.sign(kv + pk)
    tbv = tutup(ur2v, y, th)
    r = {nm: sk(tbv, y, m) for nm, m in (("2016–26", s16), ("LAMA", lama), ("BARU", baru), ("2022+", th >= 2022))}
    L.append(f"4) KLLSW dengan vintage CCSA yang berlaku H−1 (bukan rilis pertama): tanda berubah di {int(ganti.sum())} dari "
             f"{int((s16 & (kl != 0)).sum())} rilis 2016–26. UR2 versi ini: " +
             " | ".join(f"{k} {pct(*v)}" for k, v in r.items()))

    # 5. bootstrap & tanpa tahun terbaik
    ok = s16 & (tb != 0) & (y != 0)
    hit = (tb[ok] == y[ok]).astype(float)
    rng = np.random.default_rng(5)
    bs = np.array([hit[rng.integers(0, len(hit), len(hit))].mean() for _ in range(5000)])
    L.append(f"5) Bootstrap 5.000× tutup kertas 2016–26: {hit.mean() * 100:.1f}% (95%: {np.percentile(bs, 2.5) * 100:.1f}–"
             f"{np.percentile(bs, 97.5) * 100:.1f}%)")
    per = {Y: sk(tb, y, th == Y) for Y in range(2016, int(th.max()) + 1)}
    per = {Y: v for Y, v in per.items() if v[1]}
    terbaik = max(per, key=lambda Y: (per[Y][0] - per[Y][1] / 2, per[Y][1]))
    k_, n_ = sk(tb, y, s16 & (th != terbaik))
    L.append(f"   tanpa tahun terbaik ({terbaik} {per[terbaik][0]}/{per[terbaik][1]}): {pct(k_, n_)}; "
             f"tahun ≥ 50%: {sum(1 for v in per.values() if v[0] / v[1] >= 0.5)}/{len(per)}")

    # 6. binomial
    k, n = int(hit.sum()), len(hit)
    p_dn = float((y[ok] < 0).mean())
    L.append(f"6) Binomial satu sisi 2016–26 ({k}/{n}): vs 50% p {binom_p(k, n, 0.5):.3f}; vs kecenderungan dasar "
             f"'selalu TURUN' pada rilis yang sama ({p_dn * 100:.1f}%) p {binom_p(k, n, p_dn):.3f} "
             "(tanpa koreksi banyak uji)")
    L += kesimpulan(x, y, th, tb, ok, lama, baru, binom_p(k, n, p_dn))
    teks = "\n".join(L) + "\n"
    isi = OUT.read_text(encoding="utf-8")
    tanda = "\n## Cek ketahanan UR2"
    if tanda in isi:
        isi = isi[: isi.index(tanda)].rstrip("\n") + "\n"
    OUT.write_text(isi + teks, encoding="utf-8")
    print(teks)


if __name__ == "__main__":
    main()
