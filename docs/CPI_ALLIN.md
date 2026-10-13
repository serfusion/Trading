# 💥 Modal kecil + lot maksimal saat CPI (13 Okt 2026)

Permintaan pengguna: modal kecil (5–10 ribu cent = $50–100), lot sebesar mungkin; tebakan benar di detik 1–5 → untung
berlipat, salah → margin call (modal habis). Skrip `research/cpi_allin.py` → `docs/eksternal/hasil_cpi_allin.txt`.

**Cara uji:** tick ASLI Exness XAUUSDc (bid/ask saat rilis), 126 rilis CPI 2016–2026, modal $100 per rilis, lot penuh
sesuai leverage, masuk t0 − 1 dtk searah tebakan aplikasi (tutup kertas), tutup di detik h; equity dicek tiap tick
(≤ 0 = margin call, rugi maks $100 — Exness punya perlindungan saldo negatif). Belum termasuk latensi klik/eksekusi.

## Hasil (tebakan kuat saja = tanpa ⚠️; rugi maks $100 per rilis)
| Leverage | Tutup | sebelum Okt 2021 (12 rilis) | sejak Okt 2021 (32 rilis) | benar (baru) | margin call (baru) | menang rata |
|---|---|---|---|---|---|---|
| 1:200 | detik 2 | −$120 | **+$649** | 78% | 0 | ×0,3 modal |
| 1:200 | detik 5 | −$35 | +$668 | 72% | 2 | ×0,5 |
| 1:500 | detik 2 | −$285 | **+$1.795** | 78% | 2 | ×0,9 |
| 1:500 | detik 5 | −$39 | +$2.295 | 72% | 6 | ×1,3 |
| 1:2000 | detik 2 | −$546 | **+$6.556** | 69% | 9 (1 dari 3,6) | ×3,4 |
| 1:2000 | detik 5 | +$593 | +$9.476 | 66% | 11 | ×5,0 |

Per tahun (kuat, 1:500, detik 2): 2019 −$19 · 2020 −$121 · 2021 −$167 · **2022 +$243 · 2023 +$44 · 2024 +$529 · 2025 +$544 ·
2026 +$457**.

- **Detik 1 tidak menguntungkan** di semua leverage (benar 26–41%: harga broker belum bergerak, spread dulu).
- Tebakan ⚠️ lemah (SELL saat tren naik / Kalshi core berlawanan) menyumbang sebagian besar margin call 2024–2026 → jangan
  dipakai untuk strategi ini.
- **Pembanding "selalu BUY"**: sejak 2024 juga untung (emas sangat volatil & tren naik; rugi dibatasi $100 sementara untung
  tidak dibatasi) tetapi 2016–2023 rugi; 2022–2023 aturan kuat untung saat "selalu BUY" rugi → tebakan memang menambah nilai.
- Untung "berlipat" (×3–5) hanya dengan leverage 1:2000 — dan saat itu **1 dari ±3 rilis menghabiskan modal** walau memakai
  tebakan kuat. Dengan 1:200 untung rata-rata hanya ±30–50% modal per tebakan benar.

## Risiko yang belum masuk angka
1. **Batas leverage saat berita**: Exness memberlakukan margin tetap (±1:200) untuk posisi yang dibuka sekitar berita besar —
   cek ketentuan akun Anda; bila berlaku, hasil 1:2000 tidak bisa dicapai.
2. **Latensi**: masuk tepat t−1 dtk dan keluar tepat detik 2 mustahil secara manual — perlu EA/otomasi; requote/penolakan
   order saat rilis bisa membuat hasil lebih buruk.
3. **Rezim**: semua keuntungan datang dari 2022–2026 (gerak CPI besar); 2019–2021 rugi. Bila volatilitas CPI mengecil, hasil
   bisa kembali negatif.
4. Sampel kecil (32 rilis sejak 2021), aturan saringan ditemukan setelah melihat kesalahan.

## Kesimpulan
Untuk CPI, strategi modal kecil + leverage hanya masuk akal dengan **tebakan kuat saja, tutup detik 2** (bukan detik 1),
leverage sedang (1:200–1:500), dan modal yang benar-benar siap hilang. Teruji untung sejak Okt 2021, rugi sebelumnya →
belum terbukti di semua periode.

## Semua metode (13 Okt 2026, `research/cpi_allin2.py` → `docs/eksternal/hasil_cpi_allin2.txt` & `.csv`)
Pertanyaan pengguna: "sudah diuji metode apapun? kalau bagus pasang". Grid ditetapkan sebelum melihat hasil: 7 cara menebak
arah (tebakan kuat, semua tebakan aplikasi, hanya NAIK, Kalshi m/m saja, KEJAR gerak detik pertama tanpa tebakan, SEMPURNA,
selalu BUY) × masuk t−1/−3/−10 dtk × keluar detik 2/3/5/10, ambil untung 50% modal, batas rugi 50% modal × leverage 1:100–1:2000
= 570 konfigurasi.

**Temuan penting — pembanding ARAH ACAK.** Karena rugi dibatasi = modal (perlindungan saldo negatif) sementara untung tidak
dibatasi, di leverage besar arah acak pun tampak untung (1:2000 tutup detik 2 sejak 2022: acak +$88/rilis). Jadi yang dihitung
adalah selisih tebakan vs lempar koin pada rilis yang sama (`python -m research.cpi_allin2 acak`, 20.000 lemparan):

| Masuk t−1 dtk, tebakan kuat | 2016–Sep 2021 (12 rilis) | sejak Okt 2021 (32 rilis) |
|---|---|---|
| tutup detik 1, 1:200 | untung 0% rilis, −$5,6 (acak −$4,6) | untung 41%, +$2,1 (acak −$3,3), p 0,05 |
| **tutup detik 2, 1:200** | untung 25%, −$10 (acak −$5) | **untung 78%, +$20,3/rilis (acak −$4,3), p < 0,001, 0 modal habis** |
| tutup detik 2, 1:500 | −$23,7 | +$56,1 (acak +$3,5), modal habis 2× |
| tutup detik 2, 1:2000 | −$45,5 | +$204,9 (acak +$87,9), modal habis 9× |
| tutup detik 5, 1:200 | −$2,9 | +$20,9 (acak −$2,3), p 0,02 |

- Per tahun (1:200, detik 2): 2019 −$7 · 2020 −$49 · 2021 −$73 · 2022 +$60 · 2023 −$14 · 2024 +$212 · 2025 +$218 · **2026 5/5
  rilis untung, +$183**. Rugi beruntun terburuk sejak 2022: 2 rilis (−$78).
- KEJAR (masuk 1,5 dtk SETELAH rilis searah gerak detik pertama, tanpa tebakan): rugi atau ≈ 0 di semua leverage → tidak ada
  jalan pintas "lihat dulu baru masuk".
- Tebakan ⚠️ lemah sejak 2022: untung hanya 39% rilis di 1:2000 (modal habis 10 dari 18) → JANGAN.
- Kalshi m/m saja: baru ada sejak 2022, tidak bisa diuji di periode lama.

**Putusan:** sesuai prinsip pengguna ("rugi modal kecil diterima selama untung sebelumnya menutupnya") strategi ini BAGUS di
5 tahun terakhir (tebakan jauh di atas acak, untung menutup rugi, rugi beruntun maks 2) tetapi GAGAL 2019–2021 (lebih buruk dari
acak). DIPASANG 13 Okt (izin "kalau bagus pasang") sebagai INFO, tanpa order, dengan kegagalan 2019–2021 ditulis di bukti.

## Yang dipasang (aplikasi 4.35)
- Cloud `_pra_aset.allin` → `pra_satu.allin` (hanya CPI; angka dari `cpi_detik.json["allin"]`, `python -m research.cpi_allin2
  simpan`; env CPI_ALLIN=0 mematikan). Tebakan kuat: "💥 Modal kecil: BUY/SELL 1 dtk sebelum rilis → TUTUP detik 2"; ⚠️ lemah:
  "💥 Modal kecil: JANGAN".
- Aplikasi: baris 💥 di bawah kotak XAU + "Lot maks 1:200" untuk modal kecil contoh (5.000/10.000 USC atau $50/$100; lot =
  saldo × leverage ÷ (harga × 100)); ketuk = bukti. Baris ⏱️ per detik memberi aba-aba: T−5…0 "💥 MASUK BUY/SELL", detik 0–2
  "tahan", detik 2–5 "💥 TUTUP SEKARANG".
- Saran pemakaian: akun TERPISAH berisi modal kecil saja (jangan akun bot utama), leverage 1:200–1:500, jangan tutup di
  detik 1. Cek batas leverage Exness saat berita; perlu tangan cepat atau EA untuk tutup tepat detik 2–5.
- Per jalur tebakan (1:200, detik 2, sejak 2022): jalur indeks konsensus 25 rilis untung 76% (+$17,6/rilis); jalur Kalshi
  (dipakai bila konsensus indeks belum ada — seperti CPI 14 Okt 2026) 7 rilis untung 86% (+$29,8) — sampel sangat kecil.

## Saldo 200.000 USC, tutup detik 1–10, HMR Exness (13 Okt 2026, `python -m research.cpi_allin2 bank`)
**HMR Exness (resmi, Pusat Bantuan diperbarui 13 Okt 2026):** order yang dibuka 15 menit sebelum sampai 90 detik sesudah
berita penting terkena margin lebih tinggi; leverage emas (XAU) dibatasi **1:100–1:1000** (forex & kripto 1:200). Leverage
"tanpa batas" akun Cent TIDAK berlaku saat masuk 1 detik sebelum CPI. Batas untuk akun sendiri: indikator HMR di Exness
Terminal/Trade atau Personal Area. Lot yang melebihi margin HMR akan ditolak.

**Tutup detik 1–10** (masuk t−1 dtk, tebakan kuat, per modal $100, sejak 2022; lengkap di
`docs/eksternal/hasil_cpi_allin_bank.txt`):

| Tutup | untung | 1:100 | 1:200 | 1:500 | 1:1000 |
|---|---|---|---|---|---|
| detik 1 | 41% | +$1 | +$2 | +$5 | +$11 (habis 2) |
| **detik 2** | **78%** | +$10 | +$20 (habis 0) | +$56 (habis 2) | +$107 (habis 6) |
| detik 5 | 72% | +$9 | +$21 (habis 2) | +$72 (habis 6) | +$150 (habis 9) |
| detik 10 | 72% | +$10 | +$24 (habis 5) | +$86 (habis 6) | +$178 (habis 9) |
| **lentur** (detik 2 rugi → tutup; untung → tahan s/d detik 10) | 72% | +$14 | +$30 (habis 2) | +$89 (habis 4) | +$180 (habis 8) |

Semua varian 2019–2021 negatif (−$1 … −$40). Di leverage besar, arah acak pun naik (1:1000 detik 10 acak +$72), jadi
kelebihan tebakan = selisih dengan acak (±+$25 di 1:200, ±+$105 di 1:1000).

**Saldo 200.000 USC (bank) + "peluru" tetap per CPI di akun terpisah** (untung ditarik ke bank, rugi maks = peluru):
- Peluru 10.000 USC (5%): mulai 2019 (termasuk masa gagal) saldo terendah 193 rb (1:100) / 185 rb (1:200) / 167 rb (1:500) /
  132 rb (1:1000, detik 2) — tidak pernah habis; akhir 2026 226 rb / 253 rb / 351 rb / 493 rb (lentur: 241/289/470/751 rb).
- Peluru 20.000 (10%) 1:1000: terendah 64 rb. Peluru 40.000 (20%) 1:1000: **bangkrut** (−71 rb) bila mulai 2019.
- Saran: peluru ≤ 5% saldo (10.000 USC), akun terpisah; lot = peluru × leverage HMR ÷ (harga × 100).

## Aplikasi 4.36: per detik + lentur (13 Okt 2026, pengguna "ya boleh lentur … per detik dan berubah persentase")
- `research/cpi_detik_penuh.py` → `cpi_detik.json["uji"]["saring"]["per_detik_penuh"]` (+ `lemah`): persen arah emas untuk
  SETIAP detik 1–10 dan 15/20/30/45/60/90/120/180/240/300 dtk, cara sama dengan `cpi_detik.tepat` (cocok persis di detik
  1/2/3/5/10). Tebakan kuat 2016–2026: detik 1 56%, detik 2 68%, detik 3–10 64–69%, 30 dtk–3 mnt 69–74%, 4–5 mnt 61–66%.
  ⚠️ lemah: detik 1–2 62%, detik 15–5 mnt 41–48% (lebih sering salah).
- Cloud: `_cpi_detik.pakai_saring` memakai kurva penuh; `_pra_aset.allin` lentur ("detik 2 rugi TUTUP, untung tahan s/d
  detik 10", angka `cpi_detik.json["allin"]["lentur"]`).
- Aplikasi: baris ⏱️ tampil T−15 mnt (awal HMR) s/d +10 mnt, hitung mundur per detik; setelah rilis persen = kunci kurva
  terdekat ≤ detik sekarang (< 50% diberi ⚠️); aba-aba 💥: siapkan → MASUK (T−5…0) → tahan s/d detik 2 → "rugi → TUTUP •
  untung → tahan" → hitung mundur s/d detik 10 → "TUTUP SEKARANG (detik 10)".

## Sumber & metode yang BARU diuji (13 Okt 2026, pertanyaan "yakin tidak ada yang terlewat?")
| Diuji | Hasil |
|---|---|
| **Cleveland Fed nowcast** (`research/cpi_cleveland.py`, 160 bulan 2013–2026, dulu diblokir) | tebak kejutan 59–60%; emas detik 2 sendirian 52–58%, LAMA < 50%. Nowcast core hampir selalu ±0,2% (sejak 2025 selalu "di bawah konsensus") ≈ "selalu BUY". Sepakat dengan aplikasi: detik 2 73% (22; BARU 92% n 13, LAMA 44% n 9) vs berlawanan 60% (15) → kandidat lemah, sampel kecil |
| Breakeven inflasi 5 th, ekspektasi Univ. Michigan, harga bayar/jual Fed New York & Philadelphia (`research/cpi_lain2.py`) | sendirian 43–54% (≈ acak). Bucket "sepakat" 57–86% dengan n 22–37 → setelah ±10 uji, satu bucket ±2 SE di atas wajar terjadi karena kebetulan → TIDAK dipasang |
| Feed lain (Dukascopy) untuk strategi modal kecil (tebakan kuat, masuk t−1) | sejak 2022 untung 62% rilis (Exness 78%); lentur 1:200 +$27/rilis (Exness +$30), habis 3×; LAMA negatif → keunggulan bertahan di feed lain, lentur lebih tahan |

**Belum diuji (alasan):** sebaran ramalan ekonom Bloomberg/Reuters (berbayar), pasar swap/fixing CPI CME (berbayar/diblokir),
NFIB rencana harga (403), ISM harga (lisensi), Manheim mobil bekas & sewa Zillow/Apartment List (bisa diunduh; komponen
lambat dan sudah dipakai ekonom penyusun konsensus), Truflation (riwayat sejak 2021 saja), ramalan per komponen CPI
(bensin + mobil bekas + tiket pesawat + sewa + asuransi — kerja besar), posisi opsi emas sebelum CPI (data berbayar), dan
yang terpenting: **eksekusi nyata** (leverage HMR akun pengguna, slip/requote di t−1 dtk) — hanya bisa diukur dengan uji
maju lot minimum.

## Uji SEMUA sumber tersisa (13 Okt 2026, permintaan "uji semua" — `research/cpi_semua.py` → `docs/eksternal/hasil_cpi_semua.txt`)
- **29 sinyal tunggal** (tutup kertas, emas detik 2; kejutan CPI/core): harga ISM manufaktur & jasa, PPI & core PPI, harga
  impor, NFIB, Michigan 1 th, Fed NY ekspektasi 1 th, harga bayar Philly (Nasdaq, *_chg & *_sur), **Manheim mobil bekas**
  (xlsx resmi 1997–Nov 2025), **Zillow ZORI sewa** (2015–2026), Cleveland Fed, breakeven 5 th, UMich, harga bayar/jual Fed NY &
  Philly → mentah detik 2 42–60%, kejutan angka 33–60%. **Lolos 0 dari 29** (syarat detik 2 ≥ 60% + LAMA & BARU > 50%, n ≥ 20);
  bila arah emas diacak 200× rata-rata lolos 0,4 → tidak ada sinyal tersembunyi. Terdekat: Manheim 60% (n 48) tetapi BARU 50%.
- **Model gabungan** (logistik 32 fitur + aturan aplikasi + Kalshi, walk-forward per tahun): detik 2 57% (LAMA 59%, BARU 54%)
  — LEBIH BURUK dari aturan aplikasi (68%; BARU 81%). Menambah sumber lemah menurunkan ketepatan (sama seperti 10 Okt).
- **Telat eksekusi** (strategi modal kecil, tebakan kuat, lentur, tick Exness): masuk t−1,5/−1/−0,5/−0,2 dtk × tutup rugi di
  detik 2/2,5/3 × akhir detik 10/10,5/11 → sejak 2022 1:200 +$25…+$32 per $100, 1:500 +$80…+$90, untung 66–75% rilis, modal
  habis 2–6 → **tahan telat ±1 dtk**; LAMA tetap negatif.
- **Tidak bisa diuji:** CME (memblokir akses otomatis — tidak dicoba diakali), Truflation (API berkunci; bisa diuji bila
  pengguna memberi kunci lewat secret environment), NFIB rencana harga (403), sebaran ramalan Bloomberg/Reuters & opsi emas
  (berbayar), requote/slip nyata Exness (hanya lewat uji maju lot kecil).
- **Kesimpulan:** aturan aplikasi (konsensus indeks tanpa pembulatan + Kalshi + saringan) tetap yang terbaik dari semua
  yang bisa diuji; tidak ada perubahan pada cloud/aplikasi.
