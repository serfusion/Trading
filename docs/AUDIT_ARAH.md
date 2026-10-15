# 🔎 Audit per arah tebakan — semua berita (15 Okt 2026)

Pengguna: "Periksa news lain juga, saya curiga salah semua." Pemicu: PPI tampil "TURUN 74%" padahal angka itu MENCAMPUR tebakan
NAIK (7/7) dan TURUN (7/12). Skrip `research/audit_arah.py` → `docs/eksternal/hasil_audit_arah.txt` +
`cloud/api/pra_aset.json["per_arah"]` menghitung ulang SETIAP aturan yang bisa tampil di kartu berita, TERPISAH untuk tebakan
NAIK dan TURUN (tick Exness, harga tengah t0−1 dtk → detik 2/5/10), LAMA (< Okt 2021) / BARU, dengan pembanding TANPA syarat
(selalu NAIK / selalu TURUN di semua rilis kelompok berita itu).

## Hasil (detik 2–5, n = rilis bertebakan)
| aturan | tebakan NAIK | tebakan TURUN | catatan |
|---|---|---|---|
| ISM Jasa berbalik | 60–61% (62; pembanding 51%) | **69%** (45; lama 64–68 / baru 70–75; pembanding 48%) | baik dua arah ✅ |
| ISM Jasa + Fed daerah | 85% (20) | 50–58% (12; BARU 25%) | TURUN tidak layak |
| CPI Kalshi | 67% (18; pembanding 60–64%) | 47–53% (17) | TURUN tidak layak |
| CPI Kalshi & kejutan lalu | 89% (9) | 45% (11) | TURUN di bawah 50% |
| CPI + minyak sepakat | 60% (20) | 62% d2 → 54% d5 (24) | TURUN lemah setelah detik 2 |
| CPI minyak saja | 57–61% (51) | 51–57% (70; BARU 46–50%) | lemah |
| GDP GDPNow | 53–60% (15) | 40–55% (20) | detik 2 buruk |
| NFP pengangguran Kalshi/kejutan | 46–54% (50) | 53–56% (45) | ≈ pembanding |
| NFP + Indeed | 40% (25) | 44% (18) | di bawah 50% |
| Core PPI berbalik | 58–64% (31; pembanding 57–60%) | **37%** (30) | TURUN terbalik |
| JOLTS berbalik | **34–41%** (29) | 52–62% (21; pembanding 56–63%) | NAIK terbalik |
| Pengangguran kalender BLS (NFP) | 52–63% (60; BARU 50%) | 57% (104) | lemah |
| tren 4 jam searah petunjuk | 67–73% (81) | 57% (85) | |
| tren 4 jam berlawanan | 53–58% (78) | **45–48%** (71) | TURUN melawan tren naik < 50% |
| CPI aturan aplikasi (IDX\|K+S) | kuat 68% (53; sejak 2024 95%) | kuat 71% (7) • lemah 62% (29; sejak 2024 45%) | sudah per arah |

## Perbaikan cloud (`cloud/api/_pra_aset.py`)
- `per_arah()` + `status_arah()`: setiap tebakan memakai angka ARAH yang ditebak (rata-rata detik 2/5/10). < 52% atau lama/baru
  < 50% → **tidak ditampilkan (≈ 50:50)**; ≥ 60% & unggul ≥ 5 poin dari pembanding & lama/baru ≥ 55% & n ≥ 20 → ✅ teruji;
  ≥ 55% → ⚠️ belum terbukti; selain itu ⚠️ lemah.
- `ringkas()` (varian xau_arah), aturan pengangguran NFP, dan baris ➕ tren memakai angka per arah; tebakan yang melawan
  tren 4 jam dan dulu < 52% → "≈ 50:50 (petunjuk & tren berlawanan)".
- PPI: `_ppi_wti.pakai_cpi` per arah (docs/PPI_15OKT.md). CPI: sudah per arah (kuat/lemah).
- Setelah rilis: ⚡LIVE tingkat YAKIN per gerak detik 2 (aplikasi 4.42, `research/live_tingkat.py`).
