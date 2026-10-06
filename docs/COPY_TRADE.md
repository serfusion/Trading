# Copy trade: bisakah, dan apakah memilih WR / profit tertinggi berhasil? (6 Okt 2026)

Kode `research/copy_trade.py`, hasil `docs/eksternal/hasil_copy_trade.txt`.

## Bisakah Claude melakukan copy trade?
- Platform copy trade (MQL5 Signals, Exness Social Trading, Binance Copy Trading, Myfxbook, ZuluTrade, eToro) DIBLOKIR
  jaringan sesi → data penyedia tidak bisa diambil langsung, dan kredensial akun tidak boleh dititipkan ke sesi ini.
- Yang BISA: (1) cloud sudah punya jalur auto order MetaApi (`_core.MetaApi`, bawaan MATI) = "copy" sinyal 💰 kita ke MT5
  pengguna; (2) menilai penyedia dari data yang pengguna kirim (screenshot/ekspor halaman strategi: return, DD, umur,
  jumlah trade, lot terbesar).

## Literatur
- Apesteguia, Oechssler & Weidenholzer (Management Science, eToro/ZuluTrade/Tradeo): melihat & menyalin orang sukses
  membuat pengambilan risiko berlebihan.
- Studi 90 hari Binance/Bybit/MEXC (2025, >100.000 hasil): 97% lead trader untung untuk dirinya, hanya 44% memberi untung
  ke pengikut; pengikut yang untung 48%; saat BTC jatuh 9 Okt 2025 banyak "top" lead trader hilang.
- eToro 2017–2020: sebagian copy-portfolio punya alpha positif; studi 2024: tidak konsisten mengalahkan S&P 500.
- Grid/martingale (MQL5): statistik bagus lama sekali sampai satu gerakan besar menghabiskan akun (contoh EA terlaris
  Quantum Emperor: DD 70% Juni 2024).

## Uji: pasar copy trade tiruan (263 penyedia XAU H1 2013–2026)
Gaya: tren (Donchian), balik (RSI2), scalper (TP kecil/SL besar), grid/averaging tanpa SL (penyedia baru tiap tahun).
Tiap bulan: papan peringkat 12 bulan terakhir → salin 5 teratas selama 6 bulan.
| Cara memilih | Return 6 bulan (median) | Periode rugi | Periode ada penyedia meledak | Yang terpilih |
|---|---|---|---|---|
| **WR tertinggi** | **−6,6%** | 78% | **43%** | scalper 56%, grid 44% |
| **Profit tertinggi** | −0,2% | 50% | **32%** | tren 51%, grid 38% |
| Profit / DD | +1,2% | 49% | 26% | tren 56%, grid 31% |
| Profit dengan DD ≤ 20% | −1,1% | 55% | 7% | tren 71% |
| Acak | −6,8% | 87% | 7% | scalper 60% |
Grid: median umur 3 bulan, 16% bertahan ≥ 12 bulan, 3% ≥ 36 bulan, 100% akhirnya habis.
LAMA (< Okt 2021) vs BARU: WR tertinggi −1,8% → −12,9%; profit tertinggi +1,7% → −2,7%; DD ≤ 20% −3,5% → +1,8%.

## Kesimpulan
1. "Cari WR tertinggi" = jebakan: papan WR diisi scalper & grid/martingale; WR 95% di masa lalu tetap 93% ke depan, tetapi
   uangnya rugi dan 43% periode ada akun yang meledak.
2. "Cari profit tertinggi" ≈ impas dengan 1 dari 3 periode berisi penyedia yang meledak (grid yang sedang beruntung).
3. Saringan terbaik: umur ≥ 12 bulan, DD maksimum ≤ 20%, tanpa tanda grid/martingale (lot membesar setelah rugi, WR > 85%
   dengan rugi sesekali sangat besar) — hasilnya pun hanya ±impas; tidak ada cara memilih yang konsisten untung besar.
4. Pembanding: sinyal 💰 kita sendiri (teruji, replay cloud) sejak Okt 2021 XAU +0,21R/BTC +0,27R per sinyal.
