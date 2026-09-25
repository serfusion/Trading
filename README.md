# XAUUSD SMC Bot (MetaTrader 5 / Exness)

Bot 24 jam untuk XAUUSD berbasis **Smart Money Concepts**, sesuai setup di
[`docs/STRATEGY.md`](docs/STRATEGY.md): *sweep likuiditas (TS) → SMT → MSS →
entry di KEYY (FVG 50% / Order Block) → TP di likuiditas lawan*. Berjalan
untuk **SELL dan BUY** (BUY adalah cerminan persis logika SELL).

Fitur:
- Deteksi otomatis swing, equal highs/lows, high/low hari sebelumnya, range Asia,
  swing H1, sweep/turtle soup, MSS, FVG, Order Block, premium/discount, OTE,
  inducement, SMT (XAGUSD / EURUSD / DXY), bias H1, killzone.
- Skor konfluensi (default minimal 7 dari 13) + syarat wajib.
- Entry **limit order** di POI, SL di balik ekstrem sweep, **2 posisi**: TP1
  (likuiditas internal) dan TP2 (likuiditas eksternal). Setelah TP1 → SL ke BE,
  lalu trailing di swing.
- Filter: berita high-impact USD (±30 menit), spread, rollover, akhir pekan,
  Jumat sore, batas rugi harian 3% / mingguan 6%, berhenti setelah 2 SL beruntun.
- Lot otomatis dari % risiko (default 1%). **Tidak ada martingale.**
- Telegram: sinyal lengkap + perintah `/status /posisi /pause /resume /eval /berita /closeall`.
- Dashboard terminal, jurnal SQLite (tahan restart), backtest memakai kode yang sama dengan live.

---

## 1. Instalasi (Windows / VPS Windows)

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
5. Tes semua koneksi:
   ```bat
   python -m xau_bot check
   ```
   Perintah ini menampilkan simbol yang dipakai (mis. `XAUUSDm`), spesifikasi lot,
   offset jam server, simbol SMT, kalender berita, dan mengirim pesan tes ke Telegram.

## 2. Menjalankan

```bat
python -m xau_bot run                 :: auto-trade + dashboard
python -m xau_bot run --signals-only  :: hanya kirim sinyal Telegram
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
| `risk.risk_pct` | 1.0 | % balance yang dirisikokan per setup |
| `risk.allow_min_lot_over_risk` | false | bila 0.01 lot melebihi risiko → setup dilewati |
| `strategy.score_threshold` | 7 | skor minimal (maks 13) |
| `strategy.min_rr` | 3.0 | RR minimal ke TP2 |
| `strategy.max_sl` | 12.0 | SL lebih lebar dari ini → dilewati |
| `sessions.killzone_only` | false | true = hanya entry di killzone |
| `news.block_before/after_minutes` | 30 | jendela blokir berita |

Semua jarak memakai satuan harga: `1.00` = 1 poin di chart (4348.23 → 4349.23).

## 5. Struktur kode

```
xau_bot/
  smc.py        swing, equal levels, ATR, bias struktur (tanpa look-ahead)
  strategy.py   sweep → MSS → POI → SL/TP → skor
  engine.py     loop 24 jam, eksekusi, BE/trailing, Telegram, laporan harian
  risk.py       lot, batas harian/mingguan, SL beruntun
  sessions.py   killzone (jam New York + DST), rollover, akhir pekan
  news.py       kalender ekonomi ForexFactory
  broker/mt5.py MetaTrader 5 (Exness)   broker/paper.py simulasi backtest
  backtest.py   backtest dengan engine yang sama
tests/          36 unit test (strategi, risiko, sesi, berita, engine, MT5 palsu)
```

Menjalankan test: `pip install -r requirements-dev.txt` lalu `pytest`.

## ⚠️ Disclaimer

Trading emas dengan leverage berisiko tinggi. Bot ini mengotomasi aturan setup,
**bukan jaminan profit**. Hasil backtest tidak menjamin hasil ke depan. Selalu uji
di akun demo dan gunakan dana yang siap hilang.
