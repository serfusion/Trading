# 🥇 Petunjuk berita → peluang EMAS naik/turun (11 Okt 2026)

Permintaan pengguna: "arah news baru dikonversi XAU naik/turun berapa persentasenya; cari info apa pun, juga Finnhub; fokus
CPI dulu baru news lain". Skrip: `research/cpi_emas.py` (CPI) dan `research/news_emas.py` (semua berita); hasil lengkap
`docs/eksternal/hasil_cpi_emas.txt`, `docs/eksternal/hasil_news_emas.txt`. Uji LANGSUNG petunjuk (terbit sebelum rilis) →
gerak harga tengah XAU t0−1 dtk → t0+2 dtk … 1 jam (tick Exness, cadangan Dukascopy), 185 rilis CPI 2010–2026.
LAMA = sebelum Okt 2021, BARU = 5 tahun terakhir.

## Penting: angka dasar
Tanpa petunjuk apa pun emas NAIK setelah CPI pada **53% (2 dtk), 56% (10 dtk), 58% (1 mnt), 57% (5 mnt), 52% (1 jam)** rilis.
Jadi "emas naik 60%" hanya sedikit lebih baik dari selalu BUY. Yang dinilai adalah selisih peluang antara petunjuk
"DI BAWAH" dan "DI ATAS".

## Plafon (bila angka CPI sudah diketahui)
CPI core di atas konsensus → emas turun 1 mnt 75%; di bawah → naik 87% (BARU 82–100%). Petunjuk sebelum rilis TIDAK bisa
melampaui ini, dan karena tebakan angkanya hanya 65–76% benar, peluang emasnya jauh lebih kecil.

## CPI: peluang emas naik menurut petunjuk
| Petunjuk (sebelum rilis) | 10 dtk: naik bila DI BAWAH / DI ATAS | 1 mnt: naik bila DI BAWAH / DI ATAS | LAMA / BARU (1 mnt) | p (1 mnt) |
|---|---|---|---|---|
| **y/y konsistensi, cadangan kejutan lalu (YOY\|P)** | **62% / 44%** (n 80/73) | **64% / 48%** | 61/48 • 70/48 | 0,03 ✅ |
| y/y konsistensi saja (YOY) | 61% / 44% | 63% / 42% | 62/40 • 67/46 | 0,02 ✅ |
| core & y/y sepakat | 61% / 42% (n 38/24) | 66% / 42% | 63/44 • 73/38 | 0,05 ✅ |
| suara 3 judul (headline K\|P, core K\|P, y/y YOY\|P) | 60% / 46% | 68% / 53% | 67/49 • 71/59 | 0,05 ✅ |
| headline Kalshi (2022–2025 saja, n 31) | 67% / 38% | 73% / 50% | – • 73/50 | 0,17 |
| headline kejutan lalu | 60% / 52% | 62% / 50% | 56/50 • 80/50 | 0,16 |
| core kejutan lalu / KON&P / Kalshi | 56–57% / 43–50% | 56–62% / 51–58% | – | 0,2–0,6 |
| bensin, WTI, solar (headline) | ±50–61% | ±50–59% | – | > 0,1 ✗ |

- **Setelah 5 menit petunjuk sebelum rilis hilang** (YOY|P 5 mnt 56%/51%, 1 jam 47%/48%) — sama dengan riset sebelumnya.
- Pola: petunjuk "DI BAWAH" → emas naik 62–68% (dasar 56–58%); petunjuk "DI ATAS" → emas turun hanya 52–58%.
- Hitungan rantai cocok: tebakan y/y 72% × emas searah kejutan 79% (1 mnt) ≈ 63% teoritis vs 58% teramati (karena ada rilis
  "sama dengan konsensus") → hasilnya masuk akal, bukan kebetulan murni. Tetapi 114 uji CPI menghasilkan 7 lolos ≈ jumlah
  yang diharapkan dari kebetulan (±5) → tetap **belum terbukti**, perlu uji maju.
- Tren emas 4 jam sebelum rilis (searah/lawan tebakan): tidak konsisten (berganti antara 10 dtk dan 1 mnt) → tidak berguna.

## Berita lain (petunjuk teruji yang dipakai aplikasi + aturan "kejutan lalu terulang")
| Berita | Petunjuk | Emas naik bila petunjuk NAIK / TURUN (dasar) | Catatan |
|---|---|---|---|
| **ISM** | petunjuk aplikasi (ISM Jasa berbalik dll., n 96) | 2 dtk **65% / 34%** (50%), 1 mnt **58% / 36%** (49%) | LAMA & BARU sama arah ✅, hilang setelah 5 mnt |
| NFP | kejutan NFP lalu di atas → emas 1 jam | naik 65% bila lalu "buruk untuk emas" vs 44% | = aturan aplikasi "NFP prev_s +1" (LAMA 68%, BARU 61%) |
| ADP | kejutan lalu terulang, 1 jam | 56% / 37% (46%) | LAMA 46/30, BARU 69/55 — lemah, 1 dari banyak uji |
| CPI (petunjuk aplikasi lama: WTI dll.) | – | 1 mnt 68% / 56% (58%), p 0,08 | YOY\|P di atas lebih baik |
| PPI, GDP, Retail, Klaim, Konsumen, PCE, Rumah | – | ±50% atau n terlalu kecil | ✗ |
| FOMC | tidak ada konsensus angka | – | lihat Polymarket/Kalshi (info saja) |
120 uji berita lain → 4 lolos ≈ kebetulan (±5); hanya ISM yang sudah teruji di riset sebelumnya (docs/XAU_DETIK.md).

## Finnhub
`finnhub.io` terbuka dari sesi (401 = butuh kunci). Dokumentasi resmi (swagger) `/calendar/economic`: "Historical events and
surprises are available for Enterprise clients" → riwayat konsensus/kejutan BERBAYAR, tidak bisa untuk uji mundur. Kunci
gratis kemungkinan hanya memberi kalender terbaru/mendatang (konsensus pekan ini) — berguna sebagai cadangan ForexFactory,
bukan sumber petunjuk baru. Endpoint lain (berita pasar, sentimen saham AS, kurs) tidak berhubungan dengan arah CPI.
Butuh secret environment `FINNHUB_API_KEY` (diisi pengguna di pengaturan environment, bukan di chat).

## CPI 14 Okt 2026 (Sep) — konversi ke emas
Konsensus ForexFactory belum terbit (feed pekan ini masih pekan 4 Okt).
- Bila konsensus m/m 0,5% & y/y 3,7% → y/y tersirat 3,56–3,61% → **y/y DI BAWAH → emas naik 10 dtk 62% / 1 mnt 64%**
  (dasar 56–58%), setelah 5 mnt ≈ 50:50.
- Bila m/m 0,6% & y/y 3,7% → YOY diam; cadangan = kejutan y/y Agustus (belum ada di arsip) → bila juga diam: **≈ dasar 58% naik**.
- Core: kejutan lalu DI ATAS (0,3 > 0,2) → emas 1 mnt naik 51% bila DI ATAS → tidak ada keunggulan.
Ini peluang, bukan kepastian; spread & slippage saat rilis CPI besar (lihat docs/NEWS_DETIK.md: entry detik pertama rugi).
BELUM dipasang di cloud/aplikasi — tunggu "pasang".

## 📄 Uji "tutup kertas" (walk-forward murni, `research/tutup_kertas.py`, `docs/eksternal/hasil_tutup_kertas.txt`)
Permintaan pengguna: "tebak dulu seolah belum tahu, jawaban ditutup kertas, baru dibuka — semua tertebak atau ada yang salah?"
Tiap tahun hanya data tahun-tahun sebelumnya yang dipakai untuk persen & arah; tiap rilis ditebak lalu dibuka.

| Aturan | 1 dtk | 2 dtk | 10 dtk | 1 mnt | sejak 2022 (1 / 10 dtk / 1 mnt) |
|---|---|---|---|---|---|
| **WTI (yang tampil di aplikasi "CPI ▼ TURUN 56%")** | 55% (93/168) | 56% | 54% | 55% | **49% / 51% / 61%** |
| YOY\|P (baru) | 49% | 57% | 62% (88/142) | 59% | 46% / **66%** / 61% |
| Selalu BUY (pembanding) | 48% | 53% | 55% | 56% | 49% / 58% / 61% |

- **Tidak semua tertebak.** Aturan WTI 2024–2026: 32 rilis bergerak → **16 benar, 16 salah**. CPI 11 Sep 2026: tebak TURUN
  (WTI naik), emas NAIK $2,76 di detik pertama ❌.
- Angka "56%" di aplikasi = rata-rata 2–10 dtk SELURUH periode (bukan tutup kertas); sejak 2022 aturan WTI = lempar koin
  (49–51% untuk 1–10 dtk) dan kalah dari "selalu BUY" (58–60% di 2–10 dtk).
- YOY|P lebih baik di 10 dtk (sejak 2022 66% vs BUY 58%) tetapi 1 dtk 46–49% (detik pertama belum bergerak / acak) dan
  hanya 41 rilis sejak 2022 → masih kecil. Tahun buruk tetap ada (2017: 1 benar 8 salah; 2025: 3 benar 4 salah).
- Saran (BELUM diubah, tunggu izin): baris CPI "minyak WTI" di aplikasi diganti "≈ 50:50 (tutup kertas sejak 2022 49%)".
