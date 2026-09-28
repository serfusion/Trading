# Sinyal 24 Jam Tanpa PC (Vercel + Supabase + ntfy)

```
Supabase pg_cron (menit :02 & :32 tiap jam)
   └─ GET https://DOMAIN_KAMU/api/tick?key=RAHASIA   (fungsi Python di Vercel, folder cloud/)
        ├─ ambil candle H1 XAU/USD dari Twelve Data
        ├─ skema F-ensemble: 3 set Donchian H1 (40/15, 55/20, 80/30), 5 posisi/sinyal,
        │  TP1 1R untuk posisi #1, SL+ ke entry setelah TP1 (identik dengan bot)
        ├─ simpan posisi virtual & riwayat di tabel Supabase
        ├─ kirim sinyal BUY/SELL/TUTUP + status → ntfy.sh → aplikasi Gold XAU/USD Indicator
        └─ (opsional, Langkah 6) auto order → MetaApi → akun MT5 Exness  ← dikontrol dari tab "Auto" di HP
```

**Tanda ⭐**: semua sinyal dikirim; sinyal yang searah tren D1 (close D1 kemarin vs EMA50 D1) dan
menembus high/low 20 candle H4 sebelumnya diberi tanda ⭐ (`research/filters.py`).

**Badge di setiap sinyal** (dari data historis multi-tahun, `research/badge_stats.py` & `research/gap_years.py`):
⭐ = win rate (⭐⭐⭐ ≥75%, ⭐⭐ ≥60%, ⭐ ≥48%), 💸 = profit rata-rata per sinyal (💸💸💸 ≥+0,25R, 💸💸 ≥+0,12R,
💸 ≥+0,05R). Sinyal juga membawa `wr`, `avg_r`, `n_hist`, `period`.

| Sinyal | WR | Profit/sinyal | Badge |
|---|---|---|---|
| XAU konfluensi + ⭐ (EMA50/200, Supertrend, momentum 60 hari + tren D1 & H4) | 49% | +0,31R | ⭐💸💸💸 |
| XAU konfluensi saja | 48% | +0,09R | ⭐💸 |
| XAU ⭐ saja / biasa | 43–44% | ±0 | – |
| Gap pekan AUD/USD | 90% | +0,25R | ⭐⭐⭐💸💸💸 |
| Gap pekan USD/JPY | 82% | +0,26R | ⭐⭐⭐💸💸💸 |
| Gap pekan EUR/JPY | 84% | +0,14R | ⭐⭐⭐💸💸 |
| Gap pekan AUD/JPY | 86% | +0,10R | ⭐⭐⭐💸 |
| Gap pekan EUR/CHF | 74% | +0,13R | ⭐⭐💸💸 |

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
2. Aplikasi Gold XAU/USD Indicator → ⚙️ → Server `https://ntfy.sh`, Topik = `NTFY_TOPIC` → Simpan →
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

## Catatan
- Sinyal BUY/SELL hanya muncul saat breakout H1 (rata-rata ±1–2 kali per minggu). Status/harga
  dikirim setiap tick, jadi aplikasi tetap terlihat "hidup".
- Harga Twelve Data bisa selisih beberapa sen dari Exness; cek harga broker sebelum entry.
- SL virtual dicek setiap tick → saat entry manual **selalu pasang SL sungguhan di MT5** (auto order
  sudah otomatis memasang SL di server broker).
- Jangan jalankan bot PC (`python -m xau_bot run`) dan versi cloud ke topik yang sama bersamaan,
  kecuali ingin menerima dua sumber sinyal.
- Kalau `ok: false`, pesan `error` menjelaskan penyebabnya (mis. env belum diisi, API key salah).
