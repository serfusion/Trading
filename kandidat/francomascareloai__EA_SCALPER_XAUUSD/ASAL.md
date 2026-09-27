# francomascareloai/EA_SCALPER_XAUUSD

- Sumber: https://github.com/francomascareloai/EA_SCALPER_XAUUSD
- Commit yang diaudit: `b0087e93c8af6690102c6698b8123186703a9240` (26–27 Sep 2026)
- Kategori: Fitur (engineering); Scalping
- Platform & timeframe: EA MQL5 + skrip Python/infra
- Login broker: EA di terminal; skrip Python .env
- Eksekusi & SL/TP: Order otomatis; safety gates
- Risiko / martingale / grid: Recovery/hedge ≤1× ukuran (bukan martingale) di profil agresif
- AI / fitur lain: ONNX, riset ML, LLM (tooling)
- Klaim penulis: Tanpa klaim hasil (dokumen: target)
- Hasil uji ulang bot ini: Aturan inti privat → tidak bisa diuji
- Catatan: DISENSOR: API key OpenRouter penulis. Pustaka standar MetaQuotes tidak disalin. Skrip infra VPS memasang Chocolatey & pengecualian Defender — jangan dijalankan di PC pribadi. Lisensi PolyForm Noncommercial

## Perubahan terhadap aslinya

- scripts/windows/run_litellm_proxy.bat: token/password/chat ID/secret penulis diganti placeholder ISI_…/GANTI_…
- scripts/windows/start_proxy_and_roo.bat: token/password/chat ID/secret penulis diganti placeholder ISI_…/GANTI_…
- .gitattributes -> gitattributes.asli (aturan git penulis)
- GEMINI.md -> GEMINI.md.asli (instruksi AI)
- CLAUDE.md -> CLAUDE.md.asli (instruksi AI)
- .gitignore -> gitignore.asli (aturan git penulis)
- AGENTS.md -> AGENTS.md.asli (instruksi AI)

## File tidak disalin (4)

- DOCS/04_REPORTS/BACKTESTS/phase2_results_20251202_020648.json — data besar 1956 KB
- MQL5/Include/Math/Alglib/alglib.mqh — file besar 2420 KB
- MQL5/Include/Math/Alglib/optimization.mqh — file besar 2246 KB
- models/direction_model_lstm.pt — biner/model/arsip (.pt)

Kode ini milik penulis aslinya dan disimpan apa adanya untuk dibandingkan. Jangan jalankan di akun real sebelum diperiksa (`python -m xau_bot audit kandidat/francomascareloai__EA_SCALPER_XAUUSD`) dan diuji di akun demo.
