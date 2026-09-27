"""Reduced 20-feature set for XGBoost spike quality prediction (Arsitektur v8.0).
Added premium features for institutional-grade prediction on Gold (XAUUSD)."""

import numpy as np
import pandas as pd

FEATURE_COLS = [
    "atr_5",
    "vwap_dist",
    "volatility_14",
    "rsi_7",
    "range_atr_ratio",
    "spike_intensity",
    "micro_trend",
    "macd_hist",
    "vol_anomaly",
    "bb_pos",
    "momentum_3",
    "rsi_14",
    
    # Premium features (Arsitektur v8.0)
    "vol_zscore",           # Volume Z-score
    "spread_vol_ratio",     # Spread to volume ratio
    "vol_explosion",        # Volatility explosion (ATR 5 / ATR 20)
    "ema200_dist",          # Distance to EMA 200
    "rsi_diff",             # RSI divergence proxy (RSI 7 - RSI 14)
    "choppiness_14",        # Choppiness Index 14
    "session_london",       # London session flag (08:00 - 16:00 Server Time)
    "session_us",           # US session flag (14:00 - 22:00 Server Time)
    "confluence_score",     # 21. Precision Sniper Confluence Score (0-10)
    
    # Anti-Sideways & Anti-Pucuk Features (V7)
    "adx_14",               # Average Directional Index (Trend vs Sideways)
    "upper_wick_ratio",     # Upper wick relative to total range
    "lower_wick_ratio",     # Lower wick relative to total range
    "body_atr_ratio",       # Body size relative to ATR (detect exhaustion)

    # Sideways Mean Reversion Features (V8)
    "bb_width",             # Lebar Bollinger Bands (Mendeteksi kotak sideways)
    "stoch_k",              # Stochastic K (Deteksi Overbought/Oversold)
    "stoch_d",              # Stochastic D (Deteksi Crossover pembalikan)
    
    # Early Entry Trend Features (V7.1)
    "keltner_dist_upper",   # Jarak ke Keltner Upper Band
    "keltner_dist_lower",   # Jarak ke Keltner Lower Band
    "momentum_exp"          # Momentum Expansion 3 Lilin (+1, 0, -1)
]

ALL_FEATURE_COLUMNS = [f"M15_{c}" for c in FEATURE_COLS]


def _ema(s, span):
    return s.ewm(span=span, adjust=False).mean()


def _rsi(s, period=14):
    d = s.diff()
    gain = d.where(d > 0, 0.0).rolling(period).mean()
    loss = -d.where(d < 0, 0.0).rolling(period).mean()
    rs = gain / (loss + 1e-9)
    return 100.0 - (100.0 / (1.0 + rs))


def _atr(df, period=5):
    h, l, c = df["high"], df["low"], df["close"]
    tr = pd.concat(
        [h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1
    ).max(axis=1)
    return tr.rolling(period).mean()


def _stochastic(df, k_period=14, d_period=3):
    h, l, c = df["high"], df["low"], df["close"]
    l_min = l.rolling(k_period).min()
    h_max = h.rolling(k_period).max()
    stoch_k = 100 * ((c - l_min) / (h_max - l_min + 1e-9))
    stoch_d = stoch_k.rolling(d_period).mean()
    return stoch_k.fillna(50), stoch_d.fillna(50)


def _bb(s, period=20):
    sma = s.rolling(period).mean()
    std = s.rolling(period).std()
    return sma + 2 * std, sma, sma - 2 * std


def _adx(df, period=14):
    h, l, c = df["high"], df["low"], df["close"]
    up_move = h - h.shift(1)
    down_move = l.shift(1) - l
    
    plus_dm = pd.Series(np.where((up_move > down_move) & (up_move > 0), up_move, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((down_move > up_move) & (down_move > 0), down_move, 0.0), index=df.index)
    
    tr = pd.concat([h - l, (h - c.shift(1)).abs(), (l - c.shift(1)).abs()], axis=1).max(axis=1)
    
    atr = tr.ewm(alpha=1/period, adjust=False).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1/period, adjust=False).mean() / (atr + 1e-9)
    minus_di = 100 * minus_dm.ewm(alpha=1/period, adjust=False).mean() / (atr + 1e-9)
    
    dx = (abs(plus_di - minus_di) / (plus_di + minus_di + 1e-9)) * 100
    adx = dx.ewm(alpha=1/period, adjust=False).mean()
    return adx.fillna(0)


def _vwap(df):
    tp = (df["high"] + df["low"] + df["close"]) / 3
    vol = df["volume"].astype(float).replace(0, 1)
    cum_tpv = (tp * vol).cumsum()
    cum_vol = vol.cumsum()
    return cum_tpv / cum_vol


def build_feature_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Build 20-feature matrix for all bars (vectorized)."""
    if df.empty or "close" not in df.columns:
        return pd.DataFrame(columns=ALL_FEATURE_COLUMNS)

    d = df.copy()
    c, h, lo = d["close"], d["high"], d["low"]
    o = d.get("open", d["close"])
    vol = d.get("volume", pd.Series(0, index=d.index))

    # Hours extraction for sessions
    if "timestamp" in d.columns:
        ts = pd.to_datetime(d["timestamp"])
        hour = ts.dt.hour
    else:
        try:
            hour = pd.to_datetime(d.index).hour
        except Exception:
            hour = pd.Series(12, index=d.index)

    # 1. ATR 5
    atr5 = _atr(d, 5)
    d["M15_atr_5"] = atr5

    # 2. Range ATR ratio
    rng = h - lo
    d["M15_range_atr_ratio"] = (rng / (atr5 + 1e-9)).fillna(0)

    # 3. RSI 7 & 14
    d["M15_rsi_7"] = _rsi(c, 7).fillna(50)
    d["M15_rsi_14"] = _rsi(c, 14).fillna(50)

    # 4. Bollinger Bands position
    b_up, _, b_lo = _bb(c, 20)
    bbw = (b_up - b_lo).replace(0, 1e-9)
    d["M15_bb_pos"] = ((c - b_lo) / bbw).clip(0, 1)

    # 5. Volume anomaly
    vol_f = vol.astype(float)
    vm10 = vol_f.rolling(10).mean().fillna(1)
    d["M15_vol_anomaly"] = (vol_f / (vm10 + 1)).clip(0, 20)

    # 6. Momentum 3
    d["M15_momentum_3"] = c.pct_change(3).fillna(0)

    # 7. Spike intensity
    d["M15_spike_intensity"] = ((c - o).abs() / (atr5 + 1e-9)).fillna(0)

    # 8. Micro trend (EMA10/EMA20 confluence)
    e10 = _ema(c, 10)
    e20 = _ema(c, 20)
    is_up = ((c > e20) & (e10 > e20)).astype(float)
    is_dn = ((c < e20) & (e10 < e20)).astype(float)
    d["M15_micro_trend"] = is_up - is_dn

    # 9. Volatility 14
    ret = c.pct_change().fillna(0)
    d["M15_volatility_14"] = ret.rolling(14).std().fillna(0)

    # 10. VWAP distance
    vwap = _vwap(d)
    d["M15_vwap_dist"] = (
        ((c - vwap) / vwap.replace(0, 1e-9) * 100).fillna(0)
    )

    # 11. MACD hist
    ema12 = c.ewm(span=12, adjust=False).mean()
    ema26 = c.ewm(span=26, adjust=False).mean()
    macd_l = ema12 - ema26
    macd_s = macd_l.ewm(span=9, adjust=False).mean()
    d["M15_macd_hist"] = (macd_l - macd_s).fillna(0)

    # ── Premium features (Arsitektur v8.0) ─────────────────────────────
    
    # 12. Volume Z-score (standardized volume)
    vol_mean = vol_f.rolling(20).mean().fillna(1)
    vol_std = vol_f.rolling(20).std().fillna(1)
    d["M15_vol_zscore"] = ((vol_f - vol_mean) / (vol_std + 1e-9)).clip(-3.0, 3.0)

    # 13. Spread to volume ratio
    d["M15_spread_vol_ratio"] = (rng / (vol_f + 1e-9)).clip(0, 10.0)

    # 14. Volatility explosion (ATR 5 / ATR 20)
    atr20 = _atr(d, 20)
    d["M15_vol_explosion"] = (atr5 / (atr20 + 1e-9)).fillna(1.0).clip(0.1, 5.0)

    # 15. Distance to EMA 200
    ema200 = _ema(c, 200)
    d["M15_ema200_dist"] = (((c - ema200) / ema200.replace(0, 1e-9)) * 100).fillna(0).clip(-5.0, 5.0)

    # 16. RSI difference (divergence proxy)
    d["M15_rsi_diff"] = (d["M15_rsi_7"] - d["M15_rsi_14"]).clip(-30.0, 30.0)

    # 17. Choppiness Index 14
    tr = pd.concat([rng, (h - c.shift()).abs(), (lo - c.shift()).abs()], axis=1).max(axis=1)
    tr_sum = tr.rolling(14).sum()
    h_max = h.rolling(14).max()
    l_min = lo.rolling(14).min()
    d["M15_choppiness_14"] = (100 * np.log10(tr_sum / (h_max - l_min + 1e-9)) / np.log10(14)).fillna(50.0).clip(0, 100.0)

    # 18. Session flags
    d["M15_session_london"] = ((hour >= 8) & (hour <= 16)).astype(float)
    d["M15_session_us"] = ((hour >= 14) & (hour <= 22)).astype(float)

    # 19. Confluence Score (Vectorized 0-10)
    ema9 = _ema(c, 9)
    ema21 = _ema(c, 21)
    ema55 = _ema(c, 55)
    rsi13 = _rsi(c, 13)
    
    # MACD
    ema12_m = c.ewm(span=12, adjust=False).mean()
    ema26_m = c.ewm(span=26, adjust=False).mean()
    macd_line = ema12_m - ema26_m
    sig_line = macd_line.ewm(span=9, adjust=False).mean()
    hist = macd_line - sig_line
    
    vol_sma20 = vol_f.rolling(20).mean()
    
    # Bull Score components
    bull_score = pd.Series(0.0, index=d.index)
    bull_score += np.where(ema9 > ema21, 1.0, 0.0)
    bull_score += np.where(c > ema55, 1.0, 0.0)
    bull_score += np.where((rsi13 >= 50) & (rsi13 <= 75), 1.0, 0.0)
    bull_score += np.where((hist > 0) & (macd_line > sig_line), 2.0, np.where(hist > 0, 1.0, 0.0))
    bull_score += np.where(c > vwap, 1.0, 0.0)
    bull_score += np.where(vol_f > vol_sma20 * 1.2, 1.0, 0.0)
    bull_score += np.where(c > ema9, 0.5, 0.0)
    
    # Bear Score components
    bear_score = pd.Series(0.0, index=d.index)
    bear_score += np.where(ema9 < ema21, 1.0, 0.0)
    bear_score += np.where(c < ema55, 1.0, 0.0)
    bear_score += np.where((rsi13 >= 25) & (rsi13 <= 50), 1.0, 0.0)
    bear_score += np.where((hist < 0) & (macd_line < sig_line), 2.0, np.where(hist < 0, 1.0, 0.0))
    bear_score += np.where(c < vwap, 1.0, 0.0)
    bear_score += np.where(vol_f > vol_sma20 * 1.2, 1.0, 0.0)
    bear_score += np.where(c < ema9, 0.5, 0.0)
    
    # We take the max of bull or bear score as the absolute confluence strength
    d["M15_confluence_score"] = np.maximum(bull_score, bear_score).fillna(0)

    # ── Anti-Sideways & Anti-Pucuk Features (V7) ────────────────────────
    
    # 20. ADX 14
    d["M15_adx_14"] = _adx(d, 14).clip(0, 100)
    
    # 21. Wick Ratios
    body_top = np.maximum(o, c)
    body_bottom = np.minimum(o, c)
    
    d["M15_upper_wick_ratio"] = ((h - body_top) / (rng + 1e-9)).clip(0, 1)
    d["M15_lower_wick_ratio"] = ((body_bottom - lo) / (rng + 1e-9)).clip(0, 1)
    
    # 22. Body to ATR Ratio
    body_size = (o - c).abs()
    d["M15_body_atr_ratio"] = (body_size / (atr5 + 1e-9)).clip(0, 10)

    # ── Sideways Mean Reversion Features (V8) ───────────────────────────
    
    # 23. Bollinger Bands Width
    b_up2, _, b_lo2 = _bb(c, 20)
    d["M15_bb_width"] = (b_up2 - b_lo2) / c * 1000  # Normalized width
    
    # 24. Stochastic Oscillator
    stoch_k, stoch_d = _stochastic(d, 14, 3)
    d["M15_stoch_k"] = stoch_k.clip(0, 100)
    d["M15_stoch_d"] = stoch_d.clip(0, 100)
    
    # ── Early Entry Features (V7.1) ─────────────────────────────────────
    
    # 25. Keltner Channels
    ema20 = _ema(c, 20)
    atr20 = _atr(d, 20)
    k_upper = ema20 + (2.0 * atr20)
    k_lower = ema20 - (2.0 * atr20)
    d["M15_keltner_dist_upper"] = ((c - k_upper) / (atr20 + 1e-9)).fillna(0).clip(-5.0, 5.0)
    d["M15_keltner_dist_lower"] = ((c - k_lower) / (atr20 + 1e-9)).fillna(0).clip(-5.0, 5.0)
    
    # 26. Momentum Expansion
    body_size_curr = (c - o).abs()
    body_1 = body_size_curr.shift(1)
    body_2 = body_size_curr.shift(2)
    
    exp = (body_size_curr > body_1) & (body_1 > body_2)
    bull_exp = exp & (c > o) & (c.shift(1) > o.shift(1))
    bear_exp = exp & (c < o) & (c.shift(1) < o.shift(1))
    d["M15_momentum_exp"] = bull_exp.astype(float) - bear_exp.astype(float)

    available = [col for col in ALL_FEATURE_COLUMNS if col in d.columns]
    return d[available].fillna(0).replace([np.inf, -np.inf], 0)


def extract_features(df: pd.DataFrame) -> dict:
    """Extract 20 features from OHLCV DataFrame for the last bar (consistent with vectorized)."""
    if df.empty or len(df) == 0:
        return {f"M15_{k}": 0.0 for k in FEATURE_COLS}
    matrix = build_feature_matrix(df)
    if matrix.empty:
        return {f"M15_{k}": 0.0 for k in FEATURE_COLS}
    return matrix.iloc[-1].to_dict()
