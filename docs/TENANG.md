# Cek data & uji ulang "hanya saat pasar tenang" (3 Okt 2026)

Pertanyaan pengguna: "metode populer buatan ahli kok tidak untung — mungkin datamu salah? Skip news, skip crash, pilih
yang tenang saja sampai volatilitas turun." Skrip `research/tenang.py` → `docs/eksternal/hasil_tenang.txt`
(+ `hasil_tenang_blueprint.csv`), sensitivitas `research/tenang_sensitif.py` → `hasil_tenang_sensitif.txt`.

## 1. Data dicek terhadap sumber independen

- XAU H1 data riset vs Twelve Data H1, Jun 2020 – Okt 2026 (36.594 jam): selisih close median **$0,19** (P95 $4,06 saat
  pasar liar), korelasi return per jam **0,944**, arah candle sama **98,6%** (gerak > 0,05%). Bar janggal 145 dari
  626.270 (0,02%), duplikat 0. Sebelumnya sudah dicek juga terhadap Dukascopy & tick asli Exness (`docs/VERIFIKASI.md`,
  `docs/NEWS_DETIK.md`).
- Data yang sama menunjukkan metode mengikuti tren UNTUNG (sinyal 💰, piramida) → data tidak "menghukum" semua metode.
  Hasil "tidak untung" adalah hasil uji ulang aturan dengan biaya (spread), bukan asumsi.

## 2. Filter TENANG (43% waktu)

Per bar, hanya dari informasi sebelum bar itu: tidak ada berita USD high-impact 60 mnt ke depan / 120 mnt ke belakang
(ForexFactory s/d Jan 2026, lalu tanggal rilis resmi FRED CPI/NFP/PPI/GDP/PCE/Retail 08:30 ET + FOMC 2026; 3.735 rilis),
tidak ada gerak ≥ 3 × ATR H1 dalam 60 mnt selama 4 jam terakhir, dan ATR H1 ≤ median 20 hari. Grid: keranjang baru
hanya saat tenang; "lindung" = tutup keranjang 15 mnt sebelum berita dan saat crash terdeteksi.

## 3. Hasil

**10 strategi blueprint** (R per trade LAMA / BARU): filter tenang memperbaiki sebagian (mis. #1 tren+pullback 2R +
tenang + tren2: −0,05/−0,00 → +0,03/+0,21, n 440/218, WR 40%), tetapi hanya 1 kombinasi lolos seleksi LAMA (#5 momentum
F tenang+tren2: +0,21) dan **gagal di BARU (−0,06)**. WR ≥ 60% dengan filter tenang: 13 kombinasi, rata-rata −0,013R
(LAMA) / −0,034R (BARU).

**Grid/martingale** (akun baru tiap bulan, $/bulan; persentase = bulan akun habis):

| Pengaturan | Tanpa filter BARU | Tenang + lindung + akhir pekan: LAMA / BARU / 12 bulan terakhir |
|---|---|---|
| Rekonstruksi Signal Strike 0,07/$524 ×1,2 | −$65 (37%) | +$0 (0%) / **−$19 (8%)** / −$49 (25%) |
| $400 ×2 0,01 jarak $2,25 | −$33 (43%) | −$2 (2%) / −$45 (20%) / −$253 (83%) |
| $400 ×2 0,01 jarak $5 | −$13 (13%) | +$0 (0%) / **+$4 (0%)** / +$11 (0%) |
| $400 ×1,2 0,05 jarak $2,25 | −$40 (35%) | +$0 (0%) / −$15 (8%) / −$38 (25%) |

- Filter tenang + perlindungan memangkas akun habis (37% → 8% bulan untuk rekonstruksi trader), tetapi rata-rata tetap
  negatif kecuali ×2 jarak $5.
- **Sensitivitas** (36 pengaturan di sekitar ×2 jarak $5, semua dengan filter penuh): 6 plus di LAMA & BARU, semuanya
  kecil (+$0,03…0,30/bulan LAMA, +$1,5…4,3/bulan BARU, t ≤ 1,75); tetangga dekat (jarak 4, TP 3) −$10…−$28/bulan →
  kantong kebetulan, bukan keunggulan yang stabil. Tidak ada yang mendekati $150/bulan.

**Piramida searah tren** (risiko 0,5%, $400): hanya buka saat tenang menaikkan R per keranjang (jarak 3 ATR: +0,134 →
+0,219 LAMA, +0,176 → +0,250 BARU) tetapi keranjang lebih sedikit → $/bulan hampir sama (+$5,8 / +$6,9 vs +$5,4 / +$7,4).

## Kesimpulan

Data benar. Melewati berita & crash dan hanya trading saat tenang membuat semua keluarga lebih aman (akun habis jauh
berkurang) dan menaikkan kualitas per trade, tetapi tidak mengubah grid/martingale/10 strategi blueprint menjadi
untung yang meyakinkan. Yang konsisten positif tetap mengikuti tren (sinyal 💰, piramida); filter tenang layak dipakai
sebagai penyaring kualitas di keluarga itu.
