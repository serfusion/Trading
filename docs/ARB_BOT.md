# Bot arbitrase token baru (gaya screenshot wetharb/circarb) — 9 Okt 2026

Permintaan pengguna: bot Telegram seperti dua screenshot (`wetharb`, `circarb`) yang membeli token baru di chain baru
saat harganya jauh di bawah "harga wajar" lalu menjualnya mahal — dengan tombol Saldo · Harga · Log · Tx · BUY ON/OFF ·
STOP · RESTART. Dipisah dari bot XAU (aplikasi/cloud/`sniper_bot`).

Kode: `token_bot/` (bot kontrol `pantau_bot.py` + `tele.py`, memakai `strategi.py`/`dex.py`/`acuan.py`).
Perintah: `python -m token_bot bot`. Tes: `tests/test_token_bot.py`.

**Bot ini TIDAK mengirim transaksi nyata** — tidak memakai private key, tidak menandatangani apa pun. Ia memantau,
menghitung, dan mengabari; eksekusi (beli, tebus) kamu lakukan sendiri di dompetmu. Modul transaksi lama
(`eksekusi.py`, `pantau --live`) **dihapus 9 Okt** karena hasil review: jalur itu bisa mengirim order dua kali saat
status transaksi tidak pasti, dan menjual otomatis di DEX bertentangan dengan jalur untung yang sebenarnya (tebus).

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
- **Peluang BELI** bila untung **BERSIH** ≥ `beli_bawah`. Dua angka dilaporkan:
  - **diskon** = harga acuan ÷ harga beli − 1 (sudah termasuk fee pool, slippage, gas) — ini baru SATU ARAH;
  - **bersih** = diskon dikurangi biaya KELUAR: jual balik di DEX (fee + dampak sisi jual pool saat ini), atau untuk
    token jembatan (`tebus_manual: true`) tebus 1:1 dikurangi `biaya_tebus` (1% Arc↔Robinhood).
  Ukuran diperkecil otomatis sampai slippage ≤ `max_slippage`; cek **jual-balik** (honeypot/pajak) sebelum sinyal.
- **Token jembatan (`tebus_manual`)**: keluar lewat **tebus manual** di situs/kontrak jembatan, bukan jual DEX —
  menjual di pool tipis yang sama hanya mengembalikan diskon yang sama (itulah sebabnya pemegang lain menjual murah).
  Bot tidak memberi sinyal JUAL untuk posisi ini.
- Token biasa: posisi kertas ditutup bila TP / SL / harga kembali ke acuan.
- Pool **di atas** acuan ditandai `INFO_PREMI` (informasi saja): menjual mahal butuh stok token, bot tidak short.
- **Jalur DEX saja (tanpa tebus) secara historis RUGI untuk bot ritel**: di Robinhood 1 Jul–24 Sep, episode diskon
  ≥ 5% yang tertangkap bot berjeda 3 detik = **−$377 total** (jeda 1 dtk +$810, 5 dtk −$979;
  `docs/eksternal/hasil_arb_latensi.txt` bagian 5); 25 Sep–9 Okt hanya ±$11–25 untuk semua jeda.
  Satu-satunya pola untung yang terbukti adalah **diskon token jembatan + tebus** di jendela pra-publik.

## Dua mode (`mode:` di config)
| Mode | Yang terjadi |
|---|---|
| `pantau` (bawaan) | **Mengabari** peluang ke Telegram (maks 1 kabar/pasangan per `jeda_kabar` detik). Kamu yang memutuskan & mengeksekusi di dompetmu. |
| `kertas` | Simulasi uang palsu (`modal_kertas_usd`) di harga kuotasi; 🅰 BUY ON untuk mengaktifkan. Token jembatan disimulasikan langsung DITEBUS 1:1 − biaya (anggapan optimistis: jembatan membayar penuh & tepat waktu). |

Mode lain (mis. `live`) ditolak saat start.

Tombol Telegram (persis screenshot): **💰 Saldo · 📈 Harga · 📄 Log · 🧾 Tx · 🅰 BUY ON/OFF · ⏹ STOP · 🔄 RESTART**.

## Langkah menjalankan
1. **Server 24 jam** di region yang bisa mengakses RPC chain (lihat `docs/SNIPER_TELEGRAM.md` Langkah 0; hindari AS
   untuk data Binance).
2. Pasang: `pip install -r sniper_bot/requirements.txt` + `pip install eth-abi eth-utils`.
3. Bot Telegram: buat di @BotFather, salin token. `cp token_bot/.env.example token_bot/.env && chmod 600 token_bot/.env`,
   isi `TELEGRAM_TOKEN`. Jalankan `python -m token_bot chat-id` (setelah /start ke bot) → isi `TELEGRAM_CHAT_ID`.
4. Config: `cp token_bot/config.example.yaml token_bot/config.yaml`, biarkan `mode: pantau`. Isi daftar `pasangan`
   dengan pool chain targetmu. **Alamat token harus RESMI** (daftar putih berdasar alamat; banyak token tiruan pakai
   simbol sama — di Robinhood ada 5.327 token tiruan bersimbol saham/WETH/USDG).
5. Uji: `python -m token_bot cek` (tabel harga/slippage/keputusan sekali jalan), lalu `python -m token_bot bot`
   (mode pantau). Pantau pesan "🅰 PELUANG BELI …" beberapa hari. Perhatikan angka **bersih**, bukan diskon.
6. Mau simulasi: ubah `mode: kertas`, restart, tekan 🅰 BUY ON di Telegram.
7. Eksekusi nyata = **manual** di dompetmu (dompet terpisah bersaldo kecil). Ingat: peluang di pool ramai biasanya
   sudah hilang < 1 detik setelah muncul — kabar bot adalah alat pantau, bukan jaminan harga masih ada.

Memantau pool **baru**: `python -m token_bot baru --jaringan <chain>` mengabari saat pool token daftar putih dibuat
dengan harga jauh dari wajar (kasus "0,45 ETH seharga $6").

## Keamanan
- Bot **tidak memegang private key** dan tidak bisa memindahkan dana. Jangan pernah menaruh private key di `.env`.
- Perintah Telegram hanya dari **chat pribadi** dengan `TELEGRAM_CHAT_ID` (grup & orang lain diabaikan).
- Harga dari **kuotasi nyata** Quoter Uniswap (`eth_call`, baca-saja).
- State per mode **terpisah** (`token_bot/data/<mode>/`); posisi kertas tidak terbawa ke mode pantau. Satu proses saja
  (`bot.lock`). Rahasia (token Telegram, kunci Twelve Data, **URL RPC** yang bisa memuat kunci API) **disensor** dari
  pesan galat & log — galat RPC hanya menyebut nama host. `.env` tidak masuk git.

## Risiko (baca sebelum mengeksekusi manual)
- **Jendela sudah lewat di Arc & Robinhood.** Menjalankan bot sekarang di dua chain itu = hampir tidak ada peluang
  (receh, diperebutkan bot < 1 dtk). Bot berguna di **chain/jembatan baru berikutnya** yang masih pra-publik.
- **Token tiruan**: banyak token beralamat/bersimbol mirip yang tak bernilai atau tak bisa dijual. Daftar putih alamat
  + cek honeypot mengurangi, tidak menghapus.
- **Likuiditas satu sisi**: pool token baru sering hanya berisi token (dinding jual) → "murah" tak bisa dijual balik.
- **Risiko kustodian jembatan**: penebusan 1:1 bergantung satu dompet operator yang bisa berhenti membayar / pause.
- **Persaingan & latensi**: bot institusional bereaksi < 0,1 detik; bot RPC biasa (1–3 dtk) kalah di pool ramai.
- Semua angka = hasil masa lalu, **bukan janji**. Pakai dana yang siap hilang, mulai dari mode pantau.
