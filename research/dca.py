"""Tabungan emas rutin (DCA) vs trading, data asli 2012-2026 (python -m research.dca).

Beli emas senilai tetap setiap awal bulan di harga pasar + selisih beli/jual kembali, tanpa leverage.
Pembanding: modal minimum agar trading trend H1 bisa memakai risiko 0,5% per set dengan lot 0,01.
"""
import numpy as np
import pandas as pd

from xau_bot.smc import atr

from .data import resample
from .harness import periods


def main():
    ps = periods()
    full = pd.concat([p.base for p in ps])
    full = full[~full.index.duplicated()]
    monthly = full["close"].resample("MS").first().dropna()
    for setor, spread_pct in [(10.0, 5.0), (10.0, 2.0)]:
        gram_oz = (setor * (1 - spread_pct / 100) / monthly).cumsum()
        invested = setor * np.arange(1, len(monthly) + 1)
        value = gram_oz * full["close"].iloc[-1]
        worst = (gram_oz * monthly / invested - 1).min()
        print(f"DCA ${setor:.0f}/bulan {monthly.index[0]:%Y-%m} s/d {full.index[-1]:%Y-%m}, selisih beli {spread_pct}%: "
              f"setor ${invested[-1]:,.0f} -> nilai ${value.iloc[-1]:,.0f} "
              f"({(value.iloc[-1] / invested[-1] - 1) * 100:+.0f}%), {gram_oz.iloc[-1] * 31.1035:.1f} gram, "
              f"posisi terburuk selama menabung {worst * 100:+.0f}%")
    # per tahun mulai menabung: hasil sampai akhir data
    print("Hasil DCA 5 tahun (selisih 5%) per tahun mulai:")
    for y in range(2012, 2022):
        m = monthly[(monthly.index.year >= y) & (monthly.index.year < y + 5)]
        oz = (10 * 0.95 / m).sum()
        end_px = full["close"][full.index < pd.Timestamp(f"{y + 5}-01-01", tz="UTC")].iloc[-1]
        print(f"   {y}-{y + 4}: setor $600 -> ${oz * end_px:,.0f} ({(oz * end_px / 600 - 1) * 100:+.0f}%)")
    print("Modal minimum trading trend H1 (SL 3xATR20, lot 0,01 = 1 oz) untuk risiko 0,5% per set:")
    for p in ps:
        H = resample(p.base, "60min")
        risk = 3 * atr(H, 20)[25:]
        med = float(np.median(risk))
        print(f"   {p.name}: SL median ${med:,.0f} per 0,01 lot -> akun standar ${med / 0.005:,.0f}, "
              f"akun Cent ${med / 0.005 / 100:,.0f}")


if __name__ == "__main__":
    main()
