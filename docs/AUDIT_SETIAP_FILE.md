# Audit C — Kemampuan SETIAP File (63 repo)

Tanggal: 27 Sep 2026. Alat: `research/inventaris_file.py`. Data per file: `docs/inventaris_file.csv` (4.351 baris).
Kode repo **tidak dijalankan**. Python & notebook dibaca dengan **AST** (impor dan panggilan fungsi yang benar-benar
ada, bukan kata di komentar); MQL/JS/TS/shell/PowerShell/Pine dengan pola teks. Semua baris yang menunjukkan
kemampuan berisiko (jaringan + login, proses, kode dinamis, server, domain tidak umum, akses sistem) **dibaca manual**;
hasilnya di §3.

## 1. Arti kolom

| Kemampuan | Artinya | Contoh bukti |
|---|---|---|
| order | Bisa membuka/menutup/mengubah posisi | `mt5.order_send`, `OrderSend`, `trade.Buy`, `POST /v3/accounts/…/orders` (OANDA) |
| login_mt5 | Login ke akun MT5 dengan nomor/password | `mt5.initialize(login=…, password=…)`, `mt5.login` |
| jaringan | Menghubungi internet | `requests.post`, `urllib`, Telegram, API LLM, `WebRequest`, `fetch` |
| server | Membuka port/server di komputer Anda | Flask, FastAPI, `http.server`, `express`, `socket.bind` |
| proses | Menjalankan program lain / shell / DLL | `subprocess`, `os.system`, `#import "x.dll"`, `child_process`, `Start-Process` |
| kode_dinamis | Menjalankan kode yang dibuat saat berjalan / memuat pickle | `exec`, `eval`, `importlib`, `pickle.load`, `joblib.load`, `torch.load` |
| kredensial | Membaca password/token | `os.getenv`, `.env`, `keyring` |
| sistem | Clipboard, keyboard, registry, layar | `pyperclip`, `GetAsyncKeyState`, `winreg` |

## 2. Ringkasan per repo

Angka = jumlah file yang punya kemampuan itu. "biner/model" = file biner tertutup / file pickle-model.
Domain = alamat internet di kode yang **bukan** layanan umum (GitHub, Telegram, OpenAI, Yahoo, dll. tidak ditampilkan).
Repo kosong (cryptocoin81, eddiehng7, tensecrocodile, Likando21) tidak punya file di versi terakhir.

| Repo | file | kode | order | login MT5 | jaringan | server | proses | kode dinamis | biner/model | domain tak umum di kode |
|---|---|---|---|---|---|---|---|---|---|---|
| 0xagarg/xau-ai-trading-bot | 481 | 234 | 14 | 24 | 24 | 1 | 7 | 28 | 4/13 | nfs.faireconomy.media, www.worldtimeserver.com |
| 3aLaee/xauusd-trading-bot | 5 | 1 | 1 | 1 |  |  |  |  |  |  |
| AnggaKay/XAUUSD-Machine-Learning-EA | 27 | 20 | 2 |  |  |  |  | 5 |  |  |
| Aniket-Jaiswal2002/xauusd-trading-bot | 8 | 4 | 1 | 2 | 1 |  |  |  |  |  |
| Askhat707/Gold-options-terminal | 12 | 0 |  |  |  |  |  |  |  |  |
| BizShibe/XAUUSD-ai-trading-bot | 481 | 234 | 14 | 24 | 24 | 1 | 7 | 28 | 4/13 | nfs.faireconomy.media, www.worldtimeserver.com |
| BlamzKunG/XAUUSD-Grid-EA | 15 | 2 | 2 |  |  |  |  |  |  |  |
| FeziweMelvin/XAUUSD-Gold-Price | 6 | 2 |  |  |  |  |  | 1 |  |  |
| Franklin6840/gold-trading-xauusd | 9 | 1 |  |  |  |  |  |  |  |  |
| GifariKemal/xaubot-ai | 481 | 234 | 14 | 24 | 24 | 1 | 7 | 28 | 4/13 | nfs.faireconomy.media, www.worldtimeserver.com |
| HillaryMurimi/mt5-gold-ai-trader | 23 | 19 | 2 | 1 | 2 |  |  | 2 |  |  |
| HisyamAlammar/YQTS | 3 | 0 |  |  |  |  |  |  |  |  |
| ImranDev3/Gild-AI-Terminal | 8 | 3 |  | 1 | 2 | 1 |  |  |  |  |
| Kiran-Kumbar/XAU-USD-Signal-Bot | 6 | 1 |  |  | 1 |  |  |  |  |  |
| Leonard-zheng/GoldPilot | 24 | 2 |  |  | 1 |  |  |  |  |  |
| Lin-Thet-Zaw/xauusd5mTimeFrameAndDailyTFr | 8 | 0 |  |  |  |  |  |  | 7 |  |
| MarketForgeX/xauusd-ai-terminal | 12 | 6 |  |  | 3 |  |  | 1 |  | cdn-nfs.faireconomy.media, nfs.faireconomy.media, xaus.com |
| Ming-jx/xauusd-trading-dashboard | 15 | 8 |  |  |  |  |  |  |  |  |
| Minhtan2005/-Professional-automated-gold | 7 | 3 |  |  |  |  |  |  | 2 |  |
| Mnauu2201/Bot-Trade-Fucking-Gold | 83 | 16 |  | 1 | 6 |  |  |  | 6 | investinglive.com, nfs.faireconomy.media |
| P1Piyush/XAUUSD-Trading-Bots | 36 | 4 |  |  | 2 | 1 |  |  | 6 |  |
| Pestador/aurum-intelligence | 86 | 73 |  |  | 7 | 1 | 1 |  |  |  |
| RobertN1D/XAUUSD-GOLD-SCALPER-MT5-EA-F | 3 | 1 | 1 | 1 |  |  |  |  |  |  |
| Sheyswaggz/gold-signal-provider-trading | 14 | 6 |  |  | 5 | 2 | 1 |  |  |  |
| Shivkeerth-Laj/XAUUSD-Backtesting | 4 | 1 |  | 1 |  |  | 1 |  |  |  |
| Srijan69/Gold-Indicator-For-XAUUSD-fo | 2 | 1 |  |  |  |  |  |  |  |  |
| Takura-Z/Algo-Trading-Bot-Gold-Pressu | 8 | 3 |  |  |  |  |  | 1 |  |  |
| Turnipnator/Oanda_Gold | 61 | 46 | 2 |  | 11 |  | 5 | 1 |  |  |
| a1shmuk/xauusd-algo-trader | 11 | 10 | 1 | 8 | 2 |  |  | 1 |  | nfs.faireconomy.media |
| angelolockdev/trading-signals-generator | 46 | 27 |  |  | 1 |  |  |  |  | api.allorigins.win |
| armza332/aurum-gold-desk | 37 | 18 | 1 |  | 5 |  | 1 |  |  | api.alternative.me, script.googleusercontent.com |
| beingmushfiq/XAUUSD-Gold-SMC-Blueprint | 26 | 17 |  |  | 1 |  |  |  |  |  |
| blackhunter4448-ops/Bot-trading-xau-usd | 8 | 3 |  |  |  |  |  |  |  |  |
| cacastudymarket/xauusd-analysis | 14 | 11 |  |  | 1 |  |  |  |  |  |
| codebytemirza/XAUUSD_TRADING_ASISTENT_AI | 4 | 2 |  |  |  | 1 |  |  |  |  |
| damaradam04-cmd/AI-TRADE-SYSTEM | 10 | 8 | 2 | 4 |  |  |  |  |  |  |
| francomascareloai/EA_SCALPER_XAUUSD | 1054 | 394 | 10 | 7 | 44 | 6 | 33 | 7 | /1 | api.ipify.org, api.scraperapi.com, chocolatey.org, nodejs.org, polyformproject.org, s3.amazonaws.com, www.alglib.net, ww |
| haseebjaan610/XAUUSD-SafeScalper---MT5-Exp | 1 | 0 |  |  |  |  |  |  |  |  |
| iamvishalvasava/Verified-XAUUSD-Momentum-EA | 3 | 0 |  |  |  |  |  |  |  |  |
| iiah656/okx-xaut-guide | 1 | 0 |  |  |  |  |  |  |  |  |
| ilahuerta-IA/backtrader-pullback-window-x | 23 | 14 |  |  |  |  |  |  |  |  |
| jlvalaty/gold-quant-trading | 23 | 13 | 1 |  | 4 |  |  |  |  | api.gdeltproject.org |
| kaleemullahkhan786/Emperor-XAU-Expert-Advisor | 1 | 0 |  |  |  |  |  |  |  |  |
| kalpeshsinghal0055-ai/xauusdrobot | 252 | 91 |  |  | 20 | 2 |  |  | 1 | forge.butterfly-effect.dev, get.xauusdrobot.com, my.govpsfx.com, my.xs.com, nfs.faireconomy.media, one.exnessonelink.com |
| metalpriceapi/metalpriceapi-nodejs | 6 | 2 |  |  | 1 |  |  |  |  |  |
| nathanaela2002/Forex-Gold-Miner | 6 | 4 | 1 |  | 4 |  |  | 4 | /1 |  |
| nazhmi12/-XAUUSD-Hybrid-Trading-Bot-M | 3 | 2 | 1 | 1 | 2 | 1 |  |  |  | www.forexlive.com |
| phatnomenal/blackXAU_AUTOMATED-BOT-TRADE | 2 | 1 | 1 |  |  |  |  |  |  |  |
| pipela/AI-Trading-System-for-XAUUSD | 6 | 2 | 1 | 1 | 1 |  | 1 | 3 | 1/1 |  |
| sagarmeravi/XAUUSD-Pullback-Strategy-Dev | 4 | 2 | 1 |  |  |  |  |  |  |  |
| samw2591/gold-quant-trading | 202 | 143 | 2 |  | 21 |  | 7 |  |  | api.gdeltproject.org, nodejs.org, www.pizzint.watch |
| sensesVoid/XAUUSD-AI-Agent | 14 | 11 | 1 | 2 | 2 |  |  |  |  | nfs.faireconomy.media |
| shamshyder123-oss/gold-trading-ea | 9 | 5 | 2 |  |  |  |  |  |  |  |
| t54983200/algomatic-backend | 52 | 45 |  |  | 3 | 1 |  |  |  | api.lemonsqueezy.com, cdn-icons-png.flaticon.com, rejoicestore.lemonsqueezy.com, t-rclumkia.cregis.io |
| thanvish21/gold-dominator | 5 | 3 | 1 |  | 1 |  |  |  |  | api-pub.bitfinex.com, api.bybit.com, api.coinbase.com, api.gateio.ws, api.gemini.com, api.huobi.pro, api.kraken.com, api |
| tolgahan38/xauusd | 1 | 0 |  |  |  |  |  |  |  |  |
| triqbit/mt5-ai-xauusd-trader | 582 | 255 | 8 | 1 | 17 | 2 | 8 | 17 |  |  |
| wael-slimi/T-XAU | 13 | 4 |  |  | 1 |  |  | 2 | 1 |  |
| yogeshkb-yoyo/PREDICTIVE-AND-PRESCRIPTIVE- | 4 | 1 |  |  | 1 |  |  | 1 |  |  |

Total: 4.351 file = 2.013 kode (1.137 Python, 44 notebook, 832 MQL/JS/shell/lainnya), 1.182 dokumen/konfigurasi,
410 pustaka standar MetaQuotes (dilewati, sama dengan yang terpasang di setiap MT5), 665 data/gambar, 42 model
pickle, 36 biner/arsip, 3 teks > 3 MB.

## 3. Hasil tinjauan manual

### 3.1 Ke mana data dikirim (setiap file jaringan + login MT5)

Semua file yang sekaligus login MT5 dan memakai internet sudah dibaca. **Tidak ada yang mengirim password/login MT5
ke server pihak ketiga.** Tujuan kirimannya:

| Repo | File | Kiriman |
|---|---|---|
| ImranDev3 | `main.py` | Pesan sinyal ke Telegram (token di file) |
| nazhmi12 | `mesinBot.py` | Pesan trade ke Telegram |
| pipela | `main_trade.py` | Pesan trade ke Telegram |
| triqbit | `src/trading/mt5_connector.py` | MetaApi (layanan resmi MT5 cloud; login dikirim ke MetaApi **memang** cara kerjanya) |
| GifariKemal (+ 2 salinan) | `docker/scripts/*.bat/.sh`, `web-dashboard/src/data/books.ts` | Hanya mencetak alamat dashboard lokal; `books.ts` = teks dokumentasi |

### 3.2 Server yang dibuka bot (bisa diakses komputer lain)

| Repo | Server | Risiko |
|---|---|---|
| **P1Piyush** `pdhl_bot.py` | TCP `0.0.0.0:EA_PORT` tanpa autentikasi (jembatan ke EA) + webhook Flask `0.0.0.0` | 🛑 Siapa pun yang bisa menjangkau port itu bisa mengirim perintah `LONG/SHORT/CLOSE` bila tahu secret webhook — dan secret bawaannya tertulis di repo publik (sudah diganti `GANTI_…` di `kandidat/`). Jangan jalankan di VPS tanpa firewall |
| **GifariKemal** (+ 0xagarg, BizShibe) `web-dashboard/api/main.py` | FastAPI `0.0.0.0:8000`, CORS `*`, tanpa login | ⚠️ `POST /api/filters/config` bisa **mematikan filter keamanan bot** (mis. `ml_confidence`, `h1_bias`) dari komputer lain di jaringan |
| ImranDev3 `main.py` | Flask `0.0.0.0:5000` | Hanya `GET /api/data` (harga & sinyal) |
| armza332 `Aurum_EA.mq5` | EA memanggil Google Apps Script milik Anda sendiri (kosong = offline) | Perintah jarak jauh terbatas pause/resume/**close_all**; secret bawaan `aurum-secret` wajib diganti |
| Pestador `src/server.js` | HTTP lokal (dashboard agen, tangkapan layar TradingView) | Tidak ada order |
| EA_SCALPER `scripts/*` | `http.server`/LiteLLM proxy untuk alat pengembang | Tidak terkait order |
| kalpeshsinghal, t54983200 | Situs pemasaran EA / backend langganan berbayar (Lemon Squeezy, Cregis kripto) | Bukan bot |

### 3.3 Menjalankan program lain (79 file)

Semua dibaca. Isinya: `pip/npm install` di Dockerfile & skrip setup, `tasklist` untuk mencegah bot dobel
(GifariKemal), `git pull/commit/push` data trade (samw2591 `gold_runner.py` — **otomatis mem-push data trading Anda ke
GitHub** bila dijalankan di clone yang punya akses push), watchdog restart bot (samw2591), pengunduh data Dukascopy
(`npx`), skrip build/compile MQL5 & infrastruktur AWS milik penulis (EA_SCALPER, unduhan dari nodejs.org/S3 resmi).

Yang perlu dicatat di EA_SCALPER (tidak dipakai bot, tapi ada di repo):
- `scripts/python/coldturkey_blocker*.py` — alat **membobol langganan Pro aplikasi Cold Turkey Blocker** (mengubah
  database-nya lalu mematikan prosesnya). Bukan malware bagi Anda, tapi alat crack.
- `scripts/scrape_mql5_tor.py` & varian `multiproxy/scraperapi` — menyedot situs mql5.com lewat Tor/proxy berganti
  untuk menghindari blokir.
- `scripts/windows/start_proxy_and_roo.bat` — berisi API key OpenRouter asli penulis (sudah disensor di `kandidat/`).

### 3.4 Kode dinamis

Hanya 5 file memakai `exec/eval/__import__/importlib/new Function`: semuanya test atau pengecek dependensi
(MarketForgeX, Turnipnator, EA_SCALPER, triqbit ×2). Sisanya "kode_dinamis" = memuat model ML (`joblib/pickle/torch/
stable-baselines3/ONNX`) — aman hanya bila file model dibuat sendiri; **jangan memuat file model .pkl/.pth/.zip
kiriman orang** (42 file seperti itu ada di repo-repo ini).

### 3.5 Akses sistem

Hanya 1 file: tombol "salin" di web beingmushfiq (`navigator.clipboard.writeText`, menulis, bukan membaca).
Tidak ada keylogger, pembaca clipboard, registry, atau tangkapan layar di kode penulis (versi terakhir). Pola
`GetAsyncKeyState/SetWindowsHookEx` hanya ada di header WinAPI resmi MetaQuotes (`winuser.mqh`).

### 3.6 Domain tidak umum

| Domain | Repo | Kegunaan |
|---|---|---|
| nfs.faireconomy.media | GifariKemal, a1shmuk, Mnauu2201, sensesVoid, MarketForgeX, kalpeshsinghal | Kalender berita ForexFactory (JSON publik) |
| investinglive.com, www.forexlive.com | Mnauu2201, nazhmi12 | RSS berita |
| api.gdeltproject.org, www.pizzint.watch | samw2591, jlvalaty | Berita geopolitik & "Pentagon pizza index" |
| api.alternative.me | armza332 | Fear & Greed index |
| api.allorigins.win | angelolockdev | Proxy CORS publik untuk harga emas |
| xaus.com | MarketForgeX | Widget harga |
| 11 bursa kripto (Binance, Kraken, OKX, …) | thanvish21 `bot/arb_bot.py` | Harga publik untuk arbitrase (tanpa API key) |
| api.ipify.org, api.scraperapi.com | EA_SCALPER | Cek IP Tor & layanan scraping |
| get.xauusdrobot.com, my.xs.com, one.exnessonelink.com, vigco.co, markets4you, copyconnectfx, govpsfx | kalpeshsinghal | Tautan afiliasi broker/VPS di situs pemasaran |
| api.lemonsqueezy.com, *.cregis.io | t54983200 | Pembayaran langganan (kartu & kripto) |

Tidak ditemukan domain penampung data curian (webhook Discord, pastebin, requestbin, ngrok) di kode versi terakhir.

## 4. Kesimpulan C

- **Tidak ada kode penulis (versi terakhir) yang mencuri data**: tidak ada pengiriman password MT5 ke pihak ketiga,
  tidak ada keylogger/clipboard/registry, tidak ada unduh-lalu-jalankan.
- Risiko nyata yang ditemukan dari membaca setiap file: server tanpa autentikasi di P1Piyush dan GifariKemal,
  auto-push data ke GitHub di samw2591, alat crack di EA_SCALPER, dan 42 file model pickle yang bisa menjalankan kode
  saat dimuat.
- Yang tetap tidak bisa diperiksa: isi `.ex4/.ex5` (36 biner), kode tersandi Minhtan2005, dan riwayat git (lihat
  `docs/AUDIT_RIWAYAT_RELEASES.md`).

Ulangi: `python -m research.inventaris_file <folder-berisi-repo> --csv inventaris.csv`
