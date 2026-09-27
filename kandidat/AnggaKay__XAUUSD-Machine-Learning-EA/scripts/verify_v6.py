import sys
import time
from pathlib import Path
import pandas as pd
import numpy as np
import struct
import joblib

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from scalpdaily.features_reduced import build_feature_matrix, ALL_FEATURE_COLUMNS

def read_hst(filepath):
    fmt = "<q4dqIq"
    rs = struct.calcsize(fmt)
    rates = []
    with open(filepath, "rb") as f:
        f.seek(148)
        while True:
            buf = f.read(rs)
            if len(buf) < rs: break
            t, o, h, l, c, v, _, _ = struct.unpack(fmt, buf)
            rates.append((t, o, h, l, c, v))
    df = pd.DataFrame(rates, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s", utc=True)
    return df

def simulate_trade(c, h, l, i, n, direction, atr_val):
    entry = c[i]
    atr_pips = max(10, int(atr_val * 10))
    sl_pips = max(40, min(80, int(atr_pips * 1.5)))
    tp_pips = max(50, min(90, int(atr_pips * 2.0)))
    be_pips = 20
    sl_dist = sl_pips * 0.10
    tp_dist = tp_pips * 0.10
    be_dist = be_pips * 0.10
    
    if direction == "BUY":
        sl = entry - sl_dist
        tp = entry + tp_dist
        be_price = entry + be_dist
        for j in range(i+1, min(i+80, n)):
            if l[j] <= sl: return sl - entry
            if h[j] >= tp: return tp_dist
            if h[j] >= be_price: sl = entry + 0.04
        return c[min(i+79, n-1)] - entry
        
    elif direction == "SELL":
        sl = entry + sl_dist
        tp = entry - tp_dist
        be_price = entry - be_dist
        for j in range(i+1, min(i+80, n)):
            if h[j] >= sl: return entry - sl
            if l[j] <= tp: return tp_dist
            if l[j] <= be_price: sl = entry - 0.04
        return entry - c[min(i+79, n-1)]

print("Loading data...")
df = read_hst(r"C:\Users\angga\AppData\Roaming\MetaQuotes\Terminal\50CA3DFB510CC5A8F28B48D1BF2A5702\history\ValburyAsiaFutures-Demo\XAUUSD5.hst")

latest_ts = df["timestamp"].max()
cutoff = latest_ts - pd.Timedelta(days=90)
df = df[df["timestamp"] >= cutoff].reset_index(drop=True)

print("Building features...")
matrix = build_feature_matrix(df)
n = len(df)
feat_start = n - len(matrix)
X_raw = matrix.values
clean = ~np.isnan(X_raw).any(axis=1)
X = X_raw[clean]
X_idx = np.where(clean)[0] + feat_start

print("Loading Models...")
model_path = Path(__file__).resolve().parent.parent / "src" / "vektor_v6" / "models" / "vektor_v6_ml.joblib"
model = joblib.load(model_path)
probs_all = model.predict_proba(X)[:, 1]

c = df['close'].values
h = df['high'].values
l = df['low'].values
tr = np.maximum(h - l, np.maximum(np.abs(h - np.roll(c, 1)), np.abs(l - np.roll(c, 1))))
tr[0] = h[0] - l[0]
atr5 = pd.Series(tr).rolling(5, min_periods=1).mean().bfill().values

# Keltner setup
ema20 = pd.Series(c).rolling(20, min_periods=1).mean().values
k_upper = ema20 + (2.0 * atr5)
k_lower = ema20 - (2.0 * atr5)

profits = []
wins = 0
losses = 0

print("Running Backtest Simulator (Vektor v6 - Keltner + AI > 0.70)...")
for idx, prob in zip(X_idx, probs_all):
    if idx < 50 or idx >= n-2: continue
    
    if atr5[idx] <= 0: continue
    
    direction = None
    if c[idx] > k_upper[idx]:
        direction = "BUY"
    elif c[idx] < k_lower[idx]:
        direction = "SELL"
        
    if direction and prob >= 0.70:
        profit = simulate_trade(c, h, l, idx, n, direction, atr5[idx])
        profits.append(profit)
        if profit > 0: wins += 1
        else: losses += 1

print("\n=== BACKTEST RESULTS (Vektor v6 - 90 DAYS) ===")
print(f"Total Trades : {len(profits)}")
print(f"Wins         : {wins}")
print(f"Losses       : {losses}")
if len(profits) > 0:
    win_rate = wins/len(profits)*100
    gross_profit = sum([p for p in profits if p>0])
    gross_loss = abs(sum([p for p in profits if p<0]))
    pf = gross_profit / gross_loss if gross_loss > 0 else float('inf')
    
    print(f"Win Rate     : {win_rate:.2f}%")
    print(f"Gross Profit : ${gross_profit * 100:.2f} (0.01 lot)")
    print(f"Gross Loss   : ${gross_loss * 100:.2f} (0.01 lot)")
    print(f"Profit Factor: {pf:.2f}")
    
    consec_loss = 0
    max_consec_loss = 0
    balance = 1000.0
    peak = 1000.0
    max_dd = 0.0
    for p in profits:
        balance += p * 100
        if balance > peak: peak = balance
        dd = (peak - balance) / peak * 100
        if dd > max_dd: max_dd = dd
        
        if p < 0:
            consec_loss += 1
            if consec_loss > max_consec_loss: max_consec_loss = consec_loss
        else:
            consec_loss = 0
            
    print(f"Max DD       : {max_dd:.2f}%")
    print(f"Max Cons Loss: {max_consec_loss}")
