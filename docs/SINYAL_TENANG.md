# Filter "pasar tenang" pada sinyal 💰 bot — bisa naikkan WR & profit? (3 Okt 2026)

Skrip `research/sinyal_tenang.py` → `docs/eksternal/hasil_sinyal_tenang.txt`. Sinyal = replay kode cloud ASLI
(pengaturan live, TP1 0,7R, spread asli; `data/research/eksternal/verifikasi/cloud_<aset>.csv`). Filter pada waktu
sinyal (info sebelum bar sinyal, `research/tenang.py`): berita USD high-impact 60 mnt sebelum / 120 mnt sesudah, crash
(gerak ≥ 3 ATR H1 dalam 60 mnt, 4 jam terakhir), volatilitas (ATR H1 dibanding median 20 hari). WR = hasil bersih > 0.

## Hasil (WR, R per sinyal, total R; LAMA < Okt 2021 / BARU Okt 2021+)

| XAU sinyal dasar | LAMA | BARU |
|---|---|---|
| Sekarang (semua) | 60%, +0,140R, +198R | **63%, +0,172R, +163R** |
| Lewati berita | 59%, +0,131R, +144R | 63%, +0,230R, +167R |
| Lewati crash | 59%, +0,194R, +151R | 60%, +0,165R, +100R |
| Hanya volatilitas rendah | 60%, +0,238R, +164R | 59%, +0,158R, +80R |
| **Tenang penuh (3 syarat)** | 61%, +0,383R, +145R (27% sinyal) | **57%, +0,229R, +70R** (32% sinyal) |
| Hanya volatil (> median) | 61%, +0,047R, +35R | 67%, +0,188R, +83R |

| BTC sinyal dasar | LAMA | BARU |
|---|---|---|
| Sekarang | 60%, +0,691R, +565R | **57%, +0,363R, +267R** |
| Tenang penuh | 67%, +1,314R, +329R | 58%, +0,261R, +38R |
| Hanya volatil (> median) | 53%, +0,227R, +86R | 58%, +0,527R, +234R |

- **Filter tenang TIDAK menaikkan WR** (XAU BARU 63% → 57%) dan **memangkas total profit** (XAU BARU +163R → +70R,
  BTC +267R → +38R) karena sinyal tinggal 20–32%. R per sinyal memang naik di beberapa kelompok, tetapi tidak
  konsisten antar periode (BTC volatilitas rendah: LAMA +1,09R, BARU +0,11R).
- Lewati berita (XAU): R per sinyal BARU naik (+0,23 vs +0,17), total sama, tetapi LAMA turun (−27%) → tidak konsisten.
- Sinyal tren kita justru butuh pasar bergerak; ini sejalan dengan peringkat ⚡ (volatilitas tinggi) yang sudah ada.

## WR tinggi yang tersedia

1. **TP1 0,7R** (sudah dipasang 3 Okt): WR XAU 53 → 63%, BTC 50 → 56% sejak 2021, profit sama (`docs/VERIFIKASI.md`).
2. TP lebih pendek lagi (0,3–0,5R): WR 62–72% tetapi R/sinyal turun 45–95% (`docs/SKEMA_WR.md`) → tidak disarankan.
3. **Kandidat label WR tinggi: lapisan BTC saat volatilitas ≥ 1,5 × median** — WR 78% (LAMA, n 110) / 76% (BARU, n 121),
   1,5–2×: 81% / 73%, > 2×: 73% / 84%; 9 dari 11 tahun ≥ 69% (2019 47%, 2022 56%); R +0,53 / +0,46 per sinyal (rata-rata
   lapisan BTC +0,84 / +0,40). Ditemukan setelah melihat 32 sel (kedua periode) → belum terbukti; cocok sebagai LABEL
   info "🎯 WR tinggi" di aplikasi, bukan filter (sinyal lain juga untung). Belum dipasang — menunggu izin.
- Kategori/peringkat yang ada (konf, konf+⭐, ⭐, ⚡, bronze, silver) tidak ada yang WR ≥ 70% di kedua periode.

## Kesimpulan

Menerapkan filter "tenang" ke sinyal 💰 tidak menaikkan WR maupun profit total — jangan dipasang. WR tinggi yang tetap
untung sudah dipasang (TP1 0,7R); satu kandidat label tambahan (lapisan BTC saat sangat volatil, WR ±76–78%) bisa
dipasang bila pengguna mengizinkan.
