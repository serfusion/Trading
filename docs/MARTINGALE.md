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

## EA grid martingale ala screenshot trader (3 Okt 2026)

Pertanyaan pengguna: trader XAU/USD mengaku dapat ±$150 per akun dari EA martingale "x2 sampai 20 layer lebih" dan
mau membuka akun lagi di VPS — masuk akal? Skrip `research/martingale_ea.py` → `docs/eksternal/hasil_martingale_ea.txt`
(aturan ditulis ulang, bukan kode EA; data M15 2012–2020, M5 2020–2026, M5 Twelve Data 16 Sep–2 Okt 2026 tanpa bar
akhir pekan; spread $0,20; swap diabaikan).

**Isi screenshot (akun Exness Cent, angka USC ÷ 100 = dolar):**
- 3 riwayat, saldo masing-masing ±$430; profit tertutup $114 / $121 / $126 (bukan $150), sudah seluruh riwayat
  (Deposit − Withdrawal + Profit = Balance). Total: setor bersih ±$929, profit ±$360, saldo yang dipertaruhkan ±$1.290.
- Keranjang 2 Okt: BUY 1,03 / 1,24 / 1,49 / 1,79 lot = pengali **1,2 (bukan 2)**, jarak $1,35–2,1, ditutup bersama
  ±02:05 UTC di 4.154 (Twelve Data: emas turun dari 4.182 jam 00:00 ke ±4.135–4.145 jam 01:10 lalu memantul).
  KOREKSI (bukti tambahan, `docs/SIGNAL_STRIKE.md`): itu L14–L17 dari rantai 0,10 × 1,2 (17 layer sejak 00:05, layer
  minus tersembunyi karena urutan Profit ▲), bukan "8 layer mulai 0,5 lot"; 0,5 lot 17 Sep = L10 keranjang lain.
  Varian A–G di bawah tetap berlaku sebagai pembanding; aturan hasil rekonstruksi diuji di SIGNAL_STRIKE.
- Tab History hanya posisi tertutup (keranjang yang sedang mengambang tidak terlihat) dan diurutkan Profit ▲ (baris
  paling atas tidak terlihat). Status bar menunjukkan 2 Okt 13:00; 3 jam kemudian emas turun $100 (4.225 → 4.126).

**"x2 sampai 20 layer" mustahil di saldo $430:** mulai 0,01 lot → layer 20 = 5.243 lot, total 10.486 lot ($10.486 per
$1 gerak), margin 1:2000 ±$21.758. Di simulasi x2 hanya sanggup 11–13 layer (margin habis). Pengali 1,2 (yang
terlihat): 20 layer = 93 lot, rentang $28,5, rugi mengambang $625 > $430 → akun habis sekitar **layer 17** (emas turun
±$27 tanpa pantulan $3–5). Maks 30 layer hasilnya identik dengan maks 20.

**Per keranjang** (satu keranjang tiap 6 jam, akun $430 baru — tidak bergantung aturan entry EA):

| Varian | LAMA < Okt 2021 | BARU Okt 2021+ | 12 bulan terakhir |
|---|---|---|---|
| A seperti screenshot: BUY 0,5 lot ×1,2 jarak $1,5 TP rata-rata +$5 | habis 1 dari 13, untung rata $28, harapan −$6,2 | 1 dari 15, $28, −$2,1 | 1 dari 14, $32, −$0,4 |
| C sama, dua arah | 1 dari 14, −$5,6 | 1 dari 15, −$1,8 | 1 dari 14, −$1,2 |
| D ×1,2 jarak $3 | 1 dari 25, $14, −$3,8 | 1 dari 30, $14, −$1,3 | 1 dari 24, $14, −$4,8 |
| E ×2 0,05 lot jarak $1,5 TP +$3 | 1 dari 27, $12, −$4,3 | 1 dari 28, $13, −$3,0 | 1 dari 17, $15, −$10,3 |
| F ×2 0,05 lot jarak $3 | 1 dari 75, $4, −$1,8 | 1 dari 85, $3, −$1,8 | 1 dari 52, $5, −$3,8 |
| G ×2 0,01 lot jarak $3 | 1 dari 156, $1,7, −$1,1 | 1 dari 165, $1,3, −$1,3 | 1 dari 77, $1,7, −$3,8 |

Nilai harapan per keranjang negatif di semua varian & periode: makin jarang habis, makin kecil untung per keranjang.

**Akun baru tiap awal bulan, EA selalu aktif** (habis ≤ 30 hari / ≤ 90 hari / umur median / ditarik median / bersih median):
A LAMA 89% / 100% / 8 hari / $303 / −$127, BARU 100% / 100% / 2 hari / $219 / −$211; D LAMA 61% / 95% / 20 hari,
BARU 87% / 100% / 6 hari; G (paling awet) LAMA 31% / 62% / 61 hari / $241 / −$189, BARU 61% / 93% / 19 hari / $291 /
−$139. Rata-rata bersih kadang positif (A LAMA +$49, D BARU +$99) karena beberapa akun hidup lama, tetapi median selalu
negatif. Uji resolusi (M1 vs M5 Feb–Mei 2026, varian A): habis 5,9% vs 6,2% per keranjang → M5 cukup.

EA asli jelas lebih selektif (versi "selalu aktif" sejak 17 Sep habis 39x sampai 2 Okt, akun asli masih hidup), jadi
umurnya lebih panjang; tetapi kalau entrinya tidak punya keunggulan, peluang per keranjang tetap ±1 dari 14–30.
Contoh kasar: ±3 keranjang/pekan → umur harapan ±1–2,5 bulan. Akun tambahan di VPS bukan diversifikasi: EA, pair dan
arah sama → habis bersamaan dalam satu pergerakan; VPS hanya membuat EA jalan 24 jam (termasuk saat NFP/CPI).

Kesimpulan: profit $114–126/akun **masuk akal sebagai hasil sementara** (persis "ditarik median $219–303 sebelum
habis" di simulasi), **tidak masuk akal sebagai penghasilan aman/berkelanjutan**. TIDAK dipasang di bot.
