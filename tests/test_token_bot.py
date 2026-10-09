"""Tes luring token_bot (tanpa jaringan): poolId, harga sqrtPrice, keputusan beli/jual, pengaman."""
from datetime import datetime, timezone

import pytest

pytest.importorskip("eth_abi")

from eth_abi import decode

from token_bot import acuan, strategi
from token_bot.dex import Pool, sqrtp_harga
from token_bot.eksekusi import S_UR_EXEC

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


def test_ur_selector():
    assert S_UR_EXEC.hex() == "3593564c"


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


def test_kalkulasi_v4_swap_encode():
    from eth_abi import encode

    from token_bot.eksekusi import A_SETTLE_ALL, A_SWAP_EXACT_IN_SINGLE, A_TAKE_ALL
    p = Pool(4, "0x" + "11" * 32, USDG, CRCL, 3000, 60, "0x" + "00" * 20, 6, 18)
    prm = encode(["((address,address,uint24,int24,address),bool,uint128,uint128,bytes)"],
                 [(p.key, True, 10 ** 6, 1, b"")])
    (k,) = decode(["((address,address,uint24,int24,address),bool,uint128,uint128,bytes)"], prm)
    assert k[0][2] == 3000 and k[2] == 10 ** 6
    assert bytes([A_SWAP_EXACT_IN_SINGLE, A_SETTLE_ALL, A_TAKE_ALL]) == b"\x06\x0c\x0f"


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


def _bot(tmp_path, mode="kertas", r=None, monkeypatch=None):
    cfg = {"mode": mode, "modal_kertas_usd": 500, "interval": 5, "live": {"maks_usd_per_trade": 25,
           "maks_total_usd": 100, "maks_trade_per_hari": 5}, "jaringan": {"x": {"v4_quoter": "q", "v3_quoter": "q"}},
           "pasangan": [{"jaringan": "x"}]}
    p = _pas()
    store = Store(tmp_path / mode)
    jam = Jam(1_790_000_000.0)
    b = Bot(cfg, store, {"x": None}, [("x", p)], TgPalsu(), dompet=None, sekarang=jam)
    if r is not None:
        b._eval = lambda net, pas: dict(r)
    return b, jam


def test_bot_pantau_hanya_kabar(tmp_path):
    b, jam = _bot(tmp_path, "pantau", r={"aksi": "BELI", "alasan": "murah", "harga_beli": 78.0, "wajar": 80.0,
                                         "untung_beli": 0.025, "ukuran_usd": 100, "slippage_beli": 0.003})
    b.putaran()
    assert not b.s["posisi"] and any("PELUANG BELI" in x for x in b.tg.pesan)


def test_bot_kertas_beli_lalu_jual(tmp_path):
    rbeli = {"aksi": "BELI", "alasan": "murah", "harga_beli": 78.0, "wajar": 80.0, "untung_beli": 0.025,
             "ukuran_usd": 100, "slippage_beli": 0.003}
    b, jam = _bot(tmp_path, "kertas", r=rbeli)
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


def test_bot_buy_on_live_minta_konfirmasi(tmp_path):
    b, jam = _bot(tmp_path, "pantau")
    b.mode = "live"
    b.dompet = type("D", (), {"addr": "0xabc"})()
    b.perintah(1, "🅰 BUY ON/OFF", None)
    assert not b.s["buy_on"] and b.tg.tombol          # minta konfirmasi, belum ON
    tok = b.tg.tombol[-1][0][0]["callback_data"]
    b.perintah(1, tok, cbid="cb")
    assert b.s["buy_on"]


def test_bot_batas_total_kertas(tmp_path):
    b, jam = _bot(tmp_path, "live")
    # mode live tanpa dompet: cek boleh() batas total
    b.s["posisi"] = {"a": {"usd": 90}}
    assert b.boleh(25) is not None and "total" in b.boleh(25)
    assert b.boleh(10) is None


def test_bot_pending_memblokir(tmp_path):
    b, jam = _bot(tmp_path, "kertas")
    b.s["pending"] = {"nama": "x", "t": jam.t}
    assert b.boleh(10) is not None
    b.perintah(1, "/beres", None)
    assert not b.s["pending"]


def test_bot_mode_kertas_tidak_terbawa_live(tmp_path):
    s = Store(tmp_path / "live")
    s.s["mode"] = "kertas"
    s.s["posisi"] = {"x": {"usd": 10}}
    s.simpan()
    cfg = {"mode": "live", "live": {}, "jaringan": {}, "pasangan": []}
    with pytest.raises(RuntimeError):
        Bot(cfg, s, {}, [], TgPalsu())
