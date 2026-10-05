# 💎 Spot: cek semua koin Binance & deteksi "turun jauh" (5 Okt 2026, aplikasi 4.3)

Permintaan pengguna: "cek seluruhnya, supaya WR dan profit tinggi dan bisa deteksi apabila ingin turun jauh".
Kode: `research/spot_semua.py` (unduh), `research/spot_jatuh.py` (uji, `--simpan`). Hasil mentah:
`docs/eksternal/hasil_spot_jatuh.txt`. Data: `data/research/eksternal/spot_1d/` (653 pair USDT, termasuk yang sudah
dihapus Binance → tanpa bias penyintas).

## Cara uji
Tiap hari: semesta = 100 koin volume terbesar (rata-rata 7 hari s.d. kemarin), sama seperti cloud. Sinyal = model
terpasang (walk-forward) + BTC > SMA200, beli besok, limit jual +3%, maks 10 hari, biaya 0,30%. Pindai harian (pindai
tiap 10 menit sedikit lebih rendah, lihat `SPOT_PINDAI.md`). LAMA = 2019–Sep 2021, BARU = Okt 2021–Sep 2026.

## Hasil (BARU, sejak Okt 2021)
| | Naik +3% | Rata/sinyal | Portofolio 20 slot |
|---|---|---|---|
| Semua koin, tanpa filter kualitas | 89,9% | +0,64% | +10,8%/th, DD −37% |
| **+ filter kualitas (DIPASANG)** | **90,3%** | **+0,77%** | **+11,1%/th, DD −30%** |
| Ambang 97% (lebih sedikit sinyal) | 90,3% | +0,83% | +8,4%/th, DD −27% |

- Uji 54 koin besar sebelumnya (+1,16%/sinyal) terlalu optimistis: koin itu "penyintas". Angka jujur semua koin lebih
  rendah.
- **Filter kualitas** (dilewati bila): koin < 1 tahun, sudah ambruk ≥ 80% dari puncak 1 tahun, volume 24 jam ≥ 3×
  rata-rata 30 hari (panik). Rata per sinyal lebih baik di LAMA (+1,14% → +1,25%) dan BARU; DD BARU −37% → −30%.
- **Menebak sinyal mana yang akan turun jauh: TIDAK bisa diandalkan.** Model risiko jatuh AUC 0,53–0,58 (0,5 = tebak
  acak); melewatkan sinyal "berisiko" tidak memperbaiki BARU.
- **Menjual saat turun jauh memperburuk hasil**: setelah turun ≥ 10%, 66% posisi tetap kena TP (rata akhir −4%);
  setelah turun ≥ 20%, 36% tetap kena TP (rata akhir −12%). Jual saat −10/−15/−20%, saat pasar crash, atau saat BTC
  jatuh ke bawah SMA200: semua lebih buruk.
- Maka "deteksi turun jauh" dipasang sebagai **peringatan** ⚠️ (bukan jual otomatis): notifikasi sekali saat posisi
  turun ≥ 10% dan ≥ 20%, dengan angka teruji di atas.

## Yang dipasang
- Cloud `_spot.py`: `quality()` (env `SPOT_QUALITY=0` mematikan), candle 400 hari (umur & puncak 1 tahun), volume USDT
  dari kline Binance; pesan `spot_warn` (⚠️). Ringkasan `spot_status.skipped` = jumlah koin dilewati per alasan.
- Aplikasi 4.3: notifikasi ⚠️, kotak "⚠️ Turun 12% • teruji 66% tetap kena TP" di kartu posisi, angka teruji baru.

## Batas (jujur)
Tetap ada rugi besar sesekali (rugi rata −17%, terburuk −48% BARU). Hasil masa lalu tidak menjamin masa depan.
