# Risiko bangkrut EA martingale XAU lot x2, 20+ layer (3 Okt 2026)

Klaim yang diuji: EA martingale XAU/USD (lot dikali 2 tiap layer, sampai 20+ layer, jalan di VPS) "menghasilkan ±$150
per akun". Skrip `research/martingale_ruin.py` (aturan ditulis ulang, tidak menjalankan kode EA mana pun) →
`docs/eksternal/hasil_martingale_ruin.txt` + `.csv`. Uji: `tests/test_martingale_ruin.py`.

**Patokan** (sama dengan memo thread "Write a verdict on the claim" agar bisa dibandingkan): mulai 0,01 lot, x2 tiap
layer, jarak antar layer **$2**, modal **$3.000**, target laba **$150**, leverage 1:2000 (maks Exness untuk emas). TP
keranjang $1 di atas harga rata-rata, tanpa SL. Divariasikan: jarak $2/$5/$10, maks 10/12/15/20 layer, modal
$1.000–$50.000, leverage 1:500, arah BUY/SELL. Spread $0,20 per layer; swap & komisi diabaikan (menguntungkan EA).

## 1. Matematika per layer (harga emas $4.200)

| Layer | Lot layer | Lot total | Rugi mengambang sebelum layer berikut (jarak $2) | Margin 1:2000 | Modal minimum 1:2000 |
|---|---|---|---|---|---|
| 5 | 0,16 | 0,31 | −$120 | $65 | $185 |
| 8 | 1,28 | 2,55 | −$1.055 | $536 | $1.591 |
| 9 | 2,56 | 5,11 | −$2.128 | $1.073 | $3.201 |
| 10 | 5,12 | 10,23 | −$4.277 | $2.148 | $6.425 |
| 12 | 20,48 | 40,95 | −$17.175 | $8.600 | $25.775 |
| 15 | 163,84 | 327,67 | −$137.591 | $68.811 | $206.402 |
| 20 | **5.242,88** | **10.485,75** | **−$4,4 juta** | $2,2 juta | **$6,6 juta** |

(Jarak $5: modal minimum layer 10 = $12.533, layer 20 = $12,9 juta.)

- Dengan modal $3.000 di 1:2000, EA **hanya sanggup sampai layer 8**; layer 9 sudah butuh $3.201. "20+ layer" dari
  0,01 lot x2 secara fisik mustahil: layer 16 (327,68 lot) melewati batas 200 lot per order Exness, dan layer 20 butuh
  modal ±$6,6 juta. Jadi EA yang diklaim pasti memakai lot awal lebih kecil (akun Cent), pengali < 2, atau tidak
  pernah benar-benar mencapai 20 layer — atau akunnya habis sebelum sampai sana.
- Rugi naik ±2x tiap layer, sedangkan jarak balik untuk impas tetap ±1 jarak layer. Itulah sebabnya hampir semua
  siklus menang (WR mendekati 100%) — sampai satu siklus tidak balik.

## 2. Seberapa sering emas "melawan" sejauh itu (M5 Agu 2020 – Sep 2026, harga $1.955 → $4.315)

Rata-rata siklus per BULAN yang mencapai ≥ k layer (BUY, maks 20):

| Jarak | Siklus/bln | ≥ 8 layer | ≥ 10 | ≥ 12 | ≥ 15 | ≥ 20 |
|---|---|---|---|---|---|---|
| $2 | 1.335 | 29 | 14 | 7 | 3,1 | 1,0 |
| $5 | 968 | 3,7 | 1,4 | 0,7 | 0,2 | 0,04 |
| $10 | 667 | 0,8 | 0,2 | 0,1 | 0,04 | 0 |

Dengan jarak $2, kebutuhan "≥ 9 layer" (batas modal $3.000) muncul ±20 kali sebulan. Gerak emas melawan $16–40 dalam
satu arah adalah kejadian biasa, terutama 2025–2026 (rentang harian $50–100).

## 3. Monte Carlo (1.000 titik mulai acak di sejarah, urutan siklus asli)

Akun dianggap **habis** bila equity + rugi mengambang ≤ 0 (stop out Exness 0%) atau equity tidak cukup untuk margin
layer berikutnya (EA macet di posisi rugi besar tanpa jalan keluar).

| Skenario (BUY, maks 20, 1:2000) | Laba $150 tercapai dulu | Hasil rata-rata bila EA dimatikan di +$150 | Habis dalam 1 bulan | Habis dalam 1 tahun |
|---|---|---|---|---|
| **Patokan: jarak $2, modal $3.000** | **85%** (median ±0,6 hari) | **−$251** | **94%** | **100%** |
| jarak $2, modal $10.000 | 93% | −$339 | 78% | 100% |
| jarak $2, modal $50.000 | 98% | −$576 | 49% | 100% |
| jarak $5, modal $3.000 | 91% (±3 hari) | −$112 | 47% | 98% |
| jarak $10, modal $3.000 | 93% (±7 hari) | −$75 | 31% | 97% |
| jarak $2, modal $1.000 | 77% | −$74 | 99% | 100% |

- **Klaim $150 itu nyata tetapi menyesatkan**: dengan modal $3.000, laba $150 biasanya tercapai dalam kurang dari
  sehari (85%). Namun 15% sisanya kehilangan seluruh $3.000, sehingga rata-ratanya **rugi ±$251 per akun** walau EA
  langsung dimatikan begitu untung $150. Rasio taruhannya: menang $150 vs kalah $3.000 (1 : 20), padahal peluang
  menangnya hanya 85% (butuh > 95% agar impas).
- **Kalau EA dibiarkan jalan** (seperti di VPS), akun patokan habis dalam sebulan pada 94% percobaan dan dalam setahun
  pada 100%. Modal lebih besar hanya menunda: $50.000 pun habis dalam setahun di semua percobaan (jarak $2).
- Ini konsisten di setiap tahun mulai, periode LAMA (2020–Sep 2021) maupun BARU (sejak Okt 2021): BUY jarak $2 modal
  $3.000 habis dalam 1 bulan 82–99% per tahun; jarak $5 22–48% (2020–2023) naik ke 61–93% (2024–2026, emas lebih liar).
- Leverage 1:500 lebih buruk (margin lebih besar → macet lebih awal): patokan laba $150 tercapai 81%, habis 1 bulan 99%.
- **SELL** (melawan tren naik emas 2020–2026) sama buruknya; satu siklus SELL jarak $2 yang dibuka 2022 tidak pernah
  kembali sampai data habis (posisi 19 layer). Beberapa angka "rata-rata 1 tahun" SELL tampak positif karena satu–dua
  akun yang selamat melewati siklus sangat dalam mendapat laba besar sekali (lot ribuan); median akun tetap habis.
- BUY dalam data ini sudah "dibantu" pasar naik ($1.955 → $4.315), jadi hasil di atas condong optimistis untuk EA.

## Keterbatasan

Candle M5 (urutan dalam candle diperkirakan: candle naik O→L→H→C, turun O→H→L→C); dua sumber data disambung April 2025
(beda jam server ±3 jam); swap emas (negatif untuk posisi ditahan berhari-hari) & slippage saat berita tidak dihitung,
dan leverage Exness untuk emas turun di sekitar berita/akhir pekan — semuanya membuat EA lebih buruk, bukan lebih baik.

## Kesimpulan

Lot x2 sampai 20+ layer tidak mungkin dijalankan dengan modal ribuan dolar; EA seperti ini menukar banyak kemenangan
kecil (±$1 per siklus) dengan kepastian kehilangan seluruh modal saat emas bergerak searah beberapa puluh dolar — yang
di emas terjadi beberapa kali sebulan. "±$150 per akun" adalah gambaran akun yang kebetulan berhenti tepat waktu
(survivorship), bukan hasil yang bisa diharapkan. Tidak ada janji profit; riset ini tidak mengubah bot live.
