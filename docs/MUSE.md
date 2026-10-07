# Sistem "Muse" / repo moritakaaz/trading-alert — dipelajari, diuji, dan yang dipasang (7 Okt 2026)

Permintaan pengguna: *"Pelajari semua ini, riset, uji validitas dan terapkan apabila dapat menambah wr dan profit …"*
plus repo https://github.com/moritakaaz/trading-alert.

Repo mereka hanya **dibaca** (kode pihak ketiga, tidak dijalankan). Aturannya **ditulis ulang** di
`research/muse_uji.py` dan diuji pada data kita (XAU H1 2012–2026, M15 2012–2020, M5 2020–2026, spread asli/realistis).
Angka lengkap: `docs/eksternal/hasil_muse.txt`. Periode selalu dua: **LAMA** (< Okt 2021) dan **BARU** (Okt 2021–2026).

## Ringkasan

| Unsur sistem Muse | Hasil uji pada sinyal 💰 kita | Keputusan |
|---|---|---|
| Breakout Donchian 48 H1, entry saat close M5, SL 1,5×ATR, TP1 1R → BE, TP3 2R | spread $0,20: LAMA +0,00R, BARU +0,02R per trade (PF 1,00–1,05); 2026 PF 1,23 (mendekati klaim 1,38) | tidak dipakai — 💰 kita jauh lebih baik |
| Filter EMA 20/50 H1/H4 | LAMA membantu, BARU merusak (sinyal yang dibuang BARU WR 72%) | tidak dipasang |
| Entry lebih awal di M5 | sinyal palsu (5.345) lebih mahal daripada entry lebih awal; tiap tahun negatif | tidak dipasang |
| Jeda setelah SL (12 jam, v1.3) | pada sistem mereka sedikit membantu; pada sinyal kita sinyal yang dilewati justru **untung** (XAU BARU +0,98R/sinyal) | tidak dipasang |
| Kraken/Binance PAXG sebagai cadangan feed | korelasi return 1 jam 0,71; breakout jam sama hanya 46–47% | tidak dipasang |
| **Peringatan berita NFP/CPI/FOMC** | **lewati sinyal XAU sebelum NFP/CPI/Fed: lebih baik di kedua periode** | **DIPASANG** (XAU saja; 36 jam → 60 jam) |

## ⏸️ Jeda diperpanjang ke 60 jam + angka badge dihitung ulang (7 Okt 2026, izin "pasang keduanya")

Replay penuh kode cloud (konfigurasi live: set tambahan, lapisan, filter H4; **R bersih spread asli Exness**; utama +
lapisan). Angka di sini memakai R bersih, jadi sedikit berbeda dari tabel 36 jam di bawah (yang memakai r riset).

| Periode | Tanpa jeda | Jeda 36 jam | **Jeda 60 jam (dipasang)** |
|---|---|---|---|
| LAMA | n 3.658, WR 59,6%, +504R, PF 1,35, DD −264R | n 3.133, WR 60,8%, +625R, PF 1,52, DD −195R | n 2.897, WR **61,6%**, **+674R**, PF **1,62**, DD **−145R** |
| BARU | n 2.807, WR 62,4%, +567R, PF 1,56, DD −230R | n 2.474, WR 65,0%, +708R, PF 1,86, DD −180R | n 2.224, WR **65,1%**, **+711R**, PF **1,96**, DD **−169R** |
| 2026 | n 318, WR 74,2%, +171R, PF 3,22 | n 254, WR 75,6%, +178R, PF 4,09 | n 245, WR 75,9%, +174R, PF 4,09 |

- 60 jam dibanding 36 jam: LAMA jelas lebih baik (+49R, DD −50R lebih kecil). BARU total hampir sama (+3R) tetapi
  dengan sinyal 10% lebih sedikit, jadi R per sinyal +0,286 → +0,320 dan DD lebih kecil. 2026 sedikit lebih rendah (−4R).
- Per tahun dibanding tanpa jeda (60 jam): 2013 −8, 2014 +17, **2015 −10**, 2016 +34, 2017 +20, 2018 +63, 2019 +55,
  2020 +11, **2021 −24**, 2022 +27, 2023 +53, 2024 +37, 2025 +37, 2026 +3 → 11 dari 14 tahun membaik (36 jam: 12/14).
- Catatan jujur: 60 jam dipilih setelah melihat kedua periode (uji 3c), jadi ada risiko kebetulan. Dataran 30–60 jam
  semuanya positif, dan 36 jam tetap bisa dipakai lagi lewat env `XAU_NEWS_SKIP_JAM=36`.

Angka badge yang dihitung ulang (Okt 2021–2026, hanya sinyal yang dikirim, `research/muse_uji.py angka`):

| | Sebelum | Sekarang |
|---|---|---|
| XAU konf+⭐ (`_core.STATS`) | WR 61,9%, +0,206R, n 506 | WR **66,1%**, **+0,261R**, n 623 |
| XAU konf | WR 66,7%, +0,188R, n 153 | WR **70,3%**, **+0,296R**, n 128 |
| ⚡ XAU (`TIER_STATS`) | WR 54,3%, +0,346R, n 127 | WR **65,8%**, **+0,466R**, n 146 |
| Lapisan XAU (`sinyal_lapis.json`) | WR 62,3%, +0,224R, n 1.859 | WR **64,2%**, **+0,347R**, n 1.473 |

Akibatnya badge notifikasi XAU konf+⭐ naik dari 💰💰⭐⭐ ke **💰💰💰⭐⭐** (+0,261R ≥ batas +0,25R). Kategori yang dikirim
tidak berubah.

Angka "sebelum" untuk konf+⭐/konf/⚡ masih berasal dari replay lama (tanpa set 100/40 & 120/50). Kartu 📜/"teruji"
(`cloud/api/riwayat.json`) dibuat ulang dengan `python -m research.verifikasi --cepat`: XAU sejak Okt 2021 WR 62,6% →
66,8%, +0,159R → +0,267R per sinyal. XAU ⭐/biasa (tidak dikirim) dan BTC tidak berubah. Replay tanpa jeda disimpan di
`data/research/eksternal/verifikasi/cloud_XAU_tanpajeda.csv`.

## ⏸️ Jeda pra-berita XAU (DIPASANG, awalnya 36 jam)

Ide berasal dari peringatan kata kunci Finnhub di sistem Muse. Diuji pada kalender ForexFactory 2010–Jan 2026 +
tanggal rilis FRED (NFP release 50, CPI release 10) + jadwal FOMC.

**Replay penuh kode cloud asli** (`research/verifikasi_cloud.replay` + `skip_fn`, konfigurasi live, spread asli Exness,
efek slot kosong ikut dihitung), semua sinyal XAU (utama + lapisan):

| Periode | Bawaan | + jeda 36 jam |
|---|---|---|
| LAMA | n 3.658, WR 59,6%, +653R, PF 1,47, DD −212R | n 3.133, WR 60,8%, **+753R**, PF **1,66**, DD **−152R** |
| BARU | n 2.807, WR 62,4%, +597R, PF 1,60, DD −216R | n 2.474, WR **65,0%**, **+734R**, PF **1,90**, DD **−167R** |
| 2026 | n 318, WR 74,2%, +172R, PF 3,24 | n 254, WR 75,6%, +179R, PF 4,12 |

Per tahun (jeda − bawaan, R): 2013 −4, 2014 +16, 2015 +17, 2016 +23, 2017 +9, 2018 +33, 2019 +31, 2020 +10,
**2021 −48**, 2022 +28, 2023 +38, 2024 +46, 2025 +30, 2026 +7. Jadi 12 dari 14 tahun lebih baik.

Ketahanan (pasca-saring, uji 3c):
- Semua jendela 6, 12, 18, 24, 30, 36, 42, 48, 60, 72 jam: sinyal yang dilewati **rugi** di LAMA dan BARU.
  Jendela 36 jam ada di tengah dataran 30–48 jam. 60 jam sedikit lebih baik, tetapi kurvanya berisik (48 jam di LAMA
  lebih lemah), jadi tidak dikejar. Env `XAU_NEWS_SKIP_JAM` bisa mengubahnya.
- Per jenis berita (36 jam): NFP, CPI, dan Fed **masing-masing** negatif di kedua periode (BARU: NFP −0,54R,
  CPI −0,41R, Fed −0,38R per sinyal).
- Dibanding subset acak yang sama besar: LAMA −94R vs +96R, BARU −140R vs +74R (p < 0,0002 dari 5.000 undian).
- BTC: jeda yang sama **memperburuk** → tidak dipasang untuk BTC, ETH, atau koin lain.
- Berita lain (PPI/PCE/Retail/GDP): BARU tidak konsisten → tidak ikut.

Kenapa masuk akal: menjelang NFP/CPI/Fed pasar emas cenderung tertahan. Breakout pada saat itu lebih sering gagal,
lalu berbalik saat rilis keluar. Ini tetap hasil historis, **bukan jaminan**. Rugi beruntun tetap mungkin, dan 2021
justru rugi 48R karena jeda.

### Cara kerja di cloud
- `cloud/api/_jeda_berita.py`: jadwal = kalender ForexFactory pekan ini (cache Supabase `kalender`) +
  `cloud/api/jadwal.json` (FRED + FOMC 2026–2027). Bila ada NFP/CPI/Fed dalam ≤ 36 jam ke depan, **sinyal XAU baru**
  (utama dan lapisan) tidak dikirim. Alasannya dicatat di log `skip`. Posisi yang sudah terbuka tetap dikelola
  (SL/TP/SL+/TUTUP). Setelah rilis keluar, sinyal berjalan lagi.
- Heartbeat XAU membawa `jeda` {on, text, berita, sampai}. Aplikasi 4.20 menampilkan baris
  "⏸️ Sinyal XAU baru dijeda s.d. NFP Jum 6 Nov 20.30 WIB …" di kartu sinyal, dan penjelasannya ada di Syarat & Ketentuan
  (aplikasi 4.21: teks 60 jam + angka baru).
- Tanpa jadwal sama sekali (FF dan jadwal.json kosong) → tidak ada jeda (sinyal tetap jalan).
- Env Vercel: `XAU_NEWS_SKIP=0` mematikan, `XAU_NEWS_SKIP_JAM` (bawaan 60 sejak 7 Okt sore; awalnya 36).
- `jadwal.json` diperbarui otomatis tiap jam oleh workflow `arsip_data.yml` (`python -m research.jadwal_berita`, secret
  `FRED_API_KEY`; ditulis hanya bila jadwal berubah) dan dikirim ke main + branch produksi Vercel.
- Cek kesetaraan: fungsi cloud = fungsi riset di 125.641 jam 2012–2026 (0 beda; jeda aktif ±12% waktu).
  `research/verifikasi_cloud.replay("XAU")` kini memakai jeda ini (konfigurasi live).
- Angka badge `_core.STATS` / `riwayat.json` sudah dihitung ulang (lihat bagian 60 jam di atas).

## Tiruan sistem trading-alert (uji 5)

Aturan v1.1–v1.3 dari README & harness mereka: channel = 48 candle H1 yang sudah selesai; pemicu = close M5 (M15
sebelum Agu 2020) menembus channel, hanya saat transisi; SL 1,5×ATR14 H1; R per trade −1 / 0 (BE setelah TP1) / +2 (TP3)
/ tutup 48 jam; satu posisi; filter H4 (close vs SMA15) dan EMA20/50 H1; opsi jeda 12 jam setelah SL.

| Varian (spread $0,20) | LAMA | BARU | Jan–Okt 2026 |
|---|---|---|---|
| v1.1 (H4) | +0,003R, PF 1,01 | +0,013R, PF 1,03 | PF 1,16 |
| v1.2/1.3 (+EMA20/50) | +0,002R, PF 1,00 | +0,023R, PF 1,05 | PF 1,23 |
| v1.3 + jeda 12 jam setelah SL | +0,018R, PF 1,04 | +0,033R, PF 1,07 | PF 1,16 |
| tanpa filter | +0,011R, PF 1,02 | +0,027R, PF 1,06 | PF 1,20 |
| **💰 XAU kita (utama)** | **+0,140R, PF 1,38** | **+0,172R, PF 1,49** | **PF 4,08** |

Klaim "PF 1,38 dalam 9 bulan" mereka cocok dengan 2026 yang sedang tren kuat. Dalam 14 tahun sistem itu hampir
impas setelah spread (2022 −64R, 2017 −29R). WR mereka ±28–32% (BE dihitung bukan menang).
