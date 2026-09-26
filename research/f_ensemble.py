"""Uji F + ensemble 3 set parameter Donchian H1 (python -m research.f_ensemble)."""
import numpy as np
import pandas as pd

from .data import resample
from .multi_tp import fmt, simulate
from .run_scan import dataset

SETS = [(40, 15), (55, 20), (80, 30)]
F = ([1, None, None, None, None], {1: 0.1})


def main():
    m15 = dataset("m15_2012")[0]
    m5 = dataset("m5_2025")[0]
    cut = pd.Timestamp("2018-01-01", tz="UTC")
    data = {"2012-17": (resample(m15[m15.index < cut], "60min"), .30),
            "2018-22": (resample(m15[m15.index >= cut], "60min"), .30),
            "2025-26": (resample(m5, "60min"), .25)}
    plans = {
        "A  55/20 hold": lambda d, sp: simulate(d, sp, [None], {}),
        "F  55/20": lambda d, sp: simulate(d, sp, *F),
        "A-ensemble (3 set)": lambda d, sp: np.concatenate(
            [simulate(d, sp, [None], {}, ne, nx) for ne, nx in SETS]) / 3,
        "F-ensemble (3 set)": lambda d, sp: np.concatenate(
            [simulate(d, sp, *F, ne, nx) for ne, nx in SETS]) / 3,
    }
    for name, fn in plans.items():
        print(name)
        for k, (d, sp) in data.items():
            print(f"   {k}: {fmt(fn(d, sp))}")


if __name__ == "__main__":
    main()
