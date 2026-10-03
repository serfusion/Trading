# Badge 💰 vs hasil sinyal yang dikirim (3 Okt 2026)

Pertanyaan pengguna: "Katanya 💰/⭐ bagus dan yang minus hanya sinyal biasa. Sekarang sinyal biasa malah profit,
💰💰💰 minus, dan 💰⭐ konf tidak untung. Bagaimana saya bisa percaya?"

Laporan mentah ada di `docs/eksternal/hasil_kategori_badge.txt`, dibuat oleh `research/kategori_badge.py`. Mesin dan
skemanya sama dengan cloud (TP1 1R + 4 jalan). R = rata-rata 5 posisi per sinyal.

## 1. Kenapa angka badge berbeda dengan Riwayat 💰
Ada dua cara menghitung hasil per kategori:

- **Cara A (dasar badge di `_core.STATS`):** semua sinyal dikirim, lalu masing-masing diberi label kategori.
- **Cara B (yang benar-benar Anda terima):** hanya kategori 💰 yang dikirim.

Hasilnya bisa berbeda karena pada cara B sinyal biasa tidak dikirim. Akibatnya slot set lebih sering kosong, dan
slot kosong itu bisa terisi sinyal 💰 tambahan yang pada cara A tidak pernah muncul. Contohnya XAU konf:

| XAU konf, 2012–2026 | n | R/sinyal |
|---|---|---|
| Cara A (badge 💰⭐) | 335 | +0,09 |
| Cara B (dikirim) | 413 | **+0,01** |
| 73 sinyal tambahan yang hanya muncul di B | 73 | −0,27 |

**Kesalahan:** badge dihitung dengan cara A dan dari seluruh periode. Akibatnya:
- XAU konf tampak lebih baik daripada yang sebenarnya diterima pengguna.
- Pelemahan BTC konf sejak Okt 2021 tidak terlihat:
  - cara A: LAMA +0,52, BARU −0,07;
  - cara B: BARU +0,04, 2026 −0,15.

## 2. Hasil yang benar-benar dikirim (cara B)

| | LAMA R/sinyal | BARU R/sinyal (total, DD) | 2026 (s.d. Sep) |
|---|---|---|---|
| **XAU 💰** (konf+⭐ + konf) | +0,21 | **+0,21** (+127R, DD −41) | 61 sinyal, WR 72%, **+50R** |
| — XAU konf+⭐ saja | +0,28 | +0,19 (+102R, DD **−66**) | 51 sinyal, +50R |
| — XAU semua kategori (termasuk biasa) | +0,08 | +0,07 (+83R, DD −69) | 156 sinyal, +49R |
| **BTC 💰** (konf+⭐ + konf + ⭐) | +0,53 | **+0,19** (+198R, DD −47) | 149 sinyal, WR 40%, **+44R** |
| — BTC tanpa konf | +0,51 | +0,23 (+203R, DD −38) | 126 sinyal, +38R |
| — BTC semua kategori (termasuk biasa) | +0,30 | +0,10 (+193R, DD −46) | 287 sinyal, **+65R** |

**Total R per tahun BARU:**

| | 2021 (Okt–Des) | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|
| XAU 💰 | −1 | 0 | −11 | +29 | +60 | +50 |
| XAU semua | −17 | −16 | +11 | +21 | +35 | +49 |
| BTC 💰 | +7 | −32 | +93 | +45 | +40 | +44 |
| BTC semua | −11 | −4 | +72 | +52 | +20 | +65 |

## 3. Kesimpulan jujur
- **XAU:** 💰 tetap lebih baik daripada sinyal biasa, termasuk tahun 2026.
  - XAU konf+⭐ 2026: +1,45R per sinyal, WR 79%.
  - XAU biasa 2026: +0,18R per sinyal.
- **BTC:** pengamatan pengguna benar untuk 2026.
  - Sinyal biasa: +66R dari 185 sinyal.
  - Kategori 💰 (cara A): konf −6R, konf+⭐ +2R, ⭐ +3R.
  - Selama 5 tahun, BTC 💰 menang 3 tahun dan "semua sinyal" menang 3 tahun. Hasil per sinyal 💰 kira-kira 2×
    lebih tinggi (+0,19 vs +0,10), karena total yang mirip diperoleh dengan separuh jumlah sinyal.
- **Saran lama "hentikan XAU konf" DICABUT.** Tanpa konf, total BARU XAU turun (+102R vs +127R) dan DD
  memburuk (−66 vs −41). Sendirian XAU konf memang ≈ 0, tetapi dalam gabungan ia menstabilkan hasil.
- **BTC tanpa konf** sedikit lebih baik di BARU (DD −38 vs −47). Selisihnya kecil dan pilihan ini dibuat setelah
  melihat data BARU, jadi **tidak cukup untuk mengubah sinyal live**.
- **Usulan (menunggu kata "pasang"):** hitung ulang badge dengan cara B. Tampilkan juga angka "sejak Okt 2021" dan
  "tahun ini", supaya badge menggambarkan keadaan sekarang, bukan rata-rata 14 tahun.
