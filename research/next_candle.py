"""Seberapa bisa ditebak arah candle berikutnya? (python -m research.next_candle)"""
import numpy as np

from research.run_scan import dataset

for name in ["m5_2025", "m15_2012"]:
    df = dataset(name)[0]
    body = np.sign(df.close - df.open).to_numpy()
    nxt, cur = body[1:], body[:-1]
    m = (nxt != 0) & (cur != 0)
    print(f"{name}: {len(df)} candle | tebak 'sama dengan candle sekarang' benar {np.mean(nxt[m] == cur[m]) * 100:.2f}% "
          f"| tebak 'berlawanan' benar {np.mean(nxt[m] != cur[m]) * 100:.2f}%")
