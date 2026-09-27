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

Kesimpulan: aturan SMC yang diotomasi **rugi** secara konsisten setelah biaya. Mode `smc`
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
```

## 10. Periode baru 2022–2025 (data yang belum pernah dipakai)

Dataset ke-4: [ilahuerta-IA/backtrader-pullback-window-xauusd](https://github.com/ilahuerta-IA/backtrader-pullback-window-xauusd)
M5 Agu 2020 – Agu 2025 (UTC, selisih median $0,22 dengan dataset lain), dipakai untuk Apr 2022 – Apr 2025 yang
sebelumnya kosong. Engine bot (`python -m research.engine_ab`), saldo $10.000:

| Setelan | 2012–17 | 2018–22 | **2022–25** | 2025–26 |
|---|---|---|---|---|
| F-ensemble 0,5%/set (default) | +28,6% / DD −13,9% | +16,3% / −16,4% | **−14,9% / −28,9%** | +41,0% / −9,9% |
| A-ensemble 0,25%/set (usulan) | +24,0% / −12,4% | +24,9% / −11,0% | **+3,7% / −14,4%** | (sinyal dilewati: lot min.) |

- Uji ketahanan 76 varian Donchian H1: 91% positif di 2022–25 dan 89% positif di keempat periode, tetapi rata-rata
  hanya +0,04R per trade di 2022–25 (pasar lebih "berombak").
- Skema F (TP1 + SL+) memotong trend yang berlanjut; di 2022–25 hasilnya −6,2R vs +9,8R untuk skema A (uji sinyal).
- Rincian, uji repo GitHub populer, kebijakan risiko & rencana aplikasi: [`RISET_GITHUB.md`](RISET_GITHUB.md).

```bash
python -m research.engine_ab m5_2020 F --from 2022-04-01 --to 2025-04-07 --risk 0.5
python -m research.engine_ab m5_2020 A --from 2022-04-01 --to 2025-04-07 --risk 0.25
python -m research.combine
```

## 11. Metode & risiko per sinyal — simulasi saldo (`python -m research.risk_compare`)

Saldo majemuk, posisi 3 set boleh terbuka bersamaan, spread dihitung, swap belum, **tanpa** pengaman
rugi harian/mingguan (jadi DD lebih dalam daripada engine bot). Format: hasil / DD terdalam.

| Metode (risiko per sinyal) | 2012–17 | 2018–22 | 2025–26 |
|---|---|---|---|
| A-ensemble 5 runner, 0,5% | +59,6% / −25,7% | +56,6% / −20,4% | +47,0% / −9,6% |
| F-ensemble semua sama, 0,5% | +36,2% / −23,5% | +59,2% / −15,8% | +37,1% / −10,1% |
| F-ensemble ⭐ saja, 0,5% | +56,0% / −17,5% | +46,2% / −13,7% | +26,6% / −8,9% |
| **F-ensemble ⭐ 0,5% + biasa 0,25%** | **+54,0% / −21,7%** | **+66,1% / −11,3%** | **+35,3% / −6,0%** |
| F-ensemble ⭐ 1% + biasa 0,5% | +111,2% / −39,7% | +144,2% / −21,8% | +76,4% / −11,6% |
| F-ensemble ⭐ 1,5% + biasa 0,75% | +162,0% / −54,4% | +224,9% / −31,5% | +122,7% / −17,0% |

Rasio hasil/DD terbaik di 2 dari 3 periode: **⭐ penuh + biasa setengah**. Risiko 1,5% membuat DD 2012–17
lebih dari −50% → terlalu besar. Tabel lot di aplikasi (Syarat & Ketentuan) memakai ⭐ 0,5% / biasa 0,25%.
