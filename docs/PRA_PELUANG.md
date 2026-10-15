# 🎯 Persentase sebelum rilis untuk semua berita, termasuk FOMC (16 Okt 2026)

Permintaan pengguna: *"sebelum rilis pun kamu sudah predict persentase naik/turun dan berubah up to date, sekaligus mengecek data
informasi tambahan di internet dan tambahkan persentasenya"*. Pengguna juga meminta kepastian 70% untuk FOMC.

## Uji: `python -m research.pra_peluang`
Hasil lengkap ada di `docs/eksternal/hasil_pra_peluang.txt` dan `cloud/api/pra_peluang.json`.

- **Data:** tick asli Exness, 1.627 rilis 2016–2026.
- **Target:** gaya pengguna, yaitu masuk t0 − 1 detik lalu dilihat apakah emas lebih tinggi atau lebih rendah di detik 30 dan
  detik 60.
- **Input:** 8 data yang bisa dibaca live sebelum rilis:
  - tren emas 1, 4, dan 24 jam;
  - posisi terhadap EMA 50 dan EMA 200;
  - petunjuk berita yang sudah teruji;
  - yield obligasi 2 tahun (FRED DGS2);
  - dolar (FRED DTWEXBGS).
- **Cara uji:** model logistik per kelompok berita, walk-forward per tahun (dilatih hanya dengan tahun-tahun sebelumnya).

| Kelompok | Emas naik 1 mnt (dasar) | Model benar | Model vs dasar (Brier) |
|---|---|---|---|
| **FOMC** (86) | **49%** (LAMA 46 / BARU 52) | 52% | lebih buruk |
| NFP (127) | 47% | 52% | sama |
| CPI (128) | 59% | 57% | lebih buruk |
| PPI (96) | 53% | 51% | lebih buruk |
| ISM (225) | 49% | 55% | lebih buruk |
| Claims (194) | 42% | 55% | lebih buruk |

- **Kesimpulan:** tidak ada satu pun data sebelum rilis yang membuat peluang FOMC mendekati 70%.
- **Fitur tunggal:** hanya petunjuk berita teruji (KEJ +1) yang berarti: naik 62% (LAMA) / 68% (BARU). Fitur ini sudah dipakai
  untuk CPI, PPI, dan ISM.
- **Polymarket/Kalshi untuk keputusan Fed:** hampir selalu benar menebak keputusan, tetapi keputusan itu sudah tercermin di
  harga, jadi tidak menebak arah emas (docs/HARI_H.md).

## Dipasang
`cloud/api/_pra_peluang.py` (env `PRA_PELUANG=0` mematikan) mengisi baris XAU untuk berita tanpa arah teruji.

- **Baris utama:** contoh "Fed ⚪ naik 49% • turun 51% (masuk t−1 → 1 mnt) • 13 hari lagi". Tidak ada lagi baris "≈50%" tanpa
  angka.
- **Detail (ketuk):**
  - 🎯 angka dasar per periode;
  - 🧮 hasil model 8 data;
  - 🌐 data live yang dicek pada GET itu (Polymarket keputusan Fed, pernyataan Fed terbaru, tren emas 4 jam), dengan jam
    pengecekan.
- Diperbarui tiap GET, yaitu tiap 60 detik, atau tiap 20 detik bila rilis ≤ 15 menit lagi.
- Berita yang punya arah teruji (CPI, PPI, ISM Jasa, …) tidak diubah.
