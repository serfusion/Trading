# Turnipnator/Oanda_Gold

- Sumber: https://github.com/Turnipnator/Oanda_Gold
- Commit yang diaudit: `870e7964c3577ddabb77bc8ece3b008a89ac6d4e` (26–27 Sep 2026)
- Kategori: Fitur (bot live lengkap + test)
- Platform & timeframe: Node.js, broker Oanda; H1 (breakout+ADX / EMA trend / triple confirmation)
- Login broker: Oanda API key (.env)
- Eksekusi & SL/TP: Order otomatis, SL wajib di order (stopLossOnFill), trailing
- Risiko / martingale / grid: % risiko, batas harian
- AI / fitur lain: Telegram
- Klaim penulis: Target WR 55–65%; komentar config: 18 menang / 4 kalah, PF 1,57 (22 trade)
- Hasil uji ulang bot ini: Breakout 10 bar + ADX≥35 SL=TP $3: −513R (0/4)
- Catatan: claude_asli/ & CLAUDE.md.asli = file instruksi AI penulis (dinonaktifkan)

## Perubahan terhadap aslinya

- CLAUDE.md -> CLAUDE.md.asli (instruksi AI)
- .gitignore -> gitignore.asli (aturan git penulis)
- .claude/ -> claude_asli/ (konfigurasi AI)

Kode ini milik penulis aslinya dan disimpan apa adanya untuk dibandingkan. Jangan jalankan di akun real sebelum diperiksa (`python -m xau_bot audit kandidat/Turnipnator__Oanda_Gold`) dan diuji di akun demo.
