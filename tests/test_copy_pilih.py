"""👥 Pemilih copy trader (research/copy_pilih.py) & file cloud/api/copytrader.json yang dibaca aplikasi."""
import gzip
import json
from pathlib import Path

import numpy as np
import pandas as pd

from research import copy_pilih as C

ROOT = Path(__file__).resolve().parent.parent


def _row(pid, roi_path, mdd=10.0, wr=80.0, copiers=50, copier_pnl=100.0, age_days=400):
    now_ms = C.NOW.value // 1_000_000
    return {"leadPortfolioId": pid, "nickname": pid, "currentCopyCount": copiers, "maxCopyCount": 200,
            "roi": float(roi_path[-1]), "mdd": mdd, "winRate": wr, "copierPnl": copier_pnl,
            "startTime": now_ms - age_days * 86_400_000,
            "chartItems": [{"value": float(v)} for v in roi_path]}


def test_binance_saringan(tmp_path, monkeypatch):
    monkeypatch.setattr(C.B, "DIR", tmp_path)
    naik = np.linspace(0, 50, 365) + np.sin(np.arange(365)) * 0.5        # naik di kedua paruh, aktif tiap hari
    paruh2_rugi = np.r_[np.linspace(0, 60, 181), np.linspace(60, 40, 184)]
    diam = np.r_[np.linspace(0, 50, 335), np.full(30, 50.0)]              # tidak berdagang 30 hari terakhir
    rows = [_row("ok", naik), _row("paruh2", paruh2_rugi), _row("diam", diam), _row("dd", naik, mdd=35),
            _row("wr", naik, wr=50), _row("muda", naik, age_days=200), _row("sepi", naik, copiers=5),
            _row("pengikut_rugi", naik, copier_pnl=-1), _row("sempurna", naik, wr=99.9)]
    (tmp_path / "list_365D.json.gz").write_bytes(gzip.compress(json.dumps(rows).encode()))
    out = C.binance(segar=False)
    assert [x["id"] for x in out] == ["ok", "sempurna"] or [x["id"] for x in out] == ["sempurna", "ok"]
    sempurna = next(x for x in out if x["id"] == "sempurna")
    assert sempurna["wr_curiga"] is True
    assert next(x for x in out if x["id"] == "ok")["wr_curiga"] is False
    assert all(x["url"].startswith("https://www.binance.com/") for x in out)


def test_file_cloud_untuk_aplikasi():
    d = json.loads((ROOT / "cloud" / "api" / "copytrader.json").read_text(encoding="utf-8"))
    pd.Timestamp(d["dibuat"])
    assert d["uji"]["binance"] and d["uji"]["mql5"] and d["kesimpulan"]
    semua = sum((d.get(k, []) for k in ("hl_trader", "okx", "bitget", "hyperliquid", "etoro", "binance", "mql5",
                                        "gabungan")), [])
    assert semua and d["gabungan"] and d["singkat"]
    for x in semua:
        assert x["url"].startswith(("https://www.etoro.com/people/", "https://www.binance.com/", "https://www.mql5.com/",
                                    "https://www.okx.com/", "https://www.bitget.com/", "https://app.hyperliquid.xyz/"))
        assert x["mdd"] <= 20 and x["wr"] >= 60 and x["paruh"][0] > 0 and x["paruh"][1] > 0
        for k in ("name", "roi", "pengikut", "aset", "platform"):
            assert k in x
    assert "skor" not in json.dumps(d)
    g = d["gabungan"]
    assert all(x["pengikut"] >= 30 or x.get("modal", 0) >= 100_000 for x in g)
    sk = [(x.get("tier", 3), -x["roi"] / max(x["mdd"], 3)) for x in g]     # 🥇 → 🥈 → 🥉, lalu profit/DD
    assert sk == sorted(sk)
    assert max(sum(1 for x in g if x["sumber"] == s) for s in {x["sumber"] for x in g}) <= 6


def test_etoro_saringan(tmp_path, monkeypatch):
    monkeypatch.setattr(C.E, "DIR", tmp_path)
    (tmp_path / "hist").mkdir()
    now = C.NOW.tz_localize(None).to_period("M")
    months = [now - i for i in range(24, 0, -1)]                         # 24 bulan penuh sebelum bulan ini

    def hist(cid, gains):
        (tmp_path / "hist" / f"{cid}.json").write_text(json.dumps(
            {"monthly": [{"start": f"{m.start_time:%Y-%m-%d}T00:00:00Z", "gain": g, "isSimulation": False}
                         for m, g in zip(months, gains)]}))

    base = {"Verified": True, "IsFund": False, "Copiers": 50, "WeeksSinceRegistration": 200, "Gain": 20.0,
            "PeakToValley": -8.0, "WinRatio": 70.0, "RiskScore": 4, "TopTradedAssetClassId": 5}
    rows = [dict(base, CustomerId=1, UserName="Bagus"), dict(base, CustomerId=2, UserName="Rugi_Paruh2"),
            dict(base, CustomerId=3, UserName="Risiko_Tinggi", RiskScore=8), dict(base, CustomerId=4, UserName="Anjlok")]
    hist(1, [1.5] * 24)
    hist(2, [3.0] * 18 + [-1.0] * 6)
    hist(3, [1.5] * 24)
    hist(4, [2.0] * 20 + [-12.0] + [2.0] * 3)
    (tmp_path / "pilih_rankings.json").write_text(json.dumps(rows))
    out = C.etoro(segar=False)
    assert [x["name"] for x in out] == ["Bagus"]
    x = out[0]
    assert x["url"] == "https://www.etoro.com/people/bagus" and x["aset"] == "saham" and x["risiko"] == 4
    assert abs(x["roi"] - ((1.015 ** 12) - 1) * 100) < 0.2


def test_kurva_lolos():
    t = pd.date_range("2025-10-01", periods=366, freq="D")
    naik = pd.Series(np.linspace(1, 1.4, 366) + np.sin(np.arange(366)) * 0.002, index=t)
    k = C._kurva(naik)
    assert k["hari"] == 365 and k["roi"] > 0.3 and k["h1"] > 0 and k["h2"] > 0 and C._lolos(k, 300)
    jatuh = naik.copy()
    jatuh.iloc[200:] *= 0.7                                             # DD 30% → gagal
    assert not C._lolos(C._kurva(jatuh), 300)
    assert not C._lolos(k, 400)                                         # riwayat kurang panjang


def test_tier_dan_terlihat(monkeypatch):
    base = {"roi": 40.0, "mdd": 8.0, "wr": 70.0}
    assert C.tier(dict(base, terlihat=True)) == 1                         # 40/8 = 5 ≥ 4, terlihat
    assert C.tier(dict(base, terlihat=False)) == 2                        # tidak terlihat → maks 🥈
    assert C.tier(dict(base, terlihat=True, wr_curiga=True)) == 2
    assert C.tier({"roi": 10.0, "mdd": 8.0, "wr": 70.0, "terlihat": True}) == 3
    assert C.cek_terlihat({"platform": "Hyperliquid", "id": "0x1"}) is True
    assert C.cek_terlihat({"platform": "MQL5 MT5", "id": "1"}) is False
    monkeypatch.setattr(C.CM, "req", lambda url, body=None, tries=4: {"data": {"positionShow": False}})
    assert C.cek_terlihat({"platform": "Binance", "id": "9"}) is False
    monkeypatch.setattr(C.CM, "req", lambda url, body=None, tries=4: {"data": [{"instId": ""}]})
    assert C.cek_terlihat({"platform": "OKX", "id": "A"}) is False


def test_hl_trader_wr_fills():
    from research import hl_trader as H
    fills = [{"coin": "BTC", "time": 1, "dir": "Close Long", "closedPnl": "10", "fee": "1"},
             {"coin": "BTC", "time": 1, "dir": "Close Long", "closedPnl": "-2", "fee": "0"},   # satu transaksi (+7)
             {"coin": "ETH", "time": 2, "dir": "Close Short", "closedPnl": "1", "fee": "2"},   # rugi setelah biaya
             {"coin": "ETH", "time": 3, "dir": "Open Long", "closedPnl": "0", "fee": "1"}]
    assert H.wr_fills(fills) == (50.0, 2, 3)
    rows = [{"ethAddress": "a", "accountValue": "5e6", "windowPerformances": [["month", {"vlm": "1e8"}],
                                                                          ["allTime", {"vlm": "1e9"}]]},
            {"ethAddress": "mm", "accountValue": "5e6", "windowPerformances": [["month", {"vlm": "1e10"}],
                                                                           ["allTime", {"vlm": "1e11"}]]},
            {"ethAddress": "kecil", "accountValue": "500", "windowPerformances": [["month", {"vlm": "1e3"}],
                                                                              ["allTime", {"vlm": "1e4"}]]}]
    assert [r["ethAddress"] for r in H.kandidat(rows)] == ["a"]
