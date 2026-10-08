"""Tes luring sniper_bot (tanpa jaringan): fungsi strategi, paritas 💎 dengan cloud, mesin kertas, risiko, Telegram."""
import copy
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

pytest.importorskip("yaml")

from sniper_bot import config as konfig
from sniper_bot.broker import Isi, KertasBroker, LiveBroker, TidakBisa
from sniper_bot.mesin import Mesin
from sniper_bot.pasar import Bar
from sniper_bot.state import Store
from sniper_bot.strategi import listing_dip as ld
from sniper_bot.strategi import spot_dip as sd

ROOT = Path(__file__).resolve().parent.parent
T0 = 1_790_000_000.0          # Sep 2026


# ------------------------------------------------------------------ fungsi murni listing_dip
def test_p0_vwap_tipikal():
    bars = [Bar(T0 + 60 * i, 10, 11, 9, 10, 1, 100) for i in range(60)]
    assert ld.p0_dari_bar(bars) == pytest.approx(10.0)
    assert ld.p0_dari_bar(bars[:10]) is None            # < 30 menit data


def test_isi_limit_dan_gap():
    assert ld.isi_limit(4.0, Bar(0, 5, 5, 3.9, 4.5)) == 4.0
    assert ld.isi_limit(4.0, Bar(0, 3.5, 3.6, 3.0, 3.2)) == 3.5      # gap di bawah limit -> harga open
    assert ld.isi_limit(4.0, Bar(0, 5, 5, 4.1, 4.5)) is None


def test_keluar_sl_dulu():
    # satu candle menyentuh TP dan SL -> SL (konservatif, sama dengan riset)
    assert ld.keluar_bar(10, 0.2, 0.5, Bar(0, 10, 13, 4, 10)) == (5.0, "SL")
    assert ld.keluar_bar(10, 0.2, 0.5, Bar(0, 10, 13, 9, 12)) == (12.0, "TP")
    assert ld.keluar_bar(10, 0.2, 0.5, Bar(0, 10, 11, 9, 10)) is None


def test_simulasi_satu_listing():
    cfg = dict(turun=0.6, tp=0.2, sl=0.5, hari_jendela=30, hari_maks=90)
    jam = [Bar(T0 + 3600 * i, 10, 10, 9, 9.5) for i in range(1, 50)]
    jam += [Bar(T0 + 3600 * 50, 5, 5, 3.9, 4.0), Bar(T0 + 3600 * 51, 4.0, 4.9, 3.9, 4.8)]
    tr = ld.simulasi(jam, T0, 10.0, cfg)
    assert tr["masuk"] == 4.0 and tr["alasan"] == "TP" and tr["keluar"] == pytest.approx(4.8)


def test_kecualikan_token_saham():
    assert ld.kecualikan("TSLABUSDT", "TSLAB", 1_781_000_000) == "token saham"
    assert ld.kecualikan("ZKUSDT", "ZK", 1_781_000_000) is None


# ------------------------------------------------------------------ paritas 💎 dengan cloud/api/_spot.py
def _bars_dari_parquet(nama: str):
    pd = pytest.importorskip("pandas")
    f = ROOT / "data" / "research" / "eksternal" / "spot_1d" / f"{nama}.parquet"
    if not f.exists():
        pytest.skip("data spot_1d tidak ada")
    d = pd.read_parquet(f)
    return [Bar(t.timestamp(), o, h, lo, c, 0.0, q) for t, o, h, lo, c, q in
            zip(d.index, d.open, d.high, d.low, d.close, d.qvol)]


def test_paritas_spot_dengan_cloud():
    sys.path.insert(0, str(ROOT / "cloud" / "api"))
    import _core  # noqa: F401
    import _spot as cloud
    btc = _bars_dari_parquet("BTC")
    for nama in ("ETH", "SOL", "XLM"):
        coin = _bars_dari_parquet(nama)
        for akhir in range(400, len(coin), 97):
            b = coin[akhir - 400:akhir]
            bt = [x for x in btc if x.t <= b[-1].t][-420:]
            cb = [cloud._core.Bar(datetime.fromtimestamp(x.t, timezone.utc), x.o, x.h, x.l, x.c) for x in b]
            cbt = [cloud._core.Bar(datetime.fromtimestamp(x.t, timezone.utc), x.o, x.h, x.l, x.c) for x in bt]
            f1, f2 = sd.features(b, bt), cloud.features(cb, cbt)
            assert (f1 is None) == (f2 is None)
            if f1 is None:
                continue
            assert f1 == pytest.approx(f2, rel=1e-12, abs=1e-12)
            assert sd.prob(f1) == pytest.approx(cloud.prob(f2), rel=1e-12)
            assert sd.red_rule(f1) == cloud.red_rule(f2)
            assert sd.vol_rank(b) == pytest.approx(cloud.vol_rank(cb))


# ------------------------------------------------------------------ mesin kertas dengan pasar & Telegram palsu
class PasarPalsu:
    def __init__(self):
        self.simbol = {"BTCUSDT": {"base": "BTC", "status": "TRADING"}}
        self.harga = {"BTCUSDT": 80000.0}
        self.listing = {}
        self.k1m = {}

    def simbol_usdt(self):
        return dict(self.simbol)

    def harga_semua(self):
        return dict(self.harga)

    def ticker24(self):
        return {k: {"q": 10_000_000.0, "c": v, "low": v} for k, v in self.harga.items()}

    def waktu_listing(self, sym):
        return self.listing.get(sym)

    def kline(self, sym, interval, start_ms=None, limit=1000, end_ms=None):
        return self.k1m.get(sym, [])[:limit]


class TgPalsu:
    chat_ids = [1]

    def __init__(self):
        self.pesan, self.antri, self.tombol = [], [], []

    def kirim(self, teks, chat_id=None, menu=False, tombol=None):
        self.pesan.append(teks)
        if tombol:
            self.tombol.append(tombol)

    def jawab_tombol(self, *a, **k):
        pass

    def mulai_polling(self, offset):
        pass

    def berhenti(self):
        pass

    def ambil(self):
        out, self.antri = self.antri, []
        return out


class Jam:
    def __init__(self, t):
        self.t = t

    def __call__(self):
        return self.t


def _mesin(tmp_path, **ubah):
    cfg = copy.deepcopy(konfig.BAWAAN)
    cfg["data_dir"] = str(tmp_path)
    cfg["spot_dip"]["aktif"] = False
    for k, v in ubah.items():
        cfg[k].update(v)
    store = Store(cfg["data_dir"])
    jam = Jam(T0)
    m = Mesin(cfg, store, PasarPalsu(), KertasBroker(store, 1000.0, 0.0, 0.0), TgPalsu(), sekarang=jam)
    m.strategi["listing_dip"] = ld.ListingDipMesin(m)
    return m, jam


def test_alur_listing_kertas(tmp_path):
    m, jam = _mesin(tmp_path)
    m.satu_putaran()                                   # putaran pertama: BTC dikenal
    # listing baru muncul
    m.pasar.simbol["NEWUSDT"] = {"base": "NEW", "status": "TRADING"}
    m.pasar.listing["NEWUSDT"] = jam.t + 60
    m.pasar.k1m["NEWUSDT"] = [Bar(jam.t + 60 + 60 * i, 10, 10, 10, 10, 1, 1000) for i in range(60)]
    m.pasar.harga["NEWUSDT"] = 10.0
    jam.t += 400
    m.satu_putaran()
    assert any("Listing baru" in p for p in m.tg.pesan)
    jam.t += 3700                                      # P0 dihitung setelah 60 menit
    m.satu_putaran()
    d = m.s["listing"]["NEWUSDT"]
    assert d["status"] == "pantau" and d["limit"] == pytest.approx(4.0)
    m.pasar.harga["NEWUSDT"] = 3.9                     # turun > 60%
    jam.t += 61
    m.satu_putaran()
    assert d["status"] == "dibeli" and len(m.s["posisi"]) == 1
    pos = next(iter(m.s["posisi"].values()))
    assert pos["usd"] == pytest.approx(50.0)           # 10% dari $1000 dibatasi maks $50/trade
    assert pos["entry"] == pytest.approx(3.9)
    m.pasar.harga["NEWUSDT"] = 3.9 * 1.21              # TP +20%
    jam.t += 61
    m.satu_putaran()
    assert not m.s["posisi"] and m.s["riwayat"][0]["alasan"] == "TP"
    assert m.s["riwayat"][0]["pnl_usd"] == pytest.approx(10.0, rel=1e-6)
    assert m.broker.saldo_usd() == pytest.approx(1010.0)


def test_sl_dan_batas_waktu(tmp_path):
    m, jam = _mesin(tmp_path)
    m.harga = {"AUSDT": 10.0, "BUSDT": 10.0}
    pa = m.buka("uji", "AUSDT", "A", 10.0, 20.0, 0.2, 0.5, 90)
    pb = m.buka("uji", "BUSDT", "B", 10.0, 20.0, 0.2, None, 1)
    m.harga["AUSDT"] = 4.9
    jam.t += 86401
    m.kelola()
    alasan = {t["simbol"]: t["alasan"] for t in m.s["riwayat"]}
    assert alasan == {"AUSDT": "SL", "BUSDT": "WAKTU"}
    assert pa and pb


def test_batas_risiko(tmp_path):
    m, jam = _mesin(tmp_path, risiko={"maks_posisi": 2, "maks_usd_per_trade": 50, "maks_total_usd": 300,
                                      "stop_rugi_harian_usd": 15})
    m.harga = {f"{c}USDT": 10.0 for c in "ABCD"}
    assert m.buka("uji", "AUSDT", "A", 10, 50, 0.2, 0.5, 90)
    assert m.buka("uji", "BUSDT", "B", 10, 50, 0.2, 0.5, 90)
    assert m.buka("uji", "CUSDT", "C", 10, 50, 0.2, 0.5, 90) is None      # maks 2 posisi
    m.harga["AUSDT"] = 6.5                                                  # rugi mengambang -$17,5
    m.cfg["risiko"]["maks_posisi"] = 5
    assert m.buka("uji", "DUSDT", "D", 10, 50, 0.2, 0.5, 90) is None       # stop rugi harian
    assert m.s["hari"]["jeda_rugi"]
    m.s["jeda"] = True
    assert "dijeda" in m.boleh_buka("uji", 10)


def test_perintah_telegram_konfirmasi(tmp_path):
    from sniper_bot.perintah import tangani
    m, jam = _mesin(tmp_path)
    m.harga = {"SOLUSDT": 150.0}
    tangani(m, 1, "/beli SOL 20 5 10")
    assert m.tg.tombol, "perintah beli harus minta konfirmasi"
    tok = m.tg.tombol[-1][0][0]["callback_data"]
    assert not m.s["posisi"]
    tangani(m, 1, tok, cbid="cb1")
    pos = next(iter(m.s["posisi"].values()))
    assert pos["tp_px"] == pytest.approx(pos["entry"] * 1.05) and pos["sl_px"] == pytest.approx(pos["entry"] * 0.9)
    tangani(m, 1, "/beli SOL 9999")                    # di atas batas per trade
    assert "Maks" in m.tg.pesan[-1]
    tangani(m, 1, f"/tutup {pos['id']}")
    tangani(m, 1, m.tg.tombol[-1][0][1]["callback_data"], cbid="cb2")      # tekan Batal
    assert m.s["posisi"]
    for teks in ("📊 Status", "/posisi", "/riwayat", "/listing", "/strategi", "/jeda", "/lanjut", "/bantuan", "halo"):
        tangani(m, 1, teks)
    assert not m.s["jeda"]


def test_tombol_kedaluwarsa(tmp_path):
    from sniper_bot.perintah import tangani
    m, jam = _mesin(tmp_path)
    m.harga = {"SOLUSDT": 150.0}
    tangani(m, 1, "/beli SOL 20")
    tok = m.tg.tombol[-1][0][0]["callback_data"]
    jam.t += 300
    tangani(m, 1, tok, cbid="cb")
    assert not m.s["posisi"]


def test_state_atomik(tmp_path):
    s = Store(str(tmp_path))
    s.s["jeda"] = True
    s.simpan()
    assert Store(str(tmp_path)).s["jeda"] is True
    (tmp_path / "state.json").write_text("{rusak")
    assert Store(str(tmp_path)).s["posisi"] == {}       # file rusak dicadangkan, mulai bersih


# ------------------------------------------------------------------ LiveBroker dengan bursa palsu (tanpa jaringan)
class BursaPalsu:
    id = "binance"
    has = {"createMarketBuyOrderWithCost": True}

    def __init__(self):
        self.markets = {"SOL/USDT": {"active": True, "spot": True, "limits": {"amount": {"min": 0.001},
                                                                             "cost": {"min": 5}}}}
        self.orders, self.bal = {}, {"USDT": {"free": 1000.0}, "SOL": {"free": 0.0}}

    def fetch_ticker(self, sym):
        return {"last": 100.0, "ask": 100.1}

    def amount_to_precision(self, sym, x):
        return f"{int(x * 1000) / 1000:.3f}"

    def price_to_precision(self, sym, x):
        return f"{x:.2f}"

    def create_market_buy_order_with_cost(self, sym, cost):
        qty = cost / 100.1
        self.bal["SOL"]["free"] += qty * 0.999
        o = {"id": "b1", "status": "closed", "filled": qty, "average": 100.1,
             "fee": {"cost": qty * 0.001, "currency": "SOL"}}
        self.orders["b1"] = o
        return o

    def create_order(self, sym, typ, side, qty, price=None, params=None):
        oid = f"o{len(self.orders) + 1}"
        st = "closed" if typ == "market" else "open"
        o = {"id": oid, "status": st, "filled": float(qty) if st == "closed" else 0.0, "average": 100.0,
             "price": price, "fee": {"cost": 0.1, "currency": "USDT"}}
        self.orders[oid] = o
        return o

    def fetch_order(self, oid, sym):
        return self.orders[oid]

    def cancel_order(self, oid, sym):
        self.orders[oid]["status"] = "canceled"

    def fetch_balance(self):
        return self.bal


def _live():
    lb = LiveBroker.__new__(LiveBroker)
    lb.ex, lb.quote, lb.nama = BursaPalsu(), "USDT", "binance"
    return lb


def test_live_broker_beli_tp_jual():
    lb = _live()
    isi = lb.beli("SOL", 50.0, 100.0)
    assert isinstance(isi, Isi) and isi.qty == pytest.approx(50 / 100.1 * 0.999)
    assert isi.biaya_usd == pytest.approx(50 / 100.1 * 0.001 * 100.1)
    oid = lb.pasang_tp("SOL", isi.qty, 103.0)
    assert lb.ex.orders[oid]["price"] == 103.0
    lb.batal("SOL", oid)
    assert lb.cek_order("SOL", oid)["status"] == "canceled"
    j = lb.jual("SOL", isi.qty, 100.0)
    assert j.qty > 0


def test_live_broker_minimum_dan_pasar():
    lb = _live()
    with pytest.raises(TidakBisa):
        lb.beli("SOL", 1.0, 100.0)                     # < $5 minimum bursa
    with pytest.raises(TidakBisa):
        lb.beli("XYZ", 50.0, 1.0)                      # pasar tidak ada
    with pytest.raises(TidakBisa):
        lb.beli("SOL", 50.0, 100.0, limit=90.0)        # harga sudah di atas limit


def test_config_periksa(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text("risiko: {maks_usd_per_trade: 500, maks_total_usd: 100}\n")
    with pytest.raises(ValueError):
        konfig.muat(str(p))
    p.write_text("mode: nyata\n")
    with pytest.raises(ValueError):
        konfig.muat(str(p))
