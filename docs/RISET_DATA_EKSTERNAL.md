# Riset Data Eksternal sebagai Filter Sinyal 💰

*28 September 2026. Semua angka dihasilkan ulang dengan kode di `research/eksternal*.py` (perintah di bagian 8);
keluaran lengkap di [`docs/eksternal/`](eksternal/). Tidak ada perubahan pada bot live (`xau_bot/`) maupun cloud
(`cloud/`).*

## 0. Ringkasan jujur

1. **Pertanyaan:** apakah data di luar grafik harga — kalender berita, yield riil & dolar (FRED), posisi spekulan
   (COT CFTC), jam sesi / spread nyata (Dukascopy), funding & open interest BTC (Binance) — bisa menyaring sinyal
   💰 yang sekarang dikirim cloud (XAU konf+⭐ & konf; BTC konf+⭐, konf, ⭐) supaya lebih untung?
2. **XAU (emas): tidak ada satu pun filter yang lolos kriteria "konsisten" untuk sinyal 💰** (1.185 sinyal
   2013–2026, 46 varian: berita, yield riil/dolar, COT, sesi). Sistem 💰 yang ada (konfluensi tren D1/H4 +
   momentum) tampaknya sudah menyerap informasi yang bisa diberikan data ini. **Rekomendasi: jangan tambahkan
   filter eksternal untuk XAU.**
3. **BTC: satu kandidat nyata — funding rate Binance.** Lewati BUY BTC bila rata-rata funding 24 jam berada di 10%
   tertinggi setahun terakhir (posisi long terlalu ramai), lewati SELL bila di 10% terendah. Lolos keempat syarat,
   tahan di 27/27 kombinasi parameter sekitarnya, dan tetap bekerja walau data terlambat 24–48 jam (penting: cloud
   di AS tidak bisa memanggil api.binance.com, HTTP 451; file harian data.binance.vision baru ada keesokan harinya).
   Uji nyata 2021–2026 (data terlambat 24 jam): **+171R → +214R**, rata-rata +0,144 → +0,217R/sinyal, 5 dari 6 tahun
   membaik. **Tetapi**: periode latih hanya 1 tahun (2021), sebagian besar manfaat dari sisi SELL (55 sinyal dibuang,
   −0,49R), dan 2024 sedikit memburuk. Ini **usulan**, bukan perubahan: cloud tidak diubah tanpa izin pengguna.
4. Filter lain yang lolos di atas kertas tetapi **tidak diusulkan**: BTC rasio long/short akun (bukti periode uji
   hanya 11–18 sinyal); BTC "lewati ≤ 2 jam sebelum NFP/CPI/FOMC" (8 sinyal, efek hilang di uji nyata karena sinyal
   yang ditolak masuk candle berikutnya); XAU COT "ikut ramai P90" (hanya konsisten di **semua** sinyal karena membuang
   sinyal biasa yang memang sudah tidak dikirim cloud; relevan hanya bila bot men-trade semua sinyal).
5. Beberapa varian tampak sangat bagus di satu periode (mis. yield riil + dolar 60 hari untuk BTC: +1,39R/sinyal di
   periode latih vs +0,70R), lalu **gagal di periode uji** (+0,10R vs +0,12R). Ini pola *overfitting* yang persis
   ingin dihindari; karena itulah aturan penilaian ditetapkan sebelum melihat hasil.
6. Data eksternal tetap berguna sebagai **informasi** (mis. menampilkan jadwal NFP/CPI/FOMC di aplikasi).
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

⏳ Bagian B (spread nyata BID/ASK Dukascopy + mesin yang sama di sumber data kedua): unduhan masih berjalan
(server membatasi laju).

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

- Rasio L/S akun: lolos di atas kertas dan tahan parameter, tetapi hanya 11–18 sinyal dibuang di periode uji → bukti
  terlalu tipis. Open interest: tidak berguna.
- **Cara menerapkan bila pengguna setuju** (belum dikerjakan): cloud mengunduh file harian
  `data.binance.vision/data/futures/um/daily/fundingRate/BTCUSDT/` (zip kecil, library standar) sekali sehari,
  menyimpan 1 tahun funding di Supabase, lalu sinyal BTC 💰 yang "ramai" dilewati (seperti `profit_only`). Sebelum
  itu sebaiknya dijalankan dulu sebagai **tanda informasi** di aplikasi selama beberapa bulan (uji maju).

## 7. Yang belum / keterbatasan

- **Data MT5 Exness pengguna (`data_mt5/`) belum diunggah** → spread asli akun Cent belum bisa diuji. Pengganti
  sementara: spread BID/ASK Dukascopy (bagian 5).
- M1 Dukascopy untuk 2012–2026 butuh ±10.000 unduhan; server membatasi laju (HTTP 503, ±15 detik/file) → hanya H1
  BID/ASK yang diunduh. Ekspor M1 dari MT5 pengguna lebih praktis.
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
```
