# XAUUSD Bot (MetaTrader 5 / Exness)

Bot 24 jam untuk XAUUSD dengan dua mesin strategi:

| Mode | Strategi | Hasil backtest (lihat [`docs/BACKTEST.md`](docs/BACKTEST.md)) |
|---|---|---|
| **`trend` (default)** | F-ensemble Donchian H1 (40/15, 55/20, 80/30), SL 3×ATR, 5 posisi/sinyal (TP1 1R + SL+), keluar di channel exit, **+ filter SMC bias struktur H4** | **Lolos** (engine bot, risiko 0,5%/set): +36,6% (2012–17), +29,5% (2018–22, OOS), +34,7% (Apr 2025–Sep 2026, OOS); max DD −14 s/d −17% |
| `smc` | Setup gambar kamu: sweep/TS → SMT → MSS → FVG/OB → TP di likuiditas ([`docs/STRATEGY.md`](docs/STRATEGY.md)) | **Tidak lolos**: −0,10 s/d −0,28R per trade di ±350 ribu candle |
| `both` | Keduanya (magic number terpisah) | |

### Perbandingan menyeluruh metode SMC/ICT (ringkas)

Semua metode SMC yang ramai dipakai diuji dengan aturan dan data yang sama (`python -m research.smc_models`,
bagian 10 [`docs/BACKTEST.md`](docs/BACKTEST.md)): setup bot sendiri, Turtle Soup, Judas swing / Power of 3,
sweep PDH/PDL (± MSS), ICT Silver Bullet, FVG, BOS + Order Block, OTE, CISD, Breaker, Unicorn — masing-masing
tanpa filter, dengan bias H1, dan searah trend (46 varian M15 × 3 periode + M5). **Tidak ada satu pun yang
untung konsisten** (tanpa filter: −0,02 s/d −0,40R per trade di 2012–22). Yang paling baik tetap trend-following.

Studi lanjutan **win rate vs profit** (bagian 12): 14 model SMC/ICT + 6 scalping populer (RSI(2), EMA 9/21,
Bollinger, breakout, ORB London/NY) × TP 0,5R–3R, break-even, tutup sebagian = **351 kombinasi, 0 yang untung
di ketiga periode**. TP kecil menaikkan win rate (±52%) tetapi rata-rata tetap −0,21R per trade karena
win rate impasnya 66,7%. Semua hasil bisa dilihat di tab **Riset** aplikasi.

Fitur yang digabung karena terbukti berguna:
- **Bias struktur H4 (konsep BOS dari SMC) sebagai filter trend** — profit factor naik di 6/6 uji engine,
  hasil naik di 5/6; drawdown **tidak** lebih kecil (bagian 11). Default aktif, bisa dimatikan.
- Killzone, displacement, entry pullback 50% (OB/FVG), bias D1 → diuji, **ditolak** (merusak periode lain).

> ⚠️ Tidak ada strategi yang tidak pernah rugi. Mode `trend` punya win-rate ±46–50% per sinyal, tahun
> rugi (mis. 2016, 2018, 2019) dan drawdown. Saldo kecil gunakan akun Cent, jangan menaikkan risiko.

Fitur umum:
- Lot otomatis dari % risiko (default 0,5% per set trend) atau lot tetap. **Tidak ada martingale.**
- Batas rugi harian 3% / mingguan 6%, berhenti setelah 2 SL beruntun, blok rollover, akhir
  pekan, Jumat sore, spread melebar; filter berita high-impact USD untuk mode SMC.
- Telegram: sinyal lengkap + perintah `/status /posisi /pause /resume /eval /berita /closeall`.
- Dashboard terminal, jurnal SQLite (tahan restart), backtest memakai kode yang sama dengan live.
- Mode SMC: deteksi swing, equal highs/lows, PDH/PDL, range Asia, sweep, MSS, FVG, Order Block,
  premium/discount, OTE, inducement, SMT, bias H1, killzone; TP1/TP2 + BE + trailing.

---

## 0. Mulai cepat (tanpa .env & config.yaml)

1. Buka **MetaTrader 5 Exness** dan login ke akun (Standard atau **Cent/USC**) — biarkan terbuka.
2. Pasang Python 3.11+, lalu di folder ini: `pip install -r requirements.txt`
3. `python -m xau_bot run` → bot memakai akun yang sedang login di MT5, otomatis mengenali akun
   Cent (USC → simbol `XAUUSDc`) dan berjalan dalam mode **SINYAL** (tidak membuka order).
4. `python -m xau_bot app` → tampilkan **server & topik** untuk aplikasi Android.
5. Setelah yakin, eksekusi otomatis: `python -m xau_bot run --auto`.

## Sinyal + auto order 24 jam tanpa PC (Vercel + Supabase + MetaApi)

Tidak punya PC/VPS Windows? Folder `cloud/` bisa di-deploy ke Vercel dan dijadwalkan oleh
Supabase pg_cron tiap 30 menit (atau 5 menit); harga dari Twelve Data, sinyal ke aplikasi lewat
ntfy. Opsional: auto order ke akun MT5 Exness lewat MetaApi, dinyalakan/dijeda/diatur lot dari
tab **Auto** di aplikasi Android (default OFF). Panduan lengkap: [`docs/CLOUD.md`](docs/CLOUD.md).

Pengaman auto order (PC & cloud): SL wajib di server broker, anti order dobel, tidak entry saat
akhir pekan / Jumat sore / pembukaan Minggu / rollover, spread maksimum, **batas rugi harian 3% &
mingguan 6%** (order baru berhenti, posisi berjalan tetap dikelola). Versi cloud juga menghitung
SL/TP dari harga broker (bukan harga feed) dan menolak order bila harga broker beda jauh dari feed.

## Aplikasi Android "XAU Signal"

- APK dibuat otomatis oleh GitHub Actions: buka tab **Releases → "XAU Signal (APK terbaru)"**
  (tag `android-latest`) atau **Actions → Android APK → Artifacts**, unduh `app-debug.apk`, pasang
  (izinkan "instal dari sumber tidak dikenal").
- Buka aplikasi → ⚙️ Pengaturan → isi **Server** (`https://ntfy.sh`) dan **Topik** dari
  `python -m xau_bot app` → Simpan.
- Aplikasi menampilkan harga & saldo terkini, posisi sinyal aktif (entry, SL, berjalan), riwayat
  sinyal BUY/SELL & TUTUP beserta hasil BENAR/SALAH, dan notifikasi bersuara.
- Sinyal dikirim lewat [ntfy](https://ntfy.sh) (open-source). Topik acak = kunci rahasia, jangan
  dibagikan. Alternatif: aplikasi resmi "ntfy" → subscribe ke topik yang sama.
- Tab **Statistik**: menang/kalah & profit/rugi harian, mingguan, bulanan + konversi Rupiah.
- Tab **Riset**: perbandingan semua metode (trend, SMC/ICT, scalping) — win rate, R per trade, total R,
  profit factor per periode; filter Lolos/Trend/SMC/Scalping dan urutkan menurut profit atau win rate.
- Tab **Auto** (versi cloud + MetaApi): Auto ON/OFF, Jeda, lot & jumlah posisi, filter bias H4 (SMC),
  batas rugi harian/mingguan, TUTUP SEMUA, saldo dan posisi bot yang sedang terbuka — semua dari HP.
- Kode aplikasi ada di folder `android/` (Kotlin + Jetpack Compose). Setiap build di GitHub Actions
  menjalankan lint, unit test, dan uji UI di emulator Android 8 & 14; APK baru dipublikasikan hanya bila
  semuanya lolos.

## 1. Instalasi lengkap (Windows / VPS Windows)

1. Pasang **MetaTrader 5 Exness**, login ke akun, pastikan simbol XAUUSD tampil
   di Market Watch. Aktifkan *Tools → Options → Expert Advisors → Allow algorithmic trading*.
2. Pasang **Python 3.11+** (centang *Add to PATH*).
3. Di folder ini:
   ```bat
   pip install -r requirements.txt
   copy .env.example .env
   copy config.example.yaml config.yaml
   ```
4. Isi `.env` (login MT5, server, token & chat id Telegram).
5. (Opsional — tanpa .env bot memakai akun yang sedang login di MT5.) Tes semua koneksi:
   ```bat
   python -m xau_bot check
   ```
   Perintah ini menampilkan simbol yang dipakai (mis. `XAUUSDm`), spesifikasi lot,
   offset jam server, simbol SMT, kalender berita, dan mengirim pesan tes ke Telegram.

## 2. Menjalankan

```bat
python -m xau_bot run                 :: mode SINYAL (default) + dashboard
python -m xau_bot run --auto          :: eksekusi order otomatis
python -m xau_bot run --no-dashboard  :: log biasa (untuk VPS)
start_bot.bat                         :: auto-restart bila tertutup
```

MT5 harus tetap terbuka. Untuk 24 jam gunakan VPS Windows; mode sleep Windows harus dimatikan.

### Perintah Telegram
| Perintah | Fungsi |
|---|---|
| `/status` | harga, bias, sesi, berita berikut, saldo, alasan blokir |
| `/posisi` | posisi & pending order bot |
| `/pause` / `/resume` | jeda / lanjut entry baru (posisi tetap dikelola) |
| `/eval` | ringkasan hari ini + setup 24 jam terakhir |
| `/berita` | berita high-impact 24 jam ke depan |
| `/closeall ya` | tutup semua posisi & order bot, lalu jeda |

## 3. Backtest (WAJIB sebelum akun real)

```bat
python -m xau_bot fetch --days 180
python -m xau_bot backtest --data data\XAUUSDm_M5.csv --smt XAGUSD=data\XAGUSDm_M5.csv --spread 0.20 --balance 1000 --out hasil.csv
```

Hasil: win-rate, profit factor, drawdown, dan daftar setup yang dilewati beserta
alasannya. Keterbatasan: kalender berita historis tidak tersedia (filter berita
mati saat backtest), spread dibuat tetap, dan bila SL & TP tersentuh di bar yang
sama dianggap SL (konservatif).

**Urutan aman:** backtest → akun demo 2–4 minggu (`trade_enabled: true` di akun
demo) → akun real dengan `risk_pct: 0.25–0.5`.

## 4. Pengaturan penting (`config.yaml`)

| Kunci | Default | Arti |
|---|---|---|
| `trade_enabled` | false | false = sinyal saja; true / `run --auto` = order otomatis |
| `broker.account_type` | auto | auto (USC = Cent), `cent`, `standard` |
| `app.server` / `app.topic` | ntfy.sh / acak | tujuan sinyal aplikasi Android |
| `strategy.mode` | trend | `trend`, `smc`, atau `both` |
| `trend.ensemble` / `stop_atr` / `legs` / `tp1_r` | [[40,15],[55,20],[80,30]] / 3.0 / 5 / 1.0 | parameter trend tervalidasi (skema F) |
| `trend.risk_pct_per_set` / `fixed_leg_lot` | 0.5 / 0 | risiko % per set, atau lot tetap per posisi (mis. 0.01 akun Cent) |
| `trend.bias_filter` / `bias_tf` / `bias_swing` | true / H4 / 3 | filter SMC: breakout hanya searah bias struktur H4 |
| `risk.risk_pct` | 1.0 | % balance yang dirisikokan per setup SMC |
| `risk.allow_min_lot_over_risk` | false | bila 0.01 lot melebihi risiko → setup dilewati |
| `strategy.score_threshold` | 7 | skor minimal (maks 13) |
| `strategy.min_rr` | 3.0 | RR minimal ke TP2 |
| `strategy.max_sl` | 12.0 | SL lebih lebar dari ini → dilewati |
| `sessions.killzone_only` | false | true = hanya entry di killzone |
| `news.block_before/after_minutes` | 30 | jendela blokir berita |

Semua jarak memakai satuan harga: `1.00` = 1 poin di chart (4348.23 → 4349.23).

## 5. Riset & backtest data historis

Lihat [`docs/BACKTEST.md`](docs/BACKTEST.md): metodologi, hasil per periode/tahun, dan perintah
untuk mengulang (`bash research/download_data.sh`, `python -m research.engine_validate ...`).

## 6. Struktur kode

```
xau_bot/
  smc.py        swing, equal levels, ATR, bias struktur (tanpa look-ahead)
  trend.py      Donchian trend-following (mode default)
  trend_ensemble.py  skema F-ensemble (3 set, 5 posisi, TP1 + SL+) + filter bias H4, anti dobel
  strategy.py   SMC: sweep → MSS → POI → SL/TP → skor
  engine.py     loop 24 jam, eksekusi, BE/trailing, Telegram, laporan harian
  risk.py       lot, batas harian/mingguan, SL beruntun
  sessions.py   killzone (jam New York + DST), rollover, akhir pekan
  news.py       kalender ekonomi ForexFactory
  broker/mt5.py MetaTrader 5 (Exness)   broker/paper.py simulasi backtest
  backtest.py   backtest dengan engine yang sama
research/       scan, simulasi, uji ketahanan & validasi engine di data historis
  smc_models.py     perbandingan 16 model SMC/ICT (+ filter) di 3 periode
  trend_filters.py  uji fitur SMC sebagai filter trend (76 varian + skema F)
  winrate_study.py  win rate vs profit: SMC + scalping x TP/BE/parsial (351 kombinasi) -> data tab Riset
cloud/          versi 24 jam tanpa PC (Vercel + Supabase + ntfy + MetaApi)
tests/          87 unit test (strategi, trend, F-ensemble, filter bias, risiko, sesi, berita, engine,
                MT5 palsu, cloud & auto order MetaApi palsu)
```

Menjalankan test: `pip install -r requirements-dev.txt` lalu `pytest`.

## ⚠️ Disclaimer

Trading emas dengan leverage berisiko tinggi. Bot ini mengotomasi aturan setup,
**bukan jaminan profit**. Hasil backtest tidak menjamin hasil ke depan. Selalu uji
di akun demo dan gunakan dana yang siap hilang.
