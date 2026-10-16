# 🧭 Arsitektur repo & cara menambah metode baru (16 Okt 2026)

Dokumen ini membedah kode yang **benar-benar dipakai sekarang**: bot lokal, cloud (Vercel + Supabase), aplikasi Android, dan riset.
Bagian terakhir adalah resep langkah demi langkah untuk menambah metode baru tanpa merusak yang sudah ada.

## 1. Peta besar

```
                   ┌──────────────── research/ (Python + pandas, hanya di laptop/sesi) ────────────────┐
 data/research/ ──►│ uji strategi & berita → tick Exness/Dukascopy, candle, FRED, Kalshi, FF kalender  │
 (data unduhan)    │ hasil = angka teruji → ditulis ke cloud/api/*.json  (+ laporan docs/*.md)          │
                   └───────────────────────────────┬────────────────────────────────────────────────────┘
                                                   │ file JSON ikut di-deploy
 Supabase pg_cron ──► GET /api/tick  (tick.py) ────┼──► _core.tick per aset → sinyal 💰 / 🌊 / 🔗 / 💎 / gap
   (tiap jam :02)                                  │       state di Supabase (tabel xau_state, 1 baris per aset)
                                                   │       notifikasi → ntfy (topik pengguna)
 Aplikasi Android ──► GET /api/chat  (chat.py) ────┴──► kalender berita + kartu 🎯 + baris di bawah XAU (pra_satu)
   (tiap 20–60 dtk)   GET /api/control, /api/ikuti, /api/topic
        ▲                                              │
        └──── ntfy stream (sinyal masuk instan) ◄──────┘
 MetaTrader 5 (opsional) ◄── xau_bot/ (bot lokal Windows) atau MetaApi dari cloud (auto order, default MATI)
```

| Folder | Isi | Jalan di mana |
|---|---|---|
| `xau_bot/` | bot lokal MT5: `engine.py` (loop 24 jam), `trend_ensemble.py` (skema F), `broker/mt5.py`, `risk.py`, `news.py` | PC Windows (`start_bot.bat`) |
| `cloud/api/` | 39 modul Python **tanpa dependensi luar** + 30 file JSON hasil riset | Vercel (`maxDuration` 60 dtk) |
| `android/app/.../xausignal/app/` | 22 file Kotlin Compose | HP pengguna |
| `research/` | ±233 skrip uji (backtest, berita, kripto, copy trade, …) | sesi riset |
| `tests/` | 60 file pytest (cloud, bot, riset) — `python -m pytest -q` | sesi riset & sebelum push |
| `ea/` | EA MQL5 terpisah (grid/piramida, belum dipakai bot) | MetaEditor pengguna |
| `.github/workflows/` | `android.yml` (build APK → Release `android-latest`), `arsip_data.yml` (tiap jam), `copytrader.yml` | GitHub Actions |
| `kandidat/`, `arsip_repo/` | kode pihak ketiga yang **tidak dipercaya** — hanya dibaca sebagai data | — |

Produksi Vercel = branch `claude/bold-davinci-ykgq8j`. Alur rilis: branch kerja → PR ke `main` → merge → merge `main` ke
bold-davinci.

## 2. Mesin sinyal 💰 (`cloud/api/_core.py`, dipanggil `tick.py`)

**Algoritma "skema F-ensemble":**
- **Pemicu:** 3 set Donchian H1 (entry/exit 40/15, 55/20, 80/30).
  - BUY bila close H1 > high N bar sebelumnya; SELL kebalikannya (`evaluate()`, hanya bar tertutup).
- **SL:** 3 × ATR(20).
- **Posisi:** tiap sinyal = 5 posisi. Posisi #1 TP1 = **0,7R** (`CFG["tp1_r"]`); setelah TP1, sisa posisi SL dipindah ke entry
  (SL+).
- **Keluar:** TUTUP bila close menembus channel exit.
- **Label & kategori:**
  - ⭐ `star_check` (tren D1 EMA50 + tembus H4 20);
  - `konf_check`;
  - peringkat ⚡/🥈/🥉 `tier()` + `vol_pct`;
  - kategori 💰 = kategori yang dikirim (`category()` / `STATS`).
- **Filter yang aktif:**
  - `h4_ema_check` (XAU);
  - jeda 60 jam sebelum NFP/CPI/Fed (`_jeda_berita.py`);
  - funding & September (BTC, `_funding.py`);
  - batal saat guncangan ≥ 4 ATR (`guncangan`);
  - jam pasar XAU.
- **Lapisan:** sinyal tambahan lot ½ (`layer_ok`, `sinyal_lapis.json`).

**Satu putaran `_core.tick(now, prices, store, pub, cfg, symbol, …)`** untuk XAU, BTC, ETH, DOGE, ADA:
1. Ambil candle (Twelve Data / Binance).
2. Kelola posisi terbuka: TP1, SL+, SL, tutup, batal.
3. Cari sinyal baru per set.
4. Simpan state ke Supabase (`RowStore`).
5. Kirim event ke ntfy.

Modul sinyal lain di `tick.py`:

| Modul | Sinyal |
|---|---|
| `_arus.py` | 🌊 ikut arus setelah lonjakan |
| `_pulih.py` | 🔗 emas pulih → keranjang kripto |
| `_spot.py` | 💎 spot dip |
| `_gap.py` | gap forex |
| `_rekam.py` | rekam hasil berita tiap jam (bukan sinyal) |

## 3. Pipa berita (`chat.py` → GET `/api/chat`)

Satu GET membangun `persiapan` (kartu 🎯, daftar, dan baris di bawah XAU `pra_satu`) dengan urutan **tetap**. Urutan penting,
karena modul belakang membaca hasil modul depan:

| # | Langkah | Modul | Yang ditambahkan |
|---|---|---|---|
| 0 | Supabase dibaca sekaligus | `chat.MemoStore` | ±24 baris dalam 1 permintaan |
| 1 | Tren indikator (cache 3 jam) | `_tren` | `tren` |
| 2 | Kalender ForexFactory pekan ini (cache 10 mnt) | `_arsip.calendar_cached` | `rows` |
| 3 | Kartu berita | `_persiapan.cards` | `persiapan.berita[]` |
| 4 | Peluang pasar | `_kalshi.attach` | `kartu.kalshi` |
| 5 | Act resmi (BLS → FRED → Nasdaq) | `_aktual.fill` | `calendar[].actual` |
| 6 | Arah setelah Act + satu arah per rilis bersamaan | `_persiapan.kesimpulan/satukan` | `calendar[].arah` |
| 7 | Hari H / hasil + Fed (Polymarket) | `_hari_h.attach` | `kartu.hari_h/hasil_rilis`, `persiapan.fed` |
| 8 | Jadwal setelah pekan ini | `_jadwal.attach` | `persiapan.mendatang[]` |
| 9 | 🎲 sebaran Kalshi, 🗣️ pernyataan Fed/Trump | `_kalshi.mendatang`, `_pernyataan` | info (dilewati bila GET > 20 dtk) |
| 10 | Model sebelum rilis NFP/JOLTS/Fed | `_prarilis` | `kartu.prarilis` |
| 11 | Petunjuk teruji per berita | `_petunjuk` | `kartu.petunjuk_teruji` |
| 12 | Baris "NFP: peluang emas …" | `_prediksi` | `kartu.prediksi` |
| 13 | CPI detik 2 (indeks/Kalshi, saringan) | `_cpi_detik` | `kartu.cpi_detik` |
| 14 | PPI (minyak WTI + CPI inti) | `_ppi_wti` | `kartu.ppi_wti` |
| 15 | 👥 sentimen (info) | `_sentimen` | `persiapan.sentimen` |
| 16 | **Arah XAU per detik** | `_pra_aset.attach` | `persiapan.pra`, `pra_daftar`, **`pra_satu`** |
| 17 | 🔗 keterkaitan antar berita | `_keterkaitan` | poin 🔗 |
| 18 | Cadangan baris XAU | `_pra_aset.cadangan` | `pra_satu` ≈ 50% bila galat |
| 19 | 📍 gaya masuk t−1 | `_masuk_pra` | `pra_satu.t1`, `lanjut.posisi` |
| 20 | 🎯 persen sebelum rilis berita tanpa arah | `_pra_peluang` | `pra_satu.teks` "▼ TURUN 51%" |
| 21 | 📉 lonjakan memudar, arsip GitHub | `_pudar`, `_arsip.save` | info |

Setiap langkah dibungkus `try/except`, jadi satu modul gagal tidak menjatuhkan GET. Aturannya sama di semua modul:
`aktif()` membaca env (mis. `MASUK_PRA=0` mematikan), `attach(persiapan, …)` menambah field, dan angka diambil dari JSON hasil
riset.

**Kontrak `pra_satu`** (dibaca aplikasi `StatusCard.kt`):

| Field | Isi |
|---|---|
| `title`, `nama`, `time`, `sisa` | identitas & jadwal rilis |
| `arah` | `"naik"` / `"turun"` / `null` |
| `persen`, `status` | angka & status (teruji / belum terbukti / lemah / acak) |
| `teks` | baris utama, format "▲ NAIK X%" atau "▼ TURUN X%" agar diwarnai hijau/merah |
| `poin[]`, `bukti` | detail saat diketuk |
| `per_detik` | kurva persen per detik |
| `lanjut{kurva, kurva_searah, kurva_lawan, tingkat, posisi}` | data ⚡LIVE |
| `t1` | 📍 masuk t−1 |
| `allin` | 💥 CPI modal kecil |
| `peluang` | 🎯 persen dasar |

## 4. Aplikasi Android (`android/app/src/main/java/com/xausignal/app/`)

| File | Peran |
|---|---|
| `MainActivity.kt` | layar & navigasi bawah, pengaturan, `refresh()` saat dibuka |
| `SignalRepository.kt` | state global (sinyal, harga, uang, pengaturan) + `init` (memanggil `NewsCache.init`) |
| `SignalPoller.kt`, `Notifications.kt`, `CopyStream.kt` | ambil sinyal (ntfy) di latar, notifikasi |
| `NewsCache.kt` | respons GET `/api/chat` terakhir disimpan di HP, satu permintaan bersama |
| `ChatScreen.kt` | tab News/Tanya + `ChatClient` (semua HTTP ke cloud) |
| `StatusCard.kt` | `MarketStrip` (tile XAU·BTC·ETH) + **StripPra** (baris di bawah XAU) + **StripLangsung** (⚡LIVE T−15 mnt…+10 mnt, 📍 tahan/tutup) |
| `LiveGold.kt` | harga emas LIVE tiap ±0,5 dtk (XAUT OKX → KuCoin → Bitget → Gate) |
| `SignalScreen.kt`, `StatsScreen.kt`, `RankCard.kt` | kartu sinyal 💰, statistik, ⓘ peringkat |
| `ArusCard.kt`, `PulihCard.kt`, `SpotCard.kt`, `CopyTraderCard.kt`, `CopyDetail.kt`, `CopyFollow.kt` | kartu sinyal lain & copy trader |
| `NewsAlarm.kt` | pengingat ⏱️ sebelum rilis |
| `Theme.kt`, `Appearance.kt` | tampilan |

Aplikasi **hanya menampilkan**. Hampir semua logika ada di cloud, jadi banyak perbaikan cukup di cloud tanpa APK baru.

## 5. Riset (`research/`)

Polanya selalu sama:

1. **Data:** tick Exness/Dukascopy (`news_detik.prepare`, `exness.ticks_around`), candle (`harness.periods`, `data.py`),
   kalender (`news_detik.events`, FF), FRED/ALFRED, Kalshi, Nasdaq. Semua tersimpan di `data/research/eksternal/`.
2. **Aturan ditulis ulang, tanpa look-ahead:** fitur ≤ t0 − 1 dtk, harga masuk = ask/bid asli, SL dicek lebih dulu
   (`harness.simulate`).
3. **Uji jujur:**
   - pilih aturan di **LAMA** (< Okt 2021), nilai di **BARU**;
   - walk-forward per tahun (latih hanya dengan tahun sebelumnya);
   - bandingkan dengan **selalu-NAIK / acak / angka dasar**;
   - laporkan akurasi **per arah tebakan**;
   - permutasi bila banyak aturan dicoba.
4. **Output:** `docs/eksternal/hasil_*.txt` (laporan), `cloud/api/<nama>.json` (angka yang dipakai cloud), dan `docs/*.md`
   (ringkasan).

Contoh rantai lengkap:

| Riset | Data cloud | Modul cloud | Hasil di aplikasi |
|---|---|---|---|
| `research/masuk_pra.py` | `cloud/api/masuk_pra.json` | `_masuk_pra.py` | baris 📍 |
| `research/pra_peluang.py` | `pra_peluang.json` | `_pra_peluang.py` | "▼ TURUN 51%" |
| `research/cpi_detik.py` | `cpi_detik.json` | `_cpi_detik.py` | arah CPI |

## 6. Resep menambah metode baru

### A. Metode prediksi berita (paling umum)
1. **Riset** `research/<metode>.py`:
   - ambil daftar rilis + target (mis. `masuk_pra.kutipan()` untuk harga tick per detik);
   - hitung fitur yang **bisa dibaca live** sebelum rilis;
   - uji walk-forward + pembanding dasar, LAMA/BARU, per arah;
   - tulis `cloud/api/<metode>.json` (ringkas, < ±50 KB) dan `docs/eksternal/hasil_<metode>.txt`.
2. **Modul cloud** `cloud/api/_<metode>.py` (contoh terkecil: `_pra_peluang.py`):
   ```python
   _F = Path(__file__).with_name("<metode>.json")
   DATA = json.loads(_F.read_text(encoding="utf-8")) if _F.exists() else {}

   def aktif() -> bool:
       return os.environ.get("<METODE>", "1") != "0" and bool(DATA)

   def attach(persiapan: dict, now=None) -> None:
       if not isinstance(persiapan, dict) or not aktif():
           return
       ps = persiapan.get("pra_satu")            # atau tiap kartu di persiapan["berita"] / ["mendatang"]
       ...  # tambah poin / field; JANGAN menimpa arah teruji kecuali metode baru lebih baik & teruji
   ```
3. **Pasang** di `chat.py` pada urutan yang tepat (bagian 3), dibungkus `try/except`. Langkah yang butuh jaringan dan hanya
   info dibungkus `if sempat("<nama>")`.
4. **Tes:**
   - `tests/test_cloud_<metode>.py`;
   - `tests/test_cloud_simulasi.py` harus tetap lolos (kode cloud asli diputar Okt–Nov dengan jaringan tiruan);
   - jalankan `python -m pytest -q`.
5. **Aplikasi** (hanya bila perlu tampilan baru): baca field baru di `StatusCard.kt`, naikkan `versionCode/versionName` di
   `android/app/build.gradle.kts`, lalu cek kompilasi.
6. **Docs:** `docs/<METODE>.md` + 1 paragraf di `CLAUDE.md`, lalu PR → merge → sinkron bold-davinci.

### B. Sinyal trading baru (seperti 🌊 / 🔗)
1. Riset dengan `research/harness.py` (spread asli, entry di open berikutnya, SL dicek dulu), LAMA → BARU, pembanding acak.
2. Buat modul `cloud/api/_<sinyal>.py` dengan `<sinyal>_tick(now, bars, RowStore(store, "<baris>"), pub)`, simpan state di
   baris Supabase sendiri, dan kirim event ntfy `<sinyal>_signal/_close`.
3. Panggil dari `tick.py` di bawah env flag, lalu tambahkan kartunya di aplikasi.
4. Logika order live / bawaan bot hanya diubah dengan izin eksplisit pengguna. Auto order MetaApi bawaannya MATI.

### Aturan yang tidak boleh dilanggar
- Angka yang tampil = angka teruji. Bila tidak lebih baik dari dasar, tulis apa adanya (mis. FOMC 51%).
- Satu arah per rilis di semua kartu.
- Jangan menampilkan nilai env/token. Kode di `kandidat/` dan `arsip_repo/` hanya dibaca, jangan dijalankan.
