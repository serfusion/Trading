# Sinyal 💰 lebih sering: berlapis setelah TP1 (2 Okt 2026)

Permintaan pengguna: sinyal jangan hanya satu per set — XAU, lalu BTC, lalu XAU lagi — selama WR & profit tinggi.
Skrip `research/sinyal_lapis.py` → `docs/eksternal/hasil_sinyal_lapis.txt` (mesin `sl_tangga.backtest`, opsi baru
`overlap`, `fresh`, `max_layers`; bawaan tidak berubah: XAU 1.554 sinyal +0,208R, BTC 2.097 +0,365R).

| Varian | XAU sinyal/bln | XAU total R (DD) | BTC sinyal/bln | BTC total R (DD) | Lolos |
|---|---|---|---|---|---|
| Bawaan (1 per set) | 9,6 | +324 (−44) | 16,3 | +766 (−56) | – |
| Lapis setelah TP1 | 15,1 | +570 (−93) | 26,6 | +1.323 (−109) | tidak (DD 2x) |
| **Lapis setelah TP1, lapisan lot ½** | **15,1** | **+446 (−61)** | **26,6** | **+1.040 (−84)** | **LOLOS keduanya** |
| Lapis setelah TP1, maks 2, lot ½ | 13,1 | +392 (−50) | 22,3 | +968 (−75) | XAU tidak, BTC lolos |
| Lapis kapan saja | 27,6 | +896 (−227) | 45,4 | +2.527 (−142) | tidak (DD 2,5–5x) |
| Tambah set 20/10 & 30/15 | 18,7 | +515 (−78) | 31,5 | +1.220 (−90) | tidak |
| Kategori + ⭐ / + biasa (XAU) | 12–21 | +246–262 | – | – | tidak (R/sinyal turun) |

- Sinyal lapisan = sinyal baru di set yang sama setelah TP1 sinyal sebelumnya kena (sisa posisi lama sudah SL+), jadi
  sinyal yang masih berisiko tetap paling banyak 1 per set (3 per aset). R per lapisan XAU +0,28R, BTC +0,43R (lebih
  tinggi dari rata-rata sinyal biasa).
- WR tetap ±48–50% di semua varian (ciri sistem tren: untung dari posisi yang berjalan, bukan dari WR).
- Hasil per satuan risiko (total/DD) lapis lot ½: XAU 7,4 = bawaan 7,4; BTC 12,4 vs 13,7 (sedikit lebih rendah).
  Artinya: sinyal +57–63% dan total profit +36–38%, DD +39–50% — LEBIH SERING, bukan lebih bagus per sinyal.
- Posisi terbuka bersamaan bisa banyak (maks 21–22 sinyal × 5 posisi saat tren panjang; rata-rata 1,2–1,5) →
  perlu margin.

## Uji lanjutan: lapisan SEBELUM TP1 (`research/sinyal_berita.py`, pertanyaan "sudah TP1 atau belum")

| Varian (lapisan lot ½) | XAU total/DD (bawaan 7,4) | BTC total/DD (bawaan 13,7) |
|---|---|---|
| Setelah TP1 | **7,4** (DD −61) | 12,4 (DD −84) |
| Kapan saja, breakout baru | 4,6–4,8 (DD −128 s.d. −131) | 16,1–17,1 (DD −97 s.d. −101) |
| Kapan saja, breakout baru hanya lapisan, maks 2 per set | 6,4 (DD −68) | **15,6** (DD −68, total +38%, 9/11 th lebih baik) |

→ Dipasang per aset: **XAU = lapisan setelah TP1** (lapisan sebelum TP1 merusak rasio XAU), **BTC = lapisan kapan saja
pada breakout baru, maks 2 sinyal per set** (rasio lebih baik dari bawaan, sinyal dasar tidak berubah). Riwayat lapisan:
XAU 907 lapisan WR 51% +0,28R, BTC 1.293 lapisan WR 49% +0,49R (R per posisi lapisan; lot ½).

## 📰 Sinyal setelah berita (tanda, aturan sinyal tidak berubah)

Sinyal 💰 yang entry ≤ 4 jam setelah berita AS besar (NFP, CPI, PPI, FOMC, Retail, Core PCE, Advance GDP):

| | n | WR | R/sinyal (biasa) | LAMA / BARU | tahun + |
|---|---|---|---|---|---|
| XAU | 186 | 46% | +0,45 (+0,21) | +0,41 / +0,47 | 57% |
| BTC | 72 | 51% | +0,61 (+0,37) | +1,07 / +0,44 | 60% |
| BTC searah kejutan | 17 | **82%** | +2,65 | – | sampel kecil |
| XAU searah kejutan | 68 | 41% | +0,04 | – | lemah |

Sinyal berita khusus (entry detik/menit setelah rilis) tetap TIDAK ada yang lolos (`docs/NEWS_MENIT.md`,
`NEWS_DETIK.md`, `RISET_DATA_EKSTERNAL.md` bagian 15) — yang dipasang hanya tanda 📰 pada sinyal 💰 yang memang
lahir setelah berita.

## Dipasang (izin pengguna 2 Okt 2026: "bisa kamu pasang ... tandai saja jika itu sinyal news")

- `cloud/api/_core.py`: `try_open` (filter sama untuk sinyal dasar & lapisan), `layer_ok`, state `systems[set].layers`;
  TUTUP menutup dasar + semua lapisan; heartbeat `exits` memuat lapisan. Lapisan = sinyal saja (tanpa auto order),
  id berakhiran `L`, event `lapis`, `lot_mult` 0,5, `lapis_stats`.
- `cloud/api/sinyal_lapis.json` & `sinyal_berita.json` (`python -m research.sinyal_berita ekspor`),
  `cloud/api/_berita_sinyal.py` (tanda 📰, cek searah kejutan dari Act tersimpan), `tick.signal_extras`.
  Env Vercel: `LAYER_SIGNALS=0` mematikan lapisan, `NEWS_TAG=0` mematikan tanda 📰.
- Aplikasi 3.21: pil "🔁 Lapisan • lot ½" & "📰 Setelah NFP", lot otomatis ½ untuk lapisan (juga di riwayat),
  notifikasi diawali 🔁/📰.
