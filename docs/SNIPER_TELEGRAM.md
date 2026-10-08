# Sniper bot Telegram — strategi teruji bertahun-tahun, terpisah dari aplikasi (8 Okt 2026)

Permintaan pengguna: "buat botnya dengan yang sudah teruji bertahun-tahun dengan WR dan profit tinggi dari scanning sistem
anda, ibarat sniper bot di Telegram dengan otomatisasi, pisahkan dengan apk kita (dipantau lewat bot Telegram), dan
tutorkan step by step cara menjalankan supaya live".

Kode: `sniper_bot/` (terpisah dari `android/`, `cloud/`, `xau_bot/`). Tes: `tests/test_sniper_bot.py`.
Riset pendukung: `docs/TOKEN_BARU.md`, `docs/SPOT_PELUANG.md`, `docs/SPOT_PINDAI.md`, `docs/SPOT_JATUH.md`,
`docs/eksternal/hasil_listing_dip_porto.txt`, `docs/eksternal/hasil_listing_short.txt`, `docs/eksternal/hasil_bursa_infra.txt`,
`docs/eksternal/hasil_dex_latensi.txt`.

(ISI_RINGKAS)

## Strategi di dalam bot
(ISI_STRATEGI)

## Cara kerja bot
- **Sinyal** memakai data pasar PUBLIK Binance (`data-api.binance.vision`, tanpa kunci): daftar simbol, harga semua pair
  tiap 60 detik, candle 1 menit/harian. **Eksekusi** di bursa pilihan pengguna lewat pustaka `ccxt` (kunci API milik
  pengguna). Mode **kertas** (bawaan) = simulasi penuh tanpa uang.
- **Telegram**: bot hanya melayani `TELEGRAM_CHAT_ID` pemilik. Menu tombol: 📊 Status, 📂 Posisi, 🧾 Riwayat, 🆕 Listing,
  🔎 Pindai, ⏸ Jeda, ▶️ Lanjut. Aksi uang manual (`/beli`, `/tutup`) selalu minta tombol konfirmasi (kedaluwarsa 2 menit).
- **Batas risiko keras** (`risiko:` di config): maks $/trade, maks total posisi, maks jumlah posisi, maks trade/hari,
  **stop rugi harian** (rugi tertutup + mengambang hari ini ≤ −X → entry baru dijeda sampai 07:00 WIB besok).
- **TP** dipasang sebagai order limit jual di bursa begitu posisi terbuka (tetap terisi walau bot mati). **SL** dan
  **batas waktu** dipantau bot tiap 60 detik (jual pasar) — bila bot mati, SL tidak jalan → jalankan 24 jam.
- **Status** di `sniper_bot/data/state.json` (ditulis atomik) — restart tidak kehilangan posisi.
- Kode strategi yang jalan live = kode yang sama dengan uji ulang (`python -m sniper_bot replay`) → hasil identik dengan riset.

## Tutorial langkah demi langkah (dari nol sampai live)

### Langkah 0 — Siapkan "rumah" bot (harus menyala 24 jam)
Pilih SATU:
- **VPS Linux** (disarankan) region **Singapura/Jepang/Eropa** — JANGAN region Amerika Serikat (Binance menolak IP AS,
  galat 451). Spesifikasi kecil cukup (1 vCPU, 1 GB RAM). (ISI_VPS)
- **PC Windows** yang sudah menjalankan MT5 (folder repo sama, `start_sniper.bat`). PC harus menyala & tidak tidur.
- HP Android (Termux) TIDAK disarankan: sering dimatikan sistem hemat baterai → SL/batas waktu tidak jalan.

### Langkah 1 — Buat bot Telegram (5 menit)
1. Di Telegram buka **@BotFather** → kirim `/newbot` → beri nama (mis. `Sniper Fitri`) dan username yang diakhiri `bot`
   (mis. `sniper_fitri_bot`).
2. BotFather membalas **token** seperti `123456789:AA...`. Simpan; jangan dibagikan (siapa pun yang memegang token bisa
   mengendalikan bot).
3. Buka bot barumu (klik tautan dari BotFather) lalu tekan **Start** / kirim `/start`.

### Langkah 2 — Pasang kode di server/PC
Linux (VPS, Ubuntu 22.04/24.04):
```bash
sudo apt update && sudo apt install -y git python3 python3-venv
git clone https://github.com/serfusion/Trading.git && cd Trading     # repo privat: login GitHub / token akses
git checkout claude/eager-wright-sl7bob                               # atau main setelah di-merge
python3 -m venv .venv && source .venv/bin/activate
pip install -r sniper_bot/requirements.txt
```
Windows: pasang Python 3.11+ (centang "Add to PATH"), unduh repo (git clone atau ZIP), lalu di Command Prompt pada folder
repo: `pip install -r sniper_bot\requirements.txt`.

### Langkah 3 — Isi rahasia (.env) & dapatkan chat_id
```bash
cp sniper_bot/.env.example sniper_bot/.env        # Windows: copy sniper_bot\.env.example sniper_bot\.env
nano sniper_bot/.env                              # isi TELEGRAM_TOKEN=... (dari BotFather)
python -m sniper_bot chat-id                      # setelah kamu kirim /start ke bot -> muncul chat_id
nano sniper_bot/.env                              # isi TELEGRAM_CHAT_ID=angka tadi
python -m sniper_bot uji-telegram                 # pesan "✅ Uji pesan" + menu tombol harus muncul di Telegram
```

### Langkah 4 — Konfigurasi (mulai mode KERTAS)
```bash
cp sniper_bot/config.example.yaml sniper_bot/config.yaml
nano sniper_bot/config.yaml       # biarkan mode: kertas; atur modal_kertas_usd sesuai modal yang akan dipakai
```

### Langkah 5 — Uji sebelum jalan
```bash
python -m sniper_bot cek       # satu putaran tanpa Telegram: data Binance, pindai 💎, daftar listing
python -m sniper_bot replay    # uji ulang 🎯 listing dip 2017-2026 dengan KODE BOT yang sama (butuh folder data repo)
python -m pytest -q tests/test_sniper_bot.py
```

### Langkah 6 — Jalankan 24 jam (mode kertas dulu, 2–4 pekan)
Linux (systemd — hidup lagi otomatis bila server restart/bot galat):
```bash
sudo cp sniper_bot/sniper-bot.service /etc/systemd/system/
sudo nano /etc/systemd/system/sniper-bot.service     # ganti User=ubuntu & path /home/ubuntu/Trading sesuai server
sudo systemctl daemon-reload && sudo systemctl enable --now sniper-bot
journalctl -u sniper-bot -f                            # lihat log (Ctrl+C keluar; bot tetap jalan)
```
Windows: klik dua kali `start_sniper.bat` (jendela harus tetap terbuka; bot mulai ulang sendiri bila berhenti).
Di Telegram muncul "🤖 Sniper bot aktif — mode KERTAS". Pantau dengan tombol 📊 Status / 📂 Posisi / 🧾 Riwayat.
Bandingkan hasil kertas dengan angka teruji (bagian strategi). Untuk 💎 butuh ±2–4 pekan agar ada 10+ trade.

### Langkah 7 — Kunci API bursa (hanya bila mau live)
(ISI_BURSA)
Aturan keamanan WAJIB:
- Izin kunci: **Spot trading saja**. Matikan **Withdraw/penarikan**, futures, margin, transfer.
- **Whitelist IP** = IP publik VPS (`curl -4 ifconfig.me`). Kunci tanpa whitelist sering kedaluwarsa & berbahaya.
- Isi `BURSA_API_KEY` / `BURSA_API_SECRET` (`BURSA_API_PASSWORD` bila bursa memakai passphrase) di `sniper_bot/.env`.
- Uji tanpa order: `python -m sniper_bot uji-bursa` → saldo & daftar pasar tampil.

### Langkah 8 — Pindah ke LIVE (bertahap)
1. Di `config.yaml`: `mode: live`, `bursa.ccxt_id: <bursa>`, dan **batas kecil dulu**: `maks_usd_per_trade: 10`,
   `maks_total_usd: 50`, `stop_rugi_harian_usd: 10`. Pastikan saldo USDT (atau IDR) cukup di akun spot.
2. Restart: `sudo systemctl restart sniper-bot` (Windows: tutup & buka lagi `start_sniper.bat`).
3. Telegram menampilkan "mode LIVE 💸". Setiap BELI/TUTUP dikabari dengan harga & ID; TP terlihat sebagai order limit di
   aplikasi bursa.
4. Setelah 1–2 bulan hasil live mendekati angka teruji, naikkan batas pelan-pelan. Bila jauh di bawah → `/jeda` dan
   evaluasi.

### Langkah 9 — Operasional harian
- 08:00 WIB ringkasan harian otomatis. Pesan ⚠️ galat dikirim maks sekali per jam per jenis.
- `/jeda` saat berita besar/pasar kacau atau saat ragu; posisi terbuka tetap dikelola. `/lanjut` untuk membuka lagi.
- Memperbarui kode: `git pull` lalu restart. Status posisi tersimpan di `sniper_bot/data/state.json` (jangan dihapus saat
  ada posisi terbuka).
- Mematikan total: `sudo systemctl stop sniper-bot` (order TP yang sudah terpasang di bursa tetap ada; SL tidak jalan).

## Perintah Telegram
| Perintah / tombol | Fungsi |
|---|---|
| `/status` 📊 | mode, kas, nilai posisi, untung/rugi hari ini, batas risiko, status strategi |
| `/posisi` 📂 | posisi terbuka: harga masuk, harga kini, %, TP/SL, batas waktu |
| `/riwayat` 🧾 | statistik per strategi + 15 trade terakhir |
| `/listing` 🆕 | token baru ≤ 30 hari yang dipantau: P0, harga beli (−60%), jarak harga sekarang |
| `/pindai` 🔎 | pindai listing & 💎 sekarang |
| `/jeda` ⏸ / `/lanjut` ▶️ | hentikan / izinkan lagi entry baru (posisi terbuka tetap dikelola) |
| `/strategi spot_dip mati` | matikan/hidupkan satu strategi (`hidup`) |
| `/beli SOL 20 5 10` | beli manual $20 SOL, TP +5%, SL −10% (konfirmasi tombol; dibatasi maks $/trade) |
| `/tutup P12` | jual posisi P12 sekarang (konfirmasi tombol) |
| `/saldo` | saldo bursa (live) atau kertas |

## Masalah umum (FAQ)
| Gejala | Penyebab & solusi |
|---|---|
| `HTTP 451` / "Service unavailable from a restricted location" | VPS di Amerika Serikat. Pindah ke region Singapura/Jepang/Eropa. |
| Bot tidak membalas di Telegram | Token/`TELEGRAM_CHAT_ID` salah → `python -m sniper_bot chat-id`; pastikan proses jalan (`systemctl status sniper-bot`). Bot hanya menjawab chat_id pemilik; orang lain hanya diberi tahu chat_id-nya sendiri. |
| `TELEGRAM_CHAT_ID kosong` | Kirim `/start` ke bot dulu, lalu `python -m sniper_bot chat-id`. |
| `uji-bursa` gagal "Invalid API-key, IP, or permissions" | Whitelist IP salah / izin Spot Trading belum dicentang / kunci baru belum aktif (tunggu 1–5 menit). |
| "⏭ ... dilewati: XYZ/USDT tidak ada di bursa" | Koin belum/tidak terdaftar di bursa pilihanmu (sering terjadi di bursa lokal untuk listing baru). |
| "nilai ... < minimum" | Ukuran order di bawah minimum bursa (umumnya $5–10). Naikkan `maks_usd_per_trade` atau modal. |
| Posisi tidak tertutup saat bot mati | TP limit tetap di bursa; SL & batas waktu dijalankan bot → hidupkan lagi, bot melanjutkan dari `state.json`. |
| Ingin mulai dari nol (kertas) | Hentikan bot, hapus `sniper_bot/data/state.json` (HANYA bila tidak ada posisi live), jalankan lagi. |
| Ganti bursa | Pastikan tidak ada posisi terbuka, ubah `bursa.ccxt_id` & kunci API, restart. |

## Keamanan & risiko (baca sebelum live)
- Bot tidak pernah memanggil penarikan dana; tetap gunakan kunci API **tanpa izin withdraw** + whitelist IP.
- `sniper_bot/.env`, `config.yaml`, `data/` tidak masuk git (`.gitignore`). Jangan kirim isi `.env` ke siapa pun.
- Semua angka di dokumen ini adalah **hasil uji masa lalu**, bukan janji. Rugi besar sesekali tetap terjadi (💎: 1 dari
  ±10 sinyal rugi rata −13%; terburuk −58%). Pakai modal yang siap hilang, mulai kecil.
- Bot ini terpisah dari aplikasi Android & cloud: mematikan/menghapusnya tidak mengganggu sinyal XAU/BTC di aplikasi.
