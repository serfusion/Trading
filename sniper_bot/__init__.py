"""Bot sniper Telegram — terpisah dari aplikasi Android & cloud (docs/SNIPER_TELEGRAM.md).

Strategi = hanya yang lolos uji bertahun-tahun di riset repo ini (angka di docs/SNIPER_TELEGRAM.md):
  listing_dip  token baru Binance yang sudah turun >= 60% dari harga 60 menit pertamanya -> beli, TP +20%, SL -50%
  spot_dip     💎 20-100 koin besar, model peluang naik +3% dalam 10 hari (port dari cloud/api/_spot.py)
  dex          peringatan selisih harga / pool baru di DEX (token_bot) — hanya info, data baru 2026
Bawaan: mode KERTAS (paper). Mode live butuh konfigurasi + kunci API milik pengguna.
"""
