"""⏱️ Rencana pengguna: entry 1 DETIK SEBELUM rilis, tutup 1–5 (detik / menit) setelah rilis — XAU, BTC, ETH.

python -m research.pra_aset unduh        # kline 1 detik ETHUSDT Binance di sekitar tiap rilis (sekali)
python -m research.pra_aset              # → docs/eksternal/hasil_pra_aset.txt + cloud/api/pra_aset.json

Permintaan pengguna 10 Okt 2026: "rencana saya entry 1 detik sebelum news, tutup 1–5 pasca release; berikan persentase
terbaik di bawah sinyal XAU, BTC, ETH". Aturan ditetapkan sebelum melihat hasil:
  • Rilis: semua berita USD bintang 3 (research/news_detik.events), dikelompokkan (NFP, CPI, PPI, …).
  • Arah: (1) PETUNJUK TERUJI per berita (research/berita_gabung.py → arah emas; kripto ikut arah yang sama: data
    lebih lemah dari dugaan = dolar & yield turun = emas & kripto naik) — hanya rilis yang petunjuknya memberi arah;
    (2) SELALU BUY dan (3) SELALU SELL sebagai pembanding (tanpa tebakan).
  • Entry t0−1 dtk: BUY di ASK / SELL di BID; REALISTIS = terisi 0,5 dtk kemudian + slippage (XAU $0,30, BTC/ETH 0,02%)
    saat masuk & keluar. Keluar tepat t0 + 1/2/3/5 dtk atau t0 + 1/2/3/4/5 mnt di BID/ASK.
  • Feed: XAU Dukascopy & Exness (tick asli), BTC Binance 1 dtk (spread 0,03%) & Exness (tick asli), ETH Binance 1 dtk
    (spread Exness ETH diasumsikan 0,05%). Hasil XAU dalam $ per 0,01 lot; BTC/ETH dalam % harga.
  • "Terbaik" per berita & aset = keluar dengan rata-rata REALISTIS tertinggi di periode LAMA (< Okt 2021) — lalu
    dilaporkan apa adanya di BARU (≥ Okt 2021), supaya tidak memilih yang kebetulan bagus di data yang dinilai.
  • Status: "UNTUNG teruji" hanya bila n ≥ 30, rata LAMA & BARU > 0, t > 2 dan (XAU/BTC) positif di kedua feed.
"""
from __future__ import annotations

import io
import json
import sys
import time
import urllib.error
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from .news_detik import NEW, Tick, events, prepare

ROOT = Path(__file__).resolve().parent.parent
EXT = ROOT / "data" / "research" / "eksternal"
ETH_DIR = EXT / "binance_1s_eth"
OUT = ROOT / "docs" / "eksternal" / "hasil_pra_aset.txt"
JSON = ROOT / "cloud" / "api" / "pra_aset.json"
ETH_URL = "https://data.binance.vision/data/spot/daily/klines/ETHUSDT/1s"
ETH_SPREAD = 0.0005
START = pd.Timestamp("2018-01-01", tz="UTC")
DETIK = [1, 2, 3, 5]
MENIT = [60, 120, 180, 240, 300]
KELUAR = DETIK + MENIT
GRUP = ["NFP", "CPI", "PPI", "RETAIL", "PCE", "GDP", "FOMC", "JOLTS", "ISM", "ADP", "CLAIMS"]
FEEDS = {"XAU": ("XAU", "XAU_EXNESS"), "BTC": ("BTC", "BTC_EXNESS"), "ETH": ("ETH",)}
SLIP = {"XAU": 0.30, "BTC": 0.0002, "ETH": 0.0002}         # XAU $; kripto bagian harga
# judul berita → (grup waktu rilis, kolom aturan terbaik di berita_gabung)
ATURAN = {"CPI m/m": ("CPI", "K|P"), "Core CPI m/m": ("CPI", "K|P"), "CPI y/y": ("CPI", "P"),
          "Unemployment Rate": ("NFP", "K|P"), "Core PPI m/m": ("PPI", "-P"), "ISM Services PMI": ("ISM", "-P"),
          "JOLTS Job Openings": ("JOLTS", "-P"), "Advance GDP q/q": ("GDP", "G")}


# ------------------------------------------------------------------ data ETH
def _eth_file(t: pd.Timestamp) -> Path:
    return ETH_DIR / f"ETHUSDT_{t:%Y%m%d_%H%M}.parquet"


def unduh() -> None:
    """Satu zip harian per hari rilis (paralel 6), simpan jendela −2…+16 menit per rilis."""
    ETH_DIR.mkdir(parents=True, exist_ok=True)
    ev = events()
    ev = ev[(ev.time >= START) & ev.group.isin(GRUP)]
    todo: dict = {}
    for t in ev.time:
        if not _eth_file(t).exists():
            todo.setdefault(t.normalize(), []).append(t)
    print(f"ETH: {sum(len(v) for v in todo.values())} jendela, {len(todo)} hari", flush=True)

    def hari(item):
        day, ts = item
        url = f"{ETH_URL}/ETHUSDT-1s-{day:%Y-%m-%d}.zip"
        for k in range(6):
            try:
                with urllib.request.urlopen(url, timeout=120) as r:
                    raw = r.read()
                break
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    for t in ts:
                        pd.DataFrame({"close": []}).to_parquet(_eth_file(t))
                    return "404"
                time.sleep(2 ** k)
            except Exception:  # noqa: BLE001 - transfer terpotong -> ulang
                time.sleep(2 ** k)
        else:
            return "gagal"
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            k = pd.read_csv(z.open(z.namelist()[0]), header=None, usecols=[0, 4])
        k.columns = ["open_time", "close"]
        unit = "us" if k.open_time.iloc[0] > 1e14 else "ms"
        k.index = pd.to_datetime(k.open_time, unit=unit, utc=True) + pd.Timedelta(seconds=1)
        for t in ts:
            k.loc[(k.index >= t - pd.Timedelta(minutes=2)) & (k.index <= t + pd.Timedelta(minutes=16)),
                  ["close"]].to_parquet(_eth_file(t))
        return "ok"
    hasil = {}
    with ThreadPoolExecutor(6) as ex:
        for i, r in enumerate(ex.map(hari, sorted(todo.items())), 1):
            hasil[r] = hasil.get(r, 0) + 1
            if i % 50 == 0:
                print(f"  {i}/{len(todo)} {hasil}", flush=True)
    print("selesai", hasil, flush=True)


def eth_tick(t0: pd.Timestamp) -> Tick | None:
    f = _eth_file(t0)
    if not f.exists():
        return None
    k = pd.read_parquet(f)
    if len(k) < 60:
        return None
    half = k.close.to_numpy() * ETH_SPREAD / 2
    df = pd.DataFrame({"bid": k.close.to_numpy() - half, "ask": k.close.to_numpy() + half}, index=k.index)
    p = Tick(t0, df, 1.0)
    if not ((p.T >= -60) & (p.T < 0)).any() or not ((p.T >= 0) & (p.T < 5)).any():
        return None
    return p


# ------------------------------------------------------------------ simulasi
def hasil_rilis(p: Tick, aset: str) -> np.ndarray | None:
    """[arah (0 BUY, 1 SELL), keluar] P&L REALISTIS: keputusan t0−1, terisi 0,5 dtk kemudian, slippage masuk & keluar.
    XAU dalam $, kripto dalam % harga."""
    i = p.at(-0.5)
    if i < 0 or p.T[i] < -60:
        return None
    slip = SLIP[aset] if aset == "XAU" else SLIP[aset] * float(p.mid[i])
    buy, sell = float(p.ask[i]) + slip, float(p.bid[i]) - slip
    out = np.full((2, len(KELUAR)), np.nan)
    for j, h in enumerate(KELUAR):
        k = p.at(h + 0.5)
        if k < 0 or p.T[-1] < h:
            return None
        out[0, j] = float(p.bid[k]) - slip - buy
        out[1, j] = sell - (float(p.ask[k]) + slip)
    if aset != "XAU":
        out = out / float(p.mid[i]) * 100
    return out


def tab_feed(feed: str, times: list) -> dict:
    out = {}
    for t in times:
        p = eth_tick(t) if feed == "ETH" else prepare(t, feed)
        if p is None:
            continue
        r = hasil_rilis(p, feed.split("_")[0])
        if r is not None:
            out[t] = r
    return out


def arah_petunjuk() -> pd.Series:
    """Waktu rilis → +1 (emas naik → BUY) / −1 (SELL) dari petunjuk teruji (jumlah suara judul yang rilis bersamaan)."""
    from .berita_gabung import emas, tabel
    df = emas(tabel())
    df["-P"] = -df.P
    df["K|P"] = np.where(df.K.fillna(0) != 0, df.K, df.P)
    parts = []
    for judul, (_, col) in ATURAN.items():
        x = df[(df.event == judul) & df[col].notna() & (df[col] != 0) & df.arah_bawah.notna()]
        parts.append(pd.Series(np.where(x[col] < 0, x.arah_bawah, x.arah_atas), index=x.t0))
    s = pd.concat(parts).groupby(level=0).sum()
    return np.sign(s[s != 0])


def ringkas(rows: list[tuple[pd.Timestamp, float]]) -> dict:
    if not rows:
        return {"n": 0}
    t = pd.DatetimeIndex([r[0] for r in rows])
    v = np.array([r[1] for r in rows])
    lama, baru = v[t < NEW], v[t >= NEW]
    sd = v.std(ddof=1) if len(v) > 2 else np.nan
    return {"n": int(len(v)), "wr": round(float((v > 0).mean() * 100), 1), "avg": round(float(v.mean()), 4),
            "t": round(float(v.mean() / (sd / np.sqrt(len(v)))), 2) if sd and sd == sd else None,
            "n_lama": int(len(lama)), "lama": round(float(lama.mean()), 4) if len(lama) else None,
            "wr_lama": round(float((lama > 0).mean() * 100), 1) if len(lama) else None,
            "n_baru": int(len(baru)), "baru": round(float(baru.mean()), 4) if len(baru) else None,
            "wr_baru": round(float((baru > 0).mean() * 100), 1) if len(baru) else None}


def nama_keluar(h: int) -> str:
    return f"{h} dtk" if h < 60 else f"{h // 60} mnt"


# ------------------------------------------------------------------ ARAH SAJA (permintaan pengguna 10 Okt 2026)
H_ARAH = [1, 2, 3, 5, 10]


def gerak(p: Tick, h: int) -> float | None:
    """Tanda gerak harga tengah (mid) dari t0−1 dtk ke t0+h dtk: +1 naik, −1 turun, 0 belum bergerak."""
    i, k = p.at(-1), p.at(h)
    if i < 0 or k < 0 or p.T[i] < -60 or p.T[-1] < h:
        return None
    d = float(p.mid[k] - p.mid[i])
    return 0.0 if abs(d) < 1e-12 else float(np.sign(d))


def arah_main() -> None:
    """Tebakan arah SEBELUM rilis (petunjuk teruji) vs arah harga 1–10 detik setelah rilis — tanpa untung/rugi.
    Benar = harga bergerak searah tebakan; "belum gerak" (harga sama persis) dilaporkan terpisah. Juga dasar: % rilis
    harga naik (tanpa tebakan) supaya terlihat apakah tebakan lebih baik dari lempar koin."""
    ev = events()
    ev = ev[(ev.time >= pd.Timestamp("2010-01-01", tz="UTC")) & ev.group.isin(GRUP)]
    grup = dict(zip(ev.time, ev.group))
    arah = arah_petunjuk()
    feeds = {"XAU": ("XAU_EXNESS", "XAU"), "BTC": ("BTC_EXNESS", "BTC"), "ETH": ("ETH",)}
    gk = {}
    for fs in feeds.values():
        for f in fs:
            gk[f] = {}
            for t in sorted(ev.time):
                p = eth_tick(t) if f == "ETH" else prepare(t, f)
                if p is not None:
                    gk[f][t] = {h: gerak(p, h) for h in H_ARAH}
    L = ["# ⏱️ ARAH 1–10 detik setelah rilis vs tebakan sebelum rilis (tanpa untung/rugi)",
         "Harga tengah (bid+ask)/2 pada t0−1 dtk dibanding t0+1/2/3/5/10 dtk. Benar = searah tebakan (dari rilis yang "
         "harganya sudah bergerak); 'gerak' = % rilis yang harganya sudah berubah. Tebakan = petunjuk teruji "
         "(research/berita_gabung.py & sumber_lain.py → arah emas; kripto disamakan). Dasar = % naik tanpa tebakan.", ""]
    out = {}
    for g in GRUP:
        tg = [t for t in sorted(ev.time) if grup.get(t) == g]
        L += ["", f"## {g} ({len(tg)} rilis)"]
        out[g] = {}
        for aset, fs in feeds.items():
            res = {}
            for h in H_ARAH:
                per = {}
                for f in fs:
                    rows = [(t, gk[f][t][h]) for t in tg if t in gk[f] and gk[f][t][h] is not None]
                    gerak_ = [(t, v) for t, v in rows if v != 0]
                    tebak = [(t, v * arah[t]) for t, v in gerak_ if t in arah.index]
                    def pct(x, f_=lambda v: v > 0):
                        return (round(float(np.mean([f_(v) for _, v in x]) * 100), 1), len(x)) if x else (None, 0)
                    lama = [(t, v) for t, v in tebak if t < NEW]
                    baru = [(t, v) for t, v in tebak if t >= NEW]
                    per[f] = {"benar": pct(tebak), "lama": pct(lama), "baru": pct(baru),
                              "gerak": round(len(gerak_) / max(len(rows), 1) * 100), "dasar_naik": pct(gerak_)}
                res[h] = per
            out[g][aset] = {str(h): res[h][fs[0]] | {"feed": fs[0], "lain": {f: res[h][f]["benar"] for f in fs[1:]}}
                            for h in H_ARAH}
            for h in H_ARAH:
                x = res[h][fs[0]]
                lain = " ".join(f"| {f} {res[h][f]['benar'][0]}% (n {res[h][f]['benar'][1]})" for f in fs[1:])
                L.append(f"   {aset} {h:2d} dtk: tebakan benar {x['benar'][0]}% (n {x['benar'][1]}; LAMA {x['lama'][0]}% "
                         f"n {x['lama'][1]}, BARU {x['baru'][0]}% n {x['baru'][1]}) | sudah gerak {x['gerak']}% | dasar "
                         f"naik {x['dasar_naik'][0]}% (n {x['dasar_naik'][1]}) {lain}")
    d = json.loads(JSON.read_text(encoding="utf-8")) if JSON.exists() else {}
    d["arah"] = out
    JSON.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT.with_name("hasil_pra_arah.txt")).write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


def main() -> None:
    if sys.argv[1:2] == ["unduh"]:
        unduh()
        return
    if sys.argv[1:2] == ["arah"]:
        arah_main()
        return
    ev = events()
    ev = ev[(ev.time >= pd.Timestamp("2010-01-01", tz="UTC")) & ev.group.isin(GRUP)]
    grup = dict(zip(ev.time, ev.group))
    arah = arah_petunjuk()
    times = sorted(ev.time)
    tabs = {f: tab_feed(f, times) for fs in FEEDS.values() for f in fs}
    L = ["# ⏱️ Entry 1 detik sebelum rilis, tutup 1–5 dtk / 1–5 mnt — XAU, BTC, ETH", __doc__.split("\n\n")[1], ""]
    L += [f"{f}: {len(v)} rilis dengan data" for f, v in tabs.items()]
    out = {"dibuat": "research/pra_aset.py", "satuan": {"XAU": "$ per 0,01 lot", "BTC": "% harga", "ETH": "% harga"},
           "berita": {}}
    for g in GRUP:
        tg = [t for t in times if grup.get(t) == g]
        L += ["", f"## {g} ({len(tg)} rilis)"]
        out["berita"][g] = {}
        for aset, feeds in FEEDS.items():
            out["berita"][g][aset] = {}
            for cara in ("petunjuk", "BUY", "SELL"):
                if cara == "petunjuk":
                    d = {t: int(arah[t]) for t in tg if t in arah.index}
                else:
                    d = {t: 1 if cara == "BUY" else -1 for t in tg}
                if not d:
                    continue
                best = None
                for rentang, hs in (("dtk", DETIK), ("mnt", MENIT)):
                    pilih = None
                    for h in hs:
                        j = KELUAR.index(h)
                        per = {}
                        for f in feeds:
                            rows = [(t, tabs[f][t][0 if s > 0 else 1, j]) for t, s in d.items() if t in tabs[f]]
                            per[f] = ringkas(rows)
                        utama = per[feeds[-1]] if aset != "ETH" else per["ETH"]      # Exness bila ada
                        if not utama.get("n"):
                            continue
                        skor = utama["lama"] if utama.get("lama") is not None and utama["n_lama"] >= 10 else utama["avg"]
                        if pilih is None or skor > pilih[0]:
                            pilih = (skor, h, per)
                    if not pilih:
                        continue
                    _, h, per = pilih
                    utama = per[feeds[-1]]
                    teruji = (utama["n"] >= 30 and (utama.get("lama") or -1) > 0 and (utama.get("baru") or -1) > 0
                              and (utama.get("t") or 0) > 2 and all((per[f].get("avg") or -1) > 0 for f in feeds))
                    rec = {"keluar": nama_keluar(h), "detik": h, **utama, "teruji": bool(teruji),
                           "feed": {f: {k: per[f].get(k) for k in ("n", "wr", "avg")} for f in feeds}}
                    out["berita"][g][aset][f"{cara}|{rentang}"] = rec
                    L.append(f"   {aset} {cara:8s} tutup {rentang}: terbaik {nama_keluar(h):6s} n {utama['n']:4d} "
                             f"untung {utama['wr']:5.1f}% rata {utama['avg']:+.3f} t {utama.get('t')} | LAMA "
                             f"{utama.get('lama')} BARU {utama.get('baru')} (WR {utama.get('wr_baru')}%)"
                             + (" ✅ TERUJI" if teruji else "")
                             + "".join(f" | {f} rata {per[f].get('avg')}" for f in feeds if f != feeds[-1]))
                    if best is None or (rec.get("avg") or -9) > (best.get("avg") or -9):
                        best = rec
    JSON.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
