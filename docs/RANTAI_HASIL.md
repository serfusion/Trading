# Rantai hasil berita (15 Okt 2026)

Keluhan pengguna: "PPI turun menjadi 55% yang awalnya 74%" lalu "4 hari hilang lagi? Pernah hingga 7 hari PPI keluar … periksa
secara menyeluruh". Dokumen ini mencatat SEMUA tempat hasil rilis (Act vs perkiraan) dipakai berita berikutnya, bug yang
ditemukan, dan perbaikannya.

## Peta ketergantungan

| Berita berikutnya | Memakai hasil | Modul | Sebelum | Sesudah |
|---|---|---|---|---|
| PPI (tebakan 74% / 44% / 82%) | CPI inti bulan acuan sama | `_ppi_wti.cpi_inti` | kartu CPI saja (hilang 6 jam setelah rilis), lalu ≤ 4 hari | kartu → kalender → Supabase `ppi_cpi`; CPI di bulan kalender sama, sebelum PPI |
| NFP / JOLTS / Fed (model 📊) | kejutan rilis lalu (`prev_s`) | `_prarilis` | memori diisi hanya saat aplikasi dibuka; memori 2 bulan lalu tetap dipakai | rekam tiap jam + hanya bila memori = rilis sebelumnya |
| NFP aturan 61% | NFP lalu di atas perkiraan | `_prediksi.untuk` | memori basi tetap dipakai | dicek kesegaran |
| CPI / Core CPI / CPI y/y (P, K\|P) | kejutan bulan lalu | `_petunjuk` | idem | idem |
| Core PPI, ISM Jasa, JOLTS (-P) | kejutan bulan lalu (berbalik) | `_petunjuk` | ISM Jasa tidak pernah punya Act otomatis | Act Nasdaq + kesegaran |
| PPI (aturan "CPI" 🧭) | kejutan CPI ≤ 10 hari | `_petunjuk` | memori dari aplikasi saja | rekam tiap jam (batas 10 hari = riset `pra_xau_dalam`) |
| Fed (model 📊) | keputusan Fed lalu | `_prarilis` | Act Fed hanya manual → `prev_s` selalu kosong | Act Nasdaq |
| Uji maju PPI (arsip_data) | CPI pekan ini saja | `research/arsip_data.pra` | CPI pekan lalu terlewat | + `ff_<senin lalu>.json` |

## Jarak CPI → PPI (ALFRED, rilis pertama 2014–2026)

Riset (`research/ppi_dasar.py`) memakai "CPI bulan acuan SAMA sudah terbit sebelum PPI" (75 rilis). Jarak hari: 1 hari (53),
2 (6), 3 (1), 4 (4), 5 (4), 6 (2), 7 (2), 14 (Feb 2026), 17 (Jan 2026), 32 (Nov 2025, shutdown).

| Aturan cloud | cocok | salah pasang | terlewat |
|---|---|---|---|
| ≤ 4 hari (14 Okt malam) | 64 | 0 | 11 |
| ≤ 7 hari | 72 | 0 | 3 |
| ≤ 20 hari | 74 | 1 (Mar 2015) | 1 |
| **bulan kalender sama, sebelum PPI (dipasang)** | **74** | **0** | 1 (shutdown 2025) |

Bulan acuan CPI = bulan rilis − 1 pada 163/163 rilis sejak 2013; PPI 148/150.

## Kenapa memori harus direkam tiap jam

Kalender ForexFactory (`ff_calendar_thisweek.json`) hanya pekan ini dan TIDAK memuat Act. Act diisi `_aktual` (BLS → FRED →
Nasdaq) saat GET /api/chat. Bila aplikasi tidak dibuka sampai pekan berganti, hasil rilis tidak pernah masuk memori.
`cloud/api/_rekam.py` kini dipanggil cron tick tiap jam: hanya bekerja ≤ 4 hari setelah berita yang dipantau terbit, tidak
menyentuh sinyal/order, env `REKAM_HASIL=0` mematikan. Hasil terlihat di respons tick (`rekam`).

## Uji

`tests/test_cloud_rekam.py`, `tests/test_cloud_ppi_wti.py::test_cpi_inti_tetap_terbaca_setelah_kartu_cpi_hilang_15okt`.
