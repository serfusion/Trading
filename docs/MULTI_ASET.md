# Selain XAU: instrumen mana yang cocok dengan sistem ini?

Sistem yang diuji **sama persis** dengan sinyal sekarang: F-ensemble 3 set Donchian H1 (40/15, 55/20, 80/30),
SL 3×ATR, TP1 1R untuk posisi #1 + SL+, tanda ⭐ (tren D1 + breakout H4), lewati 3 candle setelah pasar buka.
Spread perkiraan akun Standard, entry di open candle berikutnya, SL dicek dulu. **Swap belum dihitung**
(posisi rata-rata ditahan ±2 hari, median ±33 jam).

Sumber data (GitHub publik): ejtraderLabs/historical-data (H1 2012–2022), FutureSharks/financial-data
(OANDA M1 2005–2020), ff137/bitstamp-btcusd-minute-data (BTC M1 2012 – Sep 2026).

## 1. Per instrumen — rata-rata R per sinyal ⭐, saldo ⭐0,5%/biasa0,25%

| Instrumen | Data | ⭐ R/sinyal | Saldo | DD | Tahun positif |
|---|---|---|---|---|---|
| **BTC/USD** | 2018–2022 | **+0,32** | +149% | −23% | 4/5 |
| **BTC/USD** | 2023–Sep 2026 | **+0,28** | +77% | −17% | 4/4 |
| **XAU/USD** | OANDA 2008–2020 | **+0,23** | +221% | −25% | 8/13 |
| **XAU/USD** | ejtrader 2012–2022 | **+0,27** | +148% | −27% | 8/11 |
| EUR/JPY | OANDA 2008–2020 | +0,13 | +107% | −18% | 10/13 |
| AUD/JPY | OANDA 2008–2020 | +0,08 | +48% | −23% | 10/13 |
| AUD/JPY | ejtrader 2012–2022 | +0,15 | +43% | −23% | 7/10 |
| WTI (minyak) | OANDA 2008–2020 | +0,08 | +60% | −16% | 8/13 |
| GBP/JPY, USD/JPY, EUR/JPY | ejtrader 2012–2022 | +0,04 | +8% s/d +38% | −17% s/d −23% | 5–7/10 |
| GBP/USD | 2008–2020 | +0,04 | −14% | −43% | 8/13 |
| EUR/USD, AUD/USD, USD/CHF, USD/CAD, EUR/GBP, EUR/CHF | 2012–2022 | −0,23 s/d +0,02 | −14% s/d −85% | besar | 0–4/10 |
| **Nasdaq 100, S&P 500, Russell 2000** | OANDA 2008–2020 | −0,05 s/d −0,06 | −50% | −60% | 3–5/13 |
| Nikkei, FTSE, CAC40, ASX200 | OANDA 2008–2020 | −0,04 s/d −0,11 | −27% s/d −46% | −36% s/d −55% | 3–5/13 |

Pola yang sama di semua instrumen yang untung: **sinyal ⭐ membawa profit, sinyal biasa ±impas**.
Indeks saham negatif: indeks sering berbalik di H1 (breakout gagal), cocoknya strategi lain, bukan breakout ini.
BTC 2012–2017 (+1,49R/sinyal) sengaja tidak dipakai sebagai acuan: masa awal, likuiditas tipis.

## 2. Digabung dalam satu akun (2018 – Mar 2022, `python -m research.portfolio_check`)

| Gabungan | ⭐0,25%/biasa0,125% | ⭐0,5%/biasa0,25% |
|---|---|---|
| XAU saja | +26% / DD −11% | +53% / DD −20% |
| BTC saja | +61% / DD −10% | +145% / DD −18% |
| **XAU + BTC** | **+101% / DD −11%** | +268% / DD −21% |
| XAU + AUDJPY + EURJPY | +40% / DD −15% | +79% / DD −28% |
| XAU + BTC + AUDJPY + EURJPY | +124% / DD −14% | +332% / DD −27% |

XAU + BTC memberi hasil/DD terbaik: keduanya jarang tren bersamaan, jadi rugi satu sering ditutup yang lain.
Tambahan pair JPY tidak memperbaiki gabungan di periode ini.

## 3. Catatan
- Saham gorengan tidak diuji dan tidak disarankan: harga mudah dimanipulasi (pump & dump), tidak bisa
  short, batas ARB/ARA membuat SL tidak bisa dieksekusi, dan data historis tidak tersedia di sini.
- BTC diperdagangkan 24/7 (termasuk akhir pekan); aturan jam pasar XAU tidak berlaku untuknya. Cek swap &
  spesifikasi lot BTC di akun Exness sebelum dipakai.
- Hasil masa lalu tidak menjamin masa depan.
