# Audit Keamanan & Uji Strategi 63 Repo XAUUSD (kiriman pengguna)

*27 September 2026. Semua repo diunduh apa adanya (shallow clone) lalu diperiksa **tanpa menjalankan kodenya**.
Strategi yang aturannya jelas ditulis ulang di mesin uji bot ini dan diuji di data asli 2012–2026.*

## 0. Jawaban singkat

**Apakah ada script mencurigakan (keylogger, dll.)?**
- **Tidak ditemukan** keylogger, pencuri password/cookie browser, pencuri wallet, reverse shell, atau unduh-lalu-
  jalankan yang aktif di kode trading ke-63 repo. Semua temuan otomatis sudah diperiksa manual satu per satu.
- Namun ada yang **berisiko nyata**:
  1. **Jangan dijalankan — `Minhtan2005/...`** ("SHARK AI TITAN"): seluruh kode disandikan PyArmor + DLL Windows
     (`pyarmor_runtime.pyd`), perlu MT5 yang sudah login, dan menawarkan "PRO Upgrade". Isinya tidak bisa diperiksa
     siapa pun → perlakukan seperti program tak dikenal yang memegang akun Anda.
  2. **Membocorkan data akun Anda ke pemilik repo** bila dijalankan apa adanya: token bot + *chat ID* Telegram milik
     penulis tertanam di kode, sehingga saldo, ekuitas, dan profit/rugi Anda terkirim ke Telegram mereka:
     `a1shmuk/xauusd-algo-trader`, `samw2591/gold-quant-trading`, `jlvalaty/gold-quant-trading` (salinan samw2591,
     token sama), `ImranDev3/Gild-AI-Terminal`. Ganti dengan token & chat ID milik sendiri sebelum dipakai.
  3. **Tidak bisa diverifikasi (hanya file terkompilasi / tanpa kode / jualan):** `Lin-Thet-Zaw` (7 file .ex5/.ex4,
     klaim $10 → $3.976 dalam 5 hari), `P1Piyush` (6 .ex5 tanpa source), `kalpeshsinghal0055-ai` (situs EA gratis
     .ex5 + tautan afiliasi broker/VPS), `iamvishalvasava` (source "rahasia", tautan Google Drive),
     `kaleemullahkhan786` & `haseebjaan610` (README jualan, kontak email/WhatsApp), `tolgahan38` (iklan eBook),
     `iiah656` (tautan referral OKX).
  4. **File model AI** (`.zip` Stable-Baselines3, `.pkl`, `.h5`) di `pipela`, `wael-slimi`, `GifariKemal` (+2 salinan),
     `nathanaela2002`: memuat model pickle = bisa menjalankan kode apa pun. Model PPO di pipela & wael-slimi terbukti
     berisi 10 objek pickle. Muat hanya dari sumber yang Anda percaya.
- `0xagarg/xau-ai-trading-bot` dan `BizShibe/XAUUSD-ai-trading-bot` adalah **salinan identik byte-per-byte** dari
  `GifariKemal/xaubot-ai` dengan nama berbeda. Empat repo kosong (`cryptocoin81`, `eddiehng7`, `tensecrocodile`,
  `Likando21`).

**Apakah ada script yang paling terbaik?** Tidak ada yang lebih baik dari resep bot ini.
- 11 strategi baru dari daftar ini ditulis ulang dan diuji di 4 periode. **Semua strategi dengan win-rate tinggi
  (62–96%) rugi** setelah spread: grid mean-reversion (92–96% basket profit), SMA pullback (67–74%), PDH retest
  (57–76%), Keltner "live" (54–67%), RSI(2) M15 (54–65%).
- Satu kandidat, **Keltner breakout H1 versi sederhana** dari samw2591, positif di 3 dari 4 periode (+33R). Tetapi
  digabung dengan Donchian bot ini, rasio hasil/drawdown tidak membaik (4,51 vs 4,50) karena keduanya strategi
  trend yang berkorelasi (+0,43 s/d +0,55).
- **Keputusan:** tidak ada script dari 63 repo yang digabungkan ke bot. Resep tetap A-ensemble Donchian H1, risiko
  0,25%/set (docs/RISET_GITHUB.md bagian 5). Win-rate tidak bisa dinaikkan tanpa menurunkan profit — terbukti lagi
  di bagian 3.

**Alat baru:** `python -m xau_bot audit <folder>` — periksa bot/EA apa pun sebelum dijalankan (bagian 5).

---

## 1. Cara audit

1. Kloning dangkal ke-63 repo (tanpa menjalankan apa pun, tanpa mengunduh file dari tautan luar).
2. Pemindai statis `xau_bot/audit.py` (27 aturan + deteksi biner/pickle): keylogger, clipboard, tangkapan layar, pencurian data browser/
   wallet/file akun MT5, unduh-lalu-jalankan, kode tersamar (exec base64/zlib, PyArmor, JS packer), persistensi
   Windows, reverse shell, pengiriman data akun lewat `WebRequest`, `#import` DLL di EA, kredensial & chat ID
   Telegram tertanam, file pickle, biner tanpa source, program yang menyamar dengan ekstensi lain, file source tanpa
   ekstensi, tautan unduhan luar/afiliasi, martingale & grid.
3. Inventaris semua domain internet yang dihubungi kode, isi arsip .zip, dan objek pickle di model.
4. **Setiap temuan BAHAYA/WASPADA dibaca manual**; alarm palsu dicatat dan aturan diperbaiki (mis. deklarasi WinAPI
   di pustaka standar MetaQuotes, `model.eval()` PyTorch, gambar base64 di notebook).

Batasan: analisis statis bisa dikelabui; file .ex5/.ex4 terenkripsi sehingga tidak bisa dibaca; aman di sini ≠
menguntungkan.

## 2. Hasil per repo

Kolom "Otomatis" = keluaran `python -m xau_bot audit`; "Kesimpulan" = setelah pemeriksaan manual.

| # | Repo | Isi | Otomatis | Kesimpulan & catatan |
|---|---|---|---|---|
| 1 | francomascareloai/EA_SCALPER_XAUUSD | Riset MQL5 (tanpa aturan publik) | 🛑 | ✅ Bukan malware. Skrip infrastruktur VPS mereka memasang Chocolatey (`IEX DownloadString`) & pengecualian Windows Defender untuk folder MT5; jangan jalankan skrip itu di PC pribadi |
| 2 | 3aLaee/xauusd-trading-bot | MACD M1 scalper | ✅ | ✅ Diuji sebelumnya: −0,39R/trade (spread 0,25) |
| 3 | triqbit/mt5-ai-xauusd-trader | ML/DRL "enterprise" | ✅ | ✅ Klaim kinerja berjudul "Target Value" (bukan hasil) |
| 4 | codebytemirza/XAUUSD_TRADING_ASISTENT_AI | Asisten LLM | ✅ | ✅ Klaim "65% akurasi" tanpa data |
| 5 | GifariKemal/xaubot-ai | XGBoost + SMC + HMM | ⚠️ | ✅ .ex5 disertai source .mq5; file .pkl = pickle |
| 6 | ilahuerta-IA/backtrader-pullback-window-xauusd | Pullback M5 | ✅ | ✅ Diuji sebelumnya: positif hanya di data optimasi penulis |
| 7 | 0xagarg/xau-ai-trading-bot | — | ⚠️ | ⚠️ Salinan identik #5, deskripsi penuh kata kunci SEO |
| 8 | HillaryMurimi/mt5-gold-ai-trader | "LSTM/Transformer/NLP" | ✅ | ⚠️ Kode strategi hanya contoh MA 5/20 yang memakai std seluruh data (look-ahead); README melebihi isi kode |
| 9 | phatnomenal/blackXAU_AUTOMATED-BOT-TRADE | Retest high kemarin (EA) | ✅ | ✅ Bagian SELL dinonaktifkan di kode. Diuji: bagian 3 |
| 10 | Lin-Thet-Zaw/xauusd5mTimeFrameAndDailyTFrame | 7 EA terkompilasi | ⚠️ | 🛑 Tanpa source; klaim $10 → $3.976 dalam 5 hari tidak masuk akal. Jangan di akun real |
| 11 | P1Piyush/XAUUSD-Trading-Bots | PDH/PDL, ICT, Random Forest | ⚠️ | ⚠️ 6 .ex5 tanpa source; secret webhook tertanam |
| 12 | Minhtan2005/-Professional-automated-gold-trading-bot... | "AI" tersandi | 🛑 | 🛑 **Jangan dijalankan**: PyArmor + DLL, kode tidak bisa diperiksa, jualan "PRO" |
| 13 | samw2591/gold-quant-trading | Keltner/ORB/RSI(2), riset luas | ⚠️ | ⚠️ Token + chat ID Telegram penulis → saldo & ekuitas Anda terkirim ke penulis. Diuji: bagian 3 |
| 14 | RobertN1D/XAUUSD-GOLD-SCALPER-MT5-EA-FREE-SOURCE-CODE | HFT scalper MQL5 (4.600 baris) | ✅ | ✅ Source tanpa ekstensi file, tanpa internet/DLL. Tidak diport (keluarga scalper M1 gagal) |
| 15 | Kiran-Kumbar/XAU-USD-Signal-Bot | Sinyal SMC/FVG | ✅ | ✅ Keluarga SMC/FVG gagal (docs/BACKTEST.md) |
| 16 | a1shmuk/xauusd-algo-trader | EMA/RSI/SMC | ⚠️ | ⚠️ Token + chat ID Telegram penulis (saldo terkirim); API key FRED bocor. Diuji sebelumnya: overfit |
| 17 | pipela/AI-Trading-System-for-XAUUSD | PPO (RL) | ⚠️ | ⚠️ Model .zip berisi 10 objek pickle |
| 18 | Askhat707/Gold-options-terminal | Analitik opsi (web) | ✅ | ✅ Bukan strategi |
| 19 | Takura-Z/Algo-Trading-Bot-Gold-Pressure-AI- | XGBoost M1 (ONNX) | ✅ | ✅ Diwakili uji ML walk-forward |
| 20 | metalpriceapi/metalpriceapi-nodejs | Library API harga | ✅ | ✅ Library resmi, bukan strategi |
| 21 | BizShibe/XAUUSD-ai-trading-bot | — | ⚠️ | ⚠️ Salinan identik #5 |
| 22 | Turnipnator/Oanda_Gold | Breakout+ADX, Oanda | ⚠️ | ✅ `child_process` hanya menjalankan skrip backtest sendiri. Diuji: bagian 3 |
| 23 | kalpeshsinghal0055-ai/xauusdrobot | Situs "robot gratis" | ⚠️ | ⚠️ EA .ex5 tanpa source + tautan afiliasi Exness/VPS, pelacak Intercom/GTM. Konflik kepentingan: afiliasi dibayar per lot |
| 24 | sagarmeravi/XAUUSD-Pullback-Strategy-Development-Analysis- | SMA pullback (Pine) | ✅ | ✅ Diuji: bagian 3 |
| 25 | FeziweMelvin/XAUUSD-Gold-Price | Dataset harga 2004– | ✅ | ✅ Data, bukan strategi |
| 26 | jlvalaty/gold-quant-trading | — | ⚠️ | ⚠️ Salinan sebagian #13 dengan token & chat ID Telegram yang sama |
| 27 | ImranDev3/Gild-AI-Terminal | Terminal sinyal | ⚠️ | ⚠️ Token + chat ID Telegram penulis tertanam |
| 28 | Franklin6840/gold-trading-xauusd | ML + makro | ✅ | ✅ Diwakili uji ML |
| 29 | Aniket-Jaiswal2002/xauusd-trading-bot | EMA 13/34 + RSI H4 | ✅ | ✅ Diuji: bagian 3 |
| 30 | BlamzKunG/XAUUSD-Grid-EA | Grid mean-reversion & grid | ✅ | ✅ Diuji: bagian 3 (grid umum: docs/RISET_GITHUB.md 6.3) |
| 31 | beingmushfiq/XAUUSD-Gold-SMC-Blueprint | Dashboard SMC | ✅ | ✅ Keluarga SMC gagal |
| 32 | iamvishalvasava/Verified-XAUUSD-Momentum-EA | Pameran hasil | ✅ | ⚠️ Source dirahasiakan, hanya gambar + tautan Google Drive → tidak bisa diverifikasi |
| 33 | nazhmi12/-XAUUSD-Hybrid-Trading-Bot-MT5- | FVG + OB M5 | ✅ | ✅ Password MT5 penulis bocor di kode (risiko bagi dia). Keluarga FVG gagal |
| 34 | HisyamAlammar/YQTS | Hanya README | ✅ | ⚠️ Klaim "+42,1%" tanpa kode |
| 35 | Shivkeerth-Laj/XAUUSD-Backtesting | Notebook "dari Instagram" | ✅ | ✅ Edukasi |
| 36 | Leonard-zheng/GoldPilot | Alarm harga menit | ✅ | ✅ Bukan sistem trading |
| 37 | t54983200/algomatic-backend | Backend layanan berbayar "arbitrase" | ✅ | ⚠️ Pembayaran LemonSqueezy & kripto; arbitrase spot–futures "milidetik" tidak realistis untuk ritel |
| 38 | Mnauu2201/Bot-Trade-Fucking-Gold | LLM (Groq) + TA | ⚠️ | ✅ .zip hanya berisi CSV laporan |
| 39 | blackhunter4448-ops/Bot-trading-xau-usd | Pustaka indikator | ✅ | ✅ |
| 40 | wael-slimi/T-XAU | PPO (RL) | ⚠️ | ⚠️ Model .zip berisi 10 objek pickle |
| 41 | nathanaela2002/Forex-Gold-Miner | LSTM + berita | ⚠️ | ⚠️ Model .h5; password penulis tertanam; scraping dengan undetected-chromedriver |
| 42 | cacastudymarket/xauusd-analysis | Notebook ML (GLD) | ✅ | ✅ Edukasi |
| 43 | tolgahan38/xauusd | Hanya README | ✅ | ⚠️ Iklan eBook situs luar |
| 44 | eddiehng7/XAU-Expert-Advisor | Kosong | ✅ | — |
| 45 | shamshyder123-oss/gold-trading-ea | EA modular (RSI/MACD/MA) | ✅ | ✅ |
| 46 | Pestador/aurum-intelligence | Multi-agen JS | ✅ | ✅ |
| 47 | thanvish21/gold-dominator | Indikator Pine + bot arbitrase kripto | ✅ | ✅ Pine memakai `request.security` HTF tanpa `[1]` → nilai HTF berubah-ubah saat live (repaint), hasil live bisa beda dari backtest |
| 48 | Sheyswaggz/gold-signal-provider-trading-bot--xauusd- | Bot sinyal TA-Lib | ✅ | ✅ |
| 49 | armza332/aurum-gold-desk | "Tim 7 AI" + EA | ⚠️ | ✅ EA hanya mengirim ekuitas/posisi ke URL Apps Script milik pengguna sendiri (kosong = offline) |
| 50 | tensecrocodile/xauusd-trading-strategy | Kosong | ✅ | — |
| 51 | cryptocoin81/Bot-Trading-XAUUSD_MT5 | Kosong | ✅ | — |
| 52 | iiah656/okx-xaut-guide | Artikel XAUT | ✅ | ⚠️ Tautan referral OKX |
| 53 | AnggaKay/XAUUSD-Machine-Learning-EA | XGBoost ganda | ✅ | ✅ Diwakili uji ML |
| 54 | Likando21/nextgen-gold-bot | Kosong (dihapus) | ✅ | ✅ Riwayat: widget harga emas |
| 55 | sensesVoid/XAUUSD-AI-Agent | Sinyal RAG, wajib persetujuan manusia | ✅ | ✅ Desain aman: tidak pernah order tanpa persetujuan |
| 56 | angelolockdev/trading-signals-generator | Aplikasi sinyal manual | ✅ | ✅ |
| 57 | yogeshkb-yoyo/PREDICTIVE-AND-PRESCRIPTIVE-ANALYSIS-ON-XAU | Analisis fuzzy/ML | ✅ | ✅ Edukasi |
| 58 | Srijan69/Gold-Indicator-For-XAUUSD-for-day-trader | Indikator Pine | ✅ | ✅ |
| 59 | kaleemullahkhan786/Emperor-XAU-Expert-Advisor | Hanya README | ✅ | ⚠️ Jualan (email); "hedging" saat drawdown hanya menunda rugi |
| 60 | haseebjaan610/XAUUSD-SafeScalper---MT5-Expert-Advisor | Hanya README | ✅ | ⚠️ Jualan (WhatsApp) |
| 61 | MarketForgeX/xauusd-ai-terminal | Terminal web | ⚠️ | ✅ `new Function` hanya di test |
| 62 | damaradam04-cmd/AI-TRADE-SYSTEM | Skrip MT5 sederhana | ✅ | ✅ |
| 63 | Ming-jx/xauusd-trading-dashboard | Dashboard UI | ✅ | ✅ |

## 3. Uji strategi (`python -m research.github_popular2`)

Aturan asli repo, tanpa optimasi ulang; spread 0,30 (2012–22) / 0,25 (2022–26); entry di open berikutnya; SL dicek
lebih dulu. Satuan R = kelipatan risiko awal per trade.

| Strategi (repo) | Win-rate | 2012–17 | 2018–22 | 2022–25 | 2025–26 | Total | Positif |
|---|---|---|---|---|---|---|---|
| Grid mean-reversion (BlamzKunG) | **92–96%** | −100,6R | −83,9R | −30,9R | −9,3R | −224,7R | 0/4 |
| SMA200/SMA10 pullback H1 (sagarmeravi) | **67–74%** | −10,3%\* | −13,3%\* | +11,4%\* | −11,8%\* | −24,0%\* | 1/4 |
| SMA pullback M5 (sagarmeravi) | 62–70% | – | – | −102,9%\* | −4,8%\* | – | 0/2 |
| Retest high kemarin, BUY (phatnomenal) | **57–76%** | −37,2R | −51,5R | −9,3R | +2,7R | −95,3R | 1/4 |
| Keltner "live": stop 3 jam + trailing 0,15 ATR (samw2591) | 54–67% | −75,1R | −36,0R | −38,9R | +7,0R | −143,0R | 1/4 |
| RSI(2) M15 (samw2591) | 54–65% | −90,7R | −52,2R | −37,7R | −9,9R | −190,5R | 0/4 |
| ORB New York 15 menit (samw2591) | 42–51% | −94,7R | −24,7R | +27,1R | +24,2R | −68,1R | 2/4 |
| Breakout 10 bar + ADX≥35, SL=TP $3 (Turnipnator) | 34–45% | −199,5R | −143,4R | −58,1R | −112,0R | −513,0R | 0/4 |
| Sama, jarak diskalakan harga | 24–39% | −548,7R | −365,1R | −132,0R | −113,0R | −1.158,8R | 0/4 |
| EMA 13/34 + RSI H4 (Aniket) | 25–49% | +11,3R | −2,9R | −14,2R | +3,1R | −2,7R | 2/4 |
| **Keltner sederhana SL 4,5 / TP 8 ATR (samw2591)** | 29–39% | +20,5R | −20,4R | +13,4R | +19,9R | **+33,4R** | **3/4** |
| *Pembanding: Donchian H1 55/20 (bot ini, 1 set)* | *33–43%* | *+48,8R* | *+30,7R* | *+9,3R* | *+34,9R* | *+123,7R* | *4/4* |

\* % harga per trade tanpa leverage (strategi aslinya memakai 100% modal tanpa stop dekat).

Dari daftar ini juga sudah diuji sebelumnya (docs/RISET_GITHUB.md): 3aLaee (−0,39R/trade), a1shmuk (2/4 periode,
backtest penulis memakai data masa depan), pullback window ilahuerta (positif hanya di data optimasi), dan keluarga
ML (xaubot-ai & salinannya, triqbit, AnggaKay, Takura-Z, Franklin6840: akurasi arah 51,3%, 2/4 periode).

Pola yang sama terulang: **makin tinggi win-rate, makin kecil untungnya**. Win-rate tinggi di sini didapat dari
target kecil dan stop jauh/tanpa stop, dan biaya spread memakan semua tepinya. Klaim samw2591 (Sharpe 0,52 selama 11 tahun sampai 8,4 di varian terbaiknya)
tidak terulang: konfigurasi live mereka (stop waktu 3 jam + trailing 0,15 ATR) rugi di 3 dari 4 periode.

## 4. Gabungan (`python -m research.combine2`)

Ketahanan Keltner (81 variasi parameter): 93% positif di ≥3 periode, tetapi hanya 16% positif di keempatnya (lemah
di 2018–22). Donchian bot ini: 89% variasi positif di keempat periode.

| Portofolio (1 unit risiko per set) | Total 4 periode | DD terburuk | Hasil/DD | Periode positif |
|---|---|---|---|---|
| A-ensemble Donchian (3 set) | +327,9 | −72,9 | 4,50 | 4/4 |
| Keltner saja | +33,4 | −41,4 | 0,81 | 3/4 |
| A-ensemble + Keltner (4 set) | +361,3 | −80,0 | 4,51 | 4/4 |

Korelasi hasil bulanan Donchian vs Keltner: +0,43 / +0,45 / +0,44 / +0,55. Menambah Keltner hanya menambah ukuran
posisi (untung dan drawdown naik bersama), bukan diversifikasi. **Keputusan: tidak ditambahkan.**

## 5. Cara aman memakai bot/EA orang lain

1. Periksa dulu: `python -m xau_bot audit folder_bot` (tambahkan `--ringkas` untuk banyak folder sekaligus). Baca
   setiap baris BAHAYA/WASPADA.
2. Tolak kode yang disandikan (PyArmor, .ex5 tanpa .mq5, .exe) untuk akun real.
3. Cari `TOKEN`, `CHAT_ID`, `WebRequest`, `requests.post`: pastikan data hanya dikirim ke akun/URL milik Anda.
4. Di MT5: matikan "Allow DLL imports" dan batasi daftar URL WebRequest untuk EA yang tidak butuh.
5. Jalankan di akun demo dan (idealnya) komputer/VPS terpisah dari email, bank, dan wallet.
6. Jangan memuat model `.pkl/.zip/.h5` dari orang yang tidak dikenal.
7. Klaim win-rate/profit tanpa data yang bisa diulang = anggap tidak ada.

## 6. Cara mengulang

```bash
# unduh 63 repo (tidak menjalankan apa pun)
while read r; do git clone -q --depth 1 "https://github.com/$r" "repos/${r//\//__}"; done < daftar.txt
python -m xau_bot audit --ringkas repos/*/
python -m xau_bot audit repos/NAMA_REPO                  # detail per baris
bash research/download_data.sh
python -m research.github_popular2                         # bagian 3
python -m research.combine2                                # bagian 4
```
