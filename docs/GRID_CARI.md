# Mencari grid/martingale yang untung (3 Okt 2026)

Permintaan pengguna: "cari sebanyak-banyaknya agar profit, bukan minus — tidak harus $150". Data XAU 2012 – 2 Okt 2026
(M15/M5, spread $0,20 per layer, tutup sebelum akhir pekan, swap belum dihitung). Setiap keranjang dibatasi risikonya
R = 5% modal ($20 dari $400) dan hasil diukur dalam R supaya tahun bervolatilitas rendah (2012) dan tinggi (2026) sebanding.
**Aturan seleksi ditetapkan sebelum melihat data baru**: dipilih dari LAMA (< Okt 2021) — n ≥ 200 keranjang,
rata-rata R > 0, t ≥ 2, ≥ 70% tahun positif — lalu diuji di BARU (Okt 2021 – 2 Okt 2026).

## Teknik yang dicari di web (EA grid emas & riset)

ATR untuk jarak/TP, filter rezim ADX H4 (grid hanya saat ranging, tutup saat tren), batas layer + stop per keranjang,
filter sesi, entri mean-reversion RSI/Bollinger, grid searah tren EMA ([Gold Range Grid Mean Reversion](https://www.mql5.com/ja/market/product/182989),
[Gold Martingale Grid Expert](https://www.mql5.com/en/market/product/187912), [Gold Hedge Martingale Pro](https://www.mql5.com/ru/market/product/185970),
[Trend Grid EA EMA + ATR](https://www.mql5.com/en/job/250547)). Riset akademis: strategi mean-reversion sering kalah oleh
biaya transaksi ([arXiv 1909.04327](https://arxiv.org/pdf/1909.04327)); grid rentan pada tren kuat
([MQL5 blog](https://www.mql5.com/en/blogs/post/776360), [gambler's ruin & grid](https://businessperspectives.org/component/zoo/gambler-s-ruin-problem-and-bi-directional-grid-constrained-trading-and-investment-strategies)).
Klaim backtest penjual EA (mis. PF 1,11) tidak diverifikasi.

## 1. Grid/martingale (melawan arah) — 936 pengaturan (`research/grid_cari.py`)

- Putaran 1 (648): 9 jenis entri/filter (selalu BUY, tren H4/D1, tren H4 BUY saja, ranging ADX+RSI dengan tutup saat
  tren, pullback RSI dalam tren, sesi Asia, Bollinger, Bollinger searah tren) × pengali 1/1,3/1,6/2 × jarak 0,5/1/2 ATR
  × TP 0,5/1 ATR × maks 4/7/10 layer + stop setelah layer maksimum.
- Putaran 2 (288): volatilitas rendah (ATR < 0,8 × median 20 hari), beli koreksi dalam tren D1, ranging ADX < 20.
- Rata-rata per jenis filter: −0,009 s/d −0,020R per keranjang (LAMA), −0,010 s/d +0,001R (BARU).
- Lolos seleksi LAMA: 1 dari 936 (tren H4 BUY, ×2, jarak 2 ATR, TP 1 ATR, maks 10) dan positif di BARU, tetapi hanya
  +0,0004…0,0009R per keranjang ≈ **$4 per tahun** pada risiko $20 per keranjang — memungut receh; satu stop menghapus
  ±4.000 keranjang. Bukan keunggulan.
- Kesimpulan: grid/martingale, dengan atau tanpa filter populer, ≈ acak dikurangi spread.

## 2. Kebalikan martingale: piramida searah tren — 104 pengaturan (`research/piramida.py`)

Layer ditambah saat harga bergerak SEARAH (tiap step × ATR H1), stop semua layer = layer terakhir − stop × ATR (ikut
naik), keluar saat stop kena atau tren tidak lagi searah. Arah: tren H4 EMA50 / D1 EMA200 / keduanya searah ("tren2").

- Hampir semua pengaturan positif di LAMA dan BARU (+0,1…+0,4R per keranjang) — sejalan dengan temuan proyek bahwa
  emas cocok untuk mengikuti tren (sinyal 💰 XAU +0,21R/sinyal sejak Okt 2021).
- Lolos seleksi LAMA: 3 (semuanya "tren2", stop 2 ATR, maks 6, lot sama), ketiganya positif di BARU (t 1,5–2,2).

| Pengaturan | LAMA R/keranjang | BARU R/keranjang | Tahun + | Spread ×2 LAMA/BARU | Risiko 0,5% ($2): $/bulan LAMA / BARU (DD) | Risiko 1% ($4): $/bulan BARU (DD) |
|---|---|---|---|---|---|---|
| jarak 1 ATR | +0,241 | +0,282 | 11/15 | +0,151 / +0,229 | +11,8 (77%) / +14,2 (41%) | +28,4 (81%) |
| jarak 2 ATR | +0,160 | +0,108 | 11/15 | +0,098 / +0,073 | +7,1 (34%) / +5,3 (51%) | +10,5 (102%) |
| **jarak 3 ATR** | **+0,134** | **+0,176** | **12/15** | **+0,082 / +0,146** | **+5,4 (30%) / +7,4 (21%)** | **+14,7 (43%)** |

- Jarak 3 ATR per tahun (R): 2012 +46, 2013 +126, 2014 +16, 2015 +27, 2016 +5, 2017 +10, 2018 +2, 2019 +1, 2020 +68,
  2021 −11, 2022 −5, 2023 +64, 2024 +73, 2025 +103, **2026 −2** (tahun ini belum positif).
- Sifatnya kebalikan martingale: **menang hanya 19–25% keranjang** (banyak rugi kecil, sedikit untung besar),
  tahan median 6–7 jam, 33–37% keranjang menginap (swap belum dihitung — cek akun swap-free).
- Profit kecil: modal $400 dengan risiko 0,5% ≈ $5–7/bulan; menaikkan risiko menaikkan drawdown setara.

## Kesimpulan

- Grid/martingale: **0 dari 936** pengaturan punya keunggulan yang berarti. $150/bulan maupun "asal profit" tidak
  ditemukan di keluarga ini.
- Yang positif di data lama DAN baru adalah kebalikannya (piramida/mengikuti tren), dengan hasil kecil dan drawdown
  nyata. EA uji: `ea/PiramidaTren.mq5` (bawaan = jarak 3 ATR, stop 2 ATR, maks 6, risiko 0,5%, tutup akhir pekan;
  belum di-compile di sesi — compile di MetaEditor, uji demo).
- Batasan: 1.040 pengaturan diuji (risiko kebetulan; diatasi dengan seleksi LAMA → uji BARU dan konsistensi satu
  keluarga), swap belum dihitung, bar M5/M15, entri di harga level tanpa slippage.
