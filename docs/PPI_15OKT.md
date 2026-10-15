# 🌙 PPI 15 Okt 2026 — "angka pasti 85%?"

Permintaan pengguna (15 Okt pagi): "Forecast PPI sudah keluar, saya yakin naik (buy), kenapa aplikasi stuck TURUN 74%? Cari semua
informasi, riset, uji validitas, semua metode — saya mau angka pasti 85% ke atas." Skrip: `research/ppi_malam.py` →
`docs/eksternal/hasil_ppi_malam.txt`; angka per arah sel CPI→PPI: `research/ppi_dasar.py simpan` (TAHAP 4).

## Data malam ini (12:30 UTC, bersamaan Retail Sales, klaim, Empire, Philly)
- Konsensus FF = Nasdaq: PPI m/m 0,6% (lalu 0,4%), y/y 5,3% (lalu 5,4%), core 0,3% (lalu 0,2%), core y/y 4,4%.
  Retail 0,3% (lalu 1,2%), control 0,3%.
- Minyak bulan acuan (5 hari s/d 13 Sep vs 13 Agu): WTI +17,5%, bensin +14%, solar +16% → PPI condong DI ATAS.
- CPI kemarin: m/m 0,6% = konsensus, inti 0,3% > 0,2% (DI ATAS), y/y 3,7% > 3,6%.
- Kalshi KXUSPPI / KXUSPPIYOY: sangat sepi, harga tidak konsisten (mis. "di atas 0,7%" 0,74/0,75 tetapi "di atas 0,5%" bid 0)
  → tidak dipakai (riwayat 2–5 rilis, tidak bisa diuji).
- Emas (OKX XAUT 09:00 UTC): 4 jam +$21, 24 jam +$9 → tren naik.

## Kenapa aplikasi "stuck" 74% — dan kenapa 74% itu salah untuk tebakan TURUN
Tebakan PPI berasal dari minyak + CPI inti, keduanya sudah tetap sejak kemarin; konsensus tidak masuk aturan, jadi persen tidak
bergerak saat konsensus terbit (by design). TETAPI angka 74% (n 19) adalah sel "CPI inti searah" yang MENCAMPUR dua arah:
tebakan NAIK 7/7 (100%) dan tebakan TURUN hanya 7/12 (58%; LAMA 50%, BARU 62%; detik 2 4/12 = 33%). Sejak 15 Okt
`_ppi_wti.pakai_cpi` memakai angka ARAH yang ditebak → kartu: "PPI ▼ TURUN 58% (lonjakan menit 1) ⚠️ ⚖️ tunggu ⚡LIVE",
💥 modal kecil "JANGAN".

## Semua petunjuk sebelum rilis (lonjakan menit 1 / detik 2, rilis PPI 2016–2026)
| petunjuk | arah | lonjakan | detik 2 |
|---|---|---|---|
| selalu NAIK (pembanding) | NAIK | 55% (118) | 60% |
| minyak naik ≥ 5% | TURUN | 55% (49) | 41% |
| minyak + CPI inti di atas (dulu tampil 74%) | TURUN | 58% (12) | 33% |
| minyak + tren 24 jam naik (= malam ini) | TURUN | 44% (18) | 33% |
| tren 4 jam / 24 jam naik | NAIK | 63% / 65% | 67% / 65% |
| core lalu < konsensus core (KONC) | NAIK | 55% (47) | 64% |
| minyak + konsensus sudah naik (gap ≥ 0,2) [pasca-lihat] | TURUN | 69% (13) | 54% |
| model gabungan 12 petunjuk (tutup kertas) | — | 51% (82) | — |
Kesimpulan: sebelum rilis ≈ lempar koin (44–65%); TIDAK ADA yang mendekati 85%. Plafon: walau angka PPI sudah diketahui, emas
searah kejutan hanya 81–86% (lonjakan) dan detik 1 51–54% (putaran 3).

## Setelah rilis (⚡LIVE detik 2)
- Arah detik 2 ≥ $0,50 masih sama di detik 5: 91% (68; BARU 86%), detik 10 87%, menit 1 84%; ≥ $1: 93% / 84% / 88%; ≥ $2: 15/15.
- Minyak naik & detik 2 turun → menit 1 turun 12/12; detik 2 naik → menit 1 naik 73% (15).
- **Tetapi masuk SETELAH melihat detik 2** (telat 0,5–1,5 dtk, bid/ask Exness): untung hanya 20–45% rilis, rata-rata −$0,3…−$0,7/oz
  (tutup detik 5–60); hanya gerak ≥ $2 sedikit positif (+$0,4–0,7/oz, n 15). 85%+ = arah BERTAHAN, bukan untung saat mengejar.
  → kartu PPI kini memuat poin "⚠️ Tapi masuk SETELAH detik 2 … rata-rata rugi".
