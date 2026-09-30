#!/usr/bin/env bash
# Unduh dataset XAUUSD publik (GitHub) ke data/research untuk riset/backtest.
set -euo pipefail
DIR="${XAU_DATA_DIR:-data/research}"
mkdir -p "$DIR" && cd "$DIR"
fetch() {  # repo  path...
  local repo=$1; shift
  local name=${repo//\//_}
  # data sudah ada di repo kita (di-commit tanpa .git, lihat data/README.md) -> jangan unduh / jangan jalankan git di
  # dalamnya (git akan naik ke repo Trading dan mengubah sparse-checkout repo utama)
  if [ -d "$name" ] && [ ! -d "$name/.git" ]; then echo "$name: sudah ada di repo, dilewati"; return; fi
  [ -d "$name" ] || git clone -q --filter=blob:none --no-checkout --depth 1 "https://github.com/$repo" "$name"
  (cd "$name" && git sparse-checkout set --no-cone "$@" && git checkout -q HEAD)
}
fetch ejtraderLabs/historical-data XAUUSD/
fetch dineshelumalai007/xauusd-5m gold_m5_historical.csv
fetch ilahuerta-IA/backtrader-pullback-window-xauusd data/XAUUSD_5m_5Yea.csv
fetch Sai310421/xauusd-data parquet/XAUUSD_M1_90d_20260526.parquet parquet/XAGUSD_M5_90d_20260526.parquet
# multi-instrumen (research/multi_asset*.py, btc_check.py, portfolio_check.py)
fetch ejtraderLabs/historical-data XAUUSD/ '*/*h1.csv'
fetch FutureSharks/financial-data README.md
fetch ff137/bitstamp-btcusd-minute-data data/historical/ data/updates/
echo "Selesai: $DIR  (lalu: python -m research.fetch_multi NAS100_USD SPX500_USD ... BTC_USD_full)"
