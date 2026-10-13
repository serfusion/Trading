# 🔁 Catatan serah-terima: riset arah emas sesaat setelah berita (11 Okt 2026)

Permintaan pengguna: "Simpan apa pun di GitHub yang sudah diperiksa — download, riset, verifikasi, dll. — supaya bisa
melanjutkan di sesi lain". File ini adalah titik mulai untuk sesi berikutnya.

## 1. Yang SUDAH DIPASANG (produksi Vercel = branch `claude/bold-davinci-ykgq8j`)
- **CPI** — `cloud/api/_cpi_detik.py` + `cpi_detik.json`, aturan IDX|K. Rincian di `docs/CPI_DETIK.md` dan `docs/BERITA_DETIK.md`.
  - Logika: suara 3 konsensus INDEKS tanpa pembulatan dari Nasdaq; bila suaranya 0 → Kalshi headline.
  - Teks di aplikasi: "CPI ▲/▼ 65% (lonjakan menit 1)".
  - Angka uji: tutup kertas 2016–2026 65%, lama 65%, baru 65%.
  - Validitas: koreksi banyak-uji p 0,037 sejak 2022 (target detik 2–10), p 0,07 untuk target lonjakan.
- PR yang memasangnya:
  - [serfusion/Trading#88](https://github.com/serfusion/Trading/pull/88), [serfusion/Trading#90](https://github.com/serfusion/Trading/pull/90) → main.
  - [serfusion/Trading#89](https://github.com/serfusion/Trading/pull/89), [serfusion/Trading#91](https://github.com/serfusion/Trading/pull/91) → produksi.
- Setelah merge ke main, **produksi harus disinkronkan** lewat PR main → `claude/bold-davinci-ykgq8j`. Workflow `arsip_data` hanya menyinkronkan bila `jadwal.json`/`validasi_maju.json` berubah.

## 2. Patokan pengguna
- **Lonjakan terbesar menit pertama** = arah yang lebih jauh, naik atau turun, dari harga 1 detik sebelum rilis, dalam 0–60 detik. Dihitung per detik dari tick.
  - Data: `research/lonjakan.py` → `data/research/eksternal/lonjakan60.parquet`.
- Selalu uji **tutup kertas**: tahun Y hanya melihat data sebelum Y.
- Selalu laporkan periode LAMA (< Okt 2021), BARU, dan sejak 2022.
- Selalu jalankan permutasi keluarga untuk koreksi banyak-uji.
- Pasang **hanya bila lolos semua syarat**. Syarat lengkap ada di skrip workflow:
  - ≥ 60%;
  - > 50% LAMA & BARU;
  - p keluarga < 0,05;
  - ≥ 40 rilis;
  - datanya bisa dihitung live.

## 3. Riset berita lain — status
Workflow paralel: `.claude/workflows/riset-berita-lonjakan.js`. Isinya 6 kelompok riset → 2 pemeriksa adversarial per kandidat (look-ahead & statistik) → kritik.

Hasil agen tersimpan di `docs/eksternal/riset_agen_hasil.json`.

| Kelompok | Status | Hasil |
|---|---|---|
| NFP (`research/riset_nfp.py`, `riset_nfp_cek.py`, `docs/eksternal/hasil_riset_nfp.txt`) | ✅ selesai | **0 layak pasang** (lihat catatan di bawah tabel) |
| ISM (`research/riset_ism*.py`, `docs/eksternal/hasil_riset_ism.txt`) | ✅ selesai | **0 layak pasang** (lihat catatan di bawah tabel) |
| PPI + PCE (`research/riset_inflasi*.py`) | ✅ selesai 13 Okt | PPI ← WTI DIPASANG (docs/PPI_WTI.md); PCE 0 |
| Retail + GDP | ✅ selesai 13 Okt (`research/riset_dalam*.py`, docs/RISET_DALAM.md) | **0 layak pasang** |
| ADP + JOLTS + klaim | ✅ selesai 13 Okt (sama) | **0 layak pasang** (JOLTS ← NFP = kandidat uji maju) |
| FOMC + konsumen | ✅ selesai 13 Okt (sama) | **0 layak pasang** |

Catatan NFP: 25 aturan diuji. UR2 (pasca-lihat) 64% tetapi uji sadar-seleksi p 0,21/0,07, dan sama dengan "selalu turun" di periode BARU.

Catatan ISM: 38 aturan diuji.
- **ISM Jasa "-P&REGK"** (pasca-lihat) 70%. Syarat formalnya lolos, tetapi uji sadar-seleksi p 0,17/0,58, dan 2026 hanya 3/7 → **belum terbukti, kandidat uji maju**.
- ISM Manufaktur tidak ada yang bekerja.
- Bug data yang ditemukan agen ISM, diperbaiki **di modulnya sendiri** saja:
  - (1) file FF spoluan memuat Januari tahun berikutnya;
  - (2) tanggal Nasdaq kadang mundur 1 hari;
  - (3) lonjakan60 memuat 1 baris ISM palsu 2016-01-05 → **perlu diperbaiki di `research/lonjakan.py`** bila dipakai lagi.

Riset putaran pertama yang sudah selesai (semua 0 lolos):
- `research/berita_detik.py`
- `research/lonjakan_uji.py berita|pola`
- `research/pola_jenis.py`

"Pola tetap per jenis berita" (CPI selalu turun / FOMC selalu naik) juga tidak lolos.

## 4. Cara melanjutkan di sesi lain
1. `git fetch origin && git checkout claude/awesome-mendel-azy3aa`. Atau mulai dari main bila PR-nya sudah di-merge; main sudah memuat semuanya setelah merge.
2. Lanjutkan kelompok yang belum selesai lewat workflow (ketik "use a workflow"/ultracode). Agen akan melanjutkan file yang sudah ada, tidak mengulang:
   `Workflow({name: "riset-berita-lonjakan", args: ["inflasi", "retail_gdp", "kerja_lain", "fomc_konsumen"]})`
3. Atau jalankan langsung tanpa workflow:
   - `PYTHONPATH=. python3 -m research.riset_nfp segar`
   - `python3 -m research.riset_nfp_cek`
   - `python3 -m research.riset_ism` (lihat docstring tiap file)
4. Kandidat yang lolos → **wajib** verifikasi adversarial (lensa look-ahead/data live + statistik ulang) → baru pasang. Pola pemasangannya sama dengan `_cpi_detik.py`: modul cloud + JSON angka uji + `_pra_aset.tebak_kartu` + test + PR main + PR produksi.
5. Perbarui file ini, `docs/eksternal/riset_agen_hasil.json`, dan `CLAUDE.md`, lalu commit & push.

## 5. Data yang tersimpan di repo (tidak perlu diunduh ulang)
- `data/research/eksternal/nasdaq/` — kalender Nasdaq/Investing semua hari kerja 2010-01-04 … Okt 2026 (4.390 tanggal).
  - Tambah/perbarui: `python -m research.nasdaq_kalender harikerja`.
  - Nasdaq kadang kosong untuk pekan berjalan → ulangi nanti.
- `data/research/eksternal/lonjakan60.parquet` — arah lonjakan menit 1 untuk 2.048 rilis.
- `data/research/eksternal/alfred_*.json` — vintage ALFRED (klaim, upah, angkatan kerja, pengangguran).
- `data/research/eksternal/riset_*` — cache tiap agen, termasuk tick Dukascopy tambahan `riset_inflasi/duka/`.
- `data/research/eksternal/kalshi/KXGDP/` — pasar Kalshi GDP.
- `data/research/eksternal/fred_*.json` — seri FRED yang dipakai.
- Belum ada di repo: tick XAU untuk beberapa rilis 2026 di luar CPI/NFP/FOMC (PPI/ISM/dll.). Agen ISM melengkapinya dari zip bulanan Exness di modulnya sendiri.
