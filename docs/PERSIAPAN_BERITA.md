# Persiapan Berita: Bisakah Hasil CPI/NFP/PPI Ditebak Sebelum Rilis? (30 Sep 2026)

Permintaan pengguna: CPI, PPI, dan FOMC terakhir keluar "kompak" lebih rendah, sesuai rumor, polling, dan
Polymarket. Ada yang meraup untung besar di detik-detik awal rilis. Pengguna meminta semua data untuk bersiap
menghadapi berita berikutnya, disimpulkan dalam persen, dan ditampilkan sebagai pengganti "Contoh pertanyaan" di
tab Tanya.

`python -m research.news_prediksi` → `cloud/api/persiapan.json` → kartu **🎯 Persiapan berita** (aplikasi 3.12,
`cloud/api/_persiapan.py`).

## Data & aturan

- Kalender ForexFactory Jan 2010 – Jan 2026 (actual & forecast; 3.585 rilis bernilai), XAU/USD M15, bensin FRED
  GASREGW. Setiap petunjuk hanya memakai data yang **sudah terbit sebelum rilis**.
- **Tidak bisa diuji di sini:** Polymarket, Kalshi, Cleveland Fed nowcast, CME FedWatch, dan BLS. Host-host itu
  diblokir kebijakan jaringan lingkungan riset (403).
- Petunjuk dianggap **terbukti** bila tebakan arah kejutan (di atas/di bawah konsensus) benar > 50% di periode LAMA
  (< Okt 2021) **dan** BARU (5 tahun terakhir), n ≥ 10 di masing-masing, dan p binomial < 0,05. Kasus "sesuai"
  tidak ikut dihitung sebagai benar/salah.

## 1. Peluang dasar & reaksi emas 1 jam sesudah rilis

| Berita | Di bawah / sesuai / di atas (semua) | 5 th terakhir | Emas naik 1 jam bila di bawah | bila di atas | Tanpa tahu hasil (5 th) |
|---|---|---|---|---|---|
| CPI m/m | 36 / 36 / 27% | 31 / 33 / 37% | **75%** (5 th 87%) | 42% (5 th 28%) | 54% (55%) |
| Core CPI m/m | 36 / 38 / 26% | 31 / 35 / 35% | 71% | 40% | 54% (55%) |
| PPI m/m | 44 / 15 / 41% | 49 / 14 / 37% | 65% | 37% | 53% (57%) |
| NFP | 44 / 1 / 55% | 30 / 0 / **70%** | 73% | 46% | 57% (51%) |
| Core PCE m/m | 28 / 59 / 12% | 20 / 64 / 16% | 67% | 29% | 50% (49%) |
| Retail Sales m/m | 49 / 7 / 43% | 50 / 0 / 50% | 67% | 32% | 53% (52%) |
| Klaim pengangguran | 55 / 3 / 42% | 61 / 5 / 34% | 41% | 60% | 48% (48%) |
| Federal Funds Rate | 1 / **98** / 1% | 3 / 94 / 3% | – | – | 57% (56%) |

- Emas bereaksi **jelas setelah angka keluar**: data AS lebih lemah dari perkiraan → emas cenderung naik, dan
  sebaliknya.
- Hanya dari kalender (tanpa tahu hasilnya), peluang emas naik 1 jam setelah rilis **46–62% di 18 jenis berita,
  praktis lempar koin**. Tidak ada satu pun yang ≥ 60% di semua data sekaligus di 5 tahun terakhir.
- Keputusan suku bunga FOMC 98% sama dengan perkiraan, karena pasar sudah memperhitungkannya jauh hari. Yang
  menggerakkan emas saat FOMC adalah pernyataan dan dot plot, bukan angka suku bunganya.

## 2. Petunjuk sebelum rilis (27 diuji)

| Petunjuk | Target | Arah benar (semua) | LAMA | BARU | Hasil |
|---|---|---|---|---|---|
| Kejutan bulan lalu | CPI m/m | 61,8% (n=76) | 60,8% | 64,0% | ✅ terbukti |
| Kejutan bulan lalu | Core CPI m/m | 67,1% (n=70) | 66,7% | 68,4% | ✅ terbukti |
| Kejutan bulan lalu | CPI y/y | 63,1% (n=84) | 59,6% | 70,4% | ✅ terbukti |
| Bensin bulan acuan naik/turun | CPI m/m | 60,7% (n=117) | 64,3% | 51,5% | ✅ terbukti (BARU tipis) |
| CPI keluar lebih dulu | PPI m/m | 72,4% (n=29) | 71,4% (7) | 72,7% (22) | data LAMA kurang |
| Core CPI lebih dulu | Core PPI m/m | 83,3% (n=18) | 80,0% (5) | 84,6% (13) | data LAMA kurang |
| PPI lebih dulu | CPI m/m | 62,3% (n=61) | 64,3% | 40,0% (5) | ❌ |
| ADP | NFP | 50,3% (n=175) | 54,6% | 37,8% | ❌ |
| Klaim 4 pekan | NFP | 54,3% (n=94) | 52,8% | 59,1% | ❌ |
| ADP | Unemployment Rate | 56,4% (n=133) | 51,0% | 70,3% | ❌ |
| Core PPI / Core CPI | Core PCE | 54–62% | 58–65% | 46–50% | ❌ |
| Kejutan bulan lalu | NFP, PPI, Retail, ISM, JOLTS, ADP, klaim, AHE, PCE | 36–57% | – | – | ❌ semua |

**Petunjuk yang terbukti tidak membuat arah emas lebih pasti.** Jika petunjuk menunjuk "CPI di bawah perkiraan",
hasil CPI memang lebih sering di bawah (43% vs dasar 36%). Tetapi peluang emas naik 1 jam tetap 47–55%. Alasannya,
±1/3 CPI keluar "sesuai" dan petunjuknya hanya menggeser peluang sedikit.

Petunjuk CPI → PPI tampak kuat di 5 tahun terakhir (bila CPI di bawah perkiraan, PPI juga di bawah 92%, n=12).
Namun emas naik 1 jam 75% saat CPI di bawah dan 64% saat CPI di atas. Artinya emas cenderung naik di kedua keadaan,
jadi petunjuk ini tidak membedakan arah emas.

## 3. Soal "untung besar di detik awal"

- Untung di detik pertama datang dari **tahu angka lebih cepat** (akses data/berita berlatensi rendah, server
  dekat bursa) atau dari posisi yang sudah dipegang sebelum rilis. Keunggulan itu tidak dimiliki akun ritel lewat
  MT5/MetaApi.
- Di akun ritel, saat rilis spread melebar dan order bisa meleset (slippage). Entry sesudah rilis sudah diuji 36
  cara di XAU 2012–2026, dan semuanya rugi.
- Beberapa rilis "kompak" searah dengan rumor bisa terjadi secara kebetulan. Di data ini, tebakan terbaik yang bisa
  diuji pun hanya benar ±62–67% untuk arah CPI, dan tidak memberi keunggulan arah emas.

## 4. Yang dipasang (izin pengguna 30 Sep 2026)

- `cloud/api/_persiapan.py`: GET `/api/chat` menambahkan `persiapan`. Isinya berita USD berdampak tinggi/sedang
  pekan ini (dari ForexFactory) beserta persen di atas, label arah emas sebelum rilis, petunjuk yang sudah diuji,
  dan kesimpulan.
- Label **"condong naik/turun"** hanya muncul bila peluang emas naik 1 jam ≥ 60% atau ≤ 40% di semua data
  **dan** di 5 tahun terakhir. Saat ini tidak ada berita yang memenuhi syarat itu, jadi semuanya berlabel
  "≈ lempar koin".
- Aplikasi 3.12: chip "Contoh pertanyaan" dihapus dan diganti kartu 🎯 Persiapan berita. Chat, isian rilis, dan
  kalender tidak berubah. Tidak ada order yang dibuka.
- Perbarui angka: jalankan `python -m research.news_prediksi` bila data kalender diperbarui.
- **Aplikasi 3.15 (permintaan pengguna 30 Sep: "singkat, jelas, padat; apa maksud menang?")**: setiap berita
  ditampilkan seperti kartu Status tren — label kiri, angka besar kanan, bukti kecil di bawah label:

  | Label | Angka besar | Bukti kecil |
  |---|---|---|
  | Data < perkiraan | **75% NAIK 🟢** | teruji 2012–2025 (52 rilis) • sejak Okt 2021: 87% naik |
  | Data > perkiraan | 58% turun ⚪ | lemah • teruji 2012–2025 (43 rilis) • sejak Okt 2021: 72% turun |
  | ⏱️ Pending ±$1 detik pertama | 77% untung ⚠️ | teruji 2015–2026 (130 rilis, tick Exness) • rata +$3,18/0,01 lot • feed Dukascopy −$1,87 → belum terbukti |

  Angka = arah emas 1 jam setelah angka keluar. Hijau/merah hanya bila ≥ 60% di semua data **dan** arah sama
  ≥ 55% sejak Okt 2021; selain itu abu-abu ⚪ dengan label "lemah", "≈ lempar koin", atau "tidak konsisten".
  Kata "menang" diganti "untung di X% rilis" (persen rilis yang ditutup untung); pending dengan rata-rata
  |< $0,50| ditulis "≈ impas", rata-rata negatif "RUGI 🔴". Setelah Act keluar, baris kalender menampilkan angka
  besar yang sama (`kesimpulan()`), otomatis tanpa diisi pengguna.

## 5. Langkah berikutnya (butuh akses jaringan)

Kalshi (pasar CPI & keputusan Fed) dan Polymarket menyimpan riwayat harga. Jika host `api.elections.kalshi.com`,
`gamma-api.polymarket.com`, dan `clob.polymarket.com` diizinkan di pengaturan jaringan environment, bisa diuji:
apakah peluang pasar prediksi sebelum rilis lebih tepat daripada konsensus ForexFactory, dan apakah itu memberi
keunggulan arah emas.

## Aplikasi 4.17 — satu baris per berita (7 Okt 2026, permintaan pengguna)
Pengguna: "cukup `NFP: peluang emas naik 1 jam 61% (teruji, belum pasti)`, bukan `<` / `>`". Cloud `cloud/api/_prediksi.py`
mengisi field `prediksi` di setiap berita pekan ini & 📅 berikutnya; aplikasi hanya menampilkan baris itu (skenario
"⚡ Hentakan … bila Act < / >" tidak tampil lagi; data skenario tetap ada di cloud untuk tab Tanya). Sumber berurutan:
1. model sebelum rilis NFP/JOLTS/Fed (`_prarilis`, walk-forward benar 60–65%) — hanya pekan rilisnya;
2. aturan teruji NFP: rilis lalu di atas perkiraan → emas naik 1 jam 72% / 61% sejak Okt 2021 (satu-satunya aturan
   konsisten dari ±216, `research/news_semua.py`);
3. dasar historis: % emas naik 1 jam setelah rilis itu (2010–2026, mis. CPI 54%, NFP 57%) — mendekati lempar koin.
Angka besar = arah yang lebih sering. Bukti di tombol Detail. Setelah rilis tetap tampil ✅ hasil (kini "Act 45K di bawah
perkiraan 89K", tanpa simbol). Fed/Kalshi/perkiraan hari H hanya di Detail.
- Aplikasi 4.18: baris cukup "NFP: peluang emas naik 1 jam 61%" + waktu; ketuk = show/hide detail (dasar angka "teruji,
  belum pasti", 🔄 titik balik ekonomi NFP — docs/NFP_MEAN.md bagian akhir —, 🏦 keputusan Fed Polymarket, Kalshi /
  perkiraan hari H, detik pertama). Tombol "Detail" kartu dihapus (diganti show/hide per baris).

## Uji gabungan kejutan semua berita terbaru (7 Okt 2026 — `research/news_gabung.py`, `docs/eksternal/hasil_news_gabung.txt`)
- Skor = jumlah kejutan pro-emas berita LAIN dalam 7/30 hari (semua, inflasi, tenaga kerja); 432 aturan (18 berita).
  Lolos (≥ 58% LAMA & BARU, n ≥ 30): **0** (kebetulan saja diharapkan ±9–22). Tanda skor 30 hari: 47% (LAMA 46%, BARU 50%),
  per tahun 40–59% (2026 75% n kecil) → lempar koin. Peringkat TIDAK diubah.
- NFP vs mean reversion: pendahulu membaik (≥ +2) → emas naik 1 jam 66% (LAMA 63% n 46, BARU 80% n 10, tahun naik-turun
  0–100%); kejutan tenaga kerja 30 hari ≤ −2 → 63% (LAMA 68%, BARU 53%); keduanya 78%/67% tetapi n 18/6. Dasar NFP 56%.
  Menarik tetapi BARU terlalu sedikit / tidak konsisten per tahun → kandidat, belum dipasang; dicek ulang tiap NFP.

## 🗄️ Arsip data otomatis (7 Okt 2026, permintaan pengguna)
`.github/workflows/arsip_data.yml` tiap jam menjalankan `research/arsip_data.py` → branch `arsip-data`: candle 1 jam
BTC/ETH/DOGE/ADA (Binance) + XAU/USD (Twelve Data), kalender ForexFactory pekan ini + Act, Act resmi FRED, potret harian
copy trader (OKX, vault & 300 trader Hyperliquid), Kalshi harian, log. Butuh secret GitHub Actions TWELVEDATA_API_KEY &
FRED_API_KEY (tanpa itu XAU & FRED dilewati). Ambil: `git fetch origin arsip-data && git worktree add ../arsip arsip-data`.
Kandidat NFP (pendahulu membaik / kejutan tenaga kerja) dicek ulang dari arsip ini tiap NFP baru.

## 📈 Uji maju otomatis (7 Okt 2026, "pasang semuanya" setelah secret GitHub diisi)
- `research/arsip_data.py` kini juga menyimpan XAU 5 menit, potret harian 🔄 titik balik NFP (`nfp_titik/`), dan baris
  prediksi PERSIS seperti di aplikasi (`prediksi/<pekan>.json`, pipa cloud yang sama: _persiapan → _jadwal → _prarilis →
  _prediksi, memori aturan NFP dari arsip ForexFactory) — versi terakhir SEBELUM rilis.
- `research/validasi_maju.py` (tiap jam setelah arsip): untuk tiap rilis sejak 7 Okt 2026 menilai arah emas 1 jam (close
  5 mnt sebelum rilis → +60 mnt) vs arah yang ditampilkan → `cloud/api/validasi_maju.json` (per peringkat, semua,
  kandidat NFP, 15 terakhir). Workflow mengirim file itu ke main + branch produksi Vercel bila berubah.
- Detail tiap baris prediksi: blok "📈 Uji maju sejak 2026-10-07: <peringkat> benar x dari y". Kandidat NFP (pendahulu
  membaik) otomatis naik ke 🥈 dan baris NFP menjadi "peluang emas naik 1 jam 66%" bila bukti sejak Okt 2021 (8/10 riset +
  uji maju) mencapai n ≥ 30 dan ≥ 58% (`_prediksi.kandidat_lolos`).
- Workflow copytrader mingguan kini juga memperbarui branch produksi Vercel.
