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

## Di aplikasi (4.27–4.28)
Satu baris di bawah tile XAU: arah tebakan + persen per detik (✅/⚠️/⚪) dan baris 📌 kepastian detik 2 untuk berita
berikutnya (cloud `_pra_aset.py`; PPI memakai kejutan CPI yang baru keluar lewat memori `_petunjuk`).
