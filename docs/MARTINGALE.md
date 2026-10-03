# Martingale pendek + sinyal 💰 (3 Okt 2026)

Permintaan pengguna (gambar akun MT5 & video EA): "auto entry 0,01 x5; kalau masih loss 0,03 x5; loss lagi 0,05 x5;
TP pendek". Video = EA grid XAUUSDm M1 NFP 2 Okt: BUY berlapis tiap ±$1–1,5 setelah puncak 4.222 (0,01 x4 →
0,03 x5 → 0,05 x5), semua ditutup di TP keranjang 4.212,23 (+$1.564 pada modal $20.000). Sesudahnya emas turun ke
4.140: tanpa pantulan itu 0,44 lot mengambang ±−$3.000.
Skrip `research/martingale.py` → `docs/eksternal/hasil_martingale.txt`. Sinyal 💰 sama dengan cloud. R dasar = rugi
1 bagian (0,01 x5) bila SL awal kena.

| | XAU WR | XAU total | XAU DD | XAU rugi terbesar 1 sinyal | BTC WR | BTC total | BTC DD |
|---|---|---|---|---|---|---|---|
| Bawaan (lot tetap) | 48% | +324R | −44R | −1,4R | 48% | +766R | −56R |
| M1 antar sinyal 1x/3x/5x setelah kalah | 48% | +1.210R | **−173R** | −5R | 48% | +2.570R | **−183R** |
| M2 grid 1/3/5 dalam sinyal, jarak 0,33R, TP +0,2R | **89%** | −14R | −105R | **−5,1R** | **90%** | +187R | −98R |
| M2 grid jarak 0,2R, TP +0,1R | **91%** | −353R | −376R | −6,8R | 92% | −256R | −445R |

- **M1** = sebenarnya hanya lot rata-rata 3,1x lebih besar (47–49% sinyal memakai lot 5x). Dinormalkan per lot:
  total/DD XAU 7,0 vs bawaan 7,4; BTC 14,0 vs 13,7 → tidak ada keunggulan, tetapi DD 4x (−86% s/d −92% modal bila
  1R = 0,5%). Satu periode kalah beruntun (sampai 22–25 sinyal) cukup menghabiskan akun.
- **M2 (seperti video)**: WR 82–94% tetapi hasil total negatif/jauh di bawah bawaan; satu sinyal gagal = −5 s/d −6,8R
  (menghapus puluhan kemenangan kecil). 0 dari 12 varian lebih baik dari bawaan.
- Kesimpulan: TIDAK dipasang. WR tinggi dari martingale dibayar dengan rugi besar yang jarang tetapi pasti datang.
