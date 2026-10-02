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

## 5. Tanda hijau: Mars di MC oposisi Pluto di IC (2 Okt 2026)

Pengguna melingkari Mars 2°34' Leo (dekat MC 29°32' Cancer) dan Pluto R 3°06' Aquarius (dekat IC) → "NFP akan turun
seturun-turunnya". Posisi terverifikasi (oposisi ±0,5°, Mars ±3° dari MC). Uji `research/astrologi_nfp.py`
(`docs/eksternal/hasil_astrologi_nfp.txt`), NFP 2010–2025 (193 rilis dengan kejutan) + 2.051 rilis bintang 3:

| Pola | NFP di bawah konsensus | Emas naik 1 menit | Besar gerak emas |
|---|---|---|---|
| Tanpa pola (dasar) | 44–45% | 49% | 1,00x |
| Mars–Pluto oposisi (7 NFP) | 43% | 44% (79 rilis) | 0,99x |
| Mars–Pluto aspek keras (23 NFP) | 35% | 48% | 1,00x |
| Mars dekat MC/IC (27 NFP) | 41% | 48% | 0,98x |
| Pola persis chart ini: aspek keras + Mars di MC/IC (3 NFP: 2014-06, 2015-12, 2022-07) | **0%** (ketiganya di ATAS konsensus) | 47% | 1,07x |

Tidak ada yang bermakna (p terkecil 0,11; batas Bonferroni 0,003). Tiga kejadian pola yang persis sama malah
berakhir NFP di atas konsensus — sampel terlalu kecil untuk berarti apa pun. → Tidak dipakai. Catatan: NFP di BAWAH
konsensus ("turun") justru membuat emas NAIK (81%), bukan turun.

## 6. Arah emas 1, 2, 3 detik setelah rilis (aplikasi 3.18, 2 Okt 2026)

Permintaan pengguna: "tuliskan hasilnya dan persentase akan ke mana setelah 1 detik news release di APK".
`research/reaksi_menit.py` sekarang juga mencatat gerak mid tick t0−1 dtk → t0+1 / +2 / +3 dtk (Dukascopy 2010–2025,
dicek tick asli Exness 2015–2026). % searah = dari rilis yang harganya sudah bergerak di detik itu; ±$ = median besar
gerak. Format sel: Dukascopy / Exness.

| Hasil | Arah emas | 1 dtk | 2 dtk | 3 dtk | 1 mnt | n |
|---|---|---|---|---|---|---|
| NFP < perkiraan | naik | 57% / 59% (±$0,17) | 85% / 82% (±$2,68) | 91% / 88% (±$3,14) | 81% | 67 |
| NFP > perkiraan | turun | 51% / 57% (±$0,19) | 74% / 78% (±$2,26) | 76% / 81% (±$3,69) | 81% | 94 |
| Pengangguran < perkiraan | turun | 52% / 53% | 49% / 55% | 48% / 55% | 61% | 69 |
| CPI m/m < perkiraan | naik | 57% / 53% (±$0,14) | 81% / 74% (±$1,35) | 84% / 86% | 81% | 58 |
| CPI m/m > perkiraan | turun | 49% / 60% (±$0,14) | 77% / 74% (±$2,08) | 80% / 80% | 74% | 46 |
| Core CPI m/m > perkiraan | turun | 57% / 59% (±$0,19) | 95% / 84% (±$3,48) | 93% / 91% | 74% | 43 |
| Core PPI m/m < perkiraan | naik | 71% / 62% (±$0,10) | 88% / 84% (±$0,69) | 90% / 88% | 90% | 49 |
| Retail Sales m/m > perkiraan | turun | 81% / 83% (±$0,72) | 83% / 89% (±$1,03) | 81% / 89% | 79% | 75 |
| ISM Manufaktur < perkiraan | naik | 88% / 89% (±$1,22) | 82% / 89% | 88% / 89% | 71% | 17 |
| Klaim pengangguran > perkiraan | naik | 55% / 57% (±$0,10) | 64% / 64% | 65% / 67% | 75% | 93 |

Kesimpulan:
- **Detik pertama NFP/CPI/PPI: harga praktis belum bergerak** (±$0,10–0,20, sama dengan spread Exness $0,16–0,20) dan
  arahnya ≈ 50:50. **Hentakan muncul antara detik ke-1 dan ke-2** (±$1,3–2,7), lalu searah hasil 82–91% di detik
  ke-2–3, konsisten di kedua feed dan sejak Okt 2021. Retail Sales & ISM sudah bergerak di detik pertama.
- Ini menjelaskan hasil `docs/NEWS_PRA.md`: entry t0−1 lalu tutup 1 detik selalu rugi spread karena harga belum bergerak.
- Angka ini **RIWAYAT reaksi**, bukan sinyal: Act baru sampai di aplikasi beberapa detik–menit setelah rilis (BLS/FRED
  dicek tiap 30 detik di 10 menit pertama), jadi saat baris ✅ tampil, hentakan 1–3 detik sudah lewat.

Tampilan: kartu 🎯 → per hasil "⚡ Bila Act < 89K → arah emas" dengan sel 1 dtk / 2 dtk / 3 dtk / 1 mnt; setelah Act keluar
"✅ Act 45K < 89K → arah emas" dengan sel yang sama (`_persiapan.tahap`, `_hari_h.result`). Hijau/merah hanya bila ≥ 60%
di Dukascopy, arah sama ≥ 55% di Exness dan sejak Okt 2021, serta gerak median ≥ $0,30 (di bawah itu "belum gerak").
Aplikasi lama (≤ 3.17) membaca ringkasannya di teks kecil ("1 dtk belum gerak (±$0,17) • 2 dtk 85% NAIK …"). Tab Tanya
("detik pertama NFP") ikut menampilkan deretan ini. Kalender News: catatan di bawah Act juga memuatnya.

## 7. Act manual (aplikasi 3.19, 2 Okt 2026)

Kartu 🎯 → kolom "Act manual" (muncul 5 menit sebelum rilis): tempel baris investing.com (mis. `Nonfarm Payrolls (Sep)
45K 89K 162K`) atau ketik `45K` → Simpan. Cloud (`_aktual.parse_manual/save_manual`, POST /api/chat `{"manual": …}`)
mengambil angka pertama (jam & isi kurung dibuang) sebagai Act, menyimpannya di Supabase baris `aktual` (src
`manual`, menimpa Act otomatis), lalu ✅ hasil & sel 1/2/3 dtk + 1 mnt dihitung ulang dari Act itu. Kosongkan → Hapus →
kembali ke Act otomatis BLS/FRED. Persen berubah sesuai Act di bawah / sama / di atas perkiraan (besar kejutan belum
dibedakan).

## 8. Revisi otomatis Act manual & besar kejutan (aplikasi 3.20, 2 Okt 2026)

- **Revisi otomatis**: Act manual tetap dicek ke BLS/FRED. Bila angka resmi berbeda (mis. salah ketik 54K, resmi 45K),
  Act diganti angka resmi dan muncul "direvisi otomatis: isian manual 54K → resmi 45K"; bila sama: "cocok ✓". Berita
  yang tidak ada di BLS/FRED (mis. ISM) tidak bisa dicek otomatis.
- **Besar kejutan** (`research/reaksi_menit.besar_kecil`): BESAR = |Act − perkiraan| ≥ 1,5× median riwayat (NFP 84K).
  Kejutan besar umumnya lebih searah & geraknya lebih besar, sampel kecil (5–36 rilis):

| Hasil | kecil: emas 1 mnt | BESAR: emas 1 mnt | gerak 1 mnt kecil → besar |
|---|---|---|---|
| NFP < perkiraan | 78% naik | 86% naik | $4,2 → $6,7 |
| NFP > perkiraan | 79% turun | 83% turun | $4,0 → $5,4 |
| CPI m/m > perkiraan | 71% turun | 82% turun | $1,7 → $4,2 |
| Core CPI m/m > | 69% turun | 100% turun (n 9) | $2,9 → $6,5 |
| Core PPI m/m < | 84% naik | 96% naik | ≈ sama |
| Klaim > perkiraan | 70% naik | 86% naik | $0,9 → $2,0 |

  Retail Sales & sisi lain: hampir sama. Dipakai di ✅ hasil (sel 1 mnt & label "kejutan BESAR (109K ≥ 84K)").

## 9. NFP 2 Okt 2026: benar di menit awal, berbalik setelah 30 menit

Hasil: NFP **29K** (perkiraan 89K), pengangguran **4,2%** (4,1%), upah per jam **+0,1%** (0,3%); Agustus direvisi
162K → 133K — semua lemah untuk USD → emas diharapkan naik. Harga (Twelve Data 1 menit, UTC):

| | Sebelum (12:29) | +1 mnt | +2 mnt | Puncak | 15:18–15:20 |
|---|---|---|---|---|---|
| XAU | 4.182 | 4.200 (+$18) | 4.222 (+$40) | 4.226 (13:03) | 4.140 (−$42 dari awal) |
| BTC | 86.616 | 86.951 | 86.860 | 87.220 (12:31) | 85.366–85.500 |

Arah 1 detik–1 menit di kartu 🎯 BENAR. Angka itu hanya untuk menit awal. Riwayat (`research/nfp_berbalik.py`,
XAU M15 2012–2025, NFP di bawah perkiraan): searah 15 mnt 75% → 3 jam 70% → 6 jam 69%; **5 tahun terakhir 93% → 67%
→ 53%**, dan 5 dari 14 kenaikan 15 menit berbalik ke bawah harga awal dalam 3 jam (36%). Hari ini termasuk kelompok
itu. Penyebab pasti tidak bisa dipastikan dari data kita (setelahnya: bursa AS buka 13:30 UTC, pidato Fed Logan 14:00
UTC). Riset `docs/NEWS_MENIT.md`: ikut arah kejutan setelah menit pertama tidak untung.

Dipasang (aplikasi 3.22, permintaan pengguna "ya pasang"): sel **3 jam** & **6 jam** di baris ⚡/✅ (`reaksi_menit.jam_stats`
→ reaksi.json `jam`, `_persiapan.tahap`). Angka "53–69%" = semua tahun vs sejak Okt 2021 bila beda ≥ 10 poin.
Contoh: NFP < perkiraan → 1 mnt 81% NAIK • 3 jam 70% NAIK • 6 jam 53–69% naik ⚪; CPI > perkiraan → 1 mnt 74% TURUN
tetapi 3 jam 63% NAIK (berbalik).
