#!/usr/bin/env bash
# Unduh dataset XAUUSD publik (GitHub) ke data/research untuk riset/backtest.
set -euo pipefail
DIR="${XAU_DATA_DIR:-data/research}"
mkdir -p "$DIR" && cd "$DIR"
fetch() {  # repo  path...
  local repo=$1; shift
  local name=${repo//\//_}
  [ -d "$name" ] || git clone -q --filter=blob:none --no-checkout --depth 1 "https://github.com/$repo" "$name"
  (cd "$name" && git sparse-checkout set --no-cone "$@" && git checkout -q HEAD)
}
fetch ejtraderLabs/historical-data XAUUSD/
fetch dineshelumalai007/xauusd-5m gold_m5_historical.csv
fetch ilahuerta-IA/backtrader-pullback-window-xauusd data/XAUUSD_5m_5Yea.csv
fetch Sai310421/xauusd-data parquet/XAUUSD_M1_90d_20260526.parquet parquet/XAGUSD_M5_90d_20260526.parquet
echo "Selesai: $DIR"
