# ilahuerta-IA/backtrader-pullback-window-xauusd

- Sumber: https://github.com/ilahuerta-IA/backtrader-pullback-window-xauusd
- Commit yang diaudit: `995c51b472bcb57bc51861994ec2a1c443dc2d63` (26–27 Sep 2026)
- Kategori: Win-rate & profit (klaim)
- Platform & timeframe: Python backtrader (backtest saja); M5, LONG saja
- Login broker: -
- Eksekusi & SL/TP: Tidak ada eksekusi live; SL 4,5×ATR, TP 6,5×ATR
- Risiko / martingale / grid: Risiko 1%
- AI / fitur lain: -
- Klaim penulis: WR 55,43%, PF 1,64, +44,75%, DD 5,81% (Jul 2020–Jul 2025, 175 trade)
- Hasil uji ulang bot ini: 2022–25 (data optimasi penulis): +11,1R/28 trade; setelah data penulis (2025–26): −2,6R/5 trade
- Catatan: Data harga 5 tahun (20 MB) tidak disalin — dipakai bot ini sebagai dataset 2022–25 (research/download_data.sh)

## Perubahan terhadap aslinya

- .gitignore -> gitignore.asli (aturan git penulis)

## File tidak disalin (1)

- data/XAUUSD_5m_5Yea.csv — data besar 19395 KB

Kode ini milik penulis aslinya dan disimpan apa adanya untuk dibandingkan. Jangan jalankan di akun real sebelum diperiksa (`python -m xau_bot audit kandidat/ilahuerta-IA__backtrader-pullback-window-xauusd`) dan diuji di akun demo.
