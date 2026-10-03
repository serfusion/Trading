import pandas as pd
import pytest

from research.martingale_ruin import cycles, layer_table


def test_layer_table_lot_ganda():
    t = layer_table(2.0, 20, price=4200.0)
    assert t.lot.iloc[-1] == pytest.approx(5242.88)
    assert t.lot_kum.iloc[-1] == pytest.approx(10485.75)
    # layer 1: rugi ke layer 2 = $2 gerak + $0,20 spread pada 0,01 lot
    assert t.rugi_di_layer_berikut.iloc[0] == pytest.approx(-2.2)
    assert t["margin_1:2000"].iloc[0] == pytest.approx(0.01 * 100 * 4200 / 2000)


def test_cycles_tambah_layer_lalu_tp():
    idx = pd.date_range("2025-01-01", periods=3, freq="5min")
    # turun $4,1 (2 layer tambahan di -2 dan -4) lalu naik ke atas rata-rata + TP
    df = pd.DataFrame(dict(open=[100.0, 96.0, 99.0], high=[100.0, 99.0, 101.0],
                           low=[96.0, 95.9, 99.0], close=[96.0, 99.0, 101.0]), index=idx)
    c = cycles(df, 2.0, 1.0, 20, 1)
    assert c.layer.iloc[0] == 3
    assert c.lot_kum.iloc[0] == pytest.approx(0.07)
    assert c.laba.iloc[0] == pytest.approx(0.07 * 100 * 1.0)
