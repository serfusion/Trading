# 🔬 Riset mendalam: Retail+GDP, ADP+JOLTS+klaim, FOMC+konsumen (13 Okt 2026)

Permintaan pengguna 13 Okt: "Di sesi lain sangat lama, kenapa di sini cepat sekali? Apakah ada yang terlewat? … Uji
keduanya." Kelompok berita sisa workflow 11 Okt (`.claude/workflows/riset-berita-lonjakan.js`, docs/LANJUTAN.md) dikerjakan
ulang sedalam workflow itu: data diperbaiki → hipotesis pra-registrasi → uji tutup kertas + permutasi keluarga →
verifikasi adversarial → kritik.

## 1. Yang terlewat di putaran cepat (dan sudah diperbaiki)
| masalah | akibat | perbaikan (`research/riset_dalam_data.py`) |
|---|---|---|
| kalender hanya ForexFactory BINTANG 3 | klaim 2018–2022 = 0 rilis, JOLTS < 2021 = 0, UoM/CB bolong | arsip FF mentah spoluan memuat SEMUA dampak 2010–2023 (+ Forecast); 2024+ FF bintang 3 + Nasdaq + tanggal FRED |
| tick Exness hanya di sekitar berita bintang 3 | rilis "Medium" tanpa target | 1.645 rilis di 134 bulan diunduh ulang dari arsip Exness → `exness/XAUUSDc/tambah_<bln>.parquet` (56 MB) |
| rilis bersamaan di menit yang sama | reaksi emas campuran | kolom `bersama`/`sendiri` (tingkat NFP/CPI/FOMC > PCE/PPI/Retail/GDP/ISM > JOLTS/ADP > klaim/UoM/CB) |
| 'previous' kalender = angka SUDAH DIREVISI | KON bocor revisi | KON/ANK memakai Act rilis sebelumnya (rilis pertama) |
| bug C_4W/A_NFPP/R_BENSIN (n 0–3) | aturan tak teruji | dihitung ulang dari tabel sendiri |

Target per tahun (rilis dengan tick, 2016–2026): klaim 49–55, UoM 23–24, Retail/ADP/JOLTS/CB 11–13, GDP 10–16, FOMC 8.
Cek: 999 rilis yang juga ada di `lonjakan60.parquet` → arah lonjakan **100% sama**.

## 2. Hasil (`research/riset_dalam.py` → `docs/eksternal/hasil_riset_dalam.txt`)
66 aturan pra-registrasi di 10 kelompok (P, P3, KON, ANK + petunjuk khusus: mobil/bensin/Redbook → Retail; GDPNow/St. Louis
ENI → GDP advance; klaim pekan survei/NFP → ADP; NFP bulan sama/Indeed/klaim → JOLTS; konsensus vs rata 4 pekan/musiman/
klaim lanjutan → klaim; S&P 500 & bensin → UoM prelim/final; UoM/S&P/klaim → CB; yield 2 th/emas 5 hari/rapat SEP → FOMC).
PLAFON (bila kejutan sudah diketahui): ADP 91%, Retail 77%, klaim 76%, CB 75%, GDP 70%, JOLTS 69%, UoM 60–66%.

Lolos kriteria per kelompok: **GDP prelim/final ← kejutan GDP sebelumnya (P)** 66% (LAMA 52 / BARU 75, p 0,028/0,003) dan
**UoM final ← S&P 500 sejak prelim (U_REVSPX)** 66% (62 / 68, p 0,022/0,052). Terdekat lain: JOLTS ← kejutan NFP bulan acuan
yang sama 60% (52 / 67, p 0,083/0,042; menebak ANGKA 66%), GDPNow → angka GDP advance 76% tetapi hanya 11 rilis ditebak.

## 3. Verifikasi adversarial (`research/riset_dalam_cek.py` → `docs/eksternal/hasil_riset_dalam_cek.txt`)
- Hitung ulang independen dari FF mentah: angka terulang (GDP 64%, UoM 64%); 15 contoh look-ahead semua OK.
- **Permutasi GLOBAL 66 aturan:** U_REVSPX p 0,142, GDP P p 0,174 (aturan terbaik dari emas acak rata-rata 62%, P95 68%) →
  **tidak lebih baik dari kebetulan** setelah koreksi banyak-uji yang jujur.
- GDP P rapuh: prelim 53% (LAMA 31%) vs final 78%; ganjil 52% vs genap 79%; detik 5/10 55%/51%.
- U_REVSPX: menebak angka hanya 57%, emas melewati PLAFON (66% > 60%) → keunggulan bukan dari berita; detik 2 10% (n 10),
  detik 5 41%; plasebo Jumat 10:00 tanpa berita 39% (n 18).
- **Kesimpulan: 0 aturan layak pasang.** Tidak ada perubahan cloud/aplikasi.

## 4. Kritik — apa yang belum diuji & peluang berikutnya
- Belum diuji (alasan ekonomi ada, data bisa didapat): Kalshi KXGDP/KXFEDDECISION (data 2022+ → n kecil), Polymarket Fed
  (9/9 sesuai konsensus), diferensial pasar kerja Conference Board (sub-indeks CB, rilis pers), NFIB rencana rekrut (sebelum
  JOLTS), ADP mingguan (baru sejak Okt 2025), Chicago Fed CARTS (2023+), nowcast NY Fed (unduhan manual), sebaran konsensus
  (Bloomberg/Reuters berbayar), fed funds futures (CME memblokir — jangan diakali).
- Kelemahan metode: target hanya feed Exness untuk rilis tambahan (Dukascopy belum diunduh); GDP kuartalan tidak pernah bisa
  mencapai ≥ 40 tebakan sejak 2016; tutup kertas mulai 2013 tetapi tick baru dari Sep 2015 → tahun awal tak tertebak;
  rilis 08:30 Kamis sering bersamaan (klaim + GDP/Retail/Philly) walau dipisah lewat `sendiri`.
- Paling realistis untuk UJI MAJU (bukan dipasang): JOLTS ← NFP bulan acuan (angka 66%, BARU 67%), GDP final ← P, UoM final
  ← S&P 500; ISM Jasa (sesi 11 Okt).
