# 🔗 Keterkaitan & rangkuman semua berita (15 Okt 2026)

Permintaan pengguna (setelah PPI tertebak TURUN): "semua news tepat predict seperti ini, rangkumkan dari semua informasi yang
ada, buat secara keterkaitan; bila ada bug / tidak sesuai betulkan dengan seksama." Lalu: "54–65% itu bukan predict, sama saja
lempar koin." Dokumen ini merangkum SEMUA aturan berita yang dipakai aplikasi, keterkaitan antar berita yang diuji, batas
akurasi yang jujur, dan bug yang diperbaiki.

## 0. Hasil PPI 15 Okt (uji maju 1 rilis)
- Act (BLS, tercatat produksi 12:33 UTC): PPI 1,3% vs perkiraan 0,6%, PPI inti 0,7% vs 0,3%; Retail Sales 0,8% vs 0,3%
  (inti 0,9% vs 0,6%); klaim 199K = 199K → semua menguatkan USD.
- Emas (OKX XAUT 1 dtk, harga t−1 dtk $4.150,0): detik 1 −$9,60, detik 2 −$16,30, detik 5 −$25,40, menit 1 −$8,10.
- Aplikasi sebelum rilis: "PPI ▼ TURUN 58% ⚠️ ⚖️ tunggu ⚡LIVE" → arah BENAR (tetap 1 rilis; angka uji tetap 58%).
  ⚡LIVE detik 1 (−$9,60, searah tebakan): PPI bersamaan Retail detik 1 ≥ $0,30 → arah bertahan ≥ 80% s/d menit 1 → benar.

## 1. Batas jujur: kenapa sebelum rilis jarang > 70%
Emas hanya mengikuti ANGKA berita ±80% walau angkanya sudah pasti (plafon, research/rilis_gabung.py: NFP 82%, CPI inti 86%,
CPI 87%, PPI 78%, Retail 78%, ISM 86–88%, ADP 88%; pengangguran 51%, upah 56% karena kalah oleh NFP). Jadi:

    peluang emas benar ≈ 20% + 60% × peluang angka tertebak
    angka tertebak 50% → 50% • 65% → 59% • 76% (Kalshi CPI) → 66% • 83% → 70% • 100% → ±80%

Untuk emas ≥ 70% sebelum rilis, angka harus tertebak ≥ 83% — tidak ada sumber yang mencapainya secara konsisten (Kalshi CPI
76–78%, keterkaitan antar berita 60–70%). Angka ≥ 80% hanya muncul SETELAH rilis (⚡LIVE detik 1–2, bagian 5).

## 2. Rilis bersamaan → SATU arah (DIPASANG, `_persiapan.satukan`)
Dulu setelah CPI 14 Okt tab News menampilkan "CPI m/m 60% NAIK 🟢" sekaligus "Core CPI 69% TURUN 🔴" (emas turun).
`research/rilis_gabung.py` (FF 2010–2026 × tick, 1.650 rilis) → `cloud/api/rilis_gabung.json`. Saat kejutan BERLAWANAN:

| pasangan berlawanan | emas mengikuti | n | sebelum Okt 2021 / sejak |
|---|---|---|---|
| NFP vs pengangguran | NFP 76% | 66 | 84% / 59% |
| NFP vs upah per jam | NFP 70% | 54 | 82% / **50%** → ≈ 50:50 |
| upah vs pengangguran | upah 59% | 27 | 53% / 75% |
| Retail vs PPI | Retail 67% | 12 | 89% / 0% (3 rilis) |
| Retail inti vs PPI | Retail inti 58% | 12 | |
| CPI tahunan vs CPI inti | 54% | 13 | → ≈ 50:50 |
| PPI vs klaim | PPI 56% | 16 | lama 45% → ≈ 50:50 |

Aturan tampilan: judul yang "sama dengan perkiraan" ikut judul utama yang angkanya meleset (urutan `UTAMA_RILIS`: NFP > upah >
pengangguran; CPI inti > CPI > tahunan; Retail > PPI; klaim terakhir). Kejutan berlawanan → angka pasangan di atas; < 55% atau
LAMA/BARU < 55% (≥ 5 rilis) atau < 10 rilis → "≈ 50:50". Berlaku di kalender tab News (`arah`) & kartu 🎯 (`hasil_rilis`).

## 3. Keterkaitan antar berita (`research/keterkaitan.py`, 263 pasangan)
Untuk setiap rilis B: kejutan berita A TERAKHIR sebelum B (≤ 35 hari). Hubungan dipilih dari LAMA, diuji di BARU + uji acak
200× (geser melingkar): lolos 6 vs kebetulan 0,3 (p < 0,005) → keterkaitan ANGKA memang ada, tetapi arah EMAS lemah:

| A → B | angka (walk-forward) | emas menit 1 (walk-forward) |
|---|---|---|
| CPI → CPI inti bulan berikutnya (searah) | 70% | 65% (lemah) |
| CPI → PPI bulan sama (searah) | 71% | 57% |
| CPI → Retail inti (searah, Retail nominal ikut harga) | 60% | 57% |
| GDP awal → Retail / Retail inti (searah) | 64–65% | 57–59% |
| keyakinan konsumen CB → CPI inti (berbalik) | 64% | 58% |
| PPI → GDP awal (searah) | 59% | **35%** (emas tidak ikut) |

Kesimpulan: 54–65% ≈ lempar koin (pengguna benar) → TIDAK dipakai sebagai arah utama. Aplikasi hanya menampilkannya sebagai
info di detail kartu ("🔗 Keterkaitan berita sebelumnya"); tautan yang emasnya < 52% atau LAMA/BARU < 50% ditulis "arah emas
tidak ikut (≈ 50:50)". Memori hasil terakhir semua berita: baris Supabase `hasil_rilis` (tiap GET & tiap jam lewat `_rekam`).
Sebelumnya juga sudah diuji (tidak lolos): CPI+PPI → PCE (TRANS, riset_inflasi), ADP/klaim/ISM/Indeed → NFP, sentimen orang,
pernyataan Fed/Trump, ±40 ribu aturan gabungan (aturan_pra 53%).

## 4. Rangkuman per berita — yang dipakai aplikasi (per arah tebakan, LAMA < Okt 2021 / BARU)
| berita | sebelum rilis (arah utama) | setelah rilis ⚡LIVE (detik 2 ≥ $0,50 → bertahan s/d detik 5 • menit 1) |
|---|---|---|
| CPI | konsensus indeks/Kalshi tersaring: detik 2 68% (61 rilis; 54/81; 2024+ 95%, NAIK 18/19); TURUN saat tren naik ⚠️ 62%; YOYc NAIK ⚠️ 55% | 92% • 82% (85 rilis) |
| PPI | minyak turun → NAIK 72,5% (40; 62/84) ✅; minyak naik → TURUN 55% ⚠️; + CPI inti bulan sama per arah (searah NAIK 7/7, TURUN 7/12; berlawanan → ≈ 50:50) | 91% • 84% (69); bersamaan Retail: detik 1 ≥ $0,30 → ≥ 80% s/d menit 1 |
| ISM Jasa | kejutan lalu berbalik: TURUN 69% (45) ✅ / NAIK 60% (62) | 98% • 96% (ISM, 160) |
| NFP | kalender survei BLS: NAIK 63% (60) / TURUN 57% (104) ⚠️ | 96% • 94% (93) |
| Fed | ≈ 50:50 (model 1 jam 60%; Polymarket = info) | 98% • 78% (45) — menit 1 lemah |
| JOLTS | ≈ 50:50 (berbalik NAIK 41% → disembunyikan) | 100% • 94% (18) |
| Retail, PCE, GDP, klaim, ADP, ISM Manufaktur, konsumen | ≈ 50:50 (tren 4 jam saja 55–56% ⚠️) | Retail 98%, ADP 96%, klaim 96%, PCE 89%, GDP 86% |
| tren emas 4 jam (semua) | searah petunjuk: NAIK 73% / TURUN 58%; berlawanan: NAIK 53% / TURUN 45% → ≈ 50:50 | — |
Masuk SETELAH detik 2 (telat + spread) rata-rata rugi untuk kebanyakan berita kecuali gerak ≥ $2 (live_tingkat "kejar").

## 5. ⚡LIVE: tebakan sebelum rilis × gerak detik 1/2 (DIPASANG, aplikasi 4.44)
`research/live_kurva.py` (tick Exness 2016–2026; tebakan = aturan aplikasi: CPI IDX|K, PPI minyak, lainnya petunjuk teruji):

| keadaan | detik 1 ≥ $0,30 | detik 2 ≥ $0,50 |
|---|---|---|
| semua berita, gerak SEARAH tebakan | **83%** (83; lama 85 / baru 80) | **90%** (125) |
| semua berita, BERLAWANAN tebakan | 53% (60) ≈ lempar koin | 71% (63) |
| PPI searah / berlawanan | 82% (11) / 38% (13) | 87% (31) / 56% (18) |
| CPI searah / berlawanan | 67% (21) / 46% (24) | 82% (45) / 71% (21) |
(angka = TERENDAH di setiap detik s/d detik 60). Cloud `pra_satu.lanjut.kurva_searah/kurva_lawan` (kelompok berita bila ≥ 10
rilis, selain itu semua berita); aplikasi 4.44: "searah tebakan → s/d menit 1 ≥ 83% ✅" atau "BERLAWANAN tebakan → ≈ lempar
koin, tunggu detik 2".

## 6. Bug yang diperbaiki 15 Okt malam (simulasi menyeluruh `tests/test_cloud_simulasi.py`)
1. PPI bisa tampil "NAIK 43%" / "TURUN 44%" (arah yang lebih sering salah) saat minyak & CPI inti berlawanan → kini ≈ 50:50 +
   alasan (`_ppi_wti.status_sel`, aturan audit); sel 9/10 rilis tidak lagi ✅ (belum terbukti).
2. Kesimpulan setelah rilis bertentangan dalam satu rilis (bagian 2).
3. Hari NFP: baris XAU "≈50%" (petunjuk & tren berlawanan) tetapi kartu "NFP: emas turun 57%" → `tandai` mengikuti daftar.
4. Kartu berdampak SEDANG (klaim pekan ini) tertahan "menunggu Act…" → Act juga untuk kartu Medium.
5. ISM Manufaktur, keyakinan konsumen CB, Michigan, Empire, Philly, barang tahan lama: tanpa sumber Act → Nasdaq (`_aktual`).
6. Poin sentimen bisa galat bila data cache sebagian → seluruh blok hilang (`_sentimen.poin`).
7. Jadwal resmi FRED baru s/d 23 Des → setelahnya baris XAU kosong → tampil berita terdekat yang diketahui.
8. ⓘ peringkat memuat aturan berita yang dipakai sekarang (bukan hanya model 1 jam lama).
Simulasi: kode cloud ASLI diputar ±100 titik waktu Okt–Nov (sebelum/sesudah rilis, ganti pekan, jam musim dingin 1 Nov)
dengan jaringan mati + tiruan; cek galat tersembunyi, satu arah per rilis, arah ≥ 50%, jam WIB, Act, memori rantai hasil.
