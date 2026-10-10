# ⏱️ XAU 1–10 detik setelah rilis: tebakan sebelum rilis & kepastian setelah detik 2 (10 Okt 2026)

Permintaan pengguna: entry 1 detik sebelum rilis; yang dibutuhkan hanya ARAH XAU 1–10 detik setelah rilis (naik/turun,
bukan untung/rugi), semua berita — terutama NFP, PPI, JOLTS — "hitung yang benar-benar pasti". Harga tengah (bid+ask)/2
1 detik sebelum rilis dibanding detik 1/2/3/5/10 sesudahnya; tick Exness (broker pengguna) 2015–2026, Dukascopy pembanding.
Skrip: `research/pra_xau_arah.py`, `research/pra_xau_dalam.py` → `docs/eksternal/hasil_pra_xau_{arah,dalam}.txt`.

## A. Tebakan SEBELUM rilis (yang bisa dipakai untuk entry t−1)
| Berita | Petunjuk terbaik | Arah XAU benar (detik 2–10) | Status |
|---|---|---|---|
| ISM Jasa | kejutan bulan lalu berbalik | 63–65% (n 107), + survei Fed daerah sepakat 66–75% | ✅ konsisten lama & baru |
| CPI | Kalshi & kejutan bulan lalu sepakat | 65–70% (n 20) | ⚠️ sampel kecil |
| Core PPI | kejutan core CPI pekan itu (CPI rilis ≤ 10 hari sebelumnya) | 57–65% (n 23; Dukascopy 61–70%) | ⚠️ |
| PPI (headline+core) | kejutan CPI pekan itu | 51–59% (n 39) | ⚠️ lemah |
| GDP | GDPNow | hanya detik 10: 66% | ⚠️ |
| **NFP** | 10 sumber diuji (kejutan lalu, ADP, klaim, Kalshi, Indeed, survei Fed, periode pengumpulan BLS, musiman bulan, anchoring) | 35–57% | ❌ tidak ada |
| **JOLTS** | Indeed (bulan acuan benar = 2 bulan sebelum rilis), kejutan lalu, klaim, musiman, anchoring | 41–55% | ❌ tidak ada |
Kesimpulan jujur: sebelum rilis, arah XAU detik 1–10 paling baik ±60–75% untuk sebagian berita; NFP & JOLTS ≈ lempar koin.

## B. Yang hampir pasti: lihat detik 2 (setelah entry)
Bila harga XAU di detik 2 sudah bergerak ≥ $0,50 dari harga 1 detik sebelum rilis, arah itu masih sama di detik 10 pada:
| Berita | detik 2 ≥ $0,50 → detik 10 sama | n | detik 1 ≥ $0,50 → detik 10 sama | n |
|---|---|---|---|---|
| Semua berita | **91,8%** | 839 | 84,8% | 525 |
| NFP | 94,7% | 95 | 82,1% | 28 |
| CPI | 89,4% | 85 | 65,8% | 38 |
| PPI | 87,0% | 69 | 73,9% | 23 |
| Retail Sales | 89,2% | 65 | 95,7% | 46 |
| JOLTS | 100% | 18 | – (sedikit) | – |
| ISM | 96,9% | 161 | 92,8% | 152 |
| ADP | 93,1% | 58 | 81,5% | 27 |
| Fed | 83,0% | 47 | 60,0% | 25 |
| Klaim pengangguran | 83,6% | 67 | 79,3% | 58 |
Gerak ≥ $1 di detik 2 → 94,2% (semua berita, n 620); ≥ $2 → 96,6% (n 325).
Cara pakai: entry t−1 dengan tebakan; di detik 2 lihat emas: sudah ≥ $0,50 searah posisi → tahan s/d detik 10;
berlawanan ≥ $0,50 → tutup segera (arah itu yang hampir pasti berlanjut). Gerak < $0,50 di detik 2 = belum jelas.

## C. SEMUA berita, SEMUA metode sebelum rilis (10 Okt sore — `research/pra_xau_semua.py`)
Permintaan: "2 detik terlalu lambat — candle 1 detik setelah rilis bot sudah entry; prediksi arah XAU SEBELUM news
apa pun". 2.051 rilis USD 2010–2026 (tick Exness 1.680, Dukascopy 1.260), target = harga tengah t0−1 → t0+1/2/3/5/10 dtk.
Semua petunjuk diambil KETAT ≤ 1 detik sebelum rilis.

**Koreksi penting**: putaran pertama memberi "tren 4 jam 60–72%" — ternyata BOCOR (candle H1 yang dipakai untuk rilis
jam :30 belum tutup, jadi ikut berisi harga setelah rilis). Setelah diperbaiki (hanya candle M15 yang sudah tutup, harga
"sekarang" dikoreksi ke t0−1) angka turun ke 53–56%. Hasil di bawah adalah versi KETAT.

| Metode (semua berita) | Benar di periode BARU (≥ Okt 2021), 1 / 3 / 10 dtk | Catatan |
|---|---|---|
| Petunjuk berita teruji (Kalshi, kejutan lalu, berbalik, WTI, Fed daerah, GDPNow, CPI→PPI) | 56 / 58 / 60% (n 130) | lama 54–60%, 9/10 tahun ✅ — satu-satunya yang konsisten |
| Gerak tick 10 / 30 / 120 dtk terakhir, tick terakhir | 48–55% | ≈ lempar koin |
| BTC 10 / 60 dtk terakhir (Binance 1 dtk) | 47–52% | tidak memimpin emas |
| Konsensus vs angka bulan lalu; kejutan rilis lalu (18 judul) | 47–51% | ≈ lempar koin |
| Gerak emas 15 mnt / 60 mnt | 52–54% | lemah |
| Tren emas 4 jam / 24 jam / EMA 50 H1 / EMA 200 H1 | 51–55% (lama 53–55%) | lemah tetapi searah di 2 periode |
| Arah mayoritas jenis berita (walk-forward) / arah rilis lalu | 50–55% | ≈ lempar koin |
| Model walk-forward (logistik, gradient boosting) semua fitur | 51–56%; subset "yakin" p ≥ 0,65: 53–62% (n 42–154) | lama 49–56% → tidak stabil |
| Gabungan suara semua aturan yang bagus di lama | 53–56% | |

Uji acak (permutasi 100×, hasil diacak di dalam tiap jenis berita): dari 702 kombinasi jenis berita × petunjuk × detik,
"lolos" karena kebetulan rata-rata 7,5 (95% ≤ 15); sungguhan 10 → **secara keseluruhan tidak lebih baik dari kebetulan**.
Yang tetap dipercaya hanya yang punya dasar & teruji sebelumnya (petunjuk berita, terutama ISM Jasa).

**Gabungan petunjuk berita × tren emas 4 jam** (ditemukan setelah melihat data → perlu uji maju; pola sama bila tren
diganti 24 jam atau EMA 50 H1):
| | 2–10 dtk benar | n | lama / baru |
|---|---|---|---|
| Petunjuk & tren 4 jam SEARAH (semua berita berpetunjuk) | **63–67%** | 142 | 62–69% / 59–66% |
| — ISM Jasa | **70–76%** (detik 1: 78%) | 46 | 67–78% / 74–79% |
| — CPI | 58–62% | 55 | 60–67% / 44–60% (tidak menambah untuk CPI) |
| Petunjuk & tren BERLAWANAN | 49–55% | 124 | ≈ lempar koin → lebih aman tidak entry |
| Berita TANPA petunjuk (NFP, Fed, retail, klaim, JOLTS, …): tren 4 jam saja | 55–56% | 1.410 | 57–58% / 52–54% (lemah) |

Kesimpulan jujur: untuk sebagian besar berita, arah XAU detik 1–10 tidak bisa ditebak lebih baik dari ±55% sebelum
rilis — reaksi ditentukan oleh angka yang baru keluar, dan konsensus pasar sudah memperhitungkan informasi publik.
Peluang terbaik: berita berpetunjuk teruji yang SEARAH dengan tren emas 4 jam (63–67%, ISM Jasa ±75%); bila berlawanan
atau tanpa petunjuk ≈ 50–55%. Hasil lengkap: `docs/eksternal/hasil_pra_xau_semua.txt` & `hasil_pra_xau_tren.txt`.

## Di aplikasi (4.27–4.28)
Satu baris di bawah tile XAU: arah tebakan + persen per detik (✅/⚠️/⚪) dan baris 📌 kepastian detik 2 untuk berita
berikutnya (cloud `_pra_aset.py`; PPI memakai kejutan CPI yang baru keluar lewat memori `_petunjuk`).

## Di aplikasi 4.29
Di bawah baris arah XAU: "➕ Tren emas 4 jam TURUN ▼ (−$8,40) SEARAH → benar 64–67% ⚠️" + "Tebakan terbaik: …", atau
"⚠️ … BERLAWANAN → hanya 49–55% ≈ lempar koin" / "tanpa petunjuk: tren saja 55–56% (lemah)". Cloud `_pra_aset.tren_emas`
(Twelve Data XAU/USD 15 mnt, cache baris Supabase `pra_tren` 5 mnt bila rilis ≤ 1 jam lagi, selain itu 15 mnt; hanya
≤ 6 jam sebelum rilis; env PRA_TREN=0 mematikan). Tren dihitung saat aplikasi dibuka → buka lagi 1–5 menit sebelum rilis.
Info saja, tanpa order.
