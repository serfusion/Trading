# Entry 1 detik SEBELUM berita, tutup 1–3 detik setelah entry (30 Sep 2026)

Permintaan pengguna: "1 detik sebelum news keluar saya akan entry … saya harap kamu bisa memprediksi kejutannya
karena 1–3 detik saya akan close posisi setelah entry".

Skrip: `python -m research.news_pra` → `docs/eksternal/hasil_news_pra.txt`. Data tick asli **Exness Cent (XAUUSDc)**
1.680 rilis 2015–2026 (1.431 dengan kejutan) dan **Dukascopy** 1.260 rilis 2010–2026 sebagai pembanding; semua berita
USD bintang 3. Hasil dalam $ per 0,01 lot (akun Cent: sen). Aturan ditetapkan sebelum melihat hasil (lihat docstring).

## Kesimpulan singkat

**Tidak bisa.** Kejutan tidak bisa ditebak cukup tepat, dan dalam 1–3 detik harga hampir belum bergerak. Dari 16 petunjuk yang
diuji, tidak ada yang untung di kedua feed, dan dengan eksekusi realistis semuanya rugi (0 lolos).

## 1. Jam feed benar (tidak ada kebocoran)

Gerak t0−5 → t0−1 searah kejutan: **50%** (Exness) / 46% (Dukascopy) = lempar koin. Jadi tidak ada yang "tahu lebih
dulu" di data ini, dan entry t0−1 benar-benar buta.

## 2. Kalau angka sudah diketahui: emas ke mana dan berapa jauh (Exness)

| Waktu | Searah kejutan (semua / LAMA / BARU) | Median gerak dari t0−1 |
|---|---|---|
| t0 (detik rilis) | 49% / 46% / 53% | $0,03 |
| t0+1 dtk | 65% / 64% / 67% | $0,17 |
| t0+2 dtk | **75%** / 73% / 78% | $0,50 |
| t0+3 dtk | **78%** / 76% / 80% | $0,65 |
| t0+10 dtk | 80% / 77% / 84% | $0,91 |

Spread Exness di t0−1: median **$0,26**. Dalam 1–2 detik pertama gerak median lebih kecil dari spread.

## 3. Batas atas: tebakan kejutan 100% benar (ORAKEL, Exness)

| Tutup setelah entry | Rata/0,01 lot (LAMA / BARU) | Tebakan benar minimal agar impas |
|---|---|---|
| 1 dtk (= t0) | −$0,32 (−0,42 / −0,19) | mustahil (harga belum bergerak) |
| 2 dtk (= t0+1) | +$0,04 (−0,27 / +0,48) | **95%** |
| 3 dtk (= t0+2) | +$0,52 (−0,09 / +1,34) | **72%** |
| 3 dtk, realistis (terisi 0,5 dtk kemudian + slippage $0,30) | +$0,14 (−0,45 / +0,94) | **94%** |
| tahan sampai t0+10 dtk | +$1,15 | 62% |

Dukascopy serupa: tutup 3 dtk butuh 77% (realistis 89%). Artinya, **walaupun tebakan selalu benar**, tutup 1–2 detik
tidak menghasilkan apa-apa. Tutup 3 detik baru untung bila tebakan benar ≥ 72–94%.

## 4. Seberapa tepat kejutan bisa ditebak sebelum rilis?

- Terbaik yang pernah terbukti (`docs/PERSIAPAN_BERITA.md`): hanya untuk CPI, arah kejutan benar **61–67%**,
  dan ±1/3 CPI keluar sama dengan perkiraan (15% rilis semua berita di Exness tanpa kejutan).
- Diuji langsung sebagai entry t0−1 (tutup 1/2/3 dtk, kedua feed): kejutan bulan lalu terulang (ULANG), "Act ke arah
  Prev", petunjuk CPI yang terbukti (P1 CPI, P7 bensin), ikut/lawan gerak harga 10–110 detik sebelum rilis, selalu
  BUY, selalu SELL → **tidak ada yang untung di kedua feed; dengan eksekusi realistis semuanya rugi** (tutup 3 dtk:
  Exness −$0,51 s.d. +$0,18, Dukascopy −$0,96 s.d. −$0,27 per 0,01 lot; lebih buruk pada 1–2 dtk). Satu-satunya angka
  positif, P1 Core CPI Exness tutup 3 dtk +$0,18, rugi di periode LAMA (−$0,29), realistis −$0,51, dan Dukascopy −$0,30.

## 5. Yang lebih masuk akal (tetap belum terbukti untung)

- Menebak sebelum rilis butuh ≥ 72% benar, dan yang tersedia ≤ 61–67% untuk CPI saja → **jangan entry sebelum rilis.**
- Arah baru jelas **setelah** angka keluar (75–80% searah kejutan dalam 2–10 detik), tetapi harus bereaksi ≤ 1 detik
  (`docs/NEWS_DETIK.md`: dengan reaksi 2 dtk + slippage hasilnya ≈ impas).
- Bila tetap ingin mencoba: lot minimum 0,01 di akun Cent, catat harga terisi nyata, dan hentikan bila 20 trade pertama
  rugi. Tidak ada janji profit.
