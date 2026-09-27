# Katalog Kandidat dari 63 Repo XAUUSD

Folder ini menyimpan **41 repo kandidat** (kode asli penulis) untuk Anda bandingkan sendiri. Setiap folder punya
`ASAL.md`: sumber, commit yang diaudit, kategori, platform, cara login, eksekusi & SL, risiko/martingale, klaim
penulis, hasil uji ulang bot ini, dan daftar perubahan.

## Sejauh mana pengecekannya

| Aspek | Cakupan | Cara |
|---|---|---|
| Keamanan (malware, pencuri data, kebocoran) | **Semua 4.357 file** di 63 repo | Pemindai `xau_bot/audit.py` + setiap temuan dibaca manual; pemindaian rahasia kedua di folder ini |
| Platform, timeframe, scalping, login MT5, order otomatis, SL/TP, trailing, martingale/grid/hedging, manajemen risiko, filter berita/sesi, AI/LLM, Telegram, backtest | **Semua 63 repo**, otomatis + kolom `verifikasi_manual` | `python -m research.inventaris_repo` → `inventaris_63_repo.csv` (bila kolom otomatis berbeda, kolom manual yang benar) |
| Kolom yang sama, diverifikasi manual (baca baris kodenya) | **41 kandidat** | Hasilnya di `ASAL.md` tiap folder |
| Klaim win-rate / profit / drawdown | README & dokumen semua repo; laporan hasil (CSV/MD) bila ada | Dikutip apa adanya |
| Uji ulang strategi di data asli 2012–2026 (spread, tanpa look-ahead) | **30 strategi** dari 18 repo + 5 repo ML diwakili uji walk-forward; yang tidak bisa diuji beserta alasannya: paragraf di bawah & `docs/AUDIT_63_REPO.md` §3.2 | `research/github_popular*.py`, `research/mnauu_confluence.py` |

Yang **tidak** bisa dipastikan: isi EA terkompilasi (.ex5/.ex4 terenkripsi), kode tersandi (Minhtan2005), strategi
yang aturannya privat (EA_SCALPER), bot berbasis LLM (hasilnya berubah-ubah), model AI tanpa dilatih ulang, dan
kinerja live siapa pun.

Temuan yang baru ketahuan setelah pemeriksaan sampai ke akar (termasuk riwayat git lengkap, `docs/AUDIT_RIWAYAT_RELEASES.md`):
- **EA_SCALPER**: branch `feature/nova-funcionalidade` & commit lama menyimpan ±420 EA bajakan dari kanal Telegram,
  termasuk terminal MT4/MT5 hasil modifikasi, `winmm.dll` "account changer", dan decompiler. Salinan di folder ini
  (versi `main`) bersih dari file tersebut; jangan checkout branch itu.
- **Turnipnator** & **nathanaela2002**: API key/token akses **OANDA** asli pernah ter-commit lalu dihapus (masih ada di riwayat).
- **Mnauu2201** (klaim WR 62,3%, R:R 1:2): backtest penulis memakai candle H4/H1/M15/M5 yang **belum tutup**.
  Ditiru persis: WR 57,3% dan +79R (M5, 17 bulan). Setelah diperbaiki dan spread dihitung: WR 27,6%, −4,2R.
- **codebytemirza** (klaim 65% akurasi di akun real): file kode intinya hanya berisi satu baris, *"Code is removed …
  contact after star this repo"*. Tidak ada kode yang bisa dinilai.
- Rahasia asli milik penulis yang ikut terunggah: API key OpenRouter (EA_SCALPER), password MT5 demo (sensesVoid),
  password MT5 (nazhmi12), password situs (nathanaela2002), token + chat ID Telegram (a1shmuk, samw2591, jlvalaty,
  ImranDev3), API key FRED (a1shmuk). Semuanya sudah **disensor** di salinan ini.

## Peringkat per kategori

### Win-rate tertinggi — klaim penulis

| # | Repo | Klaim | Kenyataan setelah diuji ulang |
|---|---|---|---|
| 1 | sagarmeravi | 72,66% (PF 1,09) | WR 67–74% terulang, tapi rugi setelah spread |
| 2 | Lin-Thet-Zaw *(tidak disalin, biner saja)* | 69,57% | Tidak bisa diuji (tanpa source) |
| 3 | GifariKemal/xaubot-ai | 63,9% (PF 2,64) | Model sejenis: akurasi 51,3% |
| 4 | Mnauu2201 | 62,3% (R:R 1:2) | Look-ahead; diperbaiki: 27,6%, −4,2R |
| 5 | a1shmuk | 61,4% (PF 2,48) | Look-ahead; diperbaiki: 31–36%, −51R |
| 6 | samw2591 (ORB) | 61% | 42–51%, −68R (positif 2022–26) |
| 7 | ilahuerta-IA | 55,4% (PF 1,64) | Positif hanya di data optimasinya |
| — | thanvish21 / Turnipnator / shamshyder / triqbit | 80% / 55–65% / 55–65% / 60–65% | Hanya **target**, bukan hasil |

### Win-rate tertinggi — terukur di data asli + spread

| # | Repo | Win-rate | Hasil |
|---|---|---|---|
| 1 | BlamzKunG (grid mean-reversion) | 92–96% | −224,7R, rugi di 4/4 periode |
| 2 | phatnomenal (retest high kemarin) | 57–76% | −95,3R |
| 3 | sagarmeravi (SMA pullback) | 67–74% | −24% harga |
| 4 | samw2591 Keltner "live" | 54–67% | −143R |
| 5 | samw2591 RSI(2) M15 | 54–65% | −190,5R |

### Profit tertinggi — terukur (4 periode 2012–2026)

| # | Repo / strategi | Total | Periode positif |
|---|---|---|---|
| 1 | samw2591 Keltner sederhana (SL 4,5 / TP 8 ATR) | **+33,4R** | 3/4 |
| 2 | samw2591 ORB New York | −68,1R (tapi +51,3R di 2022–26) | 2/4 |
| 3 | Aniket EMA 13/34 + RSI H4 | −2,7R | 2/4 |
| — | *Pembanding: Donchian H1 bot ini (1 set)* | *+123,7R* | *4/4* |

### Scalping
RobertN1D (EA MQL5 4.600 baris, paling lengkap), 3aLaee (MACD M1, diuji: −0,39R/trade), Takura-Z (XGBoost M1 via
ONNX), AnggaKay (XGBoost ganda), nazhmi12 (FVG+OB M5), P1Piyush (HFT/PDH), Mnauu2201 (trigger M1).

### Fitur / sistem terlengkap
GifariKemal (ML + SMC + HMM + dashboard + Telegram), triqbit (arsitektur ML/DRL, MetaApi), EA_SCALPER (engineering
EA, safety gates), samw2591 (riset & validasi paling serius), Turnipnator (bot Oanda live dengan test), P1Piyush (web
+ EA + ML).

### Desain paling aman
sensesVoid (order hanya setelah Anda menyetujui), Turnipnator (SL dikirim bersama order), EA MQL (tidak menyimpan
password: BlamzKunG, phatnomenal, RobertN1D, shamshyder, AnggaKay, Takura-Z, armza332).

### Login MT5 — yang perlu diperhatikan
- Aman: EA MQL (jalan di terminal), atau `.env` (GifariKemal, triqbit, 3aLaee, Mnauu2201, sensesVoid, HillaryMurimi).
- Menulis password di file kode (jangan diisi lalu di-commit): Aniket (`config.py`), nazhmi12, pipela, damaradam04.
- Memakai terminal yang sudah login tanpa password di kode: a1shmuk, ImranDev3.

## Tidak disimpan

| Repo | Alasan |
|---|---|
| 0xagarg/xau-ai-trading-bot, BizShibe/XAUUSD-ai-trading-bot | Salinan identik GifariKemal/xaubot-ai |
| jlvalaty/gold-quant-trading | Salinan sebagian samw2591 (token Telegram sama) |
| Minhtan2005/… | 🛑 Kode tersandi PyArmor + DLL, jualan "PRO" — **jangan dijalankan**, tidak ada di `ambil.sh` |
| Lin-Thet-Zaw/xauusd5mTimeFrameAndDailyTFrame | Hanya 7 EA terkompilasi. ⚠️ Riwayat git-nya berisi 22 arsip EA komersial bocoran/"fix" (MM FLIP AI, Dominant, Goldex, ORION…) — lihat `docs/AUDIT_RIWAYAT_RELEASES.md` §3.2. Jangan dipakai |
| codebytemirza/XAUUSD_TRADING_ASISTENT_AI | Kode inti dihapus penulis |
| iamvishalvasava, kaleemullahkhan786, haseebjaan610, HisyamAlammar, tolgahan38, iiah656 | Tanpa kode: jualan / iklan / referral / rumus saja |
| kalpeshsinghal0055-ai, t54983200 | Situs pemasaran EA & afiliasi; backend layanan berbayar |
| metalpriceapi, Ming-jx, Askhat707, angelolockdev | Library / UI, bukan strategi |
| Likando21, cryptocoin81, eddiehng7, tensecrocodile | Kosong |

## Yang diubah dari aslinya (semua dicatat di `ASAL.md`)

1. Kredensial asli penulis diganti `ISI_…_SENDIRI` / `GANTI_…`.
2. Tidak disalin: file biner (.ex5/.ex4/.exe/.dll/.pyd), model pickle (.pkl/.zip SB3/.h5/.pt) yang bisa menjalankan
   kode saat dimuat, arsip, `.env`, data > 500 KB, pustaka standar MetaQuotes (sudah ada di setiap MT5), presentasi.
3. File instruksi asisten AI penulis (CLAUDE.md, AGENTS.md, GEMINI.md, `.claude/`, `.cursor/`, `.cursorrules`) diberi
   akhiran `.asli` / `_asli` supaya tidak ikut aktif saat Anda memakai asisten AI di repo ini.
4. `RobertN1D/GOLD EA HIGH FREQUENCY GOLD SCRAPER FOR MT5` (tanpa ekstensi) → `GOLD-HFT-SCALPER.mq5`.

Repo asli yang lengkap (termasuk data & biner): `bash kandidat/ambil.sh [kata_kunci]` → `kandidat/_asli/` (tidak
ikut ter-commit).

## Cara membandingkan sendiri

```bash
bash research/download_data.sh
python -m research.github_popular        # GOLD_ORB, MACD M1, a1shmuk, pullback window, FVG, ML
python -m research.github_popular2       # Aniket, Turnipnator, phatnomenal, sagarmeravi, samw2591 (3), BlamzKunG
python -m research.mnauu_confluence      # Mnauu2201: versi penulis vs diperbaiki
python -m research.combine2              # gabungan Keltner + Donchian
python -m research.inventaris_repo kandidat   # inventaris ulang folder ini
python -m xau_bot audit --ringkas kandidat/*/  # keamanan
```

Lisensi: 9 dari 41 kandidat berlisensi MIT, EA_SCALPER memakai PolyForm Noncommercial, sisanya tanpa lisensi (hak
cipta tetap milik penulis). Salinan ini disimpan atas permintaan pemilik repo untuk perbandingan pribadi.
