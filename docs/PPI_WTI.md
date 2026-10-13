# ⛽ PPI ← minyak WTI (13 Okt 2026)

Lanjutan permintaan pengguna "lanjutkan setelahnya yaitu PPI kemudian FOMC, NFP, dll sesuai urutan release" dan riset
sesi 11 Okt yang terputus (`docs/LANJUTAN.md`, kelompok inflasi). Skrip: `research/riset_inflasi.py` (pra-registrasi 12 aturan
PPI + 11 aturan PCE), `research/ppi_wti_cek.py` (verifikasi adversarial), `research/ppi_wti.py` (angka → `cloud/api/ppi_wti.json`).

## Aturan (ditulis 11 Okt SEBELUM evaluasi)
Rata-rata WTI (FRED DCOILWTICO) 5 observasi s/d tanggal 13 bulan acuan vs bulan sebelumnya naik ≥ 5% → PPI di atas konsensus
→ emas TURUN; turun ≥ 5% → emas NAIK; selain itu tidak menebak. Alasan: peramal kurang bereaksi pada energi.

## Hasil
| | 2016–2026 | LAMA (< Okt 2021) | BARU | 2024+ |
|---|---|---|---|---|
| Arah lonjakan menit 1 (tutup kertas) | 68% (66) | 62% (26) | 73% (40) | 74% (39, 2022+) |
| Aturan mentah, lonjakan | 69% (78) | 66% (38) | 72% (40) | 75% (20) |
| Detik 1 / 2 / 5 / 10 (mentah) | 48% / 56% / 65% / 65% | 42% / 47% / 55% / 61% | 54% / 65% / 75% / 70% | |
- Permutasi keluarga (11 aturan PPI) p 0,004 (2016+) / 0,009 (2022+). Satu-satunya yang lolos dari 23 aturan PPI+PCE.
- Kepekaan: ambang 3–10% → 66–71%; rata-rata sebulan penuh 66%; feed Dukascopy 66%; rilis bersamaan (Retail dll.) 81% (16).
- Look-ahead: data WTI terakhir ≥ 25 hari sebelum rilis.
- Modal kecil (t−1 dtk, lentur, tick Exness) sejak 2022: 1:200 +$7,4/$100 (acak −$0,2, p 0,02), 51% rilis untung; LAMA −$2,5
  → jauh lebih lemah dari CPI (+$30, 72%).
- PCE: 11 aturan (nowcast Cleveland, YOY, Kalshi, kuartalan, terjemahan CPI+PPI) → 0 lolos.

## Dipasang (cloud saja, aplikasi tetap 4.36)
- `cloud/api/_ppi_wti.py` (+ `ppi_wti.json`): minyak live FRED API → FRED CSV → ETF USO (cadangan), cache Supabase `ppi_wti`
  6 jam, env PPI_WTI=0 mati; `_pra_aset.tebak_kartu` memakai `c["ppi_wti"]` untuk kartu PPI (aturan lama "kejutan CPI pekan
  itu" tidak lolos → tidak dipakai); `_pra_aset.allin` PPI = "💥 Modal kecil PPI: lemah — utamakan CPI".
- Tampilan: "PPI ▼ TURUN 69% (lonjakan menit 1)"; baris ⏱️ per detik memakai kurva PPI (detik 1 48% ⚠️ … detik 30 69%).
- PPI 15 Okt 2026: WTI 5 hari s/d 13 Sep $97,80 vs s/d 13 Agu $83,21 (+17,5%) → emas ▼ TURUN.

## Berita berikutnya (13 Okt 2026, urutan rilis) — semua 0 lolos, tidak dipasang
| Berita | Skrip | Aturan diuji | Hasil |
|---|---|---|---|
| FOMC (28 Okt) | `research/riset_fomc.py` | 9 (yield 2 th ×2, dolar, drift 24 jam/60 mnt, FOMC lalu, dot plot, aksi ×2) | lonjakan ±50%; terbaik drift 24 jam 56% (p 0,70) |
| Core PCE (29 Okt) | `research/riset_inflasi.py` | 11 (nowcast Cleveland, YOY, Kalshi, kuartalan, CPI+PPI) | 0 lolos |
| JOLTS (3 Nov), ADP, klaim, Retail, GDP, konsumen | `research/riset_lain.py` | aturan lama + 9 baru (Redbook, bensin, Kalshi GDP, GDPNow ±0,5, NFP lalu, rata 4 pekan, revisi Michigan) | 0 lolos; terdekat GDPNow ±0,5 71% (n 14) |
| NFP (6 Nov) | `research/riset_nfp.py` (11 Okt) | 25 | 0 layak; UR2 pasca-lihat 64% tidak tahan uji sadar-seleksi |
| ISM | `research/riset_ism.py` (11 Okt) | 38 | ISM Jasa "-P&REGK" 70% pasca-lihat → kandidat uji maju saja |
- Modal kecil semua berita (`research/berita_allin.py`): 7 dari ±195 uji "lolos" ≈ jumlah kebetulan; terbaik +$3–7/$100.
- Retail "selalu turun" 63% sudah diuji 11 Okt (pola tetap, p 0,36) → tidak lolos.

## 🔬 Putaran 3: metode & uji validitas lain (13 Okt 2026 — `research/riset_ppi3.py`, `research/riset_ppi3_cek.py`)
Permintaan pengguna: "untuk PPI saya masih kurang puas, cari metode lain untuk uji validitas serta riset mendalam seluruhnya".
Hasil: `docs/eksternal/hasil_riset_ppi3.txt`, `docs/eksternal/hasil_riset_ppi3_cek.txt`.
- **Data baru:** target tick ASLI Exness detik 1/2/3/5/10 + lonjakan untuk 123 rilis PPI Sep 2015–2026 (jendela yang belum ada
  diunduh); konsensus & Act CORE PPI; margin dagang PPITSS (rilis pertama); solar Gulf; pasar Kalshi PPI (KXUSPPI/KXUSPPIYOY —
  baru ada sejak Mei 2026, 2–5 rilis → tidak bisa diuji, hanya info).
- **PLAFON (angka sudah diketahui):** emas searah kejutan headline/core — lonjakan 81–86%, detik 2 74–78%, detik 5 80–85%, tetapi
  **detik 1 hanya 51–54%**. Artinya detik 1 PPI pada dasarnya acak walau angkanya sudah tahu → tidak ada metode yang bisa
  membuat detik 1 benar; core sedikit lebih menggerakkan emas (85% vs 81%).
- **10 petunjuk baru pra-registrasi** (keranjang energi WTI+bensin+solar, energi vs konsensus headline−core, margin dagang
  berbalik, energi→margin→core, kejutan CPI core/headline bulan sama, musiman, KON core, gabungan, model logistik walk-forward)
  + 12 aturan putaran 2 = keluarga 22 → **tidak ada yang lolos semua kriteria**. WTI dengan target Exness Sep 2015+ & keluarga
  22: tutup kertas 61% (LAMA 50% / BARU 69%), p 0,22/0,10 (putaran 2 dengan 11 aturan & target campuran: 68%, p 0,004).
  Keranjang energi 63% (LAMA 50 / BARU 71%). Kejutan CPI bulan sama: angka core 74% tetapi emas mentah 57% (feed 52–54%).
- **Uji validitas lain untuk aturan energi (mentah, lonjakan):**
  | metode | WTI | keranjang energi |
  |---|---|---|
  | mentah 2016–26 (LAMA / BARU) | 63% (57 / 69) | 65% (57 / 71) |
  | detik 1 / 2 / 5 / 10 | 43 / 52 / 62 / 60% | 47 / 53 / 61 / 65% |
  | bootstrap blok tahun 90% | 55–70% | 54–74% |
  | Bayes P(> 50%) / P(> 60%) | 0,99 / 0,69 | 1,00 / 0,79 |
  | mekanisme: harapan dari angka × plafon | 59% (teramati 67%) | 60% (teramati 69%) |
  | plasebo: rilis 08:30 LAIN bulan sama | 52% (650 rilis) | 52% (604) |
  | feed Exness / Dukascopy | 68 / 67% | 68 / 67% |
  | rolling 3 th | 2016–18 65%, **2018–21 42–52%**, 2022–26 68–75% | 2019–21 33%, 2022–25 81–82% |
  | holdout 2024–26 | 68% (22) | 70% (23) |
  | bersamaan Retail / sendiri | **81% (16)** / 59% (70) | 82% (17) / 60% (62) |
  | modal kecil BARU 1:200 / 1:500 (per $100, vs acak) | +$7,4 / +$20,2 (acak +$0,5, p 0,02), untung 52% | +$8,0 / +$22,9 (p 0,00) |
  Kesimpulan: efek energi KHAS PPI (plasebo 52%), sama di dua feed, tetapi BERGANTUNG REZIM (gagal 2018–2021, kuat sejak inflasi
  2022) dan keunggulannya di lonjakan/detik 5–10, bukan detik 1–2. Teramati > harapan mekanisme → sebagian bisa kebetulan.
- **Lonjakan melawan detik 0–10 saat arah benar (52 rilis):** median 0,024%, P90 0,067%, maks 0,202% harga (Jan 2017) →
  aman terhadap lonjakan: **≤ 1:400**; 1:500 pernah habis 1× padahal benar, 1:750–1:1000 2×.
- **PPI 15 Okt 2026:** energi bulan acuan WTI +17,5%, bensin +14,0%, solar +16,2% → PPI condong DI ATAS → emas TURUN; BERSAMAAN
  Retail Sales (situasi yang dulu 81%, n 16); konsensus headline − core = +0,2 → aturan "energi belum masuk konsensus" diam;
  margin dagang Agu −0,08% → diam. Tidak ada perubahan cloud/aplikasi (angka tampilan masih putaran 2; usulan: tampilkan angka
  putaran 3 yang lebih ketat 63% + baris ⚖️ bersamaan Retail — menunggu izin).
