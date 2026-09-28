# Mencari profit stabil & win rate tinggi: 9 keluarga metode × XAU, BTC, EUR/JPY

Aturan uji sama untuk semua: sinyal di close H1 → entry di open berikutnya (+spread), SL dicek lebih dulu,
tanpa data masa depan, swap belum dihitung. Parameter dipilih di periode **latih**, dinilai di periode **uji**
(XAU 2019–2026, BTC 2021–2026, EUR/JPY 2016–2022). Skrip: `research/strategy_lab.py` … `strategy_lab4.py`.

## 1. Satu metode, satu posisi (periode uji)

| Metode | XAU | BTC | EUR/JPY | Win rate |
|---|---|---|---|---|
| Donchian breakout | **+0,09R** | **+0,07R** | −0,03R | 30–39% |
| Supertrend | **+0,10R** | **+0,14R** | +0,01R | 28–35% |
| EMA cross | **+0,12R** | **+0,06R** | −0,39R | 19–25% |
| Momentum harian (60/20 hari) | **+0,16R** | **+0,12R** | +0,08R | 37–56% |
| Volatility breakout harian | +0,04R | +0,04R | −0,03R | 42–50% |
| MACD + tren | +0,02R | +0,06R | −0,01R | 30–33% |
| Pullback RSI dalam tren | −0,03R | +0,01R | −0,05R | 39–63% |
| **RSI(2) Connors** (win rate tinggi) | −0,01R | −0,01R | −0,02R | **60–66%** |
| **Bollinger fade** (win rate tinggi) | 0,00R | 0,00R | −0,05R | **47–63%** |

Metode ber-win rate tinggi (mean-reversion) **rugi/impas** setelah spread di ketiga instrumen. Yang untung
adalah metode tren (win rate rendah, untung per trade besar). EUR/JPY gagal di hampir semua metode
setelah 2016 → **tidak disarankan**.

## 2. Penaik win rate & stabilitas pada Donchian 3 set (skema F: TP1 1R + SL+)
- Skema F menaikkan win rate ±10 poin (35% → 45%) dengan R rata-rata sedikit lebih kecil.
- Filter **konfluensi 3/3** = EMA50 vs EMA200 (H1), Supertrend 3×ATR (H1), dan momentum 60 hari (D1) searah
  dengan sinyal. Di XAU paling baik di 3 dari 4 periode, DD paling kecil di 3 dari 4 periode:

| XAU, R/sinyal (DD) | 2012–15 | 2016–18 | 2019–20 | 2021–26 |
|---|---|---|---|---|
| Tanpa filter | +0,09 (−19%) | +0,00 (−29%) | +0,25 (−16%) | +0,05 (−39%) |
| ⭐ (sekarang) | +0,22 (−18%) | +0,01 (−25%) | +0,48 (−15%) | +0,07 (−39%) |
| **Konfluensi 3/3** | **+0,36** (−18%) | **+0,05** (−19%) | +0,31 (−8%) | **+0,19** (−18%) |

- BTC: ⭐ dan konfluensi sama-sama baik (2016–18, 2018–21); ⭐ lebih baik di 2021–26 (+0,17R vs +0,10R).

## 3. Satu akun XAU + BTC, 2021 – Sep 2026 (0,5% per sinyal, tanpa bunga majemuk)

| Rencana | Win | Total | DD | Bulan untung | Kuartal untung | Bulan terburuk |
|---|---|---|---|---|---|---|
| Donchian tanpa filter | 43,6% | +106% | −57% | 42% | 48% | −16,6% |
| Sekarang: ⭐ di XAU & BTC | 45,1% | +113% | −38% | 51% | 57% | −11,0% |
| **Konfluensi (XAU) + ⭐ (BTC)** | **46,8%** | **+153%** | **−23%** | **58%** | **65%** | **−9,1%** |
| Multi-metode (Donchian ⭐ + Supertrend konf + EMA) | 45,9% | +173% | −34% | 54% | 61% | −16,9% |

## Kesimpulan jujur
- Tidak ditemukan metode yang untung stabil **dan** win rate 70–90%. Win rate tinggi selalu dibayar dengan
  rugi besar sesekali; setelah spread hasilnya impas/rugi.
- Paling baik yang ditemukan: **XAU dengan filter konfluensi + BTC dengan filter ⭐**, skema F.
  Win rate ±47%, ±58% bulan untung, ±65% kuartal untung. Bulan rugi tetap ada.
