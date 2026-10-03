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

## 5. Bisa ditiru dengan target $150/bulan? (`research/tiru_150.py` → `docs/eksternal/hasil_tiru_150.txt`)

- Kalibrasi: aturan rekonstruksi + **jeda 30–45 menit antar keranjang** (EA asli lebih selektif; entry tetap acak)
  menghasilkan September 2026 dengan 1.401–1.886 trade dan profit tertutup $451–656 di modal $524 (laporan asli 1.792
  trade, +$426,55) → EA itu **bisa ditiru** cukup dekat. Jeda 30 mnt: 3× habis di September; 45 mnt: 0× (peka waktu).
- Per bulan kalender Jun 2012 – Sep 2026: akun baru tiap awal bulan, hasil = profit tertutup + floating akhir bulan,
  atau −modal bila habis. Lot awal & modal diskalakan bersama supaya median bulan selamat BARU ≈ $150.

| Pengaturan | Lot awal / modal | Bulan akun habis LAMA / BARU / 12 bln | Bulan ≥ $150 BARU | Rata-rata bersih/bulan LAMA / BARU | 1 akun selamat 12 bln LAMA / BARU (umur median) | Bersih median 1 akun BARU |
|---|---|---|---|---|---|---|
| Rasio trader (0,07/$524), jeda 30 | 0,10 / $749 | 15% / 37% / 75% | 38% | −$27 / −$59 | 15% / 0% (4,1 / 2,1 bln) | −$414 (ditarik $334) |
| Rasio trader, jeda 45 | 0,10 / $749 | 12% / 35% / 67% | 32% | −$5 / −$78 | 20% / 0% (5,3 / 2,1 bln) | −$387 (ditarik $361) |
| Rasio klaim 0,03/$524, jeda 30 | 0,07 / $1.223 | 7% / 25% / 50% | 35% | −$18 / −$107 | 33% / 8% (7,6 / 3,2 bln) | −$598 (ditarik $625) |
| Rasio klaim 0,03/$524, jeda 45 | 0,09 / $1.572 | 5% / 22% / 33% | 43% | +$1 / −$93 | 38% / 4% (8,7 / 3,5 bln) | −$799 (ditarik $773) |
| Selalu aktif (pembanding) | 0,06 / $449 | 16% / 52% / 100% | 27% | −$2 / −$69 | 15% / 0% (4,0 / 1,2 bln) | −$246 (ditarik $203) |

- Bulan yang selamat hampir tidak pernah rugi (0–7%) dan 12 bulan terakhir median bulan selamat $579–791 (emas sangat
  volatil) — inilah yang terlihat di laporan trader. Tetapi 22–37% bulan (BARU) berakhir dengan akun habis, sehingga
  rata-rata bersih per bulan negatif (−$59 s/d −$107); LAMA sekitar nol (−$27 s/d +$1). Satu-satunya angka positif:
  rasio klaim + jeda 45, 12 bulan terakhir +$71/bulan (4 dari 12 bulan tetap habis); total 2012–2026 varian itu −$5.428.
- Satu akun yang dijalankan terus: BARU hanya 0–8% bertahan 12 bulan (umur median 2–3,5 bulan); sempat menarik
  $334–773, lalu modal habis → bersih median −$387 s/d −$799.
- Jawaban: **bisa ditiru dan bisa menghasilkan ≥ $150 di sebagian bulan (32–43%), tetapi bukan $150 setiap bulan**;
  nilai harapannya negatif. Batasan: indikator asli tidak diketahui (jeda acak sebagai pendekatan); indikator yang
  benar-benar punya keunggulan bisa mengubah hasil, tetapi belum ada buktinya (laporan hanya 1 bulan, DD saldo saja).

## 6. Klaim "sudah jalan 6 bulan" (`research/klaim_6bulan.py` → `docs/eksternal/hasil_klaim_6bulan.txt`)

- Bukti yang ditunjukkan belum mencakup 6 bulan: setoran di screenshot pertama bertanggal 2026.09.1x (akun ±3 pekan),
  laporan MT5 "bulan lalu" 1 bulan (sumbu grafik = nomor trade), Telegram 1 keranjang.
- EA tiruan (5 pengaturan: rasio trader 0,07/$524 & rasio klaim 0,03/$524, jeda 30/45 mnt, + paling awet jarak $3)
  dimulai dari **setiap hari 15 Mar – 15 Apr 2026** sampai 2 Okt: **0 dari 32 tanggal mulai bertahan, di kelima
  pengaturan**. Habis pertama median 12 Apr (2 Apr untuk satu pengaturan), sempat menarik median $81–188.
- Kejadian yang menghabiskan akun Apr–Sep 2026 (dicek ulang di Twelve Data H1, sumber terpisah — semuanya nyata):
  12 Apr pembukaan mingguan (Jumat ±4.750 → jam pertama Minggu malam 4.644, data M5 4.585), 28 Mei (4.466 → 4.367
  dalam 5 jam), 10 & 19 Jun, 30 Jun (4.021 → 3.949 dalam 3 jam), 1 & 22 Jul, 26 Jul (lonjakan $104 di jam pembukaan
  mingguan), 14 Sep, 28 Sep (4.287 → 4.192 dalam 5 jam), 30 Sep. Pengaturan paling awet tetap kena 3 (12 Apr, 28 Mei,
  28 Sep); rasio trader 8–9.
- Jalan terus 1 Apr–2 Okt dengan setor ulang setiap habis: profit tertutup $907–3.530 tetapi setoran hilang
  $1.572–4.717 → **semua pengaturan negatif** (−$201 s/d −$1.187).
- Peluang bertahan 182 hari dari tiap Senin: LAMA 37–66%, BARU 4–44%; mulai tahun 2025 dan 2026: **0% di semua
  pengaturan** (2024: 0–40%).
- Kemungkinan penjelasan bila EA trader benar-benar jalan 6 bulan: (a) pengaturan lebih longgar/berbeda sebelum
  September (lot lebih kecil, jarak lebih lebar, tutup sebelum akhir pekan, jeda berita); (b) indikatornya kebetulan
  atau memang menghindari penurunan di atas (belum terbukti); (c) "6 bulan" = umur EA, bukan satu akun — akun yang
  habis diganti/disetor ulang (akun ke-2 di screenshot: setor $3.237, tarik $2.929); (d) beruntung. Bukti yang
  membedakan: statement lengkap 6 bulan per akun (semua setoran/penarikan) + grafik ekuitas (Myfxbook/FXBlue).

## 7. Filter "MARKET CRASH DETECTED" (`research/krisis_filter.py` → `docs/eksternal/hasil_krisis_filter.txt`)

- Bukti: notifikasi bot "Drop: $30.0 dalam 1 jam — Bot SKIP entry baru sampai volatilitas turun — cooldown sampai 21:05"
  pukul 20:13 dan 21:30 WIB. Detektor tulis-ulang (tertinggi 60 mnt − low ≥ $30) menyala **2 Okt 2026 13:15 dan 14:30
  UTC = 20:15 dan 21:30 WIB** (selisih 2 menit karena bar M5) → hari NFP, cocok.
- Diuji pada aturan rekonstruksi (0,07 lot/$524, ×1,2, jarak $2,25, TP +$1,9, jeda 45 mnt), jeda krisis 60 mnt mulai
  bar berikutnya:

| Kode | Pengaturan | BARU $/bln | BARU bulan akun habis | BARU bulan ≥ $150 | LAMA $/bln | 12 bln akhir $/bln |
|---|---|---|---|---|---|---|
| T0 | tanpa filter | −65 | 37% | 22% | −3 | −123 |
| T1 | filter "baru" (hanya tahan keranjang baru — sesuai teks notifikasi) | −69 | 37% | 22% | −3 | −143 |
| T2 | filter "beku" (juga tanpa layer baru) | −35 | 32% | 27% | −10 | +24 |
| T3 | filter "tutup" (keranjang ditutup saat krisis) | −18 | 18% | 15% | −5 | −97 |
| T4 | "beku" + tutup akhir pekan | −29 | 28% | 23% | −19 | +80 |
| Q1 | modal $400, ×1,2 0,05 lot, "beku" + akhir pekan | −22 | 27% | 15% | −7 | +45 |

- **Filter "tahan keranjang baru" saja tidak mengubah apa pun** (T1 ≈ T0): bahaya datang dari keranjang yang SUDAH
  terbuka saat penurunan mulai. Menahan layer baru (beku) atau menutup keranjang membantu, tetapi rata-rata 5 tahun
  tetap negatif.
- 12 bulan terakhir dengan "beku" + akhir pekan (Q1, $400): Okt–Feb +$247/+191/+205/+210/+162, Mar HABIS, Apr +205,
  Mei–Jul HABIS, Agu +218, Sep +237 → **8 dari 12 bulan $160–250 (cocok dengan klaim $150/bulan), 4 bulan akun habis**.
  Mulai 1 Agu / 1 Sep 2026 masih hidup sampai 2 Okt (+$477 / +$260) — persis seperti akun trader yang disetor
  September. Mulai 15 Mar–15 Apr 2026: tetap 0/32 bertahan sampai 2 Okt (habis 26 Mar / 27 Mei).
- Yang tetap menghabiskan akun meski ada filter (Q1, 2026): 26 Mar (−$91 dalam 6,8 jam), 27 Mei (−$92 dalam 11,7 jam),
  1 Jul (−$77 dalam 5,2 jam) = **penurunan pelan $8–15/jam yang tidak pernah memicu "$30 dalam 1 jam"**; 17 Jun (−$66
  dalam 30 mnt) = cepat (di MT5 tick demi tick filter menyala lebih awal daripada bar M5 di simulasi, jadi kejadian
  ini mungkin selamat di akun nyata).
- Kesimpulan: filter krisis membuat EA lebih awet di pasar yang meledak cepat dan menjelaskan mengapa akun trader bisa
  untung beberapa bulan; tetapi grid martingale tetap kalah oleh tren turun yang pelan dan panjang. Rata-rata 5 tahun
  negatif di semua tafsiran.
