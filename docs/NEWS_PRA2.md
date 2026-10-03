# Entry 1 detik sebelum rilis, tutup 1 detik s.d. 3 menit — semua cara yang bisa diuji (30 Sep 2026)

Permintaan pengguna: "1–60 detik ke depan akan saya close atau 1–3 menit boleh, tapi saya memprioritaskan sebelum
1 detik news keluar saya akan entry … silahkan cari uji metodenya". Lanjutan `docs/NEWS_PRA.md`.

Skrip `python -m research.news_pra2` → `docs/eksternal/hasil_news_pra2.txt`. Tick asli **Exness Cent** 1.680 rilis
(2015–2026) dan **Dukascopy** 1.260 rilis (2010–2026), semua berita USD bintang 3. Eksekusi CEPAT (tanpa slippage),
REALISTIS (terisi 0,5 dtk kemudian + slippage $0,30 saat masuk dan keluar), STRES ($1). 28 cara keluar: tutup 1–180 dtk,
atau "tutup begitu untung ≥ $0,5/1/2/3" (maks 60/180 dtk, dengan/tanpa SL $3). Hasil $ per 0,01 lot.

## Kesimpulan

**Arah kejutan tidak bisa ditebak sebelum rilis dengan ketepatan yang dibutuhkan.** 11.116 kombinasi (cara × cara keluar
× grup berita) diuji; **0 lolos di kedua feed**. Satu-satunya kandidat, straddle ±$1–2 di feed Exness, rugi di Dukascopy
dan ≈ impas dengan eksekusi realistis → belum terbukti.

## 1. Berapa tepat tebakan yang dibutuhkan (ORAKEL = arah kejutan diketahui 100%)

| Tutup setelah entry | Hasil bila tebakan selalu benar (Exness CEPAT / REALISTIS) | Tebakan benar minimal agar impas (CEPAT / REALISTIS) |
|---|---|---|
| 1 dtk | −$0,32 / −$0,57 | mustahil |
| 3 dtk | +$0,52 / +$0,14 | 72% / 94% |
| 10 dtk | +$1,15 / +$0,54 | 62% / 82% |
| 60 dtk | +$1,40 / +$0,80 | 61% / 78% |
| 3 menit | +$1,52 / +$0,92 | 59% / 75% |
| tutup begitu untung ≥ $1 (maks 60 dtk) | +$0,64 / +$0,39 | 76% / 87% |

Dukascopy serupa (60 dtk: 61% / 75%). "Tutup begitu untung" butuh tebakan LEBIH tepat karena untungnya dipotong kecil.

## 2. Seberapa tepat petunjuk sebelum rilis menebak arah kejutan (rilis yang punya kejutan)

| Petunjuk (sumber) | Exness | Dukascopy |
|---|---|---|
| ANCHOR — konsensus tertambat ke angka sebelumnya (Campbell & Sharpe 2009) | 51,9% (LAMA 53,6 / BARU 49,9) | 51,7% |
| MOMENTUM kejutan 30 hari (gaya indeks kejutan Citi) | 50,3% | 54,1% |
| DRIFT harga 15 / 30 / 60 menit sebelum rilis (Kurov dkk. 2019) | 53,2 / 52,0 / 51,1% | 52,5 / 49,3 / 50,7% |
| ADP besar → NFP | 42,2% | 44,6% |
| Kejutan bulan lalu terulang (semua berita) | 48,8% | 49,1% |
| Gerak harga 10–110 dtk sebelum rilis (ikut / lawan) | 47,7–52,3% | 46,9–53,1% |
| Kejutan CPI bulan lalu (khusus CPI, n 58–90) | 59,0–63,8% | 55,6–60,7% |
| MODEL regresi logistik walk-forward (semua fitur di atas) | 52,7% (yakin ≥ 55%: 51,3%) | 52,6% (52,6%) |

Semua jauh di bawah 59–94% yang dibutuhkan. Temuan literatur tidak berlaku untuk emas di data ini: bias anchoring
kecil, dan Campbell & Sharpe sendiri menemukan pasar sudah memperhitungkannya; drift pra-rilis Kurov (futures saham &
obligasi 2008–2014) hanya 51–53% di emas.

## 3. Cara tanpa menebak arah (disiapkan sebelum rilis)

| Cara | Exness CEPAT (LAMA / BARU) | Exness REALISTIS | Dukascopy CEPAT / REALISTIS |
|---|---|---|---|
| STRADDLE ±$1 dipasang t0−1, tutup 60 dtk | +$0,48 (+0,08 / +0,83), 75% tahun positif | −$0,10 | −$0,17 / −$0,76 |
| STRADDLE ±$1, tutup 3 menit | +$0,57 | −$0,03 | −$0,13 / −$0,73 |
| STRADDLE ±$2, tutup 3 menit, "perlindungan gap" Exness (gap ≤ $0,50 diisi di level) | +$0,79 (+0,01 / +1,24) | +$0,19 | +$0,11 / −$0,49 |
| HEDGE (BUY + SELL di t0−1, sisi rugi ditutup t0+1…5 dtk) | −$0,32 s.d. −$0,70 | −$1,6 s.d. −$1,9 | −$0,9 s.d. −$1,4 |

- Straddle positif di tick Exness tetapi rugi di Dukascopy untuk periode yang sama, persis seperti temuan pending ±$1 di
  `docs/NEWS_DETIK.md`. Penyebab yang mungkin: cara broker mengutip harga di detik lonjakan. Tick historis bukan harga
  eksekusi, jadi hanya uji maju yang bisa memastikan.
- Hedge selalu rugi: membayar dua spread, dan sisi yang ditutup terlambat sudah rugi besar.

## 4. Info broker (Exness) yang relevan

- Leverage posisi baru dibatasi **1:200** dari 15 menit sebelum sampai 5 menit sesudah berita penting (akun non-ECN).
- Exness mengklaim ±90% order stop diisi di harga yang diminta walau ada gap "sedang" dan tanpa stop level; besarnya
  "sedang" tidak disebut → di uji ini diasumsikan ≤ $0,50 (varian "di level").
- Spread XAUUSDc median di t0−1: $0,26.

## 5. Saran

- Jangan entry arah (BUY/SELL) 1 detik sebelum rilis: tebakan terbaik ±53%, butuh ≥ 59% bahkan dengan eksekusi sempurna.
- Bila tetap ingin mencoba "disiapkan sebelum rilis": satu-satunya kandidat adalah **straddle ±$1–2 dipasang sesaat
  sebelum rilis, tutup 1–3 menit**, di akun Cent dengan lot minimum, catat harga terisi nyata (slippage) tiap rilis, dan
  berhenti bila 20–30 rilis pertama rugi. Ini BELUM terbukti; tidak ada janji profit.
