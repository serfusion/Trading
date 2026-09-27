# a1shmuk/xauusd-algo-trader

- Sumber: https://github.com/a1shmuk/xauusd-algo-trader
- Commit yang diaudit: `0d08a488f2622da3d6b3967661965380704bbf0b` (26–27 Sep 2026)
- Kategori: Win-rate tinggi (klaim)
- Platform & timeframe: Python-MT5; H1 + filter H4
- Login broker: Terminal MT5 yang sudah login (mt5.initialize() tanpa password)
- Eksekusi & SL/TP: Order otomatis, SL/TP, keluar RSI/EMA
- Risiko / martingale / grid: % risiko 1%, lot 0,01–1,0
- AI / fitur lain: Filter makro FRED; modul ML
- Klaim penulis: WR 61,4%, PF 2,48, DD 2,91% (2024–26, 44 trade, dari 4.374 kombinasi)
- Hasil uji ulang bot ini: Backtest penulis memakai data masa depan (swing, close H4, TP sebelum SL). Tanpa itu: WR 31–36%, 2/4 periode, −51R
- Catatan: DISENSOR: token + chat ID Telegram penulis (saldo Anda akan terkirim ke dia) & API key FRED

## Perubahan terhadap aslinya

- fundamental_engine.py: token/password/chat ID/secret penulis diganti placeholder ISI_…/GANTI_…
- telegram_alerts.py: token/password/chat ID/secret penulis diganti placeholder ISI_…/GANTI_…

Kode ini milik penulis aslinya dan disimpan apa adanya untuk dibandingkan. Jangan jalankan di akun real sebelum diperiksa (`python -m xau_bot audit kandidat/a1shmuk__xauusd-algo-trader`) dan diuji di akun demo.
