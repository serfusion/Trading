# 📍 Gaya masuk 1 detik SEBELUM rilis, tahan 1 detik s/d 3 menit (15 Okt 2026)

Permintaan pengguna: *"Perlu diperhatikan style trading saya entry 1 detik sebelum release news dan bertahan 1 detik hingga
1–3 menit ke depan, karena entry pada detik ke 2 pasti delay dan pasti tertinggal jauh. Terkadang menunggu news di bawah XAU
lama muncul, terkadang tidak muncul, saya mau langsung muncul."*

Riset: `python -m research.masuk_pra` → `cloud/api/masuk_pra.json` (ringkas untuk cloud), `docs/eksternal/hasil_masuk_pra.txt`
& `.json` (semua tabel). Cache kutipan per rilis: `data/research/eksternal/masuk_pra_kutipan.parquet` (`python -m
research.masuk_pra ulang` = hitung ulang dari tick).

## Cara uji

- **Data:** tick asli Exness XAUUSDc, yaitu bid/ask yang memuat spread asli saat berita. Mencakup 1.627 jam rilis berita USD
  2016–2026, dengan daftar rilis yang sama dengan `research/live_kurva.py`.
- **Masuk:** BUY di *ask* / SELL di *bid* kutipan terakhir ≤ t0 − 1 detik.
- **Tutup:** BUY di *bid* / SELL di *ask* pada detik h, memakai kutipan terakhir ≤ h.
- **Satuan:** hasil dalam $/ons, yaitu USD per 0,01 lot standar (= USC per 0,01 lot akun Cent).
- **Spread saat masuk:** median **$0,26**, P90 $0,60, maks $8.
- **Arah:** tebakan aplikasi sebelum rilis (`live_kurva.tebakan`). Untuk CPI dipakai aturan indeks/Kalshi, untuk PPI minyak WTI,
  dan untuk berita lain petunjuk KEJ. Hanya **281 rilis yang punya tebakan** (CPI 91, ISM 87, PPI 69, GDP 34). Berita lain
  ≈ 50:50.
- **Pembanding:** selalu BUY pada rilis yang sama, dan arah acak (rata-rata BUY & SELL).
- **Periode:** LAMA (< Okt 2021) dan BARU.

## 1. Masuk t−1 searah tebakan, tahan tetap

| Tahan | Untung (semua tebakan, n 281) | LAMA | BARU | Selalu BUY LAMA / BARU |
|---|---|---|---|---|
| **1 dtk** | **27%** (−$0,05) | 17% | 37% | 16% / 34% |
| 2 dtk | 46% (+$0,32) | 33% | 59% | 33% / 54% |
| 5 dtk | 53% (+$0,60) | 43% | 64% | 43% / 55% |
| 30 dtk | 58% (+$0,64) | 54% (+$0,06) | 62% (+$1,21) | 41% / 55% (+$1,26) |
| 1 mnt | 58% (+$0,48) | 53% (+$0,00) | 62% (+$0,96) | 49% / 56% (+$1,51) |
| 3 mnt | 53% (+$0,61) | 50% (+$0,00) | 57% (+$1,23) | 45% / 56% (+$1,73) |

Per arah tebakan, tahan 1 menit (jujur, per periode):

| Tebakan | Semua | LAMA | BARU | Status 📍 |
|---|---|---|---|---|
| CPI **NAIK** (53) | **74%**, +$2,81 | 73%, **−$0,05** | 74%, +$5,56 | ⚠️ belum terbukti (LAMA ≈ impas) |
| CPI TURUN (38) | 42%, −$2,00 | 43% | 42%, −$3,15 | ✗ jangan |
| PPI **NAIK** (31) | 65%, +$1,22 | 50%, +$0,42 | 76%, +$1,89 | ⚠️ belum terbukti |
| PPI TURUN (38) | 55%, +$0,03 | 50% | 61% | ✗ jangan (≈ impas) |
| ISM TURUN (39) | 56%, +$0,27 | 55% | 59% | ⚠️ belum terbukti |
| ISM NAIK (48) | 52%, +$0,23 | 46% | 59% | ✗ jangan |
| Tanpa tebakan | acak −$0,37 | | | ✗ jangan (lempar koin − spread) |

**Kesimpulan bagian 1:**

- **Tutup di detik 1 hampir selalu rugi** (untung 16–27%). Penyebabnya spread berita, dan emas belum bergerak di detik 1.
- Masuk t−1 searah tebakan lalu tahan 30 detik–1 menit:
  - sebelum Okt 2021 **impas**;
  - sejak Okt 2021 untung, tetapi pada periode yang sama selalu-BUY juga untung (tren emas naik).
- Tebakan **TURUN** CPI/PPI rata-rata rugi.
- **Tidak ada kombinasi yang "teruji"** (≥ 60% di kedua periode dengan rata-rata > 0). Yang terbaik adalah CPI/PPI NAIK, berstatus
  ⚠️ belum terbukti.

Aturan kelola dicoba di LAMA lalu diuji di BARU (144 aturan: tutup bila detik 1/2 berlawanan, TP/SL $1–5). Hasilnya **tidak
lebih baik** dari tahan tetap 30 detik (BARU +$1,16–1,38 vs +$1,21).

## 2. ⚡ Setelah masuk t−1: tahan atau tutup di detik 2

Ini berlaku untuk posisi apa pun (BUY atau SELL) di semua rilis, karena keputusannya memakai gerak emas di detik 2, bukan tebakan.
Gerak dihitung dari harga tengah 1 detik sebelum rilis, ambang ≥ $0,50.

| Kelompok | Searah posisi → untung bila ditahan 10 dtk / 30 dtk / 1 mnt / 3 mnt | Berlawanan → kembali untung bila ditahan 1 mnt | Rata-rata berlawanan: tutup detik 3 vs tahan 1 mnt |
|---|---|---|---|
| **Semua** (829) | **89% / 82% / 79% / 77%** (LAMA 79 / BARU 78% di 1 mnt) | **14%** | −$2,90 vs −$3,24 |
| CPI (85) | 89 / 80 / 76 / 72% | 20% | −$4,24 vs −$4,84 |
| PPI (68) | 82 / 74 / 75 / 75% | 21% | −$2,26 vs −$1,93 |
| NFP (93) | 95 / 85 / 83 / 77% | 13% | −$5,26 vs −$7,68 |
| FOMC (45) | 82 / 78 / **64** / 62% | 31% | −$3,65 vs −$3,50 |
| ISM (160) | 93 / 86 / 84 / 83% | 8% | −$2,63 vs −$2,74 |
| Retail (65) | 88 / 78 / 78 / 74% | 14% | −$2,26 vs −$2,27 |

- Emas **hampir diam** (< $0,30) di detik 2 (643 rilis): posisi t−1 rata-rata rugi ±spread (−$0,36 s/d −$0,40). Ditahan sampai
  3 menit hanya 38% kembali untung.
- **Detik 1** kurang bisa dipercaya untuk CPI dan FOMC: gerak searah ≥ $0,50 di detik 1 hanya 58–63% bertahan s/d 1 menit.
  Untuk ISM, Retail, dan NFP detik 1 sudah 74–90%.

## 3. Yang dipasang (aplikasi 4.45, cloud)

- **Baris di bawah XAU langsung muncul**:
  - **Aplikasi:** respons terakhir disimpan di HP (`NewsCache.kt`, file `berita_cache.json`) dan langsung tampil saat aplikasi
    dibuka. Hitung mundur dihitung HP sendiri.
  - **Satu permintaan bersama:** dulu 2–3 GET penuh berjalan bersamaan saat aplikasi dibuka.
  - **Gagal → coba lagi** 5/10/20/40 detik (dulu kosong lalu menunggu 60 detik).
  - **Menjelang/sesudah rilis** (≤ 15 mnt sebelum s/d 10 mnt sesudah): diperbarui tiap 20 detik.
  - **Data tersimpan sudah lewat:** dipakai berita berikutnya dari daftar.
  - **Cloud (`chat.py`):**
    - baris Supabase dibaca **sekaligus** (`MemoStore` + `Supabase.get_many`; dulu ±20 perjalanan berurutan, kini 1);
    - langkah info (🗣️ pernyataan, 👥 sentimen, 📉 pudar, 🎲 sebaran Kalshi, arsip GitHub) dilewati bila GET sudah > 20 detik
      (`persiapan.dilewati`, `waktu_dtk`);
    - `pra_satu` cadangan ≈ 50% bila galat (`_pra_aset.cadangan`, alasan di `pra_galat`).
- **📍 sebelum rilis** (`_masuk_pra.t1` → `pra_satu.t1`, baris kecil di bawah baris utama XAU). Contoh:
  "📍 Masuk t−1 BUY → tahan 30 dtk–1 mnt: untung 68–74% (53 rilis) ⚠️". Tebakan TURUN CPI dan berita tanpa tebakan menampilkan
  **"JANGAN"**. Detail (ketuk) memuat angka per jangka, LAMA/BARU, dan pembanding selalu BUY. Di T−15…0 detik baris ⚡ menulis
  "📍 Siap/MASUK BUY t−1 ⚠️ belum terbukti" atau "📍 t−1: jangan masuk".
- **📍 setelah rilis** (`pra_satu.lanjut.posisi`, `StatusCard.posisiBaris`): dua baris, satu untuk BUY dan satu untuk SELL.
  - **Searah:** "TAHAN s/d 1–3 mnt: untung 30 dtk 82% • 1 mnt 79% • 3 mnt 77%".
  - **Berlawanan:** "TUTUP SEKARANG: ditahan s/d 1 mnt hanya 14% balik untung".
  - **Hampir diam:** "rata-rata rugi ±spread".
  - **Detik 1 belum pasti** (searah < 70% s/d 1 mnt, mis. CPI/FOMC): "putuskan di detik 2".
  - **Pemilihan angka:** kelompok berita dipakai bila ≥ 20 rilis, selain itu semua berita.
  - **Urutan:** baris posisi tebakan sebelum rilis tampil lebih dulu.
  - Info "masuk sekarang (detik 2,5)" dibuang dari baris ⚡LIVE.
- ⓘ Peringkat: 4 baris 📍 masuk t−1 per tebakan, plus 1 baris posisi t−1 searah detik 2 (`research/peringkat.py`, satuan $/oz).
- Env `MASUK_PRA=0` mematikan 📍. Info saja, tanpa order.

## Catatan jujur

- Angka bagian 2 memakai gerak detik 2 dari tick Exness. Aplikasi membaca emas token (XAUT OKX dll.), yang ±1 detik lebih cepat
  dari MT5, sehingga gerak yang terlihat bisa sedikit berbeda.
- Slippage saat menutup posisi di detik 2–3 belum dihitung. Hanya spread asli yang dihitung.
- Bagian 1 memakai tebakan riset (CPI IDX|K tanpa saringan ⚠️ lemah, PPI WTI tanpa CPI→PPI). Status aplikasi tidak pernah lebih
  tinggi dari status tebakan utamanya.
- Bagian 2 tidak memprediksi arah sebelum rilis. Nilainya ada pada mengelola posisi: tahan yang searah gerak detik 2, tutup yang
  berlawanan. Rugi posisi yang berlawanan tetap besar ($2–5/ons), jadi besar lot harus siap menanggungnya. Exness membatasi
  leverage 15 menit sebelum s/d 90 detik sesudah berita (HMR).
