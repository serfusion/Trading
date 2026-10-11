# Konteks riset "snipe X1 WR ≥ 75%" (11 Okt 2026)

Repo: /home/user/Trading (branch claude/fervent-mendel-uyancv). Laporan sebelumnya: docs/SNIPE_X1.md,
hasil mentah docs/eksternal/hasil_snipe_x1.txt. JANGAN commit/push (orkestrator yang commit). JANGAN ubah file yang
sudah ada di research/ — tulis skrip BARU di folder kerja Anda (lihat di bawah) dan impor modul repo dengan
`cd /home/user/Trading && PYTHONPATH=/home/user/Trading python3 <skrip>`.

## Chain & data
- X1 = L1 kompatibel Solana (koin XNT). DEX XDEX = fork Raydium CP-Swap, program sEsYH97wqmfnkzHedjNcw3zyJdPvUmsa9AixhS4b4fN.
- RPC publik https://rpc.mainnet.x1.xyz (300 permintaan/5 dtk, 150 rb/jam, batch JSON-RPC jalan). Helper:
  research/snipe_x1.py → rpc(), rpc_batch(), _sigs(), _tx(), _saldo_tx(), muat()/simpan() (json.gz), parse_pool().
- Data: data/research/eksternal/snipe_x1/ — pools.json.gz (1.381 pool), swap/<pool>.json.gz (transaksi 24 jam pertama
  tiap peluncuran), tanda/<pool>.json.gz (semua tanda tangan + 24 jam pertama), cadangan.json.gz (saldo vault 10 Okt),
  pasok.json.gz (pasokan token), otoritas.json.gz (status mint SEKARANG — BUKAN saat peluncuran, hati-hati bocor),
  penyandang.json.gz (pengirim XNT pertama + waktu tx pertama + jumlah tx SEKARANG per wallet pembuat & 5 pembeli awal),
  pemain.csv (untung/rugi wallet nyata 24 jam), ringkas_pool.csv, simulasi.csv, xnt_usd.json.gz (kurs harian).
- 556 peluncuran (pool pertama tiap token, pasangan WXNT), 25 Des 2025 – 9 Okt 2026.

## Simulasi & alat uji (research/snipe_x1_wr.py, research/snipe_x1_uji.py)
- Simulasi "sisip": beli 2 XNT disisipkan ke urutan transaksi asli, transaksi lain diputar ulang (x·y=k), biaya DEX
  0,28–0,30% + bot 1%/sisi. Validasi: putar ulang tanpa sisipan = cadangan on-chain (selisih ≤ 0,07%).
- `R.muat_siap()` → list peluncuran: field t0, latih (t0 < 15 Feb 2026), y0 (XNT awal pool), porsi (pasokan di pool /
  total), creator, creator_prev (jumlah peluncuran pembuat yang hasilnya sudah diketahui ≥ 24 jam sebelum t0),
  creator_prev_bagus, umur_pembuat (hari, dari tx pertama wallet pembuat), mint_auth/freeze (status SEKARANG — bocor),
  fee_bp, x_now/y_now, dan jalur[jeda] untuk jeda ∈ {0,30,60,120,300,600,900,1800,3600} detik setelah pool dibuat:
  t (detik sejak t0), v (XNT bersih bila semua dijual di titik itu), now (nilai jual sekarang), fitur saat masuk:
  n_beli, n_jual, pembeli (wallet unik non-pembuat), xnt_beli, xnt_jual, beli_maks, naik (harga/harga awal), y_masuk,
  dev_beli, dev_jual, lp_tarik, lp_tambah, wallets (daftar pembeli awal), penembak_n / penembak_rugi / wallet_dikenal
  (reputasi wallet dari peluncuran SEBELUMNYA ≥ 24 jam).
- `R.keluar(t, v, now, aturan)`: ("tp", k, T, telat) | ("tpsl", k, s, T, telat) | ("parsial", f, k1, k2, T) |
  ("modal", k, T). telat = jumlah transaksi orang lain sebelum jual kita tereksekusi.
- `R.hasil(data, jeda, aturan, saring=lambda r, J: ...)`, `R.ringkas(h)`, `R.p_acak(...)`, `R.lolos(o)`.

## SYARAT LOLOS (dikunci sebelum pencarian — jangan diubah)
- WR = % snipe dengan XNT bersih > modal 2 XNT. Pakai telat = 1 (jual tereksekusi setelah 1 transaksi orang lain).
- WR ≥ 75% DAN rata-rata ROI > 0 di paruh LATIH (t0 < 2026-02-15) DAN paruh UJI (≥ 2026-02-15); n ≥ 30 di masing-masing.
- Aturan dipilih HANYA dari LATIH; UJI dibuka sekali per kandidat final; laporkan jumlah aturan yang dicoba.
- Laporkan p_acak (subset acak UJI ukuran sama) dan koreksi Bonferroni untuk jumlah kandidat yang dibuka di UJI.

## Angka dasar (telat 1, tanpa saringan)
- masuk 60 dtk, TP 1,2×: WR latih 59%, uji 52%, ROI +18% / +30%. Telat 0 menaikkan WR ±5 poin (optimis).
- Petunjuk awal (belum teruji): porsi 50–90% WR tinggi; creator_prev > 10 (pembuat berantai) WR 13%;
  umur_pembuat 1–7 hari buruk; masuk 300 dtk + harga naik 2–5× atau xnt_beli > 20 WR ±75–78%.
- Contoh: masuk 60 dtk, TP 1,2× telat 1, saring creator_prev ≤ 10 & 0,5 < porsi ≤ 0,95 → WR 82% (latih n 51) / 89% (uji n 9):
  n uji terlalu kecil.
- Paruh UJI lebih sepi (16–25 peluncuran/bulan sejak Mei) → n uji kecil adalah kendala utama.

## TAMBAHAN setelah riset literatur & sumber data (11 Okt 2026, setelah restart container)
- Container sesi bisa restart kapan saja: SIMPAN hasil antara ke file di folder Anda sesering mungkin dan tulis hasil
  akhir juga ke <folder>/hasil.json sebelum mengembalikannya. Bila folder Anda sudah berisi skrip/cache dari percobaan
  sebelumnya, PAKAI ULANG (jangan unduh ulang).
- Literatur: tidak ada bukti independen orang LUAR mencapai WR ≥ 75% pada snipe peluncuran; angka 79–87% yang beredar
  milik pembuat/insider (beli di blok pembuatan, jual < 1–5 mnt). Bot sniper luar 40–60%, uji kertas 190 trade WR 40,5%.
  Model graduation AUROC 0,86 → 0,46 di validasi (peringatan overfitting). Daftar 35 aturan: /tmp/claude-0/-home-user-Trading/1743ebc4-1a36-5d32-ace5-0a0b581e06bb/scratchpad/wr/lit/ (lihat hasil).
- PERINGATAN DATA: 40 dari 198 peluncuran UJI X1 adalah GRADUASI degen.fyi (pool XDEX dibuat saat migrasi dari kurva,
  token sudah punya pemegang). Laporkan WR UJI dengan DAN tanpa graduasi itu. Daftar mint degen: create di file di bawah.
- Data tambahan independen (semua di periode UJI, 13 Apr – 10 Okt 2026): launchpad degen.fyi di X1, program
  degenDXVPhS7vgu3hcdzGA7T6dfCe6qTYyVM7npP3pc, 176 peluncuran. File: /home/user/Trading/data/research/eksternal/snipe_x1/
  degen/degen_trades.json.gz = {'trades': {mint: [{t, slot, user, tok, sol, vt, vs, fee, buy, sig}]}, 'create': {mint:
  [t0, pembuat, sig]}} (vt/vs = cadangan virtual token/XNT SETELAH trade; x·y=k terbukti tepat, galat ≤ 3e-12; fee 1% dari
  sol). Simulasi beli b XNT: token = vt − vs·vt/(vs + b·0,99); jual tok: sol = vs − vs·vt/(vt + tok), lalu −1% fee kurva,
  plus bot 1%/sisi. Skrip dekode: /tmp/claude-0/-home-user-Trading/1743ebc4-1a36-5d32-ace5-0a0b581e06bb/scratchpad/wr/sumber/skrip/.
- Data besar Solana pump.fun (Hugging Face, CDN terbuka, HTTP Range jalan): Slinky21/Pumpfun_v2_dataset (2,28 jt peluncuran,
  220 jt trade, 8 Agu – 8 Okt 2026, kolom slot/tx_index/is_buy/sol_amount/token_amount/virtual reserves/fee) dan
  Slinky21/Pumpfun_Memecoin_Corpus (798 rb peluncuran Jun–Jul 2026). Contoh pembaca kolom via HTTP Range:
  /tmp/claude-0/-home-user-Trading/1743ebc4-1a36-5d32-ace5-0a0b581e06bb/scratchpad/wr/sumber/skrip/hf_skema.py, hf_sampel.py. Pasar pump.fun penuh bot/Jito → hasil = uji ketahanan, bukan bukti untuk X1.
