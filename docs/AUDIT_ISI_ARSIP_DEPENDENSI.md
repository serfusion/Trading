# Audit A2 — Isi Arsip & Dependensi (63 repo)

Tanggal: 27 Sep 2026. Semua dibaca di memori; **tidak ada file yang diekstrak ke disk, dipasang, atau dijalankan.**
Alat: `research/audit_riwayat.py --isi-arsip` (libarchive), `research/analisa_biner.py` (pefile + openssl),
`research/audit_dependensi.py` (PyPI/npm JSON). Data: `docs/arsip_dependensi/`.

## 1. Isi 404 arsip (zip/rar) di riwayat git

| Repo | Arsip | File di dalamnya | Dipindai (teks) | Program/biner | Terkunci (password) |
|---|---|---|---|---|---|
| francomascareloai/EA_SCALPER | 374 | 9.696 | 8.284 | 495 | 16 |
| Lin-Thet-Zaw | 22 | 191 | 77 | 44 (ex4/ex5) | 23 (`Dominant EA Pro MT5.zip`) |
| Mnauu2201 | 6 | 214 | 20 (sisanya CSV laporan backtest) | 0 | 0 |
| pipela, wael-slimi | 1 + 1 | 6 + 6 | 3 + 3 | 3 + 3 (model PPO/pickle) | 0 |

Total 10.113 file, 8.387 file teks dipindai dengan aturan yang sama dengan audit awal, 545 biner, 37 terkunci,
2 arsip rusak. Seluruh arsip ini **hanya ada di riwayat** (tidak ada di versi terakhir repo mana pun) dan tidak ada di
`kandidat/` maupun bundle EA_SCALPER di `arsip_repo/`.

Temuan teks di dalam arsip (semuanya source EA/indikator bajakan yang dikoleksi): 264 impor DLL, 144 WebRequest,
123 data akun + internet, 70 kunci lisensi, 306 martingale, 238 grid, 15 `ShellExecute`, dan 4 kali pesan
**"Try to whitelist our software in antivirus or disable antivirus"** (EA ATS V4.1).

### 1.1 Program Windows di dalam arsip — analisa statis (`docs/arsip_dependensi/biner_pe.csv`)

14 program unik. SHA256 lengkap ada di CSV — bisa Anda cek sendiri di `https://www.virustotal.com/gui/file/<sha256>`.

| File (arsip) | Tanda tangan | Yang dilakukan (dari fungsi Windows yang diimpor) | Penilaian |
|---|---|---|---|
| `launcher.exe` (Quantum Gold Emperor MT5 @LifeInDreamsWorld) | ❌ tidak ada | Dipadatkan; `VirtualAllocEx` + `WriteProcessMemory` + `CreateProcess` + anti-debug = **pola menyuntikkan kode ke program lain** | 🛑 Sangat berbahaya |
| `winmm.dll` (account_changer_lib) | ❌ | Menyamar sebagai DLL sistem Windows (192 fungsi tiruan), dipadatkan, 7,5 MB; dimuat otomatis oleh terminal bila diletakkan di foldernya | 🛑 Sangat berbahaya (DLL hijacking) |
| `aininet.dll` (Hydrangea EA) | ❌ | Nama meniru `wininet.dll` (library internet Windows); membungkus fungsi HTTP + anti-debug → mencegat/memalsukan koneksi EA (bypass lisensi) | 🛑 Berbahaya |
| `KingPulse FX 2.6_.dll` (22 MB) | ❌ | Dipadatkan; `ShellExecuteEx` + `HttpSendRequest` + menulis registry. Versi "_" = modifikasi dari DLL lisensi asli (MqlLock) | 🛑 Berbahaya |
| `Deep+ Scalper Auto update.dll` | ❌ | Dipadatkan; internet + `send` + `ShellExecute` → bisa mengunduh & menjalankan program | ⚠️ Berbahaya |
| `ex4_to_mq4.exe`, `ex4 to mq4 4.0.509.5.exe`, `dllexp.exe` | ❌ | Decompiler EA 2009–2014, dipadatkan | ⚠️ Alat bajakan, tidak terverifikasi |
| `ATS.dll` | ❌ | Menghubungi `atsadmin.infosystrade.com:5003/api/checkatsuser` (server lisensi vendor) | ⚠️ Mengirim data ke vendor |
| `KingPulse FX 2.6.dll` (asli) | ❌ | 1.192 fungsi `MqlLock_*` (proteksi lisensi komersial) | ⚠️ |
| `terminal.exe`, `metaeditor.exe` (MT4 1425 @MetaTerminals), `terminal64.exe` (Quantum Gold) | ✅ MetaQuotes Ltd | Hash Authenticode **cocok** → file asli MetaQuotes, tidak diubah | ✅ Asli, tapi dibundel bersama loader/DLL di atas |
| `FX-Blue-Alert-Forwarder….exe` | ✅ FXBlue LLP | Hash cocok, file asli FX Blue | ✅ Asli (disebar ulang lewat kanal Telegram) |

Artinya: terminal MT4/MT5 di paket "crack" itu memang asli, tetapi **yang berbahaya adalah pemuat (`launcher.exe`) dan DLL
palsu yang ikut dibundel** — itulah yang membuka kunci EA bajakan, dan program dengan pola seperti itu bebas melakukan
apa saja di komputer (termasuk membaca password akun di terminal). Verifikasi tanda tangan hanya mencocokkan hash
dengan tanda tangan yang tertanam; rantai sertifikat tidak diuji terhadap root store Windows.

### 1.2 Ke mana EA di dalam arsip mengirim data (`docs/arsip_dependensi/mql_url.csv`)

44 source EA di dalam arsip memakai internet. Tujuannya: server lisensi vendor (chefsgoldea.com, clevrfx.com,
wallstreet-forex.com, omega-trend.com, purebeam.biz, pimpmyea.com, fxphantom.com, leapfx.com, …) dan kalender berita
(ForexFactory, Investing/forexprostools). 23 di antaranya memakai **data akun** (nomor/nama/server/saldo) di file yang sama dengan kode internet, umumnya dikirim ke server vendor (cek lisensi).
Tidak ada yang mengirim ke domain penampung data curian yang dikenal (webhook Discord, pastebin, requestbin, ngrok).

## 2. Dependensi (`requirements.txt`, `package.json`, `pyproject.toml`)

| Cakupan | Hasil |
|---|---|
| Versi terakhir: 44 file manifest, 28 repo, 860 baris, **286 paket unik** | Semua paket **ada** di PyPI/npm; tidak ada instalasi dari git/URL/folder lokal; tidak ada skrip npm `preinstall/postinstall`; satu-satunya index tambahan = PyTorch resmi (`download.pytorch.org/whl/cpu`, triqbit) |
| Riwayat: 2.953 versi file manifest, **459 paket unik** | Semua ada, kecuali `python>=3.11` yang salah ditulis sebagai paket (EA_SCALPER) |

Yang ditandai & sudah diperiksa manual:

| Paket | Repo | Penilaian |
|---|---|---|
| `https` (npm, 1 rilis 2015) | t54983200 | Isinya hanya `package.json` (kosong). Tidak berbahaya; Node selalu memakai modul `https` bawaan |
| `pandas-ta` (PyPI kini hanya 0.4.67b0/0.4.71b0, Sep 2025) | triqbit | Masih milik penulis asli (twopirllc, pandas-ta.dev); versi 0.3.14b yang dipatok repo sudah ditarik → `pip install` gagal, bukan pengambilalihan nama |
| `pandas-ta-classic` | triqbit (riwayat) | Fork komunitas (xgboosted), wajar |
| `tickerall` (dibuat 2 Jun 2026) | triqbit (riwayat, sudah dihapus) | SDK layanan "hosted MetaTrader API" → bila dipakai, login MT5 dikirim ke tickerall.com |
| `cuda-toolkit`, `cuda-pathfinder` | triqbit (riwayat) | Paket resmi NVIDIA |
| `vite-plugin-manus-runtime`, `streamdown`, `@builder.io/vite-plugin-jsx-loc` | kalpeshsinghal0055-ai | Paket pembuat situs (Manus, Vercel, Builder.io); tanpa skrip instalasi |
| versi `torch …+cpu`, `numpy 2.2.7`, `ccxt 4.0.0`, dll. "tidak pernah dirilis" | triqbit, blackhunter | Build PyTorch dari index resminya / salah ketik versi → hanya gagal install |

**Kesimpulan dependensi:** tidak ditemukan paket palsu, typosquatting, atau dependency confusion.

## 3. Kesimpulan A2

- Kode di versi terakhir ke-63 repo dan dependensinya tetap bersih dari malware.
- **Bahaya terbesar ada di riwayat EA_SCALPER** (branch `feature/nova-funcionalidade` dan commit lama): paket EA bajakan
  yang membawa loader injeksi kode, DLL palsu `winmm.dll`/`aininet.dll`, dan DLL "auto update" yang bisa mengunduh
  program. Jangan pernah mengambil apa pun dari riwayat repo itu.
- 37 file berpassword (Lin-Thet-Zaw `Dominant EA Pro MT5.zip`, EA_SCALPER) tidak bisa diperiksa isinya.

Ulangi:

```bash
pip install libarchive-c pefile
python -m research.audit_riwayat <mirrors> --csv docs/riwayat/riwayat_temuan.csv --isi-arsip isi.csv
python -m research.analisa_biner <mirrors> docs/riwayat/riwayat_temuan_biner.csv --csv pe.csv --mql-url mql.csv
python -m research.audit_dependensi <folder-repo> --csv dep.csv
python -m research.audit_dependensi <mirrors> --riwayat --csv dep_riwayat.csv
```
