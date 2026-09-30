"""Peluang Kalshi -> P(di atas / di bawah konsensus) (research/kalshi_uji.py), tanpa jaringan."""
import pandas as pd

from research.kalshi_uji import curve, gold_dirs, lean, p_above, prob_at, strike


def m(ticker, candles):
    return {"ticker": ticker, "candle": candles}


def test_strike_dari_ticker():
    assert strike(m("KXCPI-25AUG-T0.3", [])) == 0.3
    assert strike(m("KXCPI-25AUG-T-0.1", [])) == -0.1
    assert strike(m("KXPAYROLLS-25AUG-T150000", [])) == 150000
    assert strike(m("KXFEDDECISION-25SEP-C25", [])) is None


def test_prob_pakai_candle_terakhir_sebelum_waktu_dan_mid():
    x = m("A-T0.3", [[100, 0.36, 0.38, 0.37, 5], [200, None, None, 0.40, 0], [300, 0.50, 0.52, 0.5, 1]])
    assert prob_at(x, 99) is None                       # belum ada candle selesai
    assert abs(prob_at(x, 150) - 0.37) < 1e-12          # mid bid/ask
    assert prob_at(x, 250) == 0.40                      # bid/ask kosong -> harga terakhir
    assert abs(prob_at(x, 10_000) - 0.51) < 1e-12       # tidak memakai candle sesudah waktunya (tidak ada)


def test_peluang_di_atas_dan_di_bawah_konsensus_cpi():
    ms = [m("E-T0.2", [[1, 0.9, 0.9, 0.9, 1]]), m("E-T0.3", [[1, 0.4, 0.4, 0.4, 1]]),
          m("E-T0.4", [[1, 0.1, 0.1, 0.1, 1]])]
    pts = curve(ms, 10)
    up, down = lean(pts, 0.3, 0.1)
    # di atas 0,3 = 40%; di bawah 0,3 = 1 - P(> 0,2) = 10%; sama (0,3) = 50%
    assert abs(up - 0.4) < 1e-12 and abs(down - 0.1) < 1e-12
    assert lean(pts, 0.5, 0.1) is None                  # konsensus di luar strike -> tidak ditebak


def test_nfp_interpolasi_antar_strike():
    pts = [(100000.0, 0.8), (150000.0, 0.5), (200000.0, 0.2)]
    assert abs(p_above(pts, 125000) - 0.65) < 1e-12
    up, down = lean(pts, 125000, None)
    assert abs(up - 0.65) < 1e-12 and abs(down - 0.35) < 1e-12


def test_arah_emas_dari_tebakan_dan_gabungan_rilis_bersamaan():
    t = pd.Timestamp("2025-09-11 12:30", tz="UTC")
    u = pd.Timestamp("2025-09-05 12:30", tz="UTC")
    df = pd.DataFrame({"t0": [t, t, u], "terbalik": [False, False, True],
                       "lean 1 jam": [0.3, 0.2, 0.25]})           # CPI & core condong DI ATAS; pengangguran di atas
    d = gold_dirs(df, "1 jam", 0.1)
    assert d[t] == -1.0          # inflasi di atas perkiraan -> USD kuat -> emas turun
    assert d[u] == 1.0           # pengangguran di atas perkiraan -> USD lemah -> emas naik
