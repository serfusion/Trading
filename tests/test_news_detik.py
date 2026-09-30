"""Mesin uji detik pertama setelah berita (research/news_detik.py) dengan tick buatan."""
import numpy as np
import pandas as pd

from research.news_detik import Tick, exits, trades

T0 = pd.Timestamp("2024-01-05 13:30", tz="UTC")


def tick(points, spread=0.4, unit=1.0):
    """points: [(detik relatif, mid)] -> Tick dengan bid/ask di sekitar mid."""
    idx = [T0 + pd.Timedelta(seconds=s) for s, _ in points]
    mid = np.array([m for _, m in points], dtype=float)
    df = pd.DataFrame({"bid": mid - spread / 2, "ask": mid + spread / 2}, index=idx)
    return Tick(T0, df, unit)


def path(pre=2000.0, jump=None, after=None):
    """Harga datar sebelum rilis, lonjakan di detik 1,2, lalu tiap detik sampai 16 menit mengikuti `after(t)`."""
    pts = [(s, pre) for s in np.arange(-120, 0, 1.0)]
    for s in np.arange(0, 16 * 60, 1.0):
        m = pre if s < 1.2 else pre + (jump or 0.0) + (after(s) if after else 0.0)
        pts.append((float(s), m))
    return pts


def rows(p, bias=np.nan, besar=False):
    return pd.DataFrame(trades(p, bias, besar))


def test_keputusan_tidak_melihat_masa_depan():
    # lonjakan +$5 di detik 1,2: keputusan di detik ke-1 belum melihatnya -> tidak ada GERAK 1s
    r = rows(tick(path(jump=5.0)))
    assert not r.aturan.str.startswith("GERAK 1s").any()
    assert r.aturan.str.startswith("GERAK 2s").any() and r.aturan.str.startswith("GERAK 5s").any()


def test_entry_di_ask_plus_slippage_dan_arah_ikut_lonjakan():
    p = tick(path(jump=5.0))
    r = rows(p)
    g = r[(r.aturan == "GERAK 5s $3") & (r.lat == 0.5) & (r.keluar == "TAHAN 1m") & ~r.sl]
    assert set(g.arah) == {1}
    # harga datar sesudah lonjakan -> hasil = -spread - slippage
    assert np.allclose(sorted(g.pnl), [-1.4, -0.7, -0.4])
    lawan = r[(r.aturan == "LAWAN 5s $3") & (r.lat == 0.5) & (r.slip == 0) & (r.keluar == "TAHAN 1m") & ~r.sl]
    assert set(lawan.arah) == {-1} and np.allclose(lawan.pnl, -0.4)


def test_pending_terisi_di_tick_yang_melewati_level():
    # Buy Stop $2 di 2002; tick pertama sesudah lonjakan = mid 2005 -> terisi di ask 2005,2 (slippage gap $3,2)
    p = tick(path(jump=5.0))
    r = rows(p)
    g = r[(r.aturan == "STRADDLE $2") & (r.slip == 0) & (r.keluar == "TAHAN 1m") & ~r.sl]
    assert len(g) == 1 and g.arah.iloc[0] == 1 and np.isclose(g.pnl.iloc[0], -0.4)
    assert not r.aturan.eq("STRADDLE $1").any() or set(r[r.aturan == "STRADDLE $1"].arah) == {1}


def test_aturan_pengguna_tutup_saat_profit_di_menit_1_sampai_5():
    # naik $0,24/menit sesudah lonjakan: menit 1 masih rugi (spread $0,4), menit 2 sudah profit -> tutup di menit 2
    p = tick(path(jump=5.0, after=lambda s: s / 250.0))
    k = p.after(5.5)
    price = p.ask[k]
    out = exits(p, k, price, 1)
    ts = p.T[k]
    assert p.bid[p.at(ts + 60)] - price < 0
    expect = p.bid[p.at(ts + 120)] - price
    assert out[("PENGGUNA", False)] == expect > 0
    assert out[("TAHAN 15m", False)] > out[("PENGGUNA", False)]


def test_aturan_pengguna_tahan_sampai_15_menit_bila_belum_profit_dan_sl_darurat():
    # turun terus $1/menit: tidak pernah profit -> tutup paksa 15 menit; dengan SL $5 keluar lebih awal
    p = tick(path(jump=5.0, after=lambda s: -s / 60.0))
    k = p.after(5.5)
    out = exits(p, k, p.ask[k], 1)
    assert out[("PENGGUNA", False)] == out[("TAHAN 15m", False)] < -10
    assert -6 < out[("PENGGUNA", True)] <= -5


def test_kejutan_mengikuti_bias_dan_btc_memakai_satuan_persen():
    r = rows(tick(path(jump=0.0)), bias=-1.0, besar=True)
    assert set(r[r.aturan.str.startswith("KEJUTAN")].arah) == {-1}
    assert r.aturan.str.startswith("KEJUTAN BESAR").any()
    # BTC: satuan 0,05% dari 100.000 = 50 -> lonjakan +$150 (3 satuan) memicu GERAK $3, hasil dalam satuan
    pts = [(s, 100000.0 + (150.0 if s >= 1.2 else 0.0)) for s in np.arange(-120, 960, 1.0)]
    p = tick(pts, spread=30.0, unit=50.0)
    r = rows(p)
    g = r[(r.aturan == "GERAK 5s $3") & (r.slip == 0) & (r.lat == 0.5) & (r.keluar == "TAHAN 1m") & ~r.sl]
    assert len(g) == 1 and np.isclose(g.pnl.iloc[0], -30.0 / 50.0)
