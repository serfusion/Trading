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
Pool v4 yang kedua tokennya dari daftar: 378 (222 pernah ada swap), 125.181 swap. Untung penukar (sebelum gas):

| Periode sejak mainnet | Token resmi (USDC, EURC, cirBTC, WETH jembatan) | CRCL Arc (penerbit tidak jelas, dinilai vs NYSE) |
|---|---|---|
| sebelum publik (Mei–15 Sep, izin terbatas) | ±$12 | $82 ribu (harga uji coba, selisih median 53%) |
| hari pertama (16 Sep) | **$4,6 ribu** | **$23,7 ribu** |
| hari 1–3 | $3,5 ribu | $7,1 ribu |
| hari 3–7 | $555 | $429 |
| hari 7–14 | $186 | $1,9 ribu |
| hari 14–30 | $283 | $699 |

- Selisih harga pool vs acuan (median |selisih| sebelum swap): token resmi 0,09–0,18%, CRCL 0,7–1,6% (CRCL hanya
  dinilai saat NYSE buka). Swap dengan selisih > 5%: ≤ 0,5% dari semua swap setelah hari pertama.
- **Jackpot setelah publik**: pool "USDC/USDC" (USDC asli vs antarmuka ERC-20, seharusnya 1:1) dibuat salah harga →
  satu swap $1.034 untung **$998** (17 Sep, peluang terbuka 0,5 detik = bot). CRCL hari pertama dijual 4% di atas NYSE
  oleh beberapa alamat (untung $200–655 per swap, peluang terbuka 0–330 detik). Kasus "0,45 WETH seharga $6" TIDAK
  ditemukan di pool WETH Arc yang resmi.
- **Siapa cepat dia dapat**: hari pertama total $28,2 ribu; yang peluangnya terbuka ≥ 2 dtk $19 ribu, ≥ 10 dtk $13 ribu,
  ≥ 60 dtk $4,7 ribu. Hari 3–7: total $984 (≥ 10 dtk $487). Hari 14–30: $982 (≥ 10 dtk $434).
- **Aturan bot** (ambil swap untung bila |selisih| ≥ b dan peluang terbuka ≥ 10 dtk): hari pertama b 1% → ±1.400
  peluang/hari, median untung **$1,5** per peluang (notional median $100), total ±$12 ribu/hari DIBAGI semua pemain;
  hari 1–3 ±$2,2 ribu/hari; hari 3–7 **$39/hari**; hari 14–30 **$29/hari**.
- Slippage swap yang untung: median 0,03–0,10%, P90 0,20–0,36% (pool cukup dalam; untung datang dari selisih harga,
  bukan dari ukuran besar).
- Token TIRUAN (WETH/EURC/cirBTC `_a`): 123 swap besar ($0,7–5,7 juta) oleh SATU alamat `0xb3681811…` pada 3–7 Okt,
  "untung" $1,28 juta bila tiruan dinilai seharga aslinya — itu ilusi (tiruan diperdagangkan 10–18% di bawah aslinya
  karena memang bukan aset yang sama). Contoh nyata bahaya token beralamat mirip.

## Hasil Robinhood Chain (mainnet 1 Jul 2026)
(ISI_RH)

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
(ISI_JAWAB)

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
  $50.000 → 3,4% dari spot.

## Kesimpulan jujur
(ISI_KESIMPULAN)
