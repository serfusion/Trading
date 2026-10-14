# 👥 Sentimen orang sedunia: lebih banyak BUY atau SELL? (14 Okt 2026)

Permintaan pengguna: *"cari informasi kebanyakan orang di seluruh dunia bereaksi apa? buy atau sell, ambil sampel
sebanyak-banyaknya (survei, kepuasan konsumen, percakapan, dll) … di bawah XAU selalu tampil persentase, hide/show
dipersingkat poin-poin saja: tutup kertas sekian persen, konsensus, survei orang, dll"*.

Kode: `research/sentimen_orang.py` (pengumpul) + `research/sentimen_orang_uji.py` (uji) → `docs/eksternal/hasil_sentimen_orang.txt`,
`cloud/api/sentimen.json`. Cloud: `cloud/api/_sentimen.py`, poin di `cloud/api/_pra_aset.satu`. Data: `data/research/eksternal/sentimen/`.

## 1. Sumber yang dicoba

| Sumber | Isi | Riwayat | Hasil akses |
|---|---|---|---|
| **Kitco Weekly Gold Survey** | Main Street = voting online orang umum (naik/turun/datar pekan depan) + Wall Street = analis | Mei 2022 – Okt 2026, ±155 pekan, ±41 ribu suara | ✅ GraphQL `cms.prod.kitco.com` + artikel (arsip sebelum 2022 tidak ada di CMS) |
| **FXSSI current ratio** | % posisi BUY XAUUSD ritel di ±8–10 broker (Myfxbook, OANDA, Dukascopy, FXBlue, XM, Insta, Amarkets, …) | hanya potret kini (riwayat berbayar) | ✅ → mulai diarsip tiap jam (`arsip_data.sentimen`) |
| **CFTC COT trader kecil** | posisi long/short "non-reportable" (ritel) futures emas COMEX | 2006–2026, 1.061 pekan | ✅ publicreporting.cftc.gov |
| **Google Trends** | pencarian "buy gold" vs "sell gold" vs "gold price" seluruh dunia | 2004–2026 mingguan | ✅ pytrends |
| **StockTwits** | pesan trader berlabel Bullish/Bearish (GLD, XAUUSD, …) | API publik ±30 pesan/permintaan → beberapa bulan terakhir saja | ✅ (lambat) |
| **Wikipedia** | kunjungan harian artikel emas (perhatian publik) | Jul 2015 – kini | ✅ |
| **Survei konsumen** | UMich sentimen, UMich ekspektasi inflasi, OECD keyakinan konsumen AS | 2004–2026 bulanan | ✅ FRED |
| Myfxbook community outlook | % long/short | — | ❌ API butuh login (sesi akun) |
| IG client sentiment / DailyFX | % long/short | — | ❌ butuh akun API / 403 |
| OANDA position book | order & posisi | — | ❌ butuh token akun |
| Dukascopy SWFX | indeks sentimen | hanya 1–5 hari lalu | ⚠️ (sudah termasuk di FXSSI) |
| AAII, CNN Fear & Greed, Reddit, investing.com, ForexFactory trades | — | — | ❌ 403/418 dari jaringan sesi |
| FXCM SSI | posisi ritel | sampel gratis hanya Jan 2018 | ❌ terlalu pendek |

## 2. Hasil uji (tutup kertas, per arah, LAMA < Okt 2021 vs BARU, pembanding selalu-NAIK)

Aturan penilaian ditetapkan sebelum melihat hasil: keputusan saat data terbit; target arah close emas k hari kerja sesudahnya;
lolos hanya bila tutup kertas > selalu-NAIK, kedua paruh searah, dan p < 0,05.

| Sumber & aturan | Target | n | Benar | Tebak NAIK / TURUN | Selalu-NAIK | LAMA / BARU | Putusan |
|---|---|---|---|---|---|---|---|
| Kitco Main Street: ikut mayoritas | 1 pekan | 154 | 53% | 54% (150) / 25% (4) | 55% | – / semua BARU | ❌ = selalu-NAIK (mayoritas NAIK 97% pekan) |
| Kitco Main Street: LAWAN mayoritas | 1 pekan | 154 | 47% | – / 46% (150) | 55% | – | ❌ |
| Kitco Main Street ekstrem (P80) ikut | 1 hari | 73 | 63% | 67% / 56% | 59% | paruh 54 / 72% | ❌ p 0,28 |
| Kitco Wall Street (analis) ikut | 1 pekan | 149 | 48% | 52% / 37% | 55% | – | ❌ analis lebih buruk dari selalu-NAIK |
| Kitco tutup kertas (ikut/lawan dipilih dari tahun lalu) | 1 pekan | 132 | 43% | – | 57% | 2024 49 / 2025 33 / 2026 49% | ❌ |
| StockTwits GLD: mayoritas bull → naik (Mar–Okt 2026, 15 rb pesan, 72% bull) | 1 hari | 181 | 48% | 47% / 61% | 46% | – | ❌ |
| StockTwits lonjakan bull (z ≥ 1) → TURUN | 1 pekan | 60 | 58% | 52% / 67% | 43% | – | ❌ p 0,45, sampel 7 bulan |
| Wikipedia perhatian melonjak (z ≥ 2) → balik arah | 1 hari | 128 | 56% | 57% / 54% | 51% | 54 / 57% | ❌ p 0,17 |
| COT trader kecil ekstrem (z ±1,5) → LAWAN | 1 pekan | 241 | 54% | 55% / 52% | 52% | 55 / 48% | ❌ |
| COT trader kecil ekstrem → LAWAN | **1 bulan** | 241 | **59%** | 58% / 60% | 49% | **61% / 53%** (BARU < selalu-NAIK 57%) | ❌ hanya LAMA (p 0,04); tutup kertas 58% vs 46% |
| COT managed money ekstrem → LAWAN | 1 bulan | 253 | 56% | 58% / 53% | 54% | 56 / 56% | ❌ p 0,29 |
| Google Trends 'buy gold' melonjak → LAWAN | 1 pekan | 106 | 56% | 58% / 54% | 52% | 56 / 53% (n 15) | ❌ p 0,25 |
| Google Trends 'gold price' melonjak → balik arah | 1 bulan | 85 | 52% | 74% / 40% | 65% | 59 / 33% | ❌ |
| UMich sentimen konsumen turun → emas naik | 1 bulan | 220 | 54% | 56% / 53% | 51% | 54 / 54% (BARU < selalu-NAIK 58%) | ❌ p 0,23 |
| OECD keyakinan konsumen turun → emas naik | 1 bulan | 191 | 55% | 54% / 55% | 49% | 56 / 48% | ❌ p 0,17 |
| UMich ekspektasi inflasi | 1 bulan | 184 | 49% | 52% / 45% | 53% | 49 / 50% | ❌ |

Rincian lengkap: `docs/eksternal/hasil_sentimen_orang.txt`. COT memakai tanggal terbit asli (termasuk keterlambatan saat
shutdown pemerintah 2013, 2018–19, 2025).

## 3. Kesimpulan jujur

- **Kebanyakan orang hampir SELALU memilih BUY emas**: Kitco Main Street mayoritas NAIK di ±97% pekan, ritel 8 broker 61–78%
  posisi BUY (kini ±70%), trader kecil COT ±76% long, pencarian "buy gold" ±79% vs "sell gold", StockTwits ±71% bullish.
  Karena itu "ikut orang" = "selalu NAIK" — tidak menambah informasi di atas pembanding selalu-NAIK.
- **Melawan orang (kontrarian)** hanya bekerja di periode LAMA (COT trader kecil ekstrem → emas berbalik 1 bulan ±61%), lalu gagal
  sejak Okt 2021 (pasar emas naik terus; orang yang BUY justru benar).
- Survei konsumen (kepuasan/keyakinan konsumen) dan perhatian publik (Wikipedia, Google) 48–56% → setara lempar koin.
- **Tidak ada sumber sentimen orang yang menambah ketepatan arah emas** → tidak dipakai mengubah arah/persen. Ditampilkan sebagai
  **info** (poin 👥) karena diminta pengguna, dengan label "diuji: tidak menambah ketepatan".

## 4. Yang dipasang (cloud, tanpa ubah APK)

Baris di bawah XAU (`persiapan.pra_satu`) **selalu memuat persen**: berita dengan petunjuk teruji → arah + persen; tanpa
petunjuk → "⚪ ≈50% (arah muncul ≤ 6 jam sebelum rilis)". Ketuk baris = buka/tutup **poin-poin ringkas** (`pra_satu.poin`,
`bukti` = "• …" per baris):

```
CPI ▲ NAIK 54% (detik 2) ⚠️ • 8 jam lagi
• ⚠️ Lemah: 54% (detik 2) • dulu 33% • sejak Okt 2021 80% • dasar: pasar Kalshi headline
• Lemah karena inti m/m jarang di bawah perkiraan
• 📊 Konsensus (11:16 WIB): m/m 0,6% • y/y 3,6% • inti 0,2% / 2,5%
• 🎲 Kalshi atas/bawah perkiraan: m/m 18/34% • inti 36/22% • y/y 45/12%
• 🧮 Tersirat vs konsensus: y/y 3,71 vs 3,6 → condong DI ATAS • inti y/y 2,43 vs 2,5 → inti jarang DI BAWAH (3/33)
• 👥 Orang: Kitco 206 suara naik 45% / turun 37% • ritel 8 broker BUY 70% • trader kecil COT long 76% → info (diuji: tidak menambah ketepatan)
• Setelah rilis: emas gerak ≥ $0,50 di detik 2 → ikuti arahnya s/d 5 mnt (76%)
```

`_sentimen.py`: Kitco terbaru (kategori emas → artikel), FXSSI (1 jam), COT (12 jam); cache baris Supabase `sentimen`; sumber gagal →
nilai lama; env `SENTIMEN=0` mematikan. Berita lain tanpa 🔄 data terbaru memakai "📊 Konsensus: <forecast> • sebelumnya <previous>"
dari kalender.

Uji maju: `research/arsip_data.py` menyimpan FXSSI per broker tiap jam (`sentimen/fxssi.jsonl` di branch `arsip-data`) + Kitco &
COT harian → setelah ±6–12 bulan posisi ritel bisa diuji tutup kertas (riwayat gratis tidak tersedia).

## 5. Poin "✅ Hampir selalu benar" (14 Okt 2026, permintaan "tambahkan uji tutup kertas yg hampir selalu benar")

Sebelum rilis TIDAK ADA aturan yang hampir selalu benar (terbaik 63–76%). Yang ≥ 85% di periode LAMA **dan** BARU hanya aturan
SETELAH rilis (`pra_aset.json["lanjut"]`, tick Exness 2015–2026): bila emas sudah bergerak ≥ $0,50 di detik 2, arahnya masih sama
di detik 10 — CPI 89% (dulu 97% • sejak Okt 2021 85%, n 85), NFP 95%, semua berita 92% (96/90%, n 839). Poin ini tampil
(`_pra_aset.hampir_pasti`) hanya bila LAMA & BARU ≥ 85% (PPI BARU 84% → tidak tampil). Bukan tebakan sebelum rilis: ia
memberitahu kapan arah yang SUDAH terlihat hampir pasti berlanjut.

