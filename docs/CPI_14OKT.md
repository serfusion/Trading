# 🎯 Analisa CPI 14 Okt 2026 + semua berita besar (dan entry 1 detik sebelum rilis)

Permintaan pengguna 10 Okt 2026 (URGENT): CPI berikutnya selalu terbaru, perhatikan pernyataan pemimpin/negara yang bisa
mengubah peluang, gabungkan semua sumber yang menambah ketepatan, telusuri berita lain, dan uji entry 1 detik sebelum
rilis. Angka di bawah per **10 Okt 2026 16:40 WIB**; aplikasi memperbarui sendiri (pasar tiap 15 menit).

## 1. Fakta rilis
- **CPI September 2026: Rabu 14 Okt 2026, 19:30 WIB** (08:30 New York). Core CPI & CPI y/y rilis bersamaan.
- Konsensus (preview media, BELUM dari ForexFactory — FF memuat pekan depan pada Minggu): headline m/m **0,6%**
  (y/y 3,7% dari 3,4%), core m/m **0,2%** (y/y ±2,5%). Penggerak: harga bensin/energi rekor (perang Iran).
- Bulan lalu (Agu, rilis 11 Sep): headline 0,4% = konsensus 0,4%; core **0,3% > konsensus 0,2%** (kejutan di atas).
- Konteks: Fed menaikkan bunga 16 Sep (3,75–4,00%); notulen 7 Okt: "kenaikan lagi kemungkinan"; keputusan Fed berikut
  28 Okt. Pidato pekan depan: Hammack (Sen 12), Bowman (Rab 14), Ketua Fed Warsh (Kam 15).

## 2. Pasar & nowcast (data langsung)
| Sumber | Headline m/m | Core m/m |
|---|---|---|
| Kalshi (pasar uang sungguhan) | paling mungkin 0,6% (39%); ≥ 0,5%: 92%; ≥ 0,6%: 58%; ≥ 0,7%: 19% | 0,2% (42%); ≥ 0,3%: 36%; ≤ 0,1%: 21% |
| Nowcast Cleveland Fed (9 Okt) | 0,53% | 0,20% |
| Kalshi y/y | ≥ 3,7%: 44% (cenderung di bawah konsensus 3,7%) | – |

Bila konsensus FF = 0,6%: Kalshi condong headline **DI BAWAH** (41% vs 19% di atas) dan core **DI ATAS** (36% vs 21%).
Bila konsensus FF = 0,5%: headline condong **DI ATAS** (59% vs 8%), core tetap di atas.

## 3. Sumber mana yang benar-benar menambah ketepatan (research/cpi_gabung.py, berita_gabung.py; 2010–2025)
Tebakan ARAH ANGKA (Act vs konsensus), tanpa look-ahead:

| Sumber | CPI headline | Core CPI |
|---|---|---|
| Kalshi 1 jam sebelum rilis | **76%** (16/21) | **75%** (15/20) |
| Kalshi & kejutan bulan lalu SEPAKAT | 80% (8/10) | 80% (8/10) — gabungan **80% (16/20)** |
| Kejutan bulan lalu (searah) | 62% (47/76) | 67% (47/70) |
| Bensin bulan acuan | 61% (lama 64%, sejak 2021 52%) | – |
| Nowcast Cleveland Fed | 57% ≈ lempar koin | 56% ≈ lempar koin |
| Semua digabung (suara) | 64–65% — **lebih rendah** dari Kalshi saja | 62–67% |

Kesimpulan: menggabungkan sumber lemah MENURUNKAN ketepatan; yang dipasang = Kalshi, ditandai bila sepakat dengan kejutan
bulan lalu (80%).

**Yang paling penting:** tebakan arah ANGKA ≠ arah EMAS. Diuji ujung-ke-ujung (tebakan → emas 1 menit setelah rilis):
Kalshi CPI 65% (20/31), core 54%, Kalshi & kejutan lalu sepakat 65% (13/20). Emas tidak selalu searah kejutan.

## 4. Reaksi emas 1 menit per skenario (Dukascopy, rilis CPI 2010–2025; headline × core)
| | core DI BAWAH | core SAMA | core DI ATAS |
|---|---|---|---|
| headline DI BAWAH | 89% naik (n 36) | 65% naik (17) | 80% naik (5) |
| headline SAMA | 84% naik (19) | 56% naik (27) | 33% naik (15) |
| headline DI ATAS | 80% naik (5) | 33% naik (18) | **9% naik (23)** |

Dikalikan peluang Kalshi saat ini:
- konsensus 0,6%: emas 1 menit **±59–62% NAIK** (lemah — skenario terbanyak "sama/sama" & "bawah/atas" bertentangan);
- konsensus 0,5%: **±56–58% TURUN** (lemah); bila nanti angka keluar "headline & core di atas" → historis 91% turun.
- Arah 3 & 6 JAM setelah CPI di atas perkiraan: emas justru NAIK 63–64% (berbalik) — jangan tahan SELL terlalu lama.

## 5. Pernyataan penting yang bisa mengubah peluang (dipantau otomatis)
- Pasar prediksi (Kalshi/Polymarket) bereaksi dalam menit pada pernyataan Fed/Trump/negara; aplikasi membaca ulang tiap
  15 menit dan menandai **⚠️ "peluang bergeser X% → Y%"** bila berubah ≥ 5 poin dalam 24 jam.
- 🗣️ Daftar judul terbaru (RSS resmi Fed + Google News) di kartu 🎯 — 10 Okt: Trump mencabut sanksi diesel Rusia/kesepakatan
  dengan Putin untuk menekan harga BBM (energi = penggerak CPI); Trump: tidak menyerang Iran sebelum pemilu sela; notulen
  Fed: kenaikan bunga lagi kemungkinan. Arah tidak ditebak dari kata-kata (bisa dua arah); angka pasar yang dipakai.

## 6. Entry 1 DETIK SEBELUM rilis (research/pra_gabung.py → docs/eksternal/hasil_pra_gabung.txt)
Tick asli Dukascopy (2010–2026) & Exness Cent (2015–2026), BUY di ASK / SELL di BID pada t−1 detik, slippage $0,30 (realistis):
- Tutup 1 detik: rugi di SEMUA petunjuk (WR 0–20%) — spread & gap saat rilis memakan seluruh gerak.
- Tutup 3–60 detik: ≈ impas/rugi; "kunci untung $1" WR 57–71% tetapi rata-rata rugi (kalah jauh lebih besar).
- Kandidat satu-satunya: **CPI saat Kalshi & kejutan lalu sepakat**, tutup 10–30 detik: WR 65–70%, +$0,30…+0,80 per
  0,01 lot (realistis) di kedua feed, tetapi n 20 dan t < 1 → BELUM TERBUKTI.
- 0 aturan lolos di kedua feed. Riset lama (NEWS_PRA/NEWS_PRA2: 11.116 kombinasi) juga 0 lolos.
- Yang terbukti justru SETELAH angka keluar: arah emas di detik 2–3 searah hasil 82–91% (HARI_H bagian 6) — bila Anda bisa
  bereaksi dalam 1–2 detik setelah Act terlihat, itu lebih aman daripada menebak 1 detik sebelumnya.

Untuk 14 Okt: petunjuk terkuat (core: Kalshi & kejutan lalu sepakat DI ATAS → SELL) BERTENTANGAN dengan headline (Kalshi
condong DI BAWAH bila konsensus 0,6% → BUY); historis "headline bawah + core atas" emas naik 4 dari 5. **Tidak ada setup
kuat**. Bila tetap entry t−1: lot minimum, tutup cepat (10–30 detik), siap rugi spread. Cek ulang hari Minggu setelah
konsensus FF terbit — aplikasi menghitung ulang otomatis; bila konsensus headline 0,5%, setup SELL menjadi lebih jelas.

## 7. Berita lain (research/berita_gabung.py → docs/eksternal/hasil_berita_gabung.txt, cloud/api/petunjuk.json)
| Berita | Petunjuk yang lolos (arah angka) | Arah emas 1 menit bila diikuti |
|---|---|---|
| GDP advance | GDPNow Atlanta Fed vs konsensus 67% (sejak 2021: 14/15) | 54% |
| Pengangguran (hari NFP) | Kalshi, cadangan kejutan lalu 61% | **60%** (77/129, konsisten lama & baru) |
| CPI y/y | kejutan lalu searah 63% | 51% |
| ISM Jasa | kejutan lalu **berbalik** 64% (lama 63%, baru 70%) | 61% (n 23) |
| Core PPI | berbalik 60% | 55% |
| JOLTS | berbalik 58% | 49% |
| NFP, PPI, Retail Sales, Core PCE, ISM Manufaktur, klaim, ADP, upah | tidak ada yang lolos | ≈ lempar koin |

Semua ditampilkan di aplikasi sebagai blok **🧭 Petunjuk teruji** (ketuk baris berita) dengan dua angka: ketepatan arah
angka dan ketepatan arah emas. Batas jujur: arah emas 1 menit SEBELUM rilis paling tinggi ±60–65%.

## 8. Sumber lain selain Kalshi (research/sumber_lain.py → docs/eksternal/hasil_sumber_lain.txt)
Diuji 2010–2025 dengan tanggal terbit (vintage FRED): breakeven 5 th, yield 2 th, minyak WTI, survei Fed daerah (harga yang
dibayar, karyawan, aktivitas), ekspektasi inflasi UMich, klaim berlanjut, indeks ekonomi mingguan, lowongan Indeed.
| Berita | Sumber lain yang lolos | Digabung (sepakat) |
|---|---|---|
| CPI headline | **minyak WTI** bulan acuan 62% (lama 60%, baru 67%) | Kalshi/kejutan lalu & WTI sepakat **76%** (32/42) vs 65% |
| CPI y/y | WTI 62% (baru 74%) | kejutan lalu & WTI 68% |
| Pengangguran | lowongan Indeed 67%, karyawan Fed daerah 60% | Kalshi/kejutan lalu & Indeed **75%** (27/36) |
| ISM Jasa | aktivitas Fed daerah 62% | berbalik & aktivitas Fed **73%** (35/48) vs 64% |
| NFP, PPI, core PCE, ISM manufaktur, JOLTS, Retail, GDP | tidak ada | – |
Polymarket juga punya pasar CPI bulanan, tetapi baru ±8 bulan (2026) dan arsip konsensus kita berhenti Jan 2026 → belum
bisa diuji (info saja). Truflation/PriceStats tidak punya data historis gratis.
WTI September $97,3 vs Agustus $83,9 (+16%) → CPI headline condong DI ATAS. Bila konsensus FF 0,5%: Kalshi, kejutan lalu
& minyak sepakat DI ATAS (historis 76%). Bila 0,6%: Kalshi DI BAWAH vs minyak DI ATAS → bertentangan.

## 9. Rencana pengguna: entry 1 detik sebelum, tutup 1–5 detik / 1–5 menit — XAU, BTC, ETH (research/pra_aset.py)
Tick Dukascopy & Exness (XAU), Binance & Exness (BTC), Binance 1 detik (ETH, diunduh 934 rilis); slippage realistis.
Arah = petunjuk teruji tiap berita. Hasil terbaik (keluar dipilih dari periode lama):
| Berita | XAU ($/0,01 lot) | BTC | ETH |
|---|---|---|---|
| CPI | tutup 1 mnt: untung 43%, rata −$1,18 | 4 mnt: 30%, −0,27% | 4 mnt: 37%, −0,11% |
| NFP | 1 mnt: 54%, −$0,43 | 1 mnt: 35%, −0,14% | 5 mnt: 41%, −0,08% |
| PPI | 1 mnt: 36%, −$0,31 | 4 mnt: 28%, −0,14% | 1 mnt: 32%, −0,00% |
| ISM | 5 dtk: 40%, −$0,31 | 4 mnt: 26%, −0,21% | 5 mnt: 34%, −0,13% |
| GDP | 2 mnt: 31%, −$0,44 | 1 mnt: 11%, −0,28% | 3 mnt: 29%, −0,18% |
Tutup 1–5 DETIK selalu lebih buruk (spread + slippage > gerak awal; BTC/ETH untung 0–30% rilis). 0 yang teruji positif.
Angka per berita berikutnya tampil di bawah tile XAU · BTC · ETH (aplikasi 4.27, 🔴 = rata-rata rugi).

## 10. KHUSUS XAU: arah 1–10 detik setelah rilis (naik/turun saja) — research/pra_xau_arah.py
Permintaan pengguna: bukan untung/rugi, hanya apakah harga XAU 1–10 detik setelah rilis bergerak searah tebakan sebelum
rilis. Harga tengah 1 dtk sebelum vs 1/2/3/5/10 dtk sesudah, tick Exness (Dukascopy pembanding):
| Tebakan sebelum rilis | 1 dtk | 2 dtk | 3 dtk | 5 dtk | 10 dtk | Catatan |
|---|---|---|---|---|---|---|
| ISM Jasa: berbalik dari kejutan lalu | 66% | 65% | 65% | 64% | 63% | ✅ konsisten lama & baru, n 107 |
| ISM Jasa: + aktivitas Fed daerah sepakat | 75% | 75% | 72% | 72% | 66% | ✅ (detik 1–5), n 32 |
| CPI: Kalshi & kejutan lalu sepakat | 45% | 65% | 65% | 65% | 70% | ⚠️ n 20 (2022–2025) |
| CPI: Kalshi saja | 51% | 57% | 57% | 60% | 63% | ⚠️ n 35 |
| CPI: + minyak WTI sepakat | 59% | 61% | 61% | 57% | 61% | ⚠️ n 44 |
| CPI: minyak WTI saja | 56% | 59% | 56% | 53% | 55% | lemah, n 122 |
| GDP: GDPNow | 35% | 46% | 51% | 57% | 66% | hanya detik 10 |
| NFP, Core PPI, JOLTS | 40–55% | | | | | ≈ lempar koin |
Detik 1 sering belum bergerak berarti (< $0,30) sehingga untuk CPI angkanya acak; detik 2–10 lebih stabil.
Tampil di aplikasi 4.27 sebagai satu baris XAU di bawah tile ("XAU TURUN ▼ • benar 65–70% (2–10 dtk) ⚠️"), diperbarui
otomatis (konsensus FF hari Minggu → Kalshi ikut dihitung).

## Sumber
- Kalshi API (KXCPI, KXCPICORE, KXCPIYOY), nowcast Cleveland Fed (`nowcast_month.json`), GDPNow Atlanta Fed, FRED.
- Preview konsensus & konteks: admiralmarkets.com (US CPI September 2026 Preview), fxstreet.com (TD Securities core CPI),
  mitrade.com (US September CPI preview), cnbc.com (CPI Agustus 2026), kiplinger.com (kalender 12–16 Okt),
  federalreserve.gov (pidato Jefferson 1 Okt), coindesk.com & finance.yahoo.com (kripto 8 Okt).

## Putaran 2: petunjuk CPI baru (11 Okt 2026 — `research/cpi_petunjuk2.py`, `docs/eksternal/hasil_cpi_petunjuk2.txt`)
Permintaan: "cari lagi petunjuk yang menaikkan persentase CPI, cek mundur". 8 petunjuk BARU, aturan tanda ditetapkan sebelum
melihat hasil, semua sudah terbit sebelum rilis. Lolos = > 50% di LAMA (< Okt 2021) & BARU, n ≥ 8, p < 0,05.

| Petunjuk | Berita | Semua | LAMA | BARU | |
|---|---|---|---|---|---|
| **YOY** konsistensi y/y: y/y tersirat (y/y lalu + m/m konsensus − m/m bulan sama tahun lalu) vs konsensus y/y, selisih ≥ 0,05 | CPI y/y | **71%** (57/80, p < 0,001) | 73% | 67% | ✅ |
| YOY versi indeks NSA (tanpa revisi musiman) | CPI y/y | **74%** (55/74) | 79% | 62% | ✅ cek ketahanan |
| YOY, bila 0 pakai kejutan bulan lalu | CPI y/y | **72%** (81/112) | 73% | 71% | ✅ naik dari 63% (P saja) |
| **DSL** solar rata-rata bulan acuan naik | CPI m/m | 63% (74/117) | 64% | 61% | ✅ (mirip bensin 61% — tumpang tindih) |
| **KON** konsensus < angka bulan lalu → di atas | Core CPI | 65% (44/68) | 65% | 63% | ✅ |
| KON & kejutan lalu sepakat | Core CPI | 69% (41/59) | 70% | 69% | ✅ |
| PPI rilis lebih dulu (≤ 10 hari) | CPI/y/y | 62–64% | 63–64% | n 4–5 | ✗ BARU terlalu sedikit (PPI kini rilis setelah CPI) |
| Upah NFP, musiman, avtur, gas alam | semua | 45–56% | – | – | ✗ ≈ acak |

Arti YOY: konsensus y/y dan m/m sering dibuat terpisah dan dibulatkan; aritmetika indeks (efek basis tahun lalu) membuka
selisihnya. Per tahun 2010–2025 YOY benar ≥ 50% di 13/16 tahun (2010 0/3, 2017 1/4, 2021 2/5 lemah). Kalshi tetap terkuat
untuk m/m (76%, hanya 2022–2025). Banyak uji (19 baris) → satu lolos bisa kebetulan; YOY paling meyakinkan karena ada alasan
mekanis dan lolos dua versi data. Ini arah ANGKA, bukan arah emas (emas 1 menit hanya ±55–65% searah kejutan).

**CPI 14 Okt (Sep 2026):** y/y Agu 3,40% (NSA). Bila konsensus FF m/m 0,6% & y/y 3,7% → tersirat 3,66–3,71% → selisih
< 0,05 → YOY diam (pakai kejutan lalu: y/y Agu = konsensus → diam). Bila m/m 0,5% & y/y 3,7% → tersirat 3,56–3,61% →
**y/y condong DI BAWAH**. Core: konsensus 0,2% < Agu 0,3% dan kejutan lalu di atas → KON & P sepakat **core DI ATAS (69%)**.
BELUM dipasang di cloud/aplikasi — tunggu "pasang".
