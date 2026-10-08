# 🧪 Sinyal trader & 📊 peringkat semua sinyal (8 Okt 2026)

Permintaan pengguna:
1. "Semua teorimu dengan WR dan profit tinggi diperingkatkan pada (i) info sinyal, mulai dari XAU, BTC, ⚡⭐🥈🥉💎🌊🔄🎯🧪 dll."
2. "Apabila salah satu copy trader open posisi bagus dengan kemungkinan WR dan profit tinggi, deteksi sekaligus uji
   validitas otomatis, masuk di apk sebagai 🧪 sinyal trader" + "tidak hanya Hyperliquid, cari seluruh broker".

## 1. 📊 Peringkat di tombol ⓘ (DIPASANG, aplikasi 4.23)

`python -m research.peringkat` → `cloud/api/peringkat.json` → dikirim bersama `riwayat.json` (GET `/api/chat?riwayat=1`)
→ kartu 🏆 di dialog ⓘ. Empat grup:
- **Sinyal** (bisa ditradingkan): profit rata-rata per sinyal dalam R setelah spread, urut profit lalu WR. Sumber: replay
  kode cloud live (XAU dengan ⏸️ jeda 60 jam, BTC), riwayat.json (ETH, gap), replay DOGE/ADA, `_arus.RULES` (🌊),
  `_core.WR_TINGGI` (🎯), tanda 📰 dihitung ulang dari replay live.
- **Spot** 💎: % per trade (spot_model.json).
- **Info & prediksi**: akurasi tebakan, bukan profit (model prarilis NFP/JOLTS/Fed, aturan NFP, 🔄 titik balik,
  🧪 kandidat NFP, 🧪 sinyal trader).
- **Filter aktif** tanpa nomor: ⏸️ jeda XAU, filter BTC, saringan copy trader.

Urutan teratas (sejak Okt 2021): XAU ⚡ +0,47R (WR 66%), BTC 🎯 +0,46R (WR 76%), BTC ⚡ +0,42R, BTC 🔁 +0,38R,
XAU 🔁 +0,35R … paling bawah Gap forex −0,07R. Catatan: setelah TP1 0,7R dan jeda, tanda 📰 XAU (+0,24R) **tidak lagi
lebih baik** dari rata-rata sinyal XAU (+0,27R). Jalankan ulang `python -m research.peringkat` setelah replay/riset baru.

## 2. 🧪 Sinyal trader — TIDAK LOLOS (tidak dipasang)

`research/sinyal_trader.py unduh [okx|bitget|binance|etoro] | buka <platform> | uji`.

Data (8 Okt 2026, disimpan di `data/research/eksternal/copy_multi/`):

| Platform | Posisi tutup | Trader | Rentang | Posisi masih terbuka (potret) |
|---|---|---|---|---|
| Hyperliquid (fill on-chain, `hl_fills/`) | 63.964 | 863 | Sep 2025 – Okt 2026 | 2.479 |
| Binance | 61.009 | 582 | Agu 2025 – Okt 2026 | 1.192 |
| Bitget | 23.224 | 342 | Nov 2024 – Okt 2026 | 1.336 |
| OKX (riwayat hanya ±3 bulan) | 24.498 | 110 | Jul – Okt 2026 | 2.190 |
| eToro (saham, kripto, dll.) | 103.263 | 644 | 2013 – Okt 2026 | 21.170 |

Kandidat dipilih TANPA melihat kinerja: semua lead trader OKX/Bitget yang tercatat, Binance & eToro = 500 acak + 200
paling banyak disalin, Hyperliquid = 400 akun acak (termasuk yang meledak) + akun terbesar. Akun bot (2.000 fill < 3 hari)
dan posisi < 1 jam dibuang (tidak bisa disalin).

Return salin per posisi = arah × (harga tutup / harga buka − 1) − biaya (futures 0,14–0,15%, eToro kripto 1%, lain 0,2%),
TANPA leverage. Lima aturan pilih (WR ≥ 60/65/70%, PF ≥ 1,5/2, n ≥ 20–50, untung) dari riwayat 90 hari (OKX 45 hari).

**A. Uji maju bergulir tiap 14 hari** (posisi tutup + posisi terbuka yang waktu bukanya diketahui, dinilai harga sekarang):
trader terpilih WR 72–80% (vs semua 57%), tetapi dibanding pilihan ACAK sejumlah sama: gabungan futures p-acak
0,06–0,21 (tidak bermakna); Hyperliquid terpilih justru −0,2…−0,35%/posisi (p 0,6–0,8); OKX lebih buruk dari semua.

**B. Uji potret** (pilih per 30 hari lalu, ukur SEMUA posisi baru termasuk yang MASIH TERBUKA):

| Aturan B (WR ≥ 65, PF ≥ 1,5) | Terpilih | Semua trader | p-acak |
|---|---|---|---|
| Gabungan futures | WR 75,7%, +0,65%/posisi | +0,36% | 0,14 |
| Binance | WR 78,7%, +0,66% | +0,22% | 0,03 |
| OKX | +0,85% | +0,72% | 0,30 |
| Bitget | +0,36% | +0,41% | 0,41 |
| Hyperliquid | −0,60% | +0,25% | 0,77 |
| **Posisi masih terbuka milik trader terpilih** | **WR 18–36%, rata-rata −4 s.d. −8%** | −1,6% | — |

Kesimpulan jujur:
- WR tinggi copy trader sebagian besar datang dari **posisi rugi yang ditahan** (tidak ditutup → tidak masuk riwayat).
  Contoh nyata: trader eToro dengan posisi −99,6% masih terbuka.
- Setelah posisi terbuka ikut dihitung, memilih trader ber-WR/PF tinggi **tidak lebih baik dari memilih acak** di
  Hyperliquid, OKX, Bitget (p 0,1–0,8). Hanya Binance unggul (p 0,01–0,04 di semua aturan) tetapi baru 1 periode
  30 hari dan posisi rugi terbukanya bisa makin dalam → **kandidat**, belum terbukti.
- eToro: uji potret tidak valid (waktu buka posisi terbuka tidak diketahui; banyak posisi saham bertahun-tahun dengan
  untung ribuan %), uji bergulir hanya posisi tutup → bias rugi ditahan → tidak dipakai sebagai bukti.
- Karena itu 🧪 sinyal trader **TIDAK dipasang** sebagai sinyal (tercatat di peringkat ⓘ sebagai "tidak lolos").
  Pilihan bila pengguna bilang "pasang": uji maju otomatis kandidat Binance (pantau posisi baru trader terpilih,
  catat hasil termasuk posisi terbuka, naik status hanya bila lolos ≥ 3 bulan), atau peringatan ⚠️ "rugi ditahan" di
  kartu 👥 copy trader (trader dengan posisi terbuka rugi besar).
- Pengulangan: `python -m research.sinyal_trader unduh` (Hyperliquid, 1.225 dari 1.386 akun selesai; bisa dilanjutkan),
  `unduh okx|bitget|binance|etoro`, `buka okx|bitget|binance|etoro` (potret posisi terbuka), lalu `uji`.
  Hasil lengkap: `docs/eksternal/hasil_sinyal_trader.txt`.
