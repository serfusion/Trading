# Sinyal 24 Jam Tanpa PC (Vercel + Supabase + ntfy)

```
Supabase pg_cron (menit :02 & :32 tiap jam)
   └─ GET https://DOMAIN_KAMU/api/tick?key=RAHASIA   (fungsi Python di Vercel, folder cloud/)
        ├─ ambil candle H1 XAU/USD dari Twelve Data
        ├─ skema F-ensemble: 3 set Donchian H1 (40/15, 55/20, 80/30), 5 posisi/sinyal,
        │  TP1 1R untuk posisi #1, SL+ ke entry setelah TP1 (identik dengan bot)
        ├─ simpan posisi virtual & riwayat di tabel Supabase
        ├─ kirim sinyal BUY/SELL/TUTUP + status → ntfy.sh → aplikasi Dividend Indicator
        └─ (opsional, Langkah 6) auto order → MetaApi → akun MT5 Exness  ← dikontrol dari tab "Auto" di HP
```

**Tanda ⭐**: semua sinyal dikirim; sinyal yang searah tren D1 (close D1 kemarin vs EMA50 D1) dan
menembus high/low 20 candle H4 sebelumnya diberi tanda ⭐ (`research/filters.py`).

**Badge di setiap sinyal** (profit didahulukan, dari data historis multi-tahun, `research/badge_stats.py` &
`research/gap_years.py`): 💰 = profit rata-rata per sinyal (💰💰💰 ≥+0,25R, 💰💰 ≥+0,12R, 💰 ≥+0,05R), lalu
⭐ = win rate (⭐⭐⭐ ≥75%, ⭐⭐ ≥60%, ⭐ ≥48%). **Hanya sinyal 💰 yang dikirim** (`profit_only`); sinyal biasa & XAU
"⭐ saja" (profit ±0) dilewati.

| Sinyal | WR | Profit/sinyal | Badge |
|---|---|---|---|
| Gap pekan AUD/USD | 90% | +0,25R | 💰💰💰⭐⭐⭐ |
| Gap pekan USD/JPY | 82% | +0,26R | 💰💰💰⭐⭐⭐ |
| Gap pekan EUR/JPY | 84% | +0,14R | 💰💰⭐⭐⭐ |
| Gap pekan AUD/JPY | 86% | +0,10R | 💰⭐⭐⭐ |
| Gap pekan EUR/CHF | 74% | +0,13R | 💰💰⭐⭐ |
| BTC ⭐ (tren D1 + H4) | 50% | +0,68R | 💰💰💰⭐ |
| BTC konfluensi + ⭐ | 48% | +0,31R | 💰💰💰 |
| BTC konfluensi | 48% | +0,23R | 💰💰⭐ |
| XAU konfluensi + ⭐ | 49% | +0,31R | 💰💰💰⭐ |
| XAU konfluensi | 48% | +0,09R | 💰⭐ |

**Skema** (aplikasi 2.8+): tetap **1 posisi TP1 (1R) + 4 posisi running sampai sinyal TUTUP, SL+ ke entry saat TP1
kena** — pilihan "3 (sisa 2)" dan "SL+ 0,7R" dihapus atas permintaan pengguna (trading manual). Cloud tetap mengirim
`r_by` (hasil R keempat skema) di event TUTUP dan event info `kind: be07`, tetapi aplikasi 2.8 hanya memakai skema
bawaan. Kartu sinyal aktif menampilkan **level TUTUP** (heartbeat `exits`: low/high 15/20/30 candle H1 terakhir per
set) — 4 posisi running ditutup saat close H1 menembus level itu. SL+ bertangga / TP2-TP3 / trailing ATR diuji dan
lebih buruk (`docs/RISET_DATA_EKSTERNAL.md` §10). Riset `research/early_be.py` (XAU 2012–2026 / BTC 2016–2026):

| Skema | XAU WR | XAU total | BTC WR | BTC total |
|---|---|---|---|---|
| 1 TP1 + 4 sisa, SL+ setelah TP1 (bawaan) | 45% | +245R | 45% | +765R |
| 1 TP1 + 4 sisa, SL+ di 0,7R | 55% | +218R | 54% | +759R |
| 3 TP1 + 2 sisa, SL+ setelah TP1 | 45% | +107R | 45% | +368R |
| 3 TP1 + 2 sisa, SL+ di 0,7R | 55% | +99R | 54% | +354R |

**BTC/USD** (env `BTC_SIGNALS=0` untuk mematikan): mesin yang sama dengan XAU, 24 jam (tanpa aturan jam pasar/gap),
state di baris Supabase `btc`, ID diawali `BTC-`. Lot memakai kontrak BTCUSD(c) 1 BTC per lot (0,01 lot = 0,01 per
$1 gerak) — cek spesifikasi simbol di MT5.

**Sinyal gap pekan forex** (`cloud/api/_gap.py`, env `GAP_SIGNALS=0` untuk mematikan): 1 jam setelah pasar forex
buka (Minggu 17:00 New York), bila gap ≥ 0,5 × range harian 14 hari → lawan gap, TP 50% gap tertutup, SL 1× gap,
tutup otomatis 24 jam. Data 5 pair hanya diambil di jendela buka pekan atau saat ada posisi gap terbuka (hemat
kuota Twelve Data).

**Jam pasar & gap**: candle saat pasar tutup (Jumat 17:00 – Minggu 18:00 New York, dan jeda harian
17:00–18:00) dibuang, karena feed tetap mengirim candle datar yang membuat ATR/channel palsu
(kasus Minggu 27 Sep 2026 22:02 UTC: BUY 4279,32 dengan SL hanya $1,23). Sinyal di **3 candle H1 pertama
setelah pasar buka** (gap pekan) dilewati (`research/gap_study.py`). Sinyal lama yang lahir dari data
pasar tutup otomatis dikirim sebagai **BATAL** dan tidak dihitung menang/kalah.

Simulasi di data asli Apr 2025 – Sep 2026 (tick tiap 30 menit, `python -m research.cloud_check --semua`):

| | Sinyal | Untung | Total | Rata-rata/sinyal |
|---|---|---|---|---|
| ⭐ | 112 | 58,0% | +74,9R | +0,67R |
| Biasa | 223 | 43,5% | +1,8R | +0,01R |
| Semua | 335 | 48,4% | +76,7R | +0,23R |

Hampir semua profit datang dari sinyal ⭐; sinyal biasa rata-rata impas. Tidak ada yang pasti menang.
dinyalakan lewat Langkah 6 (semua diatur dari aplikasi Android).

## Langkah 1 — Twelve Data (harga emas)
1. Daftar gratis di <https://twelvedata.com> → Dashboard → salin **API Key**.
2. Kuota gratis 800 panggilan/hari; tick tiap 30 menit memakai 48/hari (tiap 5 menit = 288/hari).

## Langkah 2 — Topik ntfy
Buat topik acak (rahasia), misalnya dari `https://DOMAIN_KAMU/api/topic` setelah langkah 3
selesai, atau ketik sendiri: `xau-` + 20 huruf/angka acak. Topik yang sama dipakai di Vercel dan
di aplikasi.

## Langkah 3 — Vercel
1. Vercel → **Add New → Project** → impor repo GitHub **Trading**.
2. **Root Directory: `cloud`**, Framework Preset: **Other** (tanpa build command).
3. **Settings → Environment Variables** (Production):

| Nama | Isi |
|---|---|
| `TWELVEDATA_API_KEY` | API key dari langkah 1 |
| `SUPABASE_URL` | `https://xxxx.supabase.co` (Supabase → Project Settings → API) |
| `SUPABASE_SERVICE_KEY` | *service_role key* (Project Settings → API) — rahasia, jangan dibagikan |
| `NTFY_TOPIC` | topik dari langkah 2 |
| `CRON_SECRET` | kata sandi acak panjang buatanmu, mis. `k9Qm2...` |
| `NTFY_SERVER` | (opsional) default `https://ntfy.sh` |
| `SYMBOL` | (opsional) default `XAU/USD` |
| `LEGS` | (opsional) jumlah posisi per sinyal, default `5` |
| `LEG_LOT` | (opsional) lot per posisi yang ditampilkan di sinyal, default `0.01` |
| `STAR_ONLY` | (opsional) `0` = semua sinyal, ⭐ ditandai (default); `1` = hanya kirim sinyal ⭐ |
| `CHAT_KEY` | (opsional) kunci tab **Tanya**; kosong = memakai `NTFY_TOPIC` (aplikasi mengirim topiknya) |
| `BTC_FUNDING_FILTER` | (opsional) `1` = lewati sinyal BTC 💰 saat funding Binance ramai (default), `0` = mati |
| `BTC_SEPT_FILTER` | (opsional) `1` = lewati sinyal BTC 💰 di bulan September (default), `0` = mati |
| `WAR_MODE` | (opsional) `1` = label ⚠️ mode perang di sinyal XAU & heartbeat saat WTI (FRED, tanpa kunci) naik ≥ 10% dalam 10 hari bursa (default; XAU **tidak** dijeda), `0` = mati |
| `WAR_BACKUP` | (opsional) `1` = bila FRED gagal/basi (data terbaru > 10 hari; FRED WTI normal terbit mingguan), label mode perang memakai ETF USO dari Twelve Data (default; paling sering tiap 6 jam, cache di baris `perang`), `0` = mati |

4. **Deploy**. Lalu **Settings → Domains** → tambah subdomain, mis. `signal.domainkamu.com`, dan
   ikuti instruksi DNS dari Vercel.
5. Pastikan branch yang di-deploy memuat folder `cloud/` (Settings → Git → Production Branch).

## Langkah 4 — Supabase
1. **Database → Extensions** → aktifkan **pg_cron** dan **pg_net**.
2. **SQL Editor → New query** → tempel isi [`cloud/supabase.sql`](../cloud/supabase.sql).
3. Ganti `DOMAIN_KAMU` dan `CRON_SECRET_KAMU` di bagian bawah → **Run**.

## Langkah 5 — Tes
1. Buka di browser: `https://signal.domainkamu.com/api/tick?key=CRON_SECRET` → harus muncul
   `{"ok": true, "price": ..., "trend": "close ... | channel 55: ... "}`.
2. Aplikasi Dividend Indicator → ⚙️ → Server `https://ntfy.sh`, Topik = `NTFY_TOPIC` → Simpan →
   kartu atas menampilkan harga & "Mode: SINYAL (cloud)".
3. Di Supabase: `select status_code, content from net._http_response order by created desc limit 5;`
   → status 200 setiap 30 menit.

## Langkah 6 — Auto order dari HP, tanpa PC (MetaApi, opsional)
MT5 di HP tidak bisa menjalankan bot/EA, jadi order dieksekusi dari server: Vercel mengirim order ke
[MetaApi](https://metaapi.cloud) (layanan resmi yang menjalankan terminal MT5 di cloud), MetaApi
meneruskannya ke akun Exness. Aplikasi Android (tab **Auto**) hanya remote control, jadi HP boleh mati.

> ⚠️ Mulai dengan akun **DEMO** Exness minimal 1–2 minggu. Auto order default **OFF** — walau semua
> variabel sudah diisi, tidak ada order sampai kamu menyalakannya di aplikasi.

1. **MetaApi**: daftar di <https://app.metaapi.cloud> → **Accounts → Add account**:
   - Platform **MT5**, Login = nomor akun Exness, Password = **password trading** (bukan investor),
     Server = nama server persis seperti di MT5 (mis. `Exness-MT5Trial9` untuk demo).
   - Simpan → tunggu status **Deployed / Connected**. Catat **Account ID** dan **region** akun
     (mis. `new-york`, `london`, `singapore`).
   - Menu **API access / Token** → buat token → salin.
   - Cek halaman harga MetaApi: ada kuota gratis/percobaan, akun yang aktif terus bisa dikenai biaya.
2. **Vercel → Settings → Environment Variables**, tambah lalu **Redeploy**:

| Nama | Isi |
|---|---|
| `METAAPI_TOKEN` | token MetaApi — rahasia |
| `METAAPI_ACCOUNT_ID` | Account ID dari MetaApi |
| `METAAPI_REGION` | region akun, default `new-york` |
| `BROKER_SYMBOL` | simbol di MT5: `XAUUSDc` (Standard Cent, default), `XAUUSDm` (Standard), `XAUUSD` (Pro/Raw/Zero) — cek di Market Watch |
| `CONTROL_KEY` | kata sandi acak panjang (beda dari `CRON_SECRET`) untuk aplikasi — rahasia |
| `MAX_LEG_LOT` | (opsional) batas lot per posisi yang boleh diatur dari HP, default `0.10` |

3. **Supabase → SQL Editor**: saat auto aktif, jalankan tick tiap 5 menit supaya TP1/SL+/TUTUP cepat
   (288 panggilan/hari, masih di bawah kuota gratis Twelve Data 800):
   ```sql
   select cron.unschedule('xau-tick');
   select cron.schedule('xau-tick', '*/5 * * * *', $$ select net.http_get(
     url := 'https://DOMAIN_KAMU/api/tick?key=CRON_SECRET_KAMU', timeout_milliseconds := 60000); $$);
   ```
4. **Aplikasi (v1.2+) → tab Auto** → URL cloud (mis. `https://superfal-dev.com`) + `CONTROL_KEY` →
   **Simpan & hubungkan**. Harus muncul saldo akun MetaApi dan "AUTO OFF".
5. Atur **Lot/posisi** (akun Cent Rp5–10 jt: `0.01`) dan **Jumlah posisi** (`5`) → **Simpan lot** →
   nyalakan **Auto order**.

Cara kerja order (sama dengan sinyal & bot PC, skema F):
- Sinyal baru → 5 market order, semua dengan **SL sungguhan di server broker**; posisi #1 juga TP1 (1R).
- TP1 kena → SL 4 posisi sisa dipindah ke harga isi masing-masing ± 0,10 (SL+).
- Sinyal TUTUP / SL virtual → semua posisi set itu ditutup.
- Anti dobel: status disimpan ke Supabase **sebelum** order dikirim, order hanya dikirim bila set itu
  tidak punya posisi, dan tiap set memakai magic sendiri (250936–250938). Posisi manual / EA lain
  tidak pernah disentuh.
- MetaApi gangguan → sinyal tetap terkirim, auto order set itu dilewati (ada notifikasi ⚠️).
- **Auto OFF / Jeda** = tidak membuka order baru; posisi yang sudah terbuka tetap dikelola.
- **TUTUP SEMUA** = tutup semua posisi bot di harga pasar lalu auto dijeda.
- Jangan jalankan bot PC `run --auto` di akun yang sama bersamaan (magic sama → saling mengelola).

Kontrol juga bisa lewat HTTP: `GET/POST https://DOMAIN_KAMU/api/control` dengan header
`X-Control-Key: CONTROL_KEY`, body mis. `{"auto": true, "leg_lot": 0.01, "legs": 5}` atau
`{"close_all": true}`.

## Tab News (kalender + chat berbasis data, tanpa AI)

`POST /api/chat` (`cloud/api/chat.py`, `_chat.py`) menjawab dari **data** saja — tanpa AI, tanpa API berbayar,
hanya library standar:
- **statistik historis** `cloud/api/pengetahuan.json` (dibuat `python -m research.event_stats`; versi baca-manusia
  `pengetahuan.md`): reaksi emas/BTC per berita (NFP, CPI, PPI, FOMC, Retail, PCE, GDP, ISM, Claims) menurut arah &
  besar kejutan, FOMC sesuai ekspektasi vs kejutan, sinyal 💰 di sekitar berita — setiap peluang disertai n;
- **konteks langsung**: kalender USD high-impact minggu ini (ForexFactory), posisi bot XAU/BTC (Supabase), filter BTC.
- **Format ForexFactory "Act: Cons: Prev:"** (kartu 📝 di aplikasi 3.0; Cons & Prev terisi otomatis dari kalender
  lewat `GET /api/chat`): mis. `NFP Act: 45K Cons: 98K Prev: 162K`, boleh beberapa baris (`Unemployment Rate …` di
  NFP ditandai info saja). Pemindaian: arah & besar kejutan per baris (persentil terhadap semua rilis sejak 2010),
  tren vs bulan lalu, kesimpulan arah emas, peluang historis 15 menit – 1 hari, kejutan besar, dan **gabungan Act vs
  Prev** (mis. NFP lebih lemah dari perkiraan DAN dari bulan lalu: emas naik 1 jam 78%, n=54; bila tidak searah
  dengan bulan lalu: 54%, n=13). Federal Funds Rate Act/Cons/Prev → keputusan & kejutan FOMC.
- Pertanyaan bebas juga dikenali: nama berita, arah ("lebih tinggi/kecil dari perkiraan", "hawkish"), angka
  ("NFP 45K" → Cons & Prev dari kalender minggu ini), waktu ("sebelum" / "sudah keluar"), "sinyal terbuka",
  "SL+/TP", "BTC funding", "berita minggu ini". Hasil rilis tidak diambil otomatis — pengguna mengisi Act.

Aplikasi 3.8: tab **News** = kalender USD high-impact minggu ini (tanggal/jam WIB otomatis dari ForexFactory), Act
otomatis dari CSV publik FRED (tanpa API key) untuk NFP, Unemployment Rate, CPI, Core CPI, CPI y/y, PPI, Core PPI,
Retail, Core Retail, Core PCE, Claims, GDP — hanya bila periode acuannya sudah dimuat FRED (biasanya menit s/d ±1 jam
setelah rilis; bisa selisih 0,1 karena pembulatan). Tekan berita → analisa Act/Cons/Prev. Entry/TP/SL berita tidak
disarankan: `research/news_trade.py` (36 cara, semua rugi).
Aplikasi 3.9: kartu **Status tren sekarang** di tab News — tiap indikator (momentum, SMA, Donchian, Supertrend,
RSI, pindah tren, konsensus, yield riil, dolar) dengan arah sekarang dan % seberapa sering arah itu benar
(1 hari / 1 minggu / 1 bulan; data `cloud/api/tren_stats.json` dari `research/tren_kedepan.py`), diurutkan dari yang
paling sering benar di atas tebakan dasar. Dihitung `cloud/api/_tren.py` dari candle harian Twelve Data (cache 3 jam
di baris Supabase `tren`, ±2 kredit) + CSV FRED. Status, bukan ramalan (riset bagian 16: tidak ada yang lolos).

Pengaturan: tidak ada environment variable tambahan. Di aplikasi ⚙️ → **Alamat cloud** = domain Vercel (mis.
`https://signal.domainkamu.com`). Kunci = topik ntfy (atau `CHAT_KEY`). Chat **tidak** membuka order dan jawabannya
bukan jaminan profit.

Aplikasi 3.2 menaruh blok **🎯 REKOMENDASI ENTRY** (tebal & besar) di atas setiap jawaban, dihitung di HP dari data
sinyal terbaru (dicek ulang saat bertanya) dan pengaturan modal/risiko: entry, SL, TP1, lot, WR & rata-rata R
historis (≈ uang per sinyal), untung di TP1 / rugi di SL, level TUTUP, dan status (masih bisa entry bila harga ±0,25R
dari entry; terlambat; TP1 sudah kena → jangan entry baru). Tanpa sinyal 💰 terbuka: "jangan entry dulu". Baris
"Kesimpulan" jawaban berita juga ditebalkan.

## Aplikasi: waktu notifikasi & tampilan (3.2)
- Cloud mengecek pasar tiap 10 menit (:02, :12, … :52). TP1/SL/SL+ terdeteksi di cek berikutnya (≤ 10 menit);
  sinyal TUTUP (close H1 menembus channel) dihitung saat candle H1 tutup → terkirim ±:02 jam berikutnya.
- Aplikasi ntfy (langganan topik yang sama persis, **tanpa** `-data`) menerima teks dalam hitungan detik. Aplikasi XAU
  Signal sendiri mengecek :05, :15, … memakai alarm tepat waktu (3.2; sebelumnya alarm biasa yang bisa ditunda Doze).
- Floating di kartu sinyal aktif dalam uang (lot × posisi yang masih terbuka), peringatan bila harga sudah melewati
  SL+/SL; ringkasan "Hari ini" dirinci per pair; ⚙️ **Pair yang saya ikuti** (XAU/USD, BTC/USD, Forex gap) menyaring
  sinyal, notifikasi, dan ringkasan tab Sinyal.
- Pesan TUTUP yang terlewat (HP offline > 12 jam, cache ntfy habis) dikenali dari heartbeat (`exits`): sinyal itu
  tidak lagi dihitung aktif dan riwayatnya ditandai SELESAI.
- Aplikasi 3.4: sinyal kembar (beberapa set, entry sama) memakai **satu** harga TUTUP = set paling lambat (tutup
  paling akhir; di data paling untung, `docs/RISET_DATA_EKSTERNAL.md` bagian 14). Notifikasi TUTUP aplikasi hanya
  untuk set itu. Cloud (setelah merge) juga hanya mengirim 1 teks ntfy per sinyal kembar: sinyal dari set pertama, TP1/SL+ dan TUTUP dari set paling lambat; data `-data` tetap per set. Statistik (3.5): PROFIT = TP1 kena, MINUS = SL /
  TUTUP sebelum TP1; uang tetap dari hasil nyata skema. Riwayat: 4 kartu + tombol "Load more".
- Aplikasi 3.6: APK ditandatangani kunci debug TETAP (`android/app/debug.keystore`), jadi update berikutnya tidak perlu
  uninstall dan riwayat tidak hilang (sekali lagi uninstall saat pindah dari ≤3.5). Notifikasi TUTUP menunggu semua
  pesan (termasuk heartbeat) terbaca: TUTUP set cepat tidak dianggap final selama set utama masih terbuka di cloud,
  walau data sinyalnya tidak ada di HP; posisi cloud tanpa data di HP tampil sebagai kartu Aktif dengan harga TUTUP.

## Filter BTC dari riset data eksternal

Dari `docs/RISET_DATA_EKSTERNAL.md` (hanya dua filter yang lolos kriteria ketat; untuk XAU tidak ada):
- **Funding ramai** (`cloud/api/_funding.py`): sinyal BTC 💰 BUY dilewati bila rata-rata funding Binance 24 jam
  berada di 10% tertinggi setahun, SELL dilewati bila di 10% terendah. Funding direkonstruksi dari file harian
  `premiumIndexKlines` data.binance.vision (api.binance.com diblokir dari server AS), cache di baris Supabase
  `funding`, diperbarui maks. 1x/jam. Uji nyata 2021–2026 dengan data terlambat 36 jam: +171R → +214R.
- **September**: sinyal BTC 💰 di bulan September (waktu New York) dilewati (11 dari 11 tahun rugi).
- Sinyal yang dilewati hanya dicatat (`skip` di tabel log), seperti sinyal tanpa 💰. Hasil `/api/tick` memuat
  `funding: {day, n, pct}` untuk memantau.

## Catatan
- Sinyal BUY/SELL hanya muncul saat breakout H1 (rata-rata ±1–2 kali per minggu). Status/harga
  dikirim setiap tick, jadi aplikasi tetap terlihat "hidup".
- Harga Twelve Data bisa selisih beberapa sen dari Exness; cek harga broker sebelum entry.
- SL virtual dicek setiap tick → saat entry manual **selalu pasang SL sungguhan di MT5** (auto order
  sudah otomatis memasang SL di server broker).
- Jangan jalankan bot PC (`python -m xau_bot run`) dan versi cloud ke topik yang sama bersamaan,
  kecuali ingin menerima dua sumber sinyal.
- Kalau `ok: false`, pesan `error` menjelaskan penyebabnya (mis. env belum diisi, API key salah).

## ⚡ kesempatan emas & peringkat (30 Sep 2026)

Setiap sinyal membawa `tier`: `zap` (⚡ Emas), `silver` (🥈), `bronze` (🥉), `biasa`, dan `vol_pct` (XAU:
persentil ATR14 60 hari). ⚡ = XAU konf+⭐ dengan `vol_pct` < 0,331, atau BTC ⭐. Untuk ⚡, `wr/avg_r` diganti
statistik kelompok ⚡ sendiri dan ditambah `wr07/avg_r07` (skema SL+ 0,7R). Sumber: `research/momen.py`,
`docs/MOMEN_PERANG.md`.

| Peringkat | XAU | BTC | Hasil (2012/2016–2021 / 5 tahun terakhir) |
|---|---|---|---|
| ⚡ | konf+⭐ & volatilitas rendah | ⭐ | XAU +0,95 / +0,53R, BTC +0,97 / +0,64R |
| 🥈 | – | konf+⭐ | +0,56 / +0,25R |
| 🥉 | konf+⭐; konf & volatilitas rendah | – | ±+0,1 / +0,17R |
| Biasa | konf | konf | XAU −0,13 / +0,13R, BTC +0,62 / ±0R |

Aplikasi 3.11: lot per peringkat (⚡ 1%, 🥈/🥉 0,5%, biasa setengahnya bila Modal diisi), SL+ otomatis (⚡ & BTC di
0,7R, XAU lainnya setelah TP1), modal otomatis, dan kurs bawaan Rp17.500.

Aplikasi 3.12: chip "Contoh pertanyaan" di tab Tanya diganti kartu **🎯 Persiapan berita** (GET `/api/chat` →
`persiapan`, `cloud/api/_persiapan.py`): per berita USD pekan ini, peluang hasil di bawah/sesuai/di atas konsensus,
% emas naik 1 jam per hasil, dan tebakan arah emas sebelum rilis. Riset & angka: `docs/PERSIAPAN_BERITA.md`.

Aplikasi 3.13: **⏱️ detik pertama setelah berita** (`docs/NEWS_DETIK.md`).
- Pengingat: alarm tepat **1 menit sebelum** tiap berita USD berdampak tinggi pekan ini (kalender GET `/api/chat`,
  diambil ulang poller tiap 6 jam; `NewsAlarm.kt`). Bisa dimatikan lewat sakelar di kartu 🎯. Isi notifikasi = angka
  uji detik pertama untuk grup berita itu (`persiapan.detik.<grup>.alarm`).
- Kartu 🎯: tiap berita menampilkan baris ⏱️ (besar gerak 5 detik pertama, spread, hasil "ikut lonjakan" manual dan
  pending Buy/Sell Stop, dan apakah ada cara yang lolos uji). Sumber: `cloud/api/detik.json` dari
  `python -m research.news_detik XAU` dan `... BTC`.
- Tab Tanya: pertanyaan berisi "detik", "straddle", "buy stop", "lonjakan", dan sejenisnya dijawab dari data yang sama.
- Informasi saja; aplikasi dan cloud **tidak** membuka order.

## Arsip berita otomatis ke GitHub (30 Sep 2026)

Setiap aplikasi dibuka (paling sering tiap 15 menit per HP), aplikasi memanggil `GET /api/chat`. Cloud lalu menyimpan
**semua berita pekan ini** (semua negara & dampak: judul, waktu, dampak, Cons, Prev, dan Act FRED untuk berita USD
utama setelah rilis) ke `data/berita/<tahun>/ff_<tanggal awal pekan>.json` di branch **`arsip-berita`**. Riset
membacanya lewat `research/news_data.load_calendar()` setelah
`git fetch origin arsip-berita && git checkout FETCH_HEAD -- data/berita`.

- **Token hanya di Vercel, tidak di APK** (APK bisa dibongkar). GitHub → Settings → Developer settings →
  Fine-grained tokens → *Generate*: Repository access = hanya `serfusion/Trading`, Permissions → *Contents: Read and
  write*. Salin ke Vercel → Environment Variables: **Key** `GITHUB_TOKEN`, **Value** = token (diawali `github_pat_`)
  → Redeploy. **Token hanya di `GITHUB_TOKEN`.** `ARSIP_REPO` dan `ARSIP_BRANCH` sebaiknya TIDAK dibuat (bawaan
  `serfusion/Trading` & `arsip-berita`); bila dibuat, isinya nama repo/branch, bukan token. Isi yang salah bentuk
  diabaikan otomatis, dan status di aplikasi tidak pernah menampilkan token (disensor `•••`).
- Bila token pernah tampil di layar/tangkapan layar/chat: GitHub → Fine-grained tokens → token itu → **Revoke**,
  buat token baru, ganti nilai `GITHUB_TOKEN`, Redeploy.
- **Tidak kena limit**: kalender ForexFactory di-cache di Supabase 10 menit untuk semua pembukaan aplikasi
  (baris `kalender`); GitHub hanya ditulis bila isi berubah, paling sering tiap 15 menit kecuali ada Act baru
  (baris `arsip`). Pemakaian ±beberapa commit per hari, jauh di bawah batas API GitHub (5.000 permintaan/jam).
- Commit arsip tidak memicu deploy: `cloud/vercel.json` → `ignoreCommand` hanya membangun ulang bila folder `cloud/`
  berubah. CI APK hanya berjalan bila `android/` berubah.
- Cek: respons `GET /api/chat` berisi `"arsip": {"status": "tersimpan" | "tidak berubah" | "ditunda ..." | "mati
  (GITHUB_TOKEN belum diisi di Vercel)" | "gagal: ..."}`. Arti "gagal": *GITHUB_TOKEN bukan token GitHub* = nilai
  bukan token (mis. tertukar dengan nama repo); *ditolak GitHub (HTTP 401)* = token salah/kedaluwarsa/dicabut;
  *tidak bisa membaca repo (HTTP 404)* = Repository access token tidak memuat repo ini atau Resource owner salah
  (repo milik organisasi `serfusion` → Resource owner harus `serfusion`); *HTTP 403* = izin Contents masih Read-only.

## 🎲 Kalshi di kartu 🎯 (30 Sep 2026, aplikasi 3.16)

`GET /api/chat` → `persiapan.berita[].kalshi` untuk CPI, core CPI, NFP, pengangguran, dan core PCE pekan ini: peluang
angka di atas / sama / di bawah konsensus dari pasar Kalshi (API publik, tanpa kunci), dan khusus CPI peluang emas naik
1 menit (`cloud/api/kalshi.json` dari `research/kalshi_uji.py`). Kalshi dibaca paling sering tiap 15 menit untuk semua
pengguna (baris Supabase `kalshi`); bila Kalshi gagal, data terakhir dipakai dan kartu tetap tampil tanpa baris 🎲.
Informasi saja, tanpa order. Detail & bukti: `docs/KALSHI.md`.
