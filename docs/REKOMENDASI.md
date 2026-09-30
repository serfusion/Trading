# Rekomendasi Lanjutan: Profit & Win Rate (30 Sep 2026)

*Hanya berisi hal yang belum pernah diuji sebelumnya. Angka dihasilkan ulang dengan
`python -m research.rekomendasi`. Sinyal 💰 = mesin cloud yang sama; sinyal kembar = 1 entry dengan harga TUTUP set
paling lambat (sama seperti aplikasi). 1R = rugi penuh 5 posisi saat SL. Tidak ada perubahan pada bot live atau
cloud. Semua hasil adalah simulasi historis, bukan jaminan.*

Cek kebenaran: hasil per set identik dengan `realistic()` di `research/eksternal.py`
(XAU 1.554 trade +323,8R, BTC 2.096 trade +766,7R).

## 1. Biaya swap (belum pernah dihitung)

| | Entry | WR | Rata-rata | Lama pegang (median / rata / P90) |
|---|---|---|---|---|
| XAU 💰 2013–2026 | 764 | 49,2% | +0,213R | 1,2 / 2,5 / 6,6 hari |
| BTC 💰 2016–2026 | 983 | 49,8% | +0,413R | 1,1 / 1,9 / 4,7 hari |

- **BTC** (swap long −1.855,5 poin = 0,022% harga per hari, dihitung setiap hari): biaya **0,013R per entry**
  (BUY 0,021R). Totalnya +405,7R → +393,4R, sekitar 3% dari keunggulan. Kalau swap SELL sama besarnya: +387,6R.
  **Tidak masalah.**
- **XAU**: nilai swap XAUUSDc belum diketahui, jadi dihitung dengan dua skenario:

| Swap XAU | Hanya BUY kena | BUY & SELL kena |
|---|---|---|
| 5%/tahun | −0,025R/entry (+162,9 → +143,8R) | −0,043R (+130,1R) |
| 10%/tahun | −0,050R/entry (+124,7R) | −0,086R (+97,4R) |

  Swap bisa memakan **12–40% keunggulan XAU**. **Tindakan:** lihat MT5 → XAUUSDc → Spesifikasi → Swap long/short.
  Kalau nilainya 0 (bebas swap), tidak ada biaya.

## 2. Risiko berbeda per badge: tidak membantu

Rata-rata kategori dihitung dari periode LATIH. Kategori ≥ +0,2R diberi risiko 0,5%, sisanya 0,25%.
Hasilnya diuji di periode UJI (XAU 2019+, BTC 2021+):

| | Rata 0,5% | Rata 0,375% | Badge 0,5% / 0,25% |
|---|---|---|---|
| XAU | +6,5%/th, DD 11,8%, rasio 0,55 | +4,9%/th, DD 8,9%, rasio 0,55 | +6,1%/th, DD 12,6%, rasio **0,48** |
| BTC | +8,6%/th, DD 15,1%, rasio 0,57 | +6,4%/th, DD 11,3%, rasio 0,57 | sama dengan rata 0,5% (semua kategori ≥ 0,2R di latih) |

Kesimpulan: **tetap pakai risiko rata** (maks 0,5% per entry). Catatan: kategori XAU "konf" −0,017R di latih
vs +0,075R di uji; BTC "konf" +0,743R di latih vs −0,021R di uji. Keduanya dipantau, tidak dibuang, karena memilih
berdasarkan hasil periode uji sama dengan curang.

## 3. Hasil realistis dalam % modal: portofolio XAU + BTC, 2021–2026

Risiko 0,5% per entry, swap BTC dan filter September BTC ikut dihitung, filter funding tidak, tanpa bunga majemuk.

| Skema | Rata-rata/tahun | Max drawdown | Bulan untung | Bulan terburuk | Per tahun |
|---|---|---|---|---|---|
| Rata 0,5% | **+14,4%** | 15,0% | 53% | −3,9% | 2021 −8,9%, 2022 −5,5%, 2023 +31,9%, 2024 +22,1%, 2025 +23,7%, 2026 +18,1% |
| Badge 0,5/0,25% | +13,8% | 14,2% | 54% | −4,0% | 2021 −6,7%, 2022 −6,9%, 2023 +28,4%, 2024 +23,6%, 2025 +20,6%, 2026 +19,1% |

Per tahun per aset (rata-rata R per entry):

- **XAU**:
  - 2013 +1,05
  - 2014 +0,37
  - 2015 −0,20
  - 2016 +0,33
  - 2017 +0,07
  - 2018 −0,17
  - 2019 −0,01
  - 2020 +0,67
  - 2021 −0,10
  - 2022 −0,04
  - 2023 +0,15
  - 2024 +0,32
  - 2025 +0,45
  - 2026 +0,50
- **BTC** (sesudah swap, tanpa September):
  - 2016 +0,98
  - 2017 +1,40
  - 2018 +0,26
  - 2019 +0,65
  - 2020 +0,74
  - 2021 −0,15
  - 2022 −0,05
  - 2023 +0,68
  - 2024 +0,29
  - 2025 +0,18
  - 2026 +0,29

**Penting:** statistik badge BTC (mis. ⭐ +0,68R) terangkat oleh 2016–2020. Rata-rata 2021–2026 sekitar
+0,15R per entry. Ada 2 tahun rugi berturut-turut (2021–2022), jadi siapkan mental dan modal untuk itu.

## 4. Entry limit di harga pullback: tidak disarankan

| | Market (sekarang) | Limit 0,25×ATR, 3 candle | Limit 0,5×ATR, 3 candle | Limit 1×ATR, 6 candle |
|---|---|---|---|---|
| XAU latih / uji | +0,203 / +0,220R | +0,251 / +0,222R | +0,202 / +0,170R | +0,107 / +0,219R |
| BTC latih / uji | +0,754 / +0,148R | +0,792 / +0,148R | +0,807 / +0,105R | +0,803 / +0,138R |

Keuntungan limit 0,25×ATR hanya muncul di periode latih. Di periode uji hasilnya sama; per tahun XAU 10/14 dan
BTC 5/11. Win rate tidak naik. Sinyal yang paling kuat justru tidak pernah kembali ke harga limit.

## 5. Rekomendasi

1. **Cek swap XAUUSDc** di MT5 (lihat bagian 1). Ini satu-satunya biaya besar yang belum pernah dihitung.
2. **Jangan menambah filter atau mengubah cara entry.** Filter data eksternal, badge berbeda, dan limit pullback
   semuanya tidak lolos uji.
3. **Win rate tinggi** hanya realistis lewat pilihan SL+ 0,7R (WR ±55% vs ±45%, profit sedikit turun,
   `research/early_be.py`). Metode ber-WR 60–90% rugi setelah spread (`docs/UJI_DUNIA.md`).
4. **Kandidat pair baru**, menunggu izin pengguna: WTI Turtle D1 55 hari, TP 1R. Win 62–64%, +0,25–0,28R, lolos
   latih dan uji di uji dunia, tetapi hanya ±1 sinyal per bulan. Perlu diuji ulang dengan data terbaru sebelum
   dipasang.
5. **Profit terbesar datang dari modal dan waktu, bukan win rate.** Dengan rata-rata ±14%/tahun, perbarui "Modal"
   di aplikasi setiap bulan supaya lot ikut naik (bunga majemuk).
6. **Di luar trading**:
   - Pembanding tanpa leverage: SBN ritel (kupon dijamin negara; cek seri terbaru di situs Kemenkeu), deposito yang
     dijamin LPS, dan tabungan emas rutin (DCA $10/bulan 2012–2026: +156%, `docs/RISET_GITHUB.md` §7.2).
   - Trading ±14%/tahun datang dengan drawdown 15% dan tahun rugi. Pakai hanya uang yang siap hilang, dan simpan
     dana darurat terpisah.
