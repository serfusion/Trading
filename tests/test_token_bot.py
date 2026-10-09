"""Tes luring token_bot (tanpa jaringan): poolId, harga sqrtPrice, keputusan beli/jual, pengaman."""
from datetime import datetime, timezone

import pytest

pytest.importorskip("eth_abi")

from eth_abi import decode

from token_bot import acuan, strategi
from token_bot.dex import Pool, sqrtp_harga

USDG = "0x5fc5360d0400a0fd4f2af552add042d716f1d168"
CRCL = "0xdf0992e440dd0be65bd8439b609d6d4366bf1cb5"


def test_pool_id_v4_crcl():
    # pool CRCL/USDG v4 Robinhood Chain (dibaca dari event Initialize 8 Okt 2026)
    p = Pool(4, "0xdb9c34002d173981250969293af6f43f42a26f2110f19893bbe2ad373375e9e6", USDG, CRCL, 8388608, 60,
             "0x5eb87f69be00df39981622fd60a8de4b7837e080", 6, 18)
    assert p.pool_id() == p.id


def test_sqrtp_harga():
    # 1 token0 (6 desimal) = 0,0125 token1 (18 desimal)
    raw = 0.0125 * 10 ** (18 - 6)
    sq = int((raw ** 0.5) * 2 ** 96)
    assert sqrtp_harga(sq, 6, 18) == pytest.approx(0.0125, rel=1e-9)


def _pas(**kw):
    p = Pool(4, "0x" + "11" * 32, USDG, CRCL, 3000, 60, "0x" + "00" * 20, 6, 18)
    d = dict(nama="CRCL/USDG", pool=p, token=CRCL, quote=USDG, acuan_token="tetap:80", acuan_quote="tetap:1",
             ukuran_usd=1000, min_usd=10, beli_bawah=0.01, jual_atas=0.01, max_slippage=0.005, biaya_gas_usd=0)
    d.update(kw)
    return strategi.Pasangan(**d)


def _pasang(monkeypatch, harga_spot: float, slip_per_1000: float, pp_pajak: float = 0.0):
    """Pool palsu: CRCL spot `harga_spot` USDG; slippage linear terhadap ukuran; jual-balik kena pajak opsional."""
    monkeypatch.setattr(strategi, "harga_spot_token", lambda rpc, p, sv: harga_spot)

    def q(rpc, pool, token_in, amount, quoter):
        if token_in == USDG:
            usd = amount / 1e6
            px = harga_spot * (1 + slip_per_1000 * usd / 1000)
            return int(usd / px * 1e18)
        tok = amount / 1e18
        px = harga_spot * (1 - slip_per_1000 * tok * harga_spot / 1000) * (1 - pp_pajak)
        return int(tok * px * 1e6)

    monkeypatch.setattr(strategi, "quote", q)


def test_beli_bila_murah(monkeypatch):
    _pasang(monkeypatch, 78.0, 0.002)           # pool 2,5% di bawah acuan 80, slippage 0,2%/$1000
    r = strategi.evaluasi(None, _pas(), "q")
    assert r["aksi"] == "BELI" and r["untung_beli"] > 0.02
    # untung bersih = diskon dikurangi biaya jual balik di DEX -> lebih kecil dari diskon
    assert 0 < r["untung_bersih"] < r["untung_beli"]


def test_diskon_habis_dimakan_biaya_keluar(monkeypatch):
    # diskon ±1,7% tetapi biaya jual balik ±0,8% -> bersih < 1% -> TIDAK ada sinyal
    _pasang(monkeypatch, 78.0, 0.008)
    r = strategi.evaluasi(None, _pas(max_slippage=0.02), "q")
    assert r["untung_beli"] >= 0.01 and r["untung_bersih"] < 0.01 and r["aksi"] != "BELI"


def test_tebus_manual(monkeypatch):
    _pasang(monkeypatch, 40.0, 0.002)           # token jembatan dijual 50% di bawah acuan
    r = strategi.evaluasi(None, _pas(tebus_manual=True, biaya_tebus=0.01), "q")
    assert r["aksi"] == "BELI" and r["nilai_tebus"] == pytest.approx(80 * 0.99)
    assert r["untung_bersih"] == pytest.approx(80 * 0.99 / r["harga_beli"] - 1, rel=1e-9)
    # posisi token jembatan: tidak ada sinyal JUAL DEX walau TP/SL tersentuh
    r2 = strategi.evaluasi(None, _pas(tebus_manual=True), "q", posisi={"token": int(1e18), "harga": 10.0})
    assert r2["aksi"] == "TUNGGU" and "TEBUS" in r2["alasan"]


def test_premi_hanya_info(monkeypatch):
    _pasang(monkeypatch, 83.0, 0.0001)          # pool 3,75% DI ATAS acuan, tanpa posisi
    r = strategi.evaluasi(None, _pas(), "q")
    assert r["aksi"] == "INFO_PREMI"


def test_ukuran_dikecilkan_sampai_slippage_muat(monkeypatch):
    _pasang(monkeypatch, 78.0, 0.02)            # 2%/$1000 -> perlu <= $250 agar <= 0,5%
    r = strategi.evaluasi(None, _pas(), "q")
    assert r["ukuran_usd"] <= 250 and r["slippage_beli"] <= 0.005 and r["aksi"] == "BELI"


def test_likuiditas_tipis_dilewati(monkeypatch):
    _pasang(monkeypatch, 70.0, 1.0)             # slippage 100%/$1000 -> $10 pun 1%
    r = strategi.evaluasi(None, _pas(), "q")
    assert r["aksi"] == "TUNGGU" and "likuiditas" in r["alasan"]


def test_honeypot_dilewati(monkeypatch):
    _pasang(monkeypatch, 70.0, 0.001, pp_pajak=0.2)   # murah tapi jual-balik kena 20%
    r = strategi.evaluasi(None, _pas(), "q")
    assert r["aksi"] == "TUNGGU" and "honeypot" in r["alasan"]


def test_acuan_saham_tutup(monkeypatch):
    _pasang(monkeypatch, 70.0, 0.001)
    monkeypatch.setattr(acuan, "buka", lambda spec, now=None: False)
    r = strategi.evaluasi(None, _pas(), "q")
    assert r["aksi"] == "TUNGGU" and "acuan tutup" in r["alasan"]


def test_tp_posisi(monkeypatch):
    _pasang(monkeypatch, 82.0, 0.0001)
    r = strategi.evaluasi(None, _pas(tp=0.02), "q", posisi={"token": int(1e18), "harga": 78.0})
    assert r["aksi"] == "JUAL" and r["alasan"].startswith("TP")


def test_jam_bursa():
    senin_buka = datetime(2026, 10, 5, 14, 0, tzinfo=timezone.utc)    # 10:00 New York
    sabtu = datetime(2026, 10, 10, 15, 0, tzinfo=timezone.utc)
    senin_pagi = datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc)    # 08:00 New York
    assert acuan.buka("saham:CRCL", senin_buka)
    assert not acuan.buka("saham:CRCL", sabtu)
    assert not acuan.buka("saham:CRCL", senin_pagi)
    assert acuan.buka("binance:ETHUSDT", sabtu)


def test_pool_key_encode():
    from eth_abi import encode
    p = Pool(4, "0x" + "11" * 32, USDG, CRCL, 3000, 60, "0x" + "00" * 20, 6, 18)
    (k,) = decode(["(address,address,uint24,int24,address)"], encode(["(address,address,uint24,int24,address)"],
                                                                   [p.key]))
    assert k[2] == 3000 and k[3] == 60


def test_tidak_ada_modul_transaksi():
    # bot ini sengaja TIDAK bisa mengirim transaksi (tanpa private key) — docs/ARB_BOT.md
    import importlib.util
    assert importlib.util.find_spec("token_bot.eksekusi") is None


def test_sensor_url_rpc():
    from token_bot.tele import rahasia_url, sensor
    url = "https://arc-mainnet.contoh.io/v2/RAHASIA0123456789abcdef"
    rahasia_url(url)
    out = sensor(f"galat ke {url} timeout")
    assert "RAHASIA" not in out and "arc-mainnet.contoh.io" in out


def test_rpc_galat_hanya_host(monkeypatch):
    import urllib.error
    import urllib.request

    from token_bot.rpc import Rpc, RpcError
    url = "https://rpc.contoh.io/v2/KUNCIRAHASIA0123456789"

    def gagal(req, timeout=None):
        raise urllib.error.HTTPError(url, 403, "Forbidden", {}, None)
    monkeypatch.setattr(urllib.request, "urlopen", gagal)
    with pytest.raises(RpcError) as e:
        Rpc(url).call("eth_blockNumber", [])
    assert "KUNCI" not in str(e.value) and "rpc.contoh.io" in str(e.value)


# ------------------------------------------------------------------ bot kontrol Telegram (pantau_bot), tanpa jaringan
from token_bot.pantau_bot import Bot, Store      # noqa: E402


class TgPalsu:
    chat_ids = [1]

    def __init__(self):
        self.pesan, self.tombol, self.antri = [], [], []

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


def _bot(tmp_path, mode="kertas", r=None, monkeypatch=None, **cfg_kw):
    cfg = {"mode": mode, "modal_kertas_usd": 500, "interval": 5, "maks_trade_per_hari": 3,
           "jaringan": {"x": {"v4_quoter": "q", "v3_quoter": "q"}}, "pasangan": [{"jaringan": "x"}], **cfg_kw}
    p = _pas()
    store = Store(tmp_path / mode)
    jam = Jam(1_790_000_000.0)
    b = Bot(cfg, store, {"x": None}, [("x", p)], TgPalsu(), sekarang=jam)
    if r is not None:
        b._eval = lambda net, pas: dict(r)
    return b, jam


RBELI = {"aksi": "BELI", "alasan": "murah", "harga_beli": 78.0, "wajar": 80.0, "untung_beli": 0.025,
         "untung_bersih": 0.02, "ukuran_usd": 100, "slippage_beli": 0.003, "quote_usd": 1.0}


def test_bot_pantau_hanya_kabar(tmp_path):
    b, jam = _bot(tmp_path, "pantau", r=RBELI)
    b.putaran()
    assert not b.s["posisi"] and any("PELUANG BELI" in x for x in b.tg.pesan)
    n = len(b.tg.pesan)
    jam.t += 10                                     # pindai lagi 10 dtk kemudian: kabar sama DIJEDA (jeda_kabar 60)
    b.putaran()
    assert len(b.tg.pesan) == n
    b.perintah(1, "🅰 BUY ON/OFF", None)            # pantau: BUY ON tidak tersedia
    assert not b.s["buy_on"]


def test_bot_kertas_beli_lalu_jual(tmp_path):
    b, jam = _bot(tmp_path, "kertas", r=RBELI)
    b.s["buy_on"] = True
    b.putaran()                                     # putaran pertama: pindai jalan (jadwal kosong) -> beli
    pos = b.s["posisi"]["CRCL/USDG"]
    assert pos["usd"] == 100 and b.s["kas_kertas"] == 400
    assert pos["token"] == pytest.approx(100 / 78.0)
    # sekarang JUAL di 82
    b._eval = lambda net, p: {"aksi": "JUAL", "alasan": "TP", "harga_jual": 82.0, "wajar": 80.0}
    b.jadwal.pop("pindai", None)
    b.putaran()
    assert "CRCL/USDG" not in b.s["posisi"]
    assert b.s["kas_kertas"] == pytest.approx(400 + 100 / 78.0 * 82.0)


def test_bot_stop_menahan_pindai(tmp_path):
    b, jam = _bot(tmp_path, "kertas", r={"aksi": "BELI", "alasan": "m", "harga_beli": 78.0, "wajar": 80.0,
                                         "untung_beli": 0.02, "ukuran_usd": 100, "slippage_beli": 0.003})
    b.s["buy_on"] = True
    b.perintah(1, "⏹ STOP", None)
    assert b.s["stop"] and not b.s["buy_on"]
    b.putaran()
    assert not b.s["posisi"]


def test_bot_mode_live_ditolak(tmp_path):
    with pytest.raises(SystemExit):
        _bot(tmp_path, "live")


def test_bot_buy_on_kertas_toggle(tmp_path):
    b, jam = _bot(tmp_path, "kertas")
    b.perintah(1, "🅰 BUY ON/OFF", None)
    assert b.s["buy_on"]
    b.perintah(1, "🅰 BUY ON/OFF", None)
    assert not b.s["buy_on"]


def test_bot_batas_kertas(tmp_path):
    b, jam = _bot(tmp_path, "kertas")
    assert b.boleh(600) == "kas kertas kurang"
    b.s["n_trade"], b.s["hari"] = 3, "2026-09-21"
    jam.t = datetime(2026, 9, 21, 12, tzinfo=timezone.utc).timestamp()
    assert "trade/hari" in b.boleh(10)


def test_bot_kertas_tebus_manual(tmp_path):
    r = dict(RBELI, harga_beli=40.0, tebus_manual=True, nilai_tebus=79.2)
    b, jam = _bot(tmp_path, "kertas", r=r)
    b.s["buy_on"] = True
    b.putaran()
    assert not b.s["posisi"]                        # langsung disimulasikan ditebus, tidak menunggu jual DEX
    assert b.s["kas_kertas"] == pytest.approx(400 + 100 / 40.0 * 79.2)
    assert any("TEBUS" in x for x in b.tg.pesan)


def test_bot_mode_kertas_tidak_terbawa_pantau(tmp_path):
    s = Store(tmp_path / "pantau")
    s.s["mode"] = "kertas"
    s.s["posisi"] = {"x": {"usd": 10}}
    s.simpan()
    cfg = {"mode": "pantau", "jaringan": {}, "pasangan": []}
    with pytest.raises(RuntimeError):
        Bot(cfg, s, {}, [], TgPalsu())
