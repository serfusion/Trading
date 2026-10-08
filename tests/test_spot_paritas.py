"""Paritas 💎 spot dip: cloud/api/_spot.py (branch ini) dan port bot Telegram (sniper_bot) terhadap fixture
tests/data/spot_dip_paritas.json (dibuat `python -m research.spot_paritas fixture`; luring, tanpa jaringan)."""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
FIX = json.loads((ROOT / "tests" / "data" / "spot_dip_paritas.json").read_text(encoding="utf-8"))


def _cloud():
    p = str(ROOT / "cloud" / "api")
    if p not in sys.path:
        sys.path.insert(0, p)
    import _core
    import _spot
    return _core, _spot


def _cbars(core, rows):
    return [core.Bar(datetime.fromisoformat(r[0]).replace(tzinfo=timezone.utc), r[1], r[2], r[3], r[4]) for r in rows]


def test_fixture_cukup_dan_model_sama():
    assert len(FIX["contoh"]) >= 30
    model = (ROOT / "cloud" / "api" / "spot_model.json").read_bytes()
    assert hashlib.sha256(model).hexdigest() == FIX["model_sha256"], "spot_model.json berubah: buat ulang fixture"
    salinan = ROOT / "sniper_bot" / "strategi" / "spot_model.json"
    if salinan.exists():
        assert hashlib.sha256(salinan.read_bytes()).hexdigest() == FIX["model_sha256"]
    kat = {e["kategori_pilih"] for e in FIX["contoh"]}
    for k in ("model", "3 merah", "dilewati vol > P90", "BTC di bawah SMA200", "sinyal gagal (batas waktu)",
              "data < 201 hari"):
        assert k in kat


@pytest.mark.parametrize("e", FIX["contoh"], ids=[e["id"] for e in FIX["contoh"]])
def test_cloud_cocok_fixture(e):
    core, sp = _cloud()
    h = e["harapan"]
    bars = _cbars(core, e["bars"])
    btc = _cbars(core, e["btc_bars"] or e["bars"])
    x = sp.features(bars, btc)
    assert (x is None) == (h["features"] is None)
    vr = sp.vol_rank(bars)
    assert (vr is None) == (h["vol_rank"] is None)
    if vr is not None:
        assert vr == pytest.approx(h["vol_rank"], rel=1e-12, abs=1e-12)
    if x is None:
        assert not (h["cloud_branch_ini"] or {}).get("beli")
        return
    assert x == pytest.approx(h["features"], rel=1e-12, abs=1e-12)
    p = sp.prob(x)
    assert p == pytest.approx(h["prob"], rel=1e-12)
    assert sp.red_rule(x) == h["red_rule"]
    # keputusan spot_tick branch ini = fitur ada, vol_rank <= skip_vol, (p >= ambang ATAU 3 merah)
    m = FIX["model"]
    beli = (vr is None or vr <= m["skip_vol"]) and (p >= m["ambang"] or h["red_rule"])
    assert beli == bool((h["cloud_branch_ini"] or {}).get("beli"))
    cb = h["cloud_branch_ini"] or {}
    if cb.get("beli"):
        alasan = "model + 3 merah" if p >= m["ambang"] and h["red_rule"] else "model" if p >= m["ambang"] else "3 merah"
        assert cb["alasan"] == alasan
        assert cb["entry"] == e["sesudah"][0][1]                  # harga beli = open hari entry (pindai 00:05 UTC)
        lab = h["label_riset"]
        assert cb["close"]["r_persen"] == pytest.approx(lab["r"] * 100, abs=0.011)   # TP dibulatkan 8 desimal di cloud


@pytest.mark.parametrize("e", FIX["contoh"], ids=[e["id"] for e in FIX["contoh"]])
def test_bot_sniper_cocok_fixture(e):
    sd = pytest.importorskip("sniper_bot.strategi.spot_dip")
    from sniper_bot.pasar import Bar

    def tb(r):
        return Bar(datetime.fromisoformat(r[0]).replace(tzinfo=timezone.utc).timestamp(), r[1], r[2], r[3], r[4],
                   0.0, r[5])
    h = e["harapan"]
    bars = [tb(r) for r in e["bars"]]
    btc = [tb(r) for r in (e["btc_bars"] or e["bars"])]
    x = sd.features(bars, btc)
    assert (x is None) == (h["features"] is None)
    if x is not None:
        assert x == pytest.approx(h["features"], rel=1e-12, abs=1e-12)
        assert sd.prob(x) == pytest.approx(h["prob"], rel=1e-12)
        assert sd.red_rule(x) == h["red_rule"]
    vr = sd.vol_rank(bars)
    assert (vr is None) == (h["vol_rank"] is None)
    beli, _p, _alasan = sd.sinyal(bars, btc, filter_btc=False, filter_kualitas=False)
    assert beli == bool((h["cloud_branch_ini"] or {}).get("beli"))
    beli2, _p, _alasan = sd.sinyal(bars, btc, filter_btc=True, filter_kualitas=False)
    assert beli2 == h["bot_bawaan_beli"]
