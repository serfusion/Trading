# Audit D2 — Fork & Wiki dari 63 Repo

Tanggal: 27 Sep 2026. Kode tidak dijalankan. Alat: `research/audit_riwayat.py --fork` (aturan sama dengan audit awal).
Data: `docs/fork/`.

## 1. Wiki

Semua 63 repo dicek dengan `git ls-remote https://github.com/<repo>.wiki.git`. **Tidak ada satu pun yang punya wiki.**
Kontrol: wiki publik yang pasti ada (gollum/gollum, Ultimaker/Cura, microsoft/terminal) terbaca normal, jadi hasil
"tidak ada" bukan karena akses diblokir.

## 2. Fork

| Langkah | Hasil |
|---|---|
| Daftar fork lengkap (halaman *network/members* GitHub, termasuk fork dari fork) | **372 fork** di 26 repo; 37 repo tidak punya fork (3 di antaranya repo kosong) |
| `git ls-remote` setiap fork: apakah ada commit yang tidak ada di repo asli? | 342 fork = **salinan identik** (tanpa perubahan) · **30 fork punya commit baru** |
| 30 fork itu diunduh (berbagi objek dengan repo asli) dan **hanya isi barunya** dipindai | 99 commit baru, 1.514 versi file baru (`docs/fork/fork_temuan_ringkasan.csv`) |

### 2.1 Temuan di 30 fork yang berubah

| Fork | Isi baru | Penilaian |
|---|---|---|
| Photize/mt5-ai-xauusd-trader (dari triqbit) | Seluruh `venv` Windows ikut ter-commit: 872 file pustaka + `python.exe`, `pythonw.exe`, `pip.exe`. Pemindai menandai 16 BAHAYA (pola "keylog" di pustaka SSL pip, peluncur `.exe`) | ✅ Diverifikasi: 450 file cocok hash `RECORD` pip, sisanya cache `.pyc`; `python.exe`/`pythonw.exe` bertanda tangan **Anaconda, Inc.** dengan hash utuh; `pip.exe` = peluncur distlib standar + skrip pip standar. Bukan malware |
| fuzzyhead8/mt5-gold-ai-trader (dari HillaryMurimi) | 28 commit: strategi baru, 12 model `.joblib`, `install.py` (subprocess `pip install`) | ⚠️ Password MT5 pemilik fork tertulis di `backtests/get_historical_prices.py`; model `.joblib` = pickle (bisa menjalankan kode saat dimuat) |
| yusefhojjati-bit, REACH-ARC (dari 3aLaee) | File `.env` / `account2.env` ikut ter-commit | ⚠️ Password MT5 pemilik fork bocor (disensor di laporan) |
| Silentwolf360/XAUUSD-Trading-Bots (dari P1Piyush) | **Source `.mq5`** EA P1Piyush (XAU_Bot, PDH_Bot, XAU_Scalp, Bollinger_Reversal_Backtest, …) yang di repo asli hanya `.ex5` | ✅ EA hanya terhubung ke `127.0.0.1` (bot Python lokal); secret webhook bawaan `piyush_…` masih tertulis |
| akashvarshney (dari 0xagarg/GifariKemal) | Model `.pkl` cadangan | ⚠️ pickle |
| nanoracime-oss (dari phatnomenal) | Notifikasi Telegram di EA (token masih placeholder) | ✅ |
| T0RXD (dari codebytemirza) | `app.py` + `.pyc` | ✅ |
| tintommy (dari EA_SCALPER) | `CLAUDE.md` + dokumen agen AI | ✅ (instruksi AI penulis fork — tidak diikuti) |
| 22 fork lain | Perubahan README, requirements, data CSV, skrip backtest/strategi baru | ✅ Tidak ada temuan keamanan |

**Tidak ada fork yang menyisipkan malware, pencuri data, atau pengiriman data ke server asing.**

### 2.2 Fork yang menambah strategi (untuk perbandingan Anda)

JimmyTeck1991 (backtest scalper M1 & MA 5/10), tkt799 (EA MQL5 `SunriseOgle_XAUUSD.mq5` untuk ilahuerta),
andywarui (perbaikan bug & fitur breakeven ilahuerta), babaearn (Gold-Strategy-BT, versi deploy), fuzzyhead8
(beberapa strategi + model ML), Silentwolf360 (source EA P1Piyush). Belum diuji ulang; bisa ditambahkan ke tahap B
berikutnya bila Anda mau.

## 3. Batasan

- Daftar fork diambil 27 Sep 2026; fork baru setelah itu tidak tercakup. Fork privat/terhapus tidak terlihat.
- Ref pull request di fork tidak dipindai (yang dipindai: semua branch & tag fork).

Ulangi:

```bash
# daftar fork: https://github.com/<owner>/<repo>/network/members  → file "asli|fork" per baris
git clone --mirror --reference mirrors/<asli>.git https://github.com/<fork>.git forks/<asli>@@<fork>.git
python -m research.audit_riwayat mirrors --fork forks --csv docs/fork/fork_temuan.csv
```
