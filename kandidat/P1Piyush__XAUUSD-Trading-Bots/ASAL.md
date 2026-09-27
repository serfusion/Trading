# P1Piyush/XAUUSD-Trading-Bots

- Sumber: https://github.com/P1Piyush/XAUUSD-Trading-Bots
- Commit yang diaudit: `777f619f4ee46b9505c1a74b19e455f4e0d5d591` (26–27 Sep 2026)
- Kategori: Fitur; Scalping
- Platform & timeframe: Python (Flask webhook, Random Forest, PDH/PDL) + EA MQL5 socket
- Login broker: EA di terminal
- Eksekusi & SL/TP: Order via EA, SL/TP, trailing
- Risiko / martingale / grid: % risiko, batas harian 3%
- AI / fitur lain: Random Forest; Telegram
- Klaim penulis: Hasil penulis sendiri di results/: WR 0–50% per strategi
- Hasil uji ulang bot ini: PDH/PDL & ICT termasuk keluarga yang rugi (phatnomenal, SMC)
- Catatan: DISENSOR: secret webhook; 6 file .ex5 tanpa source tidak disalin

## Perubahan terhadap aslinya

- pdhl_bot.py: token/password/chat ID/secret penulis diganti placeholder ISI_…/GANTI_…
- web/index.html: token/password/chat ID/secret penulis diganti placeholder ISI_…/GANTI_…
- web/templates/dashboard.html: token/password/chat ID/secret penulis diganti placeholder ISI_…/GANTI_…
- CLAUDE.md -> CLAUDE.md.asli (instruksi AI)
- .gitignore -> gitignore.asli (aturan git penulis)

## File tidak disalin (13)

- builds/Bollinger_Reversal_Backtest.ex5 — biner/model/arsip (.ex5)
- builds/HFT_Scalp_Bot.ex5 — biner/model/arsip (.ex5)
- builds/ICT_Backtest.ex5 — biner/model/arsip (.ex5)
- builds/NY_Grid_Sweeper_Backtest.ex5 — biner/model/arsip (.ex5)
- builds/NY_Open_Reversal_Backtest.ex5 — biner/model/arsip (.ex5)
- builds/XAU_Bot.ex5 — biner/model/arsip (.ex5)
- data/historical_data.csv — data besar 635 KB
- docs/XAUUSD_Architecture_Prospectus.pdf — biner/model/arsip (.pdf)
- docs/XAUUSD_Architecture_Prospectus_v31.pdf — biner/model/arsip (.pdf)
- docs/XAUUSD_Bot_Deployment_Guide.pdf — biner/model/arsip (.pdf)
- docs/XAUUSD_Bot_Documentation.pdf — biner/model/arsip (.pdf)
- docs/XAUUSD_Bot_Future_Upgrades.pdf — biner/model/arsip (.pdf)
- docs/XAUUSD_Bot_Workflows.pdf — biner/model/arsip (.pdf)

Kode ini milik penulis aslinya dan disimpan apa adanya untuk dibandingkan. Jangan jalankan di akun real sebelum diperiksa (`python -m xau_bot audit kandidat/P1Piyush__XAUUSD-Trading-Bots`) dan diuji di akun demo.
