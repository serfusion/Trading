# Skema tarik-setor & EA SinyalCloud (4 Okt 2026)

Permintaan pengguna: *"EA MT5 coba terapkan supaya profit, bagaimanapun caranya harus profit — mungkin pakai sistem
deposit dan tarik dana, supaya ketika margin call masih ada uang lampau yang kita tarik, deposit lagi."*

Jawaban singkat: **tidak ada cara yang menjamin profit.** Skema tarik-setor tidak menambah uang. Uang yang ditarik lalu
disetor lagi berasal dari kantong yang sama, jadi hasil akhirnya = jumlah hasil semua trade. Skema ini hanya mengubah
*kapan* rugi terasa. Profit hanya datang dari strategi yang punya keunggulan. Di proyek ini satu-satunya yang teruji di
data lama dan 5 tahun terakhir adalah sinyal 💰. Karena itu EA dibuat untuk mengikuti sinyal 💰, dengan fitur Brankas
(pengingat tarik-setor).

Uji: `python -m research.tarik_setor` (hasil lengkap `docs/eksternal/hasil_tarik_setor.txt` / `.csv`; `... b` = bagian
B saja). **Dompet** = semua uang pengguna: setoran awal & setor ulang = uang keluar, tarikan = uang masuk, saldo akun di
akhir periode ikut dihitung. Akun habis = ekuitas ≤ 0 (stop out Exness 0%, perlindungan saldo negatif → rugi maksimal =
saldo akun). LAMA = Jun 2012 – Sep 2021, BARU = Okt 2021 – 3 Okt 2026, masing-masing mulai dari akun baru.

## A. EA grid/martingale + tarik-setor: 0 dari 56 kombinasi untung

Mesin `research/martingale_ea.sim` (BUY, TP rata-rata +$1,9, jeda 45 mnt). Opsi baru `tarik=` (bawaan tetap
"tiap keranjang", hasil lama tidak berubah). Tujuh cara tarik diuji: tiap keranjang, harian, pekanan, bulanan, saat saldo ≥ 1,5× / 2× modal, dan tidak ditarik.

| EA | BARU $/bulan (cara tarik terbaik … terburuk) | Setor ulang BARU | Uang keluar maks BARU | LAMA $/bulan |
|---|---|---|---|---|
| X2f bawaan EA v1.00 ($400, ×2, jarak $5, maks 15, batas rugi 30%) | −8,8 … −14,4 | 3–170× | $941–1.367 | −1,8 … −3,8 |
| X2a ×2 0,01 lot jarak $2,25, modal $400 | −195 … −406 | 62–75× | $12.169–24.800 | −44 … −114 |
| X2a sama, modal $200 | −100 … −259 | 79–101× | $6.262–15.800 | −20 … −85 |
| X2a sama, modal $100 | −65 … −169 | 103–141× | $4.238–10.300 | −16 … −54 |
| R1a ×1,2 0,05 lot (rasio trader), $400 | −8,3 … −42,6 | 9–27× | $1.775–3.600 | −7 … −17 |
| S1 rekonstruksi trader Signal Strike ($524) | −86 … −141 | 13–43× | $5.835–9.023 | −20 … −36 |
| Q1 ×1,2 + filter krisis "beku" + akhir pekan | −6,1 … −48,4 | 10–166× | $1.586–4.000 | −8,7 … −18,8 |
| Q4 bawaan EA v1.10 | −8,2 … −18,4 | 2–166× | $680–1.607 | −1,6 … −6,5 |

- **BARU: 0/56 positif** (rata-rata −$84/bulan), **LAMA: 0/56 positif**.
- Tarik tiap keranjang membuat 45–88% bulan terasa untung. Tetapi 1 kali akun habis menghapus berbulan-bulan tarikan,
  dan "uang keluar maks" (dana cadangan yang harus disiapkan untuk setor ulang) mencapai ribuan dolar.
- Modal lebih kecil ($100/$200) dengan lot sama = akun lebih sering habis. Rugi per bulan memang lebih kecil, tetapi tetap rugi.
- Cara tarik terbaik berbeda-beda per EA dan per periode, tergantung kapan akun habis. Tanpa tarik paling buruk untuk
  EA tanpa pengaman (X2a, R1a, S1 di BARU), tetapi tidak ada satu cara pun yang membuat hasil positif.

## B. Strategi yang punya keunggulan + risiko tetap $ per sinyal (akun $400)

Sinyal 💰 = replay kode cloud ASLI (konfigurasi live, TP1 0,7R, R bersih spread asli Exness, lapisan ½ lot;
`research/verifikasi.py`). Risiko = % dari $400, tetap dalam $. Urut waktu tutup: floating posisi bersamaan tidak dinilai,
jadi hasil nyata sedikit lebih buruk (lihat batasan di bawah).

**💰 XAU + BTC (yang diikuti EA SinyalCloud)** — LAMA n 5.035 (WR 56%, +683R, DD 121R), BARU n 4.013 (WR 61%, +691R, DD 91R):

| Risiko/sinyal | BARU $/bulan | BARU akun habis | BARU uang keluar maks | LAMA $/bulan | LAMA akun habis |
|---|---|---|---|---|---|
| 0,5% ($2) | +23,5 | 0 | $400 | +13,6 | 0 |
| **1% ($4)** | **+47,0** | **0** | **$400** | **+27,3** | **0–1** |
| 2% ($8) | +94 | 0–2 | $400–501 | +55 | 0–5 |
| 5% ($20) | +236–238 | 2–18 | $1.080–1.224 | +136–140 | 0–36 |
| 10% ($40) | +472–484 | 4–51 | $1.623–2.000 | +273–297 | 0–92 |

(Rentang = tarik tiap trade / tarik bulanan / tanpa tarik. Hasil $/bulan ketiganya hampir sama, selisih ≤ 3%.)

Per aset (BARU, risiko 1%): XAU +$24,7/bulan (DD 145R → 1× habis di $400), BTC +$22,6/bulan (DD 40R). LAMA: XAU +$12,8, BTC +$22,9.
Piramida tren (`ea/PiramidaTren.mq5`) 1%: +$14,7 BARU / +$10,9 LAMA.

Kesimpulan B:
- **Tarik-setor tidak menaikkan profit** pada strategi yang untung sekalipun. $/bulan sama, yang berubah hanya berapa kali
  akun habis dan berapa dana cadangan yang dibutuhkan.
- Gunanya hanya satu: menjalankan **risiko besar di akun kecil**, dengan tarikan lama sebagai cadangan setor ulang.
  Contoh 5%/sinyal: ±$237/bulan di BARU, tetapi akun habis 2–18× dalam 5 tahun dan perlu cadangan ±$1.100–1.200.
  Di LAMA hanya ±$140/bulan dengan sampai 36× habis. Itu bukan "pasti profit": urutan rugi yang buruk di awal bisa
  menghabiskan cadangan.
- Saran: risiko **1%/sinyal** ($4 di modal $400). BARU +$47/bulan dan LAMA +$27/bulan tanpa akun habis (LAMA 1× bila
  tarik rutin), dengan batas 10 sinyal berisiko bersamaan (di bawah).

### Batasan yang harus diketahui

- **Posisi bersamaan**: XAU bisa punya sampai 17,5 sinyal terbuka sekaligus (5 set + lapisan), XAU+BTC sampai 22
  (median 5,5–6). Batas EA `InpMaksSinyal = 10` (dihitung kasar: risiko dianggap terbuka sampai tutup, urut waktu sinyal):
  total R hampir sama (LAMA +692R vs +683R, BARU +632R vs +691R), DD turun (LAMA 85R vs 123R, BARU 68R vs 79R). Pada 1%:
  DD 85R × $4 = $340 < $400.
- **Lot minimum**: SL = 3×ATR H1 (median XAU $18, BTC $1.176). Akun **Standard** (simbol `…m`, seperti demo di screenshot):
  0,01 lot XAU = $1 per $1 → minimal $18 risiko per sinyal (4,6% dari $400, sebelum dibagi 5 posisi). Jadi **modal $400
  harus akun Cent** (`XAUUSDc`: 0,01 lot = $0,01 per $1). BTCUSDm 0,01 lot ≈ $11,8 risiko (2,9%). Cek apakah akun Cent
  punya BTC; bila tidak, BTC di Standard butuh modal ±$1.200 untuk 1%. EA melewati sinyal bila lot terlalu kecil
  (atau pakai lot minimum bila `InpBolehLotMin = true`, dengan risiko lebih besar dari rencana).
- Hasil riset = replay. Feed cloud (Twelve Data) dan harga broker berbeda beberapa sen, eksekusi bisa slip, dan sinyal yang
  terlambat > 0,5R dilewati. Hasil nyata bisa lebih buruk. 2026: XAU 💰 +56R, BTC 💰 +43R (replay), bukan jaminan untuk
  bulan depan.

## C. EA `ea/SinyalCloud.mq5` (belum di-compile di sesi — compile di MetaEditor, uji di DEMO)

Cara kerja:
1. Tiap 20 detik membaca topik ntfy **`<topik aplikasi>-data`** (JSON event yang sama dengan yang diterima aplikasi).
   Jadi sinyalnya **identik dengan cloud**, tanpa menulis ulang logika di MQL5.
2. Sinyal 💰 baru (XAU/BTC/ETH, umur ≤ 20 menit, harga belum lari > 0,5R) → buka `InpLeg` posisi (bawaan 5, dikurangi
   otomatis bila lot kecil) dengan risiko total = `InpRisikoPersen` × modal dasar. Lapisan pakai ½ risiko.
   SL/TP memakai jarak yang sama dengan sinyal, diukur dari harga broker. Posisi #1 diberi TP1 0,7R, sisanya ditahan.
3. Harga mencapai 0,7R (atau event TP1 dari cloud) → SL posisi lain dipindah ke harga buka ± 0,10 (SL+).
4. Event TUTUP/BATAL dari cloud → semua posisi sinyal itu ditutup. Cadangan bila pesan terlewat: EA menutup sendiri saat
   close H1 broker menembus channel keluar set (mis. T55/20 → 20 candle).
5. **Brankas**: membaca setoran & tarikan dari riwayat akun. Panel menampilkan modal dasar, disetor, ditarik, dan
   "dompet bersih". Notifikasi HP: "tarik $X" bila saldo ≥ modal dasar + 25% (maks 1×/hari), dan "akun hampir habis →
   setor ulang hanya dari uang tarikan; bila tarikan habis, berhenti". `InpBatasEkuitasPersen` (opsional) menutup semua
   posisi EA dan berhenti di bawah X% modal dasar.
   **EA tidak bisa menarik/menyetor uang sendiri** (MQL5 tidak punya fungsi itu). Tarik/setor tetap lewat Personal Area Exness.

Pemasangan:
1. Salin `ea/SinyalCloud.mq5` ke `MQL5/Experts/` (File > Open Data Folder), buka di MetaEditor, Compile (F7).
2. Tools > Options > Expert Advisors: centang *Allow algorithmic trading* dan *Allow WebRequest for listed URL*, tambahkan
   `https://ntfy.sh`.
3. Tempel EA di satu chart apa saja (mis. XAUUSDc H1). Isi `InpTopik` = topik di aplikasi (tanpa `-data`; jangan dibagikan).
   Risiko 1%, modal dasar 0 (= saldo sekarang) atau isi $400.
4. Notifikasi HP: Tools > Options > Notifications → MetaQuotes ID dari aplikasi MetaTrader di HP.
5. Jangan menyalakan auto order cloud (MetaApi, magic 250936+) di akun yang sama: order akan dobel.
6. Strategy Tester tidak bisa menjalankan EA ini (WebRequest tidak jalan di tester). Bukti historisnya adalah replay di
   atas. Uji maju di demo minimal 1–2 bulan sebelum memakai uang asli.

EA grid/martingale (`ea/GridMartingale.mq5`) **tidak** diberi fitur Brankas. Bagian A menunjukkan tarik-setor tidak
menyelamatkannya, jadi tidak disarankan untuk uang asli.
