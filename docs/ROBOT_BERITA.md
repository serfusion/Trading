# Robot berita (uji CPI 14 Okt 2026) — `mt5/NewsStraddle.mq5`

## Robot "milidetik" seperti HFT — apa yang dibutuhkan (dan kenapa belum realistis)
| Kebutuhan | Robot HFT institusi | Yang kita punya |
|---|---|---|
| Data rilis | Feed mesin berbayar (AlphaFlash, Bloomberg/Reuters), < 1 ms | Situs BLS/FRED gratis, ±1–3 detik |
| Lokasi server | Co-location di samping bursa (CME Aurora) | VPS umum |
| Eksekusi | Akses langsung bursa/FIX, mikrodetik | MT5 broker ritel, puluhan–ratusan ms + slippage |
| Biaya | Ribuan USD/bulan + kontrak institusi | ±$0–15/bulan |
Data kita: hentakan emas terjadi di detik 1→2 dan selesai ±2–3 detik; Act gratis baru datang ±1–3 detik → telat.
Uji "ikut kejutan" dengan latensi realistis = rugi (docs/NEWS_DETIK.md, NEWS_MENIT.md).

## Yang BISA diuji sekarang: straddle sebelum rilis (tanpa perlu tahu angka)
Satu-satunya kandidat dari riset (docs/NEWS_PRA2.md bagian 3, docs/NEWS_DETIK.md): Buy Stop + Sell Stop ±$1–2 dipasang
5 detik sebelum rilis, sisi lawan dihapus begitu satu terisi, tutup 1–3 menit. Feed Exness: +$0,48 s.d. +$0,79 per
0,01 lot (CPI pending ±$1: +$2,21, hanya 50% tahun positif); feed Dukascopy: RUGI. → BELUM TERBUKTI, uji maju lot
minimum, nilai setelah 20–30 rilis.

## Langkah (VPS / PC Windows)
1. VPS Windows dekat server Exness (atau PC yang menyala); **sinkronkan jam** (Settings → Time → Sync now). EA memakai
   jam GMT komputer.
2. MT5 login akun Exness (sarankan **Cent**, lot 0,01 → SL $5 ≈ 5 USC ≈ Rp900; slippage berita bisa lebih besar).
3. Salin `NewsStraddle.mq5` ke `File → Open Data Folder → MQL5\Experts`, buka MetaEditor, tekan **Compile** (kirim
   pesan error bila ada).
4. Buka chart **XAUUSDc** (simbol sesuai akun), tarik EA ke chart, centang *Allow Algo Trading*, tekan tombol
   **Algo Trading** sampai hijau.
5. Isi: `ReleaseUTC` = `2026.10.14 12:30` (CPI 08:30 New York = 12:30 UTC = **19:30 WIB**; cek ulang tanggal/jam di
   kalender aplikasi), `Lot` 0.01, `Distance` 1.0, `StopLoss` 5.0, `TakeProfit` 0, `CloseAfterSeconds` 180.
   Uji pertama boleh `RecordOnly = true` (hanya merekam tick, tanpa order).
6. Biarkan menyala dari ±15 menit sebelum rilis sampai ±5 menit sesudahnya. Chart menampilkan hitung mundur & status.
7. Setelah itu kirim 2 file dari `MQL5\Files`: `NewsStraddle_log.csv` (pasang/terisi/slippage/hasil) dan
   `NewsStraddle_ticks_20261014.csv` (tick T−60 s.d. T+300 detik).

## Catatan broker & risiko
- Exness membatasi leverage posisi baru 1:200 dari 15 menit sebelum s.d. 5 menit sesudah berita penting (non-ECN).
- MT5 tidak punya OCO bawaan; EA menghapus sisi lawan secepat mungkin, tetapi saat lonjakan kedua sisi bisa terisi →
  rugi dua kali. Order stop di akun nyata bisa terisi lebih jelek dari harga yang diminta.
- Tidak ada janji profit. Hentikan bila 20–30 rilis pertama rugi.
