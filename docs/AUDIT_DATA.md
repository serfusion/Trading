# 🧾 Audit data CPI & PPI — kenapa PPI 69% → 63% dan apakah CPI sama (13 Okt 2026)

Pertanyaan pengguna: "apakah ada metode, informasi, riset atau uji validitas yang terlewat? mengapa yang awalnya 69 turun ke 63,
apa ada data yang sangat bagus? saya curiga CPI juga sama — pelajari lebih dalam hingga menemukan metode dengan angka pasti".
Skrip: `research/audit_cpi_ppi.py` → `docs/eksternal/hasil_audit_cpi_ppi.txt`.

## Uji yang terlewat sebelumnya (sekarang dikerjakan)
1. **Kelengkapan data terhadap kalender RESMI** (FRED release dates): rilis tanpa tick dulu diam-diam tidak dihitung.
2. **Tanggal salah / ganda** di daftar rilis.
3. **Target dihitung ulang dari tick asli** untuk setiap tanggal resmi dan dibandingkan dengan tabel riset.
4. **Ketersediaan data SEBELUM rilis** (konsensus indeks CPI Nasdaq: H−1 13 Okt masih kosong).
5. **Jalur yang benar-benar dipakai live** (indeks vs Kalshi) dan unsur yang ditemukan SETELAH melihat hasil (saringan).

## PPI: penyebab 69% → 63% = DATA HILANG, bukan data yang sangat bagus
- Putaran 2: 8 rilis bersinyal minyak tidak punya tick ("tidak ada tick") → tidak dihitung. Setelah tick diunduh (putaran 3)
  kedelapannya SALAH (0/8): benar tetap 54, pembagi 78 → 86. Penyebabnya, rilis yang dulu tidak punya tick (bukan bintang 3 di
  ForexFactory) tidak hilang secara acak.
- Daftar rilis riset juga memuat 2 tanggal SALAH (2019-12-11 & 2025-09-09; resmi 12 Des & 10 Sep) dan TIDAK memuat 11 rilis
  resmi 2020–2021. Ada 7 tanggal FRED yang hanya revisi musiman Februari (bukan rilis) — dibuang.
- **Angka PPI-WTI final, 128 rilis resmi 2016–Sep 2026 (126 bertick, lengkap):**

| | lonjakan menit 1 | detik 1 | detik 2 | detik 5 | detik 10 | Bayes P(>60%) |
|---|---|---|---|---|---|---|
| 2016–2026 | **62,6%** (57/91) | 45% | 53% | 59% | 59% | 0,69 |
| sebelum Okt 2021 | 56,0% (28/50) | 42% | 46% | 48% | 52% | 0,27 |
| sejak Okt 2021 | **70,7%** (29/41) | 49% | 61% | 73% | 68% | 0,91 |
| 2024+ | 71,4% (15/21) | 48% | 62% | 76% | 71% | 0,84 |
  Keranjang energi (WTI+bensin+solar) hampir sama: 64,0% / 56,8% / 71,4%.

## CPI: TIDAK ada masalah data seperti PPI
- Tanggal: 0 tanggal salah. Rilis resmi yang tidak ada di tabel = 7 tanggal revisi musiman + 2 Jumat Agung (2017-04-14,
  2020-04-10; pasar emas tutup) → wajar.
- Target 126 rilis dihitung ulang dari tick Exness: **100% sama** (detik 2 & 10); 0 rilis bersinyal yang dulu tanpa target.
- Angka aturan aplikasi terulang persis: IDX|K + saringan detik 2 68,3% (2016–26), 53,6% LAMA, 81,2% BARU, 94,7% 2024+.
- Kebocoran konsensus indeks Nasdaq: galat konsensus indeks (median 0,07–0,21 poin) < galat konsensus m/m dibulatkan
  (0,24–0,31 poin) — wajar karena tanpa pembulatan; hampir tidak pernah persis = Act → **tidak ada tanda diisi setelah rilis**.
  TETAPI H−1 (13 Okt 18:55 WIB) konsensus indeks masih kosong → dicek langsung 14 Okt menjelang rilis (bagian F).
- **Angka per jalur (detik 2, rentang 90% bootstrap per tahun):**

| aturan | 2016–26 | sebelum Okt 2021 | sejak Okt 2021 | 2024+ |
|---|---|---|---|---|
| Aplikasi (IDX|K + saringan) | 68% (41/60) [57–79] | 54% (15/28) | 81% (26/32) [69–92] | 95% (18/19) |
| IDX|K tanpa saringan | 66% (59/89) [58–73] | 56% | 74% (37/50) [69–78] | 77% |
| **Hanya Kalshi** (jalur bila konsensus indeks belum terbit) | – | – | **65% (24/37) [55–78]** | 70% (16/23) |
| Hanya konsensus indeks | 66% (52/79) | 56% | 75% (30/40) | 80% (20/25) |
  Saringan ditemukan SETELAH melihat kesalahan Jan & Jun 2026 → angka 81–95% mengandung bias pasca-lihat; angka yang paling
  jujur untuk CPI 14 Okt (jalur Kalshi) = **±65–70% di detik 2**.

## "Angka pasti"
Tidak ada metode yang memberi kepastian di pasar; yang bisa dibuat pasti adalah ANGKANYA: dihitung dari SEMUA rilis resmi,
tanggal benar, tick asli, tanpa data hilang, dengan rentang kepercayaan. Angka di atas adalah versi itu.

## F. Cek langsung 14 Okt (terjadwal 11:40 UTC)
Pemantau mencatat jam pertama konsensus indeks CPI muncul di Nasdaq (`docs/eksternal/hasil_cek_indeks_cpi.txt`).
