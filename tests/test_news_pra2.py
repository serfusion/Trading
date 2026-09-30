"""Entry sebelum rilis, tutup 1 dtk s.d. 3 menit (research/news_pra2.py): mesin keluar, straddle, hedge, petunjuk."""
import numpy as np
import pandas as pd

from research.news_pra2 import EXITS, SCEN, STRADDLE, HEDGE, directional, hedge, momentum, straddle
from tests.test_news_detik import path, tick

E = {name: i for i, name in enumerate(EXITS)}
S = {name: i for i, name in enumerate(SCEN)}


def test_directional_buy_sell_tutup_waktu_dan_kunci_untung():
    p = tick(path(jump=5.0), spread=0.4)             # datar, lalu +$5 mulai detik 2
    d = directional(p)
    c = S["CEPAT"]
    assert abs(d[c, 0, E["tutup 1s"]] - (-0.4)) < 1e-9            # tutup di t0: belum bergerak -> rugi spread
    assert abs(d[c, 0, E["tutup 3s"]] - 4.6) < 1e-9               # tutup di t0+2
    assert abs(d[c, 1, E["tutup 3s"]] - (-5.4)) < 1e-9            # SELL salah arah
    assert abs(d[c, 0, E["untung>=$1 maks 60s"]] - 4.6) < 1e-9    # kunci untung di tick pertama >= $1
    assert abs(d[c, 1, E["untung>=$1 maks 60s SL$3"]] - (-5.4)) < 1e-9   # SL $3 kena di tick lonjakan (gap)
    r = S["REALISTIS"]                                             # masuk t0-0,5, tutup +0,5, slippage 2x $0,30
    assert abs(d[r, 0, E["tutup 3s"]] - (4.6 - 0.6)) < 1e-9


def test_straddle_terisi_di_tick_lonjakan_dengan_gap():
    p = tick(path(jump=5.0), spread=0.4)
    s = straddle(p)
    k1 = STRADDLE.index(1.0)
    # Buy Stop di 2001 terisi di ask tick lonjakan 2005,2 (gap), tutup 1 dtk kemudian di bid 2004,8
    assert abs(s[0, k1, S["CEPAT"], E["tutup 1s"]] - (-0.4)) < 1e-9
    # gap $4,2 bukan "gap sedang" -> tetap diisi di tick walau varian perlindungan gap
    assert abs(s[1, k1, S["CEPAT"], E["tutup 1s"]] - (-0.4)) < 1e-9
    # lonjakan kecil: ask 2001,4 melewati Buy Stop 2001 (gap $0,4) -> dilindungi, diisi di 2001
    small = straddle(tick(path(jump=1.2), spread=0.4))
    assert abs(small[0, k1, S["CEPAT"], E["tutup 1s"]] - (2001.0 - 2001.4)) < 1e-9
    assert abs(small[1, k1, S["CEPAT"], E["tutup 1s"]] - (2001.0 - 2001.0)) < 1e-9
    flat = straddle(tick(path(jump=0.0), spread=0.4))
    assert np.isnan(flat).all()                                     # tidak tersentuh -> batal


def test_hedge_tutup_sisi_rugi_lalu_tahan_sisi_untung():
    p = tick(path(jump=5.0), spread=0.4)
    h = hedge(p)
    d3 = HEDGE.index(3)
    # SELL ditutup di t0+3: 1999,8 - 2005,2 = -5,4; BUY ditahan 1 dtk lagi: 2004,8 - 2000,2 = +4,6
    assert abs(h[d3, S["CEPAT"], E["tutup 1s"]] - (-0.8)) < 1e-9
    flat = hedge(tick(path(jump=0.0), spread=0.4))
    assert np.allclose(flat[d3, S["CEPAT"]], -0.8)                 # tidak bergerak -> dua spread


def test_drift_tanpa_tick_lama_tidak_membaca_tick_terakhir():
    from research.news_pra2 import drift
    p = tick([(s, 2000.0 + s) for s in np.arange(-30, 900, 1.0)])     # tick baru mulai t0-30
    m1 = p.mid[p.at(-1)]
    assert drift(p, m1, 10) == 10.0
    assert np.isnan(drift(p, m1, 110))                                 # dulu: mid[-1] = harga +15 menit (bocor)


def test_momentum_hanya_kejutan_sebelum_t0():
    t = pd.Timestamp("2024-03-08 13:30", tz="UTC")
    cal = pd.DataFrame({"time": [t - pd.Timedelta(days=40), t - pd.Timedelta(days=10), t - pd.Timedelta(days=3), t],
                        "gold_bias": [-1.0, 1.0, 1.0, -1.0]})
    ev = pd.DataFrame({"time": [t]})
    # 40 hari lalu di luar jendela, rilis di t0 sendiri tidak ikut -> +1 +1 = BUY
    assert momentum(ev, cal).tolist() == [1.0]
