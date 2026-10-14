# 🔍 Kenapa tebakan CPI → emas bisa salah? Bedah rilis Jun & Sep 2026 (13 Okt 2026)

Permintaan pengguna: "telusuri, uji validitas, pastikan mengapa 2 lainnya bisa salah … supaya bisa sempurna" lalu
"yang penting pasca release news detik 1–2 benar". Skrip `research/cpi_salah.py` → `docs/eksternal/hasil_cpi_salah.txt`
(memakai tabel & aturan aplikasi IDX|K dari `research/cpi_detik.py`, uji tutup kertas). LAMA < Okt 2021, BARU ≥ Okt 2021.

## 1. Dua rilis yang "salah" — dilihat di detik 1 dan 2
| Rilis | Tebakan | Angka keluar | Emas detik 1 | Emas detik 2 | Emas detik 3–10 |
|---|---|---|---|---|---|
| 10 Jun 2026 | TURUN (indeks: CPI utama di atas) | CPI m/m & y/y **sama** dengan perkiraan, **core di BAWAH** (0,2 vs 0,3) | −$0,34 ✅ | +$5,91 ❌ | naik +$8–14 ❌ |
| 11 Sep 2026 | NAIK (indeks: CPI utama di bawah) | CPI m/m & y/y **sama**, **core di ATAS** (0,3 vs 0,2) | +$2,76 ✅ | +$2,76 ✅ | anjlok −$22…−35 ❌ |

- **September BENAR di detik 1–2.** Salahnya baru dari detik ke-3, saat pasar mencerna core yang di atas perkiraan.
- **Juni salah di detik 2**: aturan menebak arah CPI utama, tetapi CPI utama keluar persis sesuai perkiraan, dan yang
  meleset justru core.

## 2. Akar masalah (diuji)
1. **Core CPI yang paling menggerakkan emas.** Bila angka sudah diketahui, emas berlawanan dengan kejutan core di 86%
   rilis (2–10 dtk; sejak 2024 94%), sedangkan kejutan CPI utama saja (core sesuai perkiraan) hanya 75%.
2. **Aturan sekarang praktis buta core di 2026.** Konsensus indeks core (petunjuk core terbaik) tidak terbit sepanjang 2026
   (2025: 2 rilis, 2026: 0) → suara indeks hanya berisi CPI utama & y/y. Kalshi core sudah dicoba sebagai pengganti: menebak
   angka core 72% (n 25), tetapi sebagai penentu arah emas **lebih buruk** (detik 2 sejak Okt 2021 58% vs 74%) — mis. Jul 2026
   Kalshi core condong di atas, keluar 0,0 vs 0,2.
3. **Tebakan TURUN lemah selama emas tren naik.** Sejak 2024: tebakan NAIK benar **95%** di detik 2 (18/19), tebakan TURUN
   hanya **45%** (5/11). Bahkan bila CPI pasti di atas perkiraan, emas turun di detik 2 hanya 62% (5/8), sedangkan core di
   bawah → emas naik 100% (13/13). Sebelum 2021 tidak begitu (tebakan TURUN 62%) → tergantung rezim pasar (2024–2026
   emas tren naik kuat; kabar "buruk" CPI tidak bisa diandalkan menjatuhkannya).
4. **Detik 1 memang tidak bisa ditebak.** Gerak median detik 1 hanya $0,48 (detik 2: $3,98). Walau angka CPI sudah
   diketahui pasti, emas di detik 1 searah hanya **57%** = harga broker belum bergerak (feed ±1–2 detik terlambat,
   docs/LONJAKAN_BERITA.md). Batas tertinggi yang mungkin di detik 2: 76–80%.

## 3. Masalah data yang ditemukan & diperbaiki (riset; cloud live TIDAK terdampak)
- **Kalshi**: sejak ±Jul 2026 API memakai `close_dollars`, pengunduh riset membaca `close` → harga Jul–Sep 2026 tersimpan
  kosong (13 event: CPI, core, NFP, pengangguran, PCE, Fed). `research/kalshi.py` diperbaiki + `kosong()` → diunduh ulang.
  Cloud `_kalshi.py` sudah memakai `*_dollars` (aplikasi aman).
- **Nasdaq**: CPI Okt 2025 tidak pernah terbit (shutdown) → pengecekan urutan baris m/m vs y/y ke FRED gagal → rilis
  13 Jan 2026 tertukar (m/m 2,7 / y/y 0,3). `research/nasdaq_kalender.cpi` kini memakai cadangan yang sama dengan cloud
  (m/m = angka lebih kecil). Setelah diperbaiki, aturan juga menebak **TURUN di 13 Jan 2026 → salah** (core di bawah, emas
  naik) → 12 bulan terakhir detik 2: **7 benar / 2 salah** (Jan & Jun), detik 1: 5/9.

## 4. Hasil aturan aplikasi sekarang (IDX|K, tutup kertas)
| | semua 2016–2026 | LAMA | BARU | 2024+ |
|---|---|---|---|---|
| Detik 1 | 58% (51/88) | 61% | 56% | 63% |
| **Detik 2** | 66% (59/89) | 56% | **74%** | **77%** |
| Plafon detik 2 (angka sudah diketahui) | 76% | 77% | 75% | 80% |

## 5. Kandidat perbaikan: lewati tebakan TURUN saat emas tren naik
Tren = close emas kemarin di atas rata-rata 200 hari (diuji juga 50/100 hari & return 60 hari — hasil serupa).

| Detik 2 | semua | LAMA | BARU | 2024+ |
|---|---|---|---|---|
| Sekarang | 66% (59/89) | 56% (22/39) | 74% (37/50) | 77% (23/30) |
| **TURUN dilewati saat tren naik** | 69% (45/65) | 54% (15/28) | **81%** (30/37) | **90%** (18/20) |

- Uji "buang tebakan secara acak" sebanyak yang sama: BARU p 0,062, 2024+ **p 0,028**, LAMA p 0,82 (tidak berpengaruh).
- Pada 12 bulan terakhir: menghindari salah Jan 2026; **Juni tetap salah** (saat itu emas di bawah rata-rata 200 hari).
- Ditemukan SETELAH melihat kesalahan → diuji tutup kertas; biaya bila dilewati: lebih sedikit rilis ditebak (89 → 65).
- Kandidat lain yang diuji dan TIDAK lebih baik: Kalshi core diutamakan, suara Kalshi core+headline+indeks, lewati bila
  Kalshi core / headline berlawanan.

## 6. CPI 14 Okt 2026 (dicek 13 Okt)
- Kalshi CPI utama (konsensus 0,6%): di atas 15%, di bawah 38% → condong **di bawah** → aturan: emas **NAIK**.
- Kalshi core (konsensus 0,2%): di atas 38%, di bawah 22% → condong **di atas** (konflik, mirip pola September).
- Riwayat konflik ini (tebak NAIK, Kalshi core condong di atas): detik 1 **6/7**, detik 2 **6/7** benar (sampel kecil).
- Tebakan NAIK tidak terkena filter tren. Risiko: bila core benar-benar di atas, emas bisa berbalik turun setelah detik 2
  (seperti 11 Sep: +$2,76 lalu −$35).

## Kesimpulan jujur
"Sempurna" (100%) tidak mungkin: walau angka CPI sudah diketahui, emas di detik 2 hanya searah ±76–80%, dan detik 1 ±57%.
Aturan sekarang di detik 2 sudah dekat batas itu sejak 2024 (77%). Perbaikan yang terbukti paling kuat sejauh ini: jangan
mengikuti tebakan TURUN saat emas tren naik (2024+ 77% → 90%) — perlu izin untuk dipasang dan uji maju.

## 7. DIPASANG 13 Okt 2026 — tebakan TURUN yang meragukan TETAP tampil sebagai ⚠️ lemah
Urutan permintaan pengguna: "perbaiki supaya predict mu akan skip ini" (Juni) → lalu "bukannya bisa di predict malah bagus
kenapa dilewati?". Diuji: tebakan TURUN yang kena saringan masih benar ±62–67% di detik 1 → TIDAK dibuang, ditampilkan
dengan tanda lemah dan angkanya sendiri.

Saringan (D): tebakan TURUN saat emas di atas rata-rata 200 hari bursa (close Senin–Jumat; Twelve Data harian memuat
candle Sabtu/Minggu ganda → dibuang, riset disamakan) **atau** Kalshi core condong berlawanan (≥ 0,10). Menangkap Jan 2026
(tren naik) dan Jun 2026 (Kalshi core condong di bawah). Angka tutup kertas detik 2 (`cpi_detik.json["uji"]["saring"]`):

| | semua 2016–2026 | lama | sejak Okt 2021 | sejak 2024 |
|---|---|---|---|---|
| Tebakan kuat (tidak kena saringan) | **68%** (61 rilis) | 54% | **81%** | **95%** (18/19) |
| Tebakan ⚠️ lemah (kena saringan) | 62% (29 rilis; detik 1 62%) | 64% | 61% | 45% |
| Aturan lama tanpa pemisahan | 66% | 58% | 74% | 77% |

Uji "buang acak" tebakan kuat: sejak 2024 p 0,004, sejak Okt 2021 p 0,12 (belum meyakinkan). Saringan core hanya teruji
sejak 2022 (Kalshi). Detik 1 tebakan kuat 56% (harga belum bergerak).
- Cloud: `_cpi_detik.saring` / `pakai_saring` / `tren200` (Twelve Data XAU harian 300 candle, cache baris Supabase
  `cpi_tren` 6 jam; tidak terbaca → lemah), env `CPI_SARING=0` = angka lama. Patokan tampilan kini **detik 2**
  ("CPI ▲ NAIK 68% (detik 2)"); detail tebakan lemah: "Lemah karena emas sedang tren naik …".
- Riset: `research/cpi_detik.py` kolom `T200`, aturan `IDX|K+S`, `cpi_detik.json["uji"]["saring"]` (+ `"lemah"`); jalankan
  ulang `python -m research.cpi_detik` bila data bertambah (angka "lonjakan" dipertahankan).
- Cek langsung 13 Okt untuk CPI 14 Okt: emas di bawah rata-rata 200 hari, Kalshi CPI utama di bawah (37% vs 14%) →
  **NAIK (detik 2), tebakan kuat**.

## 14 Okt 2026 — bedah rilis CPI September (pengguna: "predictmu salah langsung menukik")
- Hasil: CPI y/y 3,7% (perkiraan 3,6%) DI ATAS; inti "lebih tinggi dari perkiraan" (Reuters "core CPI firmer"). Dua poin detail
  aplikasi BENAR: 🧮 "y/y tersirat 3,71 → condong DI ATAS" dan "inti jarang DI BAWAH (3/33)". Baris utama "NAIK 54% ⚠️ lemah"
  berasal dari Kalshi CPI utama m/m (condong di bawah) → arah utama SALAH untuk gerak besar.
- Emas (Twelve Data 1 mnt): candle 12:30 buka 4.153 → puncak 4.172,8 → lalu jatuh ke 4.108 (screenshot MT5 pengguna) ≈ −$64
  dari puncak dalam 6–9 menit. Tick detik 1–10 belum tersedia (arsip Exness bulanan).
- Pola berulang (data riset cpi_skenario + tick): situasi YOYc −1 (konsensus inti y/y > tersirat) sejak 2024 n 6 → detik 2
  NAIK 83%, tetapi detik 5–10 TURUN 67%, SELL t−1 tahan 10 dtk rata-rata +$12/oz (Agu & Sep 2026: detik 2 +$5,4/+$2,8 lalu
  detik 10 −$34,7/−$34,9). Sejak Okt 2021 n 10: detik 2 turun 30%, detik 10 turun 60%. Seluruh periode n 24: 52–58% (≈ acak).
  Ditemukan SETELAH melihat hasil & n kecil → kandidat, belum terbukti. Usulan tampilan "⚠️ 2 arah: detik 1–2 sering naik, lalu
  TURUN" menunggu izin "pasang".
- Detik per detik 14 Okt (OKX XAUT-USDT candle 1 dtk): t−1 4.153,0 → detik 1 4.139,9 (−$13) → detik 2 4.125,8 (−$27) → detik 6
  4.121 → pantul 4.141 (detik 39) → 4.108 (MT5). Puncak 4.172 di candle 1 mnt Twelve Data = tick salah. Tebakan NAIK salah
  sejak detik 1.
- Uji ulang aturan sebelum rilis (tutup kertas, tick Exness): aplikasi IDX|K detik 2 66%/74%/77% (semua/BARU/2024+); "YOYc −1 →
  TURUN" 64/65/66; "YOY & YOYc atas → TURUN" 66/70/73; suara app+YOY+YOYc 64/63/64 → tidak ada pengganti yang lebih baik.
- DIPASANG aplikasi 4.39 (permintaan "perbaiki sistem apk yang gagal predict di detik awal"): ⚡ LIVE `LiveGold.kt` — HP membaca
  harga XAUT (OKX → KuCoin → Bitget → Gate, tanpa kunci) tiap ±0,5 dtk dari T−15 dtk s/d +2 mnt; setelah rilis baris XAU =
  gerak harga sungguhan (≥ $0,50 → arah, "bertahan s/d detik 10: X%" dari `pra_satu.lanjut`), tebakan sebelum rilis yang
  berlawanan ditandai SALAH, posisi 💥 berlawanan → "TUTUP SEKARANG". Uji 2026: OKX ±1 dtk lebih cepat dari Exness; gerak OKX
  ≥ $1 di detik 1 searah Exness detik 2 pada 10/11 rilis (n kecil).
