# Hari H berita: Act otomatis, perkiraan sebelum rilis, Polymarket & astrologi (1 Okt 2026)

Permintaan pengguna (dengan 4 gambar): (1) chart Astro-Seek "2 Oct 2026 08:30 Washington" — apa itu dan bisa
diterapkan? (2) kalender: Act 30 Sep–2 Okt tidak terisi otomatis; (3) URGENT: kartu persiapan "tidak berubah apa pun —
bagaimana saya tahu hasil pastinya hari H akan ke mana?"; (4) Polymarket (Fed Decision in October) — bisa dipakai
untuk setiap berita?

## 1. Act tidak terisi → diperbaiki

- Penyebab: Act diambil dari CSV publik FRED. Dari jaringan riset FRED menjawab < 1 detik, tetapi dari server Vercel
  tidak (arsip berita GitHub yang sekarang jalan mencatat "0 Act" pada 1 Okt). Data FRED sendiri sudah ada (Core PCE
  diperbarui 30 Sep 07:43 CT, GDP 07:59 CT).
- Perbaikan `cloud/api/_aktual.py`: Act diambil berlapis — **BLS API resmi** (tanpa kunci; CPI, NFP, pengangguran, upah
  per jam, PPI; angka muncul beberapa detik setelah 08:30 ET) → **FRED API** (bila env `FRED_API_KEY` diisi di Vercel;
  semua seri termasuk PCE, GDP, klaim) → CSV FRED. Act yang ditemukan disimpan di Supabase (baris `aktual`), dicoba
  ulang paling sering tiap 2 menit; bila kosong, alasannya tampil di aplikasi. Ditambah: Average Hourly Earnings,
  PCE headline, ADP, JOLTS.
- Uji langsung FRED API: Core PCE 30 Sep = **0,2%** (perkiraan 0,3%), Final GDP = **2,2%** (perkiraan 1,5%).
- **Langkah pengguna (disarankan)**: Vercel → Environment Variables → tambah `FRED_API_KEY` (kunci FRED yang sama
  dengan yang dipakai riset; gratis di fred.stlouisfed.org) → Redeploy. Tanpa itu BLS tetap mengisi CPI/NFP/
  pengangguran/PPI, tetapi PCE/GDP/klaim bergantung pada CSV FRED.

## 2. "Bagaimana tahu hasil pasti hari H?"

Jawaban jujur: **sebelum angka keluar tidak ada yang tahu pasti.** Yang bisa diketahui:

| Saat | Yang tampil di kartu 🎯 | Seberapa bisa dipercaya |
|---|---|---|
| Sebelum rilis | 🎯 Perkiraan hari H: peluang emas naik 1 menit = peluang pasar Kalshi/Polymarket × reaksi emas 1 menit per hasil; diperbarui tiap 15 menit, dengan "X jam lalu → sekarang" | CPI: sinyal ≥ 60% benar 86% (7 rilis, 24 jam sebelum) / 73% (11, 1 jam sebelum); core CPI 70% (10); NFP 33–58% (≈ lempar koin); pengangguran tidak pernah ≥ 60%. Entry t0−1 ikut sinyal: rugi. |
| Setelah rilis | ✅ Hasil: Act vs perkiraan → arah emas 1 menit | Searah kejutan 75–91% di setiap tahun 2013–2025 (`docs/KALSHI.md` bagian 6) |

- Reaksi emas 1 menit per judul & hasil (`research/reaksi_menit.py`, tick Dukascopy 2010–2025, dicek Exness): NFP di
  bawah perkiraan → naik 81% (sejak Okt 2021: 87%), di atas → naik 19%; CPI m/m di bawah → 81%, di atas → 26%; core
  PPI di bawah → 90%; klaim pengangguran di atas → naik 75%. Skenario & kesimpulan di kartu/kalender sekarang memakai
  angka 1 menit ini (sebelumnya 1 jam).
- Validasi perkiraan: `research/hari_h_uji.py` (walk-forward: reaksi hanya dari rilis sebelum tanggal uji) →
  `docs/eksternal/hasil_hari_h.txt`, `cloud/api/hari_h.json`. Hijau/merah hanya bila ≥ 60% dan uji judul itu
  ≥ 60% benar dengan ≥ 15 rilis — saat ini belum ada judul yang memenuhi, jadi semua perkiraan tampil abu-abu ⚪ dengan
  angka ujinya.

## 3. Polymarket

- Data: `python -m research.polymarket unduh|uji` → `data/research/eksternal/polymarket` (75 event 2024–2026; riwayat
  harga lama hanya bisa diambil dengan rentang ≤ 7 hari).
- Volume pasar data ekonomi **tipis** (NFP Sep 2026 $19,5 ribu, core CPI $20–60 ribu) dibanding Fed ($21,8 juta).
- Tebakan kejutan (24 jam sebelum, vs konsensus FF): NFP **41%** benar (17 rilis 2024–2025; Kalshi di rilis yang sama
  64%), pengangguran 67% (6 rilis, terlalu sedikit). CPI di Polymarket baru ada sejak 2026 (konsensus belum ada → belum
  diuji).
- Keputusan Fed: 9/9 sesuai konsensus, peluang Polymarket 1 jam sebelum 90–99% → akurat tetapi tidak memberi kejutan
  untuk diperdagangkan.
- Dipasang (info): Polymarket ikut dirata-rata dengan Kalshi di perkiraan hari H, dan baris 🏦 Keputusan Fed berikutnya
  (contoh 1 Okt: Okt 2026 tetap 74%, naik 25 bps 26%).

## 4. Chart astrologi (gambar 1)

- Itu chart kelahiran Astro-Seek untuk saat rilis NFP (2 Okt 2026 08:30 ET, Washington). Posisinya **benar secara
  astronomi** (dicek PyEphem: Matahari 9°20' Libra, Bulan 25°36' Gemini, ASC 25°30' Libra, dst.).
- Uji (`research/astrologi.py`, 2.051 rilis 2010–2026, 8 fitur astrologi finansial ditetapkan dulu): **tidak ada yang
  signifikan** setelah koreksi uji berganda (terkecil: Merkurius retrograde 43% naik vs dasar 49%, p terkoreksi 0,27,
  periode baru 46%). Fitur chart NFP besok masuk kelompok 45–51% naik. → **Tidak dipasang.**

## Aplikasi 3.17

Kartu 🎯: 🏦 Fed berikutnya; per berita baris besar 🎯 Perkiraan hari H (sebelum rilis) atau ✅ Hasil (setelah Act);
skenario 1 menit; ⏱️ detik pertama. Kalender: alasan bila Act belum terisi. Tab News memuat ulang otomatis tiap
10 menit (2 menit bila rilis ≤ 30 menit lagi atau Act belum keluar). Informasi saja, tanpa order.
