"""Laporan world_lab (python -m research.world_report). Jalankan research.world_lab dulu."""
import numpy as np
import pandas as pd

from .run_scan import DATA


def main():
    df = pd.read_pickle(DATA / "world_lab.pkl")
    trades = pd.read_pickle(DATA / "world_lab_trades.pkl")
    n = len(df)
    print(f"Pasangan diuji: {n}. Bila tidak ada keunggulan sama sekali, sekitar {n * 0.023:.0f} pasangan tetap "
          f"'lolos' t>2 di periode uji hanya karena kebetulan, dan ±{n * 0.023 ** 2:.1f} lolos di latih DAN uji.")
    print(f"Teramati: uji t>2 = {(df.uji_t > 2).sum()}, latih t>2 DAN uji t>2 = "
          f"{((df.latih_t > 2) & (df.uji_t > 2)).sum()}\n")

    print("=== PER METODE (periode uji, semua instrumen) ===")
    g = df.groupby(["group", "method"]).agg(
        instrumen=("inst", "count"), untung=("uji_avg", lambda v: (v > 0).sum()),
        signifikan=("uji_t", lambda v: (v > 2).sum()), rata_R=("uji_avg", "mean"), win=("uji_win", "median"))
    print(g.sort_values("rata_R", ascending=False).round(3).to_string())

    print("\n=== PER INSTRUMEN (periode uji) ===")
    h = df.groupby("inst").agg(metode=("method", "count"), untung=("uji_avg", lambda v: (v > 0).sum()),
                               signifikan=("uji_t", lambda v: (v > 2).sum()), rata_R=("uji_avg", "mean"))
    print(h.sort_values("rata_R", ascending=False).round(3).to_string())

    print("\n=== KEUNGGULAN KONSISTEN: t>2 di latih DAN di uji ===")
    c = df[(df.latih_t > 2) & (df.uji_t > 2)].sort_values("uji_t", ascending=False)
    print(c[["inst", "method", "params", "latih_n", "latih_win", "latih_avg", "uji_n", "uji_win", "uji_avg",
             "uji_t", "uji_yrs"]].round(3).to_string())

    print("\n=== WIN RATE TINGGI (uji win >= 55% dan untung) ===")
    w = df[(df.uji_win >= 55) & (df.uji_avg > 0)].sort_values("uji_t", ascending=False)
    print(w[["inst", "method", "params", "latih_win", "latih_avg", "uji_n", "uji_win", "uji_avg", "uji_t"]]
          .round(3).head(25).to_string())

    print("\n=== PORTOFOLIO dari seleksi LATIH saja (latih t>=2 & tahun untung >=60%), dinilai di UJI ===")
    for label, pool in (("semua instrumen", df), ("XAU+BTC+EURJPY", df[df.inst.isin(["XAUUSD", "BTCUSD", "EURJPY"])])):
        sel = pool[(pool.latih_t >= 2) & (pool.latih_yrs >= 60)]
        tr = sorted(t for _, r in sel.iterrows() for t in trades[(r.inst, r.method)][1])
        if not tr:
            print(f"  {label}: tidak ada")
            continue
        r = np.array([t[2] for t in tr])
        s = pd.Series(r * 0.5, index=pd.DatetimeIndex([t[1] for t in tr]).tz_localize(None))   # 0,5%/trade
        mon = s.resample("MS").sum()
        mon = mon[mon != 0]
        q = s.resample("QS").sum()
        eq = mon.cumsum()
        print(f"  {label}: {len(sel)} pasangan terpilih, {len(r)} trade, win {np.mean(r > 0) * 100:.1f}%, "
              f"rata {r.mean():+.3f}R, total {s.sum():+.0f}% (0,5%/trade), DD {(eq - eq.cummax()).min():.0f}%, "
              f"bulan+ {(mon > 0).mean() * 100:.0f}%, kuartal+ {(q[q != 0] > 0).mean() * 100:.0f}%")
        print("     " + ", ".join(f"{a}:{b}" for a, b in zip(sel.inst, sel.method)))


if __name__ == "__main__":
    main()
