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

## 7. Lanjutan 13 Okt sore — pengguna menolak "50:50"

Kode: `research/cpi_skenario.py`. Hasil: `docs/eksternal/hasil_cpi_skenario.txt`.

### Informasi baru yang belum dipakai sebelumnya

- **Kalshi punya puluhan pasar per komponen.** Potret 13 Okt 14:20 UTC disimpan di
  `data/research/eksternal/cpi_dasar/kalshi_live_20261013.json`. Untuk September:
  - **Inti m/m:** ≤ 0,1 21% • 0,2 42–48% • ≥ 0,3 33–37%.
  - **Total m/m:** ≤ 0,5 40% • 0,6 46% • ≥ 0,7 14,5%.
  - **y/y:** ≥ 3,7 51–53%.
  - **Inti y/y:** 2,4 44–56%.
  - **Kombinasi:** total ≥ 0,5 & inti 0,2 = 43,5%; total ≥ 0,5 & inti ≥ 0,3 = 38,5%.
  - Pasar per komponen (bensin, tiket pesawat, mobil bekas, shelter) sepi transaksi, jadi tidak dipakai.
- **Cleveland Fed** (9 Okt): total 0,53, inti 0,20.
- **Preview analis** (investingLive & MUFG, 11–12 Okt):
  - Konsensus kalender Westpac: total 0,6 / y/y ±3,7; inti 0,2 / inti y/y **2,4**. MUFG: y/y 3,6.
  - Inti Agustus 0,3 terdongkrak SATU KALI oleh perubahan metode jasa telepon.
  - Hotel & mobil bekas diperkirakan berbalik turun; tiket pesawat naik (avtur).
  - Konteks: The Fed menaikkan bunga 16 Sep, payroll +29 ribu, peluang naik lagi di Oktober ±25%.
  - Karena efek satu kali itu, perkiraan inti `cpi_dasar` (0,29) ikut terdongkrak (memakai inti bulan lalu).

### Uji baru

- **A. Konsistensi inti (YOYc).** Bila konsensus inti y/y (Nasdaq) lebih tinggi dari yang tersirat oleh konsensus inti m/m
  (selisih ≤ −0,03, seperti besok: 2,5 vs 2,43), inti m/m keluar di bawah perkiraan hanya **3/33** (dasar 36%, p 0,0005).
  - LAMA 3/23 (p 0,009), BARU 0/10 (p 0,02).
  - Tetap kuat di ambang 0,02–0,04.
  - Catatan: konsensus Westpac/investingLive inti y/y = 2,4. Ketidakkonsistenan ini hanya ada di survei Nasdaq, dan survei
    itulah yang diuji secara historis.
- **B. "Total dibaca dulu" DITOLAK.** Saat kejutan total ≠ inti, emas mengikuti inti:
  - detik 2: inti 76% vs total 55%;
  - detik 5: inti 86%;
  - lonjakan menit 1: inti 78%.
  - Detik 1 tetap noise.
- **C. Mesin skenario.** Peluang skenario dari Kalshi (total × inti) dikalikan hasil dolar nyata per sel (tick Exness 2016+,
  beli di ask t−1 dtk, jual di bid).

  Peluang inti versi Kalshi:

  | | LAMA | BARU | 2024+ |
  |---|---|---|---|
  | Peluang naik detik 2 | 45% | **61%** | **76%** |
  | BUY tutup detik 2 ($/oz) | −0,79 | **+0,52** | **+1,32** |
  | BUY tahan s/d detik 10 | −1,02 | +0,01 | +0,78 |
  | SELL tutup detik 2 | −0,24 | −1,38 | −2,04 |

  Peluang inti versi YOYc (di bawah 9%, sesuai 45%, di atas 45%):

  | | LAMA | BARU | 2024+ |
  |---|---|---|---|
  | Peluang naik detik 2 | 38% | 55% | **70%** |
  | BUY tutup detik 2 ($/oz) | −0,96 | −0,09 | **+0,58** |
  | BUY tahan s/d detik 10 | −1,52 | **−1,52** | **−1,14** |

  Hasil per sel sejak Okt 2021 (BUY detik 2 / detik 10, $/oz):
  - Inti di atas: −1,85/−7,49 (total sesuai), −2,45/−5,92 (total di atas).
  - Inti sesuai & total sesuai: +1,67/−1,69.
  - Total di bawah: +3,95/+11,46.
  - Terburuk: 2024-10-10 −10,58; 2024-09-11 −7,65 (keduanya inti di atas).

### Jawaban tegas untuk CPI 14 Okt 2026

1. **Angka:** inti m/m 0,2 atau 0,3, hampir pasti TIDAK di bawah (Kalshi 79%; aturan YOYc 91%). Total 0,5–0,6.
2. **Emas detik 1–2:** condong **NAIK**. Peluang 61–76% (BARU–2024+). Tidak terbukti sebelum 2021 (38–45%).
3. **Rencana modal kecil:**
   - BUY 1 detik sebelum rilis, **TUTUP DI DETIK 2**.
   - Jangan lentur, jangan tahan ke detik 10. Bila inti 0,3 atau total dan inti sesuai, detik 10 berbalik turun (rata-rata
     −$1,7…−$7,5).
   - Leverage **maks 1:200** (±4,5 lot per 10.000 USC): modal habis bila emas melawan $20,9. Di 1:500 batasnya $8,4, dan
     2 dari 5 kejadian terburuk melewati itu.
4. **Risiko utama:** inti keluar 0,3 (peluang 36–45%). Rata-rata BUY detik 2 di skenario itu −$1,85/oz.
5. **Tampilan aplikasi** "CPI ▲ NAIK 68%" searah dengan hasil ini, jadi tidak perlu diubah. Yang perlu ditambahkan di
   aba-aba: "tutup detik 2" (menunggu "pasang").
6. **PPI 15 Okt:** masuk hanya bila CPI inti keluar ≤ 0,1 (emas naik saat PPI 76% BARU, LAMA 50%). Selain itu lewati.

## 8. DIPASANG 13 Okt malam (izin pengguna "Pasang! … otomatis jika sudah keluar") — dan koreksi bagian 7

### Koreksi: mesin skenario GAGAL uji tutup kertas, tidak dipasang

`research/cpi_skenario.py` bagian D: 46 rilis 2022–2026 dengan pasar Kalshi total & inti. Sel dan frekuensi diambil hanya
dari rilis sebelumnya.

| Metode | Arah detik 2 benar | $/oz rata-rata |
|---|---|---|
| Mesin skenario (4 varian) | 52–59% | +0,6…+1,3 |
| **Aturan aplikasi IDX|K** | **76% (31/41)** | **+1,67** |
| Selalu BUY | 67% | +0,91 |

Anjuran di bagian 7 ("BUY tutup detik 2" dari mesin skenario) dicabut sebagai dasar. Aturan aplikasi tetap menjadi penentu
arah.

### Yang lolos uji dan dipasang

**1. Perbaikan data pasar Kalshi** (`cloud/api/_kalshi.fetch`)
- API `status=open` mengembalikan 0 event untuk KXCPICORE & KXCPIYOY. Akibatnya cloud tidak pernah membaca pasar inti dan
  y/y, sehingga saringan "Kalshi inti berlawanan" dan situasi ⚖️ inti tidak pernah aktif.
- Kini pasar diambil tanpa filter lalu disaring status active/open, dengan 1× ulang bila kena batas laju (429) dan cache
  60 detik.

**2. Konsistensi inti (YOYc)** (`_cpi_detik.yoyc` / `pakai_yoyc`, `cpi_detik.json["yoyc"]` dari `cpi_skenario simpan`, env
`CPI_YOYC`)
- Tebakan aplikasi NAIK saat konsensus inti y/y > tersirat (selisih ≤ −0,03), tutup kertas:

  | Tebakan NAIK | n | Detik 2 benar | Tutup detik 2 | Lentur |
  |---|---|---|---|---|
  | YOYc −1 (semua) | 11 | 55% | −$0,12 | **−$3,29** |
  | YOYc −1, LAMA | 6 | 33% | −0,78 | −0,60 |
  | YOYc −1, BARU | 5 | 80% | +0,66 | **−6,51** |
  | Biasa (semua) | 42 | 71% | +1,48 | +4,00 |
  | Biasa, LAMA | 20 | 60% | −0,63 | −0,04 |
  | Biasa, BARU | 22 | 82% | +3,40 | +7,66 |

- Lentur jauh lebih buruk dari biasa di KEDUA periode.
- → Tebakan tetap tampil tetapi **⚠️ lemah** (persen 55%, kurva per detik dari situasi ini). 💥 Modal kecil: "JANGAN • bila
  tetap masuk BUY: TUTUP detik 2, jangan lentur" (`allin.keluar = detik2`).
- Baris 🧮 "inti y/y tersirat … → inti m/m jarang DI BAWAH (dulu 3 dari 33 rilis)" di 🔄 Data terbaru.
- Baris ⚖️ lama disembunyikan bila YOYc aktif, karena situasinya lebih khusus.

**3. PPI diperbarui setelah CPI** (`_ppi_wti.cpi_inti` / `pakai_cpi`, `ppi_wti.json["cpi_ppi"]` dari `ppi_dasar simpan`,
env `PPI_CPI`)
- Kartu "Core CPI m/m" yang sudah rilis (Act & perkiraan, ≤ 4 hari sebelum PPI) mengubah tebakan PPI-WTI:

  | Kejutan inti CPI vs tebakan PPI-WTI | Benar | LAMA | BARU |
  |---|---|---|---|
  | Searah | 74% (n 19) | 60% | 79% |
  | CPI inti sesuai perkiraan | 82% (n 17) | 50% | 100% |
  | Berlawanan | 44% (n 16) → ⚠️ lemah | 43% | 44% |

**Hasil langsung 13 Okt 21:20 WIB** (data Nasdaq + Kalshi asli):
- Baris CPI: "**CPI ▲ NAIK 54% (detik 2) ⚠️**".
- Alasan: "inti m/m jarang di bawah perkiraan (konsensus inti y/y 2,5% > tersirat 2,43%)".
- 💥 Modal kecil: JANGAN (bila masuk: tutup detik 2).

**PPI 15 Okt:** tebakan TURUN (minyak +17,5%) otomatis menjadi:
- 74% bila CPI inti 0,3;
- 82% bila 0,2;
- ⚠️ 44% bila 0,1.

Uji maju otomatis tetap berjalan (`research/uji_maju_berita.py`).
