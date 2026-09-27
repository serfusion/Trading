import numpy as np
import pandas as pd
import joblib
from pathlib import Path

from scalpdaily.volatility import VolatilityEngine
from scalpdaily.features_reduced import extract_features as _extract_features
from vektor_v6.config import SPIKE_THRESHOLD, ML_ENABLED, ML_PROB_MIN

_volatility = VolatilityEngine()


def compute_spike(bars_m5: pd.DataFrame) -> dict:
    if bars_m5.empty or len(bars_m5) < 20:
        return {"score": 0, "breakout_side": None}
    features = _extract_features(bars_m5)
    result = _volatility.compute_spike_score(bars_m5, features)
    return result


class MLQuality:
    def __init__(self):
        models_dir = Path(__file__).resolve().parent.parent / "vektor_v6" / "models"
        model_path = models_dir / "vektor_v6_ml.joblib"
        sideways_path = models_dir / "vektor_v8_sideways.joblib"
        
        self.model = None
        self.sideways_model = None
        
        if model_path.exists():
            try:
                self.model = joblib.load(model_path)
            except Exception:
                self.model = None
                
        if sideways_path.exists():
            try:
                self.sideways_model = joblib.load(sideways_path)
            except Exception:
                self.sideways_model = None

    def check(self, bars_m5: pd.DataFrame, threshold: float = None) -> tuple:
        """Returns (allow_trade, probability) for Trend Model."""
        if threshold is None:
            threshold = ML_PROB_MIN
            
        if not ML_ENABLED or self.model is None:
            return (True, 0.5)
        if bars_m5.empty or len(bars_m5) < 30:
            return (True, 0.5)
        feat = _extract_features(bars_m5)
        if not feat:
            return (True, 0.5)
        from scalpdaily.features_reduced import ALL_FEATURE_COLUMNS
        X = pd.DataFrame([feat])
        X = X[ALL_FEATURE_COLUMNS].fillna(0).replace([np.inf, -np.inf], 0)
        
        try:
            probs = self.model.predict_proba(X.values)
            prob = float(probs[0][1]) if probs.shape[1] >= 2 else 0.5
            allow_trade = prob >= threshold
            return (allow_trade, prob)
        except Exception as e:
            import logging
            logging.getLogger("vektor_v6").error(f"ML check error: {e}")
            return (False, 0.0) # HOTFIX: Block trade completely if AI crashes

    def check_sideways(self, bars_m5: pd.DataFrame, threshold: float = 0.50) -> tuple:
        """Returns (allow_trade, probability) for Sideways Mean Reversion Model."""
        if not ML_ENABLED or self.sideways_model is None:
            return (True, 0.5)
        if bars_m5.empty or len(bars_m5) < 30:
            return (True, 0.5)
        feat = _extract_features(bars_m5)
        if not feat:
            return (True, 0.5)
        from scalpdaily.features_reduced import ALL_FEATURE_COLUMNS
        X = pd.DataFrame([feat])
        X = X[ALL_FEATURE_COLUMNS].fillna(0).replace([np.inf, -np.inf], 0)
        
        # Tidak ada lagi hotfix pemotongan 28 fitur. Biarkan 31 fitur mengalir penuh.
        X_v8 = X
            
        try:
            probs = self.sideways_model.predict_proba(X_v8.values)
            prob = float(probs[0][1]) if probs.shape[1] >= 2 else 0.5
            allow_trade = prob >= threshold
            return (allow_trade, prob)
        except Exception as e:
            import logging
            logging.getLogger("vektor_v6").error(f"ML sideways check error: {e}")
            return (False, 0.0) # HOTFIX: Block trade completely if AI crashes

