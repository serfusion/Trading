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

## 5. Cara mengulang

```bash
bash research/download_data.sh                                  # unduh data ke data/research
python -m research.next_candle
python -m research.run_scan m15_2012 data/research/scan_m15.pkl  # ±6 menit (4 core)
python -m research.smc_eval m15_2012 data/research/scan_m15.pkl 2018-01-01
python -m research.trend_grid
python -m research.engine_validate m15_2012 --to 2018-01-01
python -m research.engine_validate m15_2012 --from 2018-01-01
python -m research.engine_validate m5_2025
```
