# Data riset di repo (permintaan pengguna 30 Sep 2026)

Supaya sesi berikutnya tidak perlu mengunduh ulang, data yang pernah diunduh untuk riset disimpan di repo ini
(repo **privat**; data pihak ketiga hanya untuk pemakaian pribadi, jangan disebarkan). Semua skrip riset tetap
membaca dari `data/research/...`; pengunduh melewati file yang sudah ada.

| Folder | Isi | Sumber / cara menambah |
|---|---|---|
| `research/eksternal/dukascopy/raw_XAUUSD_ticks/` | tick BID/ASK XAU per jam di sekitar rilis berita AS (`YYYYMMDD_HH.bi5`, LZMA asli Dukascopy; file kosong = tidak ada data) | `python -m research.news_detik download_bagian <tier> <k> <n> <maks>` |
| `research/eksternal/exness/<SIMBOL>/` | tick asli Exness (XAUUSDc akun Cent 2015–, BTCUSDm 2017–) di jendela berita (`<th>-<bln>.parquet`, int x1000/x100, zstd) + spread per jam UTC (`spread_<th>-<bln>.csv`) | `python -m research.exness XAUUSDc 2015-01 2026-09` |
| `research/eksternal/binance_1s/` | kline 1 detik BTCUSDT (close) 2 menit sebelum s.d. 16 menit sesudah rilis | `python -m research.news_detik download_btc` |
| `research/spoluan_forex-factory-scraper/datasets/`, `research/ehsanrs2_forexfactory-scraper/` | kalender ForexFactory 2010 – Jan 2026 (actual/forecast/previous) | klon GitHub (tanpa `.git`) |
| folder `research/<pemilik>_<repo>/` lain | data harga XAU/BTC dari repo GitHub publik (`research/download_data.sh`) | `bash research/download_data.sh` (folder yang sudah ada dilewati) |

Batas GitHub: 100 MB per file. File lebih besar tidak di-commit (dicatat di tabel "tidak di repo" di bawah) dan
tetap diunduh oleh skripnya.

## Tidak di repo

- Semua file yang sudah diunduh sesi 30 Sep ada di repo (tidak ada yang > 100 MB).
- **Belum ada** (dipakai riset sesi lama, belum diunduh ulang): Dukascopy H1/D1 BID-ASK (`python -m research.dukascopy
  h1 ...`), FRED (yield riil, dolar, GVZ/VIX, WTI; butuh `FRED_API_KEY`), COT CFTC, funding/premium index Binance,
  USO/BNO Twelve Data. Jalankan skrip riset masing-masing, lalu `git add data` dan commit.
- Unduhan tick Dukascopy untuk berita tier 1–3 belum lengkap (lihat `docs/NEWS_DETIK.md`); pakai
  `download_bagian`, lalu commit.
