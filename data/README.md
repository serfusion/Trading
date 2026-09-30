# Data riset di repo (permintaan pengguna 30 Sep 2026)

Supaya sesi berikutnya tidak perlu mengunduh ulang, data yang pernah diunduh untuk riset disimpan di repo ini
(repo **privat**; data pihak ketiga hanya untuk pemakaian pribadi, jangan disebarkan). Semua skrip riset tetap
membaca dari `data/research/...`; pengunduh melewati file yang sudah ada.

| Folder | Isi | Sumber / cara menambah |
|---|---|---|
| `research/eksternal/dukascopy/raw_XAUUSD_ticks/` | tick BID/ASK XAU per jam di sekitar rilis berita AS (`YYYYMMDD_HH.bi5`, LZMA asli Dukascopy; file kosong = tidak ada data) | `python -m research.news_detik download_bagian <tier> <k> <n> <maks>` |
| `research/eksternal/binance_1s/` | kline 1 detik BTCUSDT (close) 2 menit sebelum s.d. 16 menit sesudah rilis | `python -m research.news_detik download_btc` |
| `research/spoluan_forex-factory-scraper/datasets/`, `research/ehsanrs2_forexfactory-scraper/` | kalender ForexFactory 2010 – Jan 2026 (actual/forecast/previous) | klon GitHub (tanpa `.git`) |
| folder `research/<pemilik>_<repo>/` lain | data harga XAU/BTC dari repo GitHub publik (`research/download_data.sh`) | `bash research/download_data.sh` (folder yang sudah ada dilewati) |

Batas GitHub: 100 MB per file. File lebih besar tidak di-commit (dicatat di tabel "tidak di repo" di bawah) dan
tetap diunduh oleh skripnya.

## Tidak di repo

<!-- diisi otomatis saat commit data -->
