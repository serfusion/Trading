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

## ₿ CPI → BTC & ETH (13 Okt 2026, `research/kripto_cpi.py` → `docs/eksternal/hasil_kripto_cpi.txt`)
Tebakan CPI kuat dipakai searah untuk kripto (CPI di bawah → emas, BTC, ETH naik). Sejak Okt 2021 (spread asli Exness, HMR 1:200):
| | arah detik 1 / 2 / 3 | lonjakan menit 1 | tutup detik 2 | lentur |
|---|---|---|---|---|
| BTC Exness (32 rilis) | 69% / 75% / 78% | 75% | +$11,8/$100 (acak −$13,5), untung 53% | +$18,4, untung 38%, habis 3× |
| ETH Exness (30 rilis, tick ETHUSDm diunduh 13 Okt) | 63% / 77% / 83% | 77% | +$2,0 (spread ±$1,8 memakan) | +$27,8, untung 37%, habis 3× |
| Emas (pembanding) | 41%* / 78% | – | +$20,3, untung 78% | +$29,8, untung 72%, habis 2× |
*persen untung setelah spread. 2019–2021 kripto rugi (sama dengan emas). Kesimpulan: emas tetap terbaik (lebih sering untung);
kripto hanya lewat cara lentur. Info dipasang di bukti 💥 CPI (`_pra_aset.kripto_teks`, `cpi_detik.json["allin"]["kripto"]`).

## 🎯 BTC & ETH WR tinggi + tutup dini (antrian pengguna, 13 Okt 2026)
- Tutup dini saat candle melonjak melawan sinyal: SUDAH diuji 10 & 13 Okt (`docs/BATAL_GUNCANG.md`): lonjakan sedang 1,5–3 ATR
  MERUGIKAN (harga pulih); ≥ 4 ATR close candle 1 jam sedikit menolong XAU/BTC (terpasang 🛑); ETH/DOGE/ADA ≈ 0 (dimatikan).
- `research/kripto_wr.py` (replay kode cloud, subset dipilih di LAMA → diuji BARU): BTC sesi Eropa (08–12 UTC = 15–19 WIB)
  WR 70% → 69% vs dasar 58% (BUY + Eropa 72% → 77%, n 77); 8/17 subset bertahan vs acak 1,9. Tetapi per sinyal unik per
  tahun sesi Eropa lebih baik hanya 6 dari 11 tahun → BELUM TERBUKTI, tidak dipasang (kandidat label/uji maju). ETH: 2
  bertahan ≈ kebetulan.

## ⚡ Lonjakan melawan di detik 1 & leverage peluru (13 Okt 2026, `research/cpi_spike.py` → `docs/eksternal/hasil_cpi_spike.txt`)
Pertanyaan pengguna: "detik pertama bisa spike berlawanan, padahal prediksi benar di detik 2/3 → habis semua. Berapa lotnya?"
Tick asli Exness XAUUSDc, tebakan CPI KUAT (IDX|K+S tutup kertas), masuk t−1 dtk dengan lot penuh, spread ikut dihitung. Dengan
lot penuh, modal habis bila emas melawan ≥ **harga ÷ leverage** (berlaku untuk besar modal berapa pun) — di $4.190: 1:200 $20,95,
1:500 $8,38, 1:750 $5,59, 1:1000 $4,19.
- **Detik 1 melawan tebakan di 14 dari 32 rilis sejak Okt 2021, 10 di antaranya arah akhirnya benar** → kekhawatiran pengguna nyata.
- Di 24 rilis yang arahnya benar, gerak melawan terbesar s/d detik 10: median 0,019% harga, P90 0,064%, **maks 0,131%**
  (13 Sep 2023, SELL) dan 0,113% (13 Okt 2021, SELL). 2025–2026 jauh lebih kecil (maks 0,031%, 10 Apr 2026 $1,46) walau harga
  emas dua kali lipat — lonjakan tidak membesar seiring harga.
- Per leverage (lentur, per modal $100, sejak Okt 2021 | sebelum Okt 2021):

| leverage | untung | rata-rata | modal habis | habis padahal arah benar | arah acak | sebelum Okt 2021 |
|---|---|---|---|---|---|---|
| 1:100 | 69% | +$14,7 | 0/32 | 0 | +$3,0 | −$2,3 |
| 1:200 | 69% | +$31,5 | 2/32 | 0 | +$5,6 | −$4,7 |
| 1:300 | 69% | +$49,5 | 3/32 | 0 | +$10,2 | −$7,0 |
| **1:500 ⭐** | 69% | +$89,4 | 4/32 | **0** | +$28,2 | −$11,6 |
| 1:750 | 69% | +$140,8 | 5/32 | 0 (nyaris) | +$55,1 | −$14,4 |
| 1:1000 | 66% | +$178,7 | 8/32 | **2** | +$76,1 | −$16,3 |

  Semua leverage mengalahkan arah acak sejak 2021 (p ≤ 0,01) dan RUGI sebelum Okt 2021. Modal habis di 1:200–1:750 = tebakan
  yang memang salah, bukan lonjakan.
- **⭐ 1:500** = leverage terbesar yang tidak pernah habis saat arah benar, dengan cadangan 1,5× terhadap lonjakan terburuk
  (habis bila melawan 0,2% vs terburuk 0,131%). 1:1000 rata-rata dua kali lebih besar tetapi 2 dari 24 tebakan benar habis.
- Cara meredam (sejak 2021 | sebelum 2021, per $100):
  - **Bertahap** 1:200 di t−1 → detik 2 untung, tambah lot sampai total 1:1000 (harga t+2,5 dtk) → +$92, habis 2, sebelum 2021
    **+$3,9** (satu-satunya cara yang positif di kedua periode; 1:100 → 1:1000 +$80,7 / +$7,3). Butuh klik kedua cepat.
  - **SL darurat −80% modal** di 1:1000 → +$181,1, habis 3 (vs 8), sebelum 2021 −$13,5. SL −50% memotong untung.
  - Masuk SETELAH rilis (t+0,5 / +1 / +1,5 dtk) lebih buruk (+$5,9…+$65,6) — lonjakan sudah lewat, harga sudah lari.
- **Batas uji:** 32 rilis (24 benar) → lonjakan terburuk berikutnya bisa melebihi 0,131%; slip/requote nyata Exness saat lot
  besar tidak terlihat di tick; leverage HMR akun bisa lebih kecil dari yang dipilih (order ditolak → pakai leverage di bawahnya).
- DIPASANG (info, aplikasi 4.37): `cpi_detik.json["allin"]["spike"]` → `_pra_aset.allin` (`lev_tabel`, `saran_lev`, `bertahap`,
  baris ⚡ di bukti) → `StatusCard.StripAllin`: "1 peluru 10.000 USC: 1:200 x • 1:500 y ⭐ • 1:1000 z lot", jarak habis = harga
  ÷ leverage (harga langsung), ketuk = tabel per leverage + bertahap. Tanpa order otomatis.

## 🔄 Data terbaru & ⚖️ situasi hari ini (13 Okt 2026, `research/cpi_konflik.py` → `docs/eksternal/hasil_cpi_konflik.txt`)
Permintaan pengguna setelah konsensus CPI 14 Okt terbit (m/m 0,6% • y/y 3,6% • inti 0,2% / 2,5%): "silahkan dikalkulasikan,
kedepannya selalu cek forecast, konsensus, dll agar persentase berubah up to date".
- Cloud sudah mengambil data otomatis setiap aplikasi dibuka: konsensus ForexFactory (kartu) / Nasdaq (cache 3 jam → 30 mnt
  ≤ 24 jam → 10 mnt ≤ 3 jam sebelum rilis), konsensus INDEKS tanpa pembulatan (Nasdaq, biasanya muncul menjelang rilis —
  13 Okt 18:10 WIB belum ada), Kalshi langsung. Persen utama = aturan teruji (tidak berubah kecuali jalurnya berubah).
- BARU: `_cpi_detik.terbaru` → baris di detail CPI: 🔄 konsensus + jam cek • 🎲 Kalshi m/m, inti, y/y • 🧮 y/y tersirat
  (konsensus m/m + efek basis, indeks NSA; sama dengan petunjuk YOY riset) • ⚖️ persen RILIS SERUPA untuk situasi hari ini.
- Situasi (tebakan IDX|K tutup kertas 2016–2026, detik 2):

| tebakan | situasi | emas searah detik 2 | sejak Okt 2021 |
|---|---|---|---|
| NAIK | petunjuk lain sepakat | 70% (27 rilis) | 100% (11) |
| NAIK | y/y tersirat berlawanan (semua) | 65% (23) | 69% (13) |
| NAIK | Kalshi inti berlawanan (semua) | 86% (7) | 86% (7) |
| NAIK | keduanya berlawanan (= 14 Okt) | 100% (4) — terlalu sedikit, cloud memakai baris y/y | 100% (4) |
| TURUN | sepakat / y/y berlawanan | 65% (20) / 71% (14) | 64% / 80% |

  Cloud memakai sel paling khusus yang n ≥ 10 (keduanya → y/y → inti) supaya tidak memamerkan persen dari 3–4 rilis.
- 💥 modal kecil per situasi (lentur, tebakan kuat, per $100, sejak Okt 2021 | sebelum): sepakat untung 86% (14 rilis),
  1:500 +$115, habis 1 | 17%, −$27; **y/y berlawanan untung 53% (15)**, 1:200 +$24, 1:500 +$71 (habis 2), 1:1000 +$154
  (habis 4) | 45%, +$36. Baris 💥 kini menulis "⚖️ situasi sekarang untung X% (biasa 69%)" bila situasi lebih lemah.
- **CPI 14 Okt (dicek 13 Okt 18:10 WIB):** Kalshi m/m di atas 14% / di bawah 39% → tebakan CPI DI BAWAH → emas NAIK 68%
  (detik 2). Berlawanan: y/y tersirat 3,71% > 3,6% (Kalshi y/y di atas 51%) dan Kalshi inti di atas 36% / di bawah 22%.
  Rilis serupa: NAIK detik 2 65% (sejak Okt 2021 69%); modal kecil untung 53% rilis (rata-rata tetap positif). Bila konsensus
  indeks terbit sebelum rilis, jalur indeks didahulukan dan tebakan bisa berubah otomatis.
