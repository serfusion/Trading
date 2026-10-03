"""Verifikasi: kode cloud ASLI (cloud/api/_core.tick) diputar ulang candle demi candle di data H1 historis.

python -m research.verifikasi_cloud XAU|BTC [--mentah] [--td]

Permintaan pengguna (3 Okt 2026): "pastikan lagi, cek, verifikasi, uji secara menyeluruh". Riset (sl_tangga /
kategori_badge) adalah kode terpisah dari cloud. Skrip ini menjalankan fungsi cloud yang sama persis dengan Vercel
(evaluate, kategori, filter, manage SL/TP1/SL+, TUTUP) pada data riset, satu tick per candle (2 menit setelah candle
berikutnya dibuka; harga entry/TUTUP = open candle berikutnya, seperti cron cloud).
Konfigurasi LIVE (bawaan): XAU filter H4 EMA50 + lapisan; BTC filter funding (proksi premium Binance, terlambat
seperti cloud) + lewati September + lapisan + tanpa kategori konf (sejak 3 Okt 2026). --mentah: tanpa filter H4/funding/September/lapisan (sebanding dengan
riset "hanya 💰 dikirim"). Tanda 📰/⚡/perang hanya label -> tidak dipakai.
Catatan cloud: R virtual TANPA spread, SL+ = entry ± 0,10 (riset: entry + 0,1R), SL tanpa celah harga, ATR(20)
rata-rata sederhana (riset: ATR14 Wilder), dan sinyal dilewati bila ATR20 < 0,4 x ATR120.
--td: data Twelve Data (feed yang dipakai cloud live, data/research/eksternal/twelvedata_h1, 2018–2026) sebagai
pengganti data riset -> cek apakah sumber data mengubah hasil. --semua: semua kategori dikirim (filter live tetap,
tanpa lapisan) -> angka kategori yang TIDAK dikirim (kartu 🏆).
Hasil: data/research/eksternal/verifikasi/cloud_<aset>[_mentah][_td].csv (satu baris per sinyal yang sudah tutup).
"""
from __future__ import annotations

import bisect
import functools
import json
import sys
from datetime import timedelta
from pathlib import Path

import pandas as pd

from .eksternal import EXT, asset

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "cloud" / "api"))
import _core  # noqa: E402
import _funding  # noqa: E402

OUT = EXT / "verifikasi"
WARM = 3000


class Prices:
    """candles(n): candle H1 yang sudah tutup + candle berjalan (baru dibuka: o=h=l=c=open)."""

    def __init__(self, bars: list):
        self.bars, self.i = bars, 0

    def candles(self, n: int) -> list:
        i = self.i
        out = self.bars[max(0, i - n + 2):i + 1]
        if i + 1 < len(self.bars):
            nb = self.bars[i + 1]
            out = out + [_core.Bar(nb.t, nb.o, nb.o, nb.o, nb.o)]
        return out


class Store:
    def __init__(self):
        self.state = {}

    def get_state(self, *a):
        return dict(self.state)

    def save_state(self, d, *a):
        self.state = dict(d)

    def log(self, *a):
        pass

    def get_control(self):
        return {}


class Pub:
    def __init__(self):
        self.sig, self.close = {}, []

    def publish(self, ev, *a, **k):
        if ev.get("type") == "signal":
            self.sig[ev["id"]] = ev
        elif ev.get("type") == "close" and not ev.get("void"):
            self.close.append(ev)


def funding_series() -> tuple[list, list]:
    """Proksi funding 8 jam (sama dengan cloud) + waktu tersedia: file harian hari D baru ada D+1 ± 06:00 UTC."""
    from .eksternal_btc import premium
    pr = premium()
    hours = {int(t.timestamp()): float(p) for t, p in pr.premium.items()}
    f = sorted(_funding.funding_8h(hours).items())
    avail = []
    for t, _ in f:
        day = (t - 1) // 86400 * 86400                      # hari data jam terakhir periode settlement
        avail.append(day + 86400 + 6 * 3600)
    return f, avail


def replay(name: str, mentah: bool = False, td: bool = False, semua: bool = False, extra: dict | None = None,
           data: pd.DataFrame | None = None) -> pd.DataFrame:
    """extra: kunci cfg tambahan (mis. sets, layer, skip_fn) — dipakai research/tambahan_cloud.py; data: candle H1 lain."""
    key = {"XAU": "XAUUSD", "BTC": "BTCUSD"}.get(name, name)
    if data is not None:
        df = data[data.high > data.low]
    elif td:
        df = pd.read_parquet(EXT / "twelvedata_h1" / f"{key}.parquet")
        df = df[df.high > df.low]
    else:
        df = asset(key).b.df
    bars = [_core.Bar(t.to_pydatetime(), float(r.open), float(r.high), float(r.low), float(r.close))
            for t, r in zip(df.index, df.itertuples())]
    _core.market_open = functools.lru_cache(maxsize=None)(_core.market_open)       # hanya mempercepat
    _core.trend_status = lambda *a, **k: {}                                         # kartu status: bukan sinyal
    if name == "XAU":
        cfg = {**_core.CFG, "h4_filter": not mentah}
        if not mentah:                       # seperti tick.py sejak 3 Okt 2026 (XAU_EXTRA_SETS)
            cfg["sets"] = list(_core.CFG["sets"]) + [(100, 40), (120, 50)]
    else:
        cfg = dict(_core.BTC_CFG)
    lay = json.loads((ROOT / "cloud" / "api" / "sinyal_lapis.json").read_text(encoding="utf-8")).get(name)
    if lay and not mentah and not semua:  # XAU sejak 3 Okt: kapan saja, maks 6 (sinyal_lapis.json)
        cfg["layer"] = lay
    if semua:                                # semua kategori dikirim (pembanding kategori yang tidak dikirim)
        cfg["profit_only"] = False
    if name == "BTC" and not mentah and not semua:
        cfg["skip_cats"] = ("konf",)        # seperti tick.py sejak 3 Okt 2026 (BTC konf dimatikan, BTC_SKIP_KONF)
        f, avail = funding_series()

        def skip(direction, now):
            k = bisect.bisect_right(avail, now.timestamp())
            cache = {"f": f[max(0, k - _funding.KEEP):k]}
            return _funding.skip_reason(direction, now, cache, True, True, _core.new_york)
        cfg["skip_fn"] = skip
    cfg.update(extra or {})
    prices, store, pub = Prices(bars), Store(), Pub()
    for i in range(WARM, len(bars) - 1):
        prices.i = i
        now = bars[i + 1].t + timedelta(minutes=2)
        _core.tick(now, prices, store, pub, cfg, symbol=f"{name}/USD")
        if i % 10000 == 0:
            print(f"  {name} {bars[i].t:%Y-%m-%d} sinyal {len(pub.sig)} tutup {len(pub.close)}", flush=True)
    rows = []
    for ev in pub.close:
        s = pub.sig.get(ev["id"], {})
        rows.append({"id": ev["id"], "set": ev["set"], "dir": ev["dir"], "cat": s.get("cat", "").split(" ", 1)[-1],
                     "t_signal": s.get("time"), "t_close": ev["time"], "entry": ev["entry"], "exit": ev["price"],
                     "risk": ev["risk_points"], "r": ev["r"], "tp1": ev["tp1_hit"], "lapis": bool(ev.get("lapis")),
                     "reason": ev["reason"], "tier": s.get("tier", ""),
                     "r07": (ev.get("r_by") or {}).get("1_07", ev["r"])})     # skema SL+ 0,7R (aplikasi: BTC & ⚡)
    out = pd.DataFrame(rows)
    out["t_signal"] = pd.to_datetime(out.t_signal, utc=True)
    out["t_close"] = pd.to_datetime(out.t_close, utc=True)
    return out.sort_values("t_signal").reset_index(drop=True)


def main() -> None:
    name = sys.argv[1] if len(sys.argv) > 1 else "XAU"
    mentah, td, semua = "--mentah" in sys.argv, "--td" in sys.argv, "--semua" in sys.argv
    out = replay(name, mentah, td, semua)
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"cloud_{name}{'_mentah' if mentah else ''}{'_td' if td else ''}{'_semua' if semua else ''}.csv"
    out.to_csv(path, index=False)
    print(f"{len(out)} sinyal tutup -> {path}")
    for lap, g in out.groupby("lapis"):
        print(f"  {'lapisan' if lap else 'dasar'}: n {len(g)} WR {(g.r > 0).mean() * 100:.1f}% "
              f"R/sin {g.r.mean():+.3f} total {g.r.sum():+.1f}")


if __name__ == "__main__":
    main()
