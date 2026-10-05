# 💎 Sinyal spot Binance: peluang naik lagi (4 Okt 2026, aplikasi 4.1)

Permintaan pengguna: "bukan hanya koin jatuh — BTC, ETH, BNB, semuanya; bila kemungkinan sangat tinggi koin itu naik
lagi, infokan di aplikasi mulai dari sinyal sampai close spot". Kode riset: `research/spot_peluang.py`
(`--final` = model yang dipasang). Cloud: `cloud/api/_spot.py` + `cloud/api/spot_model.json`. Aplikasi: `SpotCard.kt`.
Hasil mentah: `docs/eksternal/hasil_spot_peluang.txt`, `docs/eksternal/hasil_spot_model.txt`.

## Arti "naik"
Beli di open hari berikutnya (± 07:05 WIB), pasang **limit jual +3%**. Naik = limit jual terisi dalam **10 hari**.
Bila tidak terisi: jual di close hari ke-10. Biaya 0,30% pulang-pergi. Tanpa SL (SL −15% memperburuk hasil).

Penting: kripto bergerak liar, jadi **hari acak pun naik +3% dalam 10 hari di 76% kasus** (sejak Okt 2021; 82%
sebelumnya). Keunggulan sinyal = selisih dari angka dasar itu, bukan angka 90%-nya saja.

## Metode
- 20 koin besar yang hidup (BTC, ETH, BNB, SOL, XRP, ADA, DOGE, TRX, LINK, AVAX, DOT, LTC, BCH, XLM, ATOM, ETC, UNI,
  NEAR, AAVE, FIL) + 28 koin ambruk/delisting untuk pelatihan & uji (LUNA, FTT, UST, WAVES, ...). USDT tidak diberi
  sinyal karena USDT adalah dolar stabil (patokan harga semua pair).
- 15 fitur harian (jarak dari high 20/60 hari, RSI14, RSI2, hari merah beruntun, return 1/3/7/30 hari, z-score, jarak
  SMA50/SMA200, volatilitas, rezim BTC). Model gradient boosting, **walk-forward per tahun** (tahun Y hanya dilatih
  dengan data sebelum Y), random_state tetap.
- Sinyal = peluang model ≥ 93% **atau** pola "3 hari merah beruntun, turun ≥ 10% dalam 3 hari, di atas SMA200".
- Maks 10 posisi (10% modal spot per koin); satu posisi per koin.

## Hasil (20 koin live)
| | Sebelum Okt 2021 | Sejak Okt 2021 | 2025–2026 |
|---|---|---|---|
| Sinyal | 642 | 799 (±13/bulan) | 132 |
| Naik +3% (limit terisi) | 91% | **91%** | 92% |
| Rata-rata per sinyal | +0,86% | +1,16% | +1,57% |
| Rugi rata saat gagal | −18,4% | −14,1% | −12,2% |
| Terburuk | −58% | −46% | |
| Portofolio 10 slot / tahun | +16% (DD −33%) | **+14% (DD −19%)** | |
| BTC beli-tahan / tahun | +37% (DD −81%) | +12% (DD −77%) | |

Per tahun (portofolio 10 slot): 2020 −13%, 2021 +49% (LAMA); Okt–Des 2021 +4%, 2022 +10%, 2023 +10%, 2024 +27%,
2025 +18%, 2026 s.d. Sep +2%. Median lama posisi: 1 hari.

Kalibrasi sejak Okt 2021: tebakan 93–95% → kenyataan 91%; ≥ 95% → 92%. Angka di aplikasi = peluang model.

## Batas & risiko (jujur)
- 9 dari 10 sinyal untung kecil (+2,7%), 1 dari 10 rugi rata −14% (kadang −30% s.d. −46%). Tanpa batas 10% per
  koin, satu kegagalan bisa menghapus banyak kemenangan.
- 2020 rugi −13% (portofolio). Hasil masa lalu tidak menjamin masa depan.
- Data live: Vercel di AS (Binance global menolak AS, 451) → data-api.binance.vision, lalu api.binance.us, lalu
  Twelve Data (maks 4 kredit per tick). Belum bisa dites langsung dari sesi riset (host diblokir jaringan sesi);
  lihat `spot.source` / `spot_error` di respons /api/tick setelah redeploy.
- Hanya informasi: cloud tidak membuka order spot. Env Vercel: `SPOT_SIGNALS=0` mematikan, `SPOT_MAX` (bawaan 10).

## Perbaikan 5 Okt 2026: filter volatilitas (`research/spot_vol.py`, hasil `docs/eksternal/hasil_spot_vol.txt`)
Permintaan pengguna: lebih banyak koin, lewati volatilitas tinggi atau manfaatkan alurnya. Diuji (portofolio 10 slot):
| Varian | Naik +3% (BARU) | Portofolio BARU | Portofolio LAMA |
|---|---|---|---|
| Terpasang sebelumnya (20 koin) | 91% | +15%/th, DD −21% | +32%/th, DD −40% |
| 54 koin yang masih diperdagangkan | 90% | +4%/th, DD −51% | +62%/th, DD −40% |
| **20 koin, lewati volatilitas > P90 (DIPASANG)** | **92%** | **+15%/th, DD −14%** | +22%/th, DD −32% |
| 20 koin, lewati volatilitas > P70 | 91% | +10%/th, DD −10% | +19%/th, DD −14% |
| TP +5% saat volatil | 86% | +16%/th, DD −21% | +45%/th, DD −40% |
| Ikut tren saat volatil (sinyal baru) | 84% | +0%/th, DD −41% | +13%/th |
Kesimpulan: menambah koin memperburuk (koin kecil ambruk bersamaan); ikut tren saat volatil rugi sejak 2021. Dipasang:
lewati koin bila volatilitas 14 hari > 90% kondisi 365 hari terakhirnya (`_spot.vol_rank`, `skip_vol` di spot_model.json).
