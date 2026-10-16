# 🧩 Dokumen "ARSITEKTUR konfluensi_85" — diuji dengan data asli & diterapkan (16 Okt 2026)

Permintaan pengguna: *"tolong kamu baca dan terapkan semuanya secara menyeluruh supaya bisa 75 persen winrate"* (unggahan
`ARSITEKTUR-konfluensi_85.md`: 5 metode, 6 rezim, klaim win rate 77–88%).

## Ringkasan

- **Klaim dokumen tidak terbukti.** Kelima metode dihitung dari data asli: 1.627 rilis bertick Exness 2016–2026. Aturan rezim
  dokumen dipakai **apa adanya** (ambang 0,6 / 0,7 / 65%, bobot 1,1, tidak disetel ke data). Hasilnya:
  - tak satu pun dari 6 rezim mencapai 75% dengan sampel yang cukup;
  - rezim yang sering muncul (MENENGAH) hanya benar 48–55% di detik 3;
  - rezim "PENUH" dan "SAPUAN" baru muncul 1–10 kali dalam 10 tahun;
  - semua rezim digabung: 174 rilis, benar 51,7%. Sebelum Okt 2021 49,5%, sejak itu 55%.
- **Angka JSON dokumen bukan hasil hitungan.** Contohnya 85,7%, Wilson 78,2, p 0,004, dan tabel per detik.
  - Skrip riset dokumen hanya berisi fungsi dan tidak memuat data apa pun.
  - Modul cloud dokumen membaca kata kunci ("hot", "turun", "naik") dari teks JSON, lalu menimpa arah.
- **Yang dipasang:**
  - kelima metode dihitung **live** di cloud dan tampil di detail baris XAU (🧩 + 🧪) dengan **angka uji asli**;
  - gerbang timpa dokumen (bagian 4) dipasang apa adanya, tetapi memakai status hasil uji;
  - karena tidak ada rezim yang teruji, **arah dan persen utama tidak berubah**.
- **Satu-satunya metode yang bekerja adalah metode 3, petunjuk teruji** (60,5%, p 0,0004). Metode ini sudah dipakai
  aplikasi.
- **Metode 4 (sapuan likuiditas) justru terbalik**: benar 43%, karena emas cenderung melanjutkan arah, bukan menyapu stop.

## Cara uji (standar dokumen sendiri + standar repo)

- **Tanpa look-ahead.** Semua vektor dihitung dari data ≤ t0−1 dtk:
  - kalender & MAD dari rilis sebelumnya;
  - Kalshi 1 jam sebelum tutup;
  - candle 15 mnt yang sudah tutup.
- **Target:** arah harga tengah tick Exness di detik 1/2/3/5/10/30/60 dibanding t0−1 dtk. Harga yang tidak bergerak dihitung
  salah.
- **Untung bersih:** posisi masuk t−1 searah rezim, BUY di ask / SELL di bid, spread asli saat berita.
- **Pembanding:** LAMA (< Okt 2021) vs BARU, dan selalu-NAIK (emas naik di detik 3 pada 49,4% rilis).
- **Statistik:**
  - Wilson lower bound (z 1,28, seperti dokumen);
  - permutasi 5.000× terhadap acak 50% dan terhadap rilis acak dengan arah yang sama (mengontrol tren emas).
- **Syarat "teruji"** (dipakai gerbang cloud): benar detik 3 ≥ 75%, Wilson ≥ 70%, p ≤ 0,01, dan LAMA & BARU masing-masing
  ≥ 5 rilis dan ≥ 60%.

## Klaim dokumen vs data asli

**Varian A** (definisi dokumen: ≥ 2 berita dampak tinggi di jam yang sama = "rilis bersamaan"):

| Rezim | Klaim | n (LAMA/BARU) | Benar detik 3 (LAMA/BARU) | Detik 1 • 10 • 60 | Untung bersih 1 mnt | Wilson | p acak rilis | Status |
|---|---|---|---|---|---|---|---|---|
| PENUH NAIK | 87,5% | 1 (1/0) | 100% | 0 • 100 • 100 | 100% (+$0,47/oz) | 37,8 | 0,49 | tidak lolos |
| PENUH TURUN | 86,7% | 2 (2/0) | 0% | 0 • 50 • 50 | 50% (−$0,64) | 0 | 1,0 | tidak lolos |
| SAPUAN PUCUK (turun → V naik) | 85,7% | 1 (0/1) | 0% | 100 • 0 • 0 | 0% (−$22,18) | 0 | 1,0 | tidak lolos |
| SAPUAN DASAR (naik → V turun) | 85,0% | 5 (2/3) | 80% (100/67) | 60 • 80 • 100 | 100% (+$6,37) | 51,4 | 0,18 | tidak lolos |
| MENENGAH NAIK | 77,8% | 74 (42/32) | 55% (55/56) | 42 • 51 • 51 | 47% (+$0,12) | 48,0 | 0,16 | tidak lolos |
| MENENGAH TURUN | 76,9% | 91 (50/41) | 48% (44/54) | 54 • 48 • 48 | 43% (−$0,03) | 41,7 | 0,69 | tidak lolos |

**Varian B** (≥ 2 *kelompok* berita berbeda, misalnya PPI + Retail Sales):

| Rezim | Klaim | n (LAMA/BARU) | Benar detik 3 (LAMA/BARU) | Detik 1 • 10 • 60 | Untung bersih 1 mnt | Wilson | p acak rilis | Status |
|---|---|---|---|---|---|---|---|---|
| PENUH NAIK | 87,5% | 10 (2/8) | 80% (50/88) | 40 • 80 • 70 | 70% (+$2,18) | 60,2 | 0,053 | belum terbukti |
| PENUH TURUN | 86,7% | 5 (3/2) | 20% (0/50) | 40 • 20 • 60 | 60% (−$0,18) | 6,2 | 0,97 | tidak lolos |
| SAPUAN PUCUK | 85,7% | 0 | – | – | – | – | – | tidak pernah terjadi |
| SAPUAN DASAR | 85,0% | 1 (0/1) | 100% | 0 • 100 • 100 | 100% (+$10,06) | 37,8 | 0,49 | tidak lolos |
| MENENGAH NAIK | 77,8% | 66 (41/25) | 52% (56/44) | 41 • 47 • 50 | 45% (−$0,11) | 43,7 | 0,40 | tidak lolos |
| MENENGAH TURUN | 76,9% | 88 (49/39) | 49% (45/54) | 53 • 50 • 48 | 42% (−$0,03) | 42,1 | 0,65 | tidak lolos |

Varian B "PENUH NAIK" adalah yang terdekat (80%), tetapi:
- hanya 10 rilis dan sebelum Okt 2021 hanya 50% (2 rilis);
- p 0,053 dan Wilson 60;
- kebalikannya, "PENUH TURUN", benar 20%;
- dengan kata lain, ini searah tren naik emas 2024–2026, bukan pola konsisten.

**Klaim "semakin banyak metode searah, semakin akurat"** (dokumen: 1–2 metode 51–58%, 3 metode 72–76%, 4 metode 85–89%):

| Metode searah | NAIK: n, benar detik 3 (LAMA/BARU) | TURUN: n, benar detik 3 (LAMA/BARU) |
|---|---|---|
| 1 | 348: 44% (42/47) | 436: 47% (43/51) |
| 2 | 64: 52% (56/44) | 85: 49% (46/54) |
| 3 | 8: 75% (50/83) | 7: 29% (0/67) |
| 4 | 3: 100% (–/100) | 0 |

Ember 3–4 metode NAIK hanya 11 rilis dalam 10 tahun, dan arah TURUN dengan 3 metode justru 29%, jadi tidak ada kenaikan yang
konsisten.

**Tiap metode sendirian** (vektor ≠ 0):

| Metode | n | Benar detik 3 (LAMA/BARU) | 1 mnt | Untung bersih 1 mnt | p acak rilis |
|---|---|---|---|---|---|
| 1 Palang perkiraan (Z ≥ 0,6) | 425 | 49,6% (48,1/51,5) | 49,4% | 46% (−$0,42) | 0,58 |
| 2 Kalshi ≥ 65% | 42 | 54,8% (–/54,8) | 69,0% | 64% (+$1,69) | 0,31 |
| 3 Petunjuk teruji (sudah di aplikasi) | 281 | **60,5%** (58,2/62,9) | 61,9% | 58% (+$0,48) | **0,0004** |
| 4 Sapuan (D ≥ 0,7 → lawan) | 913 | 43,2% (40,9/45,7) | 48,0% | 39% (−$0,35) | 1,0 |
| 5 Rilis bersamaan | — (penyaring rezim, bukan arah) | | | | |

## Kesalahan dokumen (mengapa angkanya tidak bisa dipakai)

1. **Angka tanpa kode.** `konfluensi_85.json` dokumen (n, persen per detik, Wilson, p) tidak dihasilkan oleh skrip mana pun.
   Skrip riset dokumen tidak memuat data, dan tesnya hanya meng-assert angka karangan itu (`ps["persen"] == 85.7`).
2. **MAD karangan.** Dokumen memakai MAD tetap (PPI 0,15), padahal MAD asli 12 rilis PPI terakhir adalah 0,4. Akibatnya pada
   contoh PPI 15 Okt (0,6% vs 0,4%), Z = 0,5, bukan 1,33 → palang **netral**, dan rezim "SAPUAN PUCUK" tidak terbentuk.
3. **Modul cloud membaca kata, bukan angka.**
   - `json.dumps(kartu)` dicari kata "turun", "naik", "hot", "cut".
   - Kata "turun" di teks bukti mana pun langsung dianggap "panas".
   - `persiapan.get("sentimen")` dicari kata "pucuk"/"dasar".
4. **Merusak aplikasi bila dipasang apa adanya.**
   - `lanjut["posisi"] = "tutup_detik_3"` (string) menimpa tabel ⚡LIVE yang dibaca aplikasi 4.45.
   - `ps["teks"] = "▼ TURUN 86%"` membuang nama berita dan hitung mundur.
   - Kartu lain di jam yang sama tidak ikut diubah, jadi muncul dua arah untuk satu berita.
5. **Ambang tidak konsisten.** Sapuan ditulis ±0,75 di teks tetapi ±0,70 di kode; yang dipakai di sini 0,70 (kode).
6. **CPI tidak pernah bisa "PENUH".** CPI selalu terbit bersama CPI inti & tahunan, jadi menurut definisi dokumen (≥ 2 berita)
   selalu "bersamaan". Varian B dihitung untuk menguji maksud dokumen (berita pendamping lain).
7. **Pola "V-shape" tidak terlihat di data.** Dokumen mengklaim fase 1 searah di detik 1–3 lalu berbalik V di detik 5–15
   (85,7% / 78,6%). Di data asli, porsi rilis yang searah di detik 3 lalu berbalik melewati harga t−1 di detik 10 adalah:
   - SAPUAN PUCUK: 0% (1 rilis);
   - SAPUAN DASAR: 0% (5 rilis);
   - MENENGAH: 5–10%.
8. **Polymarket untuk Fed tidak memberi arah.** Riset sebelumnya (docs/HARI_H.md) menemukan 9/9 keputusan Fed sesuai konsensus
   pasar (90–99%), jadi tidak pernah ada peluang "di atas / di bawah konsensus" ≥ 65%. Vektor pasar untuk FOMC = 0, dan yang
   dipakai hanya Kalshi CPI/NFP/core PCE (yang punya data uji).

## Yang dipasang (cloud saja; aplikasi tidak perlu diperbarui)

**Modul.** `cloud/api/_konfluensi_85.py` (env `KONFLUENSI_85=0` mematikan) dipanggil `chat.py` tepat setelah `_keterkaitan`,
yaitu titik pemasangan yang diminta dokumen.

**Vektor live** (definisi sama dengan riset):

| Vektor | Cara hitung live | ▲ (emas naik) | ▼ (emas turun) |
|---|---|---|---|
| Palang | Z = (Forecast − Previous) / MAD 12 rilis terakhir (`konfluensi_85.json["mad"]`); pengangguran/klaim dibalik | Z ≥ +0,6 | Z ≤ −0,6 |
| Kalshi | `kartu.kalshi` (CPI m/m, NFP, core PCE) | P(di bawah/sama) ≥ 65% | P(di atas) ≥ 65% |
| Petunjuk | arah `pra_satu` dari petunjuk teruji (bukan tren 4 jam saja) | arah naik | arah turun |
| Sapuan | D = (harga − EMA 16×15 mnt) / ATR20 15 mnt, ≤ 6 jam sebelum rilis | D ≤ −0,7 | D ≥ +0,7 |
| Bersamaan | jumlah berita USD dampak tinggi di jam yang sama (kalender pekan ini) | — | — |

- **Candle sapuan.** `_pra_aset.hitung_tren` kini juga menyimpan `ema16`/`atr20` dari candle 15 mnt yang sudah tutup
  (`ema_atr_m15`, sama dengan pandas `ewm(span=16, adjust=False)` / `rolling(20)`). Twelve Data diminta 64 candle, bukan 24,
  dengan kredit yang sama.
- **Hasil di `pra_satu`.** `pra_satu["konfluensi"]` berisi vektor, skor, rezim (varian A dan B), angka uji, dan `timpa`.
- **Detail baris XAU.** Dua poin ditambahkan setelah 📍 (masuk t−1) dan sebelum 👥 / 🔗:
  - `🧩 5 metode dokumen konfluensi: palang ▼ (Z −2,2) • Kalshi – • petunjuk ▼ • sapuan netral (D +0,1) • bersamaan ya
    (2 berita) → skor −2,2: rezim MENENGAH TURUN`
  - `🧪 Rezim MENENGAH TURUN diuji 91 rilis: arah benar detik 3 48% (dulu 44% • sejak Okt 2021 54%), untung bersih tahan
    1 mnt 43% • klaim dokumen 76,9% → tidak lolos, arah utama tetap`
  - Bila tidak ada rezim: `🧪 Uji data asli 1.627 rilis …: tak satu rezim pun lolos ≥ 75% (klaim dokumen 76,9–87,5% tidak
    terbukti) → arah utama tetap`.
  - Bila arah rezim berlawanan dengan arah utama, ditulis "(berlawanan dengan arah utama — tidak dipakai)", supaya tidak
    tampak ada dua arah.
  - Rezim SAPUAN juga menampilkan angka pola V asli dibanding klaim dokumen. Saran dokumen "ambil untung di detik 3 (fase 2
    V)" hanya muncul bila rezim teruji DAN pola V ≥ 65%, yang sekarang tidak pernah terjadi.
- **Gerbang timpa.** Arah baris XAU, daftar, dan semua kartu di jam yang sama hanya diganti bila rezim berstatus **teruji**
  DAN ≥ 75% DAN lebih tinggi dari arah yang ada. Sekarang tidak pernah terjadi. Bila kelak data bertambah dan riset ulang
  membuat rezim lolos, gerbang terbuka sendiri setelah JSON di-commit. Tabel ⚡LIVE (`lanjut.posisi`) tidak pernah ditimpa.
- **ⓘ peringkat.** Baris 🧩 "Dokumen konfluensi 5 metode (semua rezim)": 174 rilis, 51,7%, tidak lolos.

## Yang benar-benar ≥ 75% (sudah ada di aplikasi)

- **Setelah rilis (⚡LIVE / 📍):** posisi yang dibuka t−1, lalu emas bergerak ≥ $0,50 SEARAH di detik 2 → tahan 1 mnt untung
  79%. Datanya 829 rilis; sebelum Okt 2021 79%, sejak itu 78%. Bila BERLAWANAN → tutup (hanya 14% yang balik untung).
- **Gerak detik 2 ≥ $0,50 bertahan s/d detik 5:** 91–99%, tergantung kelompok berita.
- **Masuk t−1 CPI searah tebakan NAIK, tahan 1 mnt:** 74% (53 rilis). Statusnya masih ⚠️ belum terbukti, karena sebelum Okt
  2021 rata-ratanya impas; pembanding selalu BUY 65%.
- **Sebelum rilis:** tidak ada metode yang ≥ 75% di kedua periode, termasuk kelima metode dokumen ini.

## Menjalankan ulang

```bash
python -m research.konfluensi_85     # → cloud/api/konfluensi_85.json + docs/eksternal/hasil_konfluensi_85.txt
python -m research.peringkat         # baris 🧩 di ⓘ
python -m pytest -q tests/test_cloud_konfluensi_85.py tests/test_cloud_simulasi.py
```

Cache vektor ada di `data/research/eksternal/konfluensi_85_vektor.parquet`. Hapus cache ini bila tick, kalender, atau Kalshi
bertambah.
