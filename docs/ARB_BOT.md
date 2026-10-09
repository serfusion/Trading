# Bot arbitrase token baru (gaya screenshot wetharb/circarb) — 9 Okt 2026

Permintaan pengguna: bot Telegram seperti dua screenshot (`wetharb`, `circarb`) yang membeli token baru di chain baru
saat harganya jauh di bawah "harga wajar" lalu menjualnya mahal — dengan tombol Saldo · Harga · Log · Tx · BUY ON/OFF ·
STOP · RESTART. Dipisah dari bot XAU (aplikasi/cloud/`sniper_bot`).

Kode: `token_bot/` (bot kontrol `pantau_bot.py` + `tele.py`, memakai `strategi.py`/`dex.py`/`eksekusi.py`/`acuan.py`
yang sudah ada). Perintah: `python -m token_bot bot`. Tes: `tests/test_token_bot.py`.

## Yang ditemukan di screenshot kamu (bukti on-chain)
Kedua bot itu saya lacak di chain **Arc** (`docs/eksternal/hasil_arb_cari.txt`, 21/21 transaksi cocok persis):
- **circarb** jalan Sabtu 12 Sep 2026, **wetharb** Minggu 13 Sep — **3–4 hari sebelum Arc dibuka untuk publik**.
- Token WETH/CRCL/NVDA di Arc saat itu adalah **token jembatan dari Robinhood Chain** yang bisa **ditebus 1:1** (biaya
  1%). Banyak orang menjualnya 30–97% di bawah harga aslinya di pool yang sangat tipis. Bot membelinya murah lalu
  menebusnya penuh. Bukti cerita kamu: wetharb beli 0,441 WETH seharga **$3**, lalu grup menebus 0,45 WETH jadi
  **0,4455 ETH ≈ $1.107** di Robinhood.
- Untung seluruh grup ±**$7.600 dalam 10 hari** (modal tunai per bot hanya $40–180). Pesaing terbesar ±$90 rb.
- **Begitu Arc publik (15–16 Sep), peluang hilang**: harga kembali ke ±3% dari wajar. Sisa peluang di Arc sekarang
  **±$20–65/hari untuk SEMUA pelaku** (sejak 1 Okt ±$21/hari), direbut bot < 1 detik (`hasil_arb_latensi.txt`).
- Di Robinhood Chain **pola ini tidak ada** sejak mainnet (token dicetak langsung penerbit, bukan jembatan;
  pool utama dalam) — diskon besar hanya muncul sesaat dari kesalahan likuiditas dan ditutup bot < 0,1 detik.

**Kesimpulan jujur:** teknik ini **hanya menghasilkan di jendela peluncuran chain/jembatan BARU yang masih pra-publik**.
Itu kejadian langka yang tidak bisa dijadwalkan, dengan risiko besar (lihat bagian Risiko). Bot ini dibuat supaya kamu
**siap** saat jendela seperti itu muncul lagi — bukan mesin uang harian.

## Apa yang dilakukan bot
- Memantau daftar **pasangan pool** (`config.yaml`) dan membandingkan harga pool (kuotasi **nyata** dari Quoter
  Uniswap, sudah termasuk fee + slippage) dengan **harga acuan** (harga wajar): ETH/BTC/EUR dari Binance, token saham
  dari Twelve Data (hanya **jam bursa AS**; di luar itu acuan "basi" → tidak transaksi).
- **BELI** bila harga pool jauh **di bawah** acuan (ambang `beli_bawah`), ukuran diperkecil otomatis sampai slippage
  ≤ `max_slippage`; cek **jual-balik** (honeypot/pajak) sebelum beli. **JUAL** bila harga **di atas** acuan / kena
  TP / SL / kembali ke acuan.
- Bot **tidak menebus lewat jembatan** (leg untung utama di screenshot). Menebus butuh kontrak kustodian satu dompet
  — terlalu berisiko untuk diotomatiskan. Leg tebus kamu lakukan **manual** di situs jembatan. Tanpa tebus, bot hanya
  mengandalkan selisih antar-pool / jual premi, yang jauh lebih kecil.

## Tiga mode (`mode:` di config)
| Mode | Yang terjadi |
|---|---|
| `pantau` (bawaan) | Hanya **mengabari** peluang ke Telegram. Tidak ada transaksi. Paling aman — mulai dari sini. |
| `kertas` | Simulasi: saldo & posisi palsu diisi di harga kuotasi. Tidak menyentuh dana. BUY ON untuk mengaktifkan. |
| `live` | Transaksi **nyata** lewat dompet bot. BAWAAN MATI. Butuh `live.aktif: true` + env `TOKEN_BOT_PK`. Auto-beli hanya setelah **🅰 BUY ON** (konfirmasi sekali). Batas keras `maks_usd_per_trade`/`maks_total_usd`/`maks_trade_per_hari` selalu berlaku. |

Tombol Telegram (persis screenshot): **💰 Saldo · 📈 Harga · 📄 Log · 🧾 Tx · 🅰 BUY ON/OFF · ⏹ STOP · 🔄 RESTART**.

## Langkah menjalankan
1. **Server 24 jam** di region yang bisa mengakses RPC chain (lihat `docs/SNIPER_TELEGRAM.md` Langkah 0; hindari AS
   untuk data Binance).
2. Pasang: `pip install -r sniper_bot/requirements.txt` + `pip install eth-abi eth-utils eth-account` (mode live).
3. Bot Telegram: buat di @BotFather, salin token. `cp token_bot/.env.example token_bot/.env && chmod 600 token_bot/.env`,
   isi `TELEGRAM_TOKEN`. Jalankan `python -m token_bot chat-id` (setelah /start ke bot) → isi `TELEGRAM_CHAT_ID`.
4. Config: `cp token_bot/config.example.yaml token_bot/config.yaml`, biarkan `mode: pantau`. Isi daftar `pasangan`
   dengan pool chain targetmu. **Alamat token harus RESMI** (daftar putih berdasar alamat; banyak token tiruan pakai
   simbol sama — di Robinhood ada 5.327 token tiruan bersimbol saham/WETH/USDG).
5. Uji: `python -m token_bot cek` (tabel harga/slippage/keputusan sekali jalan), lalu `python -m token_bot bot`
   (mode pantau). Pantau pesan "🅰 PELUANG BELI …" beberapa hari.
6. Mau simulasi: ubah `mode: kertas`, restart, tekan 🅰 BUY ON di Telegram.
7. Mau live (risiko sendiri): buat dompet **baru khusus bot**, isi saldo kecil (USDC/USDG untuk gas & modal), set
   `live.aktif: true` + batas kecil, `TOKEN_BOT_PK` di `.env`, `mode: live`, restart, 🅰 BUY ON (konfirmasi).

Memantau pool **baru**: `python -m token_bot baru --jaringan <chain>` mengabari saat pool token daftar putih dibuat
dengan harga jauh dari wajar (kasus "0,45 ETH seharga $6").

## Keamanan order (sama dengan `sniper_bot`)
- Perintah Telegram hanya dari **chat pribadi** dengan `TELEGRAM_CHAT_ID` (grup & orang lain diabaikan).
- Transaksi dikuotasi & disimulasikan (`eth_call`) sebelum dikirim; `amountOutMinimum` = kuotasi × (1 − slippage) →
  kalau harga lari, transaksi **gagal**, bukan rugi besar.
- **Status tidak pasti** (transaksi terkirim tetapi receipt tak terbaca / timeout): bot **STOP + BUY OFF**, kirim 🚨,
  **tidak** mengulang. Kamu cek explorer/dompet, lalu `/beres` dan 🔄 RESTART.
- State mode kertas & live **terpisah** (`token_bot/data/<mode>/`); posisi tidak terbawa antar mode. Satu proses saja
  (`bot.lock`). Rahasia (private key, token) **disensor** dari pesan galat & log. `.env` tidak masuk git.

## Risiko (baca sebelum live)
- **Jendela sudah lewat di Arc & Robinhood.** Menjalankan bot sekarang di dua chain itu = hampir tidak ada peluang
  (receh, diperebutkan bot < 1 dtk). Bot berguna di **chain/jembatan baru berikutnya** yang masih pra-publik.
- **Token tiruan**: banyak token beralamat/bersimbol mirip yang tak bernilai atau tak bisa dijual. Daftar putih alamat
  + cek honeypot mengurangi, tidak menghapus.
- **Likuiditas satu sisi**: pool token baru sering hanya berisi token (dinding jual) → "murah" tak bisa dijual balik.
- **Risiko kustodian jembatan**: penebusan 1:1 bergantung satu dompet operator yang bisa berhenti membayar / pause.
- **Persaingan & latensi**: bot institusional bereaksi < 0,1 detik; bot RPC biasa (1–3 dtk) kalah di pool ramai.
- Semua angka = hasil masa lalu, **bukan janji**. Pakai dana yang siap hilang, mulai dari mode pantau.
