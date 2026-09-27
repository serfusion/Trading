"""Train XGBoost for Vektor Bot v6/v7/v8 — Optuna Bayesian Hyperparameter Optimization.
Specifically optimized for Arsitektur v8.0 20-feature set.
Objective: Maximize Validation Precision + Class Probability Separation.
"""

import json
import struct
import sys
import warnings
import logging
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
import optuna
import joblib
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, confusion_matrix

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

warnings.filterwarnings("ignore")
optuna.logging.set_verbosity(optuna.logging.WARNING)

HST_FILE = Path(r"C:\Users\angga\AppData\Roaming\MetaQuotes\Terminal\50CA3DFB510CC5A8F28B48D1BF2A5702\history\ValburyAsiaFutures-Demo\XAUUSD5.hst")
MODEL_DIR = Path(__file__).resolve().parent.parent / "src" / "vektor_v6" / "models"
TRAINING_DIR = Path(r"C:\Users\angga\AppData\Roaming\MetaQuotes\Terminal\Common\Files\ScalpDailyTraining")

# Exit Strategy Simulation Settings (Arsitektur v7.5 & v8.0)
SL_PIPS = 30          
TP_PIPS = 45          
BREAKEVEN_PIPS = 20   
TRAIL_STEP = 0        # Trailing stop disabled
PIP_PRICE = 0.10
DAYS_BACK = 60
SPIKE_MIN = 12        

from scalpdaily.features_reduced import build_feature_matrix, ALL_FEATURE_COLUMNS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("train_optuna")


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


def simulate_v6_trade(c, h, l, i, n, direction, atr_pips):
    entry = c[i]
    spread = 0.3  # Added spread penalty for XAUUSD (30 pips / 3 points)
    
    # Kelas A Dynamic ATR Exit Parameters (Emas $4500 Adaptif)
    sl_pips = min(55, max(30, int(atr_pips * 2.0)))
    tp_pips = int(sl_pips * 1.5)
    be_pips = 15
    trail_pips = 10
    
    sl_dist = sl_pips * PIP_PRICE
    tp_dist = tp_pips * PIP_PRICE
    be_dist = be_pips * PIP_PRICE
    trail_dist = trail_pips * PIP_PRICE

    # Track best price for breakeven and trailing
    best_price = entry
    sl_moved_to_be = False

    if direction == "BUY":
        entry = entry + spread # Buy at Ask
        sl = entry - sl_dist
        tp = entry + tp_dist
        be_price = entry + be_dist
        trail_activated = False
        for j in range(i + 1, min(i + 80, n)):
            if h[j] >= tp:
                return tp_dist
            if not trail_activated:
                if h[j] >= be_price:
                    sl = entry + 0.04   # Move SL to BE (+4 pips)
                    trail_activated = True
                elif l[j] <= sl:
                    return l[j] - entry
            else:
                if trail_dist > 0:
                    new_sl = h[j] - trail_dist
                    if new_sl > sl + 0.005:
                        sl = new_sl
                if l[j] <= sl:
                    return sl - entry

    elif direction == "SELL":
        # Sell at Bid, but SL and TP evaluated at Ask (h[j] + spread, l[j] + spread)
        sl = entry + sl_dist
        tp = entry - tp_dist
        be_price = entry - be_dist
        trail_activated = False
        for j in range(i + 1, min(i + 80, n)):
            if (l[j] + spread) <= tp:
                return tp_dist
            if not trail_activated:
                if (l[j] + spread) <= be_price:
                    sl = entry - 0.04   # Move SL to BE (+4 pips)
                    trail_activated = True
                elif (h[j] + spread) >= sl:
                    return entry - (h[j] + spread)
            else:
                if trail_dist > 0:
                    new_sl = (l[j] + spread) + trail_dist
                    if new_sl < sl - 0.005:
                        sl = new_sl
                if (h[j] + spread) >= sl:
                    return entry - sl

    last_price = c[min(i + 79, n - 1)]
    if direction == "BUY":
        return last_price - entry
    return entry - last_price


def compute_labels(df):
    n = len(df)
    c = df["close"].values.astype(float)
    h = df["high"].values.astype(float)
    l = df["low"].values.astype(float)
    v = df["volume"].values.astype(float)

    tr = np.maximum(h[1:] - l[1:],
                    np.maximum(np.abs(h[1:] - c[:-1]),
                               np.abs(l[1:] - c[:-1])))
    tr = np.concatenate([[0], tr])
    atr5 = pd.Series(tr).rolling(5, min_periods=1).mean().bfill().values
    vma = pd.Series(v).rolling(20, min_periods=1).mean().bfill().values
    vsd = pd.Series(v).rolling(20, min_periods=1).std().fillna(1).values

    spike_scores = np.zeros(n)
    labels = np.full(n, -1, dtype=int)
    profits = np.zeros(n)

    # Replicate Confluence Score logic
    ema9 = pd.Series(c).ewm(span=9, adjust=False).mean().values
    ema21 = pd.Series(c).ewm(span=21, adjust=False).mean().values
    ema55 = pd.Series(c).ewm(span=55, adjust=False).mean().values
    
    # RSI
    delta = pd.Series(c).diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=13).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=13).mean()
    rs = gain / (loss + 1e-9)
    rsi13 = (100 - (100 / (1 + rs))).fillna(50).values
    
    # MACD
    ema12_m = pd.Series(c).ewm(span=12, adjust=False).mean().values
    ema26_m = pd.Series(c).ewm(span=26, adjust=False).mean().values
    macd_line = ema12_m - ema26_m
    sig_line = pd.Series(macd_line).ewm(span=9, adjust=False).mean().values
    hist = macd_line - sig_line
    
    # VWAP
    tp = (df["high"] + df["low"] + df["close"]) / 3
    vol_f = df["volume"].replace(0, 1)
    vwap = ((tp * vol_f).cumsum() / vol_f.cumsum()).values
    
    vol_sma20 = pd.Series(v).rolling(20).mean().fillna(0).values
    
    for i in range(50, n - 2):
        if atr5[i] <= 0:
            continue

        rng = h[i] - l[i]
        rp = min(30, max(0, (rng / max(atr5[i], 0.1)) * 20))

        mv, sv = vma[i], vsd[i]
        if mv > 0 and sv > 0.5:
            vz = (v[i] - mv) / max(sv, 0.5)
            vp = min(30, max(0, vz * 5))
        elif v[i] > 1:
            vp = min(30, max(0, (v[i] / max(mv, 1) - 1) * 15))
        else:
            vp = 0

        m1 = abs(c[i] / c[i - 1] - 1) * 100
        m3 = abs(c[i] / c[i - 3] - 1) * 100 if i >= 3 else 0
        ma = abs(c[i] - 2 * c[i - 1] + c[i - 2]) / max(c[i], 1) * 100 if i >= 2 else 0
        mp = min(30, max(0, m1 * 30 + m3 * 10 + ma * 100))

        ph = h[i - 20:i].max()
        pl = l[i - 20:i].min()
        bp = 10 if (c[i] > ph or c[i] < pl) else 0
        spike_scores[i] = min(100, rp + vp + mp + bp)

        if spike_scores[i] >= SPIKE_MIN:
            bull_score = 0.0
            bear_score = 0.0
            
            if ema9[i] > ema21[i]: bull_score += 1.0
            if ema9[i] < ema21[i]: bear_score += 1.0
            
            if c[i] > ema55[i]: bull_score += 1.0
            if c[i] < ema55[i]: bear_score += 1.0
            
            if 50 <= rsi13[i] <= 75: bull_score += 1.0
            if 25 <= rsi13[i] <= 50: bear_score += 1.0
            
            if hist[i] > 0 and macd_line[i] > sig_line[i]: bull_score += 2.0
            elif hist[i] > 0: bull_score += 1.0
            
            if hist[i] < 0 and macd_line[i] < sig_line[i]: bear_score += 2.0
            elif hist[i] < 0: bear_score += 1.0
            
            if c[i] > vwap[i]: bull_score += 1.0
            if c[i] < vwap[i]: bear_score += 1.0
            
            if v[i] > vol_sma20[i] * 1.2: 
                bull_score += 1.0
                bear_score += 1.0
                
            if c[i] > ema9[i]: bull_score += 0.5
            if c[i] < ema9[i]: bear_score += 0.5

            direction = None
            if bull_score >= 5.0:
                direction = "BUY"
            elif bear_score >= 5.0:
                direction = "SELL"

            if direction:
                atr_pips = int(atr5[i] * 10)
                profit = simulate_v6_trade(c, h, l, i, n, direction, atr_pips)
                profits[i] = profit
                labels[i] = 1 if profit > 0 else 0

    return spike_scores, labels, profits


def main():
    log.info("=" * 60)
    log.info("VEKTOR v8.0 OPTUNA TUNING — Premium 21-Feature Bayesian Optimizer (Confluence AI)")
    log.info(f"  SL={SL_PIPS}  BE={BREAKEVEN_PIPS}  Trail={TRAIL_STEP}")
    log.info("=" * 60)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    log.info("[1/5] Loading files & CSVs...")
    if not HST_FILE.exists():
        log.error(f"HST not found: {HST_FILE}")
        return

    df_hst = read_hst(HST_FILE)
    df_hst = df_hst[df_hst["timestamp"] >= "2020-01-01"].reset_index(drop=True)
    df_csv = read_daily_csvs(TRAINING_DIR)

    if not df_csv.empty:
        df_csv["timestamp"] = df_csv["timestamp"].dt.tz_localize("UTC", ambiguous="NaT", nonexistent="NaT")
        df = pd.concat([df_hst, df_csv], ignore_index=True)
        df = df.sort_values("timestamp").drop_duplicates(subset="timestamp", keep="last").reset_index(drop=True)
    else:
        df = df_hst

    latest_ts = df["timestamp"].max()
    cutoff = latest_ts - pd.Timedelta(days=DAYS_BACK)
    df = df[df["timestamp"] >= cutoff].reset_index(drop=True)
    log.info(f"  Data range: {df['timestamp'].min()} -> {df['timestamp'].max()}")
    log.info(f"  Total bars: {len(df)}")

    log.info("[2/5] Building Premium 21-Feature matrix...")
    matrix = build_feature_matrix(df)
    
    n = len(df)
    feat_start = n - len(matrix)
    X_raw = matrix.values
    clean = ~np.isnan(X_raw).any(axis=1)
    X = X_raw[clean]
    X_idx = np.where(clean)[0] + feat_start

    log.info("[3/5] Labeling and splitting...")
    _, labels, profits = compute_labels(df)

    labels_aligned = labels[X_idx]
    mask = (labels_aligned != -1) & (X_idx >= 50)
    X_d = X[mask]
    y = labels_aligned[mask]
    profit_vals = profits[X_idx][mask]

    n_spike = len(y)
    n_prof = int(y.sum())
    prof_pct = n_prof / max(n_spike, 1) * 100
    log.info(f"  Spikes: {n_spike}  Profitable: {n_prof} ({prof_pct:.1f}%)")

    if len(np.unique(y)) < 2:
        log.error("Need both classes to train.")
        return

    # Train / Val Split (80/20)
    split = int(len(X_d) * 0.8)
    global X_tr, X_va, y_tr, y_va
    X_tr, X_va = X_d[:split], X_d[split:]
    y_tr, y_va = y[:split], y[split:]

    log.info("[4/5] Launching Optuna Bayesian Hyperparameter Search (50 trials)...")
    
    n_tr_prof = int(y_tr.sum())
    n_tr_unprof = len(y_tr) - n_tr_prof
    sample_weight = np.where(y_tr == 1, 1.0, n_tr_prof / max(n_tr_unprof, 1))

    def objective(trial):
        params = {
            "n_estimators": trial.suggest_int("n_estimators", 150, 750),
            "max_depth": trial.suggest_int("max_depth", 3, 7),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.12),
            "subsample": trial.suggest_float("subsample", 0.65, 0.90),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.65, 0.90),
            "min_child_weight": trial.suggest_int("min_child_weight", 2, 8),
            "gamma": trial.suggest_float("gamma", 0.0, 4.0),
            "scale_pos_weight": trial.suggest_float("scale_pos_weight", 0.8, 1.4),
            "objective": "binary:logistic",
            "random_state": 42,
            "eval_metric": "logloss",
            "n_jobs": -1
        }
        
        model = xgb.XGBClassifier(**params)
        model.fit(X_tr, y_tr, eval_set=[(X_va, y_va)], verbose=False, sample_weight=sample_weight)
        
        probs_va = model.predict_proba(X_va)[:, 1]
        y_pred = model.predict(X_va)
        
        prec = precision_score(y_va, y_pred, zero_division=0)
        f1 = f1_score(y_va, y_pred, zero_division=0)
        
        avg_prob_prof = float(probs_va[y_va == 1].mean()) if y_va.sum() > 0 else 0.5
        avg_prob_unprof = float(probs_va[y_va == 0].mean()) if (len(y_va) - y_va.sum()) > 0 else 0.5
        separation = avg_prob_prof - avg_prob_unprof
        
        if f1 < 0.48 or prec < 0.60:
            return 0.0
            
        # Target: Maximize Precision and Probability Separation
        return float(prec + 0.40 * separation)

    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=50)

    best_trial = study.best_trial
    log.info(f"  Optuna Best Score: {best_trial.value:.4f}")
    log.info("  Optuna Best Parameters:")
    for k, v in best_trial.params.items():
        log.info(f"    {k}: {v}")

    # Retrain on train set with best parameters
    best_params = best_trial.params
    best_params.update({
        "objective": "binary:logistic",
        "random_state": 42,
        "eval_metric": "logloss",
        "n_jobs": -1
    })
    
    final_model = xgb.XGBClassifier(**best_params)
    final_model.fit(X_tr, y_tr, eval_set=[(X_va, y_va)], verbose=False, sample_weight=sample_weight)

    # Evaluate
    y_pred = final_model.predict(X_va)
    acc = accuracy_score(y_va, y_pred)
    prec = precision_score(y_va, y_pred, zero_division=0)
    rec = recall_score(y_va, y_pred, zero_division=0)
    f1 = f1_score(y_va, y_pred, zero_division=0)
    cm = confusion_matrix(y_va, y_pred)

    probs_va = final_model.predict_proba(X_va)[:, 1]
    avg_prob_prof = float(probs_va[y_va == 1].mean()) if y_va.sum() > 0 else 0.0
    avg_prob_unprof = float(probs_va[y_va == 0].mean()) if (len(y_va) - y_va.sum()) > 0 else 0.0
    separation = avg_prob_prof - avg_prob_unprof

    log.info("\n[5/5] Final Model Evaluation (Validation):")
    log.info(f"  Accuracy={acc:.4f}  F1={f1:.4f}  Precision={prec:.4f}  Recall={rec:.4f}")
    log.info(f"  CM: [{cm[0][0]},{cm[0][1]}],[{cm[1][0]},{cm[1][1]}]")
    log.info(f"  Avg prob(prof)={avg_prob_prof:.3f}  avg prob(unprof)={avg_prob_unprof:.3f}")
    log.info(f"  Separation: {separation:+.4f}")

    # Save Best Model
    model_path = MODEL_DIR / "vektor_v6_ml.joblib"
    joblib.dump(final_model, model_path)
    log.info(f"  Model saved successfully: {model_path}")

    # Save Metadata
    all_probs = final_model.predict_proba(X_d)[:, 1]
    fi = sorted(zip(ALL_FEATURE_COLUMNS, final_model.feature_importances_), key=lambda x: -x[1])
    top8 = [{"feature": f, "importance": round(float(i), 4)} for f, i in fi[:8]]

    def convert_numpy(obj):
        if isinstance(obj, (np.integer,)): return int(obj)
        if isinstance(obj, (np.floating,)): return float(obj)
        if isinstance(obj, np.ndarray): return obj.tolist()
        if isinstance(obj, list): return [convert_numpy(x) for x in obj]
        return obj

    metadata = {
        "trained_at": pd.Timestamp.now().isoformat(),
        "source": "train_optuna.py (Bayesian Optimized 20-Feature)",
        "strategy_params": {
            "SL_PIPS": SL_PIPS, "BREAKEVEN_PIPS": BREAKEVEN_PIPS,
            "TRAIL_STEP": TRAIL_STEP, "SPIKE_MIN": SPIKE_MIN,
        },
        "optuna_best_score": round(float(best_trial.value), 4),
        "best_hyperparameters": best_trial.params,
        "hst_bars": len(df),
        "samples": n_spike,
        "n_profitable": n_prof,
        "profitable_pct": round(prof_pct, 1),
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
        "top_features": top8,
    }
    meta_path = MODEL_DIR / "metadata_v6.json"
    meta_path.write_text(json.dumps(metadata, indent=2, default=convert_numpy))
    log.info(f"  Metadata saved: {meta_path}")

    log.info("\n" + "=" * 60)
    log.info("BAYESIAN OPTIMIZATION TRAINING COMPLETE")
    log.info(f"  Precision={prec:.4f}  Separation={separation:+.4f}")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
