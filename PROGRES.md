# PROGRES — Audit & Uji 63 Repo XAUUSD

Permintaan pengguna (27 Sep 2026): kerjakan **A, B, C**; bila batas sesi habis, simpan hasil + repo mentah di repo ini
agar Claude bisa melanjutkan di sesi berikutnya. Perbarui file ini setiap selesai satu langkah, lalu commit & push.

## Status

| Tahap | Isi | Status | Hasil |
|---|---|---|---|
| Audit awal | Pemindai statis semua file, inventaris 63 repo, 41 kandidat disimpan | ✅ selesai | `docs/AUDIT_63_REPO.md`, `kandidat/` |
| A | Riwayat git lengkap + GitHub Releases 63 repo; simpan repo mentah (git bundle) | ✅ selesai (2 bundle belum di git, lihat catatan) | `docs/AUDIT_RIWAYAT_RELEASES.md`, `docs/riwayat/`, `arsip_repo/` |
| C | Inventaris kemampuan SETIAP file (jaringan, file, proses, kode dinamis, kredensial, order) + tinjauan manual | ✅ selesai | `docs/AUDIT_SETIAP_FILE.md`, `docs/inventaris_file.csv` |
| B | Uji ulang strategi yang belum diuji | ✅ selesai (14/14) | `research/github_popular3.py`, `docs/AUDIT_63_REPO.md` §3.2, `docs/hasil_github_popular3.txt` |

## Putaran 2 (permintaan pengguna 27 Sep 2026: "A, B, C, D")

| Tahap | Isi | Status | Hasil |
|---|---|---|---|
| A2 | Pindai ISI arsip di riwayat + audit dependensi | ✅ selesai: 404 arsip (zip **dan** rar via libarchive), 10.113 file, 14 program dianalisa statis; 286 paket (HEAD) + 459 (riwayat) dicek ke PyPI/npm | `docs/AUDIT_ISI_ARSIP_DEPENDENSI.md`, `docs/arsip_dependensi/` |
| D2 | Fork & wiki dari 63 repo | ⏳ | `docs/AUDIT_FORK_WIKI.md` |
| B2 | Strategi yang belum diuji: EA GifariKemal, EA EA_SCALPER, sisa samw2591, AnggaKay, damaradam04, nathanaela2002 | ⏳ | `research/github_popular4.py` |
| C2 | Baca manual baris demi baris file inti 41 kandidat | ⏳ | `docs/TINJAUAN_MANUAL.md` |

## B — daftar strategi yang belum diuji

| Repo | Strategi | Status |
|---|---|---|
| Turnipnator/Oanda_Gold | EMA trend H1 (SL 1,5 ATR, TP 2R, trailing) | ✅ BUY saja (asli): WR 30%, −34,3R, 0/4 periode positif; +SELL: −59,3R, 1/4 |
| Turnipnator/Oanda_Gold | Triple confirmation (EMA20/50 + RSI + engulfing/pin) | ✅ WR 51,3%, −67,8R, 0/4 periode positif |
| BlamzKunG/XAUUSD-Grid-EA | Advanced Grid EA (lot ×1,20, hedge lock) | ✅ akun $1.000: 97–99% basket profit, tapi **akun habis** di 2012, 2020, 2023; 2025-26 −29,6% |
| shamshyder123-oss/gold-trading-ea | EA RSI/MACD/MA | ✅ tidak terkompilasi (`ctrade`), `iMA` dipakai sebagai nilai; versi diperbaiki: 4 syaratnya **tidak pernah terpenuhi bersamaan** (0 trade 2012-26) |
| thanvish21/gold-dominator | Gold Dominator Pro v3 (skor ≥80, tanpa volume) | ✅ asli: filter ekuitas macet (EMA float) → berhenti setelah rugi pertama (1–2 trade/periode); tanpa filter: WR 43%, −101,5R, 1/4; SELL tak pernah (bug skala StochRSI) |
| P1Piyush/XAUUSD-Trading-Bots | PDH/PDL (pdhl_bot.py), alpha_v3 | ✅ PDH/PDL M5: hanya 15 trade 2022-26, +5R (tidak bermakna); alpha_v3 tidak bisa diuji (butuh M1 + DXY; trailing memakai close bar yang sama = look-ahead) |
| nazhmi12/-XAUUSD-Hybrid-Trading-Bot-MT5- | FVG + OB + EMA200 M5 | ✅ bot aslinya men-trade 4 pair forex, BUKAN emas; aturannya di XAUUSD M5: 89 trade, +7R (2022-25 −10R, 2025-26 +17R) |
| Kiran-Kumbar/XAU-USD-Signal-Bot | Sinyal SMC/FVG | ✅ 3.454 sinyal, WR 32%, −126,4R, 0/2 periode positif |
| Sheyswaggz/gold-signal-provider-trading-bot--xauusd- | Sinyal TA-Lib | ✅ tidak ada kode strategi di branch/riwayat mana pun (hanya klien Redis + test); sinyal hanya di README |
| MarketForgeX/xauusd-ai-terminal | Aturan sinyal JS | ✅ bukan strategi teknikal: bias dari selisih actual vs forecast berita AS, tanpa SL/TP; tidak bisa diuji (butuh kalender historis + forecast) |
| HillaryMurimi/mt5-gold-ai-trader | MA 5/20 (versi tanpa look-ahead) | ✅ 3 strategi M5 (SMA5/20, RSI 30/70, MACD) SL $10/TP $20: −186R / −168R / −196R, WR 32%; backtest penulis look-ahead |
| RobertN1D/XAUUSD-GOLD-SCALPER | Inti setup scalper | ✅ tidak bisa diuji dengan data bar: keluar per tick ($0,40–1,20), DOM & kecepatan tick; butuh data tick |
| armza332/aurum-gold-desk | Aturan EA deterministik | ✅ asli: 'self-learning' mematikan agen permanen → berhenti trade (2014, 2019); tanpa learning: H1 −35R, M15 −62,5R |
| blackhunter4448-ops/Bot-trading-xau-usd | Sinyal teknikal H1 | ✅ asli tak jalan (modul hilang, SL/TP SELL terbalik, Alligator look-ahead); versi dimaksud: WR 46%, −227,9R, 0/4 |

Tidak bisa diuji apa adanya: EA terkompilasi (.ex5), kode tersandi (Minhtan2005), aturan privat (EA_SCALPER), bot LLM
(sensesVoid, armza332 bagian AI, Pestador, Mnauu2201 bagian Groq), model ML/RL tanpa dilatih ulang (diwakili uji
walk-forward di `research/github_popular.py`).

## Cara menyiapkan ulang di sesi baru

```bash
pip install -r requirements-dev.txt scikit-learn pyarrow
bash research/download_data.sh                      # data harga (di-gitignore)
# pulihkan repo mentah dari arsip (TIDAK menjalankan apa pun):
mkdir -p /tmp/repos && for b in arsip_repo/*.bundle; do n=$(basename "$b" .bundle); git clone -q "$b" "/tmp/repos/$n"; done
python -m xau_bot audit --ringkas /tmp/repos/*/
```

## Catatan kerja

- 2026-09-27: dimulai A (riwayat & Releases).
- 2026-09-27: A selesai. 8.732 commit / 66.372 versi file dipindai. Temuan baru: perpustakaan EA bajakan (exe/dll) di
  riwayat EA_SCALPER, EA "fix" bocoran di Lin-Thet-Zaw, kredensial terhapus (OANDA Turnipnator & nathanaela2002, dll.).
  58 dari 60 bundle ter-push; push Lin-Thet-Zaw & P1Piyush **diblokir pengaman sesi** (bundle mentah berisi kredensial
  asli penulis) → menunggu keputusan pengguna (lihat arsip_repo/README.md). Jangan mencoba mem-push-nya tanpa izin.
- 2026-09-27: C dimulai: `research/inventaris_file.py` (4.351 file, AST Python + pola teks). B dimulai: Turnipnator (2 strategi).
- 2026-09-27: C selesai. Tidak ada pencurian data di kode versi terakhir; risiko baru: server tanpa autentikasi
  (P1Piyush TCP/webhook 0.0.0.0, GifariKemal FastAPI POST filter), auto-push data ke GitHub (samw2591), alat crack (EA_SCALPER).
- 2026-09-27: B 5/14 (Turnipnator ×2, BlamzKunG Advanced Grid, shamshyder, thanvish21) — semua negatif / tidak jalan.
- 2026-09-27: B 8/14 (+ P1Piyush, nazhmi12, Kiran).
- 2026-09-27: B 13/14 (+ Sheyswaggz, MarketForgeX, HillaryMurimi, RobertN1D, armza332).
- 2026-09-27: B selesai 14/14. Tidak ada yang positif konsisten; peringkat kandidat tidak berubah.
  **A, B, C selesai.** Sisa: keputusan pengguna (lihat CLAUDE.md) — skema A live, tab Android, bundle mentah.
- 2026-09-27: A2 selesai. Loader injeksi kode + DLL palsu (winmm/aininet) di paket EA bajakan riwayat EA_SCALPER; terminal MT4/MT5 di dalamnya asli (hash tanda tangan cocok). Dependensi bersih.
