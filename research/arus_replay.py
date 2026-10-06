"""Putar ulang kode cloud ASLI cloud/api/_arus.py jam demi jam lalu bandingkan dengan riset (research/pisau_cek).

python -m research.arus_replay [mulai=2024-01-01]
"""
from __future__ import annotations

import sys
from datetime import timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "cloud" / "api"))
import _arus  # noqa: E402
import _core  # noqa: E402

from . import pisau as P  # noqa: E402
from .pisau_cek import trades  # noqa: E402


class Mem:
    def __init__(self):
        self.s = {}

    def get_state(self):
        return self.s

    def save_state(self, d):
        self.s = d


class Pub:
    def __init__(self):
        self.ev = []

    def publish(self, ev, *a, **k):
        self.ev.append(ev)


def main() -> None:
    start = pd.Timestamp(sys.argv[1] if len(sys.argv) > 1 else "2024-01-01", tz="UTC")
    series = {s.name: s for s in P.load()}
    L = [f"# Replay kode cloud _arus.py vs riset (sejak {start:%Y-%m-%d})"]
    for asset, rule in _arus.RULES.items():
        s = series[asset]
        bars = [_core.Bar(t.to_pydatetime(), o, h, lo, c) for t, o, h, lo, c in zip(s.t, s.o, s.h, s.l, s.c)]
        idx = [i for i, b in enumerate(bars) if b.t >= start.to_pydatetime()]
        mem, pub = Mem(), Pub()
        for i in idx:
            now = bars[i].t + timedelta(minutes=2)          # cron :02, candle i masih berjalan
            _arus.arus_tick(now, {asset: bars[max(0, i - 3000):i + 1]}, mem, pub)
        sig = [e for e in pub.ev if e["type"] == "arus_signal"]
        cl = [e for e in pub.ev if e["type"] == "arus_close"]
        mv = rule["move"]
        tr = trades(s, mv, rule["n"], rule["k"], "l_brk" if rule["mode"] == "stop" else "l_mkt", rule["tren"],
                    rule["sl"], rule["tp"], rule["h"])
        tr = tr[tr.t >= start]
        wr_c = sum(e["win"] for e in cl) / len(cl) * 100 if cl else float("nan")
        avg_c = sum(e["r"] for e in cl) / len(cl) if cl else float("nan")
        L.append(f"{asset}: cloud sinyal {len(sig)} tutup {len(cl)} WR {wr_c:.0f}% rata {avg_c:+.2f}R (tanpa biaya) | "
                 f"riset trade {len(tr)} WR {(tr.R > 0).mean() * 100:.0f}% rata {tr.R.mean():+.2f}R (dengan biaya)")
        print(L[-1], flush=True)
    (ROOT / "docs" / "eksternal" / "hasil_arus_replay.txt").write_text("\n".join(L) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
