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
