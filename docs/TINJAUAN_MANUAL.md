# Tinjauan Manual (C2) — File Inti 41 Kandidat

Tanggal: 27 Sep 2026. Yang dibaca adalah salinan di `kandidat/` (versi terakhir tiap repo). **Kode tidak dijalankan,
tidak ada yang dipasang.** Satu-satunya akses jaringan adalah mengecek keberadaan nama paket di registry npm.

"File inti" berarti 298 file **operasional** di 41 kandidat yang menurut inventaris C (`docs/inventaris_file.csv`)
punya kemampuan berisiko: mengirim order, login, memakai internet, membuka server, menjalankan program, memuat kode
atau pickle, dan memegang kredensial. Daftarnya ada di `docs/tinjauan_manual/file_inti.csv`.

Di luar daftar itu ada 109 file lain dengan kemampuan serupa:
- 16 file model pickle, yang tidak dibuka;
- 93 file uji, backtest, arsip/legacy, dan cadangan (termasuk salinan ALGLIB di `_stdlib_backup`).

Ke-93 file itu disapu otomatis: host yang dihubungi dan pemanggilan `eval`/`exec`/`os.system`/`shell=True`/pickle/WebRequest/DLL.
- Host yang muncul hanya OANDA practice, localhost, example.com, roboforex.com, dan github.com.
- Tiga pemanggilan yang tertangkap dicek manual dan tidak berbahaya:
  - `chcp 65001` untuk mengatur encoding konsol;
  - `shell=True` untuk menguji perintah MCP milik penulis sendiri;
  - pickle yang memuat model hasil training sendiri.

## Cakupan

Setiap baris tabel di §3 menyebut file mana yang dibaca penuh dan mana yang hanya dibaca di titik aksinya.

| Cara baca | Repo | Isi |
|---|---|---|
| **Penuh**: setiap baris semua file inti, ditambah modul pendukungnya | 18 | 3aLaee, ImranDev3, Aniket, HillaryMurimi, wael-slimi, sagarmeravi, Takura-Z, cacastudymarket, phatnomenal, shamshyder, sensesVoid, nazhmi12, thanvish21, P1Piyush (kode Python & MQL5), Kiran-Kumbar, Sheyswaggz, Shivkeerth, FeziweMelvin. ±6.300 baris inti, lebih banyak lagi bila modul pendukung dihitung |
| **Campuran**: file terpenting dibaca penuh, sisanya di titik aksi | 7 | MarketForgeX, beingmushfiq, blackhunter, damaradam04, Mnauu2201, nathanaela2002, armza332 |
| **Per titik aksi**: setiap pemanggilan order, login, jaringan, server, proses, pickle, dan kredensial dibaca beserta konteksnya | 16 | yogeshkb, pipela, BlamzKunG, Pestador, AnggaKay, Leonard-zheng, RobertN1D, a1shmuk, Turnipnator, samw2591, triqbit, GifariKemal, EA_SCALPER, Franklin6840, Srijan69, ilahuerta |

Tidak dibaca baris per baris:
- Kode di repo besar yang tidak berisi titik aksi, misalnya perhitungan indikator, UI, dan pustaka ALGLIB (±117 ribu baris; hanya dicek bahwa tidak ada WebRequest atau DLL).
- Dokumentasi.
- Data CSV.
- File di riwayat git. Riwayat sudah dipindai otomatis di tahap A dan A2.

## 1. Temuan terpenting

### 1.1 Server atau jembatan yang terbuka tanpa login

Di jaringan kantor, kos, atau Wi-Fi publik, orang lain bisa memakai celah-celah ini.

| Repo | Masalah |
|---|---|
| **GifariKemal** | API dasbor berjalan di `0.0.0.0:8000` dengan CORS `*` dan tanpa login. Endpoint `POST /api/filters/config` bisa **mematikan filter keamanan bot live**, bahkan dari halaman web mana pun yang Anda buka. docker-compose juga membuka PostgreSQL (password `trading_bot_2026`) dan pgAdmin (`admin123`). |
| **Pestador** | Server Node mendengarkan di semua antarmuka tanpa login. Endpoint `/vision/capture` meneruskan URL dan path dari permintaan, jadi orang lain bisa menyuruh PC Anda membuka URL apa pun dan **menulis file ke path mana pun**. |
| **P1Piyush** | Server TCP `0.0.0.0:9998` tanpa autentikasi (antrean perintah bisa dicuri atau dipalsukan). Secret webhook ditulis di HTML dasbor. `/status` membuka saldo. |
| **armza332** | Jembatan Google Apps Script menerima `close_all` dan `pause` **tanpa secret**. |
| **EA_SCALPER** | Proxy LLM di `0.0.0.0:4000` tanpa autentikasi, memakai kunci OpenRouter Anda. |
| **Sheyswaggz** | Redis `6379` dibuka ke host tanpa password. |
| **Mnauu2201** | Bot Telegram menjawab chat dari siapa saja (memakai kuota Groq Anda). |
| **beingmushfiq** | Kunci Twelve Data ikut ke bundle browser. |

### 1.2 Rantai pasok dan perilaku berbahaya

- **EA_SCALPER `scripts/install_trading_mcps.ps1`** memasang 15 paket `@trading-mcps/*` yang **tidak ada di npm**. Hasil cek: semua 404, sedangkan paket kontrol `lodash` 200.
  - Siapa pun bisa mendaftarkan nama-nama itu, dan skrip ini akan memasang kodenya. Pola ini disebut *slopsquatting*: nama paket karangan AI.
  - Audit dependensi A2 hanya membaca file manifest, jadi skrip ini baru tertangkap di C2.
  - **Jangan jalankan.**
- **EA_SCALPER `windows_setup.ps1`** menambahkan **pengecualian Windows Defender** untuk folder MT5 dan MetaQuotes. Riwayat repo ini berisi loader dan DLL bajakan (A2), jadi kombinasinya berbahaya.
- **EA_SCALPER `coldturkey_blocker.py`** adalah alat bypass lisensi aplikasi Cold Turkey Blocker.
- EA_SCALPER juga punya 8 skrip scraping mql5.com lewat Tor atau proxy berputar.
- **samw2591**: bot otomatis menjalankan `git pull` dan `git push`, jadi kode dari remote ikut terpakai setelah restart. `npx dukascopy-node` dipanggil tanpa versi terkunci.
- **Sheyswaggz**: TA-Lib diunduh lewat HTTP tanpa checksum.
- **triqbit**: ada jalur cadangan MetaApi cloud, artinya pihak ketiga ikut memegang akses akun.

### 1.3 Order bisa terbuka tanpa stop loss, atau risikonya lebih besar dari yang tertulis

| Repo | Masalah |
|---|---|
| BlamzKunG | Semua order grid dibuka dengan **SL=0/TP=0**. Keluar hanya dikelola EA, lalu "hedge" mengunci kerugian. |
| AnggaKay | Bila broker menolak stop (error 130), EA **mengulang tanpa SL/TP**. `MaxOpenPositions=999`. |
| GifariKemal | Retcode 10016 membuat bot **mengulang tanpa SL**. |
| Turnipnator | SL diperlebar tanpa mengecilkan unit, lalu order dikirim tanpa SL dan SL ditambahkan setelahnya. Ada peringatan Telegram bila SL gagal dipasang. |
| pipela | SL digeser **lebih jauh** setelah entry, jadi risiko nyata ±3–5%, bukan 2%. |
| HillaryMurimi | Rumus lot **10× terlalu besar** (target 2% menjadi ±20%). |
| 3aLaee | SL $0,15 lebih kecil dari spread, dan tanpa batas jumlah posisi. |
| Kiran-Kumbar | Risiko default 5% (lolos sampai 10%). |
| damaradam04 | `simple_buy.py` membeli tanpa SL. |
| phatnomenal | SL/TP bisa tidak terinisialisasi. |
| phatnomenal, shamshyder | Trailing **mengubah posisi EA atau manual lain** di simbol yang sama. |

### 1.4 Bug yang membuat bot mati atau sinyalnya tidak bermakna

Kasus-kasus ini menjelaskan hasil B dan B2 (port kita memakai aturan yang *dimaksud* penulis).

| Repo | Masalah |
|---|---|
| shamshyder | Tidak bisa dikompilasi. `iMA()` dipakai sebagai nilai padahal isinya *handle*, jadi sinyal tidak pernah muncul. |
| sagarmeravi | Pine salah ketik, tidak bisa dikompilasi. |
| blackhunter | Modul yang di-import tidak ada. SL/TP untuk SELL terbalik. |
| HillaryMurimi | `TypeError` sebelum order pertama. |
| Sheyswaggz | Aplikasinya tidak ada, hanya klien Redis. |
| nathanaela2002 | Scaler di-fit ulang saat live dan PMI diisi konstan 50, jadi prediksi tidak bermakna. |
| thanvish21 | Filter kurva ekuitas mengunci selamanya setelah rugi pertama. |
| armza332 | "Self-learning" mematikan agen secara permanen. |
| P1Piyush | Retest dicari di candle sebelum breakout (logikanya terbalik). |
| nazhmi12 | Tidak memperdagangkan XAUUSD sama sekali. |
| Kiran-Kumbar | Sinyal diambil dari candle yang baru berjalan 3 detik. |

### 1.5 Riset atau backtest yang menyesatkan

- **Kebocoran data masa depan**: yogeshkb (scaler di-fit ke seluruh data).
- **Hasil in-sample**:
  - nathanaela2002 (simulasi di data latih);
  - a1shmuk ("optimasi 4.374 kombinasi");
  - Mnauu2201 (win rate dari 16 transaksi).
- **Simulasi yang terlalu optimistis**:
  - P1Piyush `alpha_v3` (entry di close, trailing memakai close lalu dicek ke low di candle yang sama);
  - Shivkeerth (TP dicek sebelum SL, entry tidak diverifikasi).
- **Model atau angka yang tidak bermakna**:
  - classifier HillaryMurimi dilatih pada 3 baris;
  - `ai_engine.py` P1Piyush dilatih pada data acak;
  - profit arbitrase BTC thanvish21 fiktif (peluang yang sama dihitung setiap detik).

### 1.6 Rancangan yang patut ditiru

- **sensesVoid**: order hanya dikirim setelah Anda mengetik "y". Ada peringatan sinyal basi dan pergeseran harga.
- **damaradam04**: executor **menolak akun live** kecuali diizinkan secara eksplisit.
- **Turnipnator**: perintah Telegram hanya untuk user terdaftar, dan bracket diverifikasi setelah order.
- **RobertN1D**: SL selalu ada di server, batas risiko dalam dolar ($6/transaksi), dan tanpa martingale.
- **a1shmuk**: sederhana, dengan SL/TP di server dan maksimal 1 posisi.
- **triqbit**: password disimpan sebagai `SecretStr`, dan Docker default ke mode demo.

## 2. Pengecekan bot kita terhadap pola-pola di atas

Hanya dibaca, tidak ada yang diubah.

- `xau_bot/broker/mt5.py` selalu mengirim `sl`/`tp` bersama order.
- Retry hanya dilakukan untuk mode pengisian yang tidak didukung (`INVALID_FILL`). Penolakan lain langsung berhenti; **tidak ada retry tanpa SL**.
- `risk.lot_size` menolak entry bila lot minimum melebihi risiko, kecuali diizinkan secara eksplisit.
- Telegram hanya menerima perintah dari `chat_id` Anda.
- Dasbor berjalan di terminal (rich), tanpa server jaringan.

Jadi pola berbahaya di §1.1 dan §1.3 **tidak ada** di bot kita. Folder `cloud/` (Vercel/Supabase) tidak termasuk tinjauan ini.

## 3. Rincian per repo

| Repo | Yang dibaca | Temuan |
|---|---|---|
| 3aLaee/xauusd-trading-bot | bot.py (185, penuh) | Login dari `.env`, data hanya ke MT5 lokal. Order selalu dengan SL/TP. ⚠️ SL default 15 "pip" × 0,01 = **$0,15** dan TP $0,10 — lebih kecil dari spread emas (±$0,2–0,3): order ditolak broker atau langsung kena SL; R:R 0,67. ⚠️ Tidak ada batas jumlah posisi: tiap menit ada sinyal → posisi menumpuk. Lot default 0,1. |
| a1shmuk/xauusd-algo-trader | xauusd_bot.py (1.080) per titik aksi: pengaturan, 5 `order_send`, trailing; 8 modul lain (fundamental, ML, SMC, optimizer, telegram, dll.) per titik jaringan/kredensial/pickle | Login memakai terminal MT5 yang sudah login (tanpa password di kode). Jaringan: FRED (St. Louis Fed), kalender ForexFactory, Telegram. Kunci FRED & token Telegram **pernah ditulis langsung di kode** (disensor di salinan; di-*override* env untuk FRED). Order: lot tetap 0,01, SL 2 ATR / TP 3 ATR di server ✅, maks 1 posisi, hanya jam 13–17 UTC, trailing SL hanya mengetat ✅. ⚠️ Parameter "dioptimasi dari 4.374 kombinasi pada 2 tahun data" → hasil in-sample, rawan overfit. Model `.joblib` dibuat & dimuat sendiri (lokal). |
| AnggaKay/XAUUSD-Machine-Learning-EA | mt4/ScalpDaily_OrderEngine.mqh (257) penuh; ScalpDaily_ML_EA_v6.mq4 (640), src/vektor_v6/*.py, scripts/*.py per titik aksi | EA MT4 + Python lewat folder file bersama MT4 (`Common\Files\ScalpDailyBridge`), tanpa internet. Model `.joblib` (pickle) dimuat dari folder lokal; file model tidak ikut di repo (hanya metadata) — jangan memuat `.joblib` dari sumber lain. 🛑 Bila broker menolak stop (error 130), EA **mengulang order dengan SL=0 dan TP=0** → posisi terbuka **tanpa stop sama sekali**. ⚠️ Default SL 7 pip = $0,70 vs TP $5 (M1), `MaxOpenPositions = 999` (praktis tanpa batas), sesi 0–24. Batas rugi harian 100 pip & circuit breaker 5 kalah beruntun ada ✅. Temuan B2: aturan yang dapat diuji rugi. |
| Aniket-Jaiswal2002 | bot.py (345), telegram_notify.py (97), config.py, penuh | Login lokal dari `config.py` (password tertulis di kode; versi riwayat berisi password asli). Order selalu dengan SL/TP, risiko 1%, maks 2 posisi, stop rugi harian 3%. ⚠️ Sinyal dihitung dari candle H4 yang **belum tutup** tiap 60 detik (bisa muncul lalu hilang). ⚠️ Trailing langsung menggeser SL dari 2 ATR ke 1 ATR pada putaran pertama, jadi SL 2 ATR di config praktis tidak pernah berlaku. `telegram_notify.py` tidak pernah dipanggil. Komentar "sesi 8–20 UTC" tapi nilainya 0–24. |
| armza332/aurum-gold-desk | js/bridge.js (94), connect.js (92), news.js (42), serve.ps1 (38) penuh; mt5/Aurum_EA.mq5 (892) & bridge/Code.gs (215) per titik aksi (WebRequest, perintah, order, ukuran lot) | EA: lot dari risiko 1% ekuitas (`tick_value/tick_size` benar), batas lot 0,20, veto bila risiko per transaksi >5% / portofolio >6%, stop harian 3%, SL 1,5 ATR, TP1 parsial + BE, TP2 runner. Internet hanya ke URL Apps Script milik Anda (kosong = offline) + Fear&Greed alternative.me di web. ⚠️ Jembatan Apps Script menerima perintah `pause`/`resume`/**`close_all`** **tanpa secret** (sengaja, karena situsnya publik) → siapa pun yang tahu URL `/exec` bisa menutup semua posisi atau menghentikan EA; status ekuitas & posisi juga bisa dibaca tanpa secret. Perintah `signal` tidak dieksekusi EA ✅. Secret bawaan `aurum-secret` perlu diganti. `serve.ps1` hanya `localhost` tetapi tidak menolak `..` (bisa membaca file di luar folder dari PC sendiri). Temuan B tetap: "self-learning" mematikan agen permanen → EA berhenti trading. |
| beingmushfiq/XAUUSD-Gold-SMC-Blueprint | vite.config.ts (25), marketDataFeed.ts (198), LogicStream.tsx (116) penuh; sisa `src/` (2.318 baris) dipindai per titik aksi | Dasbor React (dibuat di Google AI Studio), tidak mengirim order. Internet hanya Twelve Data REST + WebSocket. ⚠️ Kunci `VITE_TWELVEDATA_API_KEY` ikut ke bundle browser → **terlihat oleh siapa pun yang membuka situsnya** (sifat variabel `VITE_`). `GEMINI_API_KEY` didefinisikan di config tapi tidak dipakai di `src/`. Clipboard hanya menulis log sendiri. Candle M15 yang belum tutup ikut dianalisa (sinyal bisa berubah). |
| blackhunter4448-ops/Bot-trading-xau-usd | main.py (351) penuh; technical_analysis.py (494) & run_backtest.py (238) dibaca per fungsi sinyal/stop | Tidak ada internet selain MT5. 🛑 Modul `mt5_connection` dan `backtest` yang di-import **tidak ada di repo** → bot & backtest langsung `ImportError`. 🛑 `atr_based_stops` selalu memberi SL di bawah & TP di atas harga, **juga untuk SELL** → order SELL pasti ditolak broker (stop tidak valid). ⚠️ Sinyal dari candle H1 yang belum tutup, dicek tiap 60 detik; satu-satunya pembatas: tidak mengulang arah yang sama berturut-turut → BUY/SELL bergantian bisa menumpuk posisi. Lot tetap 0,1. |
| BlamzKunG/XAUUSD-Grid-EA | XAUUSD_Advanced_Grid_EA.mq5 (1.089) & XAUUSD_Adaptive_MeanReversion_EA.mq5 (1.130) per titik aksi: semua input, pembukaan order, langkah grid, pengali lot, hedge, penjaga DD/margin | Tanpa internet/DLL. 🛑 **Semua order dibuka dengan SL=0 dan TP=0** (tidak ada `PositionModify` sama sekali) — keluar hanya dikelola kode EA (TP keranjang, stop darurat ATR, stop ekuitas 8%/20%). Bila terminal/VPS mati atau koneksi putus, posisi grid **tanpa stop di server**. ⚠️ Grid Advanced: pengali lot 1,2×, hingga 8 level per arah (maks 2,5 lot), lalu "Smart Hedge": membuka posisi lawan seukuran seluruh keranjang → kerugian dikunci (bukan ditutup), swap terus berjalan. MeanReversion lebih konservatif (5 level, lot tetap default, stop darurat 3,5 ATR H1). Temuan B: grid ini −41R. |
| cacastudymarket/xauusd-analysis | notebooks/01_download_data.ipynb (2 sel), penuh | Hanya unduh ETF GLD harian via yfinance. Tidak ada strategi/order. |
| damaradam04-cmd/AI-TRADE-SYSTEM | mt5_connector.py (152), trade_executor.py (230), simple_buy.py (101), open_trade_with_structure.py (98), config.py (40), check/show_symbols.py, penuh; structure_engine.py (419) dibaca bagian SL/TP | Tidak ada internet selain MT5; kredensial = placeholder `...` di `config.py` (belum diisi → `initialize(path="...")` gagal sampai Anda mengisinya). ✅ `TradeExecutor` **menolak akun live** kecuali `allow_live=True`, dan skrip struktur meminta konfirmasi "yes" dua kali. Lot dihitung benar (`tick_value/tick_size`, risiko 2%). ⚠️ `DIRECTION = "buy" or "sell"` selalu `"buy"`. ⚠️ `simple_buy.py` langsung membeli 0,01 lot **tanpa SL/TP dan tanpa cek demo**, mencoba 3 mode pengisian berurutan (bisa dobel bila broker menjawab selain DONE tetapi order tetap tercatat). Tidak ada sinyal otomatis. |
| FeziweMelvin/XAUUSD-Gold-Price | xauusd-gold-price.ipynb (11 sel), penuh | Hanya eksplorasi dataset harian Kaggle (head/describe/histogram). Impor banyak model ML tetapi tidak ada yang dilatih. Tidak ada jaringan/order. |
| francomascareloai/EA_SCALPER_XAUUSD (versi terakhir) | EA utama & CTradeManager (order, input risiko); 6 bridge MQL5 (tujuan WebRequest, data akun); 72 file inti per titik aksi (jaringan, server, proses, kredensial); Alglib dicek hanya WebRequest/DLL/FILE (pustaka resmi ALGLIB/MetaQuotes) | EA utama: risiko 0,5%/transaksi, stop harian 4,5% (gaya FTMO), maks 20 transaksi/hari; WebRequest EA **hanya ke `127.0.0.1:8000`** (server Python lokal) ✅, tanpa DLL. Tetapi skrip pendukung bermasalah: 🛑 `scripts/install_trading_mcps.ps1` memasang **15 paket npm `@trading-mcps/*` yang tidak ada di npm** (dicek: semua 404) → siapa pun bisa mendaftarkan nama itu dan skrip akan memasang kodenya (*slopsquatting*); **jangan jalankan**. 🛑 `infrastructure/.../windows_setup.ps1` menambahkan **pengecualian Windows Defender** untuk folder MT5 & MetaQuotes (ditambah riwayat repo ini berisi loader/DLL bajakan → kombinasi berbahaya) dan menjalankan installer Chocolatey via `iex`. 🛑 `scripts/python/coldturkey_blocker.py` = **bypass lisensi** aplikasi Cold Turkey Blocker (ubah status ke "pro"). ⚠️ `simple_trading_proxy.py` membuka proxy LLM di `0.0.0.0:4000` **tanpa autentikasi** memakai kunci OpenRouter Anda; kunci OpenRouter pernah ditulis di `.bat` (disensor) dan master key `sk-litellm-proxy-key-12345` tertulis di kode. ⚠️ 8 skrip scraping mql5.com lewat **Tor/proxy berputar/ScraperAPI** (menghindari pembatasan situs). |
| Franklin6840/gold-trading-xauusd | gold_ai_trading.py (826) per alur data & pelatihan | Riset ML saja (RandomForest/LogReg), data CSV lokal, tanpa jaringan/order. Split train/test berurutan waktu ✅. Tanpa biaya/spread; akurasi ≠ profit. |
| GifariKemal/xaubot-ai | web-dashboard/api/main.py (478) semua endpoint; docker-compose.yml; main_live.py (2.881) jalur order/SL/lockfile; src/mt5_connector.py (888) `order_send`; src/telegram_notifier.py (1.496) penerimaan perintah; src/db/connection.py, api/db.py; news_agent/macro_connector per host; ea-research/test.mq5 per WebRequest; 40 file lain per titik aksi | Login MT5 & token dari `.env`. Jaringan: newsapi.org, Yahoo Finance, FRED, Telegram; EA riset `test.mq5` → ForexFactory & worldtimeserver.com. Telegram hanya menerima perintah dari `chat_id` Anda ✅. 🛑 **API dasbor `0.0.0.0:8000`, CORS `*`, tanpa login**: `POST /api/filters/config` bisa **mematikan filter keamanan bot live** (bot membaca `data/filter_config.json` tiap siklus) — dari siapa pun di jaringan, bahkan dari halaman web mana pun yang Anda buka (CORS `*`). ⚠️ docker-compose membuka PostgreSQL `5432` dengan password bawaan `trading_bot_2026` dan pgAdmin `5050` dengan `admin123`. ⚠️ Bila broker menolak SL (10016), bot **mengulang order tanpa SL** (SL dikelola software). Temuan B: XAUBot V3 EA berhenti sendiri; strategi rugi. |
| HillaryMurimi/mt5-gold-ai-trader | main.py (94), order_manager, trade_executor, account_handler, config, news_fetcher, sentiment_analyzer, 3 model, 3 strategi, lot_optimizer (±420 baris, penuh) | Jaringan hanya newsapi.org + unduh model HuggingFace (distilbert). `mt5.initialize()` tanpa login (memakai terminal yang sudah login); `.env` tidak dipakai. 🛑 `NewsFetcher()` dipanggil tanpa argumen `api_key` wajib → TypeError, bot berhenti sebelum order apa pun. `main.py` hanya jalan sekali (tanpa loop). ⚠️ "Pengklasifikasi strategi" RandomForest dilatih pada **3 baris** (split 80/20 dari 3 sampel) — tidak bermakna. ⚠️ Model sentimen = sentimen bahasa Inggris umum (POSITIVE/NEGATIVE), bukan arah emas. ⚠️ Lot: `pip_value=10` per $1, padahal emas 1 lot = $100 per $1 → lot **10× terlalu besar** (target risiko 2% jadi ±20%). SL/TP tetap $10/$20. LSTM `TrendPredictor` dibuat tapi tidak pernah dilatih/dipakai. `logs/trade_log.py` berisi JSON contoh (profit fiktif), bukan kode. |
| ilahuerta-IA/backtrader-pullback-window-xauusd | 14 file .py (3.450) dipindai jaringan/proses/pickle | Riset Backtrader, tidak ada jaringan/proses/pickle. Sumber dataset M5 2020–2025 yang kita pakai. Temuan B: pullback window diuji ulang. |
| ImranDev3/Gild-AI-Terminal | main.py (63), script.js (17), penuh | Tidak mengirim order. Hanya sinyal → Telegram + API Flask `0.0.0.0:5000` berisi harga & sinyal (tanpa data akun). Pesan Telegram dikirim ulang tiap 10 detik selama sinyal masih aktif (spam). |
| Kiran-Kumbar/XAU-USD-Signal-Bot | bot.py (748), Procfile, railway.json, penuh | Hanya sinyal Telegram (mode kertas, tidak ada order). Kunci Telegram & Twelve Data dari variabel lingkungan ✅. Skor SMC (BOS/CHoCH M15, OB, likuiditas, FVG, pola candle, RSI) ≥65, maks 3 sinyal/hari, SL dari OB/swing $3–20, TP 2R. ⚠️ Risiko default **5%** dari modal $200 dan masih lolos sampai 2× (10%) karena lot minimum 0,01. ⚠️ Bot bangun 3 detik setelah candle M5 baru dibuka lalu memakai `candles[-1]` — dari Twelve Data itu kemungkinan besar candle **yang baru berjalan 3 detik**, jadi pola engulfing/hammer & harga "close" belum bermakna. "Confidence %" hanyalah jumlah skor, bukan probabilitas. |
| Leonard-zheng/GoldPilot | goldx_alert.py (2.879) per titik aksi: pengambilan data, email, konfigurasi, state; config.example.env (285) penuh | **Hanya alarm email** beli/jual (tidak ada order). Data Twelve Data (M1) memakai **beberapa API key yang dirotasi** untuk melewati batas paket gratis (berpotensi melanggar ketentuan Twelve Data). Email via SMTP dengan SSL default ✅ (kredensial dari env). Tidak ada server/port terbuka, tidak ada eksekusi kode dinamis. Logika "beli dekat low sesi + rebound" berbasis puluhan parameter persentase — rawan overfit, tanpa SL/TP. |
| MarketForgeX/xauusd-ai-terminal | scripts/fetch-calendar.mjs (121), test-economic-calendar.mjs (12), xauusd-price-widget.js (55), 2 workflow; index.html dibaca per titik aksi | Situs statis. Internet: kalender ForexFactory (faireconomy.media), harga Twelve Data (kunci dari GitHub Secret, bukan di kode) / gold-api.com / xaus.com, Google Fonts. Workflow tiap 2 jam commit data ke repo sendiri. Tidak ada data pribadi/akun. Riwayat sinyal di `localStorage` browser, di-escape. Minor: judul event kalender dimasukkan ke `innerHTML` tanpa escape (sumbernya feed ForexFactory). |
| Mnauu2201/Bot-Trade-Fucking-Gold | main.py, config.py, mt5_connector.py, groq_client.py, telegram_bot.py, sentiment_analyzer.py, strategy/confluence.py (±900 baris) penuh; news_fetcher.py, calendar_fetcher.py, backtest.py per titik aksi | **Hanya sinyal** (tidak ada `order_send`). Login MT5, token Telegram, kunci Groq dari `.env` ✅. Jaringan: RSS FXStreet/investingLive, kalender ForexFactory (XML), Groq (LLM). Skor konfluensi 4 lapis (struktur H4/H1, OB/FVG H1, price action M15/M5, break M1), ambang 3,5, SL dari zona, TP 2R. ⚠️ **Handler chat Telegram menjawab siapa saja** yang mengirim pesan ke bot (tidak mengecek `chat_id`) → orang lain bisa memakai kuota Groq Anda dan membaca konteks sinyal terakhir. ⚠️ Semua timeframe memakai candle yang belum tutup. ⚠️ Angka win rate di komentar (75%) berasal dari 16 transaksi — sampel terlalu kecil. Sentimen LLM hanya dicatat, tidak memengaruhi sinyal. |
| nathanaela2002/Forex-Gold-Miner | place_order.py (239) penuh; training.py (385), sentiment.py (495), gold_scraper.py (215) per titik aksi & alur data | Broker **OANDA** (bukan MT5), token dari `.env`. Jaringan: API OANDA, Investing.com via Selenium (login memakai email/password Investing Anda dari `.env`), MySQL lokal. `sentiment.py` menulis password MySQL `root` langsung di kode (disensor di salinan). 🛑 Bot live mem-*fit* ulang `StandardScaler` pada 50 candle live pertama, bukan scaler saat training → input model berbeda skala → prediksi tidak bermakna. 🛑 Fitur `pmi_actual` diisi konstan 50 saat live. ⚠️ Model terbaik bisa berupa LSTM (input urutan 5 candle) tetapi live memberi 1 baris → error bentuk. ⚠️ Candle M30 yang belum tutup ikut dipakai; jeda loop 6.000 detik (100 menit). ⚠️ Simulasi "win rate" di training memakai data yang sama dengan pelatihan (in-sample). Ukuran order 1 unit (1 oz). `best_model_final.h5` tidak ada di repo. Temuan B2: MLP walk-forward rugi. |
| nazhmi12/-XAUUSD-Hybrid-Trading-Bot-MT5- | mesinBot.py (235), botXauusd.py (211), penuh | Login MT5 & token Telegram = placeholder di kode (tidak bocor). ⚠️ **Daftar simbol tidak memuat XAUUSD** — yang ditradingkan EURUSD, GBPUSD, USDJPY, AUDUSD (nama repo menyesatkan; port B menerapkan aturannya ke emas). Auto-trade aktif default, lot 0,01, satu posisi total, SL 1,5 ATR / TP 2×, berhenti harian di +$5 / −$3 (profit deal saja, tanpa komisi/swap; memakai jam lokal PC, bukan jam server). Pola FVG/OB memakai candle yang sudah tutup ✅, tetapi filter EMA200 memakai candle berjalan. ⚠️ `order_send` bisa mengembalikan `None` → crash (tidak dicek). Dasbor Streamlit: berita RSS (ForexFactory, FXStreet, ForexLive, Yahoo) + sentimen VADER; judul/tautan RSS dimasukkan ke HTML tanpa escape (`unsafe_allow_html`). Hanya membaca `status_market.json` lokal. |
| P1Piyush/XAUUSD-Trading-Bots | pdhl_bot.py (425), alpha_v3_enhanced.py (217), ai_engine.py (55), ExpertAdvisor.mq5 (54), penuh; web/*.html per titik aksi | Internet: Yahoo Finance (`GC=F` **futures**, bukan spot broker — level PDH/PDL bisa beda $10–30 dari harga EA), Telegram (kosong). 🛑 **Server TCP `0.0.0.0:9998` tanpa autentikasi**: siapa pun di jaringan bisa mengambil/menghapus perintah antrean atau memalsukan `STATUS` (mis. `positions=0`) → bot mengirim entry lagi. ⚠️ Flask `0.0.0.0:8081`: `/status` membuka saldo/ekuitas tanpa login; `/webhook` dijaga secret, tetapi **secret yang sama ditulis di HTML dasbor** → siapa pun yang membuka dasbor bisa mengirim order. ⚠️ Logika breakout: "retest" dicari di candle **sebelum** candle breakout (terbalik) → sinyal hampir tidak pernah muncul; port B memakai aturan yang dimaksud. WIN/LOSS dicatat dari ekuitas ≥ saldo, bukan P&L transaksi. `alpha_v3_enhanced.py` (backtest): entry di close candle sinyal, trailing digeser memakai close lalu dicek terhadap low candle yang sama, tanpa spread → hasilnya optimistis. `ai_engine.py` melatih RandomForest pada **data acak** (demo). `ExpertAdvisor.mq5` hanya kerangka (tidak ada order). EA asli hanya `.ex5` (source ada di fork Silentwolf360, lihat D2). |
| Pestador/aurum-intelligence | src/server.js (328) semua endpoint; src/vision/service.js, tradingview.js, openai-vision-provider.js, providers/live-gold-provider.js, web/app.js per titik aksi | Analisis saja — **tidak ada eksekusi order/broker**. Kunci Alpha Vantage & OpenAI dari `.env` ✅. Jaringan: Alpha Vantage, TradingView (dibuka lewat Playwright), OpenAI (screenshot chart dikirim ke OpenAI bila analisa aktif). 🛑 Server `server.listen(3000)` **tanpa host** → mendengarkan di semua antarmuka jaringan, **tanpa login**; endpoint `POST /vision/capture` meneruskan `baseUrl` dan `outputPath` dari permintaan ke browser headless → siapa pun di jaringan yang sama bisa menyuruh PC Anda membuka URL apa pun (SSRF) dan **menulis file PNG ke path mana pun** (bisa menimpa file), lalu mengirim gambarnya ke OpenAI atas biaya Anda. Penyajian file statis sudah dicegah dari `..` ✅. |
| phatnomenal/blackXAU_AUTOMATED-BOT-TRADE | blackXAU2.mq5 (252), penuh | EA MQL5 tanpa internet/DLL. Zona = high/low hari sebelumnya; breakout candle M5 lalu retest → **hanya BUY** (cabang SELL dikomentari). Lot tetap 0,1 (risk% mati secara default). ⚠️ Handle iATR/iMA dibuat & dilepas setiap bar lalu langsung `CopyBuffer` — sering gagal pada panggilan pertama: filter EMA jadi 0 (filter diam-diam lolos) dan `sl`/`tp` **tidak terinisialisasi** → order bisa ditolak atau ber-SL/TP acak. ⚠️ Trailing & BE mengubah SL **semua posisi di simbol itu** (tanpa cek magic) → ikut mengubah posisi manual/EA lain. ⚠️ Trailing/BE tidak berjalan di luar sesi 07–22 & saat filter berita (fungsi `return` lebih dulu). Filter berita memakai kalender MT5 (tidak jalan di tester). |
| pipela/AI-Trading-System-for-XAUUSD | main_trade.py (1.424) per titik aksi: login, `order_send` ×5, ukuran lot, SL/TP, tutup-semua, pickle, loop utama, belajar-online; train_ai_22_shape.py (495) per titik aksi | Login MT5 & token Telegram = placeholder kosong di kode. Jaringan hanya MT5 + Telegram. 🛑 **Setelah order terbuka, SL langsung dipindah ke "trailing" 1,5 ATR — lebih jauh dari SL awal (0,6–1 ATR) yang dipakai menghitung lot** → risiko nyata per transaksi ±3–5%, bukan 2%; hingga 4 posisi bersamaan. ⚠️ TP dibatasi $5–9 sementara SL ±0,6–1 ATR → R:R sering < 1; semua posisi ditutup begitu total profit mengambang ≥ $5. ⚠️ Model PPO **terus melatih ulang dirinya saat live** (`model.learn` tiap 5 putaran) dan menimpa file model — perilaku bot berubah tanpa diuji. `order_send` bisa `None` → crash (ditangkap, traceback dikirim ke Telegram). Pickle yang dimuat hanya buffer buatan bot sendiri. Tidak ada data aman untuk backtest (keputusan RL). |
| RobertN1D/XAUUSD-GOLD-SCALPER-MT5-EA | GOLD-HFT-SCALPER.mq5 (4.604) per titik aksi: semua input risiko, ukuran lot, `Buy/Sell`, `OrderSend` penutupan, file log; `readme html` dicek tautannya | Tanpa internet/DLL/WebRequest (sesuai klaim). Order selalu dengan **SL di server** ✅, TP=0 (profit diambil oleh kode: trailing mikro, time-stop). Lot tetap 0,01 × pengali rezim volatilitas × pengali skor (tidak pernah membesar setelah rugi — bukan martingale ✅), batas risiko $6/transaksi, stop harian $50, maks 1 posisi. ⚠️ "HFT" scalping M1 dengan target kecil sangat sensitif terhadap spread & slippage broker retail; banyak parameter (±200 input) → rawan overfit. `Sleep()` hanya pada percobaan ulang penutupan. |
| sagarmeravi/…Pullback… | emastrategy.pine (49), penuh | Pine TradingView, bukan bot. Beli saat close > SMA200 & < SMA10, keluar close > SMA10, stop darurat 10%. ⚠️ Baris 1 (`@version=5` tanpa `//`) dan baris 6 (`q  default_qty_value`) salah ketik → skrip **tidak bisa dikompilasi**. 100% ekuitas per transaksi. |
| samw2591/gold-quant-trading | config.py (138), gold_runner.py (405), watchdog.py (89), mt4_ea/GoldBridge_EA.mq4 (460), setup_data.ps1 (203), run_3_strategies.sh (92) per titik aksi; 17 file jaringan lain per host yang dihubungi | Eksekusi lewat **MT4 + jembatan file** (folder `DWX` lokal, perintah JSON) — tidak ada port jaringan terbuka. Jaringan: Google News RSS, GDELT, FRED, pizzint.watch (indeks "doomsday"), Telegram, yfinance. Token Telegram **pernah ditulis di `config.py`** (disensor di salinan). Risiko: $50/transaksi (2,5% dari $2.000), lot 0,01–0,05, turun setelah rugi (bukan martingale ✅), maks 2 posisi, maks 5 kalah/hari; `DAILY_MAX_LOSS = 9999` (batas $ praktis mati). ⚠️ `gold_runner.py` otomatis **`git pull` lalu `git push` folder `data/`** ke GitHub — kode baru dari remote ikut terpakai setelah watchdog me-restart bot; pakai hanya dengan remote milik Anda sendiri. ⚠️ `setup_data.ps1` memakai `npx dukascopy-node` **tanpa versi terkunci** (mengunduh versi terbaru dari npm saat dijalankan). Temuan B2: MACD +21,9R & gap +10,9R (di bawah Donchian bot). |
| sensesVoid/XAUUSD-AI-Agent | semua 11 file .py (667 baris), penuh | **Rancangan paling aman dari semua kandidat**: `main.py` hanya menulis sinyal ke `latest_signal.json`; order baru dikirim lewat `approve_trade.py` setelah **Anda mengetik "y"** (ada peringatan sinyal basi >5 menit & harga bergeser). Login MT5 dari `.env`. Lot dihitung benar (`tick_value/tick_size`), risiko 1%, SL AI divalidasi (sisi benar, ≥ stops level) atau fallback 1,2 ATR, TP 2R. Jaringan: kalender ForexFactory, berita Finnhub (token di URL), Ollama lokal (`qwen3:4b`, embedding), dan **Google Gemini** untuk konfirmasi — yang dikirim ke Google hanya ringkasan pasar, aturan strategi, dan judul berita (tanpa data akun). ⚠️ Keputusan dibuat LLM → tidak bisa di-backtest dan tidak deterministik. ⚠️ Candle M15 terakhir belum tutup ikut dianalisa. ⚠️ Lot dibulatkan ke minimum 0,01 → di akun kecil risiko nyata bisa > 1%. `test.py`: nomor akun demo penulis tertulis (password sudah disensor di salinan). |
| shamshyder123-oss/gold-trading-ea | GoldTradingEA.mq5 (220), TradeManager.mqh (113), Config.mqh, RiskManager.mqh, TechnicalAnalysis.mqh (±600 baris, penuh) | Tanpa internet/DLL. 🛑 `ctrade Trade;` (seharusnya `CTrade`) dan `#define LOG_LEVEL_ERRORS` bentrok dengan enum bawaan → **tidak bisa dikompilasi**. 🛑 `iMA()` di MQL5 mengembalikan *handle*, bukan nilai → `sma20`/`sma50` = nomor handle; syarat "harga > SMA20" selalu benar, "SMA20 > SMA50" salah → **sinyal BUY tidak pernah terjadi**, SELL juga tidak (harga < handle mustahil). Itu sebabnya port B memakai aturan yang dimaksud penulis. SL $1 / TP $2 (100/200 point) sangat sempit untuk H1; trailing $0,50 langsung aktif begitu profit > 0; trailing mengubah **semua posisi di simbol** (tanpa cek magic). Tutup paksa bila rugi > 5% saldo. `CTradeManager` tidak dipakai. |
| Sheyswaggz/gold-signal-provider-trading-bot | Dockerfile (84), docker-compose.yml, .env.example, redis_client.py (297), penuh | Kerangka saja: satu-satunya kode aplikasi adalah klien Redis; `app.main` yang dijalankan Dockerfile **tidak ada** → container gagal start. Tidak ada strategi/order. ⚠️ Dockerfile mengunduh TA-Lib lewat **HTTP tanpa verifikasi checksum** (rawan disusupi di jalan). ⚠️ docker-compose membuka Redis `6379` ke host **tanpa password** — bila dijalankan di VPS publik, Redis terbuka untuk siapa saja (vektor serangan umum). `redis_url` ditulis ke log (akan memuat password bila nanti ditambahkan). Container aplikasi berjalan sebagai user non-root ✅. |
| Shivkeerth-Laj/XAUUSD-Backtesting | XAUUSD BACKTEST V2.ipynb (4 sel), penuh | Notebook: unduh 50.000 candle M5 dari MT5 lokal (tanpa login di kode), lalu backtest "4 candle searah → entry di high/low candle ke-4, SL ujung lain, TP 2R". Tidak ada order live. ⚠️ Backtest tidak mengecek apakah harga benar-benar menyentuh level entry, sinyal tiap candle boleh tumpang-tindih (banyak posisi sekaligus), TP dicek sebelum SL di candle yang sama, tanpa spread → hasilnya terlalu optimistis. |
| Srijan69/Gold-Indicator-For-XAUUSD | Indicator.pine (713) per `request.security` & alert | Indikator TradingView (bukan strategi/bot). `request.security` H4 dengan `lookahead_off` tanpa `[1]` → nilai H4 berubah selama candle H4 berjalan (repaint di live). Hanya `alertcondition`, tanpa order. |
| Takura-Z/…Gold-Pressure-AI | XAUUSD_AI_MODEL.ipynb (4 sel kode), penuh | Notebook Colab: XGBoost arah candle berikutnya dari fitur tick + lag 1–3, split waktu 80/20, ambang 65%. Tidak ada order/jaringan selain Google Drive lokal Colab. Tanpa biaya/spread; "akurasi" ≠ profit. Dataset tidak ada di repo → tidak bisa diuji ulang. |
| thanvish21/gold-dominator | Gold_Dominator_Pro_v3_STRATEGY.pine (205), bot/arb_bot.py (300), penuh | Pine: skor 10 syarat ≥80 + StochRSI cross, SL 1,5 ATR, TP bertingkat 1,2/2/3 ATR, 100% ekuitas, komisi $7/order. 🛑 **Filter kurva ekuitas mematikan diri**: setelah rugi pertama, ekuitas datar sementara EMA-nya hanya mendekat dari atas (tidak pernah ≤ ekuitas) → `eq_ok` salah selamanya; guard DD 10% sama (tanpa transaksi ekuitas tidak bisa pulih). HTF `request.security` tanpa `[1]` → di live nilai H4 berubah-ubah (repaint). Harga entry/exit dihitung dari close candle sinyal, bukan harga isi. `arb_bot.py`: **BTC, bukan emas**; hanya API publik 12 bursa, mode kertas, tanpa kunci. ⚠️ "Profit kertas" menjumlahkan peluang yang sama setiap detik & tanpa biaya/transfer → angka P&L fiktif. |
| triqbit/mt5-ai-xauusd-trader | src/trading/mt5_connector.py (808) login & `order_send`; main.py (1.837) ukuran lot/SL/TP & wizard `.env`; risk_engine.py; Dockerfile, bootstrap.sh, 11 workflow GitHub per titik aksi; 14 file lain per titik jaringan/pickle | Login MT5 dari `.env` (password disimpan sebagai `SecretStr`) ✅. SL 2 ATR / TP 4 ATR, risiko 1% (lot = risiko ÷ (ATR×100)), ada "safety supervisor" yang bisa menghentikan order. ⚠️ **Jalur cadangan MetaApi**: bila MT5 lokal gagal dan token MetaApi diisi, koneksi akun dilakukan lewat layanan cloud **metaapi.cloud** (pihak ketiga memegang akses akun Anda). ⚠️ `sl`/`tp` hanya dikirim bila ada nilainya (tidak dipaksa). Docker default `--mode demo` ✅, user non-root ✅, TA-Lib diunduh dari rilis GitHub resmi (HTTPS, tanpa checksum). Workflow `auto-merge-*` memakai `pull_request` biasa (bukan `pull_request_target`) → aman dari PR fork. Model `.pkl/.pt` hanya milik sendiri. Temuan B: port strategi rugi. |
| Turnipnator/Oanda_Gold | src/config.js (361), oanda_client.js (450), telegram_bot.js (handler & otorisasi), index.js (1.958) per titik order/retry/bracket; 10 skrip research per titik file/env | Broker **OANDA** (bukan MT5), kunci dari env, default akun **practice** ✅. Risiko 1,5%/transaksi, 5% portofolio, stop harian $150. Telegram: semua perintah (`/stop`, `/emergency` tutup semua, tombol) **mengecek daftar user yang diizinkan** ✅. ⚠️ Bila order ditolak, bot mencoba ulang dengan **SL diperlebar tanpa mengecilkan unit** (risiko naik), lalu **tanpa SL** dan menambah SL setelah terisi; bila gagal, posisi terbuka tanpa SL — tetapi bot memverifikasi bracket dan mengirim peringatan "NO STOP LOSS" ke Telegram ✅. Skrip research hanya membaca data lokal. Temuan B: EMA trend & triple = rugi di data kita. |
| wael-slimi/T-XAU | CollectData.py (35), main.py (22), environment.py (55), test/test_model.py (58), penuh | Riset saja, tidak ada order/login. Internet hanya yfinance (`GC=F`). Lingkungan PPO: beli **seluruh saldo** / jual semua, tanpa biaya/spread, reward hanya di langkah terakhir (sinyal belajar sangat jarang). Path absolut milik penulis (`/home/zven/...`). Model `.zip` PPO (pickle) hanya ada di riwayat. |
| yogeshkb-yoyo/PREDICTIVE-AND-PRESCRIPTIVE-ANALYSIS-ON-XAU | Predictive and prescriptive analysis on XAU.py (316) dibaca per titik aksi & alur data | Riset: data yfinance **GOLDBEES.BO** (ETF emas India, bukan XAUUSD). ⚠️ `MinMaxScaler` di-fit pada seluruh data sebelum split 80/20 → kebocoran data masa depan. Bertanya ke Gemini "beli atau jual emas berdasarkan berita" tanpa memberi berita (jawaban LLM tidak berdasar); kunci = placeholder `"_API_"`. Jawaban dibacakan lewat gTTS (teks dikirim ke Google). "Prediksi hari berikutnya" sebenarnya prediksi hari terakhir set uji. Tidak ada order. |

## 4. Batasan

- Membaca per titik aksi berarti logika di antara titik-titik itu tidak diperiksa baris demi baris. Yang ditemukan dengan cara ini:
  - bug yang memengaruhi uang dan keamanan (order, stop, lot, jaringan, server, kredensial);
  - bukan setiap kesalahan perhitungan indikator.
- File biner seperti model `.joblib`, `.pkl`, `.h5`, `.onnx` dan `.ex5` tidak dibuka.
  - Sikap yang disarankan tetap sama: **jangan memuat pickle atau model dari repo orang lain**.
- Pengecekan nama paket npm dilakukan pada 27 Sep 2026.
  - Bila nanti ada yang mendaftarkan `@trading-mcps/*`, skrip EA_SCALPER justru menjadi lebih berbahaya.
- Temuan yang ditandai "disensor di salinan" berarti kredensial asli penulis ada di repo aslinya dan sudah diganti di `kandidat/`.
  - Riwayat lengkapnya ada di `docs/AUDIT_RIWAYAT_RELEASES.md`.

Ulangi:

```bash
python -m research.inventaris_file <folder-63-repo> --csv docs/inventaris_file.csv
# file inti = baris milik kandidat yang kolom `kemampuan`-nya memuat order/login_mt5/jaringan/server/proses/
#             kode_dinamis/kredensial/sistem, di luar model pickle, tests/, backtest, arsip/legacy/backup
# cek nama paket npm: curl -s -o /dev/null -w "%{http_code}" https://registry.npmjs.org/@trading-mcps%2fmarket-data
```
