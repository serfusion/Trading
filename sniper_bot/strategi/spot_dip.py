"""💎 Spot dip: koin besar yang peluang naik +3% dalam 10 hari tinggi (model gradient boosting walk-forward).

PORT dari cloud/api/_spot.py (versi terpasang di main) agar bot Telegram berdiri sendiri. Fungsi fitur/model DISALIN
persis (tes paritas tests/test_sniper_bot.py membandingkan dengan cloud/api/_spot.py). Model: spot_model.json (salinan).
Teruji (docs/SPOT_PELUANG.md, SPOT_PINDAI.md, SPOT_JATUH.md): 20 koin, sejak Okt 2021 naik +3% di 91-92% sinyal,
rata +1,2..1,4%/sinyal, rugi saat gagal rata -13..-14% (terburuk -58%). Tanpa SL (SL memperburuk hasil, sudah diuji).
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path

from ..pasar import Bar

MODEL = json.loads((Path(__file__).resolve().parent / "spot_model.json").read_text(encoding="utf-8"))
HARI = 86400.0


def _tgl(t: float):
    return datetime.fromtimestamp(t, timezone.utc).date()


def _mean(x):
    return sum(x) / len(x)


def _std(x):                       # simpangan baku sampel (ddof=1), seperti pandas
    m = _mean(x)
    return math.sqrt(sum((v - m) ** 2 for v in x) / (len(x) - 1))


def _rsi(closes: list[float], n: int) -> float | None:
    a = 1 / n
    up = dn = None
    for i in range(1, len(closes)):
        d = closes[i] - closes[i - 1]
        u, w = max(d, 0.0), max(-d, 0.0)
        up = u if up is None else (1 - a) * up + a * u
        dn = w if dn is None else (1 - a) * dn + a * w
    if not dn:
        return None
    return 1 - 1 / (1 + up / dn)          # RSI / 100


def features(bars: list[Bar], btc: list[Bar], model: dict = MODEL) -> list[float] | None:
    """Fitur di close candle harian TERAKHIR yang sudah tutup. bars & btc = candle tutup, urut waktu."""
    if len(bars) < 201 or len(btc) < 201:
        return None
    c = [b.c for b in bars]
    hi = [b.h for b in bars]
    red = 0
    for b in reversed(bars):
        if b.c < b.o:
            red += 1
        else:
            break
    r14, r2 = _rsi(c, 14), _rsi(c, 2)
    if r14 is None or r2 is None:
        return None
    lr = [math.log(c[i] / c[i - 1]) for i in range(len(c) - 14, len(c))]
    s20 = _std(c[-20:])
    bmap = {_tgl(b.t): b.c for b in btc}
    bdates = sorted(bmap)
    last = _tgl(bars[-1].t)
    bd = [d for d in bdates if d <= last]
    if len(bd) < 201:
        return None
    bc = [bmap[d] for d in bd]
    f = {
        "dd20": c[-1] / max(hi[-20:]) - 1,
        "dd60": c[-1] / max(hi[-60:]) - 1,
        "rsi14": r14,
        "rsi2": r2,
        "red": float(min(red, 6)),
        "r1": c[-1] / c[-2] - 1,
        "r3": c[-1] / c[-4] - 1,
        "r7": c[-1] / c[-8] - 1,
        "r30": c[-1] / c[-31] - 1,
        "z20": (c[-1] - _mean(c[-20:])) / s20 if s20 else 0.0,
        "d50": c[-1] / _mean(c[-50:]) - 1,
        "d200": c[-1] / _mean(c[-200:]) - 1,
        "vol14": _std(lr),
        "btc_up": 1.0 if bc[-1] > _mean(bc[-200:]) else 0.0,
        "btc_r7": bc[-1] / bc[-8] - 1,
    }
    return [f[k] for k in model.get("fitur", list(f))]


def vol_rank(bars: list[Bar], window: int = 365) -> float | None:
    """Peringkat volatilitas 14 hari sekarang dibanding 365 hari terakhir koin itu (0..1, seperti pandas rank pct)."""
    c = [b.c for b in bars]
    if len(c) < 15 + 120:
        return None
    lr = [math.log(c[i] / c[i - 1]) for i in range(1, len(c))]
    vols = [_std(lr[i - 14:i]) for i in range(14, len(lr) + 1)][-window:]
    if len(vols) < 120:
        return None
    cur = vols[-1]
    less = sum(1 for v in vols if v < cur)
    eq = sum(1 for v in vols if v == cur)
    return (less + (eq + 1) / 2) / len(vols)


def red_rule(x: list[float], model: dict = MODEL) -> bool:
    """Aturan cadangan yang ikut teruji: 3 hari merah beruntun, turun ≥ 10% dalam 3 hari, harga di atas SMA200."""
    if not model.get("aturan_merah"):
        return False
    f = dict(zip(model.get("fitur", []), x))
    return f.get("red", 0) >= 3 and f.get("r3", 0) <= -0.10 and f.get("d200", -1) > 0


def prob(x: list[float], model: dict = MODEL) -> float:
    """Peluang naik dari pohon gradient boosting (sama dengan research/spot_peluang.gbm_prob)."""
    s = model["base"]
    for nodes in model["trees"]:
        i = 0
        while not nodes[i][0]:
            _, f, thr, miss_left, left, right, _ = nodes[i]
            v = x[f]
            go_left = miss_left if v != v else v <= thr
            i = left if go_left else right
        s += nodes[i][6]
    return 1 / (1 + math.exp(-s))


def kualitas(bars: list[Bar]) -> str | None:
    """Filter kualitas (docs/SPOT_JATUH.md): lewati koin < 1 tahun, sudah ambruk >= 80% dari puncak 1 tahun,
    atau volume quote hari terakhir >= 3x rata-rata 30 hari (panik)."""
    if len(bars) < 365:
        return "umur < 1 tahun"
    puncak = max(b.h for b in bars[-365:])
    if bars[-1].c <= puncak * 0.2:
        return "ambruk ≥ 80% dari puncak 1 tahun"
    q30 = [b.q for b in bars[-31:-1]]
    if q30 and bars[-1].q >= 3 * _mean(q30) > 0:
        return "volume panik ≥ 3× rata-rata 30 hari"
    return None


def sinyal(bars: list[Bar], btc: list[Bar], filter_btc: bool = True, filter_kualitas: bool = False,
           model: dict = MODEL) -> tuple[bool, float | None, str]:
    """(beli?, peluang, alasan) untuk candle harian TUTUP terakhir."""
    x = features(bars, btc, model)
    if x is None:
        return False, None, "data < 201 hari"
    vr = vol_rank(bars)
    if vr is not None and vr > model.get("skip_vol", 1.1):
        return False, None, "volatilitas > P90"
    if filter_btc:
        bc = [b.c for b in btc]
        if len(bc) >= 200 and bc[-1] <= _mean(bc[-200:]):
            return False, None, "BTC di bawah SMA200"
    if filter_kualitas:
        k = kualitas(bars)
        if k:
            return False, None, k
    p = prob(x, model)
    rule = red_rule(x, model)
    if p >= model["ambang"] or rule:
        alasan = "model + 3 merah" if p >= model["ambang"] and rule else "model" if p >= model["ambang"] else "3 merah"
        return True, p, alasan
    return False, p, "peluang < ambang"


# ====================================================================== bagian live (dipakai mesin)
class SpotDipMesin:
    nama = "spot_dip"
    label = "💎 Spot dip"

    def __init__(self, mesin):
        self.m = mesin
        self.cfg = mesin.cfg["spot_dip"]

    def koin(self) -> list[str]:
        k = self.cfg.get("koin")
        if k:
            return [x.upper() for x in k]
        return list(MODEL["coins"])

    def tick_harga(self) -> None:
        return None

    def tick_jadwal(self) -> None:
        now = self.m.now()
        hari_ini = math.floor(now / HARI) * HARI
        sp = self.m.s["spot"]
        # pindai sekali sehari, >= 5 menit setelah candle harian UTC tutup (07:05 WIB) dan masih di jendela teruji
        # (entry riset = awal hari; makin siang makin jauh dari yang diuji). /pindai memaksa (dengan catatan).
        paksa = self.m.s.get("spot_paksa", False)
        jendela = float(self.cfg.get("jendela_jam", 6)) * 3600
        if not paksa and (now - hari_ini < 300 or now - hari_ini > jendela or sp.get("pindai") == hari_ini):
            return
        if paksa:
            self.m.s["spot_paksa"] = False
            if now - hari_ini > jendela:
                self.m.kabar(f"🔎 💎 dipindai di luar jendela teruji (00:05–{self.cfg.get('jendela_jam', 6):g}:00 UTC): "
                             "entry lebih siang dari riset.")
        self.m.jadwal["spot"] = now
        self.pindai(now, hari_ini)
        sp["pindai"] = hari_ini

    def _bars(self, coin: str, now: float) -> list[Bar]:
        b = self.m.pasar.kline(f"{coin}USDT", "1d", limit=420)
        return [x for x in b if x.t + HARI <= now]              # hanya candle yang sudah tutup

    def pindai(self, now: float, hari_ini: float) -> None:
        btc = self._bars("BTC", now)
        tp, hari = float(MODEL["tp"]), float(MODEL["hari"])
        terbuka = {p["base"] for p in self.m.s["posisi"].values() if p["strategi"] == self.nama}
        maks = int(self.cfg["maks_posisi"])
        ditemukan = []
        for coin in self.koin():
            if coin in terbuka:
                continue
            terakhir = self.m.s["spot"]["terakhir"].get(coin)
            if terakhir and now - terakhir < float(self.cfg["jeda_ulang_jam"]) * 3600:
                continue
            try:
                bars = btc if coin == "BTC" else self._bars(coin, now)
            except Exception as e:  # noqa: BLE001
                self.m.galat(f"spot {coin}", e)
                continue
            beli, p, alasan = sinyal(bars, btc, bool(self.cfg["filter_btc_sma200"]), bool(self.cfg["filter_kualitas"]))
            if not beli:
                continue
            if sum(1 for x in self.m.s["posisi"].values() if x["strategi"] == self.nama) >= maks:
                break
            sym = f"{coin}USDT"
            harga = self.m.harga.get(sym) or bars[-1].c
            usd_ = self.m.ukuran(float(self.cfg["persen_modal"]))
            sisa_hari = (hari_ini + hari * HARI - now) / HARI
            pos = self.m.buka(self.nama, sym, coin, harga, usd_, tp, None, sisa_hari,
                              info={"peluang": p, "alasan": alasan}, label=f"{self.label} peluang {p * 100:.0f}% ({alasan})")
            if pos:
                self.m.s["spot"]["terakhir"][coin] = now
                ditemukan.append(coin)
        self.m.s["spot"]["hasil"] = {"t": now, "beli": ditemukan}

    def status_teks(self) -> str:
        sp = self.m.s["spot"]
        from ..mesin import jam
        t = (sp.get("hasil") or {}).get("t")
        return f"{self.label}: {len(self.koin())} koin, pindai terakhir {jam(t) if t else '-'}"
