# 🛑 Batalkan sinyal saat guncangan (pernyataan Trump / Fed / pemerintah / negara lain)

Permintaan pengguna 10 Okt 2026: "jika ada statement Trump, pemerintah AS, the Fed, orang penting atau negara yang
membuat harga jatuh, tarik sinyal BUY (canceled/invalid) — seperti spot XLM yang dikirim sebelum jatuh lalu loss jauh";
lalu "sebaliknya jika entry SELL dan guncangan naik, batalkan juga SELL-nya".

## Cara menguji (research/batal_guncang.py → docs/eksternal/hasil_batal_guncang*.txt)

Pernyataan baru bisa dinilai "menjatuhkan harga" setelah harga bereaksi, dan arsip judul pernyataan historis tidak
tersedia untuk diuji kata per kata. Yang diuji: **guncangan harga** yang pasti mengikuti pernyataan penting — harga
bergerak MELAWAN posisi sejauh ambang tertentu dalam ≤ m jam — lalu dibandingkan "tutup/batal saat itu" vs "tahan
seperti sekarang". Δ > 0 = membatalkan menolong. Untuk yang BELUM entry, angka yang sama berarti: masuk setelah
guncangan dengan TP/SL lama rata-rata menghasilkan −Δ. Kriteria lolos ditetapkan sebelum melihat hasil (Δ > 0 di
periode lama < Okt 2021 & baru, ≥ 60% tahun, ambang tetangga juga Δ > 0).

## Hasil

| Sinyal | Guncangan | Hasil | Keputusan |
|---|---|---|---|
| 💰 XAU/BTC (BUY & SELL), sebelum TP1 | 1,5–3 × ATR14 H1 dalam 1–6 jam | **MERUGIKAN**: XAU BUY sejak 2021 +586R → +340…+540R, WR 64% → 52–63%; setelah guncangan harga rata-rata pulih +0,2…+0,8R | tidak dipakai |
| 💰 XAU/BTC (BUY & SELL) | **≥ 4 × ATR dalam ≤ 6 jam** | sedikit menolong; replay kode cloud penuh: XAU +734,6R → **+742,8R** (sejak Okt 2021), +792,3R → +799,2R (sebelumnya), 9/9 tahun membaik, 63 pembatalan dalam 14 tahun; BTC +457,0R → +459,2R, 4/4 tahun | **DIPASANG** 🛑 |
| 🌊 ikut arus | ≥ 3 ATR dalam ≤ 3 jam | ETH SELL saat lonjakan naik +0,02R/sinyal di kedua periode (83% tahun); XAU/BTC BUY ≈ netral | **DIPASANG** 🛑 |
| 🔗 keranjang kripto | rata-rata keranjang −5% dalam ≤ 1 jam | +0,09%/+0,13% per keranjang (lama/baru), 67% tahun; −2% merugikan | **DIPASANG** 🛑 |
| 💎 spot (TP +3%/10 hari, tanpa SL) | koin −3…−15% atau BTC −2…−5% dalam 1–24 jam, juga "guncangan murni" (jatuh di dalam jendela saja) | **MERUGIKAN di setiap tahun**: WR 92% → 52–91%, total sejak 2021 +1.040% → −83…+839%; setelah anjlok −8%/3 jam harga rata-rata pulih +6% s.d. TP/batas waktu | hanya ⚠️ PERINGATAN (env SPOT_BATAL=1 memaksa jual — tidak disarankan) |

### Kasus XLM 8 Okt 2026 (direkonstruksi dari Binance)
Sinyal 💎 XLM terkirim 8 Okt 07:05 WIB (aturan "3 merah") ±0,2005, TP 0,2065. Pukul ±22:00 WIB pasar kripto anjlok
(likuidasi ±$1 miliar, yield & dolar naik, minyak naik; BTC < $81 rb): XLM terendah 0,1860 (−7%). 10 Okt siang 0,197
(−1,7%), batas waktu 18 Okt. Bila dibatalkan saat anjlok, rugi terkunci ±−6%; ditahan, sudah pulih ke −1,7%. Ini sama
dengan pola data: menjual spot saat anjlok rata-rata lebih buruk.

## Yang dipasang (10 Okt 2026, env `GUNCANG_BATAL=0` mematikan semua)
- `_core.guncangan` + `manage`: sinyal 💰 XAU/BTC/ETH/DOGE/ADA (dan lapisan) SEBELUM TP1, harga melawan ≥ 4 × ATR14 H1
  (ATR sebelum entry) dari harga terbaik sejak entry dalam ≤ 6 jam (dicek tiap 10 menit dengan harga berjalan) →
  event `close` dengan `batal: true`, notifikasi "🛑 BATAL … Belum entry? JANGAN entry. Sudah entry: tutup semua".
  Simetris: BUY saat anjlok, SELL saat melonjak.
- `_arus`: 3 × ATR / 3 jam → `arus_close` `batal: true`. `_pulih`: keranjang −5% / 1 jam → `pulih_close` `batal: true`.
- `_spot`: ⚠️ `spot_warn` sekali per posisi (−8% dari high 3 jam) dengan saran berbasis data; `SPOT_BATAL=1` = jual paksa.
- 🗣️ `_pernyataan.py`: judul pernyataan/berita penting terbaru (RSS resmi Fed + Google News: Trump, Gedung Putih, Menkeu,
  Iran, China, OPEC, Rusia) di kartu 🎯 sebagai "kenapa". Arah harga TIDAK ditebak dari kata-kata (tanpa AI; kata yang
  sama bisa menaikkan atau menurunkan emas). Env `PERNYATAAN=0` mati.

Batasan jujur: guncangan ekstrem jarang (XAU ±5 kali/tahun) dan manfaatnya kecil (+0,003R per sinyal). Pernyataan yang
menjatuhkan harga pelan-pelan tidak terdeteksi — SL tetap pelindung utama.

## Perbaikan 15 Okt 2026 (keluhan: DOGE "batal" lalu hari berikutnya TP1 kena)
- Live memakai **harga berjalan tiap 10 menit** (ekor/wick sesaat ikut memicu), padahal yang diuji = **close candle 1 jam**.
  Uji versi wick (4 ATR/6 jam, replay cloud): XAU sejak Okt 2021 +734,6R → +720,5R (WR 65,1 → 64,4%), BTC +457 → +425R,
  DOGE lama +115 → +101R (WR 62,1 → 60,3%), ADA −9R per periode → merugikan.
- Versi close: XAU +734,6 → +743,9R, BTC +457,0 → +458,2R, WR tidak berubah; ETH/DOGE/ADA ≈ 0 (DOGE 4 pembatalan/5 tahun).
- Dipasang: `_core.manage` memanggil `guncangan(closed, v, closed[-1].c)`; 🛑 dimatikan untuk ETH/DOGE/ADA (`tick.py`
  `"guncang": False`). 🌊 `_arus` sudah memakai close candle (tidak berubah).
