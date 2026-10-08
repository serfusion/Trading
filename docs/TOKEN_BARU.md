# Token baru rilis & chain baru: Arc, Robinhood Chain, listing Binance, airdrop ala ARB (8 Okt 2026)

Permintaan pengguna (lampiran catatan): "script untuk trade token (analisa dari tahun ke tahun) di blockchain X, beli di
bawah harga XXX dan jual di atas XXX (analisa supaya pas), cek likuiditas tiap posisi beli, slippage tidak lebih dari
X% (analisa juga) ... WETH modal $6 dapat 0,45 ETH (untung $1.100), CRCL rata-rata 2-5x, sampai mainnet Arc total
$15 ribu dari modal $200; saat mainnet harga normal, tidak bisa scalping, arbitrase sama dengan harga Robinhood ...
seperti ARB ada yang jackpot ratusan juta". Gambar di catatan (tautan com.miui.notes) tidak bisa dibuka dari sesi.

Kode: `research/chain_baru.py` (GeckoTerminal + acuan), `research/chain_onchain.py` (event Uniswap langsung dari RPC),
`research/chain_baru_uji.py` (analisis swap), `research/listing_baru.py` (listing Binance & airdrop), bot `token_bot/`.
Hasil mentah: `docs/eksternal/hasil_chain_arc.txt`, `docs/eksternal/hasil_chain_robinhood.txt`,
`docs/eksternal/hasil_listing_baru.txt`.

## Konteks yang dicek (web + data)
- **Robinhood Chain** (L2 Arbitrum milik Robinhood): mainnet publik **1 Jul 2026**, chain ID 4663, gas ETH, blok 0,1 dtk.
  Token saham "• Robinhood Token" (CRCL, NVDA, SPY, ...) diperdagangkan 24 jam di Uniswap v3/v4. Tidak untuk warga AS.
- **Arc** (L1 milik Circle): chain berjalan sejak Mei 2026 (izin terbatas), **mainnet publik 16 Sep 2026**, chain ID
  5042, gas USDC, blok 0,5 dtk. Token ARC 10 miliar sudah dicetak tetapi **belum ada keputusan dibagikan ke publik**.
- Alamat kontrak Uniswap dari halaman resmi developers.uniswap.org; alamat USDC/EURC/cirBTC Arc dari
  developers.circle.com. RPC publik kedua chain bisa diakses dari sesi (Arc maks < 10.000 blok per getLogs).
- **Token tiruan banyak sekali.** Robinhood: USDG/NVDA/WETH palsu dengan alamat mirip (awal & akhir sama). Arc: "cirBTC"
  `0x560f6b48…` dan "EURC" `0x834dcdca…` (volume GeckoTerminal terbesar!) BUKAN alamat Circle; cirBTC resmi
  `0x171a4217…`, EURC resmi `0xbef5f6d5…`. Ada juga pool "USDC/CRCL" dengan USDC palsu. Bot menolak pool yang tokennya
  tidak persis alamat daftar putih.

## Cara uji (chain baru)
- Semua event `Initialize` Uniswap v4 (dan `PoolCreated` v3 Robinhood) yang KEDUA tokennya ada di daftar resmi, lalu
  setiap `Swap` pool itu (jumlah token, harga sqrtPrice, likuiditas) + `ModifyLiquidity`.
- Robinhood: pool berisi token saham = seluruh riwayat; pool ETH/WETH/USDG = 3 hari pertama sejak pool dibuat (saat
  salah harga; pool besar ETH/USDG diarbitrase bot tiap blok). Arc: seluruh riwayat (chain baru 22 hari).
- Harga ACUAN per menit: ETH/BTC/EUR Binance (data.binance.vision), saham Twelve Data 1 menit **jam reguler NYSE saja**
  (di luar jam bursa tidak ada harga wajar → swap tidak dinilai).
- Untung tiap swap = nilai token diterima − dibayar pada harga acuan (fee pool termasuk, gas tidak). Ini untung yang
  SUDAH diambil para penukar. "Jeda" = detik sejak kejadian terakhir di pool (swap lain / likuiditas ditambah / pool
  dibuat): swap untung dengan jeda ≥ L detik berarti peluang itu terbuka ≥ L detik — bisa direbut bot yang bereaksi
  dalam L detik (perkiraan ATAS: pesaing juga bisa mempercepat diri).

## Hasil Arc (mainnet 16 Sep 2026)
Pool v4 yang kedua tokennya dari daftar: 378 (222 pernah ada swap), 125.181 swap. Untung **per aksi** (semua swap satu
transaksi & pengirim dijumlah), sebelum gas:

| Periode sejak mainnet | Token resmi (USDC, EURC, cirBTC, WETH jembatan) | CRCL Arc (penerbit tidak jelas, dinilai vs NYSE) |
|---|---|---|
| sebelum publik (Mei–15 Sep, izin terbatas) | ±$12 | $82 ribu (harga uji coba, selisih median 53%, rugi penukar −$93 ribu) |
| hari pertama (16 Sep) | **$3,9 ribu** | **$15,0 ribu** |
| hari 1–3 | $3,2 ribu | $5,6 ribu |
| hari 3–7 | $544 | $422 |
| hari 7–14 | $177 | $1,9 ribu |
| hari 14–30 | $278 | $676 |

- Selisih harga pool vs acuan (median |selisih| sebelum swap): token resmi 0,09–0,18%, CRCL 0,7–1,6% (CRCL hanya
  dinilai saat NYSE buka). Swap dengan selisih > 5%: ≤ 0,5% dari semua swap setelah hari pertama.
- **Jackpot setelah publik**: pool "USDC/USDC" (USDC asli vs antarmuka ERC-20, seharusnya 1:1) diisi pada harga salah
  → penukar pertama rugi $1.008, satu aksi bot 0,5 detik kemudian untung **$998** (17 Sep). CRCL hari pertama dijual
  ±4% di atas NYSE oleh beberapa kontrak (untung $150–1.512 per aksi, peluang terbuka 0–1.156 detik). Kasus "0,45 WETH
  seharga $6" TIDAK ditemukan di pool WETH Arc yang resmi.
- **Siapa cepat dia dapat** (untung aksi yang peluangnya terbuka ≥ L detik): hari pertama total $18,9 ribu; ≥ 2 dtk
  $14,4 ribu, ≥ 10 dtk $8,7 ribu, ≥ 60 dtk $3,0 ribu. Hari 1–3 $8,9 ribu (≥ 10 dtk $4,5 ribu). Hari 3–7 $966 (≥ 10 dtk
  $492). Hari 14–30 $955 (≥ 10 dtk $418).
- **Aturan bot** (selisih ≥ b, peluang terbuka ≥ 10 dtk; perkiraan ATAS = bila memenangkan SEMUA peluang): hari
  pertama b 1% → ±1.000 peluang/hari, median untung **$0,63** per aksi (notional median $56), ±$7,1 ribu/hari DIBAGI
  semua pemain; hari 1–3 ±$1,7 ribu/hari; hari 3–7 **$39/hari**; hari 14–30 **$28/hari**.
- Slippage aksi satu-swap yang untung: median 0,02–0,10%, P90 0,16–0,33% (untung datang dari selisih harga, bukan dari
  ukuran besar).
- Token TIRUAN (WETH/EURC/cirBTC `_a`): 123 swap besar ($0,7–5,7 juta) oleh SATU kontrak `0xb3681811…` pada 3–7 Okt.
  Per swap tampak "untung" $1,28 juta, tetapi per aksi bersihnya **$0,13** → perdagangan bolak-balik (wash) untuk
  memoles volume/likuiditas di GeckoTerminal. Tiruan dihargai 10–18% di bawah aslinya. Contoh nyata bahaya token
  beralamat mirip.

## Hasil Robinhood Chain (mainnet 1 Jul 2026)
3.846 pool resmi-resmi (v4 3.737, v3 109), **19,3 juta swap** (pool saham: seluruh riwayat; pool ETH/WETH/USDG: hari
pertama tiap pool). Dinilai 6,1 juta swap (sisanya saham di luar jam NYSE). Untung dihitung **per aksi** = semua swap
satu (transaksi, pengirim) dijumlah — tanpa itu, manuver bot "pinjam 50 WETH → jatuhkan harga → swap balik" tampak
sebagai jackpot ±$83 ribu padahal bersihnya +$317.

| Periode sejak mainnet 1 Jul | Untung aksi (kotor, sebelum gas) | Rugi penukar (aksi rugi > 5%) | |selisih| median |
|---|---|---|---|
| hari pertama | $13,2 ribu (pool ETH/USDG/WETH baru) | −$11,6 ribu | 1,6% |
| hari 1–3 | $1,7 ribu | −$4,2 ribu | 0,5% |
| hari 3–7 | $31 | −$418 | — |
| hari 7–14 (token saham mulai ramai) | $25 ribu | −$19,8 ribu | 0,16% |
| hari 14–30 | $266 ribu | −$284 ribu | 0,25% |
| hari 30–60 | $587 ribu | −$648 ribu | 0,10% |
| > 60 hari (s/d 8 Okt) | $1,25 juta | −$61 ribu | 0,13% |

- Untung kotor naik seiring volume, tetapi itu **dibagi ribuan bot dan hampir sama besar dengan kerugian penukar
  lain**. Untung BERSIH semua pelaku (aksi + dan −) = **−$1,25 juta** (fee LP). Dari 7.022 kontrak pengirim hanya
  **79 yang bersih > $1.000**; terbesar +$117 ribu dari 336 ribu aksi (rata-rata **$0,35/aksi**) = bot profesional.
- **Jackpot = kejadian, bukan rutinitas.** Hari terbaik per token (untung aksi dengan selisih ≥ 1%): HIMS 28 Agu
  **$226 ribu**, GME 23 Jul $90 ribu, MSTR 24 Jul $76 ribu, COIN 22 Jul $6,8 ribu, NVDA 27 Jul $5,5 ribu, CRCL 14 Sep
  (pekan mainnet Arc) $3,8 ribu. Selisih −40…−75% (pool tertinggal dari harga bursa). Median "jeda" 100 aksi teratas
  per token **0,1–3 detik** → direbut bot, bukan manusia.
- **CRCL** (Robinhood, jam NYSE): pekan pertama (20–26 Jul) selisih median **5,5%**; Agustus ±0,5%; untung aksi
  selisih ≥ 1% memuncak pekan 14–20 Sep (mainnet Arc) $6,4 ribu, lalu turun ke $356 (5–8 Okt). Sejak September selisih
  median **0,3% = setara fee pool 0,3%** → scalping/arbitrase vs harga Robinhood tidak tersisa. **Cocok dengan
  pengalaman pengguna.** "2–5x per trade" tidak terlihat di pool resmi saat NYSE buka (mungkin terjadi di luar jam
  bursa, di pool kecil, atau berupa akumulasi banyak trade); hati-hati pool "USDC/CRCL" dengan USDC PALSU.
- Kasus "0,45 WETH seharga $6" juga tidak ditemukan di pool WETH/ETH resmi Robinhood (hari pertama tiap pool); kasus
  sejenis yang ada: pool USDC/USDC Arc salah harga (+$998 dalam 0,5 dtk), ETH/USDG 27 Agu (+$99,7 ribu satu aksi,
  selisih −100%, jeda 0,1 dtk).
- **Pelajaran slippage**: aksi paling rugi = menukar tanpa batas slippage di pool yang sedang dijatuhkan (contoh
  WETH→NVDA $7.749 jadi ±$0; kontrak yang menukar 0,163 WETH dapat NVDA senilai sen saat bot memanipulasi harga).
- Slippage aksi satu-swap yang untung: median 0,02%, P90 0,10% setelah 30 hari; di hari pertama median 1,5–2,9%
  (pool baru tipis).
- Aturan bot (selisih ≥ b, peluang terbuka ≥ 10 dtk, perkiraan ATAS bila menang semua): hari pertama b 1% → $4,8
  ribu/hari, median $2,3/aksi; hari 14–60 b 2% → $680–920/hari (median $0,3–0,5/aksi); > 60 hari b 2% → **$171/hari**
  untuk SEMUA pelaku, median **$0,07/aksi**.

## Listing baru Binance 2017–2026 (588 token, termasuk yang sudah delisting)
Harga acuan P0 = VWAP 60 menit pertama (open candle pertama Binance sering harga lelang aneh, mis. ARB 0,5).
Median per tahun listing:

| Tahun | n | 5 mnt pertama | 1 hari | 30 hari | 90 hari | naik setelah 90 hr | sempat 2× (90 hr) | sempat 5× |
|---|---|---|---|---|---|---|---|---|
| 2019 | 66 | +14% | −5% | −27% | −27% | 30% | 17% | 2% |
| 2020 | 105 | +28% | −10% | −28% | −26% | 34% | 31% | 7% |
| 2021 | 123 | +24% | −9% | −31% | −50% | 23% | 24% | 4% |
| 2022 | 41 | +22% | −15% | −37% | −53% | 17% | 27% | 5% |
| 2023 | 54 | +18% | −7% | −18% | −35% | 30% | 15% | 4% |
| 2024 | 62 | +26% | −3% | −20% | −39% | 21% | 31% | 3% |
| 2025 | 96 | +18% | −13% | −46% | −62% | 14% | 17% | 1% |
| 2026 | 22 | +9% | −9% | −35% | −50% | 5% | 18% | 0% |

LAMA (< Okt 2021, n 273): 90 hari median −32%; BARU (≥ Okt 2021, n 315): 90 hari median **−52%**, hanya 16% naik.

Aturan beli/jual (792 kombinasi dengan n ≥ 30 di kedua periode, biaya 0,4% pulang-pergi, candle 1 jam, SL dicek dulu):
- **Beli saat listing** (jam ke-2) lalu TP/SL apa pun: BARU rata-rata −8 … −24% per trade → **jangan**.
- Beli saat tembus puncak hari-1: LAMA bagus (+23…+31%), BARU negatif → gagal.
- **Kandidat: beli limit setelah token turun ≥ 60% dari P0 dalam 30 hari pertama, TP +20%, SL −50%, maks 90 hari**:
  LAMA n 70, WR 90%, +13,2%/trade; BARU n 99, **WR 77%, +7,1%/trade** (CI90 +1,3…+12,9%), 9/9 tahun positif, biaya ×3
  masih +6,3%. Pembanding token yang SAMA dibeli di jam acak 30 hari pertama (TP/SL sama): **−11,8%** vs +9,6%.
  Tetangga parameter konsisten hanya untuk turun ≥ 60–70% (turun 10–50% → BARU negatif). Ditemukan dari 792
  kombinasi → **belum terbukti**, perlu uji maju; ±10–46 sinyal per tahun, untung kecil per trade, kalah −50% sesekali.

## Airdrop "jackpot" ala ARB
21 token airdrop yang listing Binance saat TGE (UNI, 1INCH, DYDX, ENS, OP, APT, ARB, TIA, JTO, JUP, STRK, ENA, W, ZK, ZRO,
EIGEN, ME, BERA, KAITO, LINEA, MEGA), harga relatif terhadap P0:
- Median: **5 menit pertama +31%**, 7 hari −26%, 30 hari −32%, 1 tahun **−64%**, sekarang **−91%**. Hanya 6/20 lebih
  tinggi dari P0 setelah 1 tahun; 9/21 mencapai harga tertinggi sepanjang masa di hari listing.
- Pengecualian besar: UNI (+747% dalam 180 hari, bull 2021), TIA (+697% dalam 90 hari). Sisanya turun.
- **ARB**: alokasi 625–10.250 ARB per dompet; × P0 $1,34 = $835–13.688 ≈ **Rp13–209 juta** (kurs ±Rp15.300). Itu
  "jackpot ratusan juta" — hadiah untuk pemakai Arbitrum SEBELUM snapshot, bukan hasil trading. Yang menjual di menit
  awal mendapat paling banyak; ARB sekarang −85% dari P0.
- Arc: token ARC 10 miliar sudah dicetak, **belum ada pengumuman pembagian ke publik**; Robinhood Chain tidak punya
  token. Memakai chain baru dengan harapan airdrop = spekulasi tanpa angka yang bisa diuji. Sejarah: bila suatu saat
  dapat airdrop, **jual sebagian besar di jam pertama** lebih baik daripada menahan (median).

## Jawaban untuk angka XXX dan X%
Pengguna meminta "beli di bawah XXX, jual di atas XXX, slippage tidak lebih dari X%". Dari data di atas:

| Situasi | Beli bila (XXX) | Jual bila (XXX) | Slippage maks (X%) | Kapan |
|---|---|---|---|---|
| DEX chain baru, token yang punya harga acuan (ETH, BTC, saham, stablecoin) | harga eksekusi ≤ acuan × **0,99** (≥ 1% lebih murah SETELAH fee pool + slippage + gas) | harga eksekusi ≥ acuan × 1,01, atau kembali ke acuan, TP +2% / SL −4% | **0,5%** (swap untung median 0,02–0,1%, P90 0,1–0,36%) | hari 0–3 setelah mainnet, saat pool/token BARU dibuat, saat harga bursa bergerak besar (berita) |
| Sama, tetapi > 1 pekan setelah mainnet | sedikit: peluang ≥ 1% yang terbuka ≥ 10 dtk bernilai Arc ±$28/hari, Robinhood ±$950/hari (≥ 2%: $171/hari) untuk SEMUA pelaku, median $0,02–0,20 per aksi | — | — | biarkan bot memantau `baru` saja |
| Listing CEX (Binance) | harga ≤ **0,40 ×** VWAP 60 menit pertama (turun ≥ 60%) dalam 30 hari pertama | **+20%** dari harga beli; SL −50%; maks 90 hari | pasar besar, ±0,1% | kandidat — belum terbukti |
| Dapat airdrop | — | jual sebagian besar di **jam pertama** listing (median +31% di 5 menit, −64% setelah 1 tahun) | — | — |

Saham tokenisasi: hanya saat bursa AS buka (di luar jam itu tidak ada harga wajar; risiko gap Senin pagi).
Selisih < 1% tidak sepadan: fee pool 0,05–1%, derau acuan, dan bot ber-jeda < 1 detik mengambilnya lebih dulu.

## Bot `token_bot/` (dibuat sesi ini)
Pasang: `pip install eth-abi eth-utils pyyaml` (+ `eth-account` hanya untuk mode live). Salin
`token_bot/config.example.yaml` → `token_bot/config.yaml`.

```bash
python -m token_bot cek                       # satu kali: harga wajar, selisih, slippage nyata, keputusan
python -m token_bot pantau --interval 3       # loop tiap 3 dtk, log CSV token_bot/log/, notifikasi ntfy opsional
python -m token_bot baru --jaringan arc       # pantau pool BARU (event Initialize) token daftar putih: harga awal vs wajar
python -m token_bot cari --jaringan robinhood --pool <poolId v4 | alamat pool v3>
```

- Harga eksekusi diambil dari **Quoter resmi Uniswap** (eth_call, sudah termasuk fee pool, dampak likuiditas, hook v4),
  bukan dari harga tampilan. Ukuran diperkecil (bagi dua) sampai slippage ≤ `max_slippage`; kalau $10 pun tidak muat →
  "likuiditas tipis", dilewati.
- **Cek jual-balik**: jumlah token hasil beli dikuotasi dijual lagi; rugi pulang-pergi > 2× slippage + 3% → dicurigai
  hook pajak/honeypot → dilewati.
- **Daftar putih alamat**: pool yang tokennya bukan alamat resmi persis → bot berhenti dengan pesan "alamat tiruan?".
- **Saham**: di luar jam reguler NYSE tidak ada harga wajar → tidak transaksi (bawaan `luar_jam: false`).
- **Live** (BAWAAN MATI): butuh `live.aktif: true` + `--live` + env `TOKEN_BOT_PK` (dompet khusus bersaldo kecil).
  Batas $/trade, total, trade per hari. Sebelum kirim: simulasi `eth_call` transaksi persis (batal bila revert) dan
  `amountOutMinimum` = kuotasi × (1 − max_slippage). v4 lewat Universal Router (V4_SWAP), v3 lewat SwapRouter02.
  **Belum pernah dijalankan dengan dana nyata** (sesi riset tidak punya dompet dan tidak boleh bertransaksi) → wajib
  uji nominal kecil dulu.
- Diuji: `tests/test_token_bot.py` (11 tes luring: poolId v4 dihitung ulang = id pool CRCL asli, slippage, honeypot,
  jam bursa, TP); `cek` dijalankan baca-saja pada pool asli Robinhood 8 Okt 13:05 UTC (pra-pasar): CRCL v4 $200 →
  slippage 0,16%, CRCL v3 0,30%, NVDA v3 0,05%, WETH v3 0,01%; kuotasi CRCL/USDG v4: $1.000 → 0,22%, $10.000 → 0,8%,
  $50.000 → 3,4% dari spot. Saat NYSE BUKA (8 Okt ±14:30 UTC) selisih pool vs bursa: CRCL −0,01…−0,09%, NVDA +0,02%,
  SPY +0,03%, META −0,07%, MSTR −0,32%, ETH ±0,07% → semua TUNGGU (selisih < fee + slippage), sesuai temuan riset.

## Kesimpulan jujur
1. **Pengalaman pengguna terbukti oleh data**: peluang besar di chain baru ada di **hari-hari pertama** (Arc: hari
   pertama ±$19 ribu, hari 1–3 ±$9 ribu, sesudah pekan pertama ±$1–2 ribu per PEKAN dibagi semua pelaku) dan saat
   pool/token baru dibuat atau saham bergerak besar. Sesudah itu selisih harga ≈ fee pool (CRCL 0,3%) → tidak bisa
   scalping, arbitrase sama dengan harga Robinhood.
2. **Yang mengambil jackpot adalah bot ber-jeda < 1–3 detik**, bukan manusia. Script yang memantau tiap beberapa
   detik hanya kebagian sisa (perkiraan atas: ratusan dolar per hari untuk SEMUA pelaku, median beberapa sen–$2 per
   aksi). Untung bersih seluruh pelaku negatif; hanya ±1% kontrak yang untung bersih > $1.000.
3. **WR tinggi dan untung tinggi sekaligus tidak ditemukan** untuk trading token baru setelah fase peluncuran.
   Satu-satunya aturan statistik yang lolos dua periode: beli listing Binance yang sudah turun ≥ 60% dari harga
   listing, TP +20% (WR 77–90%, +7…+13%/trade, BARU n 99) — kandidat, perlu uji maju; kerugian sesekali −50%.
4. **Jackpot ala ARB = airdrop**, hadiah bagi pemakai awal, bukan hasil trading; tidak ada kepastian Arc/Robinhood
   membagi token. Sejarah 21 airdrop: jual cepat lebih baik daripada menahan.
5. **Bahaya terbesar**: token tiruan beralamat mirip (cirBTC/EURC/WETH/USDG/NVDA palsu, pool "USDC" palsu), swap tanpa
   batas slippage (dijatuhkan bot sandwich), hook v4 berpajak/honeypot. Bot `token_bot` menolak ketiganya.
6. Tidak ada yang dipasang ke bot live XAU / cloud / aplikasi. `token_bot` berdiri sendiri, bawaan hanya sinyal; mode
   live butuh izin & pengaturan pengguna sendiri dan belum pernah diuji dengan dana nyata.
