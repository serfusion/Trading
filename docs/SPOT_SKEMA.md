# 💎 Skema keluar spot & cara statistik menghitung (10 Okt 2026)

Pertanyaan pengguna: "untuk spot apakah cukup close / TP saja? Tidak seperti sinyal XAU membuka 5 entry menutup 1
sisanya biarkan? Sepertinya statistik juga menghitung semua sinyal baik XAU atau spot".

## Skema keluar (research/spot_skema.py → docs/eksternal/hasil_spot_skema.txt; 1.456 sinyal cloud 2019–2026)
| Skema | Untung (sejak Okt 2021) | Rata per sinyal | Rugi rata | Per tahun |
|---|---|---|---|---|
| **sekarang**: 100% jual di +3% atau hari ke-10 | **91%** | +1,24% | −13,5% | semua tahun + |
| 50% di +3%, 50% di +6% / hari ke-10 | 82% | +1,72% | −9,1% | semua tahun + |
| 50% di +3%, 50% tahan s.d. hari ke-10 (atau +10%) | 76% | **+2,21%** | −8,0% | semua tahun +, lebih tinggi tiap tahun |
| 20% di +3% (seperti 1 dari 5 posisi XAU), 80% di +6% / hari ke-20 | 85% | +2,13% | −14,5% | semua tahun + |
| 50% di +3%, 50% trailing low 3 hari | 49% | +1,34% | −5,4% | 2022–23 negatif |

Jawaban: skema sekarang (cukup TP) memberi WR TERTINGGI (91%). Skema bertahap seperti XAU memberi rata-rata profit lebih
tinggi (+1,7…+2,2% vs +1,24%, konsisten tiap tahun) tetapi WR turun ke 76–85%. Tidak diubah tanpa "pasang" — pilihan
pengguna: WR tinggi (sekarang) atau profit rata-rata lebih tinggi (50/50).

## Statistik di aplikasi
- Angka utama tab Statistik = sinyal 💰 saja (XAU/BTC/ETH/DOGE/ADA + lapisan), dalam uang akun MT5; 5 posisi satu sinyal
  XAU dihitung SATU sinyal (menang bila total uang > 0). Spot 💎, keranjang 🔗 dan 🌊 TIDAK masuk angka itu.
- Aplikasi 4.26: kartu "Sinyal lain (terpisah dari 💰)" menampilkan 💎 / 🔗 dalam % dan 🌊 dalam R (dari pesan di HP).
