# ⏱️ Semua berita USD → arah emas sesaat setelah rilis, uji tutup kertas (11 Okt 2026)

Permintaan pengguna (berurutan):
- "setelah persentase tinggi & validitas dapat dipercaya, uji juga news lainnya … PASANG"
- "CPI, PPI langsung turun 1 detik setelah rilis, FOMC langsung naik, ISM kemarin langsung turun — SAYA MAU SEPERTI ITU SISTEMNYA"
- "hitungannya per detik tetapi hasil akhirnya beberapa detik yang diambil tinggi candle per menit (menit pertama), naik atau turun"

## Patokan baru: LONJAKAN TERBESAR MENIT PERTAMA (`research/lonjakan.py`)
Per rilis, dihitung per detik dari tick:
- p0 = harga tengah 1 detik sebelum rilis.
- naik = harga tertinggi 0–60 dtk − p0; turun = p0 − harga terendah.
- Arah = mana yang lebih jauh (< $0,05 = diam).

2.048 rilis 2010–2026. Exness dan Dukascopy sepakat 97–100%. Puncak rata-rata di detik 25 (CPI, NFP) sampai 41 (PCE). Besar median CPI sejak 2024 $12. Cache: `data/research/eksternal/lonjakan60.parquet`.

## 1. "Pola tetap per jenis berita" (`research/pola_jenis.py`, `research/lonjakan_uji.py pola`)
Aturan yang diuji: mayoritas rilis sebelumnya, tahun berjalan, rilis terakhir, 3 rilis terakhir.

**Tidak ada yang lolos**, baik di detik 1, detik 2–10, maupun lonjakan menit pertama. Contoh lonjakan menit pertama:

| Berita | Seberapa sering melonjak naik | Aturan terbaik |
|---|---|---|
| CPI | 59% | = "selalu naik" |
| FOMC | 50% | "ikuti rilis terakhir" sejak 2022: 25% |
| ISM | 50% | – |
| PPI | 54% | – |
| NFP | 46% | – |

Data 2026 juga membantah kesan "CPI langsung turun": detik 1 CPI 2026 naik di 7 dari 9 rilis. Pada 11 Sep 2026 detik 1 naik +$2,76, lalu detik 3 turun −$21. FOMC 2026: detik 1 naik 4/6, detik 10 turun 4/6.

Arah ditentukan oleh **kejutan angka tiap rilis**, bukan oleh jenis beritanya:

| Bila kejutan sudah diketahui (plafon) | Arah lonjakan searah |
|---|---|
| NFP | 90% |
| ADP | 93% |
| CPI | 88% |
| ISM | 88% |
| JOLTS | 89% |
| PPI | 84% |
| Klaim | 84% |
| Retail | 80% |
| PCE | 75% |
| GDP | 74% |
| Konsumen | 74% |

## 2. Petunjuk sebelum rilis untuk berita lain (`research/berita_detik.py`)
Konsensus & Act dari Nasdaq/Investing.com, semua hari kerja 2010–2026 (4.390 tanggal, `data/research/eksternal/nasdaq/`).

Petunjuk yang diuji, ditetapkan sebelum melihat hasil:
- **Umum (semua berita):** kejutan lalu, 3 kejutan terakhir, konsensus vs angka lalu.
- **NFP:** ADP, klaim 4 pekan, ISM ketenagakerjaan, Kalshi payrolls/pengangguran.
- **PPI / Retail:** CPI pekan itu; Retail juga penjualan kendaraan.
- **PCE:** core CPI/PPI bulan itu, Kalshi core PCE.
- **ISM:** Chicago PMI, Fed daerah, S&P Global PMI 15 menit sebelumnya.
- **GDP:** GDPNow.
- **JOLTS:** Indeed.
- **Klaim:** klaim lanjutan.
- **Konsumen:** S&P 500, bensin.

Kriteria lolos sama dengan CPI:
- tutup kertas ≥ 60% untuk 2016–2026;
- > 50% di periode LAMA dan BARU;
- permutasi keluarga p < 0,05.

| Target | Hasil |
|---|---|
| Detik 2–10 | **TIDAK ADA yang lolos** (`docs/eksternal/hasil_berita_detik.txt`) |
| Lonjakan menit pertama | **TIDAK ADA yang lolos** (`docs/eksternal/hasil_lonjakan_uji_berita.txt`) |

Yang terdekat: GDP gabungan (GDPNow + kejutan lalu) 73% sejak 2022, tetapi hanya 22 rilis, periode lama 45%, p 0,057 → **tidak dipasang**. Sisanya 30–61% dan tidak konsisten antar periode.

## 3. CPI dengan patokan lonjakan menit pertama (`research/lonjakan_uji.py cpi`)
Aturan terpasang IDX|K: **65,2%** (89 rilis 2016–2026).
- Lama 65%, sejak Okt 2021 65%, sejak 2022 68%.
- Pembanding "selalu naik": 59%. Plafon: 88%.
- Permutasi keluarga p 0,07 (2016+) / 0,14 (2022+). Dengan target detik 2–10: p 0,037 sejak 2022.
- 2026: 3 benar dari 6.

IDXy saja (konsensus indeks → y/y): 68%, p 0,029. Dipilih setelah melihat 26 aturan, jadi tidak diganti.

Tampilan CPI di aplikasi kini memakai patokan ini: **"CPI ▲ NAIK 65% (lonjakan menit 1)"**. Detailnya juga memuat detik 2–10 dan detik 1.

## 4. Perbaikan cloud
`_cpi_detik.konsensus_nasdaq`: Nasdaq kadang mengosongkan kalender pekan berjalan (11 Okt 06:30 UTC: 9–16 Okt "No record found", padahal pagi harinya ada). Respons kosong kini **tidak menimpa** konsensus tersimpan.
