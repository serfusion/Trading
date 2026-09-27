"""Train XGBoost for Vektor Bot v6 — "Agresif Entry, Smart Exit"
Label: simulate trade with TP=10 pip target.
  - WIN  = price hits +10 pip TP before -12 pip SL
  - LOSS = price hits -12 pip SL before +10 pip TP
Strategy: SL=12, TP=10, BE=5, Trail=4
"""

import json, struct, sys, warnings
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

warnings.filterwarnings("ignore")

HST_FILE = Path(r"C:\Users\angga\AppData\Roaming\MetaQuotes\Terminal\50CA3DFB510CC5A8F28B48D1BF2A5702\history\ValburyAsiaFutures-Demo\XAUUSD5.hst")
MODEL_DIR = Path(__file__).resolve().parent.parent / "src" / "vektor_v6" / "models"
TRAINING_DIR = Path(r"C:\Users\angga\AppData\Roaming\MetaQuotes\Terminal\Common\Files\ScalpDailyTraining")

SL_PIPS = 30          # Sesuai Arsitektur v7.5 (Emas Optimized)
TP_PIPS = 45          # Sesuai Arsitektur v7.5 (Emas Optimized)
BREAKEVEN_PIPS = 20   # Sesuai Arsitektur v7.5 (Emas Optimized)
TRAIL_STEP = 0        # Sesuai Arsitektur v7.5 (Nonaktifkan trailing stop)
PIP_PRICE = 0.10
DAYS_BACK = 180

SPIKE_MIN = 12        # Sesuai config baru

from scalpdaily.features_reduced import build_feature_matrix, ALL_FEATURE_COLUMNS

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("train_v6")


def read_hst(filepath):
    fmt = "<q4dqIq"
    rs = struct.calcsize(fmt)
    rates = []
    with open(filepath, "rb") as f:
        f.seek(148)
        data = f.read(rs)
        while len(data) >= rs:
            ctm, o, h, l, c, v, sp, _ = struct.unpack_from(fmt, data, 0)
            rates.append({
                "timestamp": datetime.fromtimestamp(ctm, tz=timezone.utc),
                "open": float(o), "high": float(h), "low": float(l),
                "close": float(c), "volume": int(v),
            })
            data = f.read(rs)
    df = pd.DataFrame(rates)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


def read_daily_csvs(path: Path) -> pd.DataFrame:
    frames = []
    for f in sorted(path.glob("XAUUSD_M5_*.csv")):
        try:
            df = pd.read_csv(f, parse_dates=["timestamp"], date_format="%Y.%m.%d %H:%M")
            df = df.drop_duplicates(subset="timestamp", keep="last")
            frames.append(df)
        except Exception as e:
            log.warning(f"  Skip {f.name}: {e}")
    if not frames:
        return pd.DataFrame()
    combined = pd.concat(frames, ignore_index=True)
    combined = combined.sort_values("timestamp").drop_duplicates(
        subset="timestamp", keep="last"
    ).reset_index(drop=True)
    return combined[["timestamp", "open", "high", "low", "close", "volume"]]


def simulate_v6_trade(c, h, l, i, n, direction, atr_val=3.0):
    """
    Simulasi Realistis Bebas Bias:
    - SL/TP diatur dinamis berdasarkan ATR seperti di main.py.
    - Jika candle M5 menyentuh SL dan TP bersamaan, dianggap LOSS (Pessimistic).
    """
    entry = c[i]
    atr_pips = max(10, int(atr_val * 10))
    sl_pips = max(40, min(80, int(atr_pips * 1.5)))
    tp_pips = max(50, min(90, int(atr_pips * 2.0)))
    be_pips = 20
    
    sl_dist = sl_pips * PIP_PRICE
    tp_dist = tp_pips * PIP_PRICE
    be_dist = be_pips * PIP_PRICE

    if direction == "BUY":
        sl = entry - sl_dist
        tp = entry + tp_dist
        be_price = entry + be_dist
        for j in range(i + 1, min(i + 80, n)):
            hit_sl = l[j] <= sl
            hit_tp = h[j] >= tp
            # Pesimistic: Jika keduanya tersentuh di lilin yang sama, anggap Loss!
            if hit_sl:
                return sl - entry
            if hit_tp:
                return tp_dist
            if h[j] >= be_price:
                sl = entry + 0.04   # Move SL to BE (+4 pips)
                
    elif direction == "SELL":
        sl = entry + sl_dist
        tp = entry - tp_dist
        be_price = entry - be_dist
        for j in range(i + 1, min(i + 80, n)):
            hit_sl = h[j] >= sl
            hit_tp = l[j] <= tp
            # Pesimistic: Jika keduanya tersentuh di lilin yang sama, anggap Loss!
            if hit_sl:
                return entry - sl
            if hit_tp:
                return tp_dist
            if l[j] <= be_price:
                sl = entry - 0.04   # Move SL to BE (+4 pips)

    last_price = c[min(i + 79, n - 1)]
    if direction == "BUY":
        return last_price - entry
    return entry - last_price


def compute_labels(df):
    """Compute v6 labels for all bars. Returns spike_scores, labels."""
    from vektor_v6.direction import _keltner_channels, _ema, _adx
    
    n = len(df)
    c = df["close"].values.astype(float)
    o = df["open"].values.astype(float)
    h = df["high"].values.astype(float)
    l = df["low"].values.astype(float)
    v = df["volume"].values.astype(float)

    # Precompute indicators for the entire df to match get_direction
    ema20_s, upper_k_s, lower_k_s = _keltner_channels(df, 20, 2.0)
    ema9_s = _ema(df['close'], 9)
    adx_s, pdi_s, mdi_s = _adx(df, 14)
    
    body_s = np.abs(df['close'] - df['open'])
    avg_body_s = body_s.shift(1).rolling(5).mean()
    is_giant_s = body_s > (avg_body_s * 2.0)
    upper_wick_s = df['high'] - np.maximum(df['close'], df['open'])
    lower_wick_s = np.minimum(df['close'], df['open']) - df['low']
    bull_exp_s = is_giant_s & (df['close'] > df['open']) & (upper_wick_s < body_s * 0.5)
    bear_exp_s = is_giant_s & (df['close'] < df['open']) & (lower_wick_s < body_s * 0.5)

    ema20_arr = ema20_s.values
    upper_k_arr = upper_k_s.values
    lower_k_arr = lower_k_s.values
    ema9_arr = ema9_s.values
    adx_arr = adx_s.values
    pdi_arr = pdi_s.values
    mdi_arr = mdi_s.values
    bull_exp_arr = bull_exp_s.values
    bear_exp_arr = bear_exp_s.values

    tr = np.maximum(h[1:] - l[1:],
                    np.maximum(np.abs(h[1:] - c[:-1]),
                               np.abs(l[1:] - c[:-1])))
    tr = np.concatenate([[0], tr])
    atr5 = pd.Series(tr).rolling(5, min_periods=1).mean().bfill().values

    spike_scores = np.zeros(n)
    labels = np.full(n, -1, dtype=int)
    profits = np.zeros(n)

    for i in range(50, n - 2):
        if atr5[i] <= 0:
            continue

        direction = None
        current_adx = adx_arr[i]
        current_price = c[i]
        
        if current_adx > 20:
            up_trend = pdi_arr[i] > mdi_arr[i]
            down_trend = mdi_arr[i] > pdi_arr[i]
            
            if current_price > upper_k_arr[i] or bull_exp_arr[i]:
                direction = "BUY"
            elif current_adx > 25 and up_trend:
                if current_price >= ema20_arr[i] and c[i] > o[i]:
                    if c[i-1] < o[i-1]:
                        direction = "BUY"
                    elif current_price > ema9_arr[i]:
                        direction = "BUY"
                        
            if not direction:
                if current_price < lower_k_arr[i] or bear_exp_arr[i]:
                    direction = "SELL"
                elif current_adx > 25 and down_trend:
                    if current_price <= ema20_arr[i] and c[i] < o[i]:
                        if c[i-1] > o[i-1]:
                            direction = "SELL"
                        elif current_price < ema9_arr[i]:
                            direction = "SELL"

        if direction:
            # Pura-pura spike_score tinggi agar di-training oleh script di bawahnya
            spike_scores[i] = SPIKE_MIN 
            profit = simulate_v6_trade(c, h, l, i, n, direction, atr5[i])
            profits[i] = profit
            labels[i] = 1 if profit > 0 else 0

    return spike_scores, labels, profits, atr5

    return spike_scores, labels, profits, atr5


def main():
    log.info("=" * 60)
    log.info("VEKTOR v6 TRAINING — M5 scalper with aggressive trailing")
    log.info(f"  SL={SL_PIPS}  BE={BREAKEVEN_PIPS}  Trail={TRAIL_STEP}")
    log.info(f"  Spike threshold: {SPIKE_MIN}")
    log.info("=" * 60)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    log.info("\n[1/5] Loading data...")
    if not HST_FILE.exists():
        log.error(f"HST not found: {HST_FILE}")
        return

    df_hst = read_hst(HST_FILE)
    df_hst = df_hst[df_hst["timestamp"] >= "2020-01-01"].reset_index(drop=True)
    log.info(f"  HST (M5): {len(df_hst)} bars")

    df_csv = read_daily_csvs(TRAINING_DIR)
    if not df_csv.empty:
        df_csv["timestamp"] = df_csv["timestamp"].dt.tz_localize("UTC", ambiguous="NaT", nonexistent="NaT")
        df_csv = df_csv.dropna(subset=["timestamp"])
        log.info(f"  CSVs: {len(df_csv)} bars")
        df = pd.concat([df_hst, df_csv], ignore_index=True)
        df = df.sort_values("timestamp").drop_duplicates(
            subset="timestamp", keep="last"
        ).reset_index(drop=True)
    else:
        df = df_hst

    latest_ts = df["timestamp"].max()
    cutoff = latest_ts - pd.Timedelta(days=DAYS_BACK)
    df = df[df["timestamp"] >= cutoff].reset_index(drop=True)
    log.info(f"  Filtered to {DAYS_BACK} days: {len(df)} bars")

    if len(df) < 100:
        log.error(f"Only {len(df)} rows")
        return

    log.info("\n[2/5] Building 12-feature matrix...")
    matrix = build_feature_matrix(df)
    log.info(f"  Features: {matrix.shape}")

    n = len(df)
    feat_start = n - len(matrix)
    X_raw = matrix.values
    clean = ~np.isnan(X_raw).any(axis=1)
    X = X_raw[clean]
    X_idx = np.where(clean)[0] + feat_start
    log.info(f"  Clean samples: {len(X)}")

    log.info("\n[3/5] Computing v6 labels...")
    spike_scores, labels, profits, atr5 = compute_labels(df)

    labels_aligned = labels[X_idx]
    mask = (labels_aligned != -1) & (X_idx >= 50)
    X_d = X[mask]
    y = labels_aligned[mask]
    profit_vals = profits[X_idx][mask]

    n_spike = len(y)
    n_prof = int(y.sum())
    n_unprof = n_spike - n_prof
    prof_pct = n_prof / max(n_spike, 1) * 100
    log.info(f"  Spike bars (≥{SPIKE_MIN}): {n_spike}")
    log.info(f"  Profitable: {n_prof}/{n_spike} ({prof_pct:.1f}%)")
    log.info(f"  Avg profit: {profit_vals.mean():.4f}  Median: {np.median(profit_vals):.4f}")

    if len(np.unique(y)) < 2:
        log.error("Need both classes")
        return

    log.info("\n[4/5] Training XGBoost...")
    split = int(len(X_d) * 0.8)
    X_tr, X_va = X_d[:split], X_d[split:]
    y_tr, y_va = y[:split], y[split:]

    n_tr_prof = int(y_tr.sum())
    n_tr_unprof = len(y_tr) - n_tr_prof
    sample_weight = np.where(y_tr == 1, 1.0, n_tr_prof / max(n_tr_unprof, 1))

    import xgboost as xgb
    model = xgb.XGBClassifier(
        n_estimators=600, max_depth=7, learning_rate=0.05,
        subsample=0.85, colsample_bytree=0.85,
        min_child_weight=3,
        scale_pos_weight=1.0,
        objective="binary:logistic", random_state=42, verbosity=0,
        eval_metric="logloss",
        early_stopping_rounds=30,
    )
    model.fit(X_tr, y_tr, eval_set=[(X_va, y_va)], verbose=False,
              sample_weight=sample_weight)

    from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, confusion_matrix
    y_pred = model.predict(X_va)
    acc = accuracy_score(y_va, y_pred)
    prec = precision_score(y_va, y_pred, zero_division=0)
    rec = recall_score(y_va, y_pred, zero_division=0)
    f1 = f1_score(y_va, y_pred, zero_division=0)
    cm = confusion_matrix(y_va, y_pred)

    probs_va = model.predict_proba(X_va)[:, 1]
    avg_prob_prof = float(probs_va[y_va == 1].mean()) if y_va.sum() > 0 else 0.0
    avg_prob_unprof = float(probs_va[y_va == 0].mean()) if (len(y_va) - y_va.sum()) > 0 else 0.0
    separation = avg_prob_prof - avg_prob_unprof

    log.info(f"  Train: {len(X_tr)}  Val: {len(X_va)}")
    log.info(f"  Accuracy={acc:.4f}  F1={f1:.4f}  Precision={prec:.4f}  Recall={rec:.4f}")
    log.info(f"  CM: [{cm[0][0]},{cm[0][1]}],[{cm[1][0]},{cm[1][1]}]")
    log.info(f"  Avg prob(prof)={avg_prob_prof:.3f}  avg prob(unprof)={avg_prob_unprof:.3f}")
    log.info(f"  Separation: {separation:+.4f}")

    all_probs = model.predict_proba(X_d)[:, 1]
    log.info(f"  Prob range: [{all_probs.min():.3f}, {all_probs.max():.3f}]")
    log.info(f"  Prob median: {np.median(all_probs):.3f}")
    log.info(f"  Prob p25/p75: {np.percentile(all_probs, 25):.3f}/{np.percentile(all_probs, 75):.3f}")
    log.info(f"  Prob IQR: {np.percentile(all_probs, 75) - np.percentile(all_probs, 25):.3f}")

    if separation < 0.05:
        log.warning("  ⚠ Separation < 0.05 — model may not be useful")
    if f1 < 0.60:
        log.warning("  ⚠ F1 < 0.60 — consider adjusting features or parameters")

    log.info("\n[5/5] Saving model...")
    import joblib
    model_path = MODEL_DIR / "vektor_v6_ml.joblib"
    joblib.dump(model, model_path)
    log.info(f"  Model saved: {model_path}")

    fi = sorted(zip(ALL_FEATURE_COLUMNS, model.feature_importances_), key=lambda x: -x[1])
    top8 = [{"feature": f, "importance": round(float(i), 4)} for f, i in fi[:8]]

    def convert_numpy(obj):
        if isinstance(obj, (np.integer,)): return int(obj)
        if isinstance(obj, (np.floating,)): return float(obj)
        if isinstance(obj, np.ndarray): return obj.tolist()
        if isinstance(obj, list): return [convert_numpy(x) for x in obj]
        return obj

    metadata = {
        "trained_at": pd.Timestamp.now().isoformat(),
        "source": "train_v6.py (M5 scalper with trailing)",
        "strategy_params": {
            "SL_PIPS": SL_PIPS, "BREAKEVEN_PIPS": BREAKEVEN_PIPS,
            "TRAIL_STEP": TRAIL_STEP, "SPIKE_MIN": SPIKE_MIN,
        },
        "hst_file": str(HST_FILE),
        "hst_range": f"{df['timestamp'].iloc[0]} -> {df['timestamp'].iloc[-1]}",
        "hst_bars": len(df),
        "samples": n_spike,
        "n_profitable": n_prof,
        "n_unprofitable": n_unprof,
        "profitable_pct": round(prof_pct, 1),
        "features": len(ALL_FEATURE_COLUMNS),
        "feature_names": ALL_FEATURE_COLUMNS,
        "classes": ["LOSS", "PROFIT"],
        "val_accuracy": round(float(acc), 4),
        "val_precision": round(float(prec), 4),
        "val_recall": round(float(rec), 4),
        "val_f1": round(float(f1), 4),
        "confusion_matrix": cm.tolist(),
        "prob_separation": round(separation, 4),
        "prob_min": round(float(all_probs.min()), 4),
        "prob_max": round(float(all_probs.max()), 4),
        "prob_median": round(float(np.median(all_probs)), 4),
        "prob_p25": round(float(np.percentile(all_probs, 25)), 4),
        "prob_p75": round(float(np.percentile(all_probs, 75)), 4),
        "prob_iqr": round(float(np.percentile(all_probs, 75) - np.percentile(all_probs, 25)), 4),
        "n_train": len(X_tr),
        "n_val": len(X_va),
        "top_features": top8,
    }
    meta_path = MODEL_DIR / "metadata_v6.json"
    Path(meta_path).write_text(json.dumps(metadata, indent=2, default=convert_numpy))
    log.info(f"  Metadata: {meta_path}")

    log.info("\n" + "=" * 60)
    log.info("TRAINING COMPLETE")
    log.info(f"  Samples: {n_spike}  Profitable: {n_prof}/{n_unprof} ({prof_pct:.1f}%)")
    log.info(f"  F1={f1:.4f}  Separation={separation:+.4f}")
    log.info(f"  Model: {model_path}")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
