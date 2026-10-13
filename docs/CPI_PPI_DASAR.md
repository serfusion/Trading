# 🧱 CPI & PPI dari dasar (13 Okt 2026)

Permintaan pengguna: *"berarti riset datamu hanya sebatas 'selalu buy'? tidak mendasar sama sekali!!! PERBAIKI KEMBALI RISET
SANGAT SANGAT SANGAT MENDALAM LAGI TERHADAP CPI & PPI"*.

Riset ini membangun ulang dari dasar dengan cara kerja ekonom. Angka CPI dan PPI disusun per KOMPONEN memakai data versi
hari itu (ALFRED). Hasilnya dibandingkan dengan konsensus untuk menebak kejutan. Lalu diukur apakah tebakan kejutan itu
memberi sesuatu DI ATAS pembanding "selalu NAIK" dan tren emas. "Selalu NAIK" hanya alat ukur, bukan inti riset.

- Kode: `research/cpi_dasar_data.py` (unduh ALFRED semua versi, 34 seri), `research/cpi_dasar.py`, `research/ppi_dasar.py`.
- Hasil: `docs/eksternal/hasil_cpi_dasar.txt`, `docs/eksternal/hasil_ppi_dasar.txt`.
- Data: `data/research/eksternal/cpi_dasar/`.

**Kebersihan data:**
- Angka "rilis pertama" hasil rekonstruksi dari ALFRED cocok dengan angka aktual kalender: CPI 100% (182/182 total, inti,
  dan y/y), PPI 99% (148/149).
- Tanggal PPI diambil dari hari pertama bulan acuan muncul di ALFRED: 150 rilis, Mar 2014–Sep 2026; 126 rilis punya tick
  Exness.
- Satu baris ganda (14 Jan 2026, dua bulan terbit bersamaan karena shutdown) ditemukan lalu dibuang.

## 1. Rantai sebab: ANGKA → KEJUTAN → EMAS

Mekanisme reaksi emas terhadap kejutan itu KUAT dan konsisten di dua periode.

Definisi kejutan NET:
- CPI: inti ×2 + total + y/y.
- PPI: inti ×2 + total.

| Kejutan NET | CPI LAMA lonjakan | CPI BARU lonjakan | CPI 2024+ | PPI LAMA | PPI BARU | PPI 2024+ |
|---|---|---|---|---|---|---|
| DI BAWAH perkiraan → emas naik | 85% (46) | 96% (27) | 100% (18) | 86% (28) | 91% (34) | 94% (18) |
| SESUAI | 53% (19) | 50% (6) | 50% (4) | 25% (4) | 0% (2) | 0% (2) |
| DI ATAS → emas naik | 19% (37) | 23% (26) | **10%** (10) | 31% (36) | 14% (22) | 17% (12) |

Pada **detik 2**, reaksi tidak simetris. Kejutan di bawah → emas naik 89–100% (BARU). Kejutan di atas → emas tetap naik 35%
(CPI BARU) sampai 50% (CPI 2024+). Contoh: Mei, Agustus, dan September 2026 naik di detik 2, lalu jatuh $6–35 dalam
10–30 detik. Bid dan ask sudah dicek: tidak ada keanehan feed, spread $0,16–0,60.

**Dari mana "selalu NAIK" berasal** (hasil CPI bagian e, PPI bagian porsi):
- Pada 2025, 82% rilis CPI DI BAWAH perkiraan. Pada 2026: 56% di bawah, 22% di atas. PPI BARU: 60% di bawah.
- Pada 2022–2023, kejutan di atas 50–58% → "selalu NAIK" detik 2 hanya benar 33%.
- Jadi "selalu NAIK" bukan hukum alam. Ia kebetulan dari arah kejutan beberapa tahun terakhir (inflasi melambat lebih cepat
  dari perkiraan) ditambah reaksi detik 2 yang condong naik.

## 2. Bisakah ANGKA ditebak lebih baik dari konsensus? (bottom-up per komponen)

**Yang bisa ditebak:**

| Komponen ← petunjuk | Korelasi |
|---|---|
| bensin CPI SA ← harga eceran EIA − faktor musiman tahun lalu | **0,99** |
| energi CPI ← perkiraan energi | 0,98 |
| shelter ← 3 bulan terakhir | 0,71 |
| PPI manajemen portofolio ← S&P 500 bulan lalu | 0,66 |
| mobil bekas ← Manheim 2 bulan lalu | 0,60 |
| PPI energi ← energi grosir tgl 13 | 0,73 |
| PPI total ← CPI bulan sama | 0,75 |

**Yang tidak bisa ditebak:**
- Sisa inti: korelasi dengan inti 3 bulan terakhir hanya 0,41–0,46.
- Margin dagang PPI: 0,07 (komponen paling liar).

**Konsensus tetap lebih baik dari semua perkiraan saya (RMSE):**
- CPI total: 0,125 vs 0,142.
- CPI inti: 0,123 vs 0,143.
- PPI total: 0,30 vs 0,37.

Ekonom memakai data yang sama: bensin, Manheim, dan S&P sudah masuk ke angka mereka.

**Uji ENCOMPASSING** (apakah perkiraan tahu sesuatu yang konsensus tidak tahu, di luar sampel):

| Perkiraan | LAMA | BARU | 2024+ |
|---|---|---|---|
| CPI total | t +2,3 (ada info) | t ≤ 0,7 (hilang) | – |
| CPI inti | – | – | t +2,1 |
| PPI inti | t +3,2 (ada info) | t 1,0 (hilang) | – |

Sisa informasi kecil dan memudar sejak 2021.

**Arah kejutan dipisah per sisi tebakan** (selisih ≥ 0,08). Inilah uji yang dulu terlewat:

| Perkiraan | Tebakan DI BAWAH | Tebakan DI ATAS |
|---|---|---|
| CPI inti | LAMA 10/10 benar, BARU 10/15 | **3 dari 7 benar** → tidak terbukti |
| PPI total | BARU 70% (16/23) | LAMA 78% (7/9), BARU 70% (7/10) |
| PPI inti | BARU 71% (15/21) | BARU **31%** (4/13) → gagal |

Hipotesis lain yang diuji:
- **Anchoring** (peramal lambat mengikuti tren inflasi): DITOLAK, 42–51%. Pada 2024+ malah terbalik dan tidak konsisten.
- **Musiman sisa Januari:** inti DI ATAS 8 kali, di bawah 1 kali (LAMA 5/3/1, BARU 3/2/0). Ini fenomena yang dikenal di
  literatur, tetapi n kecil. Kandidat untuk rilis Februari, bukan untuk Oktober.
- **Kalibrasi Kalshi** (2022–2026): condong kuat ke bawah (≤ −0,3) → nyata di bawah 88% (total) / 62% (inti). Condong
  kuat ke atas pada inti → 67% di atas. Condong lemah (±0,1–0,3) ≈ campur. Kalshi berguna hanya saat condong kuat.
- **CPI → PPI** (CPI bulan sama terbit lebih dulu, 75 rilis): kejutan inti CPI searah kejutan inti PPI di LAMA 71% dan
  BARU 74%. Ini hubungan dasar terkuat yang ditemukan untuk PPI. Tetapi emas saat PPI setelah CPI inti di atas = 50%;
  setelah CPI inti di bawah = BARU 76% / LAMA 50%.

## 3. Apakah tebakan kejutan menambah sesuatu DI ATAS "selalu NAIK"?

Tahap 2 (logistik) dan tahap 3 (rantai Bayes: sumber → peluang kejutan NET → peta mekanisme → peluang emas). Semuanya
tutup kertas per tahun.

- **Kejutan NET** tertebak 60–72%. Itu batas yang bisa dicapai dari data publik.
- **Arah emas TIDAK lebih baik dari "selalu NAIK":**
  - McNemar p 0,08–1,00.
  - Log-loss model 0,664–0,814 vs konstanta 0,698.
  - Sejak 2024, "selalu NAIK" malah menang.
- **Aritmetikanya** (CPI BARU lonjakan): bila peluang kejutan di atas = 65% dan di bawah = 35%, maka peluang emas naik =
  0,65 × 23% + 0,35 × 96% ≈ 49%. Untuk menebak TURUN dengan yakin, peluang kejutan di atas harus ≥ 75–80%. Hanya Kalshi
  condong kuat yang kadang mencapainya, dan itu jarang.
- **Itulah alasan tebakan TURUN selalu lemah**, bukan karena riset hanya "selalu buy". Tebakan NAIK kuat karena kejutan di
  bawah hampir pasti diikuti emas naik. Tebakan TURUN butuh kepastian angka yang tidak tersedia.

**"Angka pasti" tidak mungkin.** Plafon walau kejutan diketahui sempurna: lonjakan 85–100% (di bawah) / 77–90% turun (di
atas). Angka tidak bisa ditebak lebih dari ±70%, jadi gabungannya ±60–68%.

## 4. CPI 14 Okt 2026, 12:30 UTC (bulan acuan September)

Data yang tersedia:
- **Konsensus:** m/m 0,6, inti 0,2, y/y 3,6.
- **Bensin SA:** diperkirakan **+9,8%** (EIA +7,3%, musiman −2,4) → kejutan energi besar. Avtur +17,8%.
- **Perkiraan saya:**
  - total fit **0,59** (sesuai 0,6);
  - inti fit **0,29** (di atas 0,2, tetapi tebakan inti DI ATAS historisnya 3/7 → tidak terbukti);
  - y/y tersirat 3,70 (di atas).
- **Kalshi langsung** (13 Okt 14:20 UTC):
  - m/m: atas 15%, sesuai 45%, bawah 41% → condong DI BAWAH, lemah (−0,26). Historis condong −0,3…−0,1: bawah hanya 33%.
  - y/y: atas 52%, bawah 13% → condong DI ATAS.
  - Pasar inti tidak terbuka.
- **Rantai Bayes:** peluang kejutan NET di atas 51–66%, di bawah 19–34% → **peluang emas naik 41–51%**, lempar koin atau
  sedikit condong turun.

Kesimpulan:
- Petunjuk BERLAWANAN. Tidak ada keunggulan dasar untuk modal kecil. Saran: **jangan masuk 1 detik sebelum rilis**.
- Kalau tetap ingin, pakai lot kecil dan tutup di detik 2. Jangan "lentur" sampai detik 10: September 2026 detik 2
  +$2,5, detik 10 −$34,9.
- Tampilan aplikasi "CPI ▲ NAIK 68%" (jalur Kalshi) tidak diubah tanpa izin.
- Usulan untuk situasi berlawanan seperti ini: tampilkan "⚖️ berlawanan ≈ 50:50". Menunggu kata "pasang".

## 5. PPI 15 Okt 2026, 12:30 UTC (bersamaan Retail, Empire, Philly, klaim)

- **Konsensus:** total 0,5, inti 0,3.
- **Komponen:** energi grosir tgl 13 **+15,9%**, avtur +17,8%, S&P September −0,5% (Agustus +3,1%), makanan 3 bulan
  −0,46, margin BBM menyempit −$0,11/galon.
- **Perkiraan sebelum CPI terbit:** total fit **0,32** (di bawah 0,5), inti fit 0,24 (di bawah 0,3). Perkiraan fisik
  berbasis energi 1,79 (jauh di atas). Keduanya bertentangan.
- **Setelah CPI terbit**, hitung ulang perkiraan PPI total dari angka CPI:

| CPI total | PPI total fit |
|---|---|
| 0,4 | 0,39 |
| 0,6 | 0,52 |
| 0,8 | 0,66 |

- Kejutan inti CPI searah kejutan inti PPI di 74% rilis BARU.
- Emas saat PPI: hanya "CPI inti di bawah → emas naik saat PPI" yang lumayan di BARU (76%, n 17), dan tidak terbukti di
  LAMA (50%).
- **Saran:** tunggu hasil CPI. Bila CPI inti di bawah perkiraan → PPI condong NAIK (belum terbukti di LAMA). Selain itu
  lewati.

## 6. Yang belum bisa / perlu izin

- **Data yang belum ada:**
  - Manheim 2026: file xlsx berhenti Nov 2025. Situs Cox Automotive perlu dicek.
  - Konsensus inti y/y CPI 2013–2023 tidak ada di ForexFactory.
  - Bobot komponen resmi BLS (relative importance) belum dipakai; masih bobot kasar.
- **Usulan (menunggu "pasang"):**
  1. Kartu CPI menampilkan peluang kejutan NET + peta mekanisme (rantai Bayes) menggantikan satu jalur Kalshi, dengan
     label ⚖️ bila berlawanan.
  2. Kartu PPI diperbarui otomatis setelah CPI bulan sama terbit.
  3. Tebakan TURUN (CPI di atas) selalu diberi ⚠️ beserta aritmetikanya.
- **Uji maju otomatis** (`research/uji_maju_berita.py`) akan menilai tebakan 14 & 15 Okt setelah rilis.
