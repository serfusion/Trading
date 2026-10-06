# Tangkap pisau jatuh: XAU, BTC, ETH & 20 koin (6 Okt 2026)

Permintaan pengguna: "saat XAU atau koin jatuh bisakah kita menangkap pisau itu untuk entry buy/sell? Seperti sekarang
XAU lagi jatuh. Uji validasi, cari informasi, keluarkan seluruh kemampuan."
Kode: `research/pisau.py` (pindai semua kombinasi), `research/pisau_cek.py` (uji ketahanan kandidat).
Hasil mentah: `docs/eksternal/hasil_pisau.txt`, `docs/eksternal/hasil_pisau_cek.txt`.

## Literatur (hipotesis awal)
- Kripto: Caporale & Plastun — pada hari "overreaction" harga cenderung **lanjut searah** (momentum) sampai akhir hari;
  hari berikutnya kadang berbalik. Ada juga temuan Bitcoin berbalik setelah guncangan negatif per jam.
- Emas intraday: hampir tidak ada studi khusus → diuji dua arah (balik dan lanjut).
- Sumber: [Brunel GMC 1909 Overreactions and trading strategies](https://www.brunel.ac.uk/economics-finance-and-accounting/research/pdf/1909-Mar-GMC-Overreactions-and-trading-strategies.pdf),
  [Momentum effect in the cryptocurrency market after one-day abnormal returns](https://www.brunel.ac.uk/economics-finance-and-accounting/research/pdf/1917-Oct-GMC-Momentum-effect-in-the-Cryptocurrency-Market-after-One-day-Abnormal-Returns.pdf),
  [Quantpedia: Price overreactions in the cryptocurrency market](https://quantpedia.com/price-overreactions-in-the-cryptocurrency-market/).

## Cara uji
- Candle H1: XAU 2012–2026, BTC 2016–2026, ETH 2017–2026, 19 koin + BTC spot 2017/2020–2026.
- "Jatuh" = turun ≥ k × ATR24 dari high tertinggi N jam terakhir (N 3–48 jam, k 3–8); "melonjak" = kebalikannya.
- Dua arah: **tangkap pisau** (BUY setelah jatuh / SELL setelah melonjak) dan **ikut arus** (SELL setelah jatuh /
  BUY setelah melonjak). Entry: pasar, tunggu konfirmasi candle balik, limit lebih dalam 0,5–1,5 ATR, pullback 25–50%,
  stop order tembus ujung candle. Keluar: SL 1–3 ATR, TP 0,5–3 ATR atau balik 38/50% gerakan, batas 6–48 jam.
  Filter tren besar (EMA ±50 hari): semua / searah / melawan. Total ±131.000 kombinasi per aset.
- Biaya: XAU $0,50 pulang-pergi (spread melebar saat pasar cepat), BTC/ETH 0,06%, koin spot 0,30%.
- Validasi: pilih hanya dari LAMA (< Okt 2021), lihat BARU; pembanding entry acak (arah, filter, aturan keluar sama);
  per tahun; tetangga parameter; biaya ×2/×3; entry telat 1 jam; ulang di candle M15/M5 (XAU).

## Hasil utama
| Aturan | LAMA | BARU (sejak Okt 2021) | Catatan |
|---|---|---|---|
| **XAU tangkap pisau sederhana** (BUY pasar setelah jatuh 5 ATR/12 jam, SL 2 / TP 1 ATR) | WR 59%, −0,11R | WR 64%, **−0,03R** | WR tinggi tapi RUGI; cek M5 sama |
| XAU jatuh 5 ATR/48 jam saat tren turun → BUY limit 1,5 ATR lebih dalam, TP balik 50%, SL 3 ATR, maks 48 jam | n 153, WR 55%, +0,20R | n 54, WR 52%, +0,12R | 4/14 tahun minus, tetangga parameter hanya 20% → rapuh |
| XAU jatuh 6 ATR/6 jam → SELL tembus low | n 45, +0,25R | n 28, +0,13R | ±0,4 sinyal/bulan, 32% sama dengan 💰 |
| **XAU melonjak 4 ATR/3 jam saat tren naik → BUY tembus high**, SL 3 / TP 2 ATR, maks 48 jam | n 93, WR 72%, +0,20R | n 71, **WR 69%, +0,16R** | 12/14 tahun +, biaya ×3 masih +, M5 +0,19R, 41% sama dengan 💰 |
| **BTC tangkap pisau sederhana** | WR 53%, −0,19R | WR 57%, **−0,13R** | RUGI |
| BTC jatuh 3 ATR/3 jam saat tren turun → SELL pasar, SL 2 / TP 3 ATR, maks 24 jam | n 222, +0,20R | n 336, WR 46%, +0,12R | 10/11 tahun ≥ 0, biaya ×3 → 0; 43% sama dengan 💰 |
| BTC melonjak 6 ATR/12 jam → BUY pasar, TP balik 50%, SL 3 ATR | n 160, +0,19R | n 185, WR 56%, +0,13R | 11/11 tahun +; 48% sama dengan 💰 |
| ETH jatuh 5 ATR/12 jam → SELL pasar, SL 2 / TP 3 ATR, maks 12 jam | n 155, +0,17R | n 262, +0,12R | 10/10 tahun + |
| ETH melonjak 6 ATR/24 jam saat tren naik → BUY pasar | n 152, +0,14R | n 168, +0,10R | 9/10 tahun + |
| **20 koin spot, BUY setelah jatuh/melonjak** (semua varian) | 1.308 kombinasi lolos | **0 tetap positif** | jangan dipakai |

Rata-rata SEMUA kombinasi (R/sinyal, BARU) dibanding entry acak dengan aturan sama:
| | Jatuh → BUY (tangkap) | Jatuh → SELL (ikut) | Melonjak → BUY (ikut) | Melonjak → SELL (tangkap) |
|---|---|---|---|---|
| XAU | −0,05 (acak −0,06) | −0,11 (acak −0,12) | −0,07 (acak −0,05) | −0,16 (acak −0,12) |
| BTC | −0,12 (acak −0,08) | −0,14 (acak −0,09) | −0,12 (acak −0,08) | −0,16 (acak −0,09) |
| ETH | −0,14 (acak −0,07) | −0,08 (acak −0,07) | −0,08 (acak −0,07) | −0,12 (acak −0,07) |
Rata-rata negatif karena sebagian besar kombinasi memang buruk + biaya; yang penting: menangkap pisau di BTC/ETH LEBIH
BURUK dari acak, di XAU sama dengan acak. Lolos LAMA lalu tetap positif BARU: XAU 17 dari 27, BTC 575 dari 2.318,
ETH 1.055 dari 3.520 (hampir semuanya varian "ikut arus"), koin spot 0 dari 1.308.

## Kesimpulan
1. **Menangkap pisau (beli tepat saat jatuh) tidak menguntungkan** di XAU, BTC, ETH, maupun koin spot. WR-nya memang
   tinggi (59–64%) karena harga sering memantul sedikit, tetapi kerugian saat lanjut jatuh lebih besar.
2. Yang konsisten justru **ikut arus**: setelah jatuh/melonjak cepat, harga cenderung **melanjutkan** arah (sesuai
   literatur kripto). Untung kecil per sinyal (+0,10–0,16R) dan ±40–48% sudah tercakup sinyal 💰 yang ada.
3. XAU sekarang (6 Okt 03:00 UTC, ±4.129): kejadian "jatuh 5 ATR/48 jam" terakhir 5 Okt 04:00 UTC; limit BUY
   4.105,49 tidak terisi dalam 12 jam → tidak ada entry pisau yang aktif. Sistem 💰 yang ada akan memberi SELL bila
   candle H1 tutup di bawah channel (±4.125,92).
4. Belum ada yang dipasang di cloud/aplikasi — menunggu kata "pasang" dari pengguna. Kandidat yang layak dipasang
   sebagai info: XAU "melonjak → BUY tembus high" dan "ikut arus" BTC/ETH.

## 🌊 Ikut arus DIPASANG (6 Okt 2026, izin "ikuti arus dengan catatan WR dan profit tinggi")
Hanya varian WR ≥ 62% di LAMA & BARU, ≥ 79% tahun positif (dipilih dari tabel riset; ambang WR ditentukan setelah
melihat kedua periode → anggap sebagai kandidat yang perlu dipantau maju):
| Aset | Aturan | LAMA | BARU |
|---|---|---|---|
| XAU | melonjak ≥ 4 ATR/3 jam, di atas EMA H1 1200 → BUY STOP 0,1 ATR di atas high (6 jam), SL 3 / TP 2 ATR, maks 48 jam | n 93, WR 72%, +0,20R | n 71, WR 69%, +0,16R |
| BTC | melonjak ≥ 6 ATR/12 jam → BUY pasar, SL 3 ATR, TP 38% gerakan, maks 48 jam | n 160, WR 63%, +0,16R | n 185, WR 62%, +0,12R |
| ETH | jatuh ≥ 5 ATR/6 jam, di bawah EMA → SELL pasar, SL 3 / TP 2 ATR, maks 12 jam | n 50, WR 64%, +0,18R | n 94, WR 64%, +0,19R |
Replay kode cloud ASLI `_arus.py` jam demi jam 2025–2026 (`research/arus_replay.py`): XAU 19/19 trade (WR 58% vs
riset 63%), BTC 63/63 (WR 59% = riset), ETH 41/41 (WR 63% = riset). 2025–2026 lebih lemah: XAU +0,06R, BTC +0,09R.
Cloud `cloud/api/_arus.py` (memakai candle yang sudah diambil, tanpa kredit Twelve Data tambahan), env ARUS_SIGNALS=0
mematikan; aplikasi 4.3 kartu 🌊 + notifikasi (sinyal, stop terisi, tutup, batal). Info saja, tanpa order.

