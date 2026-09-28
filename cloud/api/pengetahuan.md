# Basis pengetahuan statistik (dibuat otomatis oleh research/event_stats.py — jangan disunting manual)

Data: kalender ForexFactory historis 2010-01–2026-01 (actual vs forecast), XAU/USD M15 2012-05–2026-09, BTC/USD H1 Bitstamp 2016–2026-09. Gerak dalam % dari harga saat rilis; perkiraan $ memakai harga emas terakhir ≈ $4,315. 'searah' = harga bergerak ke arah yang 'seharusnya' menurut kejutan (data AS lebih lemah / Fed lebih dovish → emas naik; data lebih kuat / hawkish → emas turun). 'rata' dihitung ke arah itu: pada baris kejutan BURUK, 'rata +0,24%' berarti emas rata-rata TURUN 0,24%. Jendela (15m, 1j = 1 jam, 4j, 1h = 1 hari) diukur dari open candle 15 menit tempat rilis (sudah termasuk lonjakan pertama; orang yang masuk SETELAH rilis tidak mendapat gerak candle pertama, dan spread saat rilis melebar).

## 1. Reaksi XAU/USD per jenis berita

### FOMC (suku bunga Fed) — 110 rilis
- Sesuai perkiraan / tanpa angka (n=108): 15m: naik 59%, median |gerak| 0.22%; 1j: naik 56%, median |gerak| 0.40%; 4j: naik 57%, median |gerak| 0.49%; 1h: naik 50%, median |gerak| 0.93%
- Setelah candle 15 menit pertama tutup, 1 jam berikutnya searah candle itu: 50% (n=110) → mengejar candle rilis ≈ lempar koin

### NFP (Non-Farm Payrolls) — 162 rilis
- Kejutan BAGUS untuk emas (data lemah / dovish) (n=67): 15m: searah 75%, rata +0.38% (≈$+16); 1j: searah 73%, rata +0.39% (≈$+17); 4j: searah 69%, rata +0.42% (≈$+18); 1h: searah 64%, rata +0.45% (≈$+19)
  - hanya kejutan BESAR (≥2× median, n=14): 1j searah 79%, rata +0.46%
- Kejutan BURUK untuk emas (data kuat / hawkish) (n=92): 15m: searah 70%, rata +0.24% (≈$+11); 1j: searah 54%, rata +0.22% (≈$+9); 4j: searah 55%, rata +0.25% (≈$+11); 1h: searah 55%, rata +0.16% (≈$+7)
  - hanya kejutan BESAR (≥2× median, n=20): 1j searah 45%, rata +0.22%
- Setelah candle 15 menit pertama tutup, 1 jam berikutnya searah candle itu: 54% (n=162) → mengejar candle rilis ≈ lempar koin

### CPI (inflasi konsumen) — 164 rilis
- Kejutan BAGUS untuk emas (data lemah / dovish) (n=68): 15m: searah 74%, rata +0.23% (≈$+10); 1j: searah 69%, rata +0.21% (≈$+9); 4j: searah 66%, rata +0.27% (≈$+12); 1h: searah 62%, rata +0.23% (≈$+10)
  - hanya kejutan BESAR (≥2× median, n=5): 1j searah 80%, rata +0.62%
- Kejutan BURUK untuk emas (data kuat / hawkish) (n=60): 15m: searah 53%, rata +0.12% (≈$+5); 1j: searah 58%, rata +0.11% (≈$+5); 4j: searah 47%, rata -0.01% (≈$-0); 1h: searah 45%, rata -0.01% (≈$-1)
  - hanya kejutan BESAR (≥2× median, n=5): 1j searah 80%, rata +0.31%
- Sesuai perkiraan / tanpa angka (n=36): 15m: naik 75%, median |gerak| 0.13%; 1j: naik 44%, median |gerak| 0.21%; 4j: naik 53%, median |gerak| 0.23%; 1h: naik 44%, median |gerak| 0.66%
- Setelah candle 15 menit pertama tutup, 1 jam berikutnya searah candle itu: 43% (n=164) → mengejar candle rilis ≈ lempar koin

### Core PCE — 52 rilis
- Kejutan BAGUS untuk emas (data lemah / dovish) (n=11): 15m: searah 73%, rata +0.20% (≈$+9); 1j: searah 91%, rata +0.29% (≈$+13); 4j: searah 36%, rata -0.10% (≈$-4); 1h: searah 18%, rata -0.69% (≈$-30)
- Kejutan BURUK untuk emas (data kuat / hawkish) (n=8): 15m: searah 62%, rata +0.07% (≈$+3); 1j: searah 75%, rata +0.17% (≈$+7); 4j: searah 50%, rata -0.01% (≈$-0); 1h: searah 38%, rata -0.22% (≈$-10)
- Sesuai perkiraan / tanpa angka (n=33): 15m: naik 55%, median |gerak| 0.10%; 1j: naik 39%, median |gerak| 0.19%; 4j: naik 39%, median |gerak| 0.38%; 1h: naik 67%, median |gerak| 0.65%
- Setelah candle 15 menit pertama tutup, 1 jam berikutnya searah candle itu: 50% (n=52) → mengejar candle rilis ≈ lempar koin

### GDP awal — 53 rilis
- Kejutan BAGUS untuk emas (data lemah / dovish) (n=27): 15m: searah 70%, rata +0.14% (≈$+6); 1j: searah 70%, rata +0.12% (≈$+5); 4j: searah 74%, rata +0.21% (≈$+9); 1h: searah 59%, rata +0.16% (≈$+7)
  - hanya kejutan BESAR (≥2× median, n=10): 1j searah 70%, rata +0.13%
- Kejutan BURUK untuk emas (data kuat / hawkish) (n=24): 15m: searah 75%, rata +0.11% (≈$+5); 1j: searah 46%, rata +0.03% (≈$+1); 4j: searah 54%, rata +0.18% (≈$+8); 1h: searah 54%, rata +0.33% (≈$+14)
  - hanya kejutan BESAR (≥2× median, n=8): 1j searah 50%, rata +0.00%
- Setelah candle 15 menit pertama tutup, 1 jam berikutnya searah candle itu: 43% (n=53) → mengejar candle rilis ≈ lempar koin

### PPI (inflasi produsen) — 140 rilis
- Kejutan BAGUS untuk emas (data lemah / dovish) (n=63): 15m: searah 71%, rata +0.10% (≈$+4); 1j: searah 63%, rata +0.11% (≈$+5); 4j: searah 63%, rata +0.06% (≈$+3); 1h: searah 52%, rata -0.02% (≈$-1)
  - hanya kejutan BESAR (≥2× median, n=14): 1j searah 64%, rata +0.22%
- Kejutan BURUK untuk emas (data kuat / hawkish) (n=55): 15m: searah 58%, rata +0.02% (≈$+1); 1j: searah 64%, rata +0.07% (≈$+3); 4j: searah 47%, rata +0.02% (≈$+1); 1h: searah 49%, rata -0.06% (≈$-3)
  - hanya kejutan BESAR (≥2× median, n=8): 1j searah 50%, rata +0.00%
- Sesuai perkiraan / tanpa angka (n=22): 15m: naik 59%, median |gerak| 0.12%; 1j: naik 59%, median |gerak| 0.18%; 4j: naik 41%, median |gerak| 0.22%; 1h: naik 59%, median |gerak| 0.61%
- Setelah candle 15 menit pertama tutup, 1 jam berikutnya searah candle itu: 49% (n=140) → mengejar candle rilis ≈ lempar koin

### Retail Sales — 116 rilis
- Kejutan BAGUS untuk emas (data lemah / dovish) (n=47): 15m: searah 62%, rata +0.07% (≈$+3); 1j: searah 68%, rata +0.10% (≈$+4); 4j: searah 47%, rata -0.01% (≈$-0); 1h: searah 57%, rata +0.17% (≈$+8)
  - hanya kejutan BESAR (≥2× median, n=12): 1j searah 75%, rata +0.15%
- Kejutan BURUK untuk emas (data kuat / hawkish) (n=55): 15m: searah 62%, rata +0.05% (≈$+2); 1j: searah 58%, rata +0.08% (≈$+3); 4j: searah 60%, rata -0.00% (≈$-0); 1h: searah 47%, rata -0.06% (≈$-3)
  - hanya kejutan BESAR (≥2× median, n=10): 1j searah 50%, rata +0.04%
- Sesuai perkiraan / tanpa angka (n=14): 15m: naik 50%, median |gerak| 0.16%; 1j: naik 43%, median |gerak| 0.12%; 4j: naik 21%, median |gerak| 0.44%; 1h: naik 57%, median |gerak| 0.33%
- Setelah candle 15 menit pertama tutup, 1 jam berikutnya searah candle itu: 49% (n=116) → mengejar candle rilis ≈ lempar koin

### ISM PMI — 312 rilis
- Kejutan BAGUS untuk emas (data lemah / dovish) (n=153): 15m: searah 64%, rata +0.10% (≈$+4); 1j: searah 59%, rata +0.11% (≈$+5); 4j: searah 58%, rata +0.15% (≈$+6); 1h: searah 53%, rata +0.19% (≈$+8)
  - hanya kejutan BESAR (≥2× median, n=27): 1j searah 63%, rata +0.22%
- Kejutan BURUK untuk emas (data kuat / hawkish) (n=156): 15m: searah 67%, rata +0.10% (≈$+4); 1j: searah 59%, rata +0.08% (≈$+4); 4j: searah 58%, rata +0.05% (≈$+2); 1h: searah 44%, rata -0.13% (≈$-5)
  - hanya kejutan BESAR (≥2× median, n=36): 1j searah 61%, rata +0.15%
- Setelah candle 15 menit pertama tutup, 1 jam berikutnya searah candle itu: 52% (n=312) → mengejar candle rilis ≈ lempar koin

### Unemployment Claims (mingguan) — 352 rilis
- Kejutan BAGUS untuk emas (data lemah / dovish) (n=137): 15m: searah 62%, rata +0.06% (≈$+3); 1j: searah 57%, rata +0.03% (≈$+1); 4j: searah 58%, rata +0.09% (≈$+4); 1h: searah 53%, rata +0.08% (≈$+3)
  - hanya kejutan BESAR (≥2× median, n=24): 1j searah 58%, rata +0.06%
- Kejutan BURUK untuk emas (data kuat / hawkish) (n=204): 15m: searah 63%, rata +0.06% (≈$+3); 1j: searah 58%, rata +0.06% (≈$+3); 4j: searah 52%, rata +0.03% (≈$+1); 1h: searah 51%, rata -0.01% (≈$-1)
  - hanya kejutan BESAR (≥2× median, n=36): 1j searah 67%, rata +0.21%
- Sesuai perkiraan / tanpa angka (n=11): 15m: naik 45%, median |gerak| 0.12%; 1j: naik 27%, median |gerak| 0.20%; 4j: naik 27%, median |gerak| 0.23%; 1h: naik 45%, median |gerak| 0.42%
- Setelah candle 15 menit pertama tutup, 1 jam berikutnya searah candle itu: 43% (n=352) → mengejar candle rilis ≈ lempar koin

### FOMC — keputusan vs ekspektasi
Keputusan FOMC dengan angka actual & forecast: n=77 (2014–2025); kejutan suku bunga hanya 2 kali — keputusan hampir selalu sudah diperkirakan pasar (CME FedWatch / konsensus). Yang menggerakkan emas: pernyataan, dot plot, konferensi pers.
- naik, lebih hawkish (n=1): ['2022-06-15']
- Suku bunga naik, sesuai (n=19): emas 1 jam naik 68% (median +0.22%), 1 hari naik 53% (median +0.08%), median |gerak| 1 jam 0.46%
- Suku bunga tetap, sesuai (n=47): emas 1 jam naik 55% (median +0.09%), 1 hari naik 55% (median +0.17%), median |gerak| 1 jam 0.39%
- turun, lebih dovish (n=1): ['2024-09-18']
- Suku bunga turun, sesuai (n=9): emas 1 jam naik 33% (median -0.60%), 1 hari naik 56% (median +0.80%), median |gerak| 1 jam 0.67%

## 2. Reaksi BTC/USD terhadap berita AS yang sama (H1)
'searah' untuk BTC = BTC naik setelah data lemah/dovish dan turun setelah data kuat/hawkish (sama seperti emas).

### FOMC (suku bunga Fed) — 82 rilis (BTC)
- Sesuai perkiraan / tanpa angka (n=80): 1j: naik 56%, median |gerak| 0.38%; 4j: naik 57%, median |gerak| 0.88%; 1h: naik 48%, median |gerak| 2.23%

### NFP (Non-Farm Payrolls) — 122 rilis (BTC)
- Kejutan BAGUS untuk emas (data lemah / dovish) (n=48): 1j: searah 65%, rata +0.18% (≈$+149); 4j: searah 50%, rata -0.10% (≈$-87); 1h: searah 46%, rata -0.58% (≈$-485)
  - hanya kejutan BESAR (≥2× median, n=12): 4j searah 42%, rata -0.39%
- Kejutan BURUK untuk emas (data kuat / hawkish) (n=72): 1j: searah 44%, rata -0.23% (≈$-193); 4j: searah 38%, rata -0.41% (≈$-344); 1h: searah 46%, rata -0.70% (≈$-588)
  - hanya kejutan BESAR (≥2× median, n=21): 4j searah 48%, rata -0.20%

### CPI (inflasi konsumen) — 122 rilis (BTC)
- Kejutan BAGUS untuk emas (data lemah / dovish) (n=50): 1j: searah 68%, rata +0.60% (≈$+502); 4j: searah 58%, rata +0.42% (≈$+354); 1h: searah 62%, rata +0.57% (≈$+479)
  - hanya kejutan BESAR (≥2× median, n=5): 4j searah 80%, rata +2.08%
- Kejutan BURUK untuk emas (data kuat / hawkish) (n=45): 1j: searah 62%, rata +0.51% (≈$+430); 4j: searah 60%, rata +0.56% (≈$+467); 1h: searah 56%, rata +1.52% (≈$+1274)
  - hanya kejutan BESAR (≥2× median, n=5): 4j searah 80%, rata +2.18%
- Sesuai perkiraan / tanpa angka (n=27): 1j: naik 59%, median |gerak| 0.40%; 4j: naik 52%, median |gerak| 0.91%; 1h: naik 56%, median |gerak| 1.66%

## 3. Sinyal 💰 bot di sekitar berita (XAU, 2013–2026)
- Sinyal XAU 💰 lahir ≤ 4 jam SESUDAH NFP/CPI/FOMC: n=94, WR 54%, rata +0.40R
- Sinyal XAU 💰 lahir ≤ 24 jam SEBELUM NFP/CPI/FOMC: n=115, WR 40%, rata -0.07R
- Sinyal XAU 💰 jauh dari berita: n=981, WR 50%, rata +0.27R

## 4. Ringkasan riset filter (docs/RISET_DATA_EKSTERNAL.md)
- Uji ±70 varian filter per aset (berita, yield riil, dolar, COT, sesi, GVZ/VIX, yield 2 th, musiman) dengan kriteria latih/uji ketat: untuk XAU 💰 TIDAK ADA yang konsisten. Sinyal 💰 XAU yang lahir sesudah berita justru lebih baik (berita memicu breakout).
- BTC 💰: dua filter konsisten dan dipasang di cloud: (a) lewati BUY saat funding Binance 24 jam di 10% tertinggi setahun, lewati SELL saat di 10% terendah (short squeeze); (b) lewati sinyal di bulan September (11 dari 11 tahun rugi, rata-rata −0,43R).
- XAU: saat volatilitas tersirat emas (GVZ, FRED GVZCLS) naik dalam 5 hari terakhir, sinyal 💰 rata-rata +0,04R (WR 45,5%, n=506) vs +0,40R (WR 51,4%, n=679) saat tidak naik; tetapi hanya 8 dari 14 tahun searah → informasi, bukan filter.
- Scalping berita (ikut/lawan candle rilis) diuji 2012–2026: tidak ada yang positif konsisten setelah spread.
- Hasil masa lalu bukan jaminan; WR sinyal trend memang rendah (≈45–50%) dan profit datang dari sedikit trend besar.

## 5. Cara kerja sinyal bot (untuk menjelaskan ke pengguna)
- Sistem trend H1: 3 set Donchian (breakout 40/55/80 candle, keluar 15/20/30). SL = 3 × ATR(20); tiap sinyal 5 posisi: posisi #1 TP1 = 1R, sisanya ditahan sampai sinyal TUTUP; setelah TP1 SL sisa pindah ke entry (SL+).
- Kategori: konf+⭐ (searah EMA50/200, supertrend, momentum 60 hari DAN tren D1 + breakout H4), konf, ⭐, biasa. Hanya kategori ber-💰 yang dikirim. Statistik historis per sinyal (WR / rata-rata R / n): XAU konf+⭐ 49,2% / +0,31R / 850; XAU konf 48,1% / +0,09R / 335; BTC ⭐ 49,5% / +0,68R / 382; BTC konf+⭐ 47,8% / +0,31R / 811; BTC konf 48,1% / +0,23R / 430. Gap pekan forex (AUD/USD, USD/JPY, EUR/JPY, AUD/JPY, EUR/CHF): WR 74–90%, +0,10 s/d +0,26R.
- 1R = rugi bila kena SL awal. WR rendah itu normal untuk trend-following: banyak rugi kecil, sedikit untung besar.

