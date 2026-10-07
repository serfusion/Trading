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
| **Peringatan berita NFP/CPI/FOMC** | **lewati sinyal XAU ≤ 36 jam sebelum NFP/CPI/Fed: lebih baik di kedua periode** | **DIPASANG** (XAU saja) |

## ⏸️ Jeda pra-berita XAU (DIPASANG)

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
  "⏸️ Sinyal XAU baru dijeda s.d. NFP Jum 6 Nov 20.30 WIB …" di kartu sinyal, dan penjelasannya ada di Syarat & Ketentuan.
- Tanpa jadwal sama sekali (FF dan jadwal.json kosong) → tidak ada jeda (sinyal tetap jalan).
- Env Vercel: `XAU_NEWS_SKIP=0` mematikan, `XAU_NEWS_SKIP_JAM` (bawaan 36).
- `jadwal.json` diperbarui otomatis tiap jam oleh workflow `arsip_data.yml` (`python -m research.jadwal_berita`, secret
  `FRED_API_KEY`; ditulis hanya bila jadwal berubah) dan dikirim ke main + branch produksi Vercel.
- Cek kesetaraan: fungsi cloud = fungsi riset di 125.641 jam 2012–2026 (0 beda; jeda aktif ±12% waktu).
  `research/verifikasi_cloud.replay("XAU")` kini memakai jeda ini (konfigurasi live).
- Angka badge `_core.STATS` / `riwayat.json` **belum** dihitung ulang dengan jeda. Angkanya sedikit lebih rendah dari
  hasil dengan jeda (konservatif).

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
