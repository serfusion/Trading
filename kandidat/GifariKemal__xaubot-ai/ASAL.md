# GifariKemal/xaubot-ai

- Sumber: https://github.com/GifariKemal/xaubot-ai
- Commit yang diaudit: `10301c8665443d2b83569840df65de49b6890cbe` (26–27 Sep 2026)
- Kategori: Win-rate tinggi (klaim); Fitur terlengkap; AI
- Platform & timeframe: Python-MT5 + EA MQL5 (source ada); M15 utama (+H1/M5/H4)
- Login broker: .env (MT5_LOGIN/MT5_PASSWORD)
- Eksekusi & SL/TP: Order otomatis, SL/TP, trailing/BE
- Risiko / martingale / grid: % risiko, batas harian, maks posisi; tanpa martingale (dihapus di kode)
- AI / fitur lain: XGBoost + HMM rezim + SMC; dashboard Next.js; Telegram
- Klaim penulis: WR 63,9%, PF 2,64, DD 2,2%, Sharpe 4,83 (Jan 2025–Feb 2026, 654 trade)
- Hasil uji ulang bot ini: Model sejenis (gradient boosting walk-forward): akurasi arah 51,3%, positif 2/4 periode; SMC otomatis rugi
- Catatan: 0xagarg/xau-ai-trading-bot & BizShibe/XAUUSD-ai-trading-bot = salinan identik; file model .pkl tidak disalin

## Perubahan terhadap aslinya

- web-dashboard/.gitignore -> gitignore.asli (aturan git penulis)
- CLAUDE.md -> CLAUDE.md.asli (instruksi AI)
- .gitignore -> gitignore.asli (aturan git penulis)

## File tidak disalin (18)

- backtests/36_ml_v2_results/model_a.pkl — biner/model/arsip (.pkl)
- backtests/36_ml_v2_results/model_b.pkl — biner/model/arsip (.pkl)
- backtests/36_ml_v2_results/model_baseline.pkl — biner/model/arsip (.pkl)
- backtests/36_ml_v2_results/model_c.pkl — biner/model/arsip (.pkl)
- backtests/36_ml_v2_results/model_d.pkl — biner/model/arsip (.pkl)
- backtests/36_ml_v2_results/model_e.pkl — biner/model/arsip (.pkl)
- backtests/ml_v3/xgboost_model_v3.pkl — biner/model/arsip (.pkl)
- data/training_data.parquet — biner/model/arsip (.parquet)
- ea-research/xaubot-mq5/Experts/XAUBot_Pro.ex5 — biner/model/arsip (.ex5)
- ea-research/xaubot-mq5/Experts/XAUBot_Pro_Lite_v2.ex5 — biner/model/arsip (.ex5)
- ea-research/xaubot-mq5/Experts/XAUBot_Pro_V3.ex5 — biner/model/arsip (.ex5)
- ea-research/xaubot-mq5/Experts/XAUBot_Pro_v2.ex5 — biner/model/arsip (.ex5)
- models/backups/20260205_000415/hmm_regime.pkl — biner/model/arsip (.pkl)
- models/backups/20260205_000415/xgboost_model.pkl — biner/model/arsip (.pkl)
- models/backups/20260206_050134/hmm_regime.pkl — biner/model/arsip (.pkl)
- models/backups/20260206_050134/xgboost_model.pkl — biner/model/arsip (.pkl)
- models/backups/20260210_020005/hmm_regime.pkl — biner/model/arsip (.pkl)
- models/backups/20260210_020005/xgboost_model.pkl — biner/model/arsip (.pkl)

Kode ini milik penulis aslinya dan disimpan apa adanya untuk dibandingkan. Jangan jalankan di akun real sebelum diperiksa (`python -m xau_bot audit kandidat/GifariKemal__xaubot-ai`) dan diuji di akun demo.
