"""💎 Spot dip: koin besar yang peluang naik +3% dalam 10 hari tinggi (model gradient boosting walk-forward).

PORT dari cloud/api/_spot.py (versi terpasang di main) agar bot Telegram berdiri sendiri. Fungsi fitur/model DISALIN
persis (tes paritas tests/test_sniper_bot.py & tests/test_spot_paritas.py). Model: spot_model.json (salinan identik).

Angka teruji JUJUR (docs/eksternal/spek_spot_dip_bot.txt, research/spot_paritas.py, model walk-forward, biaya 0,30%):
varian D = semesta 20 pair volume terbesar SAAT ITU + lewati vol > P90 + BTC > SMA200, 10 slot x 10%:
  BARU (Okt 2021-Sep 2026): TP +3% tercapai 90,6%, +0,73%/sinyal, portofolio +7,7%/th DD -14%
  LAMA (Jan 2020-Sep 2021): 93,7%, +1,14%/sinyal, portofolio +23,4%/th DD -21%
  (dikoreksi 9 Okt 2026 di research/spot_apk.py: 10 hari terakhir sebelum delisting ikut dinilai)
  Gagal: rugi rata -18%, terburuk -55%. Acak (semesta sama) BARU -5,4%/th. Tanpa SL (SL memperburuk, sudah diuji).
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
    """Filter kualitas = research/spot_paritas.kualitas_riset: lewati koin < 1 tahun (sejak bar pertama), sudah ambruk
    >= 80% dari puncak 365 hari, atau volume quote hari t >= 3x rata-rata 30 hari TERMASUK hari t (panik)."""
    if (bars[-1].t - bars[0].t) / HARI < 365:
        return "umur < 1 tahun"
    if len(bars) >= 200 and bars[-1].c / max(b.h for b in bars[-365:]) - 1 <= -0.80:
        return "ambruk ≥ 80% dari puncak 1 tahun"
    q30 = [b.q for b in bars[-30:]]
    if len(q30) == 30 and _mean(q30) > 0 and bars[-1].q / _mean(q30) >= 3:
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


# ====================================================================== semesta
# bukan koin bergerak bebas (= research/spot_paritas.SKIP)
SKIP = {"USDT", "USDC", "FDUSD", "TUSD", "USDP", "DAI", "BUSD", "USDE", "PYUSD", "RLUSD", "USD1", "BFUSD", "XUSD",
        "USDS", "FRAX", "LUSD", "GUSD", "UST", "USTC", "USDD", "SUSD", "USDJ", "EURC", "EUR", "EURI", "AEUR", "GBP",
        "TRY", "BRL", "AUD", "JPY", "ARS", "MXN", "ZAR", "PLN", "RON", "UAH", "IDRT", "BIDR", "BVND", "PAXG", "XAUT",
        "WBTC", "WBETH", "BETH", "STETH", "WSTETH", "BNSOL", "CBETH", "RETH", "WETH", "PAX", "BKRW", "RUB", "NGN",
        "USDSOLD", "U", "KGST", "BNCB"}
URUTAN = {c: i for i, c in enumerate(MODEL["coins"])}


def bukan_koin(base: str) -> bool:
    return base in SKIP or (len(base) > 4 and base.endswith(("UP", "DOWN", "BULL", "BEAR")))


def qv7(bars: list[Bar]) -> float | None:
    """Rata-rata volume quote 7 hari SEBELUM candle tutup terakhir (= riset: qv.shift(1).rolling(7).mean())."""
    if len(bars) < 8:
        return None
    return _mean([b.q for b in bars[-8:-1]])


def pilih_volume20(data: dict[str, list[Bar]], btc: list[Bar], n: int = 20, model: dict = MODEL) -> list[str]:
    """Varian D: dari koin yang fiturnya bisa dihitung (>= 201 hari), ambil n dengan qv7 terbesar; urutan pindai =
    urutan koin model lalu abjad (sama dengan portofolio riset)."""
    nilai = []
    for coin, bars in data.items():
        if bukan_koin(coin) or features(bars, btc, model) is None:
            continue
        q = qv7(bars)
        if q is not None:
            nilai.append((q, coin))
    top = [c for _q, c in sorted(nilai, key=lambda x: (-x[0], x[1]))[:n]]
    return sorted(top, key=lambda c: (URUTAN.get(c, 999), c))


# ====================================================================== bagian live (dipakai mesin)
class SpotDipMesin:
    nama = "spot_dip"
    label = "💎 Spot dip"

    def __init__(self, mesin):
        self.m = mesin
        self.cfg = mesin.cfg["spot_dip"]

    @property
    def sp(self) -> dict:
        sp = self.m.s["spot"]
        sp.setdefault("hari_beli", {})
        return sp

    def tick_harga(self) -> None:
        return None

    def _bars(self, coin: str, now: float) -> list[Bar]:
        b = self.m.pasar.kline(f"{coin}USDT", "1d", limit=420)
        return [x for x in b if x.t + HARI <= now]              # hanya candle yang sudah tutup

    def semesta(self, now: float, btc: list[Bar]) -> tuple[list[str], dict[str, list[Bar]]]:
        koin = [x.upper() for x in self.cfg.get("koin") or []]
        if koin:
            return koin, {}
        if self.cfg.get("semesta", "volume20") == "tetap20":
            return list(MODEL["coins"]), {}
        t24 = self.m.pasar.ticker24()
        cand = sorted(((v.get("q") or 0.0, k[:-4]) for k, v in t24.items()
                       if k.endswith("USDT") and not bukan_koin(k[:-4])), reverse=True)
        data: dict[str, list[Bar]] = {"BTC": btc}
        for _q, coin in cand[: int(self.cfg.get("pra_pilih", 60))]:
            if coin in data:
                continue
            try:
                data[coin] = self._bars(coin, now)
            except Exception as e:  # noqa: BLE001
                self.m.galat(f"spot {coin}", e)
        return pilih_volume20(data, btc), data

    def tick_jadwal(self) -> None:
        now = self.m.now()
        hari_ini = math.floor(now / HARI) * HARI
        sp = self.sp
        jendela = float(self.cfg.get("jendela_jam", 1)) * 3600
        di_jendela = 300 <= now - hari_ini <= jendela
        if self.m.s.pop("spot_paksa", False) and not (di_jendela and sp.get("pindai") != hari_ini):
            self.pindai(now, hari_ini, beli=False)              # /pindai di luar jendela / sudah dipindai: lihat saja
            return
        if now - hari_ini > jendela and sp.get("pindai") != hari_ini and sp.get("terlewat") != hari_ini:
            sp["terlewat"] = hari_ini
            self.m.kabar(f"⚠️ Pindai 💎 hari ini terlewat (bot tidak aktif/gagal data 07:05–"
                         f"{7 + float(self.cfg.get('jendela_jam', 1)):02.0f}:00 WIB). Tidak membeli di luar jendela teruji; "
                         f"/pindai untuk melihat sinyal saja.")
            return
        if not di_jendela or sp.get("pindai") == hari_ini or now - sp.get("coba_t", 0) < 300:
            return
        sp["coba_t"] = now
        if self.pindai(now, hari_ini, beli=True):
            sp["pindai"] = hari_ini

    def _tutup_hari_ini(self, coin: str, hari_ini: float) -> bool:
        return any(t.get("strategi") == self.nama and t.get("base") == coin and t.get("t_tutup", 0) >= hari_ini
                   for t in self.m.s["riwayat"][:200])

    def pindai(self, now: float, hari_ini: float, beli: bool = True) -> bool:
        """Pindai candle harian tutup. True bila selesai (hari ditandai); False = coba lagi 5 menit."""
        from ..mesin import pct, usd
        from ..telegram import esc
        try:
            btc = self._bars("BTC", now)
            koin, data = self.semesta(now, btc)
        except Exception as e:  # noqa: BLE001
            self.m.galat("spot data", e)
            return False
        if beli and self.m.kas() is None:
            return False                                        # saldo gagal dibaca (galat sudah dikabarkan)
        tp, hari = float(MODEL["tp"]), float(MODEL["hari"])
        maks = int(self.cfg["maks_posisi"])
        hasil = {"t": now, "beli": [], "sinyal": [], "lewat": [], "koin": len(koin)}
        for coin in koin:
            try:
                bars = data.get(coin) or (btc if coin == "BTC" else self._bars(coin, now))
            except Exception as e:  # noqa: BLE001
                self.m.galat(f"spot {coin}", e)
                continue
            ok, p, alasan = sinyal(bars, btc, bool(self.cfg["filter_btc_sma200"]), bool(self.cfg["filter_kualitas"]))
            if not ok:
                if alasan == "BTC di bawah SMA200":
                    hasil["btc_bawah"] = True
                continue
            hasil["sinyal"].append(f"{coin}{' ⚡' if bars[-1].c / max(b.h for b in bars[-20:]) > 0.85 else ''} "
                                   f"skor {p * 100:.0f} ({alasan})")
            if not beli:
                continue
            terbuka = [x for x in self.m.s["posisi"].values() if x["strategi"] == self.nama]
            if any(x["base"] == coin for x in terbuka):
                continue
            if self.sp["hari_beli"].get(coin) == hari_ini or self._tutup_hari_ini(coin, hari_ini):
                continue
            if len(terbuka) >= maks:
                hasil["lewat"].append(f"{coin}: {maks} slot penuh")
                continue
            u, target = self.m.ukuran(float(self.cfg["persen_modal"]))
            if u < 5 or u < float(self.cfg.get("min_persen_target", 0.5)) * target:
                hasil["lewat"].append(f"{coin}: ukuran {usd(u)} < 50% target {usd(target)}")
                continue
            sym = f"{coin}USDT"
            harga = self.m.harga.get(sym) or bars[-1].c
            sisa_hari = (hari_ini + hari * HARI - now) / HARI
            dd20 = bars[-1].c / max(b.h for b in bars[-20:]) - 1
            kilat = dd20 > -0.15             # label ⚡ Dip ringan (research/spot_apk.py; label saja, sama dengan APK 4.24)
            pos = self.m.buka(self.nama, sym, coin, harga, u, tp, None, sisa_hari,
                              info={"peluang": p, "alasan": alasan, "dd20": dd20, "tier": "kilat" if kilat else "biasa"},
                              label=f"{self.label}{' ⚡ Dip ringan' if kilat else ''} skor {p * 100:.0f} ({alasan})")
            if pos or self.m.gagal_terakhir == "tidak pasti":
                self.sp["hari_beli"][coin] = hari_ini              # satu sinyal = satu percobaan
            if pos:
                hasil["beli"].append(coin)
            else:
                hasil["lewat"].append(f"{coin}: {self.m.gagal_terakhir}")
        self.sp["hasil"] = hasil
        teks = (f"💎 <b>Pindai {'(lihat saja, tanpa beli)' if not beli else 'harian'}</b> {len(koin)} koin "
                f"({esc(self.cfg.get('semesta', 'volume20')) if not self.cfg.get('koin') else 'daftar sendiri'})\n")
        if hasil.get("btc_bawah"):
            teks += "BTC di bawah SMA200 → filter menahan semua sinyal (teruji menurunkan DD).\n"
        teks += ("Sinyal: " + ", ".join(esc(x) for x in hasil["sinyal"]) if hasil["sinyal"] else "Tidak ada sinyal.")
        if hasil["beli"]:
            teks += f"\nDibeli: {', '.join(hasil['beli'])} (TP {pct(tp)}, maks {hari:g} hari, tanpa SL)"
        if hasil["lewat"]:
            teks += "\nDilewati: " + "; ".join(esc(x) for x in hasil["lewat"][:10])
        if hasil["sinyal"] or not beli:
            self.m.kabar(teks)
        return True

    def status_teks(self) -> str:
        from ..mesin import jam
        h = self.sp.get("hasil") or {}
        sem = "daftar sendiri" if self.cfg.get("koin") else self.cfg.get("semesta", "volume20")
        return (f"{self.label}: semesta {sem}, pindai terakhir {jam(h['t']) if h.get('t') else '-'}"
                f" ({len(h.get('sinyal', []))} sinyal, {len(h.get('beli', []))} dibeli)")
