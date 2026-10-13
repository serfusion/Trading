# 💥 Modal kecil + lot maksimal saat CPI (15 Okt 2026)

Permintaan pengguna: modal kecil (5–10 ribu cent = $50–100), lot sebesar mungkin; tebakan benar di detik 1–5 → untung
berlipat, salah → margin call (modal habis). Skrip `research/cpi_allin.py` → `docs/eksternal/hasil_cpi_allin.txt`.

**Cara uji:** tick ASLI Exness XAUUSDc (bid/ask saat rilis), 126 rilis CPI 2016–2026, modal $100 per rilis, lot penuh
sesuai leverage, masuk t0 − 1 dtk searah tebakan aplikasi (tutup kertas), tutup di detik h; equity dicek tiap tick
(≤ 0 = margin call, rugi maks $100 — Exness punya perlindungan saldo negatif). Belum termasuk latensi klik/eksekusi.

## Hasil (tebakan kuat saja = tanpa ⚠️; rugi maks $100 per rilis)
| Leverage | Tutup | sebelum Okt 2021 (12 rilis) | sejak Okt 2021 (32 rilis) | benar (baru) | margin call (baru) | menang rata |
|---|---|---|---|---|---|---|
| 1:200 | detik 2 | −$120 | **+$649** | 78% | 0 | ×0,3 modal |
| 1:200 | detik 5 | −$35 | +$668 | 72% | 2 | ×0,5 |
| 1:500 | detik 2 | −$285 | **+$1.795** | 78% | 2 | ×0,9 |
| 1:500 | detik 5 | −$39 | +$2.295 | 72% | 6 | ×1,3 |
| 1:2000 | detik 2 | −$546 | **+$6.556** | 69% | 9 (1 dari 3,6) | ×3,4 |
| 1:2000 | detik 5 | +$593 | +$9.476 | 66% | 11 | ×5,0 |

Per tahun (kuat, 1:500, detik 2): 2019 −$19 · 2020 −$121 · 2021 −$167 · **2022 +$243 · 2023 +$44 · 2024 +$529 · 2025 +$544 ·
2026 +$457**.

- **Detik 1 tidak menguntungkan** di semua leverage (benar 26–41%: harga broker belum bergerak, spread dulu).
- Tebakan ⚠️ lemah (SELL saat tren naik / Kalshi core berlawanan) menyumbang sebagian besar margin call 2024–2026 → jangan
  dipakai untuk strategi ini.
- **Pembanding "selalu BUY"**: sejak 2024 juga untung (emas sangat volatil & tren naik; rugi dibatasi $100 sementara untung
  tidak dibatasi) tetapi 2016–2023 rugi; 2022–2023 aturan kuat untung saat "selalu BUY" rugi → tebakan memang menambah nilai.
- Untung "berlipat" (×3–5) hanya dengan leverage 1:2000 — dan saat itu **1 dari ±3 rilis menghabiskan modal** walau memakai
  tebakan kuat. Dengan 1:200 untung rata-rata hanya ±30–50% modal per tebakan benar.

## Risiko yang belum masuk angka
1. **Batas leverage saat berita**: Exness memberlakukan margin tetap (±1:200) untuk posisi yang dibuka sekitar berita besar —
   cek ketentuan akun Anda; bila berlaku, hasil 1:2000 tidak bisa dicapai.
2. **Latensi**: masuk tepat t−1 dtk dan keluar tepat detik 2 mustahil secara manual — perlu EA/otomasi; requote/penolakan
   order saat rilis bisa membuat hasil lebih buruk.
3. **Rezim**: semua keuntungan datang dari 2022–2026 (gerak CPI besar); 2019–2021 rugi. Bila volatilitas CPI mengecil, hasil
   bisa kembali negatif.
4. Sampel kecil (32 rilis sejak 2021), aturan saringan ditemukan setelah melihat kesalahan.

## Kesimpulan
Untuk CPI, strategi modal kecil + leverage hanya masuk akal dengan **tebakan kuat saja, tutup detik 2** (bukan detik 1),
leverage sedang (1:200–1:500), dan modal yang benar-benar siap hilang. Teruji untung sejak Okt 2021, rugi sebelumnya →
belum terbukti di semua periode.
