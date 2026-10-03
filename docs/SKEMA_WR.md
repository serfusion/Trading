# Skema WR tinggi: TP pendek + 1–2 posisi berjalan (3 Okt 2026)

Permintaan pengguna (setelah sinyal 💰 BTC BUY 86.628 kena SL 85.094 pada 2 Okt 23:00 WIB, −1.380,89 USC; BTC lalu
turun ke 83.888): "ubah pola yang WR tinggi dengan TP pendek, sisakan 1–2 posisi sampai TUTUP".
Skrip `research/skema_wr.py` → `docs/eksternal/hasil_skema_wr.txt`. Sinyal tidak berubah (mesin cloud, kategori 💰);
yang diuji hanya pembagian 5 posisi.

| Skema (5 posisi) | XAU WR | XAU R/sinyal | XAU total | BTC WR | BTC R/sinyal | BTC total | Kalah beruntun maks (XAU/BTC) |
|---|---|---|---|---|---|---|---|
| **Bawaan: TP1 1R + 4 jalan** | 48% | **+0,21** | **+324R** | 48% | **+0,37** | **+766R** | 25 / 22 |
| 2 TP 0,5/1R + 3 jalan | 65% | +0,12 | +218R | 62% | +0,19 | +484R | 12 / 19 |
| 3 TP 0,5/1/1,5R + 2 jalan | 65% | +0,10 | +183R | 62% | +0,13 | +338R | 12 / 19 |
| 3 TP 0,3/0,5/0,7R + 2 jalan | 72% | +0,06 | +130R | 69% | +0,08 | +229R | 12 / 17 |
| 4 TP 0,3–1R + 1 jalan | 72% | +0,04 | +77R | 69% | +0,03 | +85R | 12 / 17 |
| 5 TP 0,5R (tanpa jalan) | 66% | +0,01 | +24R | 65% | −0,01 | −26R | 14 / 20 |

- **0 dari 12 skema lolos**: WR naik ke 62–72%, tetapi profit per sinyal turun 45–95% (BTC periode baru hampir nol).
  Sebabnya: rugi tetap −1R penuh bila SL kena sebelum TP pendek, sedangkan untung dipotong kecil.
- Kelebihan nyata TP pendek: kalah beruntun terpanjang XAU 12 (bawaan 25) — lebih nyaman secara psikologis.
- Kasus 2 Okt: harga tertinggi setelah entry 87.220 (+0,39R). TP 0,3R akan kena → skema 0,3/0,5/0,7R berakhir +0,14R
  (±+190 USC) alih-alih −1R. Tetapi rata-rata ribuan sinyal: skema bawaan menghasilkan 2,5–4× lebih banyak.
- Kategori: "semua sinyal (+ biasa)" XAU +0,08R vs 💰 +0,21R, BTC +0,20R vs +0,37R (`docs/SINYAL_LAPIS.md`) —
  1 sinyal biasa yang untung belum membuktikan apa pun.
- BELUM dipasang: perubahan skema = keputusan pengguna (CLAUDE.md, keputusan tertunda (1)).
