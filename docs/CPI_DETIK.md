# ⏱️ CPI → arah emas 1–10 DETIK setelah rilis, uji TUTUP KERTAS (11 Okt 2026)

Permintaan pengguna: "INGAT PATOKAN 1–10 DETIK SETELAH RELEASE, HITUNG MUNDURNYA SEPERTI ITU, USAHAKAN 65%, CARI DI MANAPUN
DATANYA". Skrip `research/cpi_detik.py` → `docs/eksternal/hasil_cpi_detik.txt`. Target = harga tengah XAU t0−1 dtk →
t0+1/2/3/5/10 dtk (tick Exness, cadangan Dukascopy). Tutup kertas: tahun Y hanya melihat rilis sebelum Y.

## Sumber data baru: Nasdaq / Investing.com (`research/nasdaq_kalender.py`)
- `api.nasdaq.com/api/calendar/economicevents?date=` (parameter tanggal bergeser +1 hari) memuat Act, konsensus, sebelumnya
  2010–2026, termasuk **konsensus INDEKS CPI tanpa pembulatan** (NSA ±97 rilis sejak 2014, core ±26) dan **konsensus 2026**
  (FF berhenti Jan 2026). Data di `data/research/eksternal/nasdaq/` (183 tanggal CPI).
- Konsensus FF vs Investing sama 83% (headline), 96% (core), 77% (y/y) — survei berbeda, beda 0,1 wajar.
- Cek bocor: konsensus indeks vs angka aktual selisih ±0,13% (sd), hanya 3/139 persis sama → dibuat sebelum rilis.
- Urutan baris m/m–y/y di API kadang terbalik → dipilih dengan mencocokkan "sebelumnya" ke FRED.

## Hasil (2–10 dtk = gabungan detik 2, 3, 5, 10)
| Aturan (tebak emas) | Semua 2016–2026 | LAMA | BARU (≥ Okt 2021) | 2022+ |
|---|---|---|---|---|
| Selalu NAIK (pembanding) | 53,5% | 50,1% | 59,3% | 58,9% |
| Plafon: kejutan SUDAH diketahui | 85% | 85% | 86% | 89% |
| **IDX\|K** = suara 3 indeks tanpa pembulatan, cadangan Kalshi headline | **64,2%** (89 rilis) | 58,5% | **68,9%** | **70,7%** (47 rilis) |
| SUARA_IDX (indeks saja, aturan ditetapkan sebelum melihat hasil) | 62,7% | 58,5% | 66,9% | 69,1% |
| Kalshi headline saja (2024–2026, 21 rilis) | 73,8% | – | 73,8% | 73,8% |
| IDXy (indeks NSA → y/y) | 60,1% | 58,5% | 61,9% | 63,8% |
| Pilih aturan terbaik tiap tahun | 58,2% | 53,9% | 64,5% | 66,1% |
| Model logistik semua petunjuk | 54–57% | 47–55% | 57–63% | 57–63% |
| Aturan WTI di aplikasi sekarang | 54% | 56% | 51% | 50% |

IDX|K per detik (semua / 2022+): **1 dtk 59% / 57%**, 2 dtk 67% / 77%, 3 dtk 62% / 68%, 5 dtk 63% / 70%, 10 dtk 65% / 68%.
Per tahun (2–10 dtk benar/total): 2016 16/20, 2017 20/28, 2018 26/35, **2019 10/28, 2020 11/28, 2021 12/28**, 2022 20/32,
2023 25/40, 2024 37/48, 2025 34/44, 2026 17/24.

## Kesimpulan jujur
- **Detik ke-1 tidak bisa 65%**: walau angka CPI sudah diketahui pun emas di detik 1 hanya searah 54–58% (harga belum
  bergerak / spread). Patokan realistis = detik 2–10.
- **65% tercapai sejak 2022 (68–77% di detik 2–10) tetapi TIDAK di seluruh periode** (64%; 2019–2021 di bawah 45%).
- IDX|K disusun SETELAH melihat hasil putaran pertama (komponennya — 3 indeks & Kalshi — ditetapkan sebelumnya); ±25 aturan
  diuji → sebagian keunggulan bisa kebetulan. Perlu uji maju (rilis 14 Okt dst.).
- Gerak 2026 sangat besar (±$20–55 dalam 10 dtk, terkonfirmasi Exness & Dukascopy) → salah tebak = rugi besar; spread &
  slippage saat rilis tidak dihitung di sini.
- Cache sumber `pra_xau_semua_v2`/`pra_menit` memuat 2 rilis CPI ganda (10 Mar 2021 & 2022 jam 07:30 New York, salah zona
  waktu); cpi_detik menyaring 08:30 New York. Hasil cpi_emas/tutup_kertas berubah < 1 poin.

## CPI 14 Okt 2026 (dicek 11 Okt)
- Konsensus Nasdaq/Investing: m/m **0,6%**, y/y **3,6%**, core m/m **0,2%**, core y/y 2,5%; konsensus INDEKS belum terbit.
- Kalshi headline (pasar KXCPI-26SEP): di atas 0,6% 18%, di bawah 35% → **condong DI BAWAH** → aturan IDX|K (cadangan
  Kalshi): **emas NAIK detik 2–10** (Kalshi saja 74%, n 21). Core Kalshi condong di atas (37% vs 22%), y/y di atas
  (48% vs 14%) — bertentangan; aturan teruji memakai headline. Nilai akhir dihitung 1 jam sebelum rilis.
- BELUM dipasang di aplikasi (tunggu "pasang").
