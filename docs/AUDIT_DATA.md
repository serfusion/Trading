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

## G. Uji validasi tambahan CPI & PPI (`research/audit_cpi2.py` → `docs/eksternal/hasil_audit_cpi2.txt`)
| uji | CPI (aturan aplikasi) | PPI-WTI (128 rilis resmi) |
|---|---|---|
| plasebo berita (aturan dipakai di rilis 08:30 lain bulan sama) | 64–70% vs lain 47–50% ✅ khas CPI | 63% vs lain 53% ✅ khas PPI |
| plasebo waktu (searah gerak emas t−100 → t−1 dtk?) | 67% (p 0,01) — karena saringan menyisakan tebakan NAIK saat tren naik; IDX|K 59%, Kalshi 54% | 55% / BARU 49% ✅ |
| Bonferroni seluruh riset (CPI ±100 aturan, PPI ±35) | BARU detik 2 p 0,027 ✅; 2016–26 0,31 ✗; **Kalshi saja 1,0 ✗** | lonjakan BARU 0,20 ✗; detik 5 BARU 0,076 ✗ |
| jam rilis (lonjakan di t0?) | 12 "curiga" → dicek: tick melonjak tepat di t0, reaksinya kecil → jam benar | 24 "curiga" → sama, jam benar |
| per tahun: angka vs plafon | gagal 2019–21 karena tebakan ANGKA salah (plafon tetap 62–88%) | gagal 2018–21: tebakan angka 25–57% (plafon 60–100%) |

**Pembanding "selalu NAIK" pada periode yang sama (uji yang paling penting dan dulu terlewat):**
- CPI detik 2: selalu NAIK 2016–26 54%, sejak Okt 2021 61%, **2024+ 81% (26/32)**. Aplikasi 2024+ 95% (18/19) hanya karena
  semua tebakannya NAIK (TURUN disaring lemah); pada rilis yang sama aplikasi vs selalu-NAIK: 0 beda (2024+), 4 vs 1 (BARU,
  p 0,19) → **keunggulan aturan di atas tren emas BELUM terbukti**. IDX|K tebakan TURUN 2024+ 45% (5/11).
- PPI-WTI: tebakan NAIK (minyak turun) 72–91%, tebakan **TURUN (minyak naik — seperti 15 Okt 2026) lonjakan 55% (2024+ 50%),
  detik 2 39% (2024+ 30%)** → lebih buruk dari acak; vs selalu-NAIK BARU p 0,26 (lonjakan) / 0,86 (detik 2).
- Pelajaran: di pasar emas tren naik (2022–2026) tebakan NAIK tampak hebat, tebakan TURUN lemah. Selalu laporkan akurasi PER
  ARAH tebakan dan pembanding selalu-NAIK pada periode yang sama.

## H. Uji maju otomatis (mulai 13 Okt 2026)
`research/arsip_data.pra` (workflow arsip tiap jam :07) merekam tebakan CPI/PPI persis seperti aplikasi (arah, persen, jalur,
konsensus, Kalshi, jam pertama konsensus indeks) → `arsip-data:pra/<pekan>.json`; dinilai setelah rilis dengan tick Exness:
`python -m research.uji_maju_berita` → `docs/eksternal/hasil_uji_maju_berita.txt`.

## F. Cek langsung 14 Okt (terjadwal 11:40 UTC)
Pemantau mencatat jam pertama konsensus indeks CPI muncul di Nasdaq (`docs/eksternal/hasil_cek_indeks_cpi.txt`).

**Hasil (14 Okt 2026, 12 pembacaan tiap 5 mnt 11:41–12:37 UTC):**
- Konsensus **indeks CPI utama NSA** (`nsa_f` 336,65; bulan lalu 334,98) SUDAH ADA paling lambat **11:41 UTC = 49 menit sebelum
  rilis** (13 Okt 18:55 WIB masih kosong → muncul antara H−1 malam dan pagi hari rilis), nilainya tidak berubah s/d rilis.
- Konsensus **indeks inti** (`cidx_f`) KOSONG sampai sesudah rilis (sama seperti sepanjang 2026).
- Nasdaq belum mengisi angka aktual 7 menit setelah rilis (`nsa_a` kosong) → sumber Act tetap BLS/FRED.
- Kesimpulan: jalur IDX (indeks utama) **sah tanpa look-ahead** untuk rilis ini — konsensus indeks tersedia sebelum t0. Jalur
  indeks INTI tidak bisa dipakai (tidak pernah tersedia sebelum rilis 2026). Uji riwayat tetap perlu dicek per rilis: tanggal
  munculnya konsensus indeks di masa lalu tidak terekam, hanya nilainya.
- Reaksi emas (Twelve Data 1 mnt, XAU/USD): candle 12:30 open 4.153,2 → high 4.172,8 / low 4.135,2 → close 4.166,3 (menit 1
  NAIK +$13, sejalan "NAIK ⚠️ lemah" aplikasi), lalu turun ke 4.113,8 di 12:36 (−$52 dari puncak). Arah detik 1–10 perlu tick
  Exness (arsip bulanan) untuk dinilai; Act CPI belum terbaca (BLS batas harian habis, FRED belum terbit).

