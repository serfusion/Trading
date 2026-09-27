# Audit A — Riwayat Git Lengkap & GitHub Releases (63 repo)

Tanggal: 27 Sep 2026. Alat: `research/audit_riwayat.py` (aturan sama dengan `xau_bot/audit.py`). Kode repo **tidak
dijalankan**; setiap versi file dibaca sebagai data lewat `git cat-file`.

## 1. Cakupan

| Yang diperiksa | Jumlah |
|---|---|
| Repo (clone `--mirror`: semua branch, tag, dan ref pull request) | 63 (3 kosong: cryptocoin81, eddiehng7, tensecrocodile) |
| Commit | 8.732 |
| Blob (setiap versi setiap file yang pernah ada) | 66.372 |
| Blob di luar versi terakhir (belum tercakup audit awal) | 62.336 |
| Branch / tag / ref PR | 1.275 / 7 / 2.540 (triqbit sendiri: 1.198 branch, 2.523 PR) |
| Arsip .zip/.rar di riwayat yang dibuka daftar isinya (tanpa ekstrak) | 404 |

Batasan: blob > 12 MB hanya dinilai dari namanya (39 blob: 31 di EA_SCALPER, sisanya data CSV); arsip di dalam arsip tidak dibuka;
isi `.ex4/.ex5` tidak bisa dibaca siapa pun tanpa dekompilasi. Kolom `pr_only` di CSV menandai versi yang hanya ada
di pull request (kode kiriman orang lain, bukan pemilik repo).

## 2. GitHub Releases

Rilis GitHub selalu menempel pada sebuah **tag**. Tag hanya ada di 2 repo, sehingga hanya 2 repo yang mungkin punya
rilis:

| Repo | Tag | Rilis | Aset |
|---|---|---|---|
| GifariKemal/xaubot-ai | v0.6.0 | tidak ada rilis | — |
| metalpriceapi/metalpriceapi-nodejs | 6 tag | ada | hanya arsip source otomatis GitHub (tanpa file tambahan) |

Lin-Thet-Zaw sempat dicek khusus (klaim WR 69,57%): tidak ada rilis. triqbit menyimpan dua `releases/*.tar.gz`
di dalam repo (bukan di Releases): isinya hanya dokumen, migrasi, dan `image.tar.gz` kosong.

**Kesimpulan: tidak ada program yang disebar lewat GitHub Releases di 63 repo ini.**

## 3. Temuan yang HANYA ada di riwayat (tidak terlihat di versi terakhir)

### 🛑 3.1 EA_SCALPER — perpustakaan EA bajakan di riwayat

Branch `feature/nova-funcionalidade` (7,1 GB) dan commit lama `main` berisi ±420 file unik berupa EA/indikator
komersial yang dikumpulkan dari kanal Telegram "gratisan" (@FundedMillionAiress, @MetaTerminals,
@LifeInDreamsWorld, @indicatorsmt5mt4, Onshoppie, dll.): 246 zip, 128 rar, 30 ex4/ex5. Dari 404 arsip yang dibuka,
14 berisi program Windows:

| Isi berbahaya | Arsip |
|---|---|
| `terminal.exe` + `metaeditor.exe` MT4 hasil modifikasi | `MT4 1425.zip` (@MetaTerminals) |
| `launcher.exe` + `terminal64.exe` | `Quantum Gold Emperor MT5@LifeInDreamsWorld.zip` |
| `winmm.dll` (pola *DLL hijacking*: dimuat otomatis oleh terminal) | `account_changer_lib_1400_1403.zip` |
| Decompiler ex4→mq4 + `dllexp.exe` | `ex4-to-mq4 decompiler and dll viewer.rar`, `Ex4 to mq4 4.0.509.rar` |
| `FX-Blue-Alert-Forwarder-….exe` | `FX-Blue-Alert-Forwarder-By @FundedMillionAiress.zip` |
| DLL milik EA (`ATS.dll`, `aininet.dll`, `KingPulse FX 2.6.dll`, `Deep+ Scalper Auto update.dll`) | 7 arsip EA |

Terminal/launcher bajakan dan DLL "account changer" adalah jalur malware yang paling umum di dunia EA. **Isi `main`
saat ini dan kedua branch yang diarsipkan (`main`, `codex-review-5a93d374`) TIDAK mengandung satu pun file ini**
(dicek: 0 zip/rar/exe/dll/ex4/ex5). Jangan pernah checkout `feature/nova-funcionalidade`.

Temuan teks lain di riwayat EA_SCALPER (749 WASPADA) seluruhnya berada di perpustakaan EA pihak ketiga itu:
DLL import (272), WebRequest (197), data akun + internet (138), kunci lisensi (42), tautan unduhan (59). Satu
"BAHAYA" `download_exec` = `curl … astral.sh/uv/install.sh | sh` di workflow CI sebuah alat pihak ketiga (installer
resmi `uv`, bukan malware).

### ⚠️ 3.2 Lin-Thet-Zaw (klaim WR 69,57%) — EA komersial bocoran/"fix"

Riwayatnya berisi 22 arsip EA komersial dari kanal "@simpleforextools / FREE TRADING TOOLS - EAS PREMIUM FREE":
MM FLIP AI (7 versi), Dominant EA, Goldex AI, Deep+ Scalper, ORION GOLD SCALPER "LIFETIME PLAN fix", VVIP EA, dll.
Kata "fix" di dunia EA biasanya berarti **kunci lisensinya sudah dibobol**. EA "MM FLIP AI" yang diklaim WR 69,57% =
salah satu EA bocoran ini (hanya `.ex4`, tidak ada source). Satu arsip berisi source MQL5 `stop_hunter_ea`
(StopHunter Pro V5.3–V5.6). Tidak ada `.exe/.dll`, tetapi status hukum & keamanannya tidak jelas → **jangan dipakai**.

### ⚠️ 3.3 Rahasia yang sudah dihapus penulis tapi masih ada di riwayat

Nilainya disensor di laporan ini dan di `docs/riwayat/*.csv`. Semua ini milik penulis repo, bukan milik Anda.

| Repo | Yang bocor di riwayat | Commit |
|---|---|---|
| Turnipnator/Oanda_Gold | **API key OANDA** (akses akun broker) + token & chat ID Telegram di `.env.ma_crossover` | a2724f976c, 2025-11-25 |
| nathanaela2002/Forex-Gold-Miner | **token akses OANDA** + password situs di `.env` | 917f1c6d65, 2025-03-25 |
| Aniket-Jaiswal2002 | password MT5 + token & chat ID Telegram | c7b8566e6f, 2026-05-21 |
| francomascareloai/EA_SCALPER | API key OpenRouter (3 file), token akses ChatGPT (JWT), 2 token bot Telegram di source EA koleksi, 3 file `.env` | beberapa |
| Kiran-Kumbar | token Telegram + API key TwelveData | 46bcd096d1 |
| MarketForgeX | API key TwelveData + Finnhub | 9ad8162bce |
| codebytemirza | API key Groq | 32c7a5560d |
| yogeshkb-yoyo | API key Google AI (Gemini) | 812d83a75d |
| angelolockdev | API key gold-api di `.env` | 9b193efc69 |
| ilahuerta-IA | password MT5 di **pull request** kontributor lain (bukan penulis) | e0634e7e74 |
| damaradam04-cmd, nazhmi12 | baris password MT5 di config versi lama | f5e36558f3, 7ce8ab2023 |
| ImranDev3 | chat ID Telegram | 970fdfac5c |
| kalpeshsinghal0055-ai | token widget situs (publik) | 8ae01e4be5 |
| triqbit | 47 temuan = semuanya nilai palsu di file test (`test…`, `fake…`, `dummy…`) → **bukan bocoran** | — |

Artinya bagi Anda: repo-repo ini tidak disiplin soal rahasia. Kalau memakai kodenya, simpan kredensial Anda
sendiri di `.env` yang di-*gitignore*, jangan di file kode.

### ℹ️ 3.4 File biner lain di riwayat

| Repo | Isi | Penilaian |
|---|---|---|
| P1Piyush | `.venv` Python ikut ter-commit: 6.449 blob, 362 biner (`.so`, `.exe` peluncur pip, `.dylib`) + 219 pola teks di pustaka pip | **Semua 581 file cocok dengan hash `RECORD` pip** → paket asli, tidak disisipi. Plus 17 `.pyc` & 6 `.ex5` build milik penulis |
| sensesVoid | 4 file `.bin` di `strategy_db/` | Indeks vektor ChromaDB (bukan program; tanpa header MZ/ELF) |
| 3aLaee, ImranDev3, wael-slimi | `.pyc` kode sendiri | Bytecode dari file `.py` yang ada; aman tapi tidak perlu |
| Mnauu2201 | 6 zip | Laporan backtest CSV |
| pipela, wael-slimi | zip model PPO (stable-baselines3) | Berisi `.pth` (pickle PyTorch) → memuatnya bisa menjalankan kode |
| triqbit | 2 `releases/*.tar.gz` | Dokumen saja |
| metalpriceapi | PR #1 (bukan kode pemilik, tidak di-merge): server dashboard memanggil `curl` lewat shell dengan URL dari request | Rawan *command injection*; tidak ada di `main` |

### ✅ 3.5 Repo lain

40 repo lainnya (termasuk 3 repo kosong): riwayatnya tidak menambah temuan keamanan di luar yang sudah ada di versi terakhir (lihat
`docs/AUDIT_63_REPO.md`).

## 4. Arsip repo mentah

`arsip_repo/` menyimpan `git bundle` setiap repo (lihat `arsip_repo/README.md`). Karena bundle berisi riwayat
mentah **termasuk rahasia di tabel 3.3**, pengiriman dua bundle terbesar (Lin-Thet-Zaw 28 MB, P1Piyush 54 MB)
diblokir oleh pengaman sesi; keduanya bisa diambil ulang kapan saja dengan `git clone --mirror`. EA_SCALPER hanya
disimpan sebagai cuplikan isi (`…__SNAPSHOT.bundle`, tanpa riwayat & tanpa perpustakaan bajakan di atas).

## 5. File hasil

| File | Isi |
|---|---|
| `docs/riwayat/riwayat_temuan_ringkasan.csv` | 1 baris per repo: branch, tag, ref PR, commit, blob, temuan baru |
| `docs/riwayat/riwayat_temuan.csv` | Temuan teks (BAHAYA/WASPADA/rahasia), dikelompokkan per path; `di_head`, `lokasi` (pustaka pip), `pr_only`, jumlah versi, commit pertama |
| `docs/riwayat/riwayat_temuan_biner.csv` | Setiap file biner/arsip/pickle di riwayat + commit pertama |
| `docs/riwayat/riwayat_arsip.csv` | Isi 404 arsip zip/rar (dibaca dari header saja) |

Ulangi audit:

```bash
git clone --mirror https://github.com/<owner>/<repo> /tmp/mirrors/<owner>__<repo>.git   # untuk setiap repo
python -m research.audit_riwayat /tmp/mirrors --csv /tmp/riwayat_temuan.csv
python -m research.audit_riwayat /tmp/mirrors --csv /tmp/riwayat_temuan.csv --arsip /tmp/riwayat_arsip.csv
```
