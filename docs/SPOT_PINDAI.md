# 💎 Spot Binance: dipindai tiap 10 menit & ±100 koin (5 Okt 2026, aplikasi 4.2)

Permintaan pengguna (URGENT): "Spot Binance seharusnya dipindai beberapa menit, bukan per hari, dan koinnya bukan hanya
20 — masih banyak koin lain". Kode riset: `research/spot_pindai.py` (`--simpan` = angka teruji di aplikasi). Cloud:
`cloud/api/_spot.py`. Hasil mentah: `docs/eksternal/hasil_spot_pindai.txt`. Model & ambang **tidak berubah**
(gradient boosting yang sama, peluang ≥ 93% atau aturan 3 merah, TP +3% dalam 10 hari) — lihat `docs/SPOT_PELUANG.md`.

## Cara uji
- Data 1 jam data.binance.vision (sudah ada di repo, `data/research/eksternal/pair_h1`): 20 koin lama, 34 koin lain
  yang masih diperdagangkan (ALGO, SHIB, SUI belum pernah ikut pelatihan model), 22 koin yang sudah delisting.
- "Pindai tiap jam": di akhir tiap jam, candle harian hari ini yang **belum tutup** dianggap candle terakhir (open hari
  ini, high sejauh ini, close = harga sekarang). Fitur ini persis sama dengan yang dihitung cloud (tes
  `test_fitur_candle_berjalan_sama_dengan_riset_pindai`); di jam terakhir hari itu sama dengan fitur harian (selisih
  ~1e-10). Entry di open jam berikutnya, limit jual +3%, TP dicek dengan high per jam **setelah** entry, batas 240 jam.
- Model walk-forward per tahun (tahun Y hanya dilatih dengan data sebelum Y). Biaya 0,30% pulang-pergi.
- Pembanding = pindai harian (yang terpasang sebelumnya), dihitung di mesin per jam yang sama.
- LAMA = sebelum Okt 2021, BARU = Okt 2021 – Agu 2026.

## Hasil (BARU, sejak Okt 2021)
| Skema | Koin | Sinyal/bulan | Naik +3% | Rata/sinyal | Portofolio |
|---|---|---|---|---|---|
| Harian (lama, terpasang s.d. 4 Okt) | 20 | 14,5 | 91% | +1,26% | 10 slot +15,8%/th, DD −21% |
| Tiap jam | 20 | 29,5 | 89% | +0,88% | 10 slot +13,4%/th, DD −29% |
| Tiap jam | 54 hidup | 91,6 | 89% | +0,74% | 20 slot +13,7%/th, DD −42% |
| **Tiap jam + BTC > SMA200 (DIPASANG)** | **54 hidup** | **51,9** | **91%** | **+1,16%** | **20 slot +13,1%/th, DD −20%** |
| Harian + BTC > SMA200 | 54 hidup | 21,8 | 92% | +1,37% | 20 slot +11,7%/th, DD −15% |

Periode LAMA (sebelum Okt 2021), skema dipasang: naik 93%, rata +1,10%/sinyal, portofolio 20 slot +27,3%/th tetapi
DD −43% (pindai harian 20 koin: +19,9%/th, DD −42%).

Temuan:
1. **Pindai lebih sering saja memperburuk** rata-rata per sinyal (+1,26% → +0,88%): sinyal di tengah hari sering
   datang saat harga masih jatuh. Sinyal 2× lebih banyak, tetapi portofolio tidak lebih baik.
2. **Koin lebih banyak saja memperburuk risiko**: banyak koin memberi sinyal bersamaan saat pasar ambruk → 2022
   portofolio −32% (10 slot) / DD −42…−50%.
3. **Filter BTC di atas rata-rata 200 hari memperbaiki keduanya** — dan filter ini juga lebih baik di periode LAMA
   (dipilih dari LAMA, terkonfirmasi di BARU): sinyal hanya saat BTC tren naik. Rata per sinyal kembali +1,16%,
   DD kembali ±−20% walau sinyal ±3,5× lebih banyak. 2022 (BTC di bawah SMA200 hampir setahun) = **tidak ada sinyal**.
4. Koin yang tidak pernah dilatih (ALGO, SHIB, SUI) dengan skema dipasang: BARU naik 93%, rata +1,46% (n 188) →
   model tidak hanya cocok di koin pelatihan.
5. Varian lain TIDAK lebih baik (tidak dipasang): sinyal harus bertahan 2–3 jam, ambang 95%, maks 2/3/5 sinyal baru
   per hari (justru mengambil sinyal paling awal yang paling buruk).

## Yang dipasang (`cloud/api/_spot.py`, env Vercel)
- Tiap tick cloud (10 menit): daftar koin dari ticker 24 jam Binance — **100 pair USDT dengan volume terbesar**
  (`SPOT_COINS`), volume ≥ $5 juta/hari (`SPOT_MIN_VOL`), tanpa stablecoin/fiat/emas token/token pembungkus/leverage;
  diperbarui tiap 6 jam. Koin dengan riwayat < 201 hari otomatis dilewati (model butuh SMA200).
- Candle harian semua koin diambil paralel (16 sekaligus, batas waktu tick Vercel 60 dtk); bila waktu habis, koin yang
  terlewat didahulukan tick berikutnya.
- Sinyal = (peluang ≥ 93% atau 3 merah) **dan BTC > SMA200** (`SPOT_BTC_FILTER=0` mematikan filter — tidak
  disarankan). Maks **20 posisi** (`SPOT_MAX`, 5% modal spot per koin). Setelah CLOSE, koin yang sama paling cepat 1 jam
  lagi.
- Close: TP dicek dengan candle 15 menit yang mulai **setelah** entry (high pagi sebelum entry tidak dihitung); batas
  10 hari sejak entry. Cadangan bila candle 15 menit gagal: high harian setelah hari entry / harga sekarang.
- Ringkasan kartu 💎 dikirim tiap 30 menit (atau segera saat BELI/CLOSE): jumlah koin, waktu pindai terakhir, status
  BTC (⏸ "BTC di bawah rata-rata 200 hari: sinyal spot dijeda").

## Batas & risiko (jujur)
- 9 dari 10 sinyal untung kecil (+2,7% bersih), 1 dari 10 rugi rata −14% (terburuk −60%). Tanpa batas 5% per koin,
  satu kegagalan menghapus banyak kemenangan.
- 54 koin uji = koin yang **masih hidup** sekarang (bias penyintas); koin delisting diuji terpisah (BARU naik 89%, rata
  +0,57%). Koin baru/kecil di daftar 100 teratas belum punya riwayat panjang untuk diuji.
- Portofolio LAMA DD −43% (2021/awal 2022). Hasil masa lalu tidak menjamin masa depan.
- Sumber live (data-api.binance.vision / api.binance.us) belum bisa dites dari sesi riset (host diblokir jaringan
  sesi). Setelah redeploy, cek respons `/api/tick` → `spot.coins`, `spot.scanned`, `spot.s` (detik), `spot.errors`.
- Hanya informasi: cloud tidak membuka order spot.
