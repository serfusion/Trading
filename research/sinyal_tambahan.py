"""±100 sumber sinyal TAMBAHAN saat sinyal lain berjalan — python -m research.sinyal_tambahan

Permintaan pengguna (3 Okt 2026): "ada sinyal lain setelah running — lapisan, pair lain atau apapun — yang penting WR
tinggi & profit; uji semua 100 jika ada". Mesin = research/sl_tangga.backtest (seperti cloud: H1 Donchian, SL 3xATR,
5 posisi, TP1 0,7R seperti cloud sekarang, SL+ setelah TP1, sisanya TUTUP). Spread: XAU $0,30 (lebih besar dari spread
asli Exness), BTC spread ASLI Exness per jam, ETH 0,05%, forex akun Standard. Yang dinilai hanya sinyal TAMBAHAN-nya.
Keluarga:
 A lapisan XAU/BTC (setelah TP1 / kapan saja, breakout baru, maks 1–10 per set)          40
 B set Donchian tambahan (20/10, 30/15, 100/40, 120/50), kategori 💰                        8
 C kategori yang tidak dikirim (XAU ⭐/biasa, BTC biasa/konf): sendiri / saat 💰 aset sama
   searah terbuka / saat 💰 aset lain searah terbuka                                        12
 D pair lain (ETH + 11 forex): semua / konf+⭐ / konf+⭐ & ⭐                                36
 E ETH saat 💰 BTC searah terbuka (3 kategori)                                               3
LOLOS (ditetapkan sebelum melihat hasil): WR >= 55% DAN R/sinyal > 0 di LAMA (< Okt 2021) dan BARU, n BARU >= 40,
>= 60% tahun positif. "WR tinggi" = WR >= 55% & R > 0 di BARU saja (lebih longgar, belum tentu konsisten).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .eksternal import asset
from .filters import features
from .gap_study import week_info
from .pair_data import FOREX
from .pair_tambahan import bars as pair_bars
from .sl_tangga import backtest
from .strategy_lab import rolling_max, rolling_min
from .strategy_lab2 import STAR, trend_states

OUT = Path(__file__).resolve().parent.parent / "docs" / "eksternal" / "hasil_sinyal_tambahan.txt"
SPLIT = pd.Timestamp("2021-10-01", tz="UTC")
SETS = ((40, 15), (55, 20), (80, 30))
LIVE = {"XAUUSD": ("konf+⭐", "konf"), "BTCUSD": ("konf+⭐", "⭐")}      # yang dikirim cloud sekarang
TP = [0.7, None, None, None, None]


def btc_real_spread(b) -> None:
    from .exness import spread_table
    t = spread_table("BTCUSDm")
    t.index = pd.to_datetime(t.index, utc=True)
    med = t["median"]
    yearly = med.groupby(med.index.year).median()
    hour = pd.DatetimeIndex(b.t).floor("h")
    out = med.reindex(hour).to_numpy(float)
    fill = yearly.reindex(np.clip(hour.year, yearly.index.min(), yearly.index.max())).to_numpy(float)
    b.sp = np.where(np.isnan(out), fill, out)


def runner(b, name: str, cats, sets=SETS, skip_open=True, gate=None, **kw) -> pd.DataFrame:
    """Sinyal kategori `cats` (None = semua). gate(i, d) -> bool tambahan. Kolom lapis = dibuka saat sinyal lain di set
    yang sama masih terbuka."""
    f = b.cached("feat", lambda: features(b.df))
    since = b.cached("since", lambda: week_info(b.df)[0])
    s = b.cached("states", lambda: trend_states(b))

    def allow(i, d):
        if skip_open and since[i] < 3:
            return False
        star = bool(STAR(f, i, d))
        konf = s["ema"][i] == d and s["st"][i] == d and s["mom"][i] == d
        c = "konf+⭐" if star and konf else "konf" if konf else "⭐" if star else "biasa"
        return (cats is None or c in cats) and (gate is None or gate(i, d))
    tr = []
    for n_in, n_out in sets:
        hi, lo = rolling_max(b.h, n_in), rolling_min(b.l, n_in)
        hx, lx = rolling_max(b.h, n_out), rolling_min(b.l, n_out)
        last = None
        for t, t_out, r, d, mr in backtest(b, b.c > hi, b.c < lo, b.c < lx, b.c > hx, allow, tps=TP, **kw):
            tr.append((t, t_out, r, d, last is not None and t < last))
            last = t_out if last is None else max(last, t_out)
    return pd.DataFrame(sorted(tr), columns=["t", "t_out", "R", "dir", "lapis"])


def open_gate(b, base: pd.DataFrame):
    """gate: True bila ada sinyal `base` searah yang sedang terbuka pada candle keputusan b.t[i+1]."""
    def ns(x):                                   # satuan waktu disamakan (data ada yang ms, us, ns)
        ix = pd.DatetimeIndex(x)
        ix = ix.tz_convert("UTC") if ix.tz else ix.tz_localize("UTC")
        return ix.as_unit("ns").asi8
    t_in, t_out, dd = ns(base.t), ns(base.t_out), base.dir.to_numpy()
    bt = ns(b.t)

    def g(i, d):
        if i + 1 >= len(bt):
            return False
        now = bt[i + 1]
        return bool(np.any((t_in <= now) & (t_out > now) & (dd == d)))
    return g


def stat(x: pd.DataFrame) -> dict:
    if len(x) == 0:
        return {"n": 0}
    lama, baru = x[x.t < SPLIT], x[x.t >= SPLIT]
    yr = x.groupby(x.t.dt.year).R.sum()
    wr = lambda y: (y.R > 0).mean() * 100 if len(y) else np.nan  # noqa: E731
    return {"n": len(x), "n_baru": len(baru), "wr": wr(x), "wr_l": wr(lama), "wr_b": wr(baru), "avg": x.R.mean(),
            "avg_l": lama.R.mean() if len(lama) else np.nan, "avg_b": baru.R.mean() if len(baru) else np.nan,
            "th": (yr > 0).mean() * 100}


def verdict(s: dict) -> str:
    if s.get("n", 0) == 0:
        return "-"
    ok = (s["wr_l"] >= 55 and s["wr_b"] >= 55 and s["avg_l"] > 0 and s["avg_b"] > 0 and s["n_baru"] >= 40
          and s["th"] >= 60)
    if ok:
        return "LOLOS"
    return "WR tinggi (BARU saja)" if s["wr_b"] >= 55 and s["avg_b"] > 0 and s["n_baru"] >= 40 else "tidak"


def main() -> None:
    rows = []

    def add(fam, label, x):
        s = stat(x)
        rows.append((fam, label, s, verdict(s)))
        print(fam, label, verdict(s), flush=True)
    A = {k: asset(k).b for k in ("XAUUSD", "BTCUSD")}
    btc_real_spread(A["BTCUSD"])
    base = {k: runner(A[k], k, LIVE[k], skip_open=k == "XAUUSD") for k in A}
    # A lapisan
    for k in A:
        for ov in ("tp1", "any"):
            for fr in (False, True):
                for mx in (1, 2, 3, 5, 10):
                    x = runner(A[k], k, LIVE[k], skip_open=k == "XAUUSD", overlap=ov, fresh_layers=fr, max_layers=mx + 1)
                    add("A", f"{k[:3]} lapisan {'setelah TP1' if ov == 'tp1' else 'kapan saja'}"
                             f"{', breakout baru' if fr else ''}, maks {mx}", x[x.lapis])
    # B set tambahan
    for k in A:
        for st in ((20, 10), (30, 15), (100, 40), (120, 50)):
            add("B", f"{k[:3]} set tambahan {st[0]}/{st[1]}", runner(A[k], k, LIVE[k], sets=(st,), skip_open=k == "XAUUSD"))
    # C kategori yang tidak dikirim
    other = {"XAUUSD": "BTCUSD", "BTCUSD": "XAUUSD"}
    for k, cats in (("XAUUSD", ("⭐",)), ("XAUUSD", ("biasa",)), ("BTCUSD", ("biasa",)), ("BTCUSD", ("konf",))):
        so = k == "XAUUSD"
        add("C", f"{k[:3]} {cats[0]} sendiri", runner(A[k], k, cats, skip_open=so))
        add("C", f"{k[:3]} {cats[0]} saat 💰 {k[:3]} searah terbuka",
            runner(A[k], k, cats, skip_open=so, gate=open_gate(A[k], base[k])))
        add("C", f"{k[:3]} {cats[0]} saat 💰 {other[k][:3]} searah terbuka",
            runner(A[k], k, cats, skip_open=so, gate=open_gate(A[k], base[other[k]])))
    # D pair lain
    for sym in ["ETHUSD"] + FOREX:
        try:
            b = pair_bars(sym)
        except Exception as exc:  # noqa: BLE001
            print(sym, "gagal", exc)
            continue
        so = sym != "ETHUSD"
        for label, cats in (("semua", None), ("konf+⭐", ("konf+⭐",)), ("konf+⭐ & ⭐", ("konf+⭐", "⭐"))):
            add("D", f"{sym} {label}", runner(b, sym, cats, skip_open=so))
        if sym == "ETHUSD":
            for label, cats in (("semua", None), ("konf+⭐", ("konf+⭐",)), ("konf+⭐ & ⭐", ("konf+⭐", "⭐"))):
                add("E", f"ETH {label} saat 💰 BTC searah terbuka",
                    runner(b, sym, cats, skip_open=False, gate=open_gate(b, base["BTCUSD"])))
    L = ["# ±100 sumber sinyal tambahan (research/sinyal_tambahan.py)", "",
         "TP1 0,7R. WR = sinyal dengan hasil bersih > 0. LAMA < Okt 2021, BARU sejak Okt 2021.", "",
         f"{'kel':3} {'sumber':58} {'n':>5} {'nB':>4} {'WR L':>5} {'WR B':>5} {'R L':>6} {'R B':>6} {'th+':>4}  hasil"]
    for fam, label, s, v in rows:
        if s.get("n", 0) == 0:
            L.append(f"{fam:3} {label:58} n=0")
            continue
        L.append(f"{fam:3} {label:58} {s['n']:5} {s['n_baru']:4} {s['wr_l']:5.0f} {s['wr_b']:5.0f} {s['avg_l']:+6.2f} "
                 f"{s['avg_b']:+6.2f} {s['th']:4.0f}  {v}")
    lol = [r for r in rows if r[3] == "LOLOS"]
    wr = [r for r in rows if r[3].startswith("WR")]
    L += ["", f"Diuji {len(rows)} sumber. LOLOS {len(lol)}, WR tinggi hanya di BARU {len(wr)}."]
    for fam, label, s, v in sorted(lol, key=lambda r: -r[2]["avg_b"]):
        L.append(f"  LOLOS: {label} — WR {s['wr_l']:.0f}%/{s['wr_b']:.0f}%, R {s['avg_l']:+.2f}/{s['avg_b']:+.2f}, "
                 f"n BARU {s['n_baru']}")
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
