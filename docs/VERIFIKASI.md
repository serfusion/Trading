# Verifikasi menyeluruh sinyal 💰 (3 Okt 2026)

Permintaan pengguna: "Sebelum dipasang ... CEK, VERIFIKASI, UJI secara MENYELURUH". Laporan mentahnya ada di
`docs/eksternal/hasil_verifikasi.txt`.

| Skrip | Isi |
|---|---|
| `research/verifikasi_cloud.py` | Replay kode cloud asli |
| `research/verifikasi.py` | Analisis |

R = hasil rata-rata 5 posisi per sinyal (1R = rugi bila SL kena). LAMA = sebelum Okt 2021, BARU = sejak Okt 2021.

## Yang dicek

| # | Cek | Cara | Hasil |
|---|---|---|---|
| 1 | Apakah riset = yang dikerjakan cloud? | Kode cloud ASLI (`_core.tick`) diputar ulang candle demi candle 2012–2026, lalu dibandingkan dengan mesin riset | XAU 96–98% sinyal sama persis, kategori sama 99,9%, korelasi R 0,91. BTC 95–97%, 99,7%, 0,95. Sisanya karena detail: ATR20 cloud vs ATR14 riset, SL+ entry+0,10 vs +0,1R. Rata-rata BARU hampir sama. ✅ |
| 2 | Look-ahead (memakai data masa depan)? | Kategori dihitung ulang dari data yang dipotong tepat di candle sinyal | 300/300 sinyal acak sama ✅ |
| 3 | Biaya | Spread ASLI Exness per jam (XAUUSDc, BTCUSDm 2015–2026) | XAU: riset ($0,30) lebih konservatif dari spread asli ($0,16–0,26 sejak 2021) ✅. BTC: spread asli LEBIH BESAR dari asumsi riset (0,2% di 2017–19, 0,05–0,09% di 2022–24, 0,02% kini), jadi dihitung ulang dengan spread asli ⚠️ |
| 4 | Filter live | Replay memakai konfigurasi live: H4 EMA50 (XAU), funding + September (BTC), lapisan | lihat tabel di bawah |
| 5 | Kebetulan? | Bootstrap 95% dan t; p-acak 💰 vs bukan-💰 | XAU & BTC 💰 BARU: CI95 di atas 0 (t 3,2–3,5) ✅. Pilihan kategori: XAU nyata (p 0,001), BTC tidak (p 0,15) ⚠️ |
| 6 | Sumber data | Replay di data Twelve Data (feed yang dipakai cloud) vs data riset, periode sama | XAU 2021–2026: +0,22R vs +0,21R per sinyal (85% sinyal sama). BTC 2020–2026: +0,21R vs +0,26R (84% sama). Tetap positif ✅ |

## Hasil sinyal yang benar-benar dikirim (kode cloud, filter live, spread asli Exness)

| | LAMA R/sinyal | BARU R/sinyal [CI95] | 2026 (s.d. Sep) |
|---|---|---|---|
| **XAU 💰** (dasar) | +0,15 | **+0,21** [+0,08..+0,35], t 3,2 | 61 sinyal, WR 72%, **+56R** |
| — XAU konf+⭐ | +0,25 | +0,23 [+0,08..+0,40] | 41 sinyal, WR 85%, +60R |
| — XAU konf | −0,13 | +0,15 [−0,05..+0,37] | 20 sinyal, −4R |
| XAU lapisan 🔁 (lot ½) | +0,26 | +0,09 [−0,06..+0,25] | +20R |
| **BTC 💰** (dasar) | +0,40 | **+0,27** [+0,12..+0,42], t 3,5 | 134 sinyal, WR 45%, **+43R** |
| — BTC ⭐ | +0,87 | +0,42 [+0,17..+0,69] | +10R |
| — BTC konf+⭐ | +0,17 | +0,26 [+0,02..+0,52] | +38R |
| — BTC konf | +0,24 | +0,07 [−0,13..+0,30] | −5R |
| BTC lapisan 🔁 (lot ½) | +0,46 | +0,39 [+0,20..+0,59] | +38R |

**Total R per tahun (dasar):**

| | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|
| XAU | +8 | −1 | −13 | +26 | +68 | +56 |
| BTC | −16 | −4 | +106 | +34 | +39 | +43 |

## Kesimpulan
- **Angka saya sebelumnya terkonfirmasi** oleh kode cloud asli dan biaya asli:
  - XAU 💰 sejak 2021: +0,21R per sinyal (laporan lalu +0,21R).
  - BTC 💰 sejak 2021: +0,27R per sinyal setelah filter live (laporan lalu +0,19R tanpa filter).
- **Positif, tetapi tidak setiap tahun:**
  - XAU rugi di 2022–2023.
  - BTC rugi di 2021–2022.
  - Kalah beruntun dan tahun minus tetap akan terjadi.
- **Kategori lemah:**
  - XAU konf: LAMA rugi, BARU belum pasti, 2026 minus.
  - BTC konf: BARU ≈ 0, 2026 minus.
  - Keduanya masih dikirim karena aturan live tidak diubah tanpa izin. Pilihan "hentikan" butuh uji dampak; uji XAU sebelumnya justru memburuk.
- **Pilihan kategori 💰:**
  - XAU: terbukti lebih baik dari sinyal biasa (p-acak 0,001 di BARU).
  - BTC: tidak signifikan di BARU (p 0,15), dan di 2026 sinyal biasa BTC malah lebih baik. Sinyal BTC 💰 tetap positif secara keseluruhan.
- **Tidak ada perubahan logika sinyal live.** Yang berubah hanya tampilan aplikasi (3.26) dan sumber angka kartu 📜.

## Tanpa kategori konf (3 Okt 2026, `research/tanpa_konf.py`, izin "pasang")
| | BARU R/sinyal (total, DD) | LAMA total | 2026 |
|---|---|---|---|
| BTC live | +0,27 (+225R, DD −41) | +345R | +43R |
| **BTC tanpa konf** | **+0,33 (+236R, DD −32)** | +300R | +40R |
| XAU live | +0,21 (+131R, DD −42) | +134R | +56R |
| XAU tanpa konf | +0,19 (+105R, DD −69) | +172R | +57R |

BTC tanpa konf lebih baik di periode BARU (untung sedikit lebih besar dengan sinyal lebih sedikit, DD lebih kecil) →
disarankan dimatikan. XAU campur (BARU memburuk) → XAU konf tetap. Pemasangan di cloud butuh perubahan kode
`cloud/` yang diblokir pengaman sesi → menunggu izin pengguna.

### Koreksi: efek "menghalangi" kecil karena ada lapisan
Pengguna benar: dengan sinyal berlapis 🔁, sinyal tetap bisa masuk walau sinyal lain masih berjalan (BTC: breakout baru,
maks 2 lapisan per set, lot ½). Ukuran ulang (BTC sejak Okt 2021, spread asli):
- Setelah konf dimatikan muncul 71 sinyal dasar baru (+0,36R/sin). 44 di antaranya SUDAH masuk sebagai lapisan lot ½
  saat konf masih ada; 27 sisanya memang tidak masuk, dan rata-ratanya justru −0,42R.
- Sinyal konf sendiri: 198 sinyal, +0,07R/sin (+14R total, belum pasti positif).
- Gabungan (lapisan dihitung ½ lot): dengan konf +323R, tanpa konf +341R (+18R dalam 5 tahun, ±5%); 2026: +62R vs +60R.
Jadi alasan "menghalangi sinyal bagus" yang dulu saya pakai terlalu dibesar-besarkan. Selisihnya kecil; mematikan atau
menyalakan BTC konf hampir sama hasilnya (env Vercel BTC_SKIP_KONF=0 untuk menyalakan lagi).
