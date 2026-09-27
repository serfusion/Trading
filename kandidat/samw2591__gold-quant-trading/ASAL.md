# samw2591/gold-quant-trading

- Sumber: https://github.com/samw2591/gold-quant-trading
- Commit yang diaudit: `c8827bb939f791a4c6a02b010db979a45061cc04` (26–27 Sep 2026)
- Kategori: Profit terukur terbaik; Riset paling serius
- Platform & timeframe: Python + EA MQL4 (jembatan file); H1 Keltner/ORB, M15 RSI(2)
- Login broker: EA MQL4 di terminal (Python tidak login)
- Eksekusi & SL/TP: Order via EA, SL/TP ATR, trailing, stop waktu
- Risiko / martingale / grid: $ risiko tetap/trade, batas harian $100, stop total $1.500
- AI / fitur lain: Sentimen berita (GDELT), faktor makro, Telegram
- Klaim penulis: Keltner Sharpe 0,52 selama 11 th (hingga 8,4 di varian terbaik); ORB WR 61%
- Hasil uji ulang bot ini: Keltner sederhana SL4,5/TP8 ATR: +33,4R (3/4) — TERBAIK dari 63 repo; setelan live (stop 3 jam + trail 0,15 ATR): −143R; ORB NY −68R (positif 2022–26); RSI(2) M15 −190R
- Catatan: DISENSOR: token + chat ID Telegram penulis (saldo & ekuitas Anda akan terkirim ke dia). jlvalaty/gold-quant-trading = salinan sebagian dengan token sama

## Perubahan terhadap aslinya

- config.py: token/password/chat ID/secret penulis diganti placeholder ISI_…/GANTI_…
- .cursorrules -> cursorrules.asli (instruksi AI)
- .cursor/ -> cursor_asli/ (konfigurasi AI)
- .gitignore -> gitignore.asli (aturan git penulis)

## File tidak disalin (5)

- data/download/download/xauusd-m15-bid-2024-01-01-2026-03-25.csv — data besar 1780 KB
- data/download/download/xauusd-m5-bid-2020-01-01-2026-03-25.csv — data besar 25880 KB
- data/download/download/xauusd-m5-bid-2022-01-01-2026-03-25.csv — data besar 11865 KB
- data/download/xauusd-h1-bid-2015-01-01-2026-03-25.csv — data besar 4794 KB
- data/macro_history.csv — data besar 703 KB

Kode ini milik penulis aslinya dan disimpan apa adanya untuk dibandingkan. Jangan jalankan di akun real sebelum diperiksa (`python -m xau_bot audit kandidat/samw2591__gold-quant-trading`) dan diuji di akun demo.
