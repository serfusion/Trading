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
    assert d["binance"] or d["mql5"]
    for x in d["binance"] + d["mql5"]:
        assert x["url"].startswith(("https://www.binance.com/", "https://www.mql5.com/"))
        assert x["mdd"] <= 20 and x["wr"] >= 60 and x["paruh"][0] > 0 and x["paruh"][1] > 0
        for k in ("name", "roi", "pengikut", "aset", "platform"):
            assert k in x
    assert "skor" not in json.dumps(d)
