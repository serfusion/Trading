# Sniper bot Telegram — strategi teruji bertahun-tahun, terpisah dari aplikasi (8 Okt 2026)

Permintaan pengguna: "buat botnya dengan yang sudah teruji bertahun-tahun dengan WR dan profit tinggi dari scanning sistem
anda, ibarat sniper bot di Telegram dengan otomatisasi, pisahkan dengan apk kita (dipantau lewat bot Telegram), dan
tutorkan step by step cara menjalankan supaya live".

Kode: `sniper_bot/` (terpisah dari `android/`, `cloud/`, `xau_bot/` — mematikan bot ini tidak mengganggu aplikasi).
Tes: `tests/test_sniper_bot.py` (37 tes, tanpa jaringan) + `tests/test_spot_paritas.py`.
Riset pendukung: `docs/eksternal/spek_spot_dip_bot.txt`, `docs/eksternal/hasil_spot_paritas.txt` (💎),
`docs/eksternal/hasil_listing_dip_porto.txt` (🎯), `docs/eksternal/hasil_listing_short.txt` (short listing futures),
`docs/TOKEN_BARU.md` (DEX/chain baru), `docs/SPOT_PELUANG.md`, `docs/SPOT_DIP.md`.

## Ringkasan jujur (baca dulu)
- Dari semua yang sudah diuji di repo ini, **hanya satu strategi kripto otomatis yang teruji bertahun-tahun dengan WR
  tinggi DAN untung di periode lama maupun 5 tahun terakhir: 💎 Spot dip** (beli koin besar yang sedang turun, jual +3%
  dalam 10 hari). Itulah mesin utama bot ini.
- Angka yang dipakai adalah versi **JUJUR** (varian D): koin dipilih menurut volume pada SAAT ITU, bukan 20 koin yang
  kita tahu hari ini masih hidup. Sejak Okt 2021: **TP tercapai 90,9%**, rata **+0,8% per sinyal**, portofolio
  **±+8,5%/tahun, DD −15%** (biaya ×2: +5%/th). Periode lama (2019–Sep 2021): +23,4%/th, DD −21%.
- Itu **bukan "jackpot"**: 1 dari ±11 sinyal gagal dengan rugi rata **−18% (terburuk −55%)**; tahun 2021 & 2022 portofolio
  −2%. BTC beli-tahan sejak Okt 2021 +11%/th tetapi DD −77%. Keunggulan 💎 = WR tinggi & DD kecil, bukan profit besar.
- 🎯 **Listing dip** (token baru turun ≥ 60%) untung sebelum 2021 tetapi **TIDAK lolos** sejak Okt 2021 (−0,7%/trade;
  flash crash 10 Okt 2025) → di mode live bot **hanya mengabari**, tidak membeli (bisa diizinkan, risiko sendiri).
- 🦄 **DEX / chain baru** (Arc, Robinhood Chain): peluang direbut bot dalam 0,1–3 detik (`docs/TOKEN_BARU.md`) → hanya
  peringatan, tanpa order.
- **Short token baru di futures** (`hasil_listing_short.txt`): lolos kriteria (+2,6%/trade BARU) tetapi **WR 47%**,
  median −13%, tanpa 5% trade terbaik ±0, butuh akun futures & berisiko squeeze (+5.000%) → **tidak dipasang**.
- Semua angka = uji masa lalu, **bukan janji**. Mulai mode KERTAS 2–4 pekan, lalu live dengan modal kecil.

## Strategi di dalam bot
| Strategi | Aturan | Periode LAMA | Sejak Okt 2021 (BARU) | Status di bot |
|---|---|---|---|---|
| 💎 `spot_dip` | Tiap hari 07:05–08:00 WIB: 20 koin volume terbesar, peluang model ≥ 93% ATAU 3 hari merah turun ≥ 10% di atas SMA200; lewati volatilitas > P90 & saat BTC < SMA200. Beli 10% ekuitas, **TP +3% (limit di bursa), maks 10 hari, tanpa SL**, maks 10 posisi | TP 93,5%, +1,15%/sinyal, portofolio +23,4%/th DD −21% | TP **90,9%**, **+0,80%**/sinyal, portofolio **+8,5%/th DD −15%**; acak −5,4%/th | **Otomatis** (kertas & live) |
| 🎯 `listing_dip` | Token baru Binance: P0 = VWAP 60 menit pertama; beli bila ≤ P0 × 0,4 dalam 30 hari; TP +20%, SL −50% (close 1 jam), maks 90 hari, 5% ekuitas | WR 89%, +12,3%/trade, porto +32%/th | WR 71%, **−0,7%**/trade (SL close 1 jam +3,5%, dipilih setelah melihat data) | Kertas: otomatis • Live: **hanya kabar** |
| 🦄 `dex` | Pool baru / selisih harga DEX (butuh `token_bot/`) | — | peluang ≥1% hilang < 3 dtk | Hanya peringatan |
| ✋ manual | `/beli SOL 20 5 10` (limit ≤ harga tampil +1%, konfirmasi tombol) | — | — | Atas keputusanmu |

Per tahun 💎 (portofolio varian D): 2021 −2%, 2022 −2% (hampir tanpa sinyal: BTC di bawah SMA200), 2023 +19%, 2024 +11%,
2025 +16%, 2026 (s.d. Sep) +2%. Per sinyal: 2020 89% +0,5%, 2021 93% +0,9%, 2023 94% +1,5%, 2024 89% +0,8%,
2025 93% +0,8%, 2026 95% +1,1%. 25% posisi sempat turun ≥ 10% (63% di antaranya tetap kena TP, rata akhir −5%); 11% sempat
turun ≥ 20% (39% tetap TP, rata akhir −12%). Menjual saat turun sudah diuji **memperburuk** hasil → bot menahan.

Pilihan semesta 💎 (`spot_dip.semesta`): `volume20` (bawaan, angka jujur di atas) atau `tetap20` (= 20 koin aplikasi/cloud;
uji BARU 92–94% dan +9,7–16,9%/th tetapi koinnya dipilih hari ini → terlalu optimistis).

## Cara kerja bot
- **Sinyal** dari data pasar PUBLIK Binance (`data-api.binance.vision`, tanpa kunci): harga semua pair tiap 60 detik,
  candle 1 menit/1 jam/harian. **Eksekusi** di bursa pilihanmu lewat pustaka `ccxt` dengan kunci API milikmu.
  Mode **kertas** (bawaan) = simulasi penuh tanpa uang; TP kertas terisi bila high candle 1 menit menyentuh TP.
- **Telegram**: perintah hanya diterima dari **chat pribadi** dengan user id di `TELEGRAM_CHAT_ID` (grup & orang lain
  diabaikan tanpa balasan). Aksi uang (`/beli`, `/tutup`, `/hapus`) selalu minta tombol konfirmasi (beli 30 detik).
- **Batas risiko keras** (`risiko:`): maks $/trade, maks total posisi, maks jumlah posisi, maks trade/hari, **stop rugi
  harian** (rugi tertutup + perubahan nilai posisi sejak 07:00 WIB ≤ −X → entry baru dijeda sampai 07:00 WIB besok).
- **TP** = order limit jual di bursa begitu posisi terbuka (tetap terisi walau bot mati; harga dibulatkan ke ATAS).
  **SL & batas waktu** dijalankan bot (jual pasar) — bot harus hidup 24 jam.
- **Order "tidak pasti"** (jaringan putus setelah order dikirim): bot TIDAK pernah membeli ulang otomatis — bot
  dijeda, kirim 🚨, kamu cek aplikasi bursa lalu `/beres`. Order diberi `clientOrderId` unik.
- **State** di `sniper_bot/data/kertas/state.json` atau `.../live/state.json` (terpisah: posisi simulasi tidak pernah
  terbawa ke akun nyata), ditulis atomik; restart tidak kehilangan posisi. Hanya satu proses boleh jalan (`bot.lock`).
- Fungsi strategi = riset: 🎯 replay kode bot vs `research/listing_dip_porto.py` **169/169 trade identik**; 💎 fitur &
  peluang sama dengan `cloud/api/_spot.py` (selisih ≤ 1e-12, 39 contoh fixture). Hasil live tetap bisa berbeda dari uji
  karena harga isi, fee, slippage, bursa berbeda, atau bot mati.

## Tutorial langkah demi langkah (dari nol sampai live)

### Langkah 0 — Siapkan "rumah" bot (harus menyala 24 jam)
Pilih SATU:
- **VPS Linux (disarankan)** dengan region **Singapura** (alternatif Jepang/Eropa). Penyedia mana pun yang punya region
  Singapura; paket terkecil cukup (1 vCPU, 1 GB RAM, ±$4–6/bulan). **JANGAN region Amerika Serikat** (Binance menolak IP
  AS: galat 451). VPS lokal Indonesia/PC rumah bisa terkena blokir domain Binance oleh operator → data sinyal gagal.
  Cek dari server: `curl -s -o /dev/null -w "%{http_code}\n" https://data-api.binance.vision/api/v3/ping` harus `200`.
- **PC Windows** yang selalu menyala (`start_sniper.bat`). Pastikan tidak tidur/hibernasi & domain Binance terbuka.
- HP Android (Termux) TIDAK disarankan: sering dimatikan sistem hemat baterai → SL/batas waktu tidak jalan.

### Langkah 1 — Buat bot Telegram (5 menit)
1. Di Telegram buka **@BotFather** → `/newbot` → nama (mis. `Sniper Saya`) & username berakhiran `bot`.
2. BotFather membalas **token** `123456789:AA...`. Simpan; jangan dibagikan (pemegang token mengendalikan bot).
3. Disarankan: di BotFather `/setjoingroups` → **Disable** (bot tidak bisa dimasukkan ke grup).
4. Buka bot barumu → tekan **Start** / kirim `/start`.

### Langkah 2 — Pasang kode di server/PC
Linux (VPS Ubuntu 22.04/24.04):
```bash
sudo apt update && sudo apt install -y git python3 python3-venv
git clone https://github.com/serfusion/Trading.git && cd Trading     # repo privat: login GitHub / token akses
git checkout claude/eager-wright-sl7bob                               # atau main setelah di-merge
python3 -m venv .venv && source .venv/bin/activate
pip install -r sniper_bot/requirements.txt
```
Windows: pasang Python 3.11+ (centang "Add to PATH"), unduh repo (git clone atau ZIP), lalu di Command Prompt pada folder
repo: `pip install -r sniper_bot\requirements.txt`.

### Langkah 3 — Isi rahasia (.env) & dapatkan id Telegram
```bash
cp sniper_bot/.env.example sniper_bot/.env && chmod 600 sniper_bot/.env   # Windows: copy sniper_bot\.env.example sniper_bot\.env
nano sniper_bot/.env                              # isi TELEGRAM_TOKEN=... (dari BotFather)
python -m sniper_bot chat-id                      # setelah kirim /start ke bot -> muncul angka id
nano sniper_bot/.env                              # isi TELEGRAM_CHAT_ID=angka tadi
python -m sniper_bot uji-telegram                 # "✅ Uji pesan" + menu tombol muncul di Telegram
```
`chat-id` dijalankan saat bot BELUM jalan (bot yang sedang jalan "menghabiskan" pesan baru).

### Langkah 4 — Konfigurasi (mulai mode KERTAS)
```bash
cp sniper_bot/config.example.yaml sniper_bot/config.yaml
nano sniper_bot/config.yaml       # biarkan mode: kertas; atur modal_kertas_usd & risiko sesuai modal
```
Patokan `risiko:` menurut modal (💎 teruji = 10 slot × 10%; minimum order bursa umumnya $5–10):

| Modal | `maks_usd_per_trade` | `maks_total_usd` | `stop_rugi_harian_usd` |
|---|---|---|---|
| $100 (minimum wajar) | 10 | 100 | 15 |
| $500 | 50 | 500 | 60 |
| $1.000 | 100 | 1000 | 120 |

Bila batas lebih kecil dari 10% ekuitas, bot tetap membeli selama ukuran ≥ 50% target; di bawah itu sinyal dilewati
(seperti portofolio riset) dan dikabari.

### Langkah 5 — Uji sebelum jalan
```bash
python -m sniper_bot cek       # satu putaran SIMULASI tanpa Telegram & tanpa order (pertama kali ±8 menit: mencari
                               # waktu listing ±400 pair; berikutnya cepat)
python -m sniper_bot replay    # uji ulang 🎯 listing dip 2017-2026 dengan KODE BOT (butuh folder data repo)
python -m research.spot_paritas uji   # uji ulang 💎 semua varian (butuh data repo, ±beberapa menit)
python -m pytest -q tests/test_sniper_bot.py tests/test_spot_paritas.py
```

### Langkah 6 — Jalankan 24 jam (mode kertas dulu, 2–4 pekan)
Linux (systemd — hidup lagi otomatis bila server restart/bot galat):
```bash
mkdir -p sniper_bot/data                                # wajib ada sebelum layanan dimulai (ReadWritePaths)
sudo cp sniper_bot/sniper-bot.service /etc/systemd/system/
sudo nano /etc/systemd/system/sniper-bot.service     # ganti User=ubuntu & semua path /home/ubuntu/Trading
sudo systemctl daemon-reload && sudo systemctl enable --now sniper-bot
journalctl -u sniper-bot -f                            # lihat log (Ctrl+C keluar; bot tetap jalan)
```
Windows: klik dua kali `start_sniper.bat` (jendela tetap terbuka; bot mulai ulang sendiri bila berhenti).

Di Telegram muncul "🤖 Sniper bot aktif — mode KERTAS". Tiap pagi 07:05–08:00 WIB ada pesan "💎 Pindai harian"
(sinyal, dibeli, dilewati). Pantau dengan 📊 Status / 📂 Posisi / 🧾 Riwayat. 💎 rata-rata ±9 sinyal/bulan (tidak ada
sinyal saat BTC di bawah SMA200 — itu disengaja). Bandingkan hasil kertas dengan tabel strategi: WR ±90%, rata ±+0,8%.

### Langkah 7 — Pilih bursa & buat kunci API (hanya bila mau live)
Bot butuh pair **USDT** spot (sinyal memakai harga Binance USDT; pair IDR tidak didukung).

| Bursa | `ccxt_id` | Catatan |
|---|---|---|
| **Tokocrypto** (disarankan untuk pengguna Indonesia) | `tokocrypto` | Bursa lokal terdaftar & diawasi OJK (dulu Bappebti), punya pair USDT, didukung ccxt. Tidak semua koin 💎/listing baru ada → bot melewati & mengabari. Harga bisa sedikit berbeda dari Binance. |
| Binance (global) | `binance` | Likuiditas terbesar & harga = sumber sinyal, tetapi **tidak terdaftar di Indonesia** (situsnya pernah diblokir Kominfo 2023) → risiko hukum/akses tanggung sendiri. Bot otomatis **menolak jalan** bila kunci API Binance boleh withdraw/transfer. |
| Bybit / OKX / KuCoin / Gate / MEXC | `bybit` / `okx` / `kucoin` / `gate` / `mexc` | Didukung ccxt; status di Indonesia mirip Binance (asing, tidak terdaftar). OKX/KuCoin butuh passphrase (`BURSA_API_PASSWORD`). |
| Indodax | — | Pair IDR saja → **belum didukung**. |

Membuat kunci API (nama menu bisa sedikit berbeda per bursa): Akun → **API Management / Manajemen API** → buat kunci →
- Izin: **Spot trading SAJA**. **Matikan withdraw/penarikan**, transfer internal, futures, margin.
- **Batasi IP** = IP publik VPS (`curl -4 ifconfig.me`).
- Isi `BURSA_API_KEY`, `BURSA_API_SECRET` (dan `BURSA_API_PASSWORD` bila ada) di `sniper_bot/.env`, lalu di
  `config.yaml` set `bursa.ccxt_id`.
- Uji TANPA order: `python -m sniper_bot uji-bursa` → saldo USDT, status izin kunci (Binance dicek otomatis), dan berapa
  dari 20 koin 💎 yang tersedia di bursa itu.

### Langkah 8 — Pindah ke LIVE (bertahap)
1. Isi saldo **USDT di akun spot** bursa (beli USDT dengan rupiah di bursa itu bila perlu).
2. Di `config.yaml`: `mode: live` dan **batas kecil dulu** (mis. `maks_usd_per_trade: 10`, `maks_total_usd: 100`,
   `stop_rugi_harian_usd: 15`).
3. Restart: `sudo systemctl restart sniper-bot` (Windows: tutup & buka lagi `start_sniper.bat`). State live mulai
   kosong di `sniper_bot/data/live/` — posisi kertas tidak ikut (dan bot menolak jalan bila state tercampur).
4. Telegram menampilkan "mode LIVE 💸". Setiap BELI/TUTUP dikabari dengan harga & ID; TP terlihat sebagai order limit di
   aplikasi bursa. Jangan memperdagangkan koin yang sama secara manual di akun itu (bot hanya mengenal posisinya sendiri).
5. Setelah 1–2 bulan hasil live mendekati angka uji (WR ±90%, rata ±+0,8%/sinyal), naikkan batas pelan-pelan.
   Bila jauh di bawah → `/jeda` dan evaluasi.

### Langkah 9 — Operasional harian
- 08:00 WIB ringkasan harian otomatis. Galat ⚠️ dikirim maks sekali per jam per jenis (rahasia disensor otomatis).
- 🚨 **"order tidak pasti"**: buka aplikasi bursa → riwayat order & saldo koin itu. Kirim `/beres`, lalu: bila order
  BELI ternyata terisi, koinnya ada di saldo tetapi tidak dikelola bot (jual manual bila perlu); bila posisi JUAL sudah
  terjual di bursa → `/hapus ID`. Setelah yakin → `/lanjut`.
- `/jeda` saat ragu atau pasar kacau; posisi terbuka tetap dikelola. `/lanjut` untuk membuka lagi.
- Memperbarui kode: `git pull` lalu restart. Jangan hapus `sniper_bot/data/live/state.json` selama ada posisi live.
- Mematikan total: `sudo systemctl stop sniper-bot` (order TP di bursa tetap ada; SL/batas waktu tidak jalan).

## Perintah Telegram
| Perintah / tombol | Fungsi |
|---|---|
| `/status` 📊 | mode, kas, ekuitas, untung/rugi sejak 07:00 WIB, batas risiko, status strategi, order tidak pasti |
| `/posisi` 📂 | posisi terbuka: harga masuk, harga kini, %, TP/SL, batas waktu |
| `/riwayat` 🧾 | statistik per strategi + 15 trade terakhir |
| `/listing` 🆕 | token baru ≤ 30 hari yang dipantau: P0, harga sinyal (−60%), jarak harga sekarang |
| `/pindai` 🔎 | cek listing sekarang; 💎 di luar 07:05–08:00 WIB atau sudah dipindai = hanya menampilkan sinyal |
| `/jeda` ⏸ / `/lanjut` ▶️ | hentikan / izinkan lagi entry baru (posisi terbuka tetap dikelola) |
| `/strategi spot_dip mati` | matikan/hidupkan satu strategi (`hidup`) |
| `/beli SOL 20 5 10` | beli manual $20 SOL, TP +5%, SL −10% (tombol 30 dtk; tidak terisi bila harga sudah > +1%) |
| `/tutup P12` | jual posisi P12 sekarang (konfirmasi tombol) |
| `/hapus P12` | hapus P12 dari catatan bot TANPA menjual (sudah dijual manual / koin delisting) |
| `/beres` | hapus tanda order tidak pasti setelah kamu cek bursa |
| `/saldo` | saldo bursa (live) atau kertas |

## Masalah umum (FAQ)
| Gejala | Penyebab & solusi |
|---|---|
| `HTTP 451` / "restricted location" | VPS di Amerika Serikat. Pindah ke region Singapura/Jepang/Eropa. |
| Galat `harga`/`spot data` terus-menerus | Domain Binance diblokir jaringan (operator Indonesia) → pakai VPS Singapura. |
| Bot tidak membalas di Telegram | Token/`TELEGRAM_CHAT_ID` salah → `python -m sniper_bot chat-id`; perintah harus dari chat PRIBADI dengan bot; pastikan proses jalan (`systemctl status sniper-bot`). |
| Log "409: bot dipakai proses lain" | Ada dua proses/komputer menjalankan token yang sama → matikan salah satu. |
| "bot lain sedang memakai ... bot.lock" | Bot sudah jalan (mis. via systemd). Jangan jalankan `jalan` dua kali; `cek` aman (simulasi). |
| "⛔ Kunci API ini boleh MENARIK/TRANSFER dana" | Buat kunci baru tanpa izin withdraw & transfer (Langkah 7). |
| `uji-bursa` gagal "Invalid API-key, IP, or permissions" | Whitelist IP salah / izin Spot belum dicentang / kunci baru belum aktif (tunggu 1–5 menit). |
| "⏭ ... dilewati: XYZ/USDT tidak ada di ..." | Koin tidak terdaftar di bursa pilihanmu (sering di bursa lokal). |
| "nilai ... < minimum" / "ukuran ... < 50% target" | Ukuran di bawah minimum bursa atau batas risiko terlalu kecil → naikkan modal/batas (tabel Langkah 4). |
| "⚠️ Pindai 💎 hari ini terlewat" | Bot mati/gagal data saat 07:05–08:00 WIB. Bot sengaja tidak membeli lebih siang (jauh dari yang diuji). |
| Posisi tidak tertutup saat bot mati | TP limit tetap di bursa; SL & batas waktu dijalankan bot → hidupkan lagi, bot melanjutkan dari state. |
| Ingin mengulang simulasi dari nol | Hentikan bot, hapus `sniper_bot/data/kertas/` (folder kertas saja), jalankan lagi. |
| Ganti bursa | Tutup semua posisi live dulu (bot menolak jalan bila state berisi posisi di bursa lain). |

## Keamanan & risiko (baca sebelum live)
- Bot tidak pernah memanggil penarikan dana; tetap gunakan kunci API **tanpa izin withdraw** + whitelist IP.
- `sniper_bot/.env`, `config.yaml`, `data/` tidak masuk git (`.gitignore`). Jangan kirim isi `.env` ke siapa pun
  (termasuk ke chat AI). Teks galat yang dikirim ke Telegram disensor (tanda tangan URL, token, kunci).
- Hanya chat pribadi pemilik yang bisa memerintah bot; jangan bagikan akun Telegram/HP yang terhubung.
- 💎 tanpa stop loss: satu sinyal gagal rugi rata −18% (terburuk −55%) dari ukuran posisinya; kegagalan cenderung datang
  bersamaan saat pasar ambruk (filter BTC mengurangi, tidak menghapus). Ukuran 10%/koin wajib dipatuhi.
- Model 💎 dilatih s.d. Sep 2026; pola bisa berubah. Koin bisa di-delist (LUNA, FTT) → `/hapus` & jual manual.
- Semua angka di dokumen ini adalah **hasil uji masa lalu**, bukan janji. Pakai modal yang siap hilang, mulai kecil.
