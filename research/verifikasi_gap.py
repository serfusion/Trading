"""Verifikasi sinyal GAP pekan forex: kode cloud ASLI (cloud/api/_gap.gap_tick) diputar ulang per jam, 2012–2026.

python -m research.verifikasi_gap

Permintaan pengguna (3 Okt 2026): "ya uji" (gap forex belum diuji ulang seperti XAU/BTC). Data H1 = research/pair_data
(ejtrader 2012–2022 + Twelve Data 2022–2026). Tick tiap jam menit :02 (candle tutup + candle berjalan berisi open),
seperti cron cloud. R bersih = r − spread/risk (1 posisi). Spread buka pekan biasanya jauh lebih lebar dari spread
normal, jadi dilaporkan spread ×1 dan ×3 (akun Standard, research/multi_asset.INSTRUMENTS).
Hasil: data/research/eksternal/verifikasi/cloud_GAP.csv (dibaca research/verifikasi.py untuk kartu 🏆 aplikasi).
"""
from __future__ import annotations

import bisect
import sys
from datetime import timedelta
from pathlib import Path

import pandas as pd

from .multi_asset import INSTRUMENTS
from .pair_data import forex

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "cloud" / "api"))
import _core  # noqa: E402
import _gap  # noqa: E402

OUT = ROOT / "data" / "research" / "eksternal" / "verifikasi" / "cloud_GAP.csv"
SPLIT = pd.Timestamp("2021-10-01", tz="UTC")


class Feed:
    def __init__(self, df: pd.DataFrame):
        self.bars = [_core.Bar(t.to_pydatetime(), float(r.open), float(r.high), float(r.low), float(r.close))
                     for t, r in zip(df.index, df.itertuples())]
        self.times = [b.t for b in self.bars]
        self.now = None

    def candles(self, n):
        k = bisect.bisect_right(self.times, self.now - timedelta(hours=1))      # candle yang sudah tutup
        out = self.bars[max(0, k - n + 1):k]
        if k < len(self.bars) and self.bars[k].t <= self.now:
            nb = self.bars[k]
            out = out + [_core.Bar(nb.t, nb.o, nb.o, nb.o, nb.o)]                 # candle berjalan (baru buka)
        return out


class Store:
    def __init__(self):
        self.s = {}

    def get_gap_state(self):
        return dict(self.s)

    def save_gap_state(self, d):
        self.s = dict(d)

    def log(self, *a):
        pass


class Pub:
    def __init__(self):
        self.sig, self.close = {}, []

    def publish(self, ev, *a, **k):
        if ev.get("type") == "signal":
            self.sig[ev["id"]] = ev
        elif ev.get("type") == "close":
            self.close.append(ev)


def main() -> None:
    feeds = {p: Feed(forex(p.replace("/", ""))) for p in _gap.PAIRS}
    start = max(f.bars[0].t for f in feeds.values()) + timedelta(days=30)
    end = min(f.bars[-1].t for f in feeds.values())
    store, pub = Store(), Pub()
    now = start.replace(minute=2, second=0, microsecond=0)
    while now <= end:
        if _gap.needs_data(now, store):
            for f in feeds.values():
                f.now = now
            _gap.gap_tick(now, feeds, store, pub)      # nilai poin tidak memengaruhi R
        now += timedelta(hours=1)
    rows = []
    for ev in pub.close:
        s = pub.sig.get(ev["id"], {})
        sym = ev["symbol"].replace("/", "")
        sp = INSTRUMENTS[sym][1]
        rows.append({"pair": ev["symbol"], "t_signal": s.get("time"), "t_close": ev["time"], "dir": ev["dir"],
                     "r": ev["r"], "risk": ev["risk_points"], "spread": sp,
                     "R": ev["r"] - sp / ev["risk_points"], "R3": ev["r"] - 3 * sp / ev["risk_points"],
                     "reason": ev["reason"]})
    df = pd.DataFrame(rows)
    df["t_signal"] = pd.to_datetime(df.t_signal, utc=True)
    df.to_csv(OUT, index=False)
    print(f"{len(df)} sinyal gap tutup -> {OUT}")
    for p, g in df.groupby("pair"):
        for per, m in (("LAMA", g.t_signal < SPLIT), ("BARU", g.t_signal >= SPLIT)):
            x = g[m]
            if len(x):
                print(f"  {p} {per}: n{len(x)} WR {(x.R > 0).mean() * 100:.0f}% R {x.R.mean():+.3f} "
                      f"(spread x3: WR {(x.R3 > 0).mean() * 100:.0f}% R {x.R3.mean():+.3f})")


if __name__ == "__main__":
    main()
