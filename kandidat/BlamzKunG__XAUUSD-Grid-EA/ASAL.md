# BlamzKunG/XAUUSD-Grid-EA

- Sumber: https://github.com/BlamzKunG/XAUUSD-Grid-EA
- Commit yang diaudit: `9ffd0840f53b17c33396427721d02885e36b88cd` (26–27 Sep 2026)
- Kategori: Win-rate tertinggi terukur; Grid
- Platform & timeframe: EA MQL5; entry M15, filter H1
- Login broker: EA di terminal (tanpa simpan password)
- Eksekusi & SL/TP: Order otomatis; basket TP, SL darurat 3,5×ATR H1, trailing basket
- Risiko / martingale / grid: Grid 5 level (MR EA, lot ×1,15 opsional); Advanced Grid EA: lot ×1,20 per level + hedge lock
- AI / fitur lain: -
- Klaim penulis: -
- Hasil uji ulang bot ini: Mean-reversion grid: 92–96% basket profit, tapi −224,7R (0/4 periode). Grid martingale umum: akun $1.000 habis berkali-kali
- Catatan: -

## Perubahan terhadap aslinya

- .gitignore -> gitignore.asli (aturan git penulis)

Kode ini milik penulis aslinya dan disimpan apa adanya untuk dibandingkan. Jangan jalankan di akun real sebelum diperiksa (`python -m xau_bot audit kandidat/BlamzKunG__XAUUSD-Grid-EA`) dan diuji di akun demo.
