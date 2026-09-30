"""cloud/api/_tren.py (library standar) harus memberi status indikator yang sama persis dengan riset
(research.tren_kedepan.price_predictors, dasar persentase tren_stats.json)."""
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cloud" / "api"))
import _tren  # noqa: E402

from research.tren_kedepan import CLOUD_KEYS, price_predictors  # noqa: E402


def _daily(n=420, seed=5):
    rng = np.random.default_rng(seed)
    # tren naik, lalu turun, lalu datar: semua indikator sempat berganti arah
    drift = np.r_[np.full(n // 3, 0.004), np.full(n // 3, -0.005), np.zeros(n - 2 * (n // 3))]
    c = 1800 * np.exp(np.cumsum(drift + rng.normal(0, 0.01, n)))
    o = np.r_[c[0], c[:-1]]
    h = np.maximum(o, c) * (1 + rng.random(n) * 0.006)
    l = np.minimum(o, c) * (1 - rng.random(n) * 0.006)
    return pd.DataFrame({"open": o, "high": h, "low": l, "close": c},
                        index=pd.date_range("2025-01-01", periods=n, freq="D", tz="UTC"))


def test_status_sama_dengan_riset():
    df = _daily()
    keys = [k for k in CLOUD_KEYS if "yield" not in k and "dolar" not in k]
    seen = {k: set() for k in keys}
    for cut in range(255, len(df), 7):
        d = df.iloc[:cut + 1]
        ref = {k: int(np.nan_to_num(v[-1])) for k, v in price_predictors(d).items()}
        got = _tren.states(list(d[["open", "high", "low", "close"]].itertuples(index=False, name=None)))
        for k in keys:
            assert got[k] == ref[k], (cut, k, got[k], ref[k])
            seen[k].add(got[k])
    assert sum(len(v) >= 2 for v in seen.values()) >= 8            # sebagian besar indikator sempat berganti arah


def test_build_urut_dan_dasar():
    st = {k: 1 for k in CLOUD_KEYS}
    st["Supertrend D1"] = -1
    st["RSI14 ekstrem (berbalik)"] = 0
    out = _tren.build("XAU/USD", st)
    week = out["jangka"]["1 minggu"]
    rows = week["baris"]
    assert rows[-1]["arah"] == 0                                        # tanpa pendapat di bawah
    active = [r for r in rows if r["arah"]]
    assert [r["lebih"] for r in active] == sorted((r["lebih"] for r in active), reverse=True)
    st_row = next(r for r in rows if r["nama"] == "Supertrend D1")
    assert st_row["dasar_uji"] == round(100 - week["naik_uji"], 1)     # bearish dibandingkan dengan "selalu turun"
    assert week["bullish"] == len(CLOUD_KEYS) - 2 and week["bearish"] == 1


def test_compute_tanpa_jaringan():
    df = _daily()
    bars = [(f"{t:%Y-%m-%d}", *row) for t, row in zip(df.index, df[["open", "high", "low", "close"]].to_numpy())]
    now = datetime(2026, 2, 26, 12, tzinfo=timezone.utc)
    out = _tren.compute("x", now, fred=lambda s: list(range(40)), bars_fn=lambda k, a: bars)
    x = out["XAU/USD"]
    assert x["tanggal"] < now.date().isoformat() and "1 bulan" in x["jangka"]
    assert next(r for r in x["jangka"]["1 hari"]["baris"] if r["nama"].startswith("yield"))["arah"] == -1
    assert "bukan ramalan" in out["catatan"]
