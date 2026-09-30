# Entry di Detik Pertama Setelah Berita (30 Sep 2026)

Permintaan pengguna: *"Yang saya perlukan adalah detik pertama setelah news keluar. Banyak orang di seluruh dunia
profit dari detik awal. 15 menit setelahnya biarkan saja karena ini jangka pendek; bahkan 1–5 menit akan saya close
jika sudah profit."*

Riset lama (`research/news_trade.py`, `docs/RISET_DATA_EKSTERNAL.md` §15) masuk **15 menit setelah rilis**
(candle M15), jadi detik-detik pertama belum pernah diuji. Di sini dipakai data **tick** (per milidetik).

`python -m research.news_detik [XAU|BTC]` → `docs/eksternal/hasil_news_detik_{xau,btc}.txt` +
`cloud/api/detik.json` (dibaca kartu 🎯, pengingat ⏱️, dan tab Tanya).

## Ringkasan

> **Pembaruan (tick asli Exness, broker pengguna — bagian 3b):**
> - Di feed **Exness (XAUUSDc, akun Cent)**, **order pending Buy Stop & Sell Stop ±$1** yang dipasang 5 detik
>   sebelum rilis, ditambah aturan pengguna, positif untuk **NFP: +$3,18 per 0,01 lot** (slippage $0,30; 130 rilis
>   2015–2026, 83% tahun positif) dan CPI (+$2,21).
> - Tetapi di feed **Dukascopy**, cara yang sama pada rilis yang sama **rugi (−$1,87)**, dan untungnya terkumpul
>   di 2021–2026. Jadi **belum terbukti**. Langkah berikutnya: uji maju dengan lot minimum sambil mencatat harga
>   terisi nyata.
> - BTC dengan spread asli Exness: **tidak ada cara yang untung**.

- **Yang benar:** emas memang bergerak besar di detik-detik awal. Median gerak 5 detik pertama ±$3,3 (5 tahun
  terakhir; NFP ±$5,5, CPI ±$5,7). Spread melebar dari ±$0,5 menjadi ±$0,9–1,1 di detik pertama.
- **Siapa yang untung:** hanya yang tahu angka Act vs Cons **dalam 1 detik** dan langsung masuk searah kejutan.
  "Ikut kejutan di detik ke-1" + aturan Anda (tutup menit 1–5 bila profit, maks 15 menit): 992 rilis, menang 79%,
  +$0,69 per 0,01 lot, positif 17/17 tahun. Tetapi dengan slippage $0,30 dan eksekusi 2 detik hasilnya **−$0,15**.
  Kecepatan itu hanya dimiliki mesin dengan feed berita berbayar, bukan manusia yang membaca ForexFactory.
- **Cara manual (aturan Anda)** – ikut lonjakan di detik ke-5, reaksi 2 detik, tutup menit 1–5 bila profit: menang
  65% tetapi **rata-rata −$0,59 per 0,01 lot** (450 rilis, hanya 13% tahun positif). Order pending Buy/Sell Stop
  ±$2: −$0,50. Win rate tinggi dari "tutup begitu profit" menutupi kerugian besar saat harga berbalik.
- **BTC:** bergerak jauh lebih pelan (±0,05% dalam 5 detik). Ada kecenderungan "ikut arah" setelah CPI, tetapi
  sebagian besar untungnya dari tahun 2022 (rapuh).
- **Dipasang di aplikasi 3.13 (informasi, bukan saran entry):** pengingat ⏱️ 1 menit sebelum setiap berita USD
  bintang 3, baris ⏱️ di kartu 🎯 dengan angka per berita, dan jawaban Tanya "detik pertama". Aplikasi tidak membuka
  order.


## 1. Data

- **XAU**: tick BID/ASK Dukascopy (`datafeed.dukascopy.com`, file per jam), 2 menit sebelum sampai 16 menit sesudah
  rilis. Spread di data ini **ikut melebar saat berita**, jadi biaya detik pertama terbayar apa adanya.
  Server Dukascopy membatasi laju (±2–4 file/menit), jadi unduhan bertahap. Status per 30 Sep:
  - NFP, CPI, FOMC: lengkap (638/638 file);
  - PPI, Retail, GDP, PCE, ADP, JOLTS, ECI: lengkap (714/714);
  - ISM & Claims: 208/1.205 file; rilis bintang 3 lain: baru mulai.

  Uji di bawah memakai **1.260 rilis**: CPI 184, NFP 171, ADP 167, PPI 157, Retail 127, FOMC 113, GDP 106,
  Claims 78, ISM 54, PCE 52, JOLTS 35, dan lainnya. Datanya di repo (`data/`); unduhan dilanjutkan di sesi berikutnya.
- **BTC**: kline 1 detik BTCUSDT spot Binance (`data.binance.vision`), 2018–2026, **semua** rilis data USD bintang 3
  (1.190 rilis). Tidak ada bid/ask, jadi harga = close tiap detik, dengan spread **diasumsikan** 0,03%
  (asumsi riset BTC lain di repo ini). Melebarnya spread BTC di broker saat berita **tidak** tercermin; untuk itu ada
  uji stres (+0,05%).
- **Kalender**: ForexFactory 2010 – Jan 2026 (dengan Act & Cons), ditambah NFP/CPI Feb–Sep 2026 dari tanggal rilis
  FRED dan FOMC 2026 (tanpa Act/Cons).
- **Cek jam**: di XAU, 84% rilis punya gerak 60 detik sesudah jam rilis > 3× menit tenang sebelumnya. Median lonjakan pertama terjadi ±1,3 detik setelah jam rilis.
- **Tidak bisa dipakai**: arsip tick Exness (`ticks.ex2archive.com`, broker pengguna) diblokir kebijakan jaringan
  lingkungan riset (403). Bila host itu dibuka di pengaturan environment, uji bisa diulang dengan spread asli Exness.

## 2. Aturan yang diuji (ditetapkan sebelum melihat hasil)

- Keputusan diambil di detik ke-d setelah rilis (d = 1, 2, 5, 10, 30) hanya dari data yang sudah ada saat itu.
  Order sampai di server setelah **latensi** 0,5 detik (cepat) atau 2 detik (manual), lalu terisi di tick
  berikutnya: **ASK untuk BUY, BID untuk SELL**, plus slippage tambahan $0 / $0,30 / $1 per ons.
- Arah masuk:
  - **KEJUTAN**: ikut kejutan Act vs Cons (data lemah untuk USD → BUY emas). Butuh angka Act dalam d detik.
  - **GERAK**: ikut lonjakan. Bila harga sudah bergerak ≥ $1/$2/$3 dari harga sebelum rilis, masuk searah.
  - **LAWAN**: kebalikan GERAK (fade).
  - **STRADDLE**: Buy Stop & Sell Stop dipasang 5 detik sebelum rilis di ±$1/$2/$3. Yang tersentuh terisi di tick
    pertama yang melewati level. Loncatan harga = slippage nyata. Yang lain batal.
- Cara keluar (dihitung di BID untuk BUY / ASK untuk SELL):
  - **aturan pengguna**: di menit ke-1, 2, 3, 4, 5 tutup bila sudah profit; bila belum, tutup paksa di menit 15;
  - tahan 1 / 5 / 15 menit; TP $1 / $3; semua juga dengan SL darurat $5.
- BTC memakai satuan 0,05% harga: ambang "$1/$2/$3" = 0,05/0,10/0,15%, SL "$5" = 0,25%.
- **Konsisten** bila: rata-rata > 0 di LAMA (< Okt 2021) **dan** BARU (5 tahun terakhir), ≥ 60% tahun positif,
  t > 2, dan tetap > 0 dengan slippage $0,30 + latensi 2 detik. Tambahan diagnosis (bukan syarat): stres slippage $1,
  hasil tanpa tahun terbaik, dan jumlah trade LAMA.
- Dua **preset aplikasi** juga ditetapkan sebelum melihat hasil XAU, dengan slippage $0,30:
  - **manual**: ikut lonjakan ≥ $2 di detik ke-5, reaksi 2 detik, lalu aturan pengguna;
  - **pending**: Buy/Sell Stop ±$2, lalu aturan pengguna.

## 3. XAU Dukascopy (1.260 rilis 2010–2026; tabel 3.1–3.2 dari putaran 710 rilis)

### 3.1 Anatomi detik pertama (median, $ per ons = $ per 0,01 lot)

| Periode | Spread sebelum → detik 1 | Gerak 1 dtk | 5 dtk | 1 mnt | 15 mnt | Arah detik-5 berlanjut s.d. 15 mnt |
|---|---|---|---|---|---|---|
| Semua, LAMA (< Okt 2021) | $0,36 → $0,49 | $0,09 | $1,09 | $1,64 | $2,56 | 50% |
| Semua, BARU (5 th) | $0,49 → $0,90 | $0,23 | $3,27 | $4,24 | $5,23 | 55% |
| NFP BARU | $0,54 → $1,14 | $0,16 | $5,53 | $6,83 | $8,06 | 51% |
| CPI BARU | $0,51 → $1,01 | $0,32 | $5,74 | $7,22 | $9,81 | 60% |
| FOMC BARU | $0,63 → $1,11 | $0,22 | $2,52 | $4,79 | $6,27 | 65% |

- Lonjakan terjadi median **±1,3 detik** setelah jam rilis. Sering hanya dalam **satu loncatan** harga (mis. NFP
  Okt 2015: +$7 dalam satu tick), jadi order apa pun terisi di harga setelah loncatan.
- Arah di detik ke-5 berlanjut sampai 15 menit hanya 50–65%, tidak jauh dari lempar koin.

### 3.2 Sisa gerak searah bila baru masuk di detik ke-d (rata-rata, **sebelum** spread & slippage)

| Periode | d = 1 dtk (1 mnt / 15 mnt) | d = 5 dtk | d = 10 dtk | d = 30 dtk |
|---|---|---|---|---|
| LAMA | +$0,14 / +$0,59 | −$0,15 / +$0,08 | −$0,11 / +$0,23 | −$0,01 / +$0,25 |
| BARU | −$0,73 / −$0,43 | +$0,50 / +$0,92 | +$0,07 / +$0,33 | +$0,18 / +$0,50 |

Sisa gerak yang searah (±$0,1–0,9) lebih kecil dari biaya masuk saat berita (spread ±$0,9 + slippage), sehingga
masuk setelah lonjakan terlihat rata-rata rugi.

### 3.3 Hasil cara masuk (516 varian)

| Cara (aturan keluar pengguna kecuali disebut) | n | Menang | Rata-rata /0,01 lot | Dengan slippage $0,30 & 2 dtk |
|---|---|---|---|---|
| Ikut kejutan Act vs Cons, detik ke-1 | 992 | 79% | **+$0,69** (17/17 th +) | **−$0,15** |
| Ikut kejutan, detik ke-5 | 990 | 73% | −$0,06 | −$0,39 |
| Ikut kejutan, detik ke-10 | 992 | 72% | −$0,17 | −$0,47 |
| **Preset manual**: ikut lonjakan ≥ $2 di detik ke-5 | 450 | 65% | −$0,59 (13% th +) | (sudah termasuk) |
| **Preset pending**: Buy/Sell Stop ±$2 | 888 | 64% | −$0,50 (24% th +) | (sudah termasuk) |
| Ikut kejutan BESAR (≥ 2× median), detik ke-1, tahan 1 mnt | 185 | 57% | +$0,88 | +$0,13; slippage $1: −$0,57 |

- **12 varian lolos kriteria konsisten**, semuanya "ikut kejutan (BESAR) di detik ke-1–2". Semuanya butuh angka
  Act dalam 1–2 detik (feed berita otomatis), dan **semuanya rugi bila slippage $1**.
- "Lawan lonjakan" (fade) selalu rugi. Aturan keluar "tutup menit 1–5 bila profit" menaikkan win rate ke 60–80%,
  tetapi tidak mengubah tanda rata-rata.
- Per berita (preset manual): NFP −$0,50, CPI −$0,61, FOMC −$0,52, PPI −$1,12, ADP −$1,14, Retail −$0,29 per
  0,01 lot. Tidak ada berita yang positif konsisten.


## 3b. Uji ulang dengan tick asli Exness (XAUUSDc akun Cent, 1.680 rilis 2015–2026)

Arsip tick Exness (`ticks.ex2archive.com`, dibuka pengguna 30 Sep) → `research/exness.py`: jendela berita tiap
bulan + tabel spread per jam (`data/research/eksternal/exness/`). Semua rilis bintang 3 ikut diuji, termasuk ISM,
Claims, dan lainnya.

**Spread asli XAUUSDc** (median per tahun): $0,47 (2015–16), $0,22–0,30 (2017–20), **$0,16–0,20 (2021–25)**,
$0,26 (2026). Saat berita (5 tahun terakhir) spread hanya $0,20 → $0,24–0,48, jauh lebih sempit dari Dukascopy
($0,9–1,1).

| Cara (aturan keluar pengguna, slippage $0,30) | n | Menang | Rata-rata /0,01 lot | 5 th | Feed Dukascopy, rilis sama |
|---|---|---|---|---|---|
| Preset manual: ikut lonjakan detik ke-5 | 472 | 69% | −$0,16 | +$0,12 | – |
| Pending ±$2 | 1.024 | 68% | +$0,26 | +$0,76 | – |
| **Pending ±$1** (5 dtk sebelum rilis), semua berita | 1.388 | 70% | +$0,36 | +$0,85 | **−$0,82** |
| Pending ±$1, **NFP** | 130 | 77% | **+$3,18** (83% th +) | +$6,22 | **−$1,87** |
| Pending ±$1, CPI | 127 | – | +$2,21 (50% th +) | +$4,92 | – |
| Pending ±$1, FOMC | 85 | 74% | **−$1,56** | −$3,51 | −$0,91 |

- 31 varian lolos kriteria di feed Exness, 9 di antaranya bisa manual. Yang terbaik: pending ±$1, tahan 5 menit,
  SL $5. Rata-rata +$0,68 (0 slippage) / +$0,38 ($0,30), **tetapi −$0,66 di feed Dukascopy**.
- NFP pending ±$1 per tahun (slippage $0,30):
  - 2016–2020: −$0,23 s.d. +$0,77;
  - 2021–2025: +$2,1 s.d. +$4,0;
  - 2026: +$25 (8 rilis).

  Dengan slippage $1 hasilnya masih +$2,07, tetapi periode LAMA menjadi −$0,33.
- **Kenapa berbeda antar feed?** Di Exness spread tetap sempit saat berita, jadi pending hanya tersentuh gerak
  sungguhan. Di Dukascopy spread melebar ±2×, sehingga pending ikut tersentuh oleh pelebaran spread dan terisi di
  harga buruk. Tick arsip adalah **kutipan**, bukan harga terisi nyata: saat NFP, order stop di akun nyata bisa
  tergelincir lebih jauh.
- MT5 tidak punya OCO bawaan. Bila order lawan ikut tersentuh sebelum dihapus, hasilnya lebih buruk dari model.
- **Kesimpulan:** belum cukup bukti untuk dipakai dengan lot normal. Langkah yang jujur adalah **uji maju** di
  NFP/CPI berikutnya dengan lot minimum (akun Cent: 0,01 lot XAUUSDc), sambil mencatat harga terisi dan slippage,
  lalu dibandingkan dengan angka di atas. Aplikasi menampilkan angka ini dengan label ⚠️ "belum terbukti, uji maju
  dulu".

## 4. BTC (1.190 rilis 2018–2026)

Detik pertama BTC jauh lebih tenang dari emas. Dalam 5 detik BTC bergerak ±0,02% (LAMA) / ±0,05% (BARU),
dalam 15 menit ±0,18% / ±0,24%. Arah detik ke-5 berlanjut sampai 15 menit 51–52% (lempar koin).

| Preset (slippage 0,015%) | n | Menang | Rata-rata per trade | LAMA / BARU | Tahun positif |
|---|---|---|---|---|---|
| Manual: ikut lonjakan ≥ 0,1% di detik ke-5, aturan pengguna | 255 | 69% | +0,012% | +0,067% (n=24) / +0,007% | 50% |
| Pending ±0,10%, aturan pengguna | 878 | 68% | −0,035% | −0,02% / −0,042% | 11% |

Per berita (preset manual): **CPI +0,248%** per trade (n=52), ISM +0,047%, PPI −0,003%, NFP −0,027%,
Claims −0,148%, FOMC −0,328%. Sisa gerak searah setelah detik ke-5 hanya jelas di **CPI 5 tahun terakhir**
(+0,28% dalam 1 menit, sebelum biaya).

Dari 516 varian, **19 lolos** kriteria, 9 di antaranya bisa dilakukan manual. Semuanya jenis "ikut"; "lawan
lonjakan" selalu rugi. Yang terbaik: ikut lonjakan ≥ 0,1% di detik ke-5, tahan 15 menit, SL 0,25%. Hasilnya
+0,116% per trade, atau +0,073% dengan slippage & reaksi 2 detik. Tetapi:

- **61% untungnya dari tahun 2022** (bear market, BTC sangat peka terhadap CPI);
- LAMA sering hanya 8–27 trade, karena sebelum 2021 BTC jarang bergerak ≥ 0,05% dalam 2–10 detik;
- spread BTC di broker saat berita tidak ada di data ini (spread diasumsikan 0,03%).

**Kesimpulan BTC:** ada kecenderungan "ikut arah" setelah berita AS, terutama CPI, tetapi rapuh.

**Dengan tick asli Exness (BTCUSDm, 1.241 rilis 2017–2026) semuanya hilang:**
- spread Exness BTC ±0,17% (2017–2021) dan ±0,06% (5 th), jauh di atas asumsi 0,03%;
- 0 dari 516 varian lolos;
- preset manual −0,078% per trade, pending −0,076%.

Spread BTCUSDm per tahun: $12–32, dan **$64 di 2021**. Riset sinyal 💰 BTC lain memakai 0,03%, jadi biaya BTC
tahun 2021 kemungkinan terlalu kecil di riset lama. Perlu dicek ulang (tindak lanjut).

## 5. Kenapa "banyak orang profit di detik pertama"?

- Yang untung di detik pertama umumnya **mesin**: feed berita berbayar (angka masuk < 1 detik), server dekat
  bursa, dan order otomatis. Di data ini, keunggulan itu habis dalam 2–5 detik.
- Trader manual melihat angka di ForexFactory beberapa detik kemudian. Saat itu spread sudah melebar ±2× dan harga
  sering sudah meloncat. Yang terlihat di media sosial biasanya kasus yang kebetulan untung (survivorship bias).
- Win rate tinggi (60–80%) dari "tutup begitu profit" itu nyata, tetapi kerugian saat tidak sempat profit lebih
  besar. Yang menentukan adalah rata-rata dolar per trade setelah biaya.

## 6. Rekomendasi

1. **Jangan entry manual "ikut lonjakan" di detik pertama berita.** Di XAU Dukascopy rata-rata −$0,59, di Exness
   −$0,16 per 0,01 lot. Di BTC Exness rugi.
2. **Pending ±$1 untuk NFP (dan CPI) di Exness**: menjanjikan di feed Exness, rugi di feed lain → **uji maju lot
   minimum** dulu dan catat harga terisi. Jangan dipakai untuk FOMC (negatif).
3. Pakai pengingat ⏱️ 1 menit sebelum rilis untuk **mengamankan posisi yang sudah terbuka**: spread melebar ±2× di
   detik pertama dan harga bisa meloncat melewati SL.
4. Otomatisasi "ikut kejutan ≤ 1 detik" (bot MT5 + feed berita cepat berbayar) adalah satu-satunya jalan yang
   positif di data. Tetapi keunggulannya habis dengan slippage $1, dan broker ritel sering menambah slippage atau
   menolak order saat berita. **Tidak dipasang**: perlu izin eksplisit dan feed berbayar. Di feed Exness,
   "ikut kejutan detik ke-1" dengan slippage $0,30 + eksekusi 2 dtk juga hanya ±$0.
5. Sinyal 💰 tetap jalur utama (+0,25R per sinyal XAU, `docs/TRADING_ALCHEMIST.md`).

## 7. Perintah

```bash
python -m research.news_detik download_bagian 1,2 0 4 100   # pekerja 0 dari 4 (ulangi k = 1, 2, 3), <= 2 jam
python -m research.news_detik download_btc                  # BTC 1 detik (cepat)
python -m research.exness XAUUSDc 2015-01 2026-09 && python -m research.exness BTCUSDm 2017-01 2026-09
python -m research.news_detik XAU_EXNESS && python -m research.news_detik BTC_EXNESS   # broker pengguna
python -m research.news_detik XAU && python -m research.news_detik BTC   # feed pembanding; semua -> detik.json
git add data cloud/api/detik.json docs/eksternal && git commit -m "..."  # simpan data di repo
```

