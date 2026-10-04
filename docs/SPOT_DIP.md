# Sinyal spot Binance "sudah turun jauh, saatnya beli" (4 Okt 2026)

Permintaan pengguna: sinyal **spot** (beli saja, tanpa leverage) saat harga sudah terlalu turun, WR tinggi dan profit
tinggi. Kode: `research/spot_dip.py` (putaran 1), `research/spot_dip2.py` (uji ketahanan). Hasil mentah:
`docs/eksternal/hasil_spot_dip.txt`, `docs/eksternal/hasil_spot_dip2.txt`.

## Cara uji
- Data 1 jam data.binance.vision → candle **harian** UTC. Entry di open hari berikutnya, satu posisi per koin.
- Biaya 0,30% pulang-pergi (fee spot 0,1% per sisi + slippage). SL dicek sebelum TP pada hari yang sama.
- Entry: turun ≥ 10–30% dari high 20/60 hari, RSI(14) < 20/25/30, di bawah Bollinger 2/2,5, z-score < −2,
  3 hari merah beruntun turun ≥ 10/15%; dengan/tanpa syarat harga di atas SMA200 ("+tren").
- Keluar: TP +3/+5/+10% dengan batas 5/10/20 hari, atau balik ke rata-rata 20 hari; tanpa SL / SL −15%.
- Pembanding: entry acak pada hari yang sama banyaknya (supaya WR tinggi karena pasar naik tidak dianggap keunggulan).

## Putaran 1 (21 koin yang masih hidup): 704 kombinasi, 68 "lolos"
WR per trade 80–95% dengan rata-rata +1–3% per trade di LAMA (< Okt 2021) dan BARU. Kelihatan bagus, tetapi ada
tiga jebakan, diuji di putaran 2.

## Putaran 2: uji ketahanan (40 koin, termasuk 16 yang ambruk/delisting)
1. **Koin yang ambruk** (LUNA, FTT, SRM, UST, WAVES, BTT, MITH, OMG, ...): "beli saat turun jauh" kena paling parah
   di koin seperti ini — LUNA −100%, UST −76%, WAVES −55% dalam satu trade.
2. **Sinyal bergerombol**: saat pasar ambruk banyak koin memberi sinyal di hari yang sama (contoh: 207 trade hanya
   94 hari berbeda) → rugi datang bersamaan.
3. **Rugi rata-rata besar**: menang +3–5%, kalah rata-rata −13% s.d. −25% (tanpa SL), terburuk −55% s.d. −100%.
   SL −15% justru memperburuk BARU (rata-rata −0,15% per trade).

Simulasi portofolio (modal dibagi 5 atau 10 slot, sinyal saat slot penuh dilewati, ekuitas harian):

| Aturan | Periode | CAGR/th | DD maks |
|---|---|---|---|
| 3 merah ≥10% +tren, TP 5%, maks 10 hari (slot 10) | LAMA 2018–Sep 2021 | +29% | −14% |
| | BARU Okt 2021–2026 | **+7%** | **−24%** |
| 3 merah ≥15% +tren, TP 5%, maks 20 hari (slot 10) | LAMA | +16% | −12% |
| | BARU | +5% | −13% |
| Turun 30% dari high 20 hari, TP 5% (slot 10) | BARU | −6% | −58% |
| RSI < 30, TP 10% (slot 10) | BARU | +11% | −35% |
| Pembanding: BTC beli-tahan | LAMA / BARU | +37% / +12% | −81% / −77% |

Per tahun (BARU, "3 merah ≥10% +tren TP 5% 10 hari", slot 10): 2021 +2%, 2022 −6%, 2023 +3%, 2024 +12%, 2025 +22%,
2026 s.d. Sep +1%. Per trade BARU: WR 81%, +1,3%/trade, median tahan 1 hari, ±7 sinyal per bulan (±3 hari berbeda).

Pemilihan aturan dari LAMA saja lalu dilihat di BARU: semua aturan tetap positif per trade, tetapi aturan terbaik
LAMA (RSI25 balik SMA20) di portofolio BARU: 2022 −48%, 2026 −31%.

## Kesimpulan
- **WR tinggi bisa (80–90%), profit tinggi tidak.** Di 5 tahun terakhir hasil portofolio terbaik ±+5–7% per tahun
  dengan drawdown −13% s.d. −24% — lebih kecil dari BTC beli-tahan (+12%/th) tetapi drawdown jauh lebih ringan
  (BTC −77%).
- Kandidat satu-satunya yang layak dijadikan sinyal info: **"3 hari merah beruntun turun ≥ 10% saat harga di atas
  SMA200 → beli di open berikutnya, TP +5%, jual paksa setelah 10 hari, maks 10% modal spot per sinyal"**. Cocok
  dengan pilihan pengguna "WR tinggi walau profit tipis". Sesekali rugi besar (−30% s.d. −55% satu koin).
- BELUM dipasang di cloud/aplikasi — menunggu kata "pasang" dari pengguna. Bila dipasang: info saja (tanpa order
  otomatis), hanya koin besar yang likuid, tampil di kartu terpisah "💎 Spot".
- Catatan: 34 koin lama/delisting lain masih diunduh (`research/pair_kripto.coin`); jalankan ulang
  `python -m research.spot_dip2` bila sudah lengkap.
