# Momen Entry, Mode Perang Timur Tengah, WTI, dan Skema SL+ (30 Sep 2026)

*Kode: `research/momen.py`, `research/mode_perang.py`, `research/wti.py` (sinyal dari `research/rekomendasi.py`,
sama dengan mesin cloud). Setiap hasil dibagi dua: **LAMA** (sebelum Okt 2021: XAU 2012–2021, BTC 2016–2021) dan
**BARU** (5 tahun terakhir, Okt 2021 – Sep 2026). Sinyal kembar dihitung 1 entry. BTC sudah memakai filter September
dan swap. Tidak ada perubahan pada bot atau cloud. Semua hasil adalah simulasi historis, bukan jaminan.*

## 1. Skema SL+: jawaban tetap

| | LAMA | BARU (5 th) |
|---|---|---|
| XAU TP1 → SL+ di entry, tahan sampai TUTUP (**bawaan**) | WR 46,8%, +0,205R, **+93,9R** | WR 52,8%, +0,225R, **+69,0R** |
| XAU SL+ saat profit 0,7R | WR 56,3%, +0,183R, +88,1R | WR 60,7%, +0,174R, +57,0R |
| BTC bawaan | WR 56,0%, +0,672R, +313,3R | WR 45,3%, +0,243R, +108,0R |
| BTC SL+ 0,7R | WR 62,6%, +0,624R, +315,3R | WR 53,8%, +0,232R, +107,6R |

- **Untuk profit: pakai bawaan** (TP1 → SL+ di entry → tahan sampai TUTUP). Di XAU, 0,7R memotong profit
  6% (LAMA) sampai 17% (BARU).
- **Di BTC hasil keduanya praktis sama**, tetapi 0,7R memberi WR 8–9 poin lebih tinggi. Pilihan 0,7R hanya
  masuk akal untuk BTC, atau kalau kamu tidak bisa memantau.

## 2. Momen entry: 13 ciri diuji

Batas tertil dipilih dari periode LAMA, lalu dinilai di BARU. Syarat konsisten: lebih baik dari dasar di
LAMA dan BARU, ≥ 60% tahun menang, dan p-acak < 0,05.

| Ciri | XAU | BTC |
|---|---|---|
| **Volatilitas ATR rendah** (persentil 60 hari < 33%) | **KONSISTEN**: LAMA +0,59R vs +0,21, BARU +0,39R vs +0,23, 12/14 th, p = 0,002 | tidak (BARU +0,11 vs +0,24) |
| Kembar ×1/×2/×3 | tidak (×3: +0,25 / +0,32) | tidak (×3 terbaik tapi p = 0,23; ×1 BARU hanya +0,07R) |
| ADX, badan candle, lebar konsolidasi, umur tren, jarak EMA50, momentum 60 hari, jam, hasil sinyal sebelumnya, OVX | tidak | tidak (badan candle kecil p = 0,047, batas; tidak dipakai karena banyak uji) |
| Hari (Selasa–Kamis vs Jumat–Minggu) | tidak | lolos di atas kertas, tapi **uji nyata memburuk** (LAMA +312,7 → +261,9R, BARU +108,0 → +103,0R) |

**XAU per tahun** (rata-rata R per entry; volatilitas rendah | sedang | tinggi):

| Tahun | Rendah | Sedang | Tinggi |
|---|---|---|---|
| 2013 | +1,57 | +0,20 | +1,36 |
| 2014 | +1,57 | −0,29 | −0,02 |
| 2015 | +0,01 | −0,48 | +0,03 |
| 2016 | +0,21 | +0,27 | +0,44 |
| 2017 | +0,22 | +0,11 | −0,17 |
| 2018 | +0,13 | −0,60 | −0,04 |
| 2019 | +0,12 | −0,13 | +0,02 |
| 2020 | +1,25 | +0,70 | −0,35 |
| 2021 | +0,02 | +0,04 | −0,40 |
| 2022 | −0,27 | −0,06 | +0,24 |
| 2023 | +0,91 | −0,07 | −0,20 |
| 2024 | +0,33 | +0,62 | −0,13 |
| 2025 | +0,60 | +0,35 | +0,40 |
| 2026 | +0,92 | +0,31 | −0,01 |

Ukuran lot dengan risiko maks 0,5% (hasil %/tahun, max DD, rasio):

| Lot | LAMA | BARU |
|---|---|---|
| Rata 0,5% | +5,4%, DD 11,6%, 0,47 | +7,1%, DD 11,2%, 0,63 |
| 0,5% saat volatilitas rendah, 0,25% lainnya | +5,3%, DD 6,4%, **0,82** | +5,6%, DD 8,7%, 0,64 |
| 0,5 / 0,35 / 0,25% | +5,1%, DD 7,8%, 0,66 | +6,1%, DD 9,7%, 0,63 |

Artinya, momen volatilitas rendah memberi profit per entry sekitar 2× rata-rata. Tetapi dengan batas risiko 0,5%,
manfaatnya hanya drawdown yang lebih kecil, bukan total profit yang lebih besar. Profit baru naik kalau lot di momen
itu melebihi 0,5%.

## 3. Mode perang Timur Tengah

Data FRED menunjukkan guncangan minyak besar tahun ini. OVX (volatilitas minyak) naik dari ±33–42 (Des 2025–Jan
2026) menjadi **95 di Maret 2026**. WTI naik dari ±$60 ke **$91–102 (Mar–Mei 2026)**, lalu $80–98 sampai September.

**XAU:**

| Mode (dipakai sejak data terbit, tanpa melihat masa depan) | LAMA perang / normal | BARU perang / normal |
|---|---|---|
| WTI naik ≥ 10% dalam 10 hari | −0,06R (33) / +0,23 | **−0,53R (18)** / +0,27 |
| Brent naik ≥ 10% dalam 10 hari | −0,08R (37) / +0,23 | −0,23R (23) / +0,26 |
| 30 hari setelah eskalasi besar (deskriptif) | −0,53R (12) | −0,51R (21) |

- **Kisi 24 kombinasi** (WTI/Brent × 5/10/20 hari × 5–15%): 4 konsisten, semuanya di jendela **10 hari ≥ 10–15%**.
  Jendela 20 hari tidak konsisten. Artinya lonjakan cepat merusak breakout emas, kenaikan pelan tidak.
- **Uji nyata** (sinyal XAU 💰 dijeda selama WTI ≥ +10%/10 hari): LAMA +93,9 → **+95,6R**, BARU +69,0 → **+78,6R**,
  7 tahun membaik dan 2 memburuk, 2026 +3,6R. Ambang 7,5% juga membaik (+98,0R / +77,9R), sedangkan 5% campur aduk.
- **Episode:**

  | Tanggal | Kejadian | XAU 💰 dalam 30 hari |
  |---|---|---|
  | 14 Sep 2019 | Abqaiq | −1,72R |
  | 3 Jan 2020 | Soleimani | −4,64R |
  | 7 Okt 2023 | Hamas–Israel | −4,55R |
  | 13 Apr 2024 | Iran → Israel | −1,72R |
  | 1 Okt 2024 | Iran → Israel | −3,49R |
  | 13 Jun 2025 | perang 12 hari | −1,00R |

  XAU rugi di keenam episode, sedangkan BTC untung di 5 dari 6.
- **Catatan jujur:** sampelnya kecil (51 sinyal di mode perang) dan ada 24 kombinasi yang diuji. Ini **kandidat
  kuat**, belum pasti.

**BTC:** 0 dari 24 kombinasi konsisten. BTC tidak terpengaruh mode perang, jadi tetap jalan.

## 4. WTI per tahun (Turtle D1 55 hari, kandidat dari `docs/UJI_DUNIA.md`)

| Sumber | TP 1R: WR, rata-rata | Tahun untung | LAMA | BARU (5 th) |
|---|---|---|---|---|
| OANDA CFD 2005–2020 (data uji dunia) | 60,4%, +0,204R | 12/16 | +31,4R | — |
| Yahoo CL=F 2000–2026 | 52,2%, +0,038R | 10/27 | +5,0R | +2,8R (35 trade) |
| FRED spot 1986–2026 (close saja) | 54,1%, +0,039R | 24/41 | +25,8R | **−6,9R** (57 trade) |

- Keunggulan WTI yang dulu terlihat **hanya muncul di satu sumber data dan satu periode**. Tahun-tahun sebelumnya
  maupun 5 tahun terakhir hampir nol atau rugi. Mode perang juga tidak menolong WTI (hasilnya berganti tanda antar
  sumber).
- 2026: Turtle menangkap lonjakan Maret (3 × +1R). Tetapi satu tahun bagus tidak cukup.
- **Kesimpulan: jangan tambahkan WTI.**

## 5. Rekomendasi (menunggu izin untuk dipasang)

1. **Mode perang XAU**: jeda sinyal 💰 XAU selama WTI naik ≥ 10% dalam 10 hari (data FRED), lalu tampilkan status
   "🛢️ Mode perang" di aplikasi. BTC tetap jalan. Bisa dimatikan lewat env.
2. **Momen emas XAU** (volatilitas rendah): tanda ⚡ di kartu sinyal. Pilihan lot: penuh saat ⚡, setengah untuk XAU
   lainnya. Ini menurunkan drawdown, bukan menaikkan total profit (pada risiko maks 0,5%).
3. **SL+**: XAU pakai bawaan (profit maksimal). BTC boleh 0,7R (profit sama, WR lebih tinggi). Butuh pengaturan
   per pair di aplikasi.
4. **Tidak dipakai**: WTI, hari/jam, ADX, kembar, dan 9 ciri lain.

## 6. Uji ulang dengan sumber minyak lain: Twelve Data (USO/BNO) + Dukascopy

`python -m research.perang_uso --duka` (30 Sep 2026). WTI/Brent di Twelve Data hanya tersedia di paket berbayar,
jadi dipakai ETF **USO** (≈ WTI) dan **BNO** (≈ Brent), harian, dianggap terbit 21:15 UTC. Dukascopy
**LIGHTCMDUSD/BRENTCMDUSD**: candle harian BID (hari UTC, data s.d. 31 Agu 2026). Aturan sama dengan bagian 3
(naik ≥ 10% dalam 10 hari bursa, jeda sinyal 💰 XAU selama aktif). Dukascopy WTI cocok dengan FRED: median selisih
harga 0,4%, status "≥ 10%/10 hari" sama di 98,7% hari.

**Uji nyata XAU 💰 (total R; tanpa filter: LAMA +93,9 / BARU +69,0):**

| Sumber pemicu | LAMA | BARU (5 th) | Tahun membaik / memburuk |
|---|---|---|---|
| FRED WTI (sumber label ⚠️ di cloud) | +95,6 | **+78,6** | 7 / 2 |
| Twelve Data USO | **+105,0** | +71,0 | 9 / 3 |
| Twelve Data BNO | +101,1 | +71,7 | 6 / 3 |
| Dukascopy WTI | +101,2 | +69,2 | 8 / 3 |
| Dukascopy Brent | +93,2 | +68,8 | 4 / 6 (memburuk) |
| Gabungan: WTI salah satu (FRED/USO/Duka) | +98,8 | +77,3 | 9 / 3 |
| Gabungan: WTI ≥ 2 dari 3 | +104,4 | +68,7 | 7 / 4 |
| Gabungan: USO atau Duka WTI (tanpa FRED) | +104,2 | +71,3 | 9 / 3 |
| Gabungan: 5 sumber, salah satu | +99,4 | +75,1 | 8 / 4 |

- **Positif (arah terkonfirmasi):** di ketiga sumber WTI, sinyal 💰 XAU saat minyak melonjak rata-rata ≤ 0R di LAMA
  dan BARU, sedangkan sinyal normal di atas rata-rata. Kisi 12 kombinasi: USO konsisten 4, BNO 2, Duka WTI 1,
  Duka Brent 0. Efeknya paling jelas pada **WTI**; Brent tidak mengonfirmasi.
- **Tetapi besarnya di 5 tahun terakhir jauh lebih kecil** di sumber lain: tambahan BARU hanya +0,2R sampai +2,7R,
  bukan +9,6R seperti FRED. Keunggulan besar FRED di BARU sebagian karena kebetulan waktu (FRED terbit 1–2 hari
  lebih lambat, sehingga sinyal yang ditandai berbeda). Tumpang tindih sinyal yang ditandai FRED dan USO hanya ±50%.
- **Gabungan tidak mengalahkan FRED saja di kedua periode.** Yang paling seimbang "WTI salah satu" (+4,9R LAMA,
  +8,3R BARU dibanding tanpa filter), setara dengan FRED (+1,7 / +9,6), tetapi butuh tiga sumber data.
- **Peluang trade minyak/emas setelah lonjakan (USO/BNO/XAU):** 0 kandidat dari 24 kombinasi (biaya 0,05%). Hasil
  bagian 3 tetap: jangan trade minyak saat mode perang.
- Banyak kombinasi yang diuji (24 kisi + 7 gabungan) dan sampel kecil (±50 sinyal) → perlakukan sebagai konfirmasi
  arah, bukan angka pasti.

**Kesimpulan:** label ⚠️ mode perang (FRED WTI) **tetap dipakai apa adanya**. Sumber lain mengonfirmasi arahnya,
tetapi tidak ada gabungan yang lebih baik. Tidak ada perubahan cloud/aplikasi. Bila FRED suatu saat gagal diakses,
USO (Twelve Data, 1 kredit/hari) atau Dukascopy WTI layak jadi cadangan (hasil setara di LAMA, sedikit di bawah
FRED di BARU). Catatan data: file Dukascopy bulan berjalan belum tersedia sebagai H1 bulanan (September 2026
kosong), jadi untuk pemakaian live perlu file per hari.
