# Mnauu2201/Bot-Trade-Fucking-Gold

- Sumber: https://github.com/Mnauu2201/Bot-Trade-Fucking-Gold
- Commit yang diaudit: `6f8fd222c1f3751aab2c17f811d9459cd2ce8329` (26–27 Sep 2026)
- Kategori: Win-rate tinggi (klaim); Scalping (trigger M1)
- Platform & timeframe: Python-MT5; struktur H4/H1, zona H1, pola M15/M5, trigger M1
- Login broker: .env
- Eksekusi & SL/TP: Sinyal Telegram (tanpa order otomatis); SL di zona, TP 2R
- Risiko / martingale / grid: -
- AI / fitur lain: LLM Groq untuk narasi/sentimen
- Klaim penulis: WR 62,3% (R:R 1:2, ±20 bulan, tanpa hitung ±33% sinyal timeout)
- Hasil uji ulang bot ini: Backtest penulis memakai candle H4/H1/M15/M5 yang BELUM tutup (look-ahead). Ditiru: M5 17 bln WR 57,3% +79R; diperbaiki + spread: WR 27,6% −4,2R. M1 3 bln: 48% +12,3R → 0 menang/6 kalah −6,9R (research/mnauu_confluence.py)
- Catatan: Bersih; .zip berisi CSV laporan (dilewati karena arsip)

## Perubahan terhadap aslinya

- md/HUONG_DAN_SETUP.md: token/password/chat ID/secret penulis diganti placeholder ISI_…/GANTI_…
- .gitignore -> gitignore.asli (aturan git penulis)

## File tidak disalin (6)

- backtest/896800.zip — biner/model/arsip (.zip)
- backtest/backtest_report_20260826_184717_raw.zip — biner/model/arsip (.zip)
- backtest/bt_buy_sell.zip — biner/model/arsip (.zip)
- backtest/bt_buy_sell_2.zip — biner/model/arsip (.zip)
- backtest/bt_buy_sell_3.5.zip — biner/model/arsip (.zip)
- backtest/bt_new.zip — biner/model/arsip (.zip)

Kode ini milik penulis aslinya dan disimpan apa adanya untuk dibandingkan. Jangan jalankan di akun real sebelum diperiksa (`python -m xau_bot audit kandidat/Mnauu2201__Bot-Trade-Fucking-Gold`) dan diuji di akun demo.
