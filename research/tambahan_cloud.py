"""Replay kode cloud ASLI untuk kandidat sinyal tambahan (research/sinyal_tambahan.py) — python -m research.tambahan_cloud X

X = XAU (set tambahan 100/40 & 120/50 + lapisan kapan saja maks 5), BTC (lapisan setelah TP1 maks 1),
    ETH (kategori konf+⭐ & ⭐, hanya saat sinyal 💰 BTC searah sedang terbuka; gerbang dari cloud_BTC.csv).
Hasil: data/research/eksternal/verifikasi/cloud_<X>_tambahan.csv; ringkasan lewat research/verifikasi.net.
Kode cloud tidak diubah di sini (konfigurasi lewat cfg).
"""
from __future__ import annotations

import sys

import pandas as pd

from . import verifikasi_cloud as vc

CAND = {
    "XAU": {"sets": [(40, 15), (55, 20), (80, 30), (100, 40), (120, 50)],
            "layer": {"mode": "any", "max": 6, "lot": 0.5}},
    "BTC": {"layer": {"mode": "tp1", "max": 2, "lot": 0.5}},
}
ETH_STATS = {"ETH konf+⭐": (55.0, 0.18, 590, "Okt 2021–2026"), "ETH ⭐": (55.0, 0.18, 590, "Okt 2021–2026"),
             "ETH konf": (0.0, -0.01, 0, "-"), "ETH biasa": (0.0, -0.01, 0, "-")}


def btc_gate():
    b = pd.read_csv(vc.OUT / "cloud_BTC.csv", parse_dates=["t_signal", "t_close"])
    b = b[~b.lapis]
    t_in, t_out, dd = b.t_signal.tolist(), b.t_close.tolist(), b.dir.tolist()

    def gate(direction, now):
        ok = any(a <= now < c and d == direction for a, c, d in zip(t_in, t_out, dd))
        return None if ok else "tidak ada 💰 BTC searah terbuka"
    return gate


def main() -> None:
    name = sys.argv[1]
    if name == "ETH":
        from .pair_data import eth
        vc._core.STATS.update(ETH_STATS)
        extra = {**vc._core.BTC_CFG, "asset": "ETH", "id_prefix": "ETH-", "skip_fn": btc_gate(),
                 "skip_cats": ("konf", "biasa")}
        out = vc.replay("ETH", extra=extra, data=eth())
    else:
        out = vc.replay(name, extra=CAND[name])
    out.to_csv(vc.OUT / f"cloud_{name}_tambahan.csv", index=False)
    print("selesai", len(out))


if __name__ == "__main__":
    main()
