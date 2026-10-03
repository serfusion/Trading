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

## Angka lain yang tampil di aplikasi/notifikasi (cek 3 Okt 2026, laporan mentah bagian 6)
Replay kode cloud + spread asli Exness. "Klaim" = angka yang sekarang tampil.

| Angka | Klaim | Replay (semua) | Replay sejak Okt 2021 | Status |
|---|---|---|---|---|
| Kartu "Teruji", 🏆, 📜 | — | — | sumbernya replay ini | ✅ |
| Badge teks notifikasi XAU konf | WR 48%, +0,09R | −0,02R | +0,15R | ❌ |
| Badge XAU konf+⭐ / BTC konf+⭐ | +0,31R / +0,31R | +0,24R / +0,20R | +0,23R / +0,27R | ⚠️ terlalu tinggi |
| Badge BTC ⭐ | +0,68R | +0,64R | +0,42R | ⚠️ |
| ⚡ XAU (skema bawaan) | WR 54%, +0,80R | WR 52%, +0,59R | WR 42%, +0,40R | ❌ |
| ⚡ XAU dengan SL+ 0,7R (otomatis di aplikasi) | WR 63%, +0,77R | WR 42%, +0,41R | WR 34%, +0,24R | ❌ (lebih buruk dari bawaan) |
| ⚡ BTC (SL+ 0,7R) | WR 64%, +0,75R | WR 48%, +0,66R | WR 52%, +0,44R | ❌ WR terlalu tinggi |
| BTC SL+ 0,7R ("WR +8 poin, profit sama") | — | +0,35R, WR 42% (bawaan +0,36R, WR 48%) | +0,35R | ⚠️ profit sama, WR tidak naik |
| Lapisan XAU | WR 52%, +0,28R | +0,18R | +0,08R | ❌ |
| Lapisan BTC | WR 49%, +0,49R | +0,48R | +0,48R | ✅ |
| 📰 XAU setelah berita | +0,45R vs +0,21R | +0,52R vs +0,13R | +0,28R vs +0,20R | ✅ (selisih mengecil) |
| 📰 BTC setelah berita | +0,61R vs +0,36R | +0,38R vs +0,36R | −0,06R (n 33) vs +0,35R | ❌ |

WR di sini = sinyal dengan hasil bersih > 0 setelah spread. SL+ di cloud = entry ± 0,10, sehingga keluar di SL+ ≈ 0
lalu minus spread → dihitung kalah; klaim lama memakai SL+ entry + 0,1R (riset), itu sebabnya WR klaim lebih tinggi.
Perbaikan teks (cloud) & pengaturan SL+ 0,7R (aplikasi) menunggu izin pengguna.

## TP1 0,7R (DIPASANG 3 Okt 2026, permintaan pengguna "WR tinggi, 1 posisi TP, sisanya dibiarkan")
Replay kode cloud asli + spread asli, sinyal dasar (`cloud_<aset>.csv` kini TP1 0,7R; versi 1R = `cloud_<aset>_tp1r.csv`):

| | WR LAMA → BARU → 2026 | R/sinyal BARU | Total BARU | Total LAMA |
|---|---|---|---|---|
| XAU TP1 1R | 49% → 53% → 72% | +0,21 | +131R | +134R |
| **XAU TP1 0,7R** | **59% → 63% → 76%** | +0,20 | +133R | +119R |
| BTC TP1 1R | 45% → 50% → 39% | +0,33 | +236R | +300R |
| **BTC TP1 0,7R** | **47% → 56% → 57%** | +0,33 | +243R | +237R |

WR naik 6–18 poin, profit sejak 2021 sama; sebelum 2021 profit lebih kecil (XAU −11%, BTC −21%). `_core.CFG["tp1_r"]`
0,7 (BTC ikut). SL+ 0,7R terpisah jadi tidak berpengaruh (TP1 sudah di 0,7R).

## Sinyal tambahan (DIPASANG 3 Okt 2026, izin "pasang semua") — `research/sinyal_tambahan.py` (99 sumber) + `research/tambahan_cloud.py`
Replay kode cloud asli, TP1 0,7R, spread asli (ETH 0,05%). Total BARU = dasar + lapisan × ½ lot.

| | WR LAMA / BARU | R/sinyal BARU | Total BARU | Keputusan |
|---|---|---|---|---|
| XAU sekarang (3 set, lapisan setelah TP1) | 59% / 63%, lapisan 61% | +0,20 / lapisan +0,04 | +144R | — |
| **XAU + set 100/40 & 120/50 + lapisan kapan saja (breakout baru) maks 5** | 60% / 63%, lapisan **62%** | +0,16 / lapisan **+0,22** | **+359R** | ✅ dipasang |
| BTC lapisan setelah TP1 maks 1 (pengganti) | 48% / 56% | +0,32 / lapisan +0,39 | +302R vs +332R sekarang | ❌ BTC tetap |
| **ETH ⭐ & konf+⭐ hanya saat 💰 BTC searah terbuka** | **70% / 56%** | **+0,25** | +130R | ✅ dipasang |

Catatan risiko: XAU kini jauh lebih banyak sinyal bersamaan (lapisan BARU 1.859 vs 550) — pakai lot ½ untuk lapisan.
Env Vercel: XAU_EXTRA_SETS=0, ETH_SIGNALS=0, LAYER_SIGNALS=0 untuk mematikan.

## Gap pekan forex (cek 3 Okt 2026, `research/verifikasi_gap.py`)
Kode cloud asli `_gap.gap_tick` diputar ulang per jam 2012–2026 (184 sinyal), spread akun Standard (×3 = perkiraan
spread buka pekan yang melebar).

| Pair | Sebelum Okt 2021: n, WR, R/sinyal | Sejak Okt 2021: n, WR, R/sinyal | Spread ×3 sejak 2021 |
|---|---|---|---|
| USD/JPY | 30, 83%, +0,27 | **4**, 25%, −0,74 | −0,77 |
| AUD/USD | 17, 82%, +0,20 | 6, 83%, +0,10 | +0,06 |
| AUD/JPY | 37, 73%, +0,05 | 9, 89%, +0,19 | +0,13 |
| EUR/JPY | 27, 78%, +0,15 | 9, 67%, −0,21 | −0,26 |
| EUR/CHF | 36, 72%, +0,10 | 9, 56%, +0,01 | −0,11 |

WR gap memang tinggi (72–83% sebelum 2021), tetapi untung per sinyal kecil dan sejak 2021 sinyalnya sangat sedikit
(4–9 per pair) → belum bisa dipastikan. Tidak diubah (tetap jalan); tampil di kartu 🏆 dengan jumlah sinyalnya.
