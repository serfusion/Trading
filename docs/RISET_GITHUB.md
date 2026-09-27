# Riset: Repo GitHub XAUUSD Terpopuler, Seleksi "Terbaik dari yang Terbaik", dan Rencana Aplikasi untuk Dhuafa

*Snapshot GitHub 26 September 2026. Semua angka dihasilkan ulang dari data harga asli dengan kode di folder
`research/` (perintah di bagian 9).*

## 0. Ringkasan jujur

1. **Tidak ada yang bisa "menggerakkan pasar" emas** (volume harian puluhan–ratusan miliar dolar), dan mencoba
   memanipulasi pasar itu ilegal. Yang bisa kita kendalikan hanya: aturan masuk/keluar, besar risiko, dan disiplin.
2. **11 repo emas paling populer** di GitHub dikaji; 6 strategi dapat ditulis ulang dan diuji di **±630 ribu candle
   asli 2012–2026** (4 periode + data M1), termasuk periode **2022–2025 yang belum pernah dipakai** sebelumnya.
3. **Klaim win-rate 55–68% dan profit factor 1,6–2,8 dari repo-repo itu tidak terbukti.** Opening Range Breakout,
   FVG/Order Block, MACD scalper, EMA/RSI multi-filter, dan machine learning semuanya rugi atau tidak konsisten
   setelah spread, tanpa *look-ahead*.
4. **Satu-satunya yang lolos di 4 dari 4 periode: trend-following Donchian H1 dua arah**, dengan win-rate hanya
   **33–39%** (untung dari sedikit trend besar). 89% dari 76 variasi parameternya positif di keempat periode.
5. **Temuan penting untuk bot ini:** lewat engine bot sendiri (kode yang sama dengan live), setelan default sekarang
   (skema F = TP1 1R + SL+, risiko 0,5%/set) **rugi −14,9% dengan drawdown −28,9% di periode baru 2022–25**.
   Skema A (tanpa TP1, hold sampai sinyal TUTUP) pada **0,25%/set** menghasilkan +61% vs +27% (2012–2025) dengan
   drawdown lebih kecil di ketiga periode → itulah rekomendasi (bagian 5). Kode live belum diubah.
   Catatan jujur: selama 2012–2026, **sekadar membeli emas tanpa leverage (+178%) mengalahkan semua setelan bot**;
   kelebihan bot hanya bisa untung saat emas turun (2012–17: bot +20–29%, emas −16%).
6. **Win-rate tinggi bisa "dibeli", tetapi mahal:** sinyal yang sama dengan TP 0,25R → win-rate 77%, tapi rugi;
   EA grid/martingale → 97–99% basket profit, tapi akun $1.000 habis 44 kali dalam 14 tahun (umur median 11 hari).
7. **Kebijakan uang terbaik:** risiko tetap **0,25–0,5% per set**, tanpa martingale/grid. Risiko 2% per trade →
   peluang drawdown >50% sebesar 98%; martingale → bangkrut di 100% simulasi.
8. **Untuk pengemis, orang miskin, dan dhuafa, trading berleverage adalah alat yang salah.** Menabung emas rutin
   $10/bulan (Mei 2012–Sep 2026) → setor $1.730 menjadi **$4.427 (+156%)** tanpa kemungkinan akun "habis".
   Aplikasi yang tepat: **Tabungan Emas + Dompet Berbagi (sedekah dari profit bersih) + Kalkulator Zakat**, dengan
   trading hanya untuk yang modalnya cukup. Modul hitungnya sudah dibuat: `python -m xau_bot berbagi|zakat|tabungan`.

---

## 1. Repo yang dikaji

### 1.1 Repo khusus emas (diurutkan menurut bintang)

| Repo | ★ / fork | Isi & klaim penulis | Hasil uji ulang kita | Status |
|---|---|---|---|---|
| [yulz008/GOLD_ORB](https://github.com/yulz008/GOLD_ORB) | 297 / 101 | Opening Range Breakout H1 (MQL5), SL $4 / TP $12 + trailing | −0,04 s/d −0,11R per trade di 2012–25; 2025–26 ≈ impas (+0,01R) | ❌ Gagal |
| [francomascareloai/EA_SCALPER_XAUUSD](https://github.com/francomascareloai/EA_SCALPER_XAUUSD) | 244 / 64 | Riset terbuka, **tanpa klaim profit**. Menganalisis 5.000+ bot: "kebanyakan martingale/grid daur ulang" | Tidak ada aturan publik untuk diuji; temuannya **sejalan** dengan uji grid kita (bagian 6.3) | ℹ️ Pelajaran |
| [zero-was-here/tradingbot](https://github.com/zero-was-here/tradingbot) | 200 / 73 | Deep RL (PPO/Dreamer), "target 80–120%/tahun, Sharpe 3,5–4,5" | Itu **target**, bukan hasil. Model terlatih tidak disertakan; uji ML walk-forward kita (bagian 3) tidak konsisten | ⚠️ Tak terbukti |
| [3aLaee/xauusd-trading-bot](https://github.com/3aLaee/xauusd-trading-bot) | 175 / 45 | MACD M1 + S/R 10 bar, **SL $1,50 > TP $1,00** | M1 Feb–Mei 2026, spread 0,25: −0,39R/trade; bahkan dengan asumsi paling optimistis −0,08R | ❌ Gagal |
| [triqbit/mt5-ai-xauusd-trader](https://github.com/triqbit/mt5-ai-xauusd-trader) | 148 / 45 | Gabungan "25+ repo" ML/DRL; tabel kinerja berjudul **"Target Value"** (60–90%/th, Sharpe 2,8–3,5); 561 issue terbuka | Target, bukan hasil. Diwakili uji ML walk-forward (bagian 3) | ⚠️ Tak terbukti |
| [mehdi-jahani/GoldTraderEA](https://github.com/mehdi-jahani/GoldTraderEA) | 145 / 51 | 14 teknik (Elliott, harmonic, Wolfe, dll.), klaim +287%, WR 68% (2020–23) | Grafik ekuitas di README adalah **gambar placeholder** (via.placeholder.com); tidak ada bukti. Pola subjektif tidak bisa diuji apa adanya | ⚠️ Tanpa bukti |
| [codebytemirza/XAUUSD_TRADING_ASISTENT_AI](https://github.com/codebytemirza/XAUUSD_TRADING_ASISTENT_AI) | 139 / 38 | Asisten LLM (DeepSeek + LangChain), klaim "65% akurasi di akun real" | Tanpa data/riwayat yang bisa diperiksa; jawaban LLM tidak bisa diulang persis | ⚠️ Tak terbukti |
| [GifariKemal/xaubot-ai](https://github.com/GifariKemal/xaubot-ai) | 83 / 34 | XGBoost + SMC + HMM, klaim WR 63,9%, PF 2,64, Sharpe 4,83 (Jan 2025–Feb 2026) | ML walk-forward kita: akurasi arah **51,3%**; SMC yang diotomasi rugi di ±350 rb candle (docs/BACKTEST.md) | ❌ Tak terbukti |
| [ilahuerta-IA/backtrader-pullback-window-xauusd](https://github.com/ilahuerta-IA/backtrader-pullback-window-xauusd) | 75 / 28 | Pullback + breakout M5 (LONG), klaim WR 55%, PF 1,64 (2020–25) | 2022–25 (data optimasi penulis sendiri): +0,40R, 28 trade. Setelah data penulis (2025–26): −0,51R, 5 trade | ⚠️ Belum lolos OOS |
| [foeed/FvgGold-EA](https://github.com/foeed/FvgGold-EA) | 36 / 8 | FVG + OB M15, RR 1,5, klaim +48,7% dalam 6 bulan (64 trade, lot 0,01, saldo $10.000) | −0,20 s/d −0,35R per trade di **keempat** periode. Klaimnya tidak konsisten secara matematis (butuh SL ±$570 per trade) | ❌ Gagal |
| [a1shmuk/xauusd-algo-trader](https://github.com/a1shmuk/xauusd-algo-trader) | 10 / 1 | EMA 9/21 + RSI + EMA50 H4 + sesi + SL swing, klaim WR 61,4%, PF 2,48 (44 trade, **4.374 kombinasi** dioptimasi) | Backtest penulis memakai **data masa depan** (swing butuh 5 bar ke kanan, close H4 yang belum terjadi, TP dicek sebelum SL). Tanpa itu: WR 31–36%, 2 dari 4 periode rugi | ❌ Overfit |

### 1.2 Framework umum paling populer (alat, bukan strategi siap untung)

| Repo | ★ | Yang diambil untuk proyek ini |
|---|---|---|
| [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents) | 108.770 | Ide "tim analis" LLM. Tidak bisa diuji per candle 14 tahun tanpa biaya API besar & hasil yang bisa diulang, jadi **tidak dipakai untuk eksekusi**. |
| [freqtrade/freqtrade](https://github.com/freqtrade/freqtrade) | 54.820 | Pola bot: dry-run dulu, perlindungan (stoploss wajib, *max drawdown protection*), kontrol lewat Telegram — sudah ada di bot ini. |
| [microsoft/qlib](https://github.com/microsoft/qlib), [stefan-jansen/machine-learning-for-trading](https://github.com/stefan-jansen/machine-learning-for-trading) | 48.876 / 21.055 | Walk-forward: model hanya dilatih dengan data sebelum periode uji → dipakai di uji ML kita. |
| [vnpy/vnpy](https://github.com/vnpy/vnpy), [nautechsystems/nautilus_trader](https://github.com/nautechsystems/nautilus_trader), [QuantConnect/Lean](https://github.com/QuantConnect/Lean), [mementum/backtrader](https://github.com/mementum/backtrader) | 45.564 / 29.426 / 21.791 / 23.330 | Engine event-driven: backtest memakai kode yang sama dengan live → sudah diterapkan (`xau_bot/backtest.py`, `research/engine_validate.py`). |
| [AI4Finance-Foundation/FinRL](https://github.com/AI4Finance-Foundation/FinRL) | 16.407 | Deep RL; untuk emas diwakili repo zero-was-here (klaim berupa target). |
| [polakowo/vectorbt](https://github.com/polakowo/vectorbt), [kernc/backtesting.py](https://github.com/kernc/backtesting.py) | 9.194 / 9.000 | Uji banyak parameter sekaligus → dipakai sebagai *robustness grid* (76 varian), bukan untuk memilih yang terbaik saja. |

**Pelajaran umum:** bintang GitHub mengukur popularitas, bukan profit. Semua repo dengan angka "win-rate 60%+ /
Sharpe 4+" yang kami periksa ternyata (a) hanya target, (b) diuji di data yang juga dipakai untuk optimasi,
(c) mengandung *look-ahead*, atau (d) tanpa bukti.

---

## 2. Metode uji

| Periode | Data | Candle | Sumber |
|---|---|---|---|
| 2012-05 → 2017-12 | M15 | 132 rb | ejtraderLabs/historical-data |
| 2018-01 → 2022-03 | M15 | 98 rb | ejtraderLabs/historical-data |
| **2022-04 → 2025-04 (baru)** | M5 | 214 rb | ilahuerta-IA/backtrader-pullback-window-xauusd (UTC; dicek selisih median $0,22 terhadap sumber lain) |
| 2025-04 → 2026-09 | M5 | 101 rb | dineshelumalai007/xauusd-5m |
| Feb → Mei 2026 | M1 | 87 rb | Sai310421/xauusd-data (khusus scalper M1) |

Aturan yang sama untuk semua strategi (`research/harness.py`): spread dihitung (0,30 untuk 2012–22, 0,25 sesudahnya),
entry di open candle berikutnya setelah sinyal, SL dicek lebih dulu bila SL & TP tersentuh di candle yang sama, TP
tidak dihitung di candle entry, indikator timeframe besar hanya dari candle yang sudah tutup, tidak ada parameter
yang diubah setelah melihat hasil. Hasil dalam **R** (kelipatan risiko awal) supaya strategi berbeda bisa dibandingkan.
Swap & komisi belum dihitung.

## 3. Hasil per strategi (rata-rata R per trade | total R)

| Strategi | 2012–17 | 2018–22 | 2022–25 (baru) | 2025–26 | Positif |
|---|---|---|---|---|---|
| GOLD_ORB asli | −0,042 \| −65 | −0,096 \| −108 | −0,111 \| −101 | +0,012 \| +5 | 1/4 |
| GOLD_ORB diskalakan harga | −0,070 \| −118 | −0,156 \| −192 | −0,073 \| −66 | +0,007 \| +3 | 1/4 |
| a1shmuk seperti diterbitkan (look-ahead) | +0,059 \| +47 | −0,070 \| −45 | +0,021 \| +10 | +0,069 \| +14 | 3/4 |
| a1shmuk tanpa look-ahead | +0,033 \| +27 | −0,098 \| −62 | −0,057 \| −29 | +0,057 \| +12 | 2/4 |
| Pullback window (M5) | – | – | +0,397 \| +11 (28 trade, in-sample) | −0,511 \| −3 (5 trade) | – |
| FVG RR 1,5 killzone | −0,280 \| −451 | −0,233 \| −293 | −0,197 \| −161 | −0,346 \| −84 | 0/4 |
| MACD scalper M5 | – | – | −0,245 \| −3.615 | −0,512 \| −3.996 | 0/2 |
| ML gradient boosting (walk-forward) | −0,029 \| −42 | −0,065 \| −155 | +0,019 \| +33 | +0,048 \| +40 | 2/4 |
| **Donchian H1 A-ensemble (hold sampai exit)** | **+0,029 \| +39** | **+0,032 \| +33** | **+0,013 \| +10** | **+0,084 \| +28** | **4/4** |
| Donchian H1 F-ensemble (bot sekarang) | +0,017 \| +24 | +0,030 \| +33 | −0,007 \| −6 | +0,071 \| +25 | 3/4 |
| *Beli & tahan emas (tanpa leverage)* | *−16%* | *+50%* | *+55%* | *+44%* | *3/4* |

MACD scalper M1 asli (Feb–Mei 2026, 6.984 trade): spread 0 → −0,29R; spread 0,25 → −0,39R. Dengan asumsi paling
optimistis (TP selalu tersentuh lebih dulu): spread 0 → +0,04R, spread 0,25 → **−0,08R**. Target $1 terlalu kecil
dibanding biaya spread.

## 4. Sortir & seleksi per klasifikasi

| Klasifikasi | Juara | Angka | Catatan |
|---|---|---|---|
| Win-rate tertinggi (absolut) | EA grid/martingale | 97–99% basket profit | Akun habis 5–465 kali dalam 14 tahun → **ditolak** |
| Win-rate tertinggi yang masih untung | F-ensemble (bot sekarang) | 42–49% | Rugi di 2022–25; total 4 periode kalah dari A |
| Profit total tertinggi (4 periode) | A-ensemble + filter ML | +122,7R | Butuh model ML dilatih tiap kuartal; kandidat, bukan default |
| Paling sederhana & konsisten | **A-ensemble** | +109,3R, positif 4/4 | 89% dari 76 varian parameter positif di 4/4 periode |
| Drawdown terkecil | A-ensemble + filter ML / SMA200 | DD terburuk −15R / −19,8R | Filter SMA200: rata-rata R per trade naik di 3 dari 4 periode |
| Kebijakan risiko | Risiko tetap 0,25–0,5% per set | lihat 6.2 | Tanpa martingale, tanpa grid, batas rugi harian/mingguan |
| Modal kecil / dhuafa | Tabungan emas rutin tanpa leverage | +156% (2012–2026) | Bisa turun (−22% untuk 2012–16), tapi tidak bisa "habis" |

Gabungan yang diuji (`research/combine.py`, parameter sama, filter pra-didaftarkan):

| Gabungan | 2012–17 | 2018–22 | 2022–25 | 2025–26 | Total | DD terburuk |
|---|---|---|---|---|---|---|
| F-ensemble (bot sekarang) | +24,3R | +32,6R | **−6,2R** | +24,5R | +75,2R | −26,4R |
| **A-ensemble** | +39,0R | +32,8R | +9,8R | +27,7R | **+109,3R** | −25,0R |
| A + filter SMA200 harian | +22,3R | +35,1R | +17,3R | +26,5R | +101,2R | −19,8R |
| A + filter searah ML | +40,7R | +33,0R | +18,7R | +30,3R | +122,7R | −15,0R |

(R = total risiko satu sinyal untuk ketiga set; DD dihitung kronologis.)

## 5. Keputusan: resep "terbaik dari yang terbaik"

### 5.1 Uji lewat engine bot (kode yang sama dengan live), saldo awal $10.000

Termasuk semua pengaman bot (batas rugi harian 3% / mingguan 6%, stop setelah 2 SL beruntun, blok rollover &
akhir pekan, pembulatan lot 0,01). Skema A dijalankan di backtest tanpa mengubah kode: `tp1_r` dibuat sangat besar
sehingga TP1/SL+ tidak pernah aktif (`python -m research.engine_ab <dataset> A`; hanya untuk PaperBroker).

| Periode | F 0,5%/set (default) | A 0,5%/set | F 0,25%/set | **A 0,25%/set** | Emas fisik |
|---|---|---|---|---|---|
| 2012–17 | +28,6% (DD −13,9%) | +25,4% (DD −23,1%) | +19,5% (DD −7,5%) | **+24,0% (DD −12,4%)** | −16% |
| 2018–22 | +16,3% (DD −16,4%) | +14,7% (DD −20,2%) | +24,7% (DD −6,7%) | **+24,9% (DD −11,0%)** | +50% |
| 2022–25 (baru) | **−14,9% (DD −28,9%)** | +1,3% (DD −33,2%) | −0,8% (DD −13,2%) | **+3,7% (DD −14,4%)** | +55% |
| 2025–26 | +41,0% (DD −9,9%) | +47,8% (DD −13,0%) | +0,3%\* | −0,3%\* | +44% |
| Gabungan 2012–2025 | +27% | +46% | +48% | **+61%** | +93% |

\* Pada 0,25% dengan saldo $10.000 hampir semua sinyal 2025–26 **dilewati**: SL ±$50 per 0,01 lot > 0,25% saldo
($25), dan bot menolak lot minimum yang melebihi risiko (`allow_min_lot_over_risk: false`). Butuh saldo ±$20.000
di akun standar atau akun Cent.

Pengamatan:
- Skema F selalu punya drawdown lebih kecil dan win-rate lebih tinggi (±43–49% vs ±33–39%), tetapi rugi di 2022–25.
- Skema A menang di 5 dari 7 perbandingan hasil, tetapi drawdown-nya lebih dalam pada risiko yang sama.
- **A 0,25%/set vs default sekarang (F 0,5%/set):** hasil lebih tinggi di 2 dari 3 periode, gabungan +61% vs +27%,
  dan drawdown lebih kecil di ketiga periode (−12/−11/−14% vs −14/−16/−29%).
- Semua setelan kalah dari emas fisik selama 2012–2026. Trading ini hanya masuk akal sebagai *pelengkap* yang bisa
  untung saat emas turun, bukan jalan cepat kaya.

### 5.2 Resep

1. **Mesin:** Donchian H1 tiga set (40/15, 55/20, 80/30), BUY & SELL, SL awal 3×ATR(20), **tanpa TP**, keluar saat
   close H1 menembus channel exit (skema A). Satu-satunya keluarga strategi yang positif di keempat periode pada uji
   sinyal; tidak bergantung pada tebakan arah candle berikutnya (yang terbukti ≈ lempar koin).
2. **Risiko: 0,25% per set** (maksimal 0,5% bila siap menanggung drawdown ±30%). Batas rugi harian 3%, mingguan 6%,
   stop setelah 2 SL beruntun (sudah ada). **Tidak pernah** martingale, grid, atau menambah lot setelah rugi.
3. **Modal:** di volatilitas 2025–26 butuh ±$20.000 (akun standar) atau ±$200 (akun Cent) agar 0,25%/set bisa
   dijalankan dengan lot 0,01; di bawah itu bot akan (benar) melewati sinyal.
4. **Filter (opsional, kandidat):** SMA200 harian atau ML searah memperbaiki hasil di uji sinyal (bagian 4), tetapi
   dipilih setelah melihat 3 kandidat → **wajib diuji di akun demo ±3 bulan** sebelum dipakai.
5. **Ekspektasi jujur:** win-rate 33–40%, ada tahun rugi (2015, 2018, 2022), drawdown ±11–15% pada 0,25%/set.
6. **Perubahan bot yang disarankan (menunggu persetujuan):** opsi resmi `tp1_r: 0` = skema A di bot PC & cloud, lalu
   default `risk_pct_per_set: 0.25`. **Jangan** meniru trik `tp1_r` besar dari backtest di akun demo/real: untuk SELL
   harga TP-nya bisa negatif dan ditolak broker.

## 6. Kebijakan uang & risiko

### 6.1 Ilusi win-rate (sinyal Donchian 55/20 yang sama, hanya TP diubah, 4 periode)

| TP | Win-rate | Rata-rata | Total |
|---|---|---|---|
| 0,25R | **77,3%** | −0,027R | −112,8R |
| 0,5R | 65,0% | −0,006R | −17,5R |
| 1R | 48,0% | +0,021R | +46,2R |
| 2R | 37,5% | +0,060R | +94,6R |
| Tanpa TP (channel exit) | 36,3% | **+0,114R** | **+131,6R** |

Makin tinggi win-rate, makin kecil profit. Mengejar win-rate tinggi = memotong profit dan membiarkan rugi.

### 6.2 Besar risiko (3.486 trade A-ensemble, Mei 2012–Sep 2026, simulasi acak 3.000×)

| Kebijakan | Urutan asli: hasil, DD maks | CAGR median | P(DD > 30%) | P(DD > 50%) | P(bangkrut) |
|---|---|---|---|---|---|
| Tetap 0,25% per set | 2,19×, −21% | +5,6%/th | 0,2% | 0% | 0% |
| **Tetap 0,5% per set** (default config) | 4,45×, −38% | +11,0%/th | 19,6% | 0,3% | 0% |
| Tetap 1% | 14,9×, −63% | +20,8%/th | 95,7% | 25,7% | 0% |
| Tetap 2% | 77,9×, −87% | +35,5%/th | 100% | 98,0% | 2,3% |
| Tetap 5% | **bangkrut** | +1,4%/th | 100% | 100% | 48,8% |
| Martingale (×2 setelah rugi) | **bangkrut** | −90%/th | 100% | 100% | 100% |

Kelly penuh = 5,3% per trade, tetapi di atas ±1% drawdown sudah tidak tertahankan secara psikologis dan finansial.

### 6.3 EA grid/martingale (pola yang paling banyak dijual), akun $1.000, leverage 1:500

| Jarak & lot | Basket profit | Akun habis | Umur median akun | Setor total → saldo akhir |
|---|---|---|---|---|
| 0,25%, lot ×1,5, 12 level | 98,7% | 44× | 11 hari | $45.000 → $3.226 |
| 0,25%, lot ×2, 10 level | 96,9% | 465× | 5 hari | $466.000 → $6.221 |
| 0,25%, lot tetap, 20 level | 98,9% | 47× | 7 hari | $48.000 → $3.228 |
| 1%, lot ×1,3, 10 level | 99,0% | 5× | 320 hari | $6.000 → $16.630 |

Varian paling "sabar" masih habis 5 kali (2020, 2024, 2025 — tahun trend kuat). Terlihat untung hanya bila selalu
bisa menyetor lagi setelah akun habis — **tepat hal yang tidak dimiliki orang miskin.**

## 7. Untuk pengemis, orang miskin & dhuafa

### 7.1 Kenapa bukan aplikasi trading

- Modal minimum: dengan SL 3×ATR H1 dan lot 0,01, risiko 0,5% per set butuh ±$10.000 di akun standar (2025–26,
  SL median $50 per 0,01 lot) atau ±$100 di akun Cent. Modal lebih kecil memaksa risiko per trade puluhan persen →
  pola "akun habis" di bagian 6.
- Broker CFD di Eropa wajib mencantumkan persentase akun ritel yang rugi; angkanya umumnya 70–80%-an.
- Di Indonesia, banyak kasus "robot trading" ilegal 2021–2022 yang merugikan orang kecil. Selalu cek legalitas
  broker dan produk di OJK dan Bappebti sebelum menyetor.
- Dari sisi syariah, fatwa DSN-MUI No. 28/DSN-MUI/III/2002 membolehkan jual-beli mata uang secara tunai (spot) dan
  melarang forward/swap/option; transaksi berleverage dan swap bunga dipersoalkan banyak ulama. Tanyakan ke ulama/
  dewan syariah; bila tetap trading, gunakan akun bebas swap.

### 7.2 Yang lebih membantu: tabungan emas rutin (`research/dca.py`)

| Skenario | Setor | Nilai akhir | Hasil |
|---|---|---|---|
| $10/bulan Mei 2012 – Sep 2026, selisih beli-jual 5% | $1.730 | $4.427 (31,9 gram) | **+156%** |
| Sama, selisih 2% | $1.730 | $4.567 | +164% |
| Menabung 5 tahun terburuk (2012–2016) | $600 | $470 | −22% |
| Menabung 5 tahun terbaik (2021–2025) | $600 | $1.165 | +94% |

Dalam Rupiah hasilnya lebih besar lagi karena Rupiah melemah (±Rp9.400/USD di 2012 → ±Rp16.000-an di 2025).
Emas bisa turun bertahun-tahun, tetapi tabungan tidak bisa "habis" seperti akun berleverage.

### 7.3 Rencana aplikasi "Emas Berkah"

| Modul | Untuk siapa | Fungsi | Status |
|---|---|---|---|
| **Tabungan Emas** | Dhuafa, pekerja harian | Rencana setoran (mis. Rp10.000/hari), simulasi skenario harga, pengingat, edukasi selisih beli-jual; beli di lembaga resmi pilihan pengguna | ✅ Kalkulator: `python -m xau_bot tabungan` |
| **Dompet Berbagi** | Trader yang sudah untung | Sisihkan X% dari profit bersih **baru** (high-water mark: rugi harus tertutup dulu), laporan bulanan transparan, salurkan lewat BAZNAS/LAZ resmi | ✅ `python -m xau_bot berbagi` (CSV atau riwayat MT5) |
| **Kalkulator Zakat** | Semua | Zakat mal 2,5% bila harta bersih ≥ nisab 85 gram emas & haul | ✅ `python -m xau_bot zakat` |
| **Pelindung** | Semua | Mode demo wajib 3 bulan, tolak auto-trade bila modal < minimum atau risiko > 1%, larang martingale/grid, peringatan legalitas broker | Sebagian ada (`allow_min_lot_over_risk: false`, batas harian/mingguan) |
| **Sinyal trend** | Yang lolos syarat modal & demo | Sinyal/auto order skema A 0,25%/set, laporan jujur termasuk periode rugi | ✅ Ada (skema F 0,5%), usulan ganti ke A 0,25% |

Tahapan:
1. **Sekarang (repo ini):** hitungan berbagi/zakat/tabungan di CLI + riset lengkap.
2. **Berikutnya:** tab "Tabungan Emas" dan "Berbagi" di aplikasi Android (data profit dari tab Statistik yang sudah
   ada), endpoint cloud untuk laporan berbagi bulanan.
3. **Kemitraan:** penyaluran lewat lembaga zakat resmi dan produk tabungan emas resmi — aplikasi tidak memegang uang
   orang, hanya menghitung, mengingatkan, dan mencatat.

## 8. Batasan

- Spread dibuat tetap; swap/komisi belum dihitung (posisi trend rata-rata ±2,5 hari → swap mengurangi hasil).
- Port strategi mengikuti kode/README asli sedekat mungkin, tetapi ada penyederhanaan: trailing GOLD_ORB di level candle,
  skor FVG didekati dari deskripsi README (tanpa bonus OB), ML memakai scikit-learn HistGradientBoosting (setara
  XGBoost) dengan fitur standar, GoldTraderEA & model DRL tidak bisa direplikasi apa adanya.
- Grid martingale disimulasikan di candle M15/M5 (bukan tick); bila level ditambah di sebuah candle, TP basket tidak
  dihitung di candle itu.
- Masa depan bisa berbeda. Semua strategi tetap harus melewati akun demo sebelum uang sungguhan.

## 9. Cara mengulang

```bash
bash research/download_data.sh              # 4 dataset (±48 MB + 20 MB)
pip install scikit-learn pyarrow            # untuk uji ML & data M1
python -m research.github_popular           # bagian 3 (±1 menit)
python -m research.combine                  # bagian 4 (gabungan)
python -m research.policy                   # bagian 6
python -m research.dca                      # bagian 7.2
python -m research.engine_ab m5_2020 A --from 2022-04-01 --to 2025-04-07 --risk 0.25   # bagian 5.1
python -m xau_bot berbagi --csv riwayat.csv --persen 10 --kurs 16500
python -m xau_bot zakat --harta 250000000 --harga-gram 2300000
python -m xau_bot tabungan --setoran 300000 --harga-gram 2300000 --bulan 60
```

Harga per gram di contoh hanyalah angka contoh — isi dengan harga hari ini dari tempat membeli.
