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
    for b in ("MUB", "BEB", "GSB", "ZMB"):                 # = riset: semua *BUSDT sejak 1 Jun 2026
        assert ld.kecualikan(f"{b}USDT", b, 1_781_000_000) == "token saham"
    assert ld.kecualikan("ZKUSDT", "ZK", 1_781_000_000) is None
    assert ld.kecualikan("ARBUSDT", "ARB", 1_679_000_000) is None       # sebelum Jun 2026 tidak


def test_jendela_sama_riset():
    awal, akhir = ld.jendela(T0)
    assert awal % 3600 == 0 and T0 + 3600 <= awal < T0 + 7200
    assert akhir == T0 + 30 * 86400


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
        self.kd = {}
        self.vol = {}

    def simbol_usdt(self):
        return dict(self.simbol)

    def harga_semua(self):
        return dict(self.harga)

    def ticker24(self):
        return {k: {"q": self.vol.get(k, 10_000_000.0), "c": v, "low": v} for k, v in self.harga.items()}

    def waktu_listing(self, sym):
        return self.listing.get(sym)

    def kline(self, sym, interval, start_ms=None, limit=1000, end_ms=None):
        bars = self.kd.get(sym, []) if interval == "1d" else self.k1m.get(sym, [])
        if start_ms is not None:
            bars = [b for b in bars if b.t * 1000 >= start_ms]
        return bars[:limit] if interval != "1d" else bars[-limit:]


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
    awal, _akhir = ld.jendela(d["t_listing"])
    m.pasar.harga["NEWUSDT"] = 3.9                     # turun > 60% tetapi SEBELUM jendela riset (jam penuh >= +60 mnt)
    jam.t += 61
    assert jam.t < awal
    m.satu_putaran()
    assert d["status"] == "pantau" and not m.s["posisi"]
    jam.t = awal + 30
    m.satu_putaran()
    assert d["status"] == "dibeli" and len(m.s["posisi"]) == 1
    pos = next(iter(m.s["posisi"].values()))
    assert pos["usd"] == pytest.approx(50.0)           # 5% dari $1000 (portofolio riset)
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
    for salah in ("/beli SOL nan", "/beli SOL inf", "/beli SOL 20 -5", "/beli SOL 20 5 100", "/beli S$L 20"):
        n = len(m.tg.tombol)
        tangani(m, 1, salah)
        assert len(m.tg.tombol) == n, salah             # tidak ada tombol konfirmasi untuk input salah
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

    gagal = None

    def create_market_buy_order_with_cost(self, sym, cost, params=None):
        if self.gagal:
            raise self.gagal
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
        return dict(self.orders[oid])

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


def test_listing_live_hanya_kabar(tmp_path):
    """Mode live: listing dip (belum lolos uji BARU) hanya mengabari, tidak membuka order."""
    m, jam = _mesin(tmp_path)
    m.broker.live = True                               # broker kertas berpura-pura live (tanpa jaringan)
    m.satu_putaran()
    m.pasar.simbol["NEWUSDT"] = {"base": "NEW", "status": "TRADING"}
    m.pasar.listing["NEWUSDT"] = jam.t + 60
    m.pasar.k1m["NEWUSDT"] = [Bar(jam.t + 60 + 60 * i, 10, 10, 10, 10, 1, 1000) for i in range(60)]
    m.pasar.harga["NEWUSDT"] = 10.0
    jam.t += 4200
    m.satu_putaran()
    jam.t += 400
    m.satu_putaran()
    m.pasar.harga["NEWUSDT"] = 3.0
    jam.t = ld.jendela(m.s["listing"]["NEWUSDT"]["t_listing"])[0] + 30
    m.satu_putaran()
    assert not m.s["posisi"] and m.s["listing"]["NEWUSDT"]["status"] == "sinyal"
    assert any("TIDAK dieksekusi" in p for p in m.tg.pesan)


def test_sl_close_jam_abaikan_wick(tmp_path):
    """SL listing dip dicek di close 1 jam: wick menit di bawah SL tidak menjual bila close jam di atas SL."""
    m, jam = _mesin(tmp_path)
    m.harga = {"XUSDT": 10.0}
    pos = m.buka("listing_dip", "XUSDT", "X", 10.0, 20.0, 0.2, 0.5, 90, info={"sl_close_jam": True})
    jam.t = (int(jam.t // 3600) + 1) * 3600 + 10      # jam baru dimulai
    m.pasar.k1m["XUSDT"] = [Bar(jam.t - 7200, 10, 10, 3, 6), Bar(jam.t - 3600, 6, 7, 4.0, 6.0)]
    m.harga["XUSDT"] = 4.5                             # harga menit di bawah SL 5
    m.kelola()
    assert pos["id"] in m.s["posisi"]                  # close jam 6.0 > SL 5 -> tahan
    jam.t += 3600
    m.pasar.k1m["XUSDT"] = [Bar(jam.t - 7200, 6, 7, 4.0, 6.0), Bar(jam.t - 3600, 6, 6, 4.0, 4.8)]
    m.kelola()
    assert pos["id"] not in m.s["posisi"] and m.s["riwayat"][0]["alasan"] == "SL"


def test_simulasi_candle_entry_dicek():
    """Koreksi 8 Okt: candle tempat limit terisi lalu jatuh > 50% di jam yang sama = SL (simulator lama melewatkannya)."""
    cfg = dict(turun=0.6, tp=0.2, sl=0.5, hari_jendela=30, hari_maks=90)
    jam = [Bar(T0 + 3600 * i, 10, 10, 9, 9.5) for i in range(1, 5)]
    jam += [Bar(T0 + 3600 * 5, 5, 5, 1.5, 3.9), Bar(T0 + 3600 * 6, 3.9, 6.0, 3.8, 5.9)]
    stop = ld.simulasi(jam, T0, 10.0, cfg, sl_mode="stop")
    assert stop["alasan"] == "SL" and stop["keluar"] == pytest.approx(2.0)
    tutup = ld.simulasi(jam, T0, 10.0, cfg, sl_mode="tutup")
    assert tutup["alasan"] == "TP"                     # close 3.9 > SL 2 -> tahan; jam berikut high 6 >= TP 4.8


# ------------------------------------------------------------------ keselamatan uang (review 8 Okt 2026)
class BrokerRagu(KertasBroker):
    """Kertas yang bisa dibuat gagal: beli melempar galat tak terduga, jual sebagian, jual gagal per simbol."""

    def __init__(self, store, modal):
        super().__init__(store, modal, 0.0, 0.0)
        self.galat_beli, self.isi_sebagian, self.gagal_jual = None, None, set()
        self.n_beli = 0

    def beli(self, base, usd, harga_ref, limit=None, client_id=None):
        self.n_beli += 1
        if self.galat_beli:
            raise self.galat_beli
        return super().beli(base, usd, harga_ref, limit, client_id)

    def jual(self, base, qty, harga_ref, limit=None):
        if base in self.gagal_jual:
            raise RuntimeError("bursa error 500")
        if self.isi_sebagian:
            q = qty * self.isi_sebagian
            self.isi_sebagian = None
            isi = super().jual(base, q, harga_ref, limit)
            isi.diminta = qty
            return isi
        return super().jual(base, qty, harga_ref, limit)


def _mesin_ragu(tmp_path):
    m, jam = _mesin(tmp_path)
    m.broker = BrokerRagu(m.store, 1000.0)
    return m, jam


def test_beli_tidak_pasti_menjeda_tanpa_ulang(tmp_path):
    from sniper_bot.broker import TidakPasti
    from sniper_bot.perintah import tangani
    m, jam = _mesin_ragu(tmp_path)
    m.harga = {"AUSDT": 10.0}
    m.broker.galat_beli = TidakPasti("timeout setelah kirim")
    assert m.buka("uji", "AUSDT", "A", 10.0, 20.0, 0.2, None, 5) is None
    assert m.s["jeda"] and len(m.s["pending"]) == 1
    assert any("tidak pasti" in p for p in m.tg.pesan)
    m.broker.galat_beli = None
    assert m.buka("uji", "AUSDT", "A", 10.0, 20.0, 0.2, None, 5) is None     # tidak beli ulang
    assert m.broker.n_beli == 1
    tangani(m, 1, "/lanjut")
    assert m.s["jeda"], "/lanjut ditolak selama ada order tidak pasti"
    tangani(m, 1, "/beres")
    tangani(m, 1, "/lanjut")
    assert not m.s["pending"] and not m.s["jeda"]
    assert m.buka("uji", "AUSDT", "A", 10.0, 20.0, 0.2, None, 5)


def test_galat_tak_terduga_saat_beli_juga_menjeda(tmp_path):
    m, jam = _mesin_ragu(tmp_path)
    m.broker.galat_beli = ValueError("respons aneh")
    assert m.buka("uji", "AUSDT", "A", 10.0, 20.0, 0.2, None, 5) is None
    assert m.s["jeda"] and m.s["pending"]


def test_satu_posisi_gagal_tidak_menghentikan_yang_lain(tmp_path):
    m, jam = _mesin_ragu(tmp_path)
    m.harga = {"AUSDT": 10.0, "BUSDT": 10.0}
    pa = m.buka("uji", "AUSDT", "A", 10.0, 20.0, 0.2, 0.5, 90)
    pb = m.buka("uji", "BUSDT", "B", 10.0, 20.0, 0.2, 0.5, 90)
    m.broker.gagal_jual = {"A"}
    m.harga.update(AUSDT=4.0, BUSDT=4.0)
    m.kelola()
    assert pb["id"] not in m.s["posisi"] and m.s["riwayat"][0]["alasan"] == "SL"
    assert pa["id"] in m.s["posisi"] and pa.get("tidak_pasti")              # A ditandai, bot dijeda
    assert m.s["jeda"]


def test_jual_sebagian_tetap_terbuka(tmp_path):
    m, jam = _mesin_ragu(tmp_path)
    m.harga = {"AUSDT": 10.0}
    pos = m.buka("uji", "AUSDT", "A", 10.0, 20.0, None, 0.5, 90)
    q0 = pos["qty"]
    m.broker.isi_sebagian = 0.4
    m.harga["AUSDT"] = 4.0
    m.kelola()
    assert pos["id"] in m.s["posisi"] and pos["qty"] == pytest.approx(q0 * 0.6)
    m.kelola()                                          # sisa dijual putaran berikutnya
    t = m.s["riwayat"][0]
    assert pos["id"] not in m.s["posisi"] and t["pnl_usd"] == pytest.approx(q0 * 4.0 - 20.0)


def test_rugi_harian_dihitung_dari_awal_hari(tmp_path):
    m, jam = _mesin(tmp_path, risiko={"stop_rugi_harian_usd": 15})
    m.harga = {"AUSDT": 10.0, "BUSDT": 10.0}
    m.buka("uji", "AUSDT", "A", 10.0, 50.0, None, None, 30)
    m.harga["AUSDT"] = 6.0                              # rugi -$20 kemarin
    assert m.boleh_buka("uji", 10) is not None
    jam.t = (int(jam.t // 86400) + 1) * 86400 + 60      # hari UTC baru
    m._hari()
    assert m.rugi_hari_ini() == pytest.approx(0.0)
    assert m.boleh_buka("uji", 10) is None              # rugi kemarin tidak memblokir hari ini
    m.harga["AUSDT"] = 5.0                              # turun lagi -$5 hari ini
    assert m.rugi_hari_ini() == pytest.approx(-5.0)


def test_tp_live_dibatalkan_terisi_sebagian(tmp_path):
    m, jam = _mesin(tmp_path)

    class BrokerTP(KertasBroker):
        live = True

        def __init__(self, store):
            super().__init__(store, 1000.0, 0.0, 0.0)
            self.tp_ke = 0

        def pasang_tp(self, base, qty, harga_tp):
            self.tp_ke += 1
            return f"tp{self.tp_ke}"

        def cek_order(self, base, oid):
            if oid == "tp1":
                return {"status": "canceled", "filled": 2.0, "average": 12.0, "biaya_usd": 0.0}
            return {"status": "open", "filled": 0.0, "average": None, "biaya_usd": 0.0}

        def harga_venue(self, base):
            return None

    m.broker = BrokerTP(m.store)
    m.harga = {"AUSDT": 10.0}
    pos = m.buka("uji", "AUSDT", "A", 10.0, 50.0, 0.2, None, 30)
    q0 = pos["qty"]
    m.kelola()
    assert pos["qty"] == pytest.approx(q0 - 2.0) and pos["tp_order"] == "tp2"
    assert pos["realisasi"] == pytest.approx(24.0)


def test_otorisasi_telegram_from_id_dan_privat():
    from sniper_bot.telegram import Telegram
    tg = Telegram("123:abc", [111])
    pribadi = {"message": {"chat": {"id": 111, "type": "private"}, "from": {"id": 111}, "text": "/status"}}
    grup = {"message": {"chat": {"id": 111, "type": "group"}, "from": {"id": 999}, "text": "/beli SOL 50"}}
    lain = {"message": {"chat": {"id": 222, "type": "private"}, "from": {"id": 222}, "text": "/status"}}
    tombol = {"callback_query": {"id": "c", "from": {"id": 999}, "data": "ya:x",
                                 "message": {"chat": {"id": 111, "type": "private"}}}}
    assert tg._milik(pribadi)
    assert not tg._milik(grup) and not tg._milik(lain) and not tg._milik(tombol)


def test_tombol_dari_chat_lain_ditolak(tmp_path):
    from sniper_bot.perintah import tangani
    m, jam = _mesin(tmp_path)
    m.harga = {"SOLUSDT": 150.0}
    tangani(m, 1, "/beli SOL 20")
    tok = m.tg.tombol[-1][0][0]["callback_data"]
    tangani(m, 2, tok, cbid="cb")
    assert not m.s["posisi"]


def test_beli_manual_ditolak_bila_harga_lari(tmp_path):
    from sniper_bot.perintah import tangani
    m, jam = _mesin(tmp_path)
    m.harga = {"SOLUSDT": 150.0}
    tangani(m, 1, "/beli SOL 20")
    tok = m.tg.tombol[-1][0][0]["callback_data"]
    m.harga["SOLUSDT"] = 155.0                         # > +1% dari harga saat konfirmasi
    tangani(m, 1, tok, cbid="cb")
    assert not m.s["posisi"] and "Tidak dibeli" in m.tg.pesan[-1]


def test_sensor_rahasia(monkeypatch):
    from sniper_bot.telegram import sensor
    monkeypatch.setenv("BURSA_API_SECRET", "rahasiaSekali123")
    t = sensor("GET https://api.binance.com/api/v3/order?symbol=X&signature=abcdef galat rahasiaSekali123 "
               "https://api.telegram.org/bot123:AAbbCC/sendMessage https://eth.example.io/v2/abcdefghijklmnopqrstu")
    assert "abcdef" not in t and "rahasiaSekali123" not in t and "AAbbCC" not in t and "abcdefghijklmnop" not in t


def test_hapus_posisi_tanpa_jual(tmp_path):
    from sniper_bot.perintah import tangani
    m, jam = _mesin(tmp_path)
    m.harga = {"AUSDT": 10.0}
    pos = m.buka("uji", "AUSDT", "A", 10.0, 20.0, None, None, 5)
    kas = m.broker.saldo_usd()
    tangani(m, 1, f"/hapus {pos['id']}")
    tangani(m, 1, m.tg.tombol[-1][0][0]["callback_data"], cbid="cb")
    assert not m.s["posisi"] and m.s["riwayat"][0]["alasan"] == "DIHAPUS"
    assert m.broker.saldo_usd() == pytest.approx(kas)


def test_live_broker_galat_jaringan_tidak_pasti():
    import ccxt
    from sniper_bot.broker import TidakPasti
    lb = _live()
    lb.ex.gagal = ccxt.NetworkError("koneksi putus")
    with pytest.raises(TidakPasti):
        lb.beli("SOL", 50.0, 100.0, client_id="sbP1x1")
    lb.ex.gagal = ccxt.InsufficientFunds("saldo kurang")
    with pytest.raises(TidakBisa):
        lb.beli("SOL", 50.0, 100.0)
    lb.ex.gagal = None
    with pytest.raises(TidakBisa):
        lb.beli("SOL", 2000.0, 100.0)                 # > saldo USDT bebas: ditolak SEBELUM order dikirim


def test_listing_tersentuh_saat_bot_mati_dilewati(tmp_path):
    m, jam = _mesin(tmp_path)
    st = m.strategi["listing_dip"]
    awal, _ = ld.jendela(T0)
    m.s["listing"]["NEWUSDT"] = {"base": "NEW", "t_listing": T0, "p0": 10.0, "limit": 4.0, "status": "pantau",
                                 "catatan": "", "cek_t": awal + 60}
    jam.t = awal + 7200                                # bot mati ±2 jam
    m.pasar.k1m["NEWUSDT"] = [Bar(awal + 60 * i, 5, 5, 3.8 if i == 70 else 4.5, 4.6) for i in range(120)]
    m.harga = {"NEWUSDT": 4.6}
    st.tick_harga()
    d = m.s["listing"]["NEWUSDT"]
    assert d["status"] == "lewat" and "tersentuh" in d["catatan"] and not m.s["posisi"]


def test_listing_ditolak_risiko_dilewati_permanen(tmp_path):
    m, jam = _mesin(tmp_path)
    st = m.strategi["listing_dip"]
    awal, _ = ld.jendela(T0)
    m.s["listing"]["NEWUSDT"] = {"base": "NEW", "t_listing": T0, "p0": 10.0, "limit": 4.0, "status": "pantau",
                                 "catatan": ""}
    jam.t = awal + 10
    m.s["jeda"] = True
    m.harga = {"NEWUSDT": 3.9}
    st.tick_harga()
    assert m.s["listing"]["NEWUSDT"]["status"] == "lewat"          # = portofolio riset: tidak dikejar nanti
    m.s["jeda"] = False
    st.tick_harga()
    assert not m.s["posisi"]


def _bar_hari(t, c, q=1e6, o=None):
    return Bar(t, o if o is not None else c, c * 1.01, c * 0.99, c, 0.0, q)


def test_spot_semesta_volume20():
    t0 = 1_700_000_000 // 86400 * 86400
    zig = [1.0 if i % 2 else -1.0 for i in range(260)]                       # naik-turun: RSI terdefinisi
    btc = [_bar_hari(t0 + 86400 * i, 100 + i + zig[i], q=5e6) for i in range(260)]
    data = {"BTC": btc}
    for k, coin in enumerate(["AAA", "ETH", "USDC", "BBB", "MUDA"]):
        n = 100 if coin == "MUDA" else 260                                   # MUDA < 201 hari -> tidak memenuhi
        data[coin] = [_bar_hari(t0 + 86400 * i, 50 + i * 0.1 + zig[i], q=1e6 * (k + 1)) for i in range(n)]
    pilih = sd.pilih_volume20(data, btc, n=3)
    assert "USDC" not in pilih and "MUDA" not in pilih and len(pilih) == 3
    assert pilih[:2] == ["BTC", "ETH"]                  # urutan model dulu, lalu abjad
    assert set(pilih) == {"BTC", "ETH", "BBB"}          # 3 qv7 terbesar dari yang memenuhi syarat


def test_spot_pindai_jendela_dan_sekali_sehari(tmp_path, monkeypatch):
    m, jam = _mesin(tmp_path)
    m.cfg["spot_dip"].update(aktif=True, semesta="tetap20", koin=["SOL", "ETH"])
    st = sd.SpotDipMesin(m)
    m.strategi = {"spot_dip": st}
    hari = (int(jam.t // 86400) + 1) * 86400
    for c in ("BTC", "SOL", "ETH"):
        m.pasar.kd[f"{c}USDT"] = [_bar_hari(hari - 86400 * (300 - i), 100 + (i % 2)) for i in range(300)]
    m.harga = {"SOLUSDT": 100.0, "ETHUSDT": 100.0, "BTCUSDT": 100.0}
    monkeypatch.setattr(sd, "sinyal", lambda bars, btc, *a, **k: (True, 0.95, "model"))
    jam.t = hari + 3 * 3600                            # di luar jendela 1 jam -> tidak beli
    st.tick_jadwal()
    assert not m.s["posisi"] and "terlewat" in m.tg.pesan[-1]
    hari2 = hari + 86400
    for c in ("BTC", "SOL", "ETH"):
        m.pasar.kd[f"{c}USDT"].append(_bar_hari(hari, 100))
    jam.t = hari2 + 600
    st.tick_jadwal()
    assert {p["base"] for p in m.s["posisi"].values()} == {"SOL", "ETH"}
    for p in m.s["posisi"].values():
        assert p["usd"] == pytest.approx(50.0)          # 10% ekuitas dibatasi maks $50/trade
        assert p["deadline"] == pytest.approx(hari2 + 10 * 86400)
    pid = next(p["id"] for p in m.s["posisi"].values() if p["base"] == "SOL")
    m.tutup(m.s["posisi"][pid], 103.0, "TP")
    m.s["spot_paksa"] = True                            # /pindai lagi hari yang sama -> lihat saja
    st.tick_jadwal()
    assert {p["base"] for p in m.s["posisi"].values()} == {"ETH"}
    assert "lihat saja" in m.tg.pesan[-1]


def test_state_kertas_tidak_terbawa_ke_live(tmp_path):
    from sniper_bot import __main__ as utama
    cfg = copy.deepcopy(konfig.BAWAAN)
    cfg["data_dir"] = str(tmp_path)
    cfg["telegram"]["aktif"] = False
    st = Store(str(utama.dir_state(cfg)))
    st.s["posisi"]["P1"] = {"id": "P1", "live": True, "simbol": "XUSDT"}
    st.simpan()
    with pytest.raises(SystemExit):
        utama.buat_mesin(cfg, tg_mati=True)
    assert utama.dir_state(cfg).name == "kertas"


def test_kunci_satu_proses(tmp_path):
    a, b = Store(str(tmp_path)), Store(str(tmp_path))
    a.kunci()
    with pytest.raises(RuntimeError):
        b.kunci()
