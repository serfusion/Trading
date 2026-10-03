# Verifikasi "Signal Strike EA" (3 Okt 2026)

Bukti dari pengguna (trader yang sama dengan bagian akhir `docs/MARTINGALE.md`): notifikasi Telegram, 17 deal tutup,
dan laporan MT5 "bulan lalu". Klaim trader: layer yang minus selalu ditutup layer berikutnya, tidak pernah tutup minus,
minimal 0,03 lot, floating 2 jam lebih tetap aman, bot jalan 24 jam dan tetap entry saat berita kalau indikator memberi
sinyal. Skrip `research/signal_strike.py` → `docs/eksternal/hasil_signal_strike.txt` (aturan ditulis ulang, bukan kode
EA; data & mesin `research/martingale_ea.py`).

## 1. Rekonstruksi keranjang 2 Okt 2026 (terbukti dari angka)

- Telegram 07:05 & 09:05 WIB = 00:05 & 02:05 UTC: "BUY Entry | Lot 0.07 | 4177.890" lalu "+1274.85 USC, Balance
  53682.14 USC, TP HIT L17 + Close All". 17 deal ditutup 02:05:00–02:05:04 (Close All butuh 4 detik, harga bergeser
  4.155,48 → 4.155,08), urutan layar terbaru → terlama.
- Deal terakhir = L1: 0,07 × 100 × (4.177,890 − 4.155,084) = **159,64 → sama persis** dengan −159,64 USC. Deal dan
  Telegram berasal dari keranjang yang sama.
- Lot **×1,2 dibulatkan tiap layer** (0,07 → 0,08 → 0,10 → 0,12 → … → 1,24 di L17) adalah satu-satunya pengali yang
  membuat harga entry turun terus dengan jarak wajar. Pengali 1,1/1,15 membuat entry naik-turun, 1,25/1,3 membuat L17
  2,7–4,9 lot. Jarak antar layer $1,16–5,06 (median $2,05): tidak tetap, cocok dengan "masuk kalau indikator".

| Layer | Lot | Entry | Profit USC | | Layer | Lot | Entry | Profit USC |
|---|---|---|---|---|---|---|---|---|
| L1 | 0,07 | 4.177,890 | −159,64 | | L10 | 0,35 | 4.160,258 | −167,37 |
| L2 | 0,08 | 4.176,105 | −166,83 | | L11 | 0,42 | 4.158,158 | −112,65 |
| L3 | 0,10 | 4.174,102 | −188,51 | | L12 | 0,50 | 4.155,376 | +5,00 |
| L4 | 0,12 | 4.171,680 | −197,19 | | L13 | 0,60 | 4.153,395 | +106,68 |
| L5 | 0,14 | 4.169,880 | −205,75 | | L14 | 0,72 | 4.152,150 | +217,66 |
| L6 | 0,17 | 4.168,071 | −219,08 | | L15 | 0,86 | 4.148,872 | +537,50 |
| L7 | 0,20 | 4.166,204 | −220,40 | | L16 | 1,03 | 4.146,737 | +870,25 |
| L8 | 0,24 | 4.165,049 | −235,32 | | L17 | 1,24 | 4.141,677 | +1.700,91 |
| L9 | 0,29 | 4.162,549 | −205,12 | | | | | |

- 11 layer pertama tutup minus (−2.077,86 USC), 6 layer terakhir plus (+3.438,00) → **+1.360,14 USC** (Telegram
  +1.274,85; selisih 85 USC tidak terjelaskan: mungkin baris terpotong atau biaya). Total 7,13 lot, rata-rata entry
  4.153,37, ditutup di rata-rata **+$1,90**.
- Floating keranjang ini (saldo $524): di 4.141,5 −$85 (−16%), di 4.140 −$95 (−18%), di low Twelve Data 4.134,45 −$135
  (−26%). **Risiko floating $85–135 untuk untung $12,75.**
- Koreksi bacaan screenshot pertama: 1,03 / 1,24 / 1,49 / 1,79 = **L14–L17 rantai 0,10 × 1,2** (0,10 → 1,79 tepat di
  L17), keranjang yang sama (2 Okt 00:05–02:05) di akun lain; layer minusnya tersembunyi karena diurutkan Profit ▲.
  0,5 lot 17 Sep = L10 keranjang lain. Bukan "8 layer mulai 0,5 lot" seperti tulisan awal di MARTINGALE.

## 2. Klaim vs hasil verifikasi

| Klaim | Hasil |
|---|---|
| Layer minus ditutup layer berikutnya | **Benar sebagai hitungan** (11 minus ditutup 6 plus). Ini definisi averaging: lot makin besar menarik rata-rata entry turun sehingga pantulan ±$2 cukup. Bukan keunggulan; syaratnya harga memantul SEBELUM ekuitas habis. |
| Tidak pernah tutup minus | Benar menurut desain: keranjang hanya ditutup di TP. Kerugian tidak muncul sebagai "tutup minus", tetapi sekali sebagai stop out (seluruh saldo). |
| Minimal 0,03 lot aman | Lebih awet, bukan aman. Jarak $2,25: 0,03 lot/$524 habis ±L31 (emas turun ±$70 tanpa pantulan), 0,07 lot ±L27 (±$61), 0,10 lot/$430 ±L24 (±$54); tanpa layer baru ±$98 dari L1. |
| Floating 2 jam tetap aman | Lamanya floating bukan ukuran aman; yang menentukan kedalaman vs ekuitas (2 Okt: 17 layer, −16…−26%). |
| Bot 24 jam, tetap entry saat berita | Risiko terbesar. 2 Okt setelah NFP (emas 4.225 → 4.126 pukul 13:00–15:55): aturan hasil rekonstruksi yang selalu aktif → keranjang 18 layer selamat (−19%), lalu keranjang 26 layer **AKUN HABIS 15:45 UTC**. |
| Laporan bulan lalu (PF 2,83, DD 5,36%) | Laporan riwayat MT5 hanya menghitung **drawdown SALDO** (posisi tertutup), bukan ekuitas. DD maksimal 2.937,30 = persis "14 kalah beruntun −2.937,30" = layer minus satu keranjang yang ditutup berurutan saat Close All. Recovery factor 14,52 = 42.654,80 / 2.937,30 dan "drawdown absolut 0" karenanya menyesatkan. 14 layer minus → ada keranjang ±20 layer di September → floating ±−$127 (20 layer, −24%) s/d −$155 (21 layer, −30%) dari $524. |

- Profit bergantung pada keranjang dalam: keranjang ≥ 10 layer hanya 3% keranjang menang tetapi memberi ±50% profit
  (keranjang 1 layer +$0,13, 10–17 layer +$6,3). Bulan yang "bagus" justru bulan dengan banyak keranjang dalam yang
  kebetulan memantul.
- September 2026, EA selalu aktif dengan aturan rekonstruksi: 6.261 trade (laporan asli 1.792 → EA asli 3–4× lebih
  selektif), akun habis 8× (BUY saja) / 4× (dua arah) / 2× (0,03 lot). Pada keranjang yang selamat saja: DD saldo ala
  MT5 26–27% tetapi floating terdalam −81% s/d −100% (S2 16/09: selamat dengan sisa ekuitas hampir nol).

## 3. Uji 2012 – 2 Okt 2026 dengan aturan hasil rekonstruksi

Lot ×1,2 rekursif, TP rata-rata +$1,9, jarak tetap (pendekatan indikator), maks 40 layer, margin 1:2000, stop out 0%,
spread $0,20. "Per keranjang" = satu keranjang tiap 6 jam (tidak bergantung aturan entry); "akun baru" = EA selalu
aktif mulai tiap awal bulan, maks 1 tahun.

| Varian | Habis per keranjang LAMA / BARU / 12 bln | Harapan $/keranjang LAMA / BARU / 12 bln | Akun baru BARU: habis ≤ 30 / ≤ 90 hari, umur median |
|---|---|---|---|
| S1 BUY 0,07 lot, jarak $2,25, modal $524 | 1/338, 1/339, 1/108 | −0,79 / −0,85 / −3,81 | 52% / 87%, 26 hari |
| S2 sama, dua arah | 1/362, 1/271, 1/108 | −0,74 / −1,21 / −3,89 | 54% / 85%, 28 hari |
| S3 0,03 lot (klaim minimum) | 1/634, 1/603, 1/181 | −0,41 / −0,48 / −2,23 | 44% / 72%, 42 hari |
| S4 jarak $1,8 | 1/254, 1/236, 1/90 | −1,12 / −1,36 / −4,67 | 54% / 92%, 23 hari |
| S5 jarak $3 | 1/483, 1/543, 1/217 | −0,54 / −0,46 / −1,70 | 48% / 74%, 32 hari |
| S6 0,10 lot, modal $430 | 1/260, 1/259, 1/90 | −0,65 / −0,75 / −3,47 | 61% / 93%, 22 hari |
| S7 TP rata-rata +$5 | 1/67, 1/86, 1/64 | −2,63 / −1,49 / −3,41 | 57% / 93%, 22 hari |

- LAMA (akun baru < Okt 2021): S1 habis ≤ 1 tahun 85%, umur median 109 hari; S3 83%, 171 hari. Uang yang sempat
  ditarik sebelum habis (median) $183–365; bersih median −$153 s/d −$342 per akun di semua varian.
- Nilai harapan per keranjang **negatif di semua varian dan periode**; 12 bulan terakhir (emas sangat volatil) peluang
  habis per keranjang 2–3,5× lebih besar daripada LAMA/BARU (S1–S6; S7 hampir sama).

## 4. Kesimpulan & batasan

- Bukti trader konsisten (bukan rekayasa): EA = grid martingale lot ×1,2 per layer, TP keranjang rata-rata +$1,9,
  Close All. Profit nyata selama emas memantul sebelum ekuitas habis.
- Tidak masuk akal sebagai "tidak pernah rugi": nilai harapan negatif, dan laporan yang dipakai sebagai bukti tidak
  memuat floating. Bukti yang bermakna: grafik **ekuitas** (tautan Myfxbook/FXBlue dengan investor password) atau
  Strategy Tester "Every tick based on real ticks" 2020–2026 yang menampilkan **Equity Drawdown Maximal**, termasuk
  Jan–Mar 2026 dan 2 Okt 2026.
- Batasan: aturan indikator tidak diketahui (jarak tetap sebagai pendekatan; EA asli lebih selektif → umur akun lebih
  panjang daripada versi "selalu aktif", peluang per keranjang dalam tetap); TP keranjang dangkal tidak diketahui (uji
  TP +$5 = S7); bar M5/M15 (uji M1 vs M5 Feb–Mei 2026 mirip); feed Twelve Data ≠ Exness (low 2 Okt lebih dalam: ulang
  keranjang 00:05 → TP 01:30, 20 layer, +$23,86, floating −$155).
- TIDAK dipasang di bot (martingale tetap menunggu "pasang" dari pengguna).
