# Laporan Backtest XAUUSD

Semua angka di bawah ini dihasilkan dari data harga **asli** XAUUSD. Aturannya konservatif:
spread ikut dihitung; kalau SL dan TP tersentuh di candle yang sama, dianggap SL; TP tidak
dihitung di candle saat order limit terisi; tidak ada *look-ahead*. Swap/komisi **belum**
dihitung.

## 1. Data (±350 ribu candle)

| Dataset | TF | Periode | Candle | Sumber |
|---|---|---|---|---|
| A | M15 | Mei 2012 – Mar 2022 | 230.400 | [ejtraderLabs/historical-data](https://github.com/ejtraderLabs/historical-data) |
| B | M5 | Apr 2025 – 17 Sep 2026 | 101.023 | [dineshelumalai007/xauusd-5m](https://github.com/dineshelumalai007/xauusd-5m) |
| C | M1→M5 + XAGUSD M5 | Feb – Mei 2026 | 17.371 | [Sai310421/xauusd-data](https://github.com/Sai310421/xauusd-data) |

Zona waktu A & B = jam server MT5 "New York + 7" (buka mingguan selalu Senin 01:00),
dikonversi ke UTC. C sudah UTC. Spread: 0.30 (A), 0.25 (B, C).

Metode anti-*overfitting*: parameter hanya dipilih di periode pengembangan, lalu diuji di
periode yang **tidak pernah dilihat** (out-of-sample, OOS).

## 2. Bisakah arah candle berikutnya ditebak?

| Data | Tebak "sama dengan candle sekarang" | Tebak "berlawanan" |
|---|---|---|
| M5 2025–26 (101 rb) | 49,25% | 50,75% |
| M15 2012–22 (230 rb) | 47,86% | 52,14% |

Arah satu candle ≈ lempar koin. Selisih 2% di M15 lebih kecil dari biaya spread, jadi tidak bisa
diperdagangkan. **Tidak ada setup yang bisa menebak candle berikutnya secara konsisten.**

## 3. Setup SMC (sweep → MSS → FVG/OB) — TIDAK LOLOS

Diuji memakai `SmcStrategy` yang sama dengan bot, di setiap candle.

| Data | Setup | Default bot | TP 1R | TP 1R + BE + 3R | TP 2R |
|---|---|---|---|---|---|
| M5 2025–26 (sebelum Feb 2026) | 2.871 | −0,18R | −0,16R | −0,11R | −0,14R |
| M5 2025–26 (sesudah Feb 2026) | | −0,18R | −0,01R | +0,05R | −0,16R |
| M15 2012–17 | 7.215 | −0,16R | −0,23R | −0,20R | −0,18R |
| M15 2018–22 | | −0,26R | −0,31R | −0,29R | −0,24R |
| M5 2026 + SMT perak asli | 443 | −0,18R | −0,15R | | |

- Arah sinyal benar setelah 1–24 candle: **46–49%** (lebih buruk dari lempar koin).
- Skor konfluensi lebih tinggi **tidak** memperbaiki hasil; SMT juga tidak.
- Konfigurasi terbaik hasil pencarian di data M5 (+0,16R, 89 trade) **gagal** di 10 tahun data
  M15 (−0,16R / −0,12R) → itu hasil kebetulan (*overfitting*).

Kesimpulan: aturan SMC yang diotomasi **rugi** secara konsisten setelah biaya (16 model SMC/ICT populer
lain juga rugi — bagian 10). Mode `smc`
tetap tersedia, tapi **bukan default** dan hanya disarankan untuk mode sinyal.

## 4. Trend-following Donchian H1 — LOLOS

Aturan (`xau_bot/trend.py`): BUY bila close H1 > high tertinggi 55 bar sebelumnya, SELL bila
close < low terendah 55 bar; SL awal 3×ATR(20); keluar saat close menembus channel 20 bar
berlawanan; tidak ada TP (profit dibiarkan berjalan).

### 4.1 Ketahanan parameter (riset, satuan R)

76 kombinasi (entry 30–100, exit 10–30, SL 2–3,5 ATR) per timeframe:

| TF | Positif di 2012–17 | Positif di 2018–22 (OOS) | Positif di 2025–26 (OOS) | Positif di ketiganya |
|---|---|---|---|---|
| **H1** | 100% | **99%** | 100% | **99% (75/76)** |
| H4 | 100% | 46% | 97% | 43% |
| M30 | 100% | 32% | 100% | 32% |

H1 membentuk "dataran" parameter yang stabil. Tetap positif walaupun spread dinaikkan 2× (OOS
2018–22 +0,046R). Di H4/M30 parameter terbaik di pengembangan sering gagal di OOS, sehingga yang
dipakai adalah H1 dengan parameter tengah (55/20/3).

### 4.2 Validasi lewat Engine bot (kode yang sama dengan live), risiko 1% per trade

Termasuk batas rugi harian 3% / mingguan 6%, stop setelah 2 SL beruntun, blok rollover &
akhir pekan. Saldo awal 10.000.

| Periode | Trade | Win-rate | Profit factor | Hasil | Max drawdown | Tahun positif |
|---|---|---|---|---|---|---|
| 2012–2017 | 444 | 39,0% | 1,17 | **+53,0%** | −15,6% | 4 dari 6 |
| 2018–2022 (OOS) | 340 | 33,5% | 1,15 | **+27,6%** | −18,0% | 3 dari 5 |
| Apr 2025 – Sep 2026 (OOS) | 102 | 41,2% | 1,61 | **+28,7%** | −8,4% | 2 dari 2 |

PnL per tahun (riset, R): 2012 +1,3 · 2013 +29,6 · 2014 +14,6 · 2015 −9,3 · 2016 +15,2 ·
2017 +3,1 · 2018 −17,3 · 2019 +20,8 · 2020 +33,2 · 2021 −11,4 · 2022 (2 bln) +5,5 · 2025 +17,8 ·
2026 +17,1 → **10 dari 13 tahun positif**.

### 4.3 Yang harus diketahui (jujur)

- **Tidak ada strategi yang tidak pernah rugi.** Win-rate 33–41%: lebih banyak kalah kecil, profit
  datang dari sedikit trend besar. Ada tahun rugi (2015, 2018, 2021) dan drawdown hingga −18%
  dengan risiko 1%. Risiko 0,5% ≈ drawdown setengahnya.
- Rata-rata posisi dipegang ±2,5 hari → **swap** mengurangi hasil (belum dihitung). Gunakan akun
  swap-free bila tersedia.
- Jarak SL median 2025–26 ≈ **$50 per 0,01 lot**. Dengan risiko 1% butuh saldo ±$5.000 di akun
  USD standar. Saldo kecil → pakai akun **Cent**, jangan menaikkan risiko.
- Hasil masa lalu tidak menjamin masa depan. Jalankan di akun demo dulu.

## 6. Berita (NFP, CPI, PPI, FOMC, Retail Sales, PCE, GDP)

Kalender historis ForexFactory ([spoluan](https://github.com/spoluan/forex-factory-scraper) 2010–2023,
[ehsanrs2](https://github.com/ehsanrs2/forexfactory-scraper) 2020–Jan 2026) lengkap dengan *actual* &
*forecast*; 582 rilis dianalisis di candle M15 (`python -m research.news_study`).

| Periode | Rilis | Candle 15m pertama searah kejutan data | Berlanjut 1 jam | Berlanjut 4 jam | Arah 4 jam sebelum = arah reaksi |
|---|---|---|---|---|---|
| 2012–17 | 302 | 67,8% | 49,7% | 49,0% | 42,4% |
| 2018–22 | 232 | 62,3% | 48,7% | 53,4% | 50,0% |
| 2025–26 | 48 | 73,3% | 52,1% | 56,2% | 50,0% |

- Reaksi pertama mengikuti hasil data (actual vs forecast), tetapi hasilnya baru diketahui saat rilis;
  setelah candle rilis tertutup arah berikutnya ≈ 50/50, dan pergerakan sebelum berita tidak memberi
  petunjuk.
- Scalping berita (ikut / lawan / ikut kejutan, TP 1R/2R/2 jam, spread 0,60): **tidak ada** yang positif
  konsisten di 2012–17 dan 2018–22.
- Trade TREND H1 yang dibuka ≤ 1 jam dari berita justru lebih baik (+1,07R dan +0,58R vs +0,03R dan
  +0,06R) → berita memicu breakout yang ditangkap trend. Karena itu filter berita untuk mode trend
  **mati** (`trend.respect_news: false`).

## 7. Scalping (M5/M15) — TIDAK LOLOS

Scalping searah trend H1 (breakout 10/20 bar, SL 1–2 ATR, TP 1–2R, keluar paksa 16 bar), 18 varian
pra-daftar (`python -m research.scalp`): **0 dari 18** positif di semua periode; 2012–22 rata-rata
−0,11 s/d −0,36R. Biaya spread terlalu besar dibanding target scalping. Setup SMC/ICT
("Alchemist x ICT") di M5/M15 juga rugi (bagian 3).

## 8. Ujian "soal & kunci jawaban" (masa depan tertutup)

`python -m research.exam <dataset>` menjalankan bot mode SINYAL (kode yang sama yang mengirim ke
aplikasi Android) candle demi candle. Setiap sinyal = soal; saat bot mengirim sinyal TUTUP, jawaban
dibuka.

| Data | Soal | Benar | Nilai total | Rata-rata benar / salah |
|---|---|---|---|---|
| M15 2012–2022 (230 rb candle) | 786 | 287 (36,5%) | **+84,9R** | +1,72R / −0,82R |
| M15 2025–Sep 2026 | 106 | 43 (40,6%) | **+35,7R** | +2,03R / −0,82R |

Jumlah soal yang benar hanya 37–41%, tetapi karena jawaban benar rata-rata 2× lebih besar dari
jawaban salah, nilai totalnya positif. Contoh 8 soal terakhir (Agustus–September 2026): 2 benar, 6 salah
— periode rugi seperti ini normal dan akan terjadi lagi.

## 9. Cara mengulang

```bash
bash research/download_data.sh                                  # unduh data ke data/research
python -m research.next_candle
python -m research.run_scan m15_2012 data/research/scan_m15.pkl  # ±6 menit (4 core)
python -m research.smc_eval m15_2012 data/research/scan_m15.pkl 2018-01-01
python -m research.trend_grid
python -m research.engine_validate m15_2012 --to 2018-01-01
python -m research.engine_validate m15_2012 --from 2018-01-01
python -m research.engine_validate m5_2025
python -m research.news_study
python -m research.scalp
python -m research.exam m15_2012
python -m research.exam m5_2025
python -m research.run_scan m5_2025 data/research/scan_m5.pkl    # setup bot M5 untuk smc_models
python -m research.smc_models --m5                               # bagian 10 (±1 menit)
python -m research.trend_filters                                 # bagian 11
python -m research.engine_validate m5_2025 --risk 0.5 [--no-bias]
python -m research.cloud_check [--no-bias]
python -m research.winrate_study --json android/app/src/main/assets/strategies.json   # bagian 12
```

## 10. Perbandingan menyeluruh metode SMC/ICT populer — SEMUA TIDAK LOLOS

`python -m research.smc_models [--m5]` menguji **16 varian dasar model SMC/ICT** yang paling sering
dipakai (setup bot sendiri dengan 2 jenis target + 14 varian model buku teks), masing-masing tanpa filter,
dengan **bias struktur H1** (konsep SMC), dan **searah trend H1** (Donchian) → 46 varian di M15, ditambah
semuanya di M5 2025–26. Parameter tetap (aturan buku teks, tidak dioptimasi), aturan simulasi sama
untuk semua: entry setelah candle sinyal tertutup, spread dihitung, SL dicek dulu, satu posisi per model. **LOLOS** = rata-rata R > 0 di ketiga
periode dengan ≥ 30 trade.

Rata-rata R per trade (jumlah trade), M15, tanpa filter:

| Model | 2012–17 | 2018–22 (OOS) | 2025–26 (OOS) | Lolos |
|---|---|---|---|---|
| Setup bot: sweep → MSS → FVG/OB, TP likuiditas | −0,19R (998) | −0,25R (764) | −0,10R (883) | ❌ |
| Setup bot, TP 2R | −0,14R (927) | −0,28R (710) | −0,23R (656) | ❌ |
| Turtle Soup 20 (Raschke) | −0,32R (3690) | −0,33R (2723) | −0,08R (1014) | ❌ |
| Judas swing / Power of 3 (sweep range Asia di London) | −0,23R (920) | −0,18R (707) | −0,13R (208) | ❌ |
| Judas swing, TP sisi lain range Asia | −0,21R (920) | −0,18R (706) | −0,19R (208) | ❌ |
| Judas swing + MSS | −0,18R (613) | −0,09R (470) | −0,08R (136) | ❌ |
| Sweep PDH/PDL (high/low kemarin) | −0,11R (813) | −0,06R (657) | −0,21R (187) | ❌ |
| Sweep PDH/PDL + MSS | −0,13R (655) | −0,02R (521) | −0,01R (145) | ❌ |
| ICT Silver Bullet 10–11 NY | −0,09R (223) | −0,16R (157) | −0,07R (52) | ❌ |
| Silver Bullet 3 jendela (03, 10, 14 NY) | −0,08R (469) | −0,17R (387) | −0,11R (130) | ❌ |
| FVG dengan displacement | −0,22R (3541) | −0,17R (2728) | −0,08R (992) | ❌ |
| BOS + Order Block | −0,17R (2229) | −0,24R (1804) | +0,04R (592) | ❌ |
| OTE 70,5% setelah BOS | −0,32R (1995) | −0,28R (1502) | −0,08R (479) | ❌ |
| CISD setelah sweep | −0,13R (3185) | −0,09R (2641) | −0,07R (928) | ❌ |
| Breaker block | −0,31R (2106) | −0,24R (1654) | −0,13R (588) | ❌ |
| Unicorn (breaker + FVG) | −0,40R (552) | −0,32R (451) | −0,30R (185) | ❌ |

- **Filter bias H1 atau searah trend tidak menyelamatkan satu pun**: 0 dari 30 varian berfilter lolos.
  Yang tampak positif hanya di satu periode dengan trade sangat sedikit (mis. "Sweep PDH/PDL + MSS
  searah trend": +0,71R dari 14 trade di 2018–22 tetapi −0,32R di 2012–17) → kebetulan.
- M5 2025–26: 47 dari 48 varian rugi; Silver Bullet 10–11 NY ±0,00R (130 trade, impas). Satu periode
  saja tidak cukup, dan versi M15-nya rugi di 2012–22.
- Pembanding di H1 (periode sama): Donchian 55/20 +0,11R / +0,10R / +0,33R; ikut struktur BOS/CHoCH
  H1 +0,03R / +0,00R / +0,10R (hampir impas); Turtle Soup H1 −0,15R / −0,21R / −0,17R.

**Kesimpulan: yang paling baik tetap trend-following Donchian H1 (skema F-ensemble).** Konsep SMC tidak
menghasilkan edge sebagai *entry*. Yang diuji ulang sebagai *filter* trend ada di bagian 11.

## 11. Fitur SMC yang digabung ke trend: filter bias struktur H4 — dipakai (manfaat sedang)

Karena tidak ada *entry* SMC yang lolos, konsep SMC diuji ulang sebagai **filter** trend Donchian
(`python -m research.trend_filters`): breakout hanya diambil bila searah bias tertentu.

### 11.1 Di 76 varian parameter Donchian H1 (1 posisi)

| Filter | Varian positif di 3 periode | Varian yang R/trade-nya membaik (2012–17 / 2018–22 / 2025–26) |
|---|---|---|
| tanpa filter | 100% | – |
| killzone London + NY (02–05, 07–11 NY) | 95% | 45% / 55% / 76% |
| sesi London + NY penuh (02–12 NY) | 100% | 43% / 45% / 75% |
| tanpa sesi Asia | 99% | 74% / 63% / 58% |
| **bias struktur H4 (BOS terakhir, swing 3)** | **97%** | **67% / 71% / 84%** |
| bias struktur H4 (swing 5) | 91% | 100% / 67% / 87% |
| bias struktur H4 (swing 2) | 92% | 43% / 42% / 37% |
| bias struktur D1 | 58% | 57% / 5% / 100% |

### 11.2 Skema F-ensemble bot (R, drawdown kronologis)

| Filter | 2012–17 | 2018–22 (OOS) | 2025–26 (OOS) |
|---|---|---|---|
| tanpa filter | +34,0R · PF 1,16 · DD −13,8R | +31,8R · PF 1,19 · DD −13,9R | +24,0R · PF 1,48 · DD −8,5R |
| **bias struktur H4** | **+38,8R · PF 1,23** · DD −12,6R | **+33,3R · PF 1,25** · DD −15,4R | +22,5R · **PF 1,57** · DD −11,0R |
| killzone London + NY | +17,7R · PF 1,10 · DD −15,2R | +21,0R · PF 1,16 · DD −16,9R | +24,2R · PF 1,71 · DD −5,0R |

Killzone hanya bagus di 2025–26 dan merusak 2012–22 → **ditolak**. Bias H4 menaikkan kualitas per
trade di ketiga periode dengan ±18% trade lebih sedikit.

### 11.3 Validasi lewat Engine bot (kode live, risiko per set, batas rugi harian/mingguan aktif)

| Periode | Risiko 0,5%/set (default) — dengan filter | tanpa filter | Risiko 1%/set — dengan filter | tanpa filter |
|---|---|---|---|---|
| 2012–2017 | **+36,6%** · PF 1,15 · DD −14,1% | +28,6% · PF 1,09 · DD −13,9% | **+96,8%** · PF 1,15 · DD −28,6% | +66,0% · PF 1,08 · DD −29,8% |
| 2018–2022 (OOS) | **+29,5%** · PF 1,18 · DD −17,2% | +16,3% · PF 1,08 · DD −16,4% | **+81,1%** · PF 1,22 · DD −29,1% | +66,9% · PF 1,13 · DD −29,5% |
| Apr 2025 – Sep 2026 (OOS) | +34,7% · PF 1,73 · DD −13,7% | **+41,0%** · PF 1,67 · DD −9,9% | **+50,4%** · PF 1,45 · DD −23,4% | +47,0% · PF 1,30 · DD −19,8% |

Versi cloud (`python -m research.cloud_check`, 2025–26, tick 30 menit, termasuk blok akhir pekan/rollover):
dengan filter 281 sinyal, +53,3R (rata-rata +0,190R); tanpa filter 344 sinyal, +61,6R (+0,179R).

**Keputusan:** filter bias struktur H4 **aktif secara default** (bot PC & cloud) karena profit factor lebih
tinggi di 6 dari 6 run engine dan hasil lebih besar di 5 dari 6. Yang jujur perlu diketahui:
- **Drawdown tidak menjadi lebih kecil** (2012–22 hampir sama, 2025–26 lebih dalam ±4%): sinyal dari
  3 set cenderung masuk bersamaan saat bias berbalik.
- Di 2025–26 total hasil tanpa filter justru lebih besar (engine 0,5% & cloud). Manfaatnya sedang,
  bukan jaminan.
- Bisa dimatikan: `trend.bias_filter: false` di `config.yaml`, atau switch **Filter bias struktur H4**
  di tab Auto aplikasi (versi cloud).

## 12. Win rate vs profit: TP kecil, break-even, tutup sebagian + scalping — TIDAK ADA YANG LOLOS

`python -m research.winrate_study [--m5]` menguji **20 model** (14 SMC/ICT dari bagian 10 + 6 scalping
populer: breakout searah trend H1, EMA 9/21 + EMA200, RSI(2) Connors, Bollinger reversal, ORB London,
ORB New York), masing-masing tanpa filter dan searah trend H1, dengan **9 skema keluar**: TP bawaan,
TP 0,5R / 1R / 1,5R / 2R / 3R, BE di 0,5R + TP 1R, 50% di 0,5R + BE sisa 1,5R, 50% di 1R + BE sisa 3R.
Total **351 kombinasi × 3 periode**. Skema terbaik tiap model dipilih **hanya** dari 2012–17 lalu dinilai
apa adanya di 2018–22 dan 2025–26.

**Hasil: 0 dari 351 kombinasi untung di ketiga periode.** Rata-rata semua model per skema (M15):

| Skema keluar | Win rate | R per trade | Win rate minimal agar impas* |
|---|---|---|---|
| TP 0,5R | **51,7%** | −0,21R | 66,7% |
| 50% di 0,5R + BE, sisa 1,5R | 52,2% | −0,17R | – |
| BE di 0,5R + TP 1R | 48,9% | −0,17R | – |
| TP 1R | 41,4% | −0,17R | 50,0% |
| TP 1,5R | 35,7% | −0,15R | 40,0% |
| TP 2R | 32,5% | −0,12R | 33,3% |
| TP 3R | 28,4% | −0,11R | 25,0% |

\* sebelum spread. TP kecil memang menaikkan win rate, tetapi kerugian per kalah tetap 1R, sehingga
win rate yang dibutuhkan untuk impas naik lebih cepat daripada win rate yang didapat.

Contoh yang sering ditanyakan:

| Model (M15) | Skema | 2012–17 | 2018–22 | 2025–26 |
|---|---|---|---|---|
| ICT Silver Bullet 10–11 NY | TP 1R (terbaik) | win 46,5% · −0,03R | win 40,8% · −0,21R | win 47,6% · −0,07R |
| ICT Silver Bullet 10–11 NY | BE 0,5R + TP 1R (win tertinggi) | win 55,4% · −0,03R | win 44,4% · −0,23R | win 57,1% · −0,08R |
| CISD setelah sweep, searah trend | TP 0,5R | win 56,1% · −0,14R | win 57,7% · −0,13R | win 63,4% · −0,04R |
| Scalping RSI(2), searah trend | TP 0,5R | win 58,1% · −0,11R | win 60,4% · −0,08R | win 67,3% · +0,02R |
| Scalping RSI(2), searah trend | TP 1,5R (terbaik) | win 40,1% · −0,08R | win 40,6% · −0,06R | win 46,8% · +0,06R |
| Setup SMC bot | TP 2R (terbaik) | win 29,1% · −0,14R | win 24,2% · −0,28R | win 25,8% · −0,23R |
| **Trend F-ensemble H1 + bias H4 (bot)** | skema F | win 46,9% · **+0,10R** | win 46,1% · **+0,11R** | win 49,3% · **+0,24R** |

- Beberapa scalping (RSI(2), EMA cross, breakout) positif **hanya di 2025–26** (emas naik kuat) dan rugi
  di 2012–22 → tidak bisa diandalkan. Di M5 2025–26 saja 30 dari 351 kombinasi positif; satu periode
  tidak cukup (bagian 7 & 10).
- Kombinasi "win rate tinggi + profit" tidak bertahan: win rate tertinggi dengan trade memadai (≥ 30) ada
  di ±56–67% dengan TP 0,5R, paling bagus pas di batas impas 66,7% (RSI(2) searah trend 2025–26: 67,3% →
  +0,02R) dan rugi di 2012–22. Angka lebih tinggi (mis. 78,6%) hanya dari ≤ 16 trade dan rugi di periode lain.
- Hasil lengkap per model (skema terbaik & skema win rate tertinggi) tampil di tab **Riset** aplikasi
  Android (`android/app/src/main/assets/strategies.json`, dibuat oleh skrip ini).
