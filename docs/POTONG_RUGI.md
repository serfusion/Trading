# Sinyal 💰: apakah hanya berlaku beberapa jam? Perlu dipotong setelah turun separuh? (2 Okt 2026)

Pertanyaan pengguna (BTC BUY 86.628, harga turun ke 85.796 ≈ −0,54R): "apakah sinyal 💰 hanya sementara, berlaku
beberapa jam saja? Setelah turun setengahnya dia tidak akan ke atas lagi, alhasil ke bawah."

Skrip `python -m research.potong_rugi` → `docs/eksternal/hasil_potong_rugi.txt`. Mesin sama dengan cloud
(`research/sl_tangga.backtest`, skema bawaan 5 posisi). BTC 2.097 sinyal 💰 (2016–2026, WR 48% = badge aplikasi),
XAU 1.554 sinyal (2013–2026). LAMA = BTC < 2021 / XAU < 2019.

## Jawaban

1. **Sebagian benar:** dari sinyal yang sempat rugi −0,5R sebelum TP1, **58–59% akhirnya kena SL** dan hanya **21%**
   kena TP1 (BTC & XAU, kedua periode).
2. **Tetapi memotong di −0,5R tetap lebih buruk.** Rata-rata hasil akhir bila ditahan: BTC **−0,30R**, XAU **−0,41R**
   — lebih baik daripada potong −0,5R. Uji nyata (set boleh masuk lagi lebih cepat):
   | Skema | BTC R/sinyal (LAMA/BARU) | XAU R/sinyal (LAMA/BARU) |
   |---|---|---|
   | Bawaan (tahan sampai SL/TUTUP) | **+0,365** (+0,655/+0,144) | **+0,208** (+0,191/+0,221) |
   | Potong −0,5R sebelum TP1 | +0,257 (+0,485/+0,083) | +0,113 (+0,136/+0,098) |
   | Potong −0,7R sebelum TP1 | +0,295 | +0,128 |
   Potong membuat WR turun ke 35% dan profit total turun 15–35%.
3. **Sinyal tidak kedaluwarsa dalam beberapa jam.** TP1 kena median **11–12 jam** setelah entry, 75% dalam 21–23 jam,
   90% dalam 38–42 jam. Sinyal yang belum TP1 setelah 24 jam masih rata-rata **+0,36 s.d. +0,40R** bila ditahan.
   −0,5R biasanya tersentuh di jam ke-5 (median) — jadi "turun separuh dalam beberapa jam" adalah hal yang biasa,
   bukan tanda sinyal mati.
4. Batas waktu 12/24/48 jam (semua atau hanya bila rugi): tidak ada yang lebih baik di LAMA **dan** BARU dengan ≥ 60%
   tahun lebih baik → **skema bawaan tetap**.

## Catatan risiko

Satu sinyal bisa tetap kena SL; yang diuji adalah rata-rata ratusan sinyal. Pakai lot yang dihitung aplikasi
(rugi maks di SL ±0,5% modal). Lot yang lebih besar dari anjuran membuat rugi beruntun terasa jauh lebih berat
walaupun peluangnya sama.
