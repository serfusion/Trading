# NFP mean reversion vs deterioration lanjutan (6 Okt 2026)

Mengikuti "NFP Mean Reversion Validation Framework" dari pengguna. Kode `research/nfp_mean.py`, hasil mentah
`docs/eksternal/hasil_nfp_mean.txt`. Data: **vintage ALFRED** (angka NFP persis seperti saat pertama dirilis, revisi yang
baru diketahui belakangan TIDAK dipakai), 306 rilis Mar 2001 – Agu 2026. Pendahulu yang sudah terbit sebelum rilis:
klaim pengangguran (rata 4 minggu), ADP (2011+), tingkat pengangguran 3 bulan, JOLTS lowongan (2010+), revisi bulan lalu.
ISM Employment tidak ada di FRED → belum diuji.

## Uji 1–2: apakah NFP lemah diikuti rebound?
Baseline: NFP bulan berikutnya lebih tinggi di **47%** rilis.
| Definisi pelemahan | n | Rebound | +50K | Selisih vs baseline | p (binomial > 50%) |
|---|---|---|---|---|---|
| A z24 ≤ −1,0 | 57 | 65% | 53% | +18 pp | 0,017 |
| A z24 ≤ −1,25 / −1,5 / −1,75 / −2,0 | 47 / 37 / 28 / 23 | 62% / 59% / 64% / 61% | 45–57% | +12..+17 pp | 0,07–0,20 |
| B turun 2 bulan | 68 | 57% | 38% | +10 pp | 0,14 |
| C turun 3 bulan & di bawah rata-rata | 46 | 67% | 41% | +20 pp | 0,013 |
| D Δ2 ≤ persentil 20 | 53 | 66% | 55% | +19 pp | 0,014 |
| Normal | 196 | 40% | 26% | −7 pp | |
Arah konsisten di semua ambang (bukan satu angka kebetulan). Sebagian besar karena "regresi ke rata-rata" angka pertama
NFP yang sangat berisik. Regime: berlaku 2003–07, 2010–19, 2022–26; **gagal di krisis 2008–09** (rebound 35%).

## Uji 3: indikator pendahulu memisahkan rebound vs deterioration lanjutan ✅
| Kondisi | n | Rebound | Rata perubahan |
|---|---|---|---|
| Pelemahan + pendahulu membaik (skor ≥ +2) | 31 | **68%** | +56K |
| Pelemahan + pendahulu netral | 50 | **70%** | |
| Pelemahan + pendahulu memburuk (skor ≤ −2) | 29 | **31%** | −719K (termasuk 2008/2020) |
Hipotesis framework terbukti searah: pelemahan + pendahulu memburuk = **deterioration lanjutan**, bukan rebound.
Revisi bulan lalu: pengaruh kecil (revisi turun → rebound 54% vs 44–46%).

## Uji 5: walk-forward (latih s.d. tahun sebelumnya)
Akurasi arah: NFP saja 60%, + klaim/pengangguran/revisi/skor 61%, + ADP + JOLTS (2013+) 63% (baseline 47–48%).
Saat model yakin (p ≥ 0,65): rebound 63% (n 63) / 70% (n 40, dengan ADP+JOLTS).

## Uji 6: apakah ini bisa dipakai untuk emas? ❌ (belum)
- Yang menggerakkan emas adalah KEJUTAN vs konsensus: aktual < konsensus → emas naik 1 jam 73% (+$6,5 rata);
  aktual > konsensus → naik 46% (−$3,0). Ini baru diketahui SETELAH rilis.
- Konsensus sudah memperhitungkan rebound: setelah pelemahan, konsensus sendiri memperkirakan naik di 65% kasus;
  aktual > konsensus hanya 60% (baseline 55%) → keunggulan sebelum rilis sangat tipis.
- Emas setelah pelemahan: naik 1 jam 41% (n 54); + pendahulu membaik 50%; + memburuk 38% (n 8, terlalu sedikit).
- Whipsaw (arah 15 mnt ≠ 1 jam) 22%, sama untuk kejutan kecil/besar.
Kesimpulan: model berguna untuk MEMAHAMI arah ekonomi, tetapi belum memberi entry emas sebelum rilis yang lolos.

## Kondisi sekarang (data per 6 Okt 2026)
- NFP Sep 2026 = **+29K** (Agu +162K, Jul −23K, Jun +57K); z24 −0,83 → BELUM termasuk "pelemahan ekstrem" (A/B/C/D tidak menyala).
- Pendahulu: klaim −3,6% (membaik), pengangguran 3 bulan tetap, JOLTS −6% (memburuk); ADP Okt belum rilis → skor +1 (netral).
- Model logistik: peluang NFP Okt > +29K ≈ **57%** (lemah, hampir lempar koin).
