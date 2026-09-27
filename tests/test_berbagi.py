import pandas as pd
import pytest

from xau_bot.__main__ import main
from xau_bot.berbagi import alokasi_berbagi, baca_pnl_csv, format_alokasi, rencana_tabungan_emas, zakat_mal


def pnl(rows):
    idx = pd.DatetimeIndex([pd.Timestamp(t, tz="UTC") for t, _ in rows])
    return pd.Series([x for _, x in rows], index=idx, dtype=float)


def test_alokasi_high_water_mark_tidak_dobel_setelah_rugi():
    s = pnl([("2026-01-10", 100), ("2026-01-20", 50),     # Jan +150 -> puncak 150
             ("2026-02-05", -120),                         # Feb -120 -> kumulatif 30
             ("2026-03-03", 100),                          # Mar +100 -> kumulatif 130 (< 150)
             ("2026-04-01", 70)])                          # Apr +70 -> kumulatif 200 -> baru 50
    rows = alokasi_berbagi(s, persen=10, periode="M")
    assert [r.periode for r in rows] == ["2026-01", "2026-02", "2026-03", "2026-04"]
    assert [r.alokasi for r in rows] == [15.0, 0.0, 0.0, 5.0]
    assert rows[-1].total_alokasi == 20.0
    assert rows[2].puncak == 150.0 and rows[2].kumulatif == 130.0


def test_alokasi_pakai_kalender_wib_dan_mingguan():
    # 31 Jan 20:00 UTC = 1 Feb 03:00 WIB -> masuk Februari
    rows = alokasi_berbagi(pnl([("2026-01-31 20:00", 10)]), persen=50)
    assert rows[0].periode == "2026-02" and rows[0].alokasi == 5.0
    rows = alokasi_berbagi(pnl([("2026-09-21", 10), ("2026-09-25", 10), ("2026-09-29", -5)]), 10, "W")
    assert len(rows) == 2 and rows[0].alokasi == 2.0 and rows[1].alokasi == 0.0


def test_alokasi_validasi_dan_kosong():
    assert alokasi_berbagi(pd.Series(dtype=float)) == []
    with pytest.raises(ValueError):
        alokasi_berbagi(pnl([("2026-01-01", 1)]), persen=150)
    txt = format_alokasi(alokasi_berbagi(pnl([("2026-01-05", 100), ("2026-02-05", -40)]), 10), 10, "USD", 16500)
    assert "Rp165.000" in txt and "Masih harus menutup rugi" in txt


def test_zakat_nisab_dan_haul():
    z = zakat_mal(200_000_000, 2_000_000)                  # nisab 170 jt
    assert z.wajib and z.zakat == 5_000_000
    assert not zakat_mal(150_000_000, 2_000_000).wajib
    assert not zakat_mal(200_000_000, 2_000_000, haul=False).wajib
    z = zakat_mal(200_000_000, 2_000_000, hutang_jatuh_tempo=40_000_000)
    assert not z.wajib and z.harta == 160_000_000
    with pytest.raises(ValueError):
        zakat_mal(1, 0)


def test_rencana_tabungan_emas():
    r = rencana_tabungan_emas(100_000, 2_000_000, 12, kenaikan_tahunan=(0.0, 0.10), selisih_buyback_pct=0)
    assert r.total_setor == 1_200_000
    assert r.gram == pytest.approx(0.6)
    assert r.nilai[0.0] == pytest.approx(1_200_000)
    assert r.nilai[0.10] > 1_200_000
    r = rencana_tabungan_emas(100_000, 2_000_000, 12, kenaikan_tahunan=(0.0,), selisih_buyback_pct=5)
    assert r.nilai[0.0] == pytest.approx(1_140_000)


def test_baca_csv_dan_cli(tmp_path, capsys):
    f = tmp_path / "hasil.csv"
    f.write_text("close_time,profit\n2026-01-05 10:00,12.5\n2026-02-07 11:00,-2.5\n2026-03-01 09:00,10\n")
    s = baca_pnl_csv(f)
    assert list(s) == [12.5, -2.5, 10.0]
    assert main(["berbagi", "--csv", str(f), "--persen", "20"]) == 0
    out = capsys.readouterr().out
    assert "2026-03" in out and "sisihkan +1.50 USD" in out  # Mar: 20% x 7,5 di atas puncak 12,5
    assert "Total untuk berbagi: +4.00 USD" in out
    assert main(["zakat", "--harta", "200000000", "--harga-gram", "2000000"]) == 0
    assert "Rp5.000.000" in capsys.readouterr().out
    assert main(["tabungan", "--setoran", "100000", "--harga-gram", "2000000", "--bulan", "12"]) == 0
    assert "0.60 gram" in capsys.readouterr().out
    with pytest.raises(ValueError):
        f.write_text("a,b\n1,2\n")
        baca_pnl_csv(f)
