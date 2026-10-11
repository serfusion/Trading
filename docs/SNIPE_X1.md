# 🎯 Snipe token baru di chain "yang tidak banyak orang tahu" — X1 / XNT (10–11 Okt 2026)

Pertanyaan pengguna (dengan 2 screenshot bot Telegram): *"Ini bukan apk tapi bot, cari tau ini. Snipe di on chain,
dexscreener, dextools, geckoterminal … lebih bagus chain yang ga banyak orang tau, tutor merubah 1$ jadi 200$+. rugger
gada, snipe langsung dapat besar."* Screenshot: token **KMN**, "Buy 2.000000 XNT → Value 435.046481 XNT, PnL 21.652%",
Creator `CHzRiK…z6Jq`, Updated 2026-03-01 08:00:40.

Skrip: `research/snipe_x1.py` (unduh) dan `research/snipe_x1_uji.py` (analisis). Hasil mentah:
`docs/eksternal/hasil_snipe_x1.txt`. Data on-chain: `data/research/eksternal/snipe_x1/` (28 MB). Perintah:
`python -m research.snipe_x1 unduh` → `tx` → `dana` → `uji` (studi KMN: `kmn`).

**Tidak ada yang dipasang** ke bot/cloud/aplikasi. Riset ini hanya membaca data publik dan tidak memakai wallet atau private key.

## Ringkasan singkat

| Klaim tutorial | Hasil data on-chain X1 (556 token, Des 2025 – Okt 2026) |
|---|---|
| "Chain yang tidak banyak orang tahu" | **Benar sepi**: XDEX hanya 1.381 pool & ±2.200 pemegang; median pembeli pertama datang **195 dtk** setelah token dibuat (≤ 10 dtk hanya 11%) → persaingan snipe kecil |
| "$1 jadi $200+" | Pernah terjadi, tetapi **jarang**: nilai jual nyata 2 XNT pernah ≥ 200× hanya di **1%** token (±6 dari 556), itu pun bila menjual tepat di puncak. Angka "Value" bot = harga × jumlah, bukan uang yang bisa diterima |
| "Snipe langsung dapat besar" | **Median satu snipe ×0,98 (sedikit rugi); 55–60% snipe rugi**. Untung datang dari segelintir token |
| "Rugger gada" | **Salah**: 32% pembuat menarik likuiditas dalam 24 jam, 18% pembuat menjual tokennya, 53% pembuat hanya memasukkan < 50% pasokan ke pool; 14% token pembuatnya masih bisa mencetak token baru, 5% masih bisa membekukan akun pembeli (honeypot); 50% token kini "mati" (likuiditas ≤ 10% dari puncak) |
| Snipe SEMUA token baru (2 XNT, masuk 1 menit, jual jam ke-24) | Secara total **untung** dalam XNT (+429%, CI90 +219…+708%, positif di dua paruh waktu, masih +43% tanpa 20 token terbaik) — **tetapi** total seluruh 10 bulan hanya **±$2.800 dari modal $794**, dan Mei–Okt 2026 tinggal **±$200** (token baru 16–25/bulan) |
| Wallet di screenshot | Asli: `RVNFmE…` = **pembeli ke-2, 50 dtk** setelah KMN dibuat; menjual 75% → 227,8 XNT, lalu 28,3 XNT (**×128**, ±$118). Wallet ini penembak berulang dan didanai `AKqn1g…` (juga penembak); berdua: 167 posisi, modal 1.155 XNT → **+3.058 XNT** dalam ±9 bulan |

Kesimpulan jujur: di X1 memang ada **keunggulan nyata bagi yang paling cepat** (pembeli ≤ 5 menit rata-rata +91%),
karena untung itu diambil dari pembeli belakangan (masuk > 6 jam: −50%, hanya 13% wallet untung). Tetapi **pasarnya sangat
kecil** (median likuiditas puncak 50 XNT ≈ $35), **makin sepi**, koin XNT turun 84%, dan setiap snipe lebih sering rugi
daripada untung. Ini bukan "pasti $200 dari $1"; paling realistis = banyak tiket lotre kecil yang sesekali menang besar.

## 1. Studi kasus KMN (screenshot)

Mint `CzgRKzLkBP52uXAzQh8Yu8vuMk37G8YY12vYj6EthRD8`, pool XDEX `Ckz5EoXvxKgkNUUcXMfLkWkdTQphMPEzTtZMM6fvvw87`
(KMN/WXNT, biaya 0,28%). Pembuat pool `CHzRiKLDMStUvAMUJGABA2uSCfswKJN56fgWp1cFz6Jq` = "Creator" di screenshot. Seluruh
125 transaksi pool diputar ulang dari RPC. Waktu UTC.

| Waktu (1 Mar 2026) | Kejadian | XNT di pool |
|---|---|---|
| 05:59:26 | Pembuat memasukkan **1 miliar KMN (100% pasokan) + 20 XNT** — harga awal 0,00000002 XNT | 20 |
| 06:00:11 (+45 dtk) | Pembeli ke-1 `CmSnHu…` beli 2 XNT → 90,7 jt KMN | 22 |
| **06:00:16 (+50 dtk)** | **Pembeli ke-2 `RVNFmE…` beli 2 XNT → 75.587.617 KMN** ← wallet di screenshot | 24 |
| 06:04:08 | `55s27Z…` beli 0,2 XNT — **wallet yang mendanai pembuat** (kirim 1 XNT ke `CHzRiK…` 23 Feb) | 47 |
| 06:39–06:45 | `CezdNA…` beli 100 XNT, `Dfkb27…` beli 2 × 100 XNT lalu menambah likuiditas | 72 → 332 |
| 08:00:40 | Saat screenshot: harga 0,00000576 XNT × 75,59 jt = **435,05 XNT** (angka bot) | 760 |
| 08:01:50 | `RVNFmE…` jual 56,69 jt KMN (75%) → **227,8 XNT** | 532 |
| 09:12:48 | `RVNFmE…` jual 8,53 jt → 28,3 XNT (sisa 10,4 jt KMN) | 564 |
| 3 Mar 14:50 | Puncak harga 0,0000069 XNT (×350 dari harga awal) | 1.475 |
| 3 Mar 14:53–16:07 | Jual besar beruntun (`Ay6MTC…` 564 XNT, `CezdNA…`, `Dfkb27…`, `4aKC5Z…`) | 1.475 → 339 |
| 5 Mar 00:43 | `55s27Z…` (penyandang pembuat) **menarik likuiditas** 98 XNT + 164 jt KMN, lalu menjual 166 jt KMN → 70 XNT | 339 → 171 |
| 10 Okt | Pool tinggal 29,25 XNT + 709 jt KMN; menjual 75,59 jt KMN sekarang = **2,77 XNT (≈ $0,45)** | 29 |

1. **"Value 435 XNT" = harga terakhir × jumlah token** (cocok sampai 6 desimal). Pada 08:00:40 pool berisi 760 XNT;
   menjual 75,59 jt KMN sekaligus memberi **±276 XNT (−37%)**. Yang benar-benar diterima pemiliknya: 227,8 + 28,3 =
   **256 XNT dari 2 XNT** (XNT ≈ $0,46 → modal ±$0,93 jadi ±$118). Screenshot asli, "$200" angka di atas kertas.
2. **Kecepatan menentukan.** Simulasi beli 2 XNT di KMN (bagian 4): masuk sebelum siapa pun → puncak 327 XNT; masuk
   menit ke-1 → 263; menit ke-5 → 96; menit ke-30 → 48.
3. **Zero-sum.** Untung-rugi semua wallet KMN (XNT masuk-keluar + sisa token): pemenang `Ay6MTC…` +310 (+95 lewat
   `4aKC5Z…` penerima tokennya), `RVNFmE…` +254, `4irxYN…` +208, `55s27Z…` +168, `CmSnHu…` +99; yang kalah `Dfkb27…` −481,
   `Bw6kUG…` −201, `CRXm7o…` −139, `By4C8P…` −116, `B9Dc4z…` −108, `DeqDLp…` −106. **Jumlah semuanya −13 XNT** (biaya DEX).
4. **Jejak orang dalam**: wallet pembuat hanya 6 transaksi seumur hidup, didanai `55s27Z…` yang ikut membeli dan 4 hari
   kemudian menarik likuiditas.
5. **XNT ikut turun**: ±$0,46 (1 Mar) → $0,17 (9 Okt). 256 XNT hari ini ±$44.

## 2. Seberapa besar "pasar" X1

- 1.381 pool XDEX; 556 peluncuran token (pool pertama tiap token, berpasangan WXNT, tanpa aset jembatan .X/stabil).
  Per bulan: Des 8 · **Jan 216** · Feb 137 · Mar 30 · Apr 67 · Mei 20 · Jun 16 · Jul 25 · Agu 16 · Sep 18 · Okt (9 hari) 3.
- XNT di pool saat dibuat: median 11 XNT; puncak 24 jam median **50 XNT (≈ $35)**; ≥ 1.000 XNT hanya 5,8%.
- Pembeli lain dalam 24 jam: median 3 wallet; 16% token tanpa pembeli sama sekali; 55% ≤ 3 pembeli.
- Pembeli pertama (bukan pembuat): median **195 dtk** setelah pool dibuat; ≤ 10 dtk 11%, ≤ 60 dtk 32%.
- Pool XNT/USDC.X (jalan keluar ke dolar) hanya 23.036 WXNT + 3.882 USDC.X (±$7.800). XNT: $1,09 (2 Jan) → $0,17 (9 Okt).

## 3. Pemain NYATA (bukan simulasi) — untung/rugi wallet di 24 jam pertama

XNT masuk-keluar + sisa token dinilai seolah **dijual bersamaan** ke pool di akhir jam ke-24 (pembuat tidak dihitung).

| Masuk setelah pool dibuat | Posisi | Modal | Untung bersih | Wallet untung | ≥ 10× |
|---|---|---|---|---|---|
| ≤ 1 menit | 271 | 3.884 XNT | **+91%** | 56% | 9,2% |
| 1–5 menit | 289 | 4.683 XNT | **+91%** | 60% | 9,0% |
| 5–60 menit | 1.078 | 36.624 XNT | +29% | 44% | 3,3% |
| 1–6 jam | 1.172 | 36.157 XNT | **−27%** | 26% | 2,1% |
| > 6 jam | 1.138 | 32.539 XNT | **−50%** | 13% | 0,9% |

- 41 wallet yang ≥ 5 kali menjadi 3 pembeli pertama (bot/penembak): gabungan modal 3.436 XNT → **+126%**, tetapi
  12 wallet teratas hanya untung di **33–64%** peluncurannya, dan sebagian hampir impas (`DX38UJ…` +20 XNT dari 296; `48GFaq…` −3 dari 132).
- 15% peluncuran punya pembeli awal yang **terhubung ke pembuat** (didanai pembuat / mendanai pembuat / sumber dana sama).

## 4. Simulasi "sisip": beli 2 XNT (≈ $1) di setiap token baru

Cara: transaksi kita disisipkan ke urutan transaksi asli, lalu transaksi orang lain diputar ulang dengan jumlah masuk
yang sama (beli = XNT masuk, jual = token masuk, tambah/tarik likuiditas = proporsi pool). Validasi: tanpa sisipan,
putar ulang sama dengan cadangan on-chain (selisih maks 0,07%). Biaya DEX 0,28–0,30% + **bot 1% per sisi**. Aturan
ditetapkan sebelum melihat hasil.

| Masuk | Nilai jual pernah ≥ 2× | ≥ 10× | ≥ 200× | Median per snipe (jual jam 24) | Snipe rugi | ROI total jual jam 24 | TP 10× | TP 2× |
|---|---|---|---|---|---|---|---|---|
| sebelum siapa pun | 42% | 15% | 1% | ×0,98 | 55% | +518% | +198% | +72% |
| 1 menit | 38% | 13% | 1% | ×0,98 | 58% | +429% | +160% | +45% |
| 5 menit | 35% | 12% | 1% | ×0,98 | 61% | +220% | +168% | +78% |
| 30 menit | 26% | 8% | 0% | ×0,98 | 68% | +89% | +115% | +57% |

- Masuk 0 dan 10 detik hampir sama → di X1 belum ada perang bot di detik pertama (beda dengan Solana).
- Ketahanan (masuk 1 menit): bootstrap CI90 jual jam 24 **+219…+708%**; Des–14 Feb +274%, 15 Feb–Okt +709%;
  tanpa 5/10/20 token terbaik +177% / +109% / +43%. TP 10×: +160% (CI90 +127…+196%), tanpa 20 terbaik +93%.
  Pool awal ≥ 5 XNT saja (sisipan kita ≤ 40% pool): tetap positif.
- Modal 10 XNT per token → ROI turun (masuk 1 menit, jual jam 24: +168%) karena pool kecil: **tidak bisa diperbesar**.
- Jual 1 transaksi terlambat (TP 10×): +147% vs +160%. "Tahan sampai sekarang": median ×0,07, 80% rugi; dalam
  dolar hanya +58% (XNT turun).
- **Dalam dolar per bulan** (masuk 1 menit, jual jam 24, semua token): Des $61 · Jan $1.120 · Feb $492 · Mar $111 ·
  Apr $837 · **Mei −$12 · Jun $2 · Jul $107 · Agu $7 · Sep $60** · Okt $36 → total ±$2.800 dari modal $794;
  **Mei–Okt hanya ±$200**.

Batas simulasi: diasumsikan orang lain tetap membeli/menjual sama walau ada wallet kita (di pool 1–10 XNT, wallet kita
bisa memegang porsi besar dan membuat pembeli lain mundur); jendela putar ulang 24 jam; tidak ada slippage antrian,
gagal transaksi, atau pembekuan akun oleh pembuat (5% token masih punya freeze authority; 84% token memakai Token-2022
tetapi hampir semua hanya untuk metadata, pajak transfer 1,6%, permanent delegate/transfer hook 0%).
Tren token baru menurun, jadi hasil Jan–Apr belum tentu terulang.

## 5. Sumber data & cara kerja bot seperti di screenshot

| Sumber | X1 | Catatan |
|---|---|---|
| DexScreener API (gratis) | **tidak mendukung X1** | pencarian "XNT"/"WXNT" hanya memberi pasangan Solana |
| GeckoTerminal API (gratis, sering 429) | ada (`x1-network`, DEX `xdex`) | **tidak semua pool terindeks** — KMN 404 |
| DEXTools API | berbayar (403 tanpa kunci) | tidak dicek |
| pump.fun | **tidak ada di X1** | hanya Solana (alamat …pump) |
| XDEX API (`api.xdex.xyz`) | daftar 721 token, kutipan jual (`swap/quote`), grafik | volume grafik KMN 9–84× lebih besar dari on-chain |
| degen.fyi (launchpad kurva bonding ala pump.fun) | `app.degen.fyi/api/tokens/ungraduated?network=4` | 127 token belum lulus |
| **RPC `rpc.mainnet.x1.xyz`** | **sumber kebenaran** | gratis, 300 permintaan/5 dtk, 150 rb/jam; kompatibel Solana (bisa batch JSON-RPC) |

XDEX = fork Raydium CP-Swap (program `sEsYH97wqmfnkzHedjNcw3zyJdPvUmsa9AixhS4b4fN`, akun pool 637 byte, biaya 0,28%/0,30%).
Harga & likuiditas yang benar = **saldo dua vault pool**, nilai jual = rumus x·y=k (bukan harga × jumlah). Pengamatan
pengguna "DexScreener kadang harga & likuiditas sesat" juga terlihat di X1 (agregator kosong/salah). Bot snipe bekerja:
pantau pool baru (getProgramAccounts / getSignaturesForAddress program XDEX), beli secepatnya, tampilkan "Value", tombol Sell.

## 6. Risiko di luar angka

- **Bot Telegram snipe memegang private key** (wallet dibuat/diimpor di bot) → admin/peretas bisa menguras dana; banyak
  "tutorial $1 → $200" adalah corong referral (biaya bot ±1%/transaksi) atau skrip penguras wallet. Jangan menempel seed
  phrase/private key ke bot, skrip, atau situs yang tidak bisa diaudit; pakai wallet terpisah berisi kecil.
- **Kapasitas kecil & makin sepi**: untung seluruh pasar Mei–Okt ±$200 untuk "snipe semua". Bila lebih banyak bot masuk,
  untung pembeli awal dibagi (zero-sum) dan keunggulan "chain sepi" hilang.
- **Likuiditas keluar**: jual ke pool kecil menjatuhkan harga; XNT → USD lewat pool ±$7.800.
- **Koin XNT** turun 84% sejak Januari — untung dalam XNT bisa hilang dalam dolar.
- **Solana/pump.fun** jauh lebih ramai: menurut laporan Solidus Labs (lewat The Defiant), ±98,6% token pump.fun berakhir
  pump-and-dump/rug, dan hanya ±0,6–1,4% token yang "lulus" kurva. Perang bot di detik pertama (Jito, bundle pembuat)
  di sana belum diuji di riset ini.

## 7. Screenshot lain: laporan bot sinyal futures (`report_bind`)

"10 sinyal hari ini, 4 menang / 2 kalah, +8R" = **satu hari**, tidak bisa membuktikan apa pun (varians satu hari
sinyal R:R 1:2,5 sangat besar). Butuh riwayat ≥ 100–200 sinyal berbulan-bulan (waktu entry, SL, TP) untuk diuji seperti
sinyal 💰 sendiri (`docs/VERIFIKASI.md`: +0,2–0,3R/sinyal jangka panjang).

## 8. Status & pilihan berikutnya (menunggu keputusan pengguna)

Tidak ada yang dipasang. Bila ingin lanjut, urutan aman:
1. **Uji maju tanpa uang** (paper): pemantau pool baru XDEX lewat RPC yang mencatat "beli 2 XNT di menit 1, jual
   jam 24 / TP 10×" + nilai jual nyata, 1–2 bulan, lalu dibandingkan dengan angka riset di atas.
2. Bila uji maju tetap positif: wallet terpisah dengan modal kecil, tanpa memberikan private key ke pihak ketiga
   (perlu izin eksplisit — menyangkut uang dan kunci wallet).
3. Riset yang sama untuk Solana pump.fun (persaingan bot jauh lebih ketat; butuh RPC/arsip yang lebih kuat).
