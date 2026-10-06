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

## Data nyata: MQL5 Signals & Binance Copy Trading (6 Okt 2026, host dibuka pengguna)
`research/mql5_signals.py` (4.402 sinyal aktif MT5+MT4, 1.043 dengan riwayat bulanan ≥ 18 bulan) dan
`research/binance_copy.py` (9.267 lead portfolio publik, grafik ROI harian 365 hari). Hasil lengkap:
`docs/eksternal/hasil_mql5.txt`, `docs/eksternal/hasil_binance_copy.txt`.
- Binance: median ROI 365 hari +0%, MDD median 30%; **PnL pengikut positif hanya 15%** dari semua portfolio. WR tidak
  berhubungan dengan untung pengikut (korelasi peringkat +0,01). Return 180 hari lalu vs 185 hari berikutnya: korelasi −0,10.
- MQL5: WR tinggi tidak berarti DD kecil (korelasi −0,06); 13% penyedia WR ≥ 90% pernah rugi > 20% dalam sebulan.
- Keduanya hanya memuat penyedia yang MASIH hidup → **bias penyintas**: hasil nyata lebih buruk dari angka di bawah.

## DIPASANG: 👥 Copy trader teruji (aplikasi 4.7, permintaan pengguna 6 Okt 2026)
`research/copy_pilih.py` → `cloud/api/copytrader.json` → `GET /api/chat?copytrader=1` → kartu 👥 di tab Sinyal
(`CopyTraderCard.kt`): 2 Binance + 1 MQL5 teratas, "Semua & bukti" = 6 per platform + hasil uji. Ketuk nama = buka
halaman salin di Binance/MQL5. **Info saja — aplikasi tidak menyalin order** (salin dilakukan pengguna di platform itu).
Diperbarui otomatis tiap Senin 07:41 WIB (`.github/workflows/copytrader.yml`, hanya pandas/numpy); satu sumber gagal →
daftar minggu lalu dipakai dan ditandai "basi".

Saringan (dipilih dari uji di atas, bukan dari WR/ROI tertinggi):
- Binance: umur ≥ 365 hari, ROI 365 hari > 0 dan positif di paruh 1 & 2, MDD ≤ 20%, WR ≥ 60%, PnL pengikut > 0,
  ≥ 30 pengikut, masih aktif 30 hari terakhir. Peringkat ROI/MDD. WR ≥ 95% diberi ⚠️ (biasanya posisi rugi ditahan).
- MQL5: akun real, ≥ 52 minggu, DD ≤ 20%, win ≥ 65%, ≥ 100 trade, ≥ 5 pelanggan, saldo ≥ $1.000, 12 bulan penuh
  terakhir positif di kedua paruh, bulan terburuk > −10%, max deposit load ≤ 30% (anti grid/martingale), growth
  12 bulan ≤ 300%.

Uji maju aturan ini (`python -m research.copy_pilih uji` → `docs/eksternal/hasil_copy_pilih.txt`):
| Binance: pilih hari 1–180 → ukur hari 181–365 | n | Median | Rugi | Hancur < −50% | DD median |
|---|---|---|---|---|---|
| semua portfolio aktif | 1.790 | +5,7% | 38% | 10% | −34% |
| lolos aturan | 140 | +2,5% | 41% | 6% | −14% |
| aturan, 20 teratas ROI/DD | 20 | +9,4% | 25% | 0% | −13% |
| aturan, 6 teratas ROI/DD | 6 | +27,0% | 0% | 0% | −11% |
| ROI tertinggi 20 (pembanding) | 20 | +26,5% | 25% | 0% | −35% |

| MQL5: tiap bulan pilih dengan 12 bln → ukur 6 bln (72 periode 2020–2026) | n rata | Median | Rugi | < −30% |
|---|---|---|---|---|
| semua | 248 | +12,1% | 19% | 4% |
| lolos aturan | 88 | +12,4% | 10% | 1% |
| aturan, 6 teratas | 6 | +18,6% | 4% | 1% |
| growth 12 bln tertinggi 6 (pembanding) | 6 | +38,6% | 15% | 6% |

Arti jujurnya:
1. Saringan ini terutama **mengurangi risiko** (rugi, hancur, DD ≈ sepertiga), bukan menaikkan profit. "Lolos aturan"
   secara median tidak lebih untung dari semua penyedia; peringkat ROI/DD di dalamnya yang menambah.
2. Uji Binance hanya 1 periode (grafik 365 hari) dan n kecil (6–20) → angka "6 teratas" bisa kebetulan.
3. WR/pengikut/PnL pengikut di daftar adalah angka SEKARANG (tidak dipakai saat uji maju); max deposit load MQL5 juga
   angka sekarang (sedikit look-ahead).
4. Pilihan 6 Okt: Binance 9 lolos, MQL5 2 lolos. Semua penyedia Binance terpilih untung lebih kecil di paruh kedua
   dibanding paruh pertama (contoh +85% → +31%) — wajar (regresi ke rata-rata), jangan harapkan ROI setahun terulang.
5. Saran: modal kecil, sebar ke 2–3 penyedia, batasi rugi di pengaturan salin (Binance: stop loss / batas per posisi;
   MQL5: persentase dana & batas DD). Pembanding sinyal 💰 sendiri: XAU +0,21R / BTC +0,27R per sinyal sejak Okt 2021.
