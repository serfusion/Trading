# Sinyal 24 Jam Tanpa PC (Vercel + Supabase + ntfy)

```
Supabase pg_cron (menit :02 & :32 tiap jam)
   └─ GET https://DOMAIN_KAMU/api/tick?key=RAHASIA   (fungsi Python di Vercel, folder cloud/)
        ├─ ambil candle H1 XAU/USD dari Twelve Data
        ├─ skema F-ensemble: 3 set Donchian H1 (40/15, 55/20, 80/30), 5 posisi/sinyal,
        │  TP1 1R untuk posisi #1, SL+ ke entry setelah TP1 (identik dengan bot)
        ├─ simpan posisi virtual & riwayat di tabel Supabase
        └─ kirim sinyal BUY/SELL/TUTUP + status → ntfy.sh → aplikasi XAU Signal
```

Simulasi di data asli Apr 2025 – Sep 2026 (tick tiap 30 menit): 343 sinyal (3 set), 48,7% untung,
**+65,2R** (`python -m research.cloud_check`). Hanya SINYAL — order tetap dibuka manual di MT5/HP.

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
2. Aplikasi XAU Signal → ⚙️ → Server `https://ntfy.sh`, Topik = `NTFY_TOPIC` → Simpan →
   kartu atas menampilkan harga & "Mode: SINYAL (cloud)".
3. Di Supabase: `select status_code, content from net._http_response order by created desc limit 5;`
   → status 200 setiap 30 menit.

## Catatan
- Sinyal BUY/SELL hanya muncul saat breakout H1 (rata-rata ±1–2 kali per minggu). Status/harga
  dikirim setiap tick, jadi aplikasi tetap terlihat "hidup".
- Harga Twelve Data bisa selisih beberapa sen dari Exness; cek harga broker sebelum entry.
- SL dicek setiap tick (30 menit) → **selalu pasang SL sungguhan di MT5** saat membuka posisi.
- Jangan jalankan bot PC (`python -m xau_bot run`) dan versi cloud ke topik yang sama bersamaan,
  kecuali ingin menerima dua sumber sinyal.
- Kalau `ok: false`, pesan `error` menjelaskan penyebabnya (mis. env belum diisi, API key salah).
