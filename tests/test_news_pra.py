"""Entry 1 detik sebelum rilis, tutup 1-3 detik kemudian (research/news_pra.py) dengan tick buatan."""
import numpy as np
import pandas as pd

from research.news_pra import pnl, simple_clues
from tests.test_news_detik import path, tick


def test_pnl_entry_t0_min1_bayar_spread_dan_slippage():
    p = tick(path(jump=5.0), spread=0.4)             # lonjakan +$5 di detik 1,2
    # tutup 1 dtk setelah entry = t0 (angka belum keluar): rugi sebesar spread
    assert abs(pnl(p, 1, 0.0, 0.0, 1) - (-0.4)) < 1e-9
    # tutup 3 dtk setelah entry = t0+2: BUY untung 5 - spread, SELL rugi 5 + spread
    assert abs(pnl(p, 1, 0.0, 0.0, 3) - 4.6) < 1e-9
    assert abs(pnl(p, -1, 0.0, 0.0, 3) - (-5.4)) < 1e-9
    # REALISTIS: terisi t0-0,5, tutup t0+2 (klik t0+1,5 + 0,5), slippage $0,30 dua kali
    assert abs(pnl(p, 1, 0.5, 0.3, 2) - (5.0 - 0.4 - 0.6)) < 1e-9


def test_pnl_tanpa_kutipan_sebelum_rilis_dilewati():
    p = tick([(s, 2000.0) for s in np.arange(0, 60, 1.0)])
    assert np.isnan(pnl(p, 1, 0.0, 0.0, 1))


def test_petunjuk_hanya_pakai_info_sebelum_rilis():
    t = pd.Timestamp("2024-01-05 13:30", tz="UTC")
    ev = pd.DataFrame({"time": [t, t + pd.Timedelta(days=30), t + pd.Timedelta(days=90)],
                       "group": ["NFP"] * 3, "bias": [1.0, -1.0, 1.0],
                       "event": ["Non-Farm Employment Change", "Non-Farm Employment Change", "Unemployment Rate"],
                       "forecast": ["150K", "200K", "4.1%"], "previous": ["100K", "250K", "4.3%"]})
    c = simple_clues(ev)
    # ULANG: rilis ke-2 memakai kejutan rilis ke-1 (bukan miliknya sendiri); rilis ke-3 berjarak 60 hari -> tidak
    assert c["ULANG kejutan sebelumnya"].isna().tolist() == [True, False, True]
    assert c["ULANG kejutan sebelumnya"][1] == 1.0
    # ACT->PREV: Prev < Cons NFP -> tebak NFP di bawah perkiraan -> USD lemah -> BUY emas;
    # Prev > Cons Unemployment Rate (terbalik) -> tebak pengangguran lebih tinggi -> USD lemah -> BUY emas
    assert c["ACT->PREV"].tolist() == [1.0, -1.0, 1.0]
