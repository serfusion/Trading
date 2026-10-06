# Kenapa harga melonjak/anjlok dalam 1 detik setelah berita? Ada yang tahu duluan? (4 Okt 2026)

Pertanyaan pengguna: apakah ada "perkumpulan", komunitas, atau orang kaya yang sudah tahu arah sebelum rilis.

## Mekanisme lonjakan (umum, terdokumentasi)
1. **Data mesin, bukan manusia.** Angka rilis dikirim ke feed khusus algoritma (mis. AlphaFlash Deutsche Börse,
   ±150 indikator, latensi < 1 ms). Robot membandingkan Act vs konsensus lalu mengirim order dalam mikrodetik.
2. **Likuiditas ditarik sebelum rilis.** Market maker/HFT melebarkan spread dan menarik order beberapa detik sebelum
   rilis → buku order tipis → sedikit order saja menggeser harga jauh ("loncat").
3. **Semua orang punya konsensus yang sama.** Yang menggerakkan harga adalah KEJUTAN (Act − konsensus). Arahnya
   mengikuti kejutan: data riset kita, emas searah kejutan 82–91% di detik 2–3 (docs/HARI_H.md).
4. **Feed broker ritel lebih lambat.** Futures emas CME & obligasi bergerak dalam milidetik; harga spot di broker
   (Exness) ikut ±1–2 detik kemudian — itu sebabnya detik pertama di data kita "belum gerak" (±$0,17).

## Kebocoran yang PERNAH terbukti (pengecualian, lalu diselidiki & diperketat)
| Kasus | Apa yang terjadi | Akibat |
|---|---|---|
| FOMC 18 Sep 2013 ("no taper") | ±$600–800 juta futures emas/saham di Chicago diperdagangkan ±1–2 ms setelah 14:00, padahal sinyal butuh 7 ms dari Washington | Fed memperketat lockup (Okt 2013), embargo app dihentikan 2015 |
| Thomson Reuters – UMich sentiment (2008–2013) | Klien HFT membayar ±$6.000/bulan untuk data 2 detik lebih awal | Dihentikan atas tekanan Jaksa Agung New York |
| Medley Global Advisors (2012) | Rincian rapat FOMC bocor ke newsletter klien | Presiden Fed Richmond (Lacker) mundur 2017 |
| BLS "super users" (2024) | Ekonom BLS mengirim detail metodologi CPI perumahan ke ±50 bank/hedge fund | Diselidiki Kongres |
| Lockup Dept. Tenaga Kerja | Media menjual data ke algo lebih cepat | Lockup NFP/CPI DIHAPUS sejak 3 Jun 2020 |

## Riset akademik
- Kurov dkk. (JFQA 2019): 9 dari 20 rilis penggerak pasar menunjukkan harga futures saham/obligasi sudah bergerak ke
  arah "benar" ±30 menit sebelum rilis (±40% dari total gerak) — campuran kebocoran & ramalan dari data privat.
- Bernile, Hu & Tang (JFE 2016): ada perdagangan terinformasi selama lockup FOMC, TETAPI TIDAK ditemukan untuk NFP,
  PPI, dan GDP.
- Lucca & Moench: saham AS naik rata-rata 0,49% dalam 24 jam sebelum FOMC (apa pun keputusannya) — anomali, bukan
  tahu arah.

## Data kita sendiri (emas, tick Dukascopy & Exness)
- Gerak t0−5 → t0−1 detik searah kejutan: 50% (Exness) / 46% (Dukascopy) = lempar koin (docs/NEWS_PRA.md).
- Drift 15/30/60 menit sebelum rilis searah kejutan: 51–53% (docs/NEWS_PRA2.md) — tidak bisa dipakai.
- Pasar prediksi Kalshi menebak arah kejutan CPI 76–78% (informasi publik), tetapi entry emas ikut tebakan itu tetap
  tidak untung (docs/KALSHI.md).

## Kesimpulan
Lonjakan 1 detik terutama karena robot + likuiditas tipis + kejutan terhadap konsensus. Kebocoran nyata pernah ada
(terutama FOMC/lockup), tetapi diselidiki dan prosedurnya diperketat; untuk emas di data 2013–2026 kita, tidak ada
jejak "orang yang tahu duluan" menjelang NFP/CPI. Ritel tidak bisa bersaing di milidetik pertama → strategi tetap
sinyal 💰 dan menghindari entry di detik-detik rilis.
