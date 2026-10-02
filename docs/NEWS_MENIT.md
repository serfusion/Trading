# Entry beberapa menit setelah berita, tutup beberapa menit kemudian (2 Okt 2026)

Permintaan pengguna: "sinyal setelah news dengan WR tinggi; entry beberapa menit saja lalu close, bukan hold. NFP
cenderung sell, tapi ada yang spike buy dulu setelah rilis baru sell."

Skrip: `research/news_menit.py` → `docs/eksternal/hasil_news_menit.txt`. Tick Dukascopy 2010–2026 dan tick asli Exness
2015–2026, semua rilis USD bintang 3 (NFP 161 rilis Dukascopy / 121 Exness). Keputusan di menit 0,5 / 1 / 2 / 3 / 5
setelah rilis (Act sudah diketahui), masuk 2 detik kemudian + slippage $0,30, tahan 1 / 3 / 5 / 10 menit atau
TP/SL $3 / $5. Arah: ikut kejutan, ikut gerak, lawan gerak (fade), SPIKE-BALIK (pola pengguna: spike melawan kejutan
→ masuk searah kejutan), KONFIRMASI, PULLBACK. Lolos = untung di kedua feed, periode LAMA & BARU, ≥ 60% tahun, t > 2.

## Hasil
- **2.280 kombinasi, 0 lolos.** WR tertinggi hanya 57–62% dengan rata-rata ≈ $0 (mis. NFP +2 mnt KONFIRMASI $4
  tahan 5 mnt: WR 59% / 57%, rata +$0,13 / −$0,01 per 0,01 lot).
- **Ikut arah kejutan setelah menit pertama RUGI**: NFP WR 34–51%, rata −$0,3 s.d. −$1,0; semua berita WR 35–40%
  (t −6 s.d. −8). Hentakan sudah selesai dalam 2–3 detik (`docs/HARI_H.md` bagian 6); sesudahnya harga tidak
  melanjutkan arah, malah sering mundur.
- **Pola "spike buy dulu baru sell" (NFP)**: spike ≥ $2 melawan kejutan hanya terjadi di 7–17% rilis (8–25 kali dalam
  16 tahun). Masuk searah kejutan setelah spike itu: hasil campur; satu-satunya yang positif di kedua feed = keputusan
  menit ke-2, tahan 5 mnt (Dukascopy WR 59% rata +$0,95, Exness WR 71% rata +$1,21) tetapi **n 14–17, t 1,4–1,8, LAMA
  hampir nol** → belum terbukti, kandidat uji maju lot minimum saja.

Kesimpulan: tidak ada sinyal berita beberapa menit yang WR tinggi DAN untung konsisten. Sumber untung yang teruji tetap
sinyal 💰 (skema bawaan).
