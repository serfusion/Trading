# sensesVoid/XAUUSD-AI-Agent

- Sumber: https://github.com/sensesVoid/XAUUSD-AI-Agent
- Commit yang diaudit: `a59875e30061267ea32f2a2c5ed0cf2e6b3be1b0` (26–27 Sep 2026)
- Kategori: Keamanan desain terbaik
- Platform & timeframe: Python-MT5, M15; sinyal RAG dari dokumen strategi + berita
- Login broker: .env (test.py berisi password penulis → disensor)
- Eksekusi & SL/TP: Order HANYA setelah persetujuan manual (y/N)
- Risiko / martingale / grid: % risiko
- AI / fitur lain: LLM lokal + RAG
- Klaim penulis: -
- Hasil uji ulang bot ini: Tidak bisa diuji otomatis (LLM)
- Catatan: DISENSOR: password MT5 demo penulis di test.py

## Perubahan terhadap aslinya

- test.py: token/password/chat ID/secret penulis diganti placeholder ISI_…/GANTI_…
- .gitignore -> gitignore.asli (aturan git penulis)

Kode ini milik penulis aslinya dan disimpan apa adanya untuk dibandingkan. Jangan jalankan di akun real sebelum diperiksa (`python -m xau_bot audit kandidat/sensesVoid__XAUUSD-AI-Agent`) dan diuji di akun demo.
