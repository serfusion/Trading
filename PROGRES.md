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
| D2 | Fork & wiki dari 63 repo | ✅ selesai: 0 wiki; 372 fork (342 identik, 30 berubah → isi barunya dipindai) | `docs/AUDIT_FORK_WIKI.md`, `docs/fork/` |
| B2 | Strategi yang belum diuji: EA GifariKemal, EA EA_SCALPER, sisa samw2591, AnggaKay, damaradam04, nathanaela2002 | ✅ selesai: 6 strategi diuji, 5 dicatat tak bisa diuji (alasan dari kode) | `research/github_popular4.py`, `docs/AUDIT_63_REPO.md` §3.3, `docs/hasil_github_popular4.txt` |
| C2 | Baca manual file inti 41 kandidat | ✅ selesai: 298 file inti / 243.552 baris (18 repo dibaca penuh, 7 campuran, 16 per titik aksi) + sapuan 93 file uji/backtest | `docs/TINJAUAN_MANUAL.md`, `docs/tinjauan_manual/file_inti.csv` |

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

## Riset data eksternal (permintaan pengguna 28 Sep 2026: "lanjutkan riset data eksternal")

Tujuan: apakah data luar grafik bisa menyaring sinyal 💰 cloud. Laporan: `docs/RISET_DATA_EKSTERNAL.md`, keluaran
`docs/eksternal/`. Kriteria "konsisten" ditetapkan sebelum melihat hasil (`research/eksternal.py`).

| # | Data | Status | Hasil |
|---|---|---|---|
| 1 | Kalender berita NFP/CPI/FOMC (FF + FRED) | ✅ | tidak ada yang konsisten di XAU 💰; BTC "≤2 jam sebelum berita" lolos di atas kertas tapi 0 efek di uji nyata |
| 2 | Yield riil DFII10 & dolar DTWEXBGS (FRED, vintage ALFRED) | ✅ | tidak konsisten; varian terbaik latih gagal di uji (overfitting) |
| 3 | COT CFTC emas & bitcoin | ✅ | tidak konsisten di 💰; "ikut ramai P90" konsisten hanya di SEMUA sinyal XAU (membuang sinyal biasa) |
| 4 | Sesi + BID/ASK Dukascopy H1 | ✅ | statistik 💰 terulang di data Dukascopy; spread nyata hanya −2,4%; spread 22–23 UTC 2–3× lebih lebar; filter sesi tidak konsisten |
| 5 | Funding/OI BTC (data.binance.vision) | ✅ | **funding "hindari ramai P90" konsisten** di BTC 💰 (tahan 27/27 parameter, data terlambat 24–48 jam, proxy premium index harian): uji nyata 2021–26 +171R → +214R → usulan, menunggu izin; OI tidak berguna; L/S bukti tipis |

| 6 | Putaran 2: GVZ, VIX, yield 2 th (proksi FedWatch), breakeven, musiman | ✅ | **BTC 💰 "lewati September" konsisten** (11/11 tahun); XAU tidak ada (GVZ naik → info di chat) |
| 7 | Pasang (permintaan pengguna "pasang semua") | ✅ live | filter BTC funding + September di cloud; tab **Tanya** berbasis data tanpa AI (`POST /api/chat`); aplikasi 2.9–3.0; PR serfusion/Trading#13 di-merge 28 Sep 07:21 UTC |
| 8 | Laporan pengguna "hari ini minus gede" (28 Sep) | ✅ | rekonstruksi dari data Yahoo (GC=F, BTC-USD): emas −$135 (−3,1%) sejak Jumat, BTC −2%; tidak ada sinyal XAU 💰 terbuka; BTC BUY 27 Sep kena SL 05:02 WIB (masuk "Hari ini"). Tidak ditemukan bug hitungan; aplikasi 3.2: floating dalam uang, rincian per pair, pair diikuti, alarm tepat waktu, blok 🎯 REKOMENDASI ENTRY di Tanya |

Catatan: `data_mt5/` (ekspor MT5 Exness pengguna) belum diunggah; `TWELVEDATA_API_KEY` sudah diperbarui pengguna tetapi
sesi ini masih membaca nilai lama (401) → jalankan `python -m research.eksternal_twelvedata` di sesi baru.

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
- 2026-09-27: D2 selesai. Tidak ada malware di fork; beberapa fork membocorkan password MT5 pemiliknya; fork Silentwolf360 berisi source .mq5 EA P1Piyush.
- 2026-09-27: B2 selesai. Terbaik baru: samw2591 MACD +21,9R & gap Senin +10,9R (keduanya dimatikan penulis, 2/4 periode). XAUBot V3 berhenti permanen (bug canTrade); SmartPropAI = TP acak.
- 2026-09-27: C2 selesai. Temuan baru terpenting:
  - EA_SCALPER `install_trading_mcps.ps1` memasang 15 paket npm `@trading-mcps/*` yang tidak ada (slopsquatting — jangan dijalankan);
  - EA_SCALPER `windows_setup.ps1` menambah pengecualian Windows Defender;
  - Pestador: server tanpa login bisa disuruh membuka URL & menulis file;
  - GifariKemal: API dasbor tanpa login bisa mematikan filter bot live;
  - armza332: jembatan menerima `close_all` tanpa secret;
  - order tanpa SL di BlamzKunG (semua order), AnggaKay & GifariKemal (retry tanpa SL);
  - lot 10× kebesaran di HillaryMurimi;
  - pipela memperlebar SL setelah entry.

  Bot kita dicek: tidak punya pola-pola itu. **Putaran 2 (A2, B2, C2, D2) selesai.**
- 2026-09-28: riset data eksternal dimulai. Akses jaringan & FRED_API_KEY OK. Tahap 1–3 (berita, FRED, COT) selesai:
  tidak ada filter konsisten untuk sinyal 💰 XAU. Kerangka + tes: `research/eksternal.py`, `tests/test_eksternal.py`.
- 2026-09-28: tahap 5 selesai: funding BTC lolos (usulan). File funding Binance hanya bulanan → funding direkonstruksi
  dari premiumIndexKlines harian (tetap konsisten). Menunggu unduhan Dukascopy untuk tahap 4b.
- 2026-09-28: pengguna minta "pasang semua" + cari info sebanyak-banyaknya + kotak chat. Putaran 2 selesai (BTC
  September lolos). Basis pengetahuan berita `cloud/api/pengetahuan.md` (`research/event_stats.py`), chat
  (`cloud/api/_chat.py`, `chat.py`, tab Tanya di aplikasi 2.7), filter BTC (`cloud/api/_funding.py`) terpasang di
  branch; 47 tes cloud lulus.
- 2026-09-28: pengguna: chat "tidak usah pakai AI, hanya analisa berdasarkan data" → `_chat.py` ditulis ulang
  (kata kunci + `pengetahuan.json`), dependensi anthropic dihapus. Riset SL+ bertangga/0,7R: pertahankan bawaan.
  Aplikasi 2.8 (ikon, skema tetap, level TUTUP) & 2.9 (teks Tanya). PR serfusion/Trading#13 dibuka.
- 2026-09-28: pengguna minta isian "Act: Cons: Prev:" + scanning menyeluruh → kalender historis kini memuat Previous
  (`research/news_data.py`), `pengetahuan.json` + persentil besar kejutan & gabungan Act vs Prev; `_chat.py`
  memindai format ForexFactory (banyak baris); `GET /api/chat` = kalender minggu ini; aplikasi 3.0 kartu 📝.
- 2026-09-29/30: riset momen entry & mode perang (`docs/MOMEN_PERANG.md`, `docs/REKOMENDASI.md`), ⚡ peringkat, label
  ⚠️ mode perang + cadangan USO, aplikasi 3.10–3.11 → di main lewat PR serfusion/Trading#24 & serfusion/Trading#25.
- 2026-09-30: ditemukan 2 commit 🎯 Persiapan berita (aplikasi 3.12, `cloud/api/_persiapan.py`,
  `docs/PERSIAPAN_BERITA.md`) yang di-push ke `claude/gallant-cannon-93b6rp` 47 menit SETELAH PR #25 di-merge, jadi
  tidak ikut ke main walau deskripsi PR #25 menyebutnya. Digabung ke `claude/confident-keller-lj25i3` tanpa konflik;
  165 tes lulus; APK 3.12 sudah lulus build CI (run 57). Menunggu merge ke main.
- 2026-09-30: permintaan pengguna "detik pertama setelah news" → `research/news_detik.py` (tick Dukascopy XAU & 1 detik
  BTC, 516 varian: ikut kejutan / ikut-lawan lonjakan / pending Buy-Sell Stop; aturan pengguna "tutup menit 1–5 bila
  profit, maks 15 menit"), laporan `docs/NEWS_DETIK.md`, aplikasi 3.13 (pengingat ⏱️ 1 menit sebelum rilis, baris ⏱️
  di kartu 🎯, jawaban Tanya). Hasil: keunggulan hanya untuk yang tahu angka Act ≤ 1 detik; cara manual ±0 / rugi.
- 2026-09-30: pengguna minta semua berita bintang 3 (PPI, ADP, GDP, PCE, dll.) → daftar rilis diperluas (4 tier);
  unduhan tick bertahap (lihat CLAUDE.md "Detik pertama"). Status unduhan per tier dicatat di `docs/NEWS_DETIK.md`.
- 2026-09-30: pengguna minta data unduhan disimpan di repo → `data/` (±300 MB, `data/README.md`).
- 2026-09-30: Trading Alchemist (Rizki Aditama) → `docs/TRADING_ALCHEMIST.md`: Momentum Candle rugi (48 varian);
  validasi H4 EMA50 untuk 💰 XAU lolos kriteria → dipasang di cloud (env XAU_H4_FILTER).
- 2026-09-30: arsip GitHub gagal karena `ARSIP_REPO` di Vercel berisi token (token ikut tampil di aplikasi) →
  `_arsip.py` mengabaikan ARSIP_REPO/ARSIP_BRANCH yang salah bentuk, memeriksa format GITHUB_TOKEN, dan menyensor
  semua teks mirip token (`redact`). Pengguna diminta mencabut token lama. Aplikasi 3.15: persen berita besar
  ("75% NAIK 🟢") + bukti "teruji 2012–2025 (n rilis)", kata "menang" diganti "untung di X% rilis".
- 2026-09-30: pengguna ingin entry 1 detik sebelum rilis dan tutup 1–3 detik → `research/news_pra.py`,
  `docs/NEWS_PRA.md`: tebakan kejutan harus benar ≥ 72–95% (tersedia ≤ 61–67%, hanya CPI); 16 petunjuk, 0 lolos.
- 2026-09-30: lanjutan (tutup 1 dtk–3 menit, semua cara) → `research/news_pra2.py`, `docs/NEWS_PRA2.md`: 11.116
  kombinasi, 0 lolos di kedua feed; straddle ±$1–2 hanya positif di tick Exness → saran uji maju lot minimum.
- 2026-09-30: pengguna membuka host Kalshi/Polymarket → `research/kalshi.py` (unduh 2021–2026) & `kalshi_uji.py`,
  `docs/KALSHI.md`: tebakan kejutan CPI 76–78%; sinyal emas CPI ≥ 60% n 18 (positif di kedua feed, t < 2 → kandidat);
  aplikasi 3.16 baris 🎲 Kalshi di kartu 🎯 (`cloud/api/_kalshi.py`).
- 2026-10-01: Act kalender kosong (CSV FRED tidak menjawab dari Vercel) → `_aktual.py` BLS/FRED API/CSV + Supabase;
  perkiraan hari H hidup (Kalshi+Polymarket × reaksi 1 menit) + hasil setelah Act; Polymarket diuji (NFP 41%, Fed
  9/9 sesuai konsensus); astrologi diuji (0 signifikan). Aplikasi 3.17. Laporan `docs/HARI_H.md`.
- 2026-10-02: "sinyal 💰 hanya beberapa jam / setelah turun separuh pasti ke SL?" → `research/potong_rugi.py`,
  `docs/POTONG_RUGI.md`: 58% memang ke SL, tetapi menahan tetap lebih baik (−0,30/−0,41R vs −0,5R); potong & batas
  waktu tidak lolos; skema bawaan tetap.
- 2026-10-02: "tuliskan hasil & persentase arah 1 detik setelah rilis di APK" → `research/reaksi_menit.py` + 1/2/3 dtk
  (Dukascopy + Exness), `docs/HARI_H.md` bagian 6: detik pertama NFP/CPI/PPI belum bergerak (±$0,17, 50:50), hentakan
  di detik 1→2, searah hasil 82–91% di detik 2–3. Aplikasi 3.18: sel 1 dtk / 2 dtk / 3 dtk / 1 mnt di kartu 🎯 (⚡ & ✅),
  Act dicek tiap 30 detik di 10 menit pertama.
- 2026-10-02: Act manual (3.19) + revisi otomatis & besar kejutan (3.20). "Sinyal berita beberapa menit, WR tinggi?" →
  `research/news_menit.py`, `docs/NEWS_MENIT.md`: 2.280 kombinasi, 0 lolos; ikut kejutan setelah menit 1 rugi.
- 2026-10-02: sinyal lebih sering → `research/sinyal_lapis.py`, `sinyal_berita.py`, `docs/SINYAL_LAPIS.md`: DIPASANG
  lapisan (XAU setelah TP1, BTC breakout baru maks 2/set, lot ½) + tanda 📰 sinyal setelah berita; aplikasi 3.21.
