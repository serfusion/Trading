# 🔗 Emas jatuh dalam lalu memantul → apakah BTC & koin lain ikut naik? (9 Okt 2026)

Pertanyaan pengguna: *"xau / token crypto lain akan naik apabila xau telah turun sangat dalam; ketika dia pullback ke atas
kembali mulai dari xau, btc, koin lainnya ikut naik … saya mencoba membeli beberapa koin, mereka serempak ikut naik."*

Skrip: `research/xau_kripto.py` (uji 1–4) dan `python -m research.xau_kripto rezim` (uji 5), replay kode cloud
`research/pulih_replay.py`. Hasil mentah: `docs/eksternal/hasil_xau_kripto.txt`, `hasil_xau_kripto_rezim.txt`,
`hasil_pulih_replay.txt`. Modul cloud: `cloud/api/_pulih.py` (DIPASANG 9 Okt 2026), tes `tests/test_cloud_pulih.py`.

Data: XAU H1 2018–Sep 2026, BTC H1, 19 koin Binance (ETH, BNB, SOL, XRP, ADA, DOGE, TRX, LINK, AVAX, DOT, LTC, BCH, XLM,
ATOM, ETC, UNI, NEAR, AAVE, FIL). Beli spot di close jam pantulan, jual H jam kemudian, biaya 0,2% pulang-pergi.
**LAMA** = 2018 – Sep 2021, **BARU** = Okt 2021 – 2026.

## Ringkasan singkat

| | LAMA | BARU |
|---|---|---|
| Beli koin kapan saja, tahan 48 jam (dasar) | naik 54%, +0,6% | naik 50%, ±0% |
| Emas jatuh ≥ 5 ATR lalu pantul 38%, **tanpa** syarat korelasi | lebih baik dari dasar | hampir sama dengan dasar |
| **Sama + emas & BTC sedang searah (korelasi 60 hari ≥ 0,2)** | **51 kejadian, naik 63%, +1,3%** | **111 kejadian, naik 64%, +1,1%** |
| Dasar pada kondisi korelasi yang sama | +0,9% | −0,2% (naik 46%) |

- Ide pengguna **sebagian benar**: setelah emas jatuh dalam lalu memantul, keranjang kripto naik rata-rata ±1% dalam
  48 jam, tetapi **hanya saat emas dan BTC memang sedang bergerak searah** (2020, sebagian 2022–2025, hampir seluruh 2026).
  Saat korelasinya rendah, efeknya hilang (BARU: naik 50%, +0,3%).
- **Bukan "selalu serempak"**: rata-rata hanya 56–62% koin naik bersamaan; ≥ 80% koin naik bareng di 41–51% kejadian.
- **Emas tidak bergerak duluan.** Korelasi jam ini emas dengan jam berikutnya BTC +0,03 (≈ nol). Urutan "XAU → BTC →
  koin lain" tidak terlihat di data per jam; yang ada: keduanya bergerak di jam yang sama, lemah.
- Untung kecil, rugi bisa besar: median +1,3% per 48 jam, tetapi 5% kejadian terburuk ≤ −6% dan satu kali −20%
  (keranjang alt), BTC terburuk −10%. 2025 negatif (−0,5%).
- Pemisah korelasi **ditemukan setelah melihat data 2026** (korelasi tinggi tahun ini) → belum terbukti seperti aturan
  yang dipilih murni dari LAMA. Status: **DIPASANG 9 Okt 2026** sebagai sinyal info (pengguna: "WR dan profit tinggi? Jika
  tinggi pasang" — peluang naik 63–65% di kedua periode, setara syarat 🌊 WR ≥ 62% dua periode), tanpa order otomatis.

## 1. Mekanisme: apakah emas & BTC benar-benar bergerak bersama?

Korelasi return harian XAU vs BTC per tahun: 2018 +0,01 · 2019 +0,12 · 2020 +0,34 · 2021 −0,00 · 2022 +0,13 · 2023 +0,12 ·
2024 +0,15 · 2025 +0,07 · **2026 +0,43**. Porsi hari dengan korelasi 60 hari ≥ 0,2: 2018 0% · 2019 34% · 2020 83% ·
2021 0% · 2022 43% · 2023 46% · 2024 41% · 2025 24% · **2026 96%**.

Artinya pengalaman pengguna tahun ini (emas pulih → koin ikut naik) wajar: 2026 adalah tahun dengan korelasi emas–kripto
tertinggi di data. Pada tahun lain (2018, 2021) keduanya hampir tidak berhubungan. Penjelasan umum (bukan diuji di sini):
saat dolar/likuiditas global menjadi penggerak utama, emas dan kripto sama-sama dibeli/dijual sebagai "aset non-dolar";
saat penggerak masing-masing berbeda (ETF kripto, halving, krisis bank), hubungan itu lepas.

Lead-lag (return XAU jam t vs BTC jam t+k, 2018–2026): k=0 +0,090, k=1 +0,027, k=2 −0,001 … → tidak ada jeda yang bisa
dimanfaatkan ("tunggu emas naik dulu lalu beli BTC sejam kemudian" tidak didukung data).

## 2. Uji kejadian tanpa syarat korelasi (336 kombinasi)

Kejadian: dalam N jam terakhir emas jatuh dari puncak ke dasar ≥ k × ATR24 (atau ≥ d%), dasar ≤ 12 jam lalu, lalu close
baru saja memantul ≥ r dari jarak jatuh. N 6/12/24/48, k 3–6 atau d 1–2%, r 0,382/0,5, tahan 12/24/48/72 jam.

- Aturan terbaik dipilih dari LAMA (jatuh 1,5% dalam 12 jam, pantul 50%, tahan 72 jam): LAMA alt +3,5% (p-acak 0,017) →
  BARU −0,8% (p 0,91). **Gagal di BARU.**
- 61% kombinasi BTC positif di kedua periode (kebetulan ≈ 25%), tetapi rata-rata kelebihan BARU hanya +0,07% → efek
  umum "pantulan emas" hampir nol sejak 2021.
- Jatuh sangat dalam (≥ 5 ATR) lebih baik dari jatuh biasa, tetapi BARU p 0,13–0,40 (belum meyakinkan).

## 3. Rezim korelasi (uji 5, tahan 48 jam)

| Aturan | Korelasi | LAMA | BARU |
|---|---|---|---|
| N24 k5 r0,382 | ≥ 0,2 | n 51, naik 63%, +1,34% | **n 111, naik 64%, +1,11%** |
| N24 k5 r0,382 | < 0,2 | n 122, naik 61%, +1,36% | n 135, naik 50%, +0,28% |
| N24 k5 r0,5 | ≥ 0,2 | n 26, 54%, +1,63% | n 91, 63%, +1,30% |
| N12 k5 r0,5 | ≥ 0,2 | n 16, 62%, +2,37% | n 39, 59%, +1,19% |
| N6 k5 r0,382 | ≥ 0,2 | n 13, 77%, +4,02% | n 26, 65%, +1,49% |
| N24 k4 r0,5 | ≥ 0,2 | n 49, 55%, +1,25% | n 151, 53%, +0,45% |

Kepekaan (63 varian: jendela korelasi 30/60/90 hari × ambang 0,1/0,2/0,3 × 5 aturan tetangga × tahan 24/48/72 jam):
BARU 57 dari 63 varian p-acak ≤ 0,05 dan rata-rata positif di semua varian; LAMA positif di semua varian tetapi umumnya
TIDAK signifikan (hanya 7 dari 63 varian p ≤ 0,05; p 0,001–0,59) — di LAMA kripto memang sedang naik kencang, sehingga beli acak pun sudah untung.
Aturan terpilih (korelasi 60 hari ≥ 0,2, N24 k5 r0,382, 48 jam): LAMA +1,34% vs dasar rezim +0,91% → **p 0,29 (tidak
signifikan)**; BARU +1,11% vs −0,23% → p 0,001. Per pekan (satu nilai per pekan supaya kejadian beruntun tidak dihitung
ganda): LAMA 41 pekan, +1,7% vs pekan acak +0,9%, p 0,006; BARU 85 pekan, +1,1% vs −0,2%, p < 0,001; 65–71% pekan naik.

Aturan yang dipilih untuk cloud: **N24 k5 r0,382, korelasi 60 hari ≥ 0,2, tahan 48 jam** (kejadian terbanyak di BARU,
tetangga-tetangganya juga positif). Pada harga emas 2026, 5 ATR ≈ **$90–130** jatuh dalam ≤ 24 jam (2025: $35–80).

Rincian aturan terpilih (keranjang 19 alt):
- Per tahun: 2019 +0,3% (11) · 2020 +1,6% (40) · 2022 +1,5% (17) · 2023 +0,6% (28) · 2024 +1,1% (19) · **2025 −0,5% (14)** ·
  2026 +2,1% (33). (2018 & 2021 tidak ada kejadian karena korelasi tidak pernah ≥ 0,2.)
- Sebaran BARU: alt P5 −6,0% · P25 −1,5% · median +1,3% · P75 +3,2% · P95 +8,7% · terburuk −20,0%; BTC P5 −4,7% ·
  median +0,6% · P95 +7,6% · terburuk −10,0%.
- Per koin BARU (rata per kejadian): DOGE +1,7, ETH +1,6, UNI +1,5, FIL +1,4, AAVE +1,4, AVAX +1,3, SOL +1,3, ETC +1,3,
  LINK +1,2, NEAR +1,2, XLM +1,1, ADA +1,1, BCH +1,0, BTC +1,0, BNB +0,9, XRP +0,9, ATOM +0,8, LTC +0,8, DOT +0,8, TRX ±0.
  Semua koin besar positif → efeknya "pasar kripto ikut naik", bukan satu koin khusus.
- TP/SL (5 koin besar, dicek per jam, SL dulu): TP 5%/SL 5% BARU +0,69%; TP 3%/SL 4% +0,34%; tahan 48 jam penuh +1,06%
  → TP/SL memperkecil rugi terburuk (−5%) tetapi juga memotong untung; tahan 48 jam tetap terbaik rata-ratanya.

## 4. Replay kode cloud `_pulih.py` (jam demi jam, 2018–2026)

Kode cloud asli diputar pada data riset (feed XAU 2.400 candle, BTC harian, harga 9 koin per jam): **143 dari 144 sinyal
cloud = kejadian riset**; 20 kejadian riset tidak dikirim karena keranjang 48 jam sebelumnya masih terbuka (cloud hanya
membuka 1 keranjang sekaligus). Keranjang cloud = 9 koin (BTC, ETH, SOL, XRP, BNB, DOGE, ADA, LINK, AVAX), bagi rata.

| | n | naik | rata per 48 jam | terburuk |
|---|---|---|---|---|
| LAMA | 46 | 65% | +1,49% | −13,7% |
| BARU | 97 | 63% | +1,35% | −10,5% |

Per tahun: 2019 +1,0% (10) · 2020 +1,6% (36) · 2022 +1,5% (16) · 2023 +1,4% (24) · 2024 +1,5% (15) · 2025 −0,2% (13) ·
2026 +1,9% (29). Korelasi cloud = korelasi riset untuk 420/432 kejadian; 12 sisanya awal 2018 (data < 60 hari, keduanya
kosong).

Gambaran uang (bukan janji): modal $100 per sinyal → rata-rata ±+$1,3 per 48 jam, ±12–30 sinyal per tahun → ±$15–40 per
tahun per $100, dengan kemungkinan satu sinyal −$10 s.d. −$20.

## 5. Risiko & keterbatasan (jujur)

1. **Ditemukan setelah melihat 2026.** Ide pemisah korelasi muncul karena 2026 korelasinya tinggi; LAMA searah (positif)
   tetapi per kejadian tidak signifikan (p 0,29). Bukti kuat hanya dari periode yang sama dengan tempat ide itu ditemukan
   → perlu uji maju.
2. **Korelasi bisa hilang tiba-tiba** (2021: 0% hari ≥ 0,2). Saat itu sistem otomatis berhenti mengirim sinyal — itu
   disengaja.
3. Untung kecil (±1% per 48 jam) dibanding risiko ekor (−10% s.d. −20%). Jangan pakai leverage/futures; spot saja, porsi kecil.
4. Tidak "serempak" seperti kesan pengguna: separuh kejadian hanya sebagian koin naik.
5. Data koin = Binance spot; spread/biaya bursa lain bisa lebih besar dari 0,2%.

## 6. Terpasang (9 Okt 2026, aplikasi 4.25)

Keputusan: pengguna "WR dan profit tinggi? Jika tinggi pasang". Penilaian: peluang naik 63–65% di LAMA dan BARU (replay
cloud 65% / 63%), rata-rata positif di kedua periode (+1,5% / +1,35% per 48 jam) dan 6 dari 7 tahun → setara syarat
🌊 (WR ≥ 62% di dua periode) → dipasang sebagai info. Profit per sinyal kecil dan rugi ekor besar (lihat bagian 5).

- Cloud: `cloud/api/tick.py` memanggil `_pulih.pulih_tick` setelah 🌊 (memakai candle XAU yang sudah diambil — tanpa
  kredit Twelve Data tambahan; BTC harian 250 hari & harga koin dari data-api.binance.vision), env `PULIH_SIGNALS` (0 = mati),
  baris Supabase `pulih`, 1 keranjang terbuka sekaligus, ntfy `pulih_signal` (🔗 EMAS PULIH → BELI KRIPTO • tahan 48 jam,
  harga beli 9 koin) & `pulih_close` (rata-rata & per koin setelah biaya 0,2%).
- Aplikasi 4.25: kartu 🔗 (`PulihCard.kt`: koin + harga beli dalam 📋 isi order, jam jual, angka teruji), notifikasi
  buka/jual (`Notifications.pulih`), ikut pilihan pair "SPOT", baris di 🏆 peringkat (ⓘ, `research/peringkat.py`).
- Feed live = Twelve Data. Dibanding data riset (Jul–Sep 2026) candle Twelve Data ±8% lebih kecil sehingga ATR ±9% lebih
  rendah → kejadian ±20% lebih banyak (12 vs 10 dalam 2,5 bulan; kejadian besar sama jamnya, tambahan = jatuh ±5,2–5,4
  ATR di batas bawah). Aturan tidak diubah (sampel tumpang tindih terlalu pendek untuk kalibrasi); dicatat untuk uji maju.
- Cek 9 Okt 2026 (Twelve Data 3000 candle): korelasi 60 hari XAU–BTC 0,51 (sinyal aktif bila ada pantulan), 5 ATR ≈ $70.
