# Riset Data Eksternal sebagai Filter Sinyal 💰

*28 September 2026. Semua angka dihasilkan ulang dengan kode di `research/eksternal*.py` (perintah di bagian 8);
keluaran lengkap di [`docs/eksternal/`](eksternal/). Tidak ada perubahan pada bot live (`xau_bot/`) maupun cloud
(`cloud/`).*

## 0. Ringkasan jujur

1. **Pertanyaan:** apakah data di luar grafik harga — kalender berita, yield riil & dolar (FRED), posisi spekulan
   (COT CFTC), jam sesi / spread nyata (Dukascopy), funding & open interest BTC (Binance) — bisa menyaring sinyal
   💰 yang sekarang dikirim cloud (XAU konf+⭐ & konf; BTC konf+⭐, konf, ⭐) supaya lebih untung?
2. **XAU (emas): tidak ada satu pun filter yang lolos kriteria "konsisten" untuk sinyal 💰** (1.185 sinyal
   2013–2026, 62 varian: berita, yield riil/dolar, COT, sesi, GVZ/VIX, yield 2 th, breakeven, musiman). Sistem 💰 yang ada (konfluensi tren D1/H4 +
   momentum) tampaknya sudah menyerap informasi yang bisa diberikan data ini. **Rekomendasi: jangan tambahkan
   filter eksternal untuk XAU.**
3. **BTC: satu kandidat nyata — funding rate Binance.** Lewati BUY BTC bila rata-rata funding 24 jam berada di 10%
   tertinggi setahun terakhir (posisi long terlalu ramai), lewati SELL bila di 10% terendah. Lolos keempat syarat,
   tahan di 27/27 kombinasi parameter sekitarnya, dan tetap bekerja walau data terlambat 24–48 jam (penting: cloud
   di AS tidak bisa memanggil api.binance.com, HTTP 451; file harian data.binance.vision baru ada keesokan harinya).
   Uji nyata 2021–2026 (data terlambat 24 jam): **+171R → +214R**, rata-rata +0,144 → +0,217R/sinyal, 5 dari 6 tahun
   membaik; versi yang bisa diterapkan cloud (funding direkonstruksi dari file harian premium index, terlambat 36 jam)
   memberi hasil yang sama (+214R). **Tetapi**: periode latih hanya 1 tahun (2021), sebagian besar manfaat dari sisi SELL (55 sinyal dibuang,
   −0,49R), dan 2024 sedikit memburuk. **Dipasang di cloud atas permintaan pengguna (28 Sep 2026, "pasang semua")**
   — `cloud/api/_funding.py`, bisa dimatikan dengan env `BTC_FUNDING_FILTER=0`.
3b. **BTC: sinyal 💰 di bulan September** (putaran 2, §6b) rugi di 11 dari 11 tahun (rata-rata −0,43R, WR 29%,
   BUY maupun SELL; bulan lain +0,05 s/d +0,79R). Uji nyata: +765,7R → +826,5R. Dipasang (env `BTC_SEPT_FILTER=0`
   untuk mematikan). Catatan jujur: anomali kalender dengan hanya 11 sampel tahun — wajib dipantau.
4. Filter lain yang lolos di atas kertas tetapi **tidak diusulkan**: BTC rasio long/short akun (bukti periode uji
   hanya 11–18 sinyal); BTC "lewati ≤ 2 jam sebelum NFP/CPI/FOMC" (8 sinyal, efek hilang di uji nyata karena sinyal
   yang ditolak masuk candle berikutnya); XAU COT "ikut ramai P90" (hanya konsisten di **semua** sinyal karena membuang
   sinyal biasa yang memang sudah tidak dikirim cloud; relevan hanya bila bot men-trade semua sinyal).
5. Beberapa varian tampak sangat bagus di satu periode (mis. yield riil + dolar 60 hari untuk BTC: +1,39R/sinyal di
   periode latih vs +0,70R), lalu **gagal di periode uji** (+0,10R vs +0,12R). Ini pola *overfitting* yang persis
   ingin dihindari; karena itulah aturan penilaian ditetapkan sebelum melihat hasil.
6. Data eksternal tetap berguna sebagai **informasi**: dipakai di tab **Tanya** (chat berbasis data, tanpa AI) lewat basis pengetahuan
   statistik berita `cloud/api/pengetahuan.md` (mis. NFP lebih lemah dari perkiraan → emas naik dalam 1 jam pada 73%
   dari 67 rilis; sinyal 💰 XAU yang lahir ≤ 24 jam sebelum NFP/CPI/FOMC rata-rata −0,07R vs +0,40R sesudahnya).
7. Tidak ada jaminan profit. Semua hasil adalah simulasi historis dengan spread, tanpa swap/komisi/biaya funding.

## 1. Cara uji (sama untuk semua data)

- **Sinyal**: mesin cloud (F-ensemble 3 set Donchian H1, SL 3×ATR, 5 posisi, TP1 1R + SL+, lewati 3 candle setelah
  buka pekan untuk XAU), kategori dihitung di close candle sinyal — identik dengan `research/badge_stats.py`
  (statistik badge terreproduksi persis: XAU konf+⭐ 850 sinyal +0,309R, konf 335 +0,093R).
  Data harga: XAU H1 2012-11 – 2026-09 (ejtraderLabs + M5 2020–2026), BTC Bitstamp H1 2016 – 2026-09.
- **Waktu keputusan** = open candle entry. Setiap nilai eksternal dipakai mulai **waktu terbitnya**, bukan tanggal
  datanya (`asof()` di `research/eksternal.py`, dites di `tests/test_eksternal.py`):

| Data | Sumber | Dianggap terbit |
|---|---|---|
| Jadwal NFP/CPI/FOMC/PPI/Retail/PCE/GDP | ForexFactory historis (2010 – Jan 2026) + FRED release dates (NFP id 50, CPI id 10) + jadwal FOMC 2026 | jadwal diketahui jauh hari; arah kejutan (actual vs forecast) baru dipakai setelah jam rilis |
| DFII10, DGS10 | FRED + vintage ALFRED | vintage pertama setelah tanggal data, 21:00 UTC (median 1,9 hari) |
| DTWEXBGS (indeks dolar luas) | FRED + vintage ALFRED | terbit mingguan (H.10); sebelum 2019: Senin berikutnya 21:00 UTC (median 5,9 hari) |
| COT emas (Managed Money) & bitcoin CME (Leveraged Funds) | publicreporting.cftc.gov | Senin setelah Selasa laporan, 21:00 UTC; laporan saat shutdown 2013, 2018–19, 2025 dianggap terbit setelah antrean selesai |
| Funding rate BTCUSDT | data.binance.vision | saat `calc_time` |
| Open interest & rasio L/S BTCUSDT | data.binance.vision (metrics 5 menit) | akhir jam |
| BID/ASK XAUUSD H1 | datafeed.dukascopy.com | — (data harga kedua + spread nyata) |

- **Penilaian (ditetapkan sebelum melihat hasil)**, di sinyal 💰 dan — sebagai pembanding — di semua sinyal:
  latih XAU 2012-11..2018 / uji 2019..2026-09; BTC latih 2016..2020 / uji 2021..2026-09 (sama dengan
  `research/strategy_lab.py`). Filter **konsisten** bila: (a) sinyal yang dibuang rata-rata ≤ 0R di latih DAN uji
  (tidak membuang profit), (b) sinyal yang lolos lebih baik dari dasar di latih DAN uji, (c) ≥ 60% tahun: dibuang <
  lolos, (d) p-acak < 0,05 (5.000 undian filter acak yang membuang jumlah sinyal sama).
- **Uji nyata** untuk filter yang konsisten: filter dipasang di `allow()` seperti cloud (sinyal ditolak → set tetap
  kosong → candle berikutnya boleh masuk lagi bila breakout berlanjut).

Cara membaca tabel: "lolos / dibuang [dasar]" = R rata-rata per sinyal.

## 2. Kalender berita NFP / CPI / FOMC (`research/eksternal_berita.py`)

Cek silang tanggal 2012–2025: NFP FRED 172 vs ForexFactory 170 (167 sama); CPI 178 vs 167 (167 sama; FRED
mencatat juga rilis revisi). Tanggal FOMC 2026 dicek lewat lonjakan range emas pukul 14:00 ET di data M5
(mis. 17 Jun 2026: range 15 menit $117 vs $14 sebelumnya).

| XAU 💰 (1.185 sinyal) | Dikirim | Latih lolos/dibuang [dasar] | Uji lolos/dibuang [dasar] | Total R | p |
|---|---|---|---|---|---|
| Lewati entry ≤ 2 jam sebelum NFP/CPI/FOMC | 1.179 | +0,26 / +0,75 [+0,27] | +0,24 / −1,00 [+0,23] | +295 (dasar +294) | 0,37 |
| Lewati ≤ 24 jam sebelum NFP/CPI/FOMC | 1.064 | +0,28 / +0,15 [+0,27] | +0,29 / −0,38 [+0,23] | +306 | **0,009** |
| Lewati ≤ 4 jam sesudah NFP/CPI/FOMC | 1.088 | +0,23 / +0,64 | +0,22 / +0,37 | +246 | 0,91 |
| Lewati hari berita | 1.002 | +0,20 / +0,62 | +0,23 / +0,24 | +218 | 0,90 |
| Lewati bila kejutan data 24 jam terakhir berlawanan | 1.142 | +0,31 / −0,40 | +0,22 / +0,92 | +290 | 0,31 |

- **Tidak ada yang konsisten untuk XAU 💰.** Yang paling dekat: "lewati 24 jam sebelum NFP/CPI/FOMC" (p = 0,009,
  11/14 tahun) gagal syarat (a): sinyal yang dibuang di periode latih justru untung (+0,15R). Layak dipantau ke
  depan, belum layak dipasang.
- Sinyal yang lahir **sesudah** berita justru lebih baik (dibuang +0,37 s/d +0,64R) — sama dengan temuan lama
  (`docs/BACKTEST.md` §6): berita memicu breakout yang ditangkap trend.
- BTC 💰: "lewati ≤ 2 jam sebelum NFP/CPI/FOMC" lolos di atas kertas (8 sinyal dibuang, −0,78R), tetapi di uji
  nyata tidak berpengaruh (+765,7R → +764,9R) karena sinyal yang ditolak masuk di candle berikutnya.

## 3. Yield riil DFII10 & dolar (FRED) (`research/eksternal_makro.py`)

"searah makro" = BUY emas hanya bila yield riil / dolar turun dalam L hari bursa terakhir (teori klasik), SELL bila
naik; "lawan" = kebalikannya.

| | Dikirim | Latih lolos/dibuang [dasar] | Uji lolos/dibuang [dasar] | Total R | tahun | p |
|---|---|---|---|---|---|---|
| XAU 💰 yield riil 20h searah | 815 | +0,14 / +0,55 [+0,27] | +0,20 / +0,30 [+0,23] | +144 (dasar +294) | 7/14 | 0,97 |
| XAU 💰 yield riil 60h searah | 798 | +0,41 / +0,02 | +0,24 / +0,22 | +245 | 9/14 | 0,055 |
| XAU 💰 dolar 20h **lawan** | 406 | +0,90 / −0,00 | +0,38 / +0,14 | +234 | 10/14 | **0,000** |
| XAU 💰 yield riil + dolar 60h searah | 531 | +0,30 / +0,24 | +0,09 / +0,35 | +94 | 6/14 | 0,89 |
| BTC 💰 yield riil + dolar 60h searah | 598 | **+1,39** / +0,36 [+0,70] | +0,10 / +0,12 [+0,12] | +369 (dasar +606) | 8/11 | 0,003 |

- Teori "emas naik saat yield riil turun" **tidak** berguna sebagai filter sinyal breakout: versi 20 hari malah
  membuang sinyal terbaik. Hubungan itu memang patah sejak 2022 (emas naik bersama yield riil tinggi).
- Yang paling kuat secara statistik justru kebalikannya: sinyal 💰 **melawan** tren dolar 20 hari (emas breakout
  walau dolar menguat) rata-rata +0,58R vs +0,08R. Tetapi sinyal yang dibuang di periode uji masih untung (+0,14R →
  total turun 294 → 234R) dan **2025–2026 berbalik** (lolos −0,18/−0,58R, dibuang +0,57/+1,01R). Tidak stabil →
  tidak diusulkan.
- BTC: pola overfitting klasik — sangat bagus di latih, hilang di uji.

## 4. COT ekstrem (CFTC) (`research/eksternal_cot.py`)

Indeks COT = persentil net posisi (long − short)/open interest di 156 laporan terakhir (3 tahun). Posisi terakhir
(22 Sep 2026): emas Managed Money net +30,9% OI (indeks 61%); bitcoin CME Leveraged Funds net −35,6% (indeks 92%).

| | Dikirim | Latih lolos/dibuang [dasar] | Uji lolos/dibuang [dasar] | Total R | p |
|---|---|---|---|---|---|
| XAU 💰 hindari ramai P90 (BUY saat spekulan sangat long dilewati) | 902 | +0,19 / +0,48 [+0,27] | +0,26 / +0,12 [+0,23] | +212 (dasar +294) | 0,67 |
| XAU 💰 ikut ramai P90 | 1.132 | +0,28 / +0,13 | +0,24 / +0,04 | +288 | 0,29 |
| XAU 💰 tren posisi 4 minggu lawan | 470 | +0,45 / +0,17 | +0,37 / +0,13 | +187 | 0,015 |
| XAU **semua** sinyal, ikut ramai P90 | 2.909/3.416 | +0,07 / −0,07 [+0,05] | +0,13 / −0,12 [+0,10] | +307 (dasar +262) | **0,001 ✅** |

- "Hindari keramaian" (kontrarian) merugikan: breakout emas saat spekulan sudah sangat long tetap untung.
- "Ikut ramai P90" konsisten di **semua** sinyal XAU (uji nyata semua kategori: +262,1R → +302,9R; latih +0,046 →
  +0,068R, uji +0,101 → +0,128R), tetapi bekerja dengan membuang sinyal **biasa** (421 dari 507, rata-rata −0,11R)
  yang sudah tidak dikirim cloud. Di sinyal 💰: konf+⭐ yang dibuang +0,01R, konf yang dibuang +0,51R → tidak
  membantu. Hanya relevan bila bot live men-trade semua sinyal (menunggu keputusan pengguna).
- BTC: tidak ada yang konsisten.

## 5. Sesi & spread nyata (Dukascopy) (`research/eksternal_sesi.py`, `research/dukascopy.py`)

Bagian A — filter sesi (jam keputusan UTC) di data yang sama:

| XAU 💰 | Dikirim | Latih lolos/dibuang [dasar] | Uji lolos/dibuang [dasar] | Total R | p |
|---|---|---|---|---|---|
| Lewati Asia (22–07 UTC) | 954 | +0,32 / +0,04 [+0,27] | +0,21 / +0,32 [+0,23] | +247 (dasar +294) | 0,34 |
| Hanya London + NY (07–21) | 935 | +0,33 / +0,03 | +0,21 / +0,33 | +243 | 0,34 |
| Lewati sore NY (16–21) | 920 | +0,26 / +0,29 | +0,31 / −0,03 | +268 | 0,065 |
| Lewati 2 jam setelah buka harian (22–00) | 1.162 | +0,28 / −0,79 | +0,22 / +0,65 | +289 | 0,52 |
| Hanya tumpang tindih London–NY (12–16) | 416 | +0,12 / +0,35 | +0,46 / +0,11 | +132 | 0,18 |

- Tidak ada yang konsisten: sesi yang "buruk" di periode latih (Asia) justru bagus di periode uji, dan sebaliknya.
  Sinyal trend H1 tidak bergantung pada jam. BTC juga tidak ada yang konsisten (`docs/eksternal/hasil_sesi_a.txt`).

Bagian B — data kedua Dukascopy (H1 BID & ASK 2012-11 – 2026-08, 354 file bulanan; `docs/eksternal/hasil_sesi.txt`):

- Close Dukascopy vs data riset: selisih median $0,04 (p95 $0,54) di 80.967 candle yang sama.
- **Statistik 💰 terulang di sumber data independen**: konf+⭐ +0,334R (data riset +0,309R), konf +0,125R (+0,093R);
  💰 total +323,7R (spread tetap 0,30), 9/14 tahun untung.
- **Spread nyata** (ASK − BID di open tiap candle): median per tahun $0,24–0,38 (2012–2024), **$0,59 (2025) dan
  $0,70 (2026)** seiring harga emas naik. Per jam UTC (2024–26): ±$0,44–0,58 hampir sepanjang hari, tetapi
  **$1,77 pukul 22:00 dan $1,12 pukul 23:00 UTC** (pergantian hari / buka ulang).
- Mesin yang sama dengan spread nyata per candle: 💰 +315,8R vs +323,7R dengan spread tetap (−2,4%), latih +0,310R /
  uji +0,235R → biaya spread nyata kecil dibanding SL 3×ATR; hasil riset lain yang memakai spread 0,25–0,30 tetap valid.
- Filter sesi di data Dukascopy + spread nyata: tidak ada yang konsisten (lewati sore NY 16–21 UTC p = 0,011 tetapi
  sinyal yang dibuang di periode latih untung +0,26R; lewati 22–00 UTC membuang sinyal yang justru untung +0,53R).
- Saran praktis: saat entry manual di jam 22:00–23:00 UTC (05:00–06:00 WIB), spread broker bisa 2–3× lebih lebar;
  cek spread di MT5 sebelum masuk.

## 6. Funding rate & open interest BTC (Binance) (`research/eksternal_btc.py`)

Data mulai 2020 → latih/uji disesuaikan: funding latih 2021 / uji 2022–2026; OI & rasio L/S latih 2021–2022 / uji
2023–2026 (sinyal 💰 BTC 2021-01 .. 2026-09: 911).

| BTC 💰 (911 sinyal) | Dikirim | Latih lolos/dibuang [dasar] | Uji lolos/dibuang [dasar] | Total R | tahun | p |
|---|---|---|---|---|---|---|
| **Funding hindari ramai P90** | 717 | −0,10 / −0,16 [−0,11] | +0,25 / −0,11 [+0,17] | +128 (dasar +105) | 6/6 | 0,013 ✅ |
| Funding hindari ramai P80 | 597 | −0,13 / −0,07 | +0,33 / −0,13 | +142 | 5/6 | 0,001 (gagal: latih lolos < dasar) |
| Funding ikut ramai P80 | 842 | −0,08 / −0,99 | +0,11 / +0,79 | +59 | 2/6 | 0,99 |
| OI 24 jam naik | 600 | −0,10 / −0,22 [−0,15] | +0,31 / +0,16 [+0,26] | +101 | 4/6 | 0,11 |
| OI 24 jam turun | 311 | −0,22 / −0,10 | +0,16 / +0,31 | +4 | 2/6 | 0,88 |
| Rasio L/S akun hindari ramai P80 | 841 | −0,09 / −0,46 | +0,28 / −0,17 | +132 | 5/6 | 0,002 ✅ |

**Ketahanan funding** (periode uji, rata-rata sinyal yang lolos; dasar +0,17R) — tidak satu pun dari 27 kombinasi di
bawah dasar (terendah +0,17R, tertinggi +0,34R):

| Rata-rata funding | Jendela persentil | P85 | P90 | P95 |
|---|---|---|---|---|
| 8 jam | 0,5 / 1 / 2 tahun | +0,31 / +0,33 / +0,34 | +0,28 / +0,29 / +0,26 | +0,22 / +0,19 / +0,18 |
| 24 jam | 0,5 / 1 / 2 tahun | +0,26 / +0,28 / +0,24 | +0,25 / **+0,25** / +0,21 | +0,25 / +0,18 / +0,17 |
| 72 jam | 0,5 / 1 / 2 tahun | +0,28 / +0,29 / +0,27 | +0,28 / +0,23 / +0,20 | +0,25 / +0,24 / +0,17 |

- BUY yang dibuang (funding sangat positif): 139 sinyal, +0,03R (netral); SELL yang dibuang (funding sangat
  negatif): 55 sinyal, **−0,49R**. Artinya: short breakout saat pasar sudah sangat short (funding negatif ekstrem)
  cenderung gagal — konsisten dengan *short squeeze*.
- Data terlambat 24 jam: uji +0,23 / −0,07 (p = 0,032, tetap konsisten); 48 jam: +0,27 / −0,16.
- **Uji nyata** (filter di `allow()` seperti cloud, 2021–2026):

| | Sinyal | WR | Rata-rata | Total | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|---|---|
| Tanpa filter | 1.190 | 43,9% | +0,144R | +171R | −19 | −32 | +93 | +45 | +40 | +44 |
| Funding P90 (data seketika) | 980 | 45,3% | +0,226R | +221R | −14 | −13 | +126 | +35 | +38 | +49 |
| Funding P90 (terlambat 24 jam) | 988 | 45,6% | +0,217R | +214R | −13 | −26 | +115 | +39 | +45 | +53 |
| Funding dari premium index harian (terlambat 36 jam) | 1.025 | — | +0,209R | +214R | −16 | −33 | +113 | +54 | +46 | +49 |

- Rasio L/S akun: lolos di atas kertas dan tahan parameter, tetapi hanya 11–18 sinyal dibuang di periode uji → bukti
  terlalu tipis. Open interest: tidak berguna.
- **Kendala penerapan & jalan keluarnya:** api.binance.com / fapi diblokir dari server AS (HTTP 451, Vercel juga di
  AS), dan data.binance.vision hanya punya file funding **bulanan**. Tetapi file **harian** `premiumIndexKlines`
  (1 jam) tersedia, dan funding Binance dihitung dari premium index: funding ≈ rata-rata premium 8 jam +
  clamp(0,01% − premium, ±0,05%) (`funding_proxy()`, korelasi 0,82 dengan funding asli 2020–2026, 0,93 sejak 2022).
  Dengan proxy ini dan data dianggap terlambat 36 jam: subset p = 0,001 (tetap konsisten), uji nyata +171R → +214R.
- **Cara menerapkan bila pengguna setuju** (belum dikerjakan): cloud mengunduh file harian premium index kemarin
  (zip kecil, library standar) sekali sehari, menyimpan 1 tahun proxy funding di Supabase, lalu sinyal BTC 💰 yang
  "ramai" dilewati (seperti `profit_only`). Sebaiknya dijalankan dulu beberapa bulan sebagai **tanda informasi** di
  aplikasi (uji maju) sebelum benar-benar menyaring.

## 6b. Putaran 2 — ide dari literatur/web (`research/eksternal_putaran2.py`)

Dicari di web (28 Sep 2026): GVZ lebih berguna untuk rezim risiko daripada arah ([SSRN, Hysa](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6978741));
keputusan FOMC hampir selalu sudah diperkirakan pasar, yang menggerakkan emas adalah kejutannya
([Yale CSEC](https://csec.yale.edu/node/81)); musiman emas sebagian besar lemah, hanya bias Jumat yang signifikan
([evtradelabs](https://evtradelabs.com/blog/xauusd-seasonality-day-month-session)); funding BTC negatif ekstrem
sering mendahului short squeeze ([CoinDesk](https://www.coindesk.com/markets/2026/04/16/bitcoin-funding-rates-hit-most-negative-since-2023-history-suggests-bottom-is-in)).
Diuji dengan kriteria yang sama (16 varian): GVZ/VIX (FRED GVZCLS/VIXCLS), yield 2 tahun (proksi ekspektasi Fed /
FedWatch, FRED DGS2), breakeven 10 tahun (T10YIE), hari & bulan.

| | Dikirim | Latih lolos/dibuang [dasar] | Uji lolos/dibuang [dasar] | Total R | tahun | p |
|---|---|---|---|---|---|---|
| XAU 💰 GVZ naik 5 hari dilewati | 679 | +0,51 / −0,04 [+0,27] | +0,32 / +0,11 [+0,23] | +273 (dasar +294) | 8/14 | 0,000 |
| XAU 💰 VIX naik 5 hari dilewati | 641 | +0,41 / +0,12 | +0,39 / +0,04 | +253 | 7/14 | 0,002 |
| XAU 💰 lewati 15 Des – 5 Jan | 1.110 | +0,31 / −0,33 | +0,26 / −0,24 | +315 | 10/11 | 0,001 ✅ |
| XAU 💰 yield 2 th 20 hari searah | 801 | +0,13 / +0,50 | +0,24 / +0,21 | +159 | 8/14 | 0,90 |
| **BTC 💰 lewati September** | 1.503 | +0,79 / **−0,36** [+0,70] | +0,16 / **−0,48** [+0,12] | +658 (dasar +606) | **11/11** | 0,000 ✅ |

- XAU "lewati 15 Des – 5 Jan" lolos di atas kertas, tetapi di uji nyata **memburuk** (+323,8R → +308,3R): sinyal
  yang ditolak masuk lagi setelah 5 Januari di harga yang lebih buruk → tidak dipasang.
- XAU GVZ naik 5 hari: sinyal 💰 saat GVZ tidak naik WR 51,4% / +0,40R vs saat naik WR 45,5% / +0,04R — menaikkan
  profit per sinyal, tetapi total turun dan hanya 8/14 tahun searah → dijadikan **informasi** di chat, bukan filter.
- BTC September: bulan satu-satunya yang negatif (−0,43R, 121 sinyal); dipasang (lihat ringkasan 3b).

## 7. Yang belum / keterbatasan

- **Data MT5 Exness pengguna (`data_mt5/`) belum diunggah** → spread asli akun Cent belum bisa diuji. Pengganti
  sementara: spread BID/ASK Dukascopy (bagian 5).
- M1 Dukascopy untuk 2012–2026 butuh ±10.000 unduhan; server membatasi laju (HTTP 503, ±15 detik/file) → hanya H1
  BID/ASK (354 file) yang diunduh. Ekspor M1 dari MT5 pengguna lebih praktis.
- Nilai FRED yang dipakai adalah revisi terakhir (waktu terbitnya benar, nilainya bisa sedikit direvisi);
  DTWEXBGS sebelum 2019 adalah seri yang dihitung mundur.
- Kalender ForexFactory adalah hasil scraping pihak ketiga (dicek silang dengan FRED: cocok ±98%).
- Banyak varian diuji (XAU 46, BTC 53, ditambah kisi ketahanan funding) → beberapa p < 0,05 memang akan muncul secara kebetulan; karena itu syarat
  konsistensi (a)–(d) dipakai, bukan p saja.

## 8. Perintah

```bash
pip install -r requirements-dev.txt scikit-learn pyarrow
bash research/download_data.sh && python -m research.fetch_multi EUR_JPY BTC_USD_full
git clone -q --depth 1 https://github.com/spoluan/forex-factory-scraper data/research/spoluan_forex-factory-scraper
git clone -q --depth 1 https://github.com/ehsanrs2/forexfactory-scraper data/research/ehsanrs2_forexfactory-scraper
# secret environment: FRED_API_KEY (unduhan disimpan di data/research/eksternal, di-gitignore)
python -m research.eksternal_berita     # (1)
python -m research.eksternal_makro      # (2)
python -m research.eksternal_cot        # (3)
python -m research.dukascopy h1 2012-01 2026-09 && python -m research.eksternal_sesi   # (4)
python -m research.eksternal_btc        # (5)
python -m research.eksternal_putaran2   # putaran 2 (GVZ, VIX, yield 2 th, breakeven, musiman)
python -m research.event_stats          # basis pengetahuan chat -> cloud/api/pengetahuan.md
```

## 9. Yang dipasang (28 Sep 2026, permintaan pengguna "pasang semua")

- Cloud: filter BTC funding + September (`cloud/api/_funding.py`, `tick.py`), level TUTUP di heartbeat, tab Tanya
  `POST /api/chat` **berbasis data tanpa AI** (`cloud/api/chat.py`, `_chat.py`, `pengetahuan.json`; pengguna
  memilih tidak memakai AI) — aktif setelah branch ini di-merge ke branch produksi Vercel (`docs/CLOUD.md`).
- Aplikasi 2.9: tab **Tanya**, ikon baru, skema tetap 1 TP + 4 running, level TUTUP di kartu sinyal
  (APK di release `android-latest`).
- Tidak dipasang: filter XAU apa pun (tidak ada yang konsisten), dan keputusan lama di CLAUDE.md (skema A live,
  tab Tabungan Emas, bundle repo) yang bukan bagian riset ini.

## 10. SL+ bertangga, TP2/TP3, trailing ATR (pertanyaan pengguna 28 Sep 2026) — `research/sl_tangga.py`

Pertanyaan: dengan skema bawaan (posisi #1 TP1 1R, 4 posisi jalan, SL+ setelah TP1), apakah lebih baik SL+ terus
dinaikkan setiap harga mencapai target, atau memakai TP2/TP3? Mesin sama dengan cloud (hanya sinyal 💰, uji nyata),
mereproduksi skema bawaan persis (XAU 1.554 sinyal +323,8R; BTC 2.097 sinyal +765,7R). SL baru berlaku candle
berikutnya, SL dicek lebih dulu. Keluaran: `docs/eksternal/hasil_sl_tangga.txt`.

| Skema | XAU WR | XAU R/sinyal | XAU total | BTC WR | BTC R/sinyal | BTC total |
|---|---|---|---|---|---|---|
| **Bawaan** (TP1 1R + 4 jalan, SL+ setelah TP1) | 48,3% | +0,208 | +324R | 48,2% | +0,365 | +766R |
| Tangga 1R (2R→SL 1R, 3R→SL 2R, …) | 49,1% | +0,184 | +308R | 48,1% | +0,187 | +453R |
| Tangga 0,5R (1,5R→SL 0,5R, 2R→SL 1R, …) | 49,0% | +0,141 | +249R | 48,0% | +0,179 | +447R |
| Tangga jarak 2R (3R→SL 1R, …) | 48,8% | +0,189 | +301R | 47,9% | +0,237 | +534R |
| Tangga jarak 3R (4R→SL 1R, 5R→SL 2R, …) | 48,1% | +0,230 | +360R | 48,1% | +0,294 | +638R |
| TP 1R/2R/3R + 2 jalan | 48,3% | +0,162 | +252R | 48,2% | +0,248 | +520R |
| TP 1R/2R/3R + 2 jalan + tangga 1R | 49,1% | +0,157 | +262R | 48,1% | +0,156 | +379R |
| Trailing 3 ATR setelah TP1 | 49,2% | +0,151 | +276R | 47,1% | +0,182 | +463R |
| Trailing 5 ATR setelah TP1 | 49,1% | +0,173 | +285R | 48,1% | +0,253 | +570R |
| A: tanpa TP1 & SL+ (5 jalan) | 36,9% | +0,251 | +373R | 34,1% | +0,459 | +924R |
| SL+ lebih awal saat profit 0,7R (TP1 tetap 1 posisi) | 58,9% | +0,185 | +312R | 56,0% | +0,331 | +752R |
| SL+ lebih awal saat profit 0,5R | 64,4% | +0,146 | +273R | 60,5% | +0,247 | +633R |
| TP1 1R tanpa SL+ (4 jalan, SL awal tetap) | 39,9% | +0,211 | +313R | 37,6% | +0,372 | +750R |
| 3 posisi TP1 + 2 jalan, SL+ setelah TP1 | 48,3% | +0,120 | +186R | 48,4% | +0,196 | +412R |
| 3 posisi TP1 + 2 jalan, SL+ di 0,7R | 58,9% | +0,113 | +190R | 56,1% | +0,174 | +394R |

- **SL+ yang terus dinaikkan TIDAK sepadan.** WR hanya naik ≤ 1 poin (sebagian besar sinyal rugi kena SL awal
  sebelum 1R, jadi tangga tidak menolongnya), tetapi profit per sinyal turun 12–32% (XAU) dan 35–51% (BTC), karena
  profit sistem trend datang dari sedikit trend besar yang terpotong oleh tangga yang rapat.
- TP2/TP3 dan trailing ATR juga lebih buruk dari bawaan di kedua aset.
- Satu-satunya yang tidak merugikan XAU adalah tangga yang sangat longgar (SL baru naik ke +1R setelah harga +4R):
  XAU +360R vs +324R (11/14 tahun sama/lebih baik), tetapi di periode latih justru sedikit lebih buruk (+0,180 vs
  +0,191R) dan di BTC lebih buruk (−128R) → tidak diusulkan sebagai perubahan.
- **SL+ di 0,7R vs bawaan** (pertanyaan lanjutan): WR naik 8–11 poin (XAU 58,9% vs 48,3%, BTC 56,0% vs 48,2%)
  karena lebih banyak sinyal berakhir di +0,1R, tetapi total sedikit turun (XAU −3,5%, BTC −1,8%), hanya 5 dari
  14 (XAU) / 5 dari 11 (BTC) tahun lebih baik, dan drawdown XAU lebih dalam (−49,5R vs −43,6R) karena set lebih
  cepat kosong lalu mengambil sinyal baru. Praktis seimbang; bawaan sedikit lebih untung dan lebih sederhana
  untuk trading manual (satu tindakan saat TP1). SL+ 0,5R dan 3 posisi TP1 jelas lebih buruk.
- Kesimpulan: **pertahankan skema bawaan**. (Skema A tanpa TP1 memberi total terbesar tetapi WR turun ke 34–37%
  dan drawdown lebih dalam — sudah tercatat sebagai keputusan pengguna yang menunggu.)


## 11. Konsep dashboard "SMC ELITE PRO v9.1" (tangkapan layar pengguna 28 Sep 2026) — `research/smc_dashboard.py`

Kode indikator tidak dipakai. Setiap baris dashboard ditulis ulang sebagai aturan tanpa look-ahead lalu diuji
sebagai filter sinyal 💰 dengan kriteria konsisten yang sama (keluaran lengkap: `docs/eksternal/hasil_smc_dashboard.txt`).

| Baris dashboard | Aturan yang diuji | XAU 💰 | BTC 💰 |
|---|---|---|---|
| Higher Timeframe | searah tren mingguan (SMA20 W) / harian (SMA50 D) | tidak konsisten | tidak konsisten (harian: uji +0,12 vs +0,12) |
| PD Position (discount/premium, OTE) | BUY hanya di discount, SELL di premium (range 20 hari / 1 minggu) | tidak konsisten; hanya 41 sinyal lolos | tidak konsisten |
| Market Structure (HH/HL, LH/LL) | struktur swing H1 searah / tidak berlawanan | lebih buruk (buang sinyal bagus) | lebih buruk |
| Liquidity Pools (BSL/SSL) | BUY bila swing high belum tersapu di atas > swing low di bawah | lebih buruk | lebih buruk |
| FVG / displacement | FVG searah di 3 candle terakhir | lebih buruk | tidak konsisten |
| Zone Status (FVG lawan) | lewati bila ada FVG lawan belum terisi di depan harga (100 candle) | lolos kriteria (buang 104 sinyal, −0,07R; uji nyata +324R → +332R) | tidak konsisten |
| Session | sudah diuji di bagian 4 | tidak konsisten | — |

Cek ketahanan FVG lawan (XAU 💰): hanya lolos di jendela 100 candle; 75, 150, 200 candle gagal (dibuang +0,02 /
−0,01 / +0,11R). Dengan 20 uji sekaligus, satu "lolos" di p = 0,023 wajar terjadi kebetulan → **tidak dipasang**.
Catatan menarik: untuk SEMUA sinyal (termasuk "biasa" yang tidak dikirim), "BUY di premium" (ikut momentum) justru
konsisten lebih baik — kebalikan dari saran SMC "beli di discount" — dan sinyal biasa yang searah tren harian lebih
baik; kategori konf/⭐ yang sudah dipakai cloud menangkap efek tren itu.

Kesimpulan: tidak ada konsep SMC dashboard yang menaikkan hasil sinyal 💰 secara andal. Pelajaran yang diambil
hanya tampilan: status ringkas sekilas (WAIT / aktif), angka TUTUP besar, dan "profit terkunci" di kartu sinyal
(aplikasi 3.3). Persentase zona ("T3 74%") di dashboard itu tidak bisa diverifikasi dari luar.

## 12. Setelah TP1: tahan running atau ambil profit lebih awal, per kategori — `research/runner_kategori.py`

Pertanyaan pengguna (28 Sep 2026) untuk sinyal SELL format lama (kategori "⭐ saja", tidak dikirim lagi sejak ada 💰)
yang sudah TP1. Mesin sama dengan `sl_tangga.py`; semua varian identik sampai TP1. Keluaran:
`docs/eksternal/hasil_runner_kategori.txt`.

| XAU, R/sinyal (total) | bawaan (tahan sampai TUTUP/SL+) | semua tutup di TP1 | TP running 2R | TP running 3R | SL bertangga 1R | trailing 3 ATR |
|---|---|---|---|---|---|---|
| konf+⭐ (💰💰💰) | **+0,242 (+327R)** | +0,066 (+142R) | +0,121 (+214R) | +0,162 (+256R) | +0,206 (+302R) | +0,176 (+281R) |
| konf (💰) | +0,026 (+11R) | −0,018 | +0,017 | +0,070 (+29R) | +0,056 (+24R, 12/14 th lebih baik) | +0,027 |
| ⭐ saja (tidak dikirim) | −0,056 (−39R) | −0,062 (−50R) | −0,055 | −0,086 | **−0,012 (−8R, 11/15 th lebih baik, DD −39 vs −59)** | −0,054 |
| biasa (tidak dikirim) | −0,011 | −0,021 | −0,005 | +0,000 | −0,005 | +0,002 |

BTC: bawaan terbaik di semua kategori (mis. konf+⭐ +560R; varian lain ≤ +280R).

Kesimpulan: untuk sinyal 💰💰💰 (konf+⭐) dan semua BTC, **tahan running sampai TUTUP** tetap terbaik; menutup semua
di TP1 memotong hasil ±55–90%. Untuk kategori "⭐ saja" (sinyal lama), SL bertangga 1R (profit 2R → SL ke +1R,
3R → SL +2R, …) paling membantu tetapi kategori itu tetap rugi secara rata-rata — alasan kategori ini tidak dikirim
lagi. XAU konf (💰): tangga/TP 3R sedikit lebih baik; efek kecil, skema bawaan tidak diubah.

## 13. Sinyal XAU sesudah gap buka pekan (pertanyaan pengguna 28 Sep 2026, uji cepat)

Sinyal ≤ 24 jam setelah buka pekan, searah vs lawan arah gap (2012–2026):

| Kategori | searah gap | lawan gap | > 24 jam |
|---|---|---|---|
| konf+⭐ | n=98, WR 48%, +0,05R | n=56, WR 48%, +1,01R | n=696, +0,29R |
| konf | n=26, WR 77%, +1,19R | n=35, WR 37%, −0,14R | n=274, +0,02R |
| ⭐ saja (sinyal pengguna) | **n=43, WR 33%, −0,47R** | n=11, +0,29R | n=302, −0,02R |
| biasa | n=216, −0,03R | n=126, −0,05R | n=1533, +0,00R |

Pola berlawanan antar kategori dan sampel kecil → bukan aturan; tidak ada perubahan. Sinyal "⭐ saja" searah gap
justru kelompok terburuk; profit 28 Sep adalah satu kejadian.

## 14. Sinyal kembar: satu harga TUTUP (permintaan pengguna 28 Sep 2026) — `research/kembar_tutup.py`

Sinyal kembar = beberapa set (T40/15, T55/20, T80/30) sinyal di candle yang sama; pengguna entry sekali. Untuk SELL,
high 30 candle ≥ high 20 ≥ high 15 (BUY: low sebaliknya), jadi set paling lambat selalu tutup paling akhir.

| Grup 3 set (XAU n=173 / BTC n=241) | XAU R/grup | BTC R/grup |
|---|---|---|
| keluar di TUTUP pertama (T40/15) | +0,22 | +0,33 |
| rata-rata 3 set (cara aplikasi lama) | +0,33 | +0,40 |
| **keluar di set paling lambat (T80/30)** | **+0,42** | **+0,47** |

Grup 2 set: campuran (XAU T55/20+T80/30: T55/20 lebih baik; BTC: T80/30 lebih baik). Total semua grup kembar: set
paling lambat XAU ±+114R vs rata-rata ±+99R vs TUTUP pertama ±+80R; BTC ±+217R / ±+187R / ±+156R.
Dipasang di aplikasi 3.4 (tanpa mengubah cloud): kartu menampilkan satu harga TUTUP (set paling lambat), notifikasi
TUTUP hanya untuk set itu, riwayat/statistik memakai hasil set itu. Statistik aplikasi: MENANG = TP1 kena,
KALAH = SL / TUTUP sebelum TP1 (permintaan pengguna).

## 15. Entry/TP/SL karena berita? (permintaan tab News, 29 Sep 2026) — `research/news_trade.py`

Rilis AS high-impact 2010–2026 (NFP, CPI, PPI, Retail, PCE, GDP, ISM, Claims; 1.639 rilis) × XAU M15 2012–2026.
Entry di open candle 15 menit setelah rilis (+spread 2×), IKUT atau LAWAN kejutan, SL di ekstrem candle rilis atau
3 ATR, TP 1R / 2R / tutup 4 jam, semua kejutan / kejutan besar / candle rilis searah — 36 varian gabungan + per
grup NFP/CPI/PPI. Keluaran: `docs/eksternal/hasil_news_trade.txt`.

**Tidak ada yang lolos**: semua varian rata-rata rugi (−0,02 s/d −0,43R per trade), banyak yang rugi di 15 dari 15
tahun. Reaksi searah kejutan (bagian 1–2 pengetahuan chat) terjadi di candle pertama, sebelum orang bisa masuk;
sesudahnya ≈ acak dan spread berita membuatnya rugi. Tab News karena itu tidak menyarankan entry/TP/SL berita;
saran entry tetap hanya dari sinyal 💰 (sinyal yang lahir ≤ 4 jam setelah berita justru lebih baik dari rata-rata).
