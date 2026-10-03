# EA Grid Martingale (`ea/GridMartingale.mq5`) — 3 Okt 2026

Dibuat atas permintaan pengguna: "modal $400 bisa $150/bulan, tiru martingale x2 setiap loss". EA ini **terpisah dari
bot kita** (tidak menyentuh `xau_bot/` atau `cloud/`, tidak memakai sinyal 💰) dan **belum di-compile di sesi riset**
(tidak ada MetaEditor) → compile di MetaEditor, uji di Strategy Tester dan akun **demo** dulu.

## Cara kerja (sama dengan simulasi `research/martingale_ea.sim`)

1. Tidak ada posisi → buka layer 1 (`InpLotAwal`) ke arah `InpArah` (BUY saja seperti trader), setelah jeda
   `InpJedaMenit` sejak keranjang terakhir tutup, bukan akhir pekan, tidak ada berita USD penting, spread wajar.
2. Harga melawan sejauh `InpJarak` dari layer terakhir → layer baru, lot = lot terakhir × `InpPengali` (dibulatkan ke
   langkah lot; ×1,2 dari 0,07 menghasilkan 0,08 / 0,10 / … / 1,24 persis seperti deal Signal Strike).
3. Harga = rata-rata entry ± `InpTP` → tutup semua (Close All).
4. Pengaman: floating rugi ≥ `InpBatasRugiPersen`% saldo → tutup semua; Jumat ≥ `InpJamTutupJumat` → tutup semua,
   buka lagi Senin ≥ `InpJamBukaSenin`; berita USD high impact (kalender MT5, `InpMenitSebelum`/`InpMenitSesudah`) →
   tidak membuka keranjang baru (layer keranjang yang berjalan tetap ditambah). Kalender MT5 tidak tersedia di
   Strategy Tester, jadi jeda berita hanya bekerja di akun live/demo.

## Hasil uji modal $400 (`research/ea_400.py` → `docs/eksternal/hasil_ea_400.txt`)

BUY, TP rata-rata +$1,9, jeda 45 mnt (kalibrasi September 2026), Jun 2012 – Sep 2026, akun baru $400 tiap awal bulan.
Batas rugi dicek di setiap level harga (seperti tick demi tick di MT5).

| Kode | Pengaturan | Rata-rata $/bulan BARU (LAMA) | Bulan ≥ $150 BARU | Bulan akun habis BARU | Bulan rugi BARU | Total 2012–2026 |
|---|---|---|---|---|---|---|
| X2a | ×2 0,01 lot jarak $2,25, tanpa pengaman | −33 (−44) | 30% | 43% | 43% | −$6.989 |
| X2b | ×2 0,01 lot jarak $5 | −13 (−9) | 3% | 13% | 13% | −$1.735 |
| X2c | ×2 0,02 lot jarak $5 | −44 (−9) | 5% | 25% | 25% | −$3.686 |
| X2d | ×2 0,01 jarak $5 + batas rugi 50% + akhir pekan | −23 (+0) | 0% | 0% | 25% | −$1.369 |
| X2e | ×2 0,02 jarak $5 + batas rugi 50% + akhir pekan | −36 (−8) | 0% | 0% | 32% | −$3.087 |
| **X2f** | **bawaan EA: ×2 0,01 jarak $5 maks 15 + batas rugi 30% + akhir pekan** | **−15 (−4)** | **0%** | **0%** | **28%** | **−$1.325** |
| R1a | ×1,2 0,05 lot (rasio trader) jarak $2,25, tanpa pengaman | −40 (−4) | 12% | 35% | 33% | −$2.906 |
| R1b | ×1,2 0,05 + batas rugi 50% + akhir pekan | −24 (−19) | 3% | 0% | 37% | −$3.559 |
| R1c | ×1,2 0,05 + batas rugi 30% + akhir pekan | −6 (−12) | 3% | 0% | 40% | −$1.779 |
| R1d | ×1,2 0,03 + batas rugi 50% + akhir pekan | −23 (−13) | 7% | 0% | 35% | −$2.792 |
| R1e | ×1,2 0,05 jarak $3 + batas rugi 50% + akhir pekan | −22 (−7) | 7% | 0% | 33% | −$2.077 |

- **Tidak ada pengaturan dengan rata-rata positif** (BARU semua negatif; LAMA terbaik ±$0).
- Tanpa pengaman, $150/bulan memang bisa muncul (X2a: 30% bulan BARU; 2024 seluruh tahun +$2.679, 2016 +$943), tetapi
  43% bulan berakhir dengan akun habis — bulan-bulan "bagus" inilah yang terlihat di laporan trader.
- Dengan pengaman, akun tidak lagi habis total, tetapi 25–40% bulan rugi (batas rugi kena) dan median bulan selamat
  hanya $5–29 → **$150/bulan dari $400 (37,5%/bulan) tidak tercapai**. Satu akun 12 bulan (BARU): X2f bersih median
  −$155, R1c −$116.
- Batasan: jeda berita tidak bisa disimulasikan (kalender Feb–Sep 2026 tidak ada); bar M5/M15 (uji M1 vs M5 mirip);
  indikator entry trader tidak diketahui (jeda acak sebagai pendekatan); swap diabaikan (menguntungkan EA).

## Preset

| Preset | Pengali | Lot awal | Jarak | Batas rugi | Catatan |
|---|---|---|---|---|---|
| Bawaan (permintaan ×2) | 2,0 | 0,01 | 5,0 | 30% | X2f: −$15/bulan BARU, tidak pernah habis total |
| Seperti trader + pengaman | 1,2 | 0,05 | 2,25 | 30% | R1c: −$6/bulan BARU, paling ringan ruginya |
| Seperti trader persis | 1,2 | 0,05 | 2,25 | 0 (mati), akhir pekan mati, berita mati | R1a: 35% bulan akun habis |

## Cara memasang (uji)

1. Salin `ea/GridMartingale.mq5` ke `MQL5/Experts/` (MetaTrader 5 → File → Open Data Folder), buka di MetaEditor,
   Compile (F7). Bila ada error, kirim pesan error-nya.
2. Strategy Tester: simbol XAUUSDc, model "Every tick based on real ticks", 2024–2026, deposit 40.000 (USC).
   Perhatikan **Equity Drawdown Maximal**, bukan hanya Balance Drawdown.
3. Akun demo minimal 1–3 bulan sebelum uang sungguhan; hanya uang yang siap hilang.
