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
  perlu margin. BELUM dipasang di cloud (menunggu keputusan pengguna).
