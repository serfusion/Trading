# Kalshi: peluang hasil berita beberapa jam sebelum rilis (30 Sep 2026)

Permintaan pengguna: "kumpulkan info untuk prediksi arah news beberapa jam kemudian, berapa persentase akan kemana,
jadi saya bisa bersiap untuk 1 detik sebelum news". Host baru yang dibuka pengguna: `api.elections.kalshi.com`,
`gamma-api.polymarket.com`, `clob.polymarket.com` (Cleveland Fed, BLS, CME, Hugging Face masih diblokir).

- Data: `python -m research.kalshi unduh` → `data/research/eksternal/kalshi/<seri>/<event>.json` (event, pasar,
  candle 1 jam 48 jam terakhir; 2021–2026; di-commit). Pasar lama lewat endpoint `/historical/...`.
- Uji: `python -m research.kalshi uji` → `docs/eksternal/hasil_kalshi.txt` + `cloud/api/kalshi.json`.
- Konsensus & Act: ForexFactory s.d. Jan 2026, jadi uji memakai rilis 2022–2025 (171 rilis). Rilis 2026 belum bisa
  diuji karena konsensusnya tidak ada di data (arsip GitHub aplikasi akan mengisinya ke depan).
- Latar: makalah Federal Reserve (Diercks, Katz & Wright, FEDS 2026-010) menemukan Kalshi lebih akurat daripada konsensus
  Bloomberg untuk CPI headline.

## 1. Seberapa tepat Kalshi menebak kejutan (Act vs konsensus), 24 jam sebelum, selisih peluang ≥ 10 poin

| Berita | Rilis dengan kejutan | Tebakan benar | 2021–2023 / 2024–2026 |
|---|---|---|---|
| CPI m/m | 21 | **76%** | 69% / 88% |
| Core CPI m/m | 18 | **78%** | 71% / 82% |
| NFP | 23 | 57% | 29% / 69% |
| Pengangguran | 22 | 50% | 27% / 73% |
| Core PCE | 3 | (data kurang) | |

±30% rilis CPI keluar **sama** dengan konsensus; saat itu tebakan arah tidak berlaku.

## 2. Apakah emas ikut? (entry t0−1, tick Exness & Dukascopy, mesin `research/news_pra2.py`)

- Semua seri digabung, atau "ikut arah tebakan kejutan" saja: **tidak ada yang lolos** (1.680 kombinasi, 0 lolos).
  CPI saja, tutup 10 dtk: +$0,88 per 0,01 lot (t 0,7), Dukascopy +$0,06 → tidak berbeda dari nol. Sebab: rilis yang
  keluar "sama" dengan konsensus dan tebakan yang salah memberi rugi besar.
- **Kandidat terbaik — "peluang emas naik 1 menit" untuk CPI.** Peluang Kalshi (di atas / sama / di bawah) dikalikan
  reaksi emas historis per hasil (rilis CPI 2010–2025, dihitung walk-forward). Bila ≥ 60% → BUY di t0−1:

| 24 jam sebelum, sinyal ≥ 60% | n | Emas naik 1 mnt | Tutup 60 dtk (CEPAT / REALISTIS / STRES) | 2021–23 / 2024–26 | Tutup begitu untung ≥ $2 (maks 3 mnt) |
|---|---|---|---|---|---|
| Exness | 18 | 72% | +$3,28 / +$2,68 / +$1,28 | +2,54 / +3,65 | 89% untung, +$1,94 |
| Dukascopy | 18 | 78% | +$2,77 / +$2,11 / +$0,71 | +2,61 / +2,85 | 83% untung, +$1,71 |

  t = 1,6–1,9 (syarat proyek t > 2) dan n baru 18 → **belum terbukti**. Semua sinyal berarah NAIK karena secara
  historis emas naik 1 menit setelah CPI "sama" (67,5%, n = 40) dan "di bawah" (84,5%), sedangkan setelah "di atas"
  hanya 26,6% naik; sinyal "TURUN ≥ 60%" hampir tidak pernah muncul. Aturan penggabungan ini ditambahkan setelah uji
  pertama (ikut arah kejutan) tidak signifikan → ada unsur memilih setelah melihat hasil; uji maju wajib.

## 3. Keputusan Fed

Hasil konsensus hampir selalu sudah dihargai 94–100% di Kalshi saat pasar tutup; satu-satunya kejutan (Sep 2024,
potong 50 bps) dihargai 57% untuk 25 bps. Tidak ada informasi arah tambahan.

## 4. Yang dipasang (aplikasi 3.16, informasi saja)

- `cloud/api/_kalshi.py`: kartu 🎯 menampilkan baris 🎲 per berita CPI/core CPI/NFP/pengangguran/core PCE pekan ini:
  peluang "di atas / sama / di bawah perkiraan" dari pasar Kalshi (dibaca tiap 15 menit, cache Supabase baris
  `kalshi`). CPI: angka besar "xx% NAIK 🟢 / TURUN 🔴 / ⚪" (emas 1 menit) + bukti uji 2023–2025 dan label ⚠️ belum
  terbukti. NFP/pengangguran/PCE: hanya peluang angka, dengan catatan "arah emas tidak terbukti".
- Tidak membuka order dan tidak mengubah sinyal 💰.

## 5. Langkah berikutnya

- Uji maju: catat setiap CPI (peluang Kalshi 24 jam & 1 jam sebelum, hasil, gerak emas) — arsip berita aplikasi +
  `research/kalshi.py unduh` bulanan. Setelah ±30 sinyal, jalankan ulang uji.
- Konsensus 2026 (Feb–Sep) belum ada: buka host `huggingface.co` (dataset Ehsanrs2/Forex_Factory_Calendar) atau
  perbaiki arsip GitHub aplikasi, lalu uji ulang dengan 8 rilis CPI 2026 sebagai data di luar sampel.
