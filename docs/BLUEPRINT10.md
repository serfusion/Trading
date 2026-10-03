# Uji "Blueprint EA XAU/USD — 10 Strategi Non-Martingale" (3 Okt 2026)

Dokumen unggahan pengguna (prinsip: risiko tetap per trade, SL wajib, expectancy > win rate). Aturan setiap strategi
ditulis ulang dari parameter baseline dokumen (`research/blueprint10.py`), XAU 2012 – 2 Okt 2026, bar dasar M15, setup
H1/H4/D1 dari bar yang sudah selesai, entry di open berikutnya, spread $0,20 (stres ×2), SL dicek dulu, satu posisi per
strategi, tahan maks 5 hari. Cara keluar: 2R (dokumen), 1R & 0,5R (win rate tinggi), F (½ TP 1R + ½ TP 2R, SL impas
setelah +1R), alami (middle band/VWAP untuk #4 & #7). Filter tambahan "tren2" (H4 EMA50 & D1 EMA200 searah). Seleksi
ditetapkan dulu: LAMA (< Okt 2021) n ≥ 100, rata-rata > 0, t ≥ 2, ≥ 70% tahun + → diuji di BARU.
Hasil: `docs/eksternal/hasil_blueprint10.txt/.csv`, gabungan `docs/eksternal/hasil_gabung_bp.txt`.

## 1. Sepuluh strategi berdiri sendiri — 79 kombinasi, 0 lolos

| Strategi (keluar 2R) | Tanpa filter: LAMA / BARU R per trade (WR) | + tren2: LAMA / BARU |
|---|---|---|
| 1 Tren + pullback EMA20 | −0,05 / −0,00 (32–33%) | −0,01 / +0,05 |
| 2 Breakout + retest | −0,09 / −0,01 | −0,00 / +0,01 |
| 3 Liquidity sweep + MSS | −0,00 / −0,11 | −0,08 / +0,01 |
| 4 Mean reversion BB (ADX < 20) | +0,13 / +0,09 (hanya 45 / 44 trade) | terlalu sedikit |
| 5 Momentum expansion (squeeze) | +0,00 / +0,04 | −0,01 / +0,14 |
| 6 London breakout range Asia | −0,03 / −0,03 | +0,08 / +0,03 |
| 7 VWAP reversion | −0,37 / −0,21 | −0,20 / +0,21 (28 / 18 trade) |
| 8 MTF struktur H4/H1/M15 | −0,10 / −0,02 | −0,10 / +0,02 |
| 9 ATR volatility breakout | +0,02 / −0,03 | **+0,06 / +0,11** (t 1,4 / 2,0; spread ×2 +0,01 / +0,09) |
| 10 Regime switching (1+9 saat tren, 4 saat range, stop saat ATR > P90) | −0,03 / +0,01 | — |

- **Win rate tinggi ada, untung tidak**: TP 0,5R memberi WR 61–68% di LAMA dan BARU pada #1, #2, #3, #5, #6, #8, #9,
  tetapi rata-rata −0,08…+0,02R per trade (impas/rugi setelah spread). Strategi yang mendekati untung punya WR 23–37%.
- Filter tren2 memperbaiki hampir semua strategi (sejalan dengan temuan: emas cocok mengikuti tren).
- Sejalan dengan uji lama proyek: SMC sweep→MSS rugi (`docs/BACKTEST.md`), RSI(2)/Bollinger fade WR 53–66% tetapi rugi
  (`docs/STRATEGI_LAB.md`, `docs/UJI_DUNIA.md`), London breakout/ORB rugi (`docs/RISET_GITHUB.md`).

## 2. Digabung dengan piramida searah tren (`research/gabung_bp.py`)

Piramida terpilih (tren2, jarak 3 ATR, stop 2 ATR, maks 6), risiko 0,5% ($2 per $400):

| Pemicu keranjang | LAMA R/keranjang (t) | BARU R/keranjang (t) | $/bulan LAMA / BARU | WR |
|---|---|---|---|---|
| **Tanpa pemicu (piramida biasa)** | **+0,134 (2,0)** | **+0,176 (2,2)** | **+5,4 / +7,4** | 25% |
| #1 tren + pullback | +0,416 (2,3) | +0,164 (1,4) | +5,8 / +2,4 | 25% |
| #9 ATR breakout | +0,195 (2,1) | +0,130 (1,4) | +3,3 / +2,3 | 25–26% |
| #5 momentum expansion | +0,147 (1,1) | +0,428 (1,9) | +0,9 / +2,7 | 23–26% |
| #6 London | +0,313 (2,2) | −0,079 (−0,6) | +2,5 / −0,7 | 19–23% |
| Salah satu dari #1/#2/#5/#6/#8/#9 | +0,217 (2,0) | +0,118 (1,5) | +5,3 / +3,0 | 23–25% |

- Pemicu dari dokumen menaikkan R per keranjang di LAMA, tetapi mengurangi jumlah keranjang dan **tidak lebih baik di
  BARU** → piramida biasa tetap pilihan terbaik.
- Aturan risiko dokumen (rugi harian 2%, mingguan 5%, 4 kalah beruntun) hampir tidak pernah aktif pada risiko 0,5%
  per keranjang → hasil sama; berguna sebagai rem darurat, bukan sumber profit.

## Kesimpulan

- Dokumen benar soal prinsip (expectancy > win rate, risiko tetap, SL wajib). Diuji di data emas 14 tahun, tidak ada
  dari 10 strategi itu yang untung meyakinkan sendirian; yang WR ≥ 60% semuanya impas/rugi.
- WR tinggi yang TETAP untung di proyek ini: sinyal 💰 dengan TP1 0,7R (sudah dipasang 3 Okt): replay cloud WR XAU
  53 → 63%, BTC 50 → 56% sejak 2021 dengan profit sama (`docs/VERIFIKASI.md`).
- Yang positif di data lama & baru tetap kelompok mengikuti tren: sinyal 💰 dan piramida (`docs/GRID_CARI.md`).
