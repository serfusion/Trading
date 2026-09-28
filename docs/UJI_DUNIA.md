# Uji besar: 31 metode × 21 instrumen + metode lintas pasar

Skrip: `research/world_lab.py` (uji), `research/world_report.py` (laporan), `research/cross_asset.py`.
Aturan sama untuk semua: sinyal di close H1 → entry open berikutnya (+spread), SL dicek dulu, tanpa data masa
depan, swap belum dihitung. Tiap metode punya beberapa parameter × 3 cara keluar (sinyal / TP 1R / TP 2R);
yang terbaik dipilih di periode **latih**, lalu dinilai di periode **uji** yang belum dilihat.

Instrumen (21): XAU, BTC, 11 forex (EURUSD, GBPUSD, AUDUSD, USDCAD, USDCHF, EURGBP, EURCHF, USDJPY, EURJPY,
GBPJPY, AUDJPY), WTI, Nasdaq 100, S&P 500, Russell 2000, Nikkei 225, FTSE 100, CAC 40, ASX 200.

Metode (31): Donchian, Turtle D1, EMA cross, Triple MA, Supertrend, Parabolic SAR, Ichimoku, ADX/DMI, Keltner,
Bollinger squeeze, MACD, Aroon, Hull MA, Heikin-Ashi, momentum harian, volatility breakout, London breakout,
inside bar D1, RSI(2) Connors, RSI(14) 30/70, Bollinger fade, Stochastic, CCI, Williams %R, z-score,
pivot S1/R1, engulfing D1, pin bar D1, turn-of-month, overnight drift, gap fade pekan.
Lintas pasar: rotasi momentum antar 12 instrumen (9 variasi), pairs trading (4 pasangan).

## Hasil utama (jujur)
1. **Hampir semua metode tidak punya keunggulan nyata.** Dari 648 pasangan (instrumen, metode), hanya 7 yang
   untung meyakinkan (t>2) di periode uji — padahal ±15 bisa muncul hanya karena kebetulan.
2. **Hanya 2 yang meyakinkan di latih DAN uji** (peluang kebetulan ±0,3):
   - BTC volatility breakout (k 0,6, TP 2R): latih +0,19R, uji +0,06R/trade, semua tahun uji untung.
   - WTI Turtle D1 55 hari (TP 1R): win 62–64%, +0,25–0,28R/trade, tapi hanya ±1 trade/bulan.
3. **Metode win rate tinggi** (RSI(2), Stochastic, CCI, Williams %R, pivot, z-score, pairs): win 53–66%,
   rata-rata **rugi** di hampir semua instrumen; tidak satu pun signifikan.
4. **XAU dan BTC satu-satunya instrumen yang rata-rata metodenya untung** (tren kuat). Indeks saham, mayor,
   dan cross selain JPY rata-rata rugi.
5. Rotasi momentum & pairs: untung di satu periode, rugi di periode lain → tidak konsisten.
6. Menarik tapi belum terbukti: XAU turn-of-month (beli hari terakhir bulan, TP 1R): uji win 58%, +0,18R,
   latih +0,12R (t<2). Layak dipantau, belum untuk dipakai.

| Golongan | Contoh | Win rate median | Hasil rata-rata (uji) |
|---|---|---|---|
| Tren & breakout | Keltner, Turtle, Donchian, Supertrend | 28–41% | ±0 (untung di XAU & BTC) |
| Mean-reversion | RSI(2), Stochastic, CCI, Williams | 51–61% | rugi |
| Pola candle | engulfing, pin bar | 45–46% | rugi |
| Waktu/musiman | turn-of-month, overnight, gap | 49–51% | ±0 |
| Lintas pasar | rotasi momentum, pairs | 44–66% | tidak konsisten |

## Kesimpulan
Tidak ada metode "ajaib" ber-win rate tinggi yang untung stabil. Yang terbukti tetap: **trend-following di XAU
dan BTC** dengan filter kualitas sinyal (lihat `docs/STRATEGI_LAB.md`: XAU konfluensi, BTC ⭐, skema F).
Kandidat tambahan untuk diversifikasi: BTC volatility breakout.
