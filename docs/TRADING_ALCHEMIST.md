# Trading Alchemist (Rizki Aditama) vs Sistem Kita (30 Sep 2026)

Permintaan pengguna: telusuri buku *Trading Alchemist* karya Rizki Aditama, bandingkan dengan strategi kita, dan
terapkan hal yang baik.

`python -m research.momentum_candle` (metode sebagai strategi sendiri) dan `python -m research.alchemist` (unsurnya
sebagai perbaikan sinyal 💰).

## 1. Sumber & keterbatasan

- Buku: *Trading Alchemist* (Yash Media, viii + 137 hlm., ISBN 978-623-89898-1-2). Tiga pilar: analisa teknikal
  (strategi scalping & swing, support/resistance, pola candlestick, MA/RSI/MACD), psikologi trading, dan manajemen
  risiko, ditambah latihan praktis. Isinya berbayar dan tidak tersedia terbuka; **PDF bajakan tidak dipakai**.
- Aturan yang bisa diuji diambil dari materi publik penulis dan ringkasan komunitas tentang metode andalannya,
  **Momentum Candle** (Sekolah Trading):
  - entry di M5/M15 setelah candle berbadan besar & dominan, sumbu kecil, **menembus supply/demand kecil**, dan
    candle sudah **tutup**; validasi arah di H1–H4;
  - SL di bawah/atas candle momentum; TP ke S/R terdekat atau minimal RR 1:1,5;
  - BE hanya setelah minor BOS (bukan karena floating kecil); maksimal 2 momentum candle per hari.
- Situs penulis, YouTube, TradingView, dan Myfxbook diblokir jaringan lingkungan riset. Rincian yang hanya ada di
  buku atau video (mis. definisi "supply kecil" yang persis) mungkin berbeda dari tafsiran di bawah.
- Catatan Myfxbook publik penulis (akun scalping: 82 trade, win rate 84%, profit factor 3,91) terlalu sedikit untuk
  menilai keunggulan jangka panjang, dan tidak bisa dicek ulang dari sini.

## 2. Momentum Candle sebagai strategi sendiri (XAU/USD, spread 0,25–0,30)

Tafsiran (ditetapkan sebelum melihat hasil): badan ≥ 1× atau 1,5× ATR14, total sumbu ≤ 30% range, close menembus
high/low 10 candle sebelumnya. Entry di open candle berikutnya, SL di ujung candle momentum, TP 1,5R / 2R, BE
tanpa / di +1R. Validasi arah: tanpa / close vs EMA50 H1 / H4. Maksimal 2 entry per hari, tutup paksa 1 hari.
Timeframe M15 2012–2026 dan M5 2022–2026 (48 varian).

| | Trade/tahun | Win rate | Rata-rata per trade | Total per tahun | Periode positif |
|---|---|---|---|---|---|
| **Terbaik**: M15, badan 1,5×ATR, validasi H4, TP 2R | 208 | 34,5% | −0,008R | −1,7R | 2/4 |
| Terburuk: M15, badan 1×ATR, tanpa validasi, BE +1R | 471 | 29,6% | −0,127R | −59,9R | 0/4 |
| M5 terbaik (2022–26): badan 1,5×ATR, validasi H4, TP 2R | 407 | 32,4% | −0,031R | −12,7R | 1/2 |
| **Sinyal 💰 XAU kita**, periode yang sama (2012–26) | 83 | 48,9% | **+0,248R** | **+20,5R** | 64% tahun |

- **Semua 48 varian rugi setelah spread**. Momentum candle besar di M5/M15 sering sudah di ujung dorongan: SL-nya
  lebar (sepanjang candle), dan harga kerap berbalik sebelum 1,5R.
- Validasi H1/H4 dan badan yang lebih besar mengurangi kerugian, tetapi tidak membuatnya untung.
- BE di +1R menurunkan win rate 5–8 poin tanpa memperbaiki hasil. Di M15 hasilnya selalu lebih buruk; di M5 bedanya hanya ±0,01R.

## 3. Unsurnya sebagai perbaikan sinyal 💰 (kriteria konsisten (a)–(d) `research/eksternal.py`)

| Unsur | XAU (1.185 sinyal 💰) | BTC (1.624 sinyal 💰) |
|---|---|---|
| F1 candle sinyal H1 = momentum candle (1,5×ATR) | lolos +0,46R vs dibuang +0,12R, tetapi yang dibuang **masih untung** → total turun +294R → +203R; 8/14 tahun | tidak berpengaruh (p = 0,64) |
| F2 momentum candle M15 terakhir searah | tidak konsisten (di periode latih terbalik) | – |
| F3 maksimal 2 sinyal per hari | netral (lolos = dibuang = +0,25R) | membuang profit |
| **F4 validasi arah H4 (close vs EMA50)** | **✅ konsisten**: yang dibuang rata-rata −0,56R (latih −0,85, uji −0,26), 4/6 tahun, p = 0,008; uji nyata +323,8R → **+332,5R** | tidak konsisten (yang dibuang justru +1,20R) |
| BE setelah minor BOS (fraktal 3, atau setelah TP1) | WR 48,3% → 55,4%, total +324R → +343R, DD −43,6R → −42,3R; lebih baik hanya 7/14 tahun | WR 48,2% → 53,4%, total +766R → +788R; 7/11 tahun |

## 4. Mana yang lebih baik?

- **Sinyal 💰 kita lebih baik** dari Momentum Candle di data 2012–2026: rata-rata +0,25R vs ±0 s.d. −0,13R per
  trade, dengan 5× lebih sedikit trade (biaya spread jauh lebih kecil). Metode scalping dengan SL sempit di M5/M15
  kalah oleh spread XAU; sistem breakout H1 kita bertahan karena target geraknya besar.
- Win rate 84% di Myfxbook penulis tidak bertentangan dengan hasil ini: win rate tinggi bisa datang dari TP kecil,
  manajemen manual, dan sampel pendek. Yang menentukan adalah rata-rata R setelah biaya dalam bertahun-tahun.

## 5. Yang diterapkan

- **Validasi arah H4 untuk 💰 XAU** (satu-satunya unsur yang lolos kriteria): cloud tidak mengirim sinyal 💰 XAU
  bila close candle H4 terakhir yang sudah tutup berada di sisi yang berlawanan dari EMA50 H4
  (`cloud/api/_core.h4_ema_check`, env `XAU_H4_FILTER`, default aktif; `0` = mati). Efeknya kecil: ±1 sinyal per
  tahun dibuang, +0,6R/tahun di uji nyata. BTC tidak memakai filter ini.
- **Tidak diterapkan**:
  - entry momentum candle M5/M15 (rugi);
  - maksimal 2 sinyal/hari (membuang profit);
  - momentum candle sebagai syarat sinyal (membuang sinyal yang masih untung).
- **BE setelah minor BOS** hanya menukar profit dengan win rate, seperti pilihan SL+ 0,7R yang sudah ada. Tidak
  konsisten per tahun, jadi tidak dipasang.
- Prinsip manajemen risiko & psikologi buku (risiko kecil per trade, RR ≥ 1:1,5, disiplin) **sudah** ada di sistem:
  - risiko 0,25–1% per sinyal;
  - TP1 1R + posisi berjalan dengan rata-rata R positif;
  - batas modal di aplikasi.
