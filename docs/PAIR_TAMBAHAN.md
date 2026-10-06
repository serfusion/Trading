# Pair tambahan untuk sinyal 💰 (3 Okt 2026)

Permintaan pengguna: "uji juga pair tambahan tadi". Sumber sinyal tambahan yang paling sehat adalah **pair yang
berbeda**, bukan set yang sama. Laporan mentah: `docs/eksternal/hasil_pair_tambahan.txt`. Skrip yang dipakai:
`research/pair_data.py` (unduh data) dan `research/pair_tambahan.py` (uji).

## Cara uji (aturan ditetapkan sebelum melihat hasil)
- Mesinnya sama dengan cloud (`research/sl_tangga.backtest`):
  - 3 set Donchian H1 (40/15, 55/20, 80/30), SL 3×ATR, 5 posisi.
  - TP1 1R untuk posisi #1, lalu SL+; 4 posisi lainnya jalan sampai TUTUP.
  - Forex melewati 3 candle pertama setelah pasar buka pekan.
- Biaya spread mengikuti akun Standard (`multi_asset.INSTRUMENTS`, misalnya USD/JPY 1,2 pip); ETH 0,05%. Swap belum
  dihitung.
- Data:
  - Forex: ejtrader 2012–2022, disambung Twelve Data 2022–Okt 2026. Di masa tumpang tindih, selisih median kedua
    sumber ±0,00007.
  - ETH: Binance 1 jam, Sep 2017 – Agu 2026.
  - Semua data tersimpan di `data/research/eksternal/pair_h1/`.
- **Tanpa look-ahead.** Kategori 💰 per pair (konf+⭐ / konf / ⭐ / biasa) dipilih **hanya dari periode LAMA
  (< Okt 2021)**: kategori yang rata-ratanya > 0 dengan n ≥ 30. Setelah itu baru diuji di periode BARU.
- **Syarat LOLOS:**
  - rata-rata BARU > 0 dengan n ≥ 40;
  - ≥ 60% tahun positif;
  - total/DD ≥ 3.

## Hasil (R = rata-rata 5 posisi per sinyal, 1R = SL)

| Pair | 💰 dipilih dari LAMA | LAMA R/sinyal | BARU R/sinyal (n) | Tahun + | Total/DD | Status |
|---|---|---|---|---|---|---|
| **ETH/USD** | semua kategori | +0,25 | **+0,06** (1.816) | 90% | 10,0 | LOLOS (tipis) |
| **USD/JPY** | konf+⭐, konf, biasa | +0,09 | **+0,07** (1.339) | 73% | 4,5 | LOLOS (tipis) |
| AUD/JPY | konf+⭐, konf, ⭐ | +0,09 | +0,05 (821) | 67% | 2,1 | tidak |
| GBP/JPY | konf+⭐, konf, ⭐ | +0,06 | +0,02 (838) | 67% | 1,5 | tidak |
| EUR/JPY | konf+⭐, ⭐, biasa | +0,05 | −0,06 (1.398) | 53% | 0,2 | tidak |
| GBP/USD | konf+⭐, konf, ⭐ | +0,02 | −0,03 (864) | 67% | 0,0 | tidak |
| USD/CHF | biasa | +0,02 | −0,06 (879) | 47% | −0,2 | tidak |
| USD/CAD | konf+⭐, ⭐ | −0,03 | −0,09 (852) | 33% | −0,7 | tidak |
| EUR/USD, AUD/USD, EUR/GBP, EUR/CHF | — (tidak ada kategori positif di LAMA) | −0,05 s/d −0,20 | — | 7–20% | negatif | tidak |

Pembanding dari mesin yang sama, periode BARU yang sama (sejak Okt 2021, `docs/KATEGORI_BADGE.md`): **XAU 💰
+0,21R** dan **BTC 💰 +0,19R** per sinyal. Kedua pair yang lolos hanya sekitar sepertiga dari angka itu.

## Uji ketahanan (setelah lolos)

**Per tahun di periode BARU (total R):**

| Pair | 2022 | 2023 | 2024 | 2025 | 2026 (s.d. Sep) |
|---|---|---|---|---|---|
| ETH/USD | +11 | +1 | +31 | +25 | +61 |
| USD/JPY | **+97** | +1 | −7 | −13 | +10 |

- USD/JPY: keuntungan BARU **hampir seluruhnya dari 2022** (tren besar karena Fed menaikkan bunga). Total 2023–2026
  ≈ 0.

**Spread ×2** (perkiraan akun Cent/kondisi buruk):

| Pair | BARU R/sinyal | Total/DD | Hasil |
|---|---|---|---|
| ETH/USD | +0,03 | 5,9 | masih positif, tipis |
| USD/JPY | +0,05 | 2,4 | **gagal** syarat total/DD ≥ 3 |

**ETH vs BTC:** ETH berkorelasi dengan BTC (korelasi R bulanan 0,38). 32% sinyal ETH muncul saat sinyal 💰 BTC
searah sedang terbuka.

| Sinyal ETH | LAMA R/sinyal | BARU R/sinyal (n) | Tahun + di BARU |
|---|---|---|---|
| Searah sinyal 💰 BTC yang sedang terbuka | +0,29 | +0,15 (591) | 2023–2026 positif semua |
| Tidak searah | +0,24 | +0,02 (1.225) | — |

Pemisahan ini **ditemukan setelah melihat data BARU**, jadi statusnya kandidat yang belum terbukti dan butuh uji
maju. Di LAMA, keunggulan sinyal yang searah hanya tipis.

## Kesimpulan jujur
- Tidak ada pair baru yang sekuat XAU atau BTC. Pola yang sama juga terlihat di `docs/MULTI_ASET.md` (2012–2022):
  - pair JPY positif tipis;
  - EUR/USD, AUD/USD, EUR/GBP, EUR/CHF, dan USD/CAD rugi.
- **USD/JPY:** lolos di atas kertas, tetapi hanya karena 2022 dan tidak tahan spread ×2. **Tidak disarankan.**
- **ETH/USD:** paling tahan (90% tahun positif, tetap positif dengan spread ×2), tetapi rata-rata BARU kecil
  (+0,06R).
  - Bila ingin dicoba, pakailah lot ½ sebagai uji maju, idealnya hanya saat sinyal 💰 BTC searah sedang terbuka
    (kandidat, belum terbukti).
  - Ingat juga bahwa ETH menambah risiko kripto yang sama dengan BTC.
- **Tidak ada yang dipasang.** Pengguna minta: pasang hanya setelah ia bilang "pasang".

## DIPASANG 6 Okt 2026: DOGE & ADA (izin "pasang semua WR dan profit tinggi yang belum dipasang")
Dari `research/pair_kripto.py` (114 varian, 9 lolos) dipilih varian dengan WR ≥ 58% di kedua periode dan profit
jelas positif: **DOGE** dan **ADA** "semua kategori, hanya saat 💰 BTC searah terbuka". Diverifikasi dengan replay
kode cloud asli (`python -m research.tambahan_cloud DOGE|ADA`, `docs/eksternal/hasil_kripto_cloud.txt`):

| Koin | LAMA (< Okt 2021) | BARU (sejak Okt 2021) | Tahun + | Pembanding BTC 💰 BARU |
|---|---|---|---|---|
| DOGE | n 219, WR 62%, +0,50R/sin | n 579, WR 60%, **+0,17R/sin**, DD −63R | 7/8 | +0,27R |
| ADA | n 369, WR 61%, +0,23R/sin | n 592, WR 60%, **+0,13R/sin**, DD −33R | 7/9 | |

Cloud (`tick.py`, env `KRIPTO_SIGNALS=0` mati, `KRIPTO_COINS=DOGE,ADA`): candle 1 jam Binance data-api (tanpa kredit
Twelve Data, cadangan TD), `_core.KRIPTO_CFG` (6 desimal, SL+ ≈ entry — `be_offset` 0,10 milik emas terlalu besar
untuk harga ±0,1, ukuran dalam KOIN karena ukuran kontrak broker berbeda), baris Supabase `doge`/`ada`, peringkat
selalu "biasa" (lot ½). Aplikasi 4.15: kelompok "Kripto (BTC·ETH·DOGE·ADA)", koin Ð/₳, ukuran "N DOGE".
Catatan jujur: DD BARU DOGE besar (−63R); 114 varian diuji → sebagian bisa kebetulan; tanpa auto order.

Tidak dipasang (sengaja): XLM (WR 55%), TRX/AVAX (≤ +0,08R), skema WR tinggi 2 TP (WR naik tetapi profit turun,
docs/SKEMA_WR.md), USD/JPY (gagal spread ×2), piramida (WR 25%), martingale/grid (negatif), spot "3 merah ≥10% TP 5%"
(tidak lebih baik dari 💎 yang sudah dipasang), 🌊 BTC jatuh→SELL (WR 46%) & ETH lonjak→BUY (+0,10R, WR < 62%).
