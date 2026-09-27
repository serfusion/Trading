# Spesifikasi Strategi XAUUSD (acuan bot)

> **Hasil backtest:** setup SMC di dokumen ini, setelah diotomasi, **rugi** di ±350 ribu candle
> asli (2012–2022 & 2025–2026). Model SMC/ICT populer lain (Silver Bullet, Judas/PO3, Turtle Soup, OB,
> FVG, OTE, CISD, Breaker, Unicorn) juga rugi (BACKTEST.md bagian 10). Bot memakai mode `trend`
> (F-ensemble Donchian H1) sebagai default; satu-satunya konsep SMC yang dipakai adalah bias struktur
> H4 sebagai filter (bagian 11). Detail di [`BACKTEST.md`](BACKTEST.md).

Dokumen ini adalah hasil verifikasi dari 20+ screenshot setup (TradingView) dan
screenshot bot referensi. Semua aturan di sini akan diterjemahkan ke kode.

- Broker: **Exness**, platform **MetaTrader 5**, akun **USD (standar, bukan cent)**
- Mode bot: **eksekusi otomatis + sinyal Telegram** (bisa di-on/off terpisah)
- Simbol: XAUUSD (nama persis di Exness bisa `XAUUSD`, `XAUUSDm`, dst. — dibuat konfigurasi)

---

## 1. Cara membaca chart setup (WAJIB — sumber kesalahan sebelumnya)

### 1.1 Arah posisi
| Posisi | Kotak merah/pink (SL) | Zona profit |
|---|---|---|
| **BUY** | di **bawah** entry | di **atas** entry |
| **SELL** | di **atas** entry | di **bawah** entry |

- Chart *Ibnulzeroprot*: zona profit **biru**.
- Chart *febedin166*: zona profit **abu-abu muda**.
- Warna zona profit tidak menentukan arah; **posisi kotak merah** yang menentukan.

### 1.2 Warna candle
| Tema | Candle naik (bullish) | Candle turun (bearish) |
|---|---|---|
| Ibnulzeroprot | **abu-abu** | **biru/hijau gelap** |
| febedin166 | **abu-abu muda/putih** | **hitam/abu tua** |

Garis tipis hitam = **ekor (wick)**. Ekor yang masuk ke zona SL tetapi body
tidak close di sana ≠ SL kena (kecuali harga benar-benar menyentuh level SL).
Selalu baca **candle terakhir** untuk status posisi.

### 1.3 Satu chart bisa berisi beberapa posisi
Contoh (24–25 Sep, 10m): **SELL → SELL → sweep + SMT → BUY → BUY**. Target
satu setup sering menjadi titik entry setup berlawanan berikutnya.

---

## 2. Rekap setup yang diverifikasi

| Hal. | Waktu (WIB) | Arah | Entry | SL | Target | Catatan / hasil |
|---|---|---|---|---|---|---|
| 1 | 18 Sep 22:09 | BUY | 4349.19 (QML / KEY LEVEL 2) | 4344.49 | BSL 4399.38 / 4402.78 | SMT di low, MSS kecil. Ada layer BUY ke-2 lebih dalam 4335.30 / SL 4332.72 |
| 2 | 18 Sep 23:47 | BUY ×2 | QML 4348.23 & CLASSIC V 4351.37 | 4345.18 & 4348.21 | BSL 4399.47–4402.78 | Panah hijau: retest Classic V lalu ke BSL |
| 3 | 20 Sep 13:44 | BUY | 4348.23 | 4345.18 | 4399.48 → LIQUIDITY/KEY 4426.92 | ✅ Tercapai ±4400. FVG 50%, SSMT, IDM, BOS, MSS |
| 4 | 21 Sep 07:11 | BUY (BTCUSD) | 57 922 | 56 403 | BSL 97 932 | TS di last liquidity, CE 50%. Berjalan (81 415) |
| 5–6 | 21 Sep 09:30 | BUY limit | KEY LEVEL'S 4350.13 | 4347.11 / 4345.18 | 4383.38 | Hal. 6 = duplikat hal. 5. Panah: turun dulu ke key level lalu naik |
| 7 | 21 Sep 17:42 | BUY | 4350.12 | 4345.18 | 4355.19 / 4356.11 | TP = tinggi range key level (5.99 poin) diproyeksikan. Ekor terendah ±4346, **SL tidak tersentuh**, candle terakhir abu-abu (naik) |
| 8–9 | 21 Sep 21:03 | SELL | 4364.18 | 4366.68 | SSL 4334.37 | ✅ SMT (high 4374.42 → lower high) + TS. Kiri: BUY Classic V 4340.89 / SL 4338.35 → 4374.42 ✅ |
| 10 | 21 Sep 21:33 | SELL ke-2 | KEY LEVEL'S 4361.66–4363.31 | 4366.41 | LIQUIDITY 4314.80 | Retracement setelah SSL tersapu |
| 11 | 22 Sep 06:17 | SELL | KEY LEVEL'S 4364.22 | 4367.28 | ±4340 | Ekor masuk zona SL tapi tidak menyentuh SL; candle terakhir turun panjang → **running profit** |
| 12–13 | 22 Sep | (setup lampau) | — | — | — | Studi garis: SMT, TS, garis horizontal bertingkat 4365.43 / 4361.66 / 4357.02 = BOS ke bawah → KEY LEVEL SELL |
| 14 | 24 Sep 12:32 | SELL + BUY limit | SELL 4289.53 (KEYY) / BUY 4249.59 (KEYY) | 4294.58 / 4247.04 | LAST LIQUIDITY 4254.48 / — | |
| 15 | 24 Sep 17:31 | SELL berjalan + BUY limit | BUY KEYY 4243.91 | 4241.40 | BSL 4303.16 | ✅ SELL mencapai last liquidity |
| 16 | 25 Sep 06:11 | BUY | 4272.19 | 4270.88 | 4281.37 | |
| 17 | 25 Sep 08:02 | BUY bertingkat | KEYY 4245.71 → 4256.79 → 4264.84 | 4243.17 / 4254.22 / 4262.29 | BSL 4303 | Garis lengkung di high = liquidity pool, trendline turun, SMT + TS di low |
| 18 | 25 Sep 09:32 | BUY limit | KEYY 4283.84 | 4281.34 | BSL 4303.21 | **INDUCEMENT ZONE** di atas KEYY: tunggu tersapu dulu |
| 19 | 25 Sep 11:21 (5m) | pemicu BUY | ±4264.89 / 4265.93 | — | — | Bulatan hijau: dua ekor menyapu low lalu ditolak (double bottom TS) |
| 20 | 24–25 Sep (10m) | 2× SELL lalu 2× BUY | SELL KEYY ±4300 & 4289.53; BUY KEYY 4245 & 4256.75 | 4302.72 & 4292.58; 4243.17/4242.00 & 4254.18 | SSL ±4243; BSL 4303 | ✅ semua, harga tembus ±4310 |

Ciri-ciri umum:
- SL **sangat tipis**: 1.3–5 poin (± 130–500 point di MT5).
- RR umumnya **1:5 sampai 1:20**. TP selalu di **likuiditas** (bukan angka tetap).
- Posisi ditambah **bertingkat** di KEYY baru hanya setelah posisi sebelumnya aman (struktur sudah BOS).

---

## 3. Kamus garis & label

| Label / garis | Cara menarik | Fungsi di bot |
|---|---|---|
| **BSL / SSL / LIQUIDITY / LAST LIQUIDITY** | Horizontal di ujung ekor swing high/low, terutama equal highs/lows | Target TP & area sweep |
| **KEY / KEYY / KEY LEVEL'S** | Body candle berlawanan terakhir sebelum dorongan (order block) atau level yang baru ditembus | Zona entry (limit order) |
| **QML** | Pola high–low–higher high–lower low (atau kebalikan); level di left shoulder | Zona entry |
| **CLASSIC V** | Reversal V tajam: sweep lalu langsung naik/turun kuat | Zona entry ulang (retest) |
| **BOS** | Body close melewati swing searah tren | Tren berlanjut |
| **MSS / X** | Body close melewati swing berlawanan pertama | Tren berbalik — syarat entry |
| **IDM / INDUCEMENT ZONE** | Swing kecil sebelum KEYY | Harus tersapu dulu sebelum entry |
| **SMT / SSMT** (garis merah diagonal) | Menghubungkan 2 high/2 low XAU yang divergen dengan XAG/DXY | Konfirmasi reversal |
| **-TS** (Turtle Soup) | Garis pendek di ekor yang menyapu high/low | Pemicu: likuiditas diambil lalu ditolak |
| **FVG 50% / CE 50%** | Titik tengah celah 3-candle | Entry presisi |
| **Fibo 0.5 / 0.56 / 0.8x** | Swing low → swing high | Premium / discount |
| **Trendline hitam** | Menghubungkan lower highs / higher lows | Trendline liquidity |
| **Garis lengkung** | Menghubungkan high/low yang membulat | Liquidity pool (akan disapu) |
| **Garis putus-putus di kotak posisi** | Entry → TP | Proyeksi jalur |
| **Ukuran range (mis. 5.99 poin)** | Tinggi range konsolidasi di key level | Proyeksi TP minimal (measured move) |

---

## 4. Model entry (digabung dengan metode populer)

Inti strategi = **ICT / Smart Money Concepts**. Tambahan dari model yang
sudah umum dipakai dan terdokumentasi:

| Model | Inti | Dipakai sebagai |
|---|---|---|
| **Liquidity sweep + SMT + MSS** (setup asli) | Sweep → divergensi → struktur berbalik → entry KEYY | Model utama |
| **Turtle Soup** (Raschke/Connors) | False breakout high/low lalu reversal | Pemicu sweep |
| **ICT Silver Bullet** | FVG setelah raid likuiditas pada jam 10–11 & 14–15 New York | Filter waktu prioritas |
| **Power of 3 / AMD / Judas Swing** | Akumulasi Asia → manipulasi London open → distribusi NY | Bias arah harian & target (high/low Asia) |
| **OTE** | Entry di retracement Fibo 0.62–0.79 | Konfluensi KEYY |
| **Breaker / Unicorn** | OB gagal yang tertembus + FVG di area yang sama | Konfluensi KEYY |
| **CISD** (change in state of delivery) | Close melewati open rangkaian candle berlawanan | Konfirmasi MSS di TF kecil |

> Klaim win-rate (mis. "80% Silver Bullet XAUUSD") dari blog/YouTube **tidak
> dianggap valid** sampai dibuktikan dengan backtest bot sendiri di data Exness.

### 4.1 Skor konfluensi (entry hanya jika ≥ 7 dan syarat wajib terpenuhi)
| Komponen | Poin | Wajib? | Implementasi (`xau_bot/strategy.py`) |
|---|---|---|---|
| Sweep likuiditas / TS | 2 | ✅ | ekor menembus level, close kembali di dalam ≤ 2 bar |
| MSS / CISD di TF entry | 2 | ✅ | close menembus swing internal terakhir sebelum sweep, dengan displacement ≥ 1 ATR |
| SMT dengan XAGUSD / EURUSD (/ DXY) | 2 | | pasangan gagal membuat high/low baru |
| Entry di KEYY: FVG 50% atau Order Block | 1 | ✅ | FVG belum termitigasi, kalau tidak ada pakai OB (50% body) |
| Premium (SELL) / discount (BUY) | 1 | ✅ | entry di atas/bawah 50% range sweep → leg |
| Searah bias H1 | 1 | | BOS terakhir di H1 |
| Dalam killzone (London / NY / Silver Bullet) | 1 | | jam New York, ikut DST otomatis |
| Inducement di depan entry | 1 | | swing internal di antara harga & entry |
| Entry di OTE 62–79% | 1 | | rasio retracement |
| Likuiditas eksternal tersapu | 1 | | equal highs/lows, swing H1, high/low hari sebelumnya, range Asia |
| Tidak ada berita high-impact ±30 menit | — | ✅ (filter) | kalender ForexFactory |
| Spread ≤ 0.40 | — | ✅ (filter) | |

Skor maksimum 13.

### 4.2 Timeframe
- **H4/H1**: bias & likuiditas besar (BSL/SSL, high/low harian & mingguan).
- **M15/M10**: POI (KEYY, OB, FVG, QML).
- **M5/M1**: sweep, MSS, CISD, eksekusi.

---

## 5. Faktor fundamental & pasar

| Faktor | Aturan bot |
|---|---|
| Kalender ekonomi (NFP, CPI, PCE, FOMC, GDP, klaim pengangguran, ISM, pidato Powell) | Stop entry baru 30 menit sebelum – 30 menit setelah high-impact; posisi berjalan dipindah ke BE |
| DXY & US10Y / real yield | Dipakai untuk SMT (DXY terbalik) dan bias harian |
| Ekspektasi suku bunga Fed | Bias mingguan (manual/konfigurasi) |
| Geopolitik / risk-off | Mode waspada: lot dikurangi |
| Sesi (WIB, musim panas AS) | Asia 06–13, London 14–17 (killzone 14–16), NY 19–23 (killzone 19–21), Silver Bullet NY 21–22 & 01–02 |
| Rollover harian 17:00 New York (±04:00 WIB musim panas AS / 05:00 WIB musim dingin), ±30 menit | Tidak ada entry, spread lebar |
| Senin gap / Jumat malam | Lot dikurangi / tidak entry setelah Jumat 22:00 WIB |
| Pergantian DST AS/Eropa | Jam sesi otomatis mengikuti zona waktu New York/London |

---

## 6. Manajemen risiko

- Risiko **per setup 0.5–1% equity** (default 1%), lot dihitung dari jarak SL
  + spread. Tidak ada kenaikan lot ala martingale.
- SL = di balik sweep/KEYY + buffer (spread + 0.3–0.5 poin). **SL minimum**
  mengikuti `stops_level` broker.
- TP1 di likuiditas internal (tutup 50%, SL → BE), TP2 di likuiditas eksternal
  (BSL/SSL), sisa jadi runner dengan trailing per swing.
- Maks **1 setup aktif per arah**; posisi bertingkat hanya jika posisi
  sebelumnya sudah BE.
- **Batas rugi harian 3%**, **berhenti setelah 2 SL beruntun**, batas rugi
  mingguan 6%.
- Jika koneksi/AI/data error → **tidak buka posisi baru**, posisi lama tetap
  dikelola oleh aturan SL/TP di server broker.

---

## 7. Kesalahan bot referensi yang TIDAK boleh diulang

1. Bias hanya dari EMA20 < EMA50 (terlambat, bertentangan dengan SMC).
2. Logika "RSI belum oversold → SELL" (RSI 69 = momentum naik kuat).
3. SL/TP tetap 5/10 poin, tidak mengikuti struktur & likuiditas.
4. Tiga entry dalam satu menit dengan lot naik (0.03→0.04→0.06).
5. SELL di area discount (di bawah entry sebelumnya).
6. AI timeout → seluruh bot HOLD; seharusnya rule engine tetap jalan dan AI hanya pelengkap.

---

## 8. Referensi

- Python SMC indicators: [joshyattridge/smart-money-concepts](https://github.com/joshyattridge/smart-money-concepts) (`pip install smartmoneyconcepts`: swing highs/lows, BOS/CHoCH, OB, FVG, liquidity)
- SMC untuk MT5: [GeneralTradingSarl/Smart-Money-Concepts](https://github.com/GeneralTradingSarl/Smart-Money-Concepts)
- ICT Silver Bullet: [LuxAlgo Blog](https://www.luxalgo.com/blog/ict-silver-bullet-setup-trading-methods/), [innercircletrader.net](https://innercircletrader.net/tutorials/ict-silver-bullet-strategy/)
- MetaTrader5 Python API (resmi MetaQuotes): paket `MetaTrader5`

## 9. Prosedur sebelum akun real

1. Backtest di data Exness ≥ 6 bulan M1 (termasuk spread nyata).
2. Forward test di **akun demo Exness minimal 2–4 minggu**.
3. Akun real dengan risiko 0.25–0.5% per trade dulu, naik bertahap.
4. Evaluasi jurnal mingguan (win-rate, RR rata-rata, drawdown per sesi & per model).
