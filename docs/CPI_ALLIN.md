# 💥 Modal kecil + lot maksimal saat CPI (13 Okt 2026)

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

## Semua metode (13 Okt 2026, `research/cpi_allin2.py` → `docs/eksternal/hasil_cpi_allin2.txt` & `.csv`)
Pertanyaan pengguna: "sudah diuji metode apapun? kalau bagus pasang". Grid ditetapkan sebelum melihat hasil: 7 cara menebak
arah (tebakan kuat, semua tebakan aplikasi, hanya NAIK, Kalshi m/m saja, KEJAR gerak detik pertama tanpa tebakan, SEMPURNA,
selalu BUY) × masuk t−1/−3/−10 dtk × keluar detik 2/3/5/10, ambil untung 50% modal, batas rugi 50% modal × leverage 1:100–1:2000
= 570 konfigurasi.

**Temuan penting — pembanding ARAH ACAK.** Karena rugi dibatasi = modal (perlindungan saldo negatif) sementara untung tidak
dibatasi, di leverage besar arah acak pun tampak untung (1:2000 tutup detik 2 sejak 2022: acak +$88/rilis). Jadi yang dihitung
adalah selisih tebakan vs lempar koin pada rilis yang sama (`python -m research.cpi_allin2 acak`, 20.000 lemparan):

| Masuk t−1 dtk, tebakan kuat | 2016–Sep 2021 (12 rilis) | sejak Okt 2021 (32 rilis) |
|---|---|---|
| tutup detik 1, 1:200 | untung 0% rilis, −$5,6 (acak −$4,6) | untung 41%, +$2,1 (acak −$3,3), p 0,05 |
| **tutup detik 2, 1:200** | untung 25%, −$10 (acak −$5) | **untung 78%, +$20,3/rilis (acak −$4,3), p < 0,001, 0 modal habis** |
| tutup detik 2, 1:500 | −$23,7 | +$56,1 (acak +$3,5), modal habis 2× |
| tutup detik 2, 1:2000 | −$45,5 | +$204,9 (acak +$87,9), modal habis 9× |
| tutup detik 5, 1:200 | −$2,9 | +$20,9 (acak −$2,3), p 0,02 |

- Per tahun (1:200, detik 2): 2019 −$7 · 2020 −$49 · 2021 −$73 · 2022 +$60 · 2023 −$14 · 2024 +$212 · 2025 +$218 · **2026 5/5
  rilis untung, +$183**. Rugi beruntun terburuk sejak 2022: 2 rilis (−$78).
- KEJAR (masuk 1,5 dtk SETELAH rilis searah gerak detik pertama, tanpa tebakan): rugi atau ≈ 0 di semua leverage → tidak ada
  jalan pintas "lihat dulu baru masuk".
- Tebakan ⚠️ lemah sejak 2022: untung hanya 39% rilis di 1:2000 (modal habis 10 dari 18) → JANGAN.
- Kalshi m/m saja: baru ada sejak 2022, tidak bisa diuji di periode lama.

**Putusan:** sesuai prinsip pengguna ("rugi modal kecil diterima selama untung sebelumnya menutupnya") strategi ini BAGUS di
5 tahun terakhir (tebakan jauh di atas acak, untung menutup rugi, rugi beruntun maks 2) tetapi GAGAL 2019–2021 (lebih buruk dari
acak). DIPASANG 13 Okt (izin "kalau bagus pasang") sebagai INFO, tanpa order, dengan kegagalan 2019–2021 ditulis di bukti.

## Yang dipasang (aplikasi 4.35)
- Cloud `_pra_aset.allin` → `pra_satu.allin` (hanya CPI; angka dari `cpi_detik.json["allin"]`, `python -m research.cpi_allin2
  simpan`; env CPI_ALLIN=0 mematikan). Tebakan kuat: "💥 Modal kecil: BUY/SELL 1 dtk sebelum rilis → TUTUP detik 2"; ⚠️ lemah:
  "💥 Modal kecil: JANGAN".
- Aplikasi: baris 💥 di bawah kotak XAU + "Lot maks 1:200" untuk modal kecil contoh (5.000/10.000 USC atau $50/$100; lot =
  saldo × leverage ÷ (harga × 100)); ketuk = bukti. Baris ⏱️ per detik memberi aba-aba: T−5…0 "💥 MASUK BUY/SELL", detik 0–2
  "tahan", detik 2–5 "💥 TUTUP SEKARANG".
- Saran pemakaian: akun TERPISAH berisi modal kecil saja (jangan akun bot utama), leverage 1:200–1:500, jangan tutup di
  detik 1. Cek batas leverage Exness saat berita; perlu tangan cepat atau EA untuk tutup tepat detik 2–5.
- Per jalur tebakan (1:200, detik 2, sejak 2022): jalur indeks konsensus 25 rilis untung 76% (+$17,6/rilis); jalur Kalshi
  (dipakai bila konsensus indeks belum ada — seperti CPI 14 Okt 2026) 7 rilis untung 86% (+$29,8) — sampel sangat kecil.
